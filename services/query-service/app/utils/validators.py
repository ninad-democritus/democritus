"""SQL validation utilities"""
import re
import logging
from typing import List, Set
import sqlparse

from ..models import SQLValidationResult, TableMetadata

logger = logging.getLogger(__name__)


def validate_sql_syntax(sql: str) -> SQLValidationResult:
    """
    Validate SQL syntax.
    
    Args:
        sql: SQL query string
        
    Returns:
        Validation result
    """
    errors = []
    warnings = []
    suggestions = []
    
    if not sql or not sql.strip():
        return SQLValidationResult(
            is_valid=False,
            errors=["SQL query is empty"],
            warnings=[],
            suggestions=["Provide a valid SQL query"]
        )
    
    try:
        # Parse SQL
        parsed = sqlparse.parse(sql)
        
        if not parsed:
            errors.append("Failed to parse SQL")
            return SQLValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                suggestions=["Check SQL syntax"]
            )
        
        # Basic syntax checks
        sql_upper = sql.upper()
        
        # Check for SELECT or WITH statement (CTEs)
        if not sql_upper.strip().startswith("SELECT") and not sql_upper.strip().startswith("WITH"):
            warnings.append("Query does not start with SELECT or WITH")
        
        # Check for dangerous operations
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                errors.append(f"Dangerous operation '{keyword}' not allowed")
        
        # Check GROUP BY and SELECT alignment
        group_by_validation = _validate_group_by_in_select(sql)
        if not group_by_validation["valid"]:
            errors.extend(group_by_validation["errors"])
            suggestions.extend(group_by_validation["suggestions"])
        
        # Check for proper statement termination
        if sql.strip().endswith(";"):
            sql = sql.strip()[:-1]  # Remove trailing semicolon
        
        is_valid = len(errors) == 0
        
        return SQLValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"SQL syntax validation error: {e}")
        return SQLValidationResult(
            is_valid=False,
            errors=[f"Syntax error: {str(e)}"],
            warnings=[],
            suggestions=["Check SQL syntax and try again"]
        )


def _validate_group_by_in_select(sql: str) -> dict:
    """
    Validate that all GROUP BY columns are in SELECT clause.
    
    Args:
        sql: SQL query string
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    suggestions = []
    
    # Check if query has GROUP BY
    group_by_pattern = r'GROUP\s+BY\s+(.+?)(?:ORDER\s+BY|HAVING|LIMIT|$)'
    match = re.search(group_by_pattern, sql, re.IGNORECASE | re.DOTALL)
    
    if not match:
        return {"valid": True, "errors": [], "suggestions": []}
    
    group_by_clause = match.group(1).strip()
    
    # Extract GROUP BY columns (handle table.column and aliases)
    group_by_cols = []
    for col in group_by_clause.split(','):
        col = col.strip()
        # Remove table prefix if present (e.g., "E.Team" -> "Team")
        if '.' in col:
            col = col.split('.')[-1]
        group_by_cols.append(col.upper())
    
    # Extract SELECT columns (simplified - look for column names before FROM)
    select_pattern = r'SELECT\s+(.+?)\s+FROM'
    select_match = re.search(select_pattern, sql, re.IGNORECASE | re.DOTALL)
    
    if not select_match:
        return {"valid": True, "errors": [], "suggestions": []}
    
    select_clause = select_match.group(1).strip()
    select_upper = select_clause.upper()
    
    # Check if each GROUP BY column appears in SELECT
    missing_cols = []
    for col in group_by_cols:
        # Check if column name appears in SELECT (could be aliased or aggregated)
        if col not in select_upper:
            missing_cols.append(col)
    
    if missing_cols:
        errors.append(f"GROUP BY columns not in SELECT: {', '.join(missing_cols)}")
        suggestions.append(f"Add these columns to SELECT clause: {', '.join(missing_cols)}")
        return {"valid": False, "errors": errors, "suggestions": suggestions}
    
    return {"valid": True, "errors": [], "suggestions": []}


def validate_sql_against_schema(
    sql: str,
    metadata: List[TableMetadata]
) -> SQLValidationResult:
    """
    Validate SQL against table schemas.
    
    Args:
        sql: SQL query string
        metadata: List of table metadata
        
    Returns:
        Validation result
    """
    errors = []
    warnings = []
    suggestions = []
    
    # First check syntax
    syntax_result = validate_sql_syntax(sql)
    if not syntax_result.is_valid:
        return syntax_result
    
    # Extract table and column names from SQL
    sql_upper = sql.upper()
    
    # Build schema lookup
    schema_tables = {}
    schema_columns = {}
    
    for table_meta in metadata:
        table_name = table_meta.table_name.lower()
        full_name = f"{table_meta.schema_name}.{table_name}".lower()
        # Also store with catalog prefix (iceberg.schema.table)
        full_name_with_catalog = f"iceberg.{table_meta.schema_name}.{table_name}".lower()
        
        schema_tables[table_name] = table_meta
        schema_tables[full_name] = table_meta
        schema_tables[full_name_with_catalog] = table_meta
        
        # Store columns for this table
        schema_columns[table_name] = {col.name.lower(): col for col in table_meta.columns}
        schema_columns[full_name] = {col.name.lower(): col for col in table_meta.columns}
        schema_columns[full_name_with_catalog] = {col.name.lower(): col for col in table_meta.columns}
    
    # Debug: Log schema tables
    logger.info(f"Schema tables available: {list(schema_tables.keys())}")
    
    # Extract CTE (Common Table Expression) names from WITH clauses
    cte_names = set()
    with_pattern = r'\bWITH\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+AS'
    with_matches = re.findall(with_pattern, sql_upper, re.IGNORECASE)
    cte_names.update([cte.lower() for cte in with_matches])
    
    # Also look for multiple CTEs (comma-separated)
    # Pattern: WITH cte1 AS (...), cte2 AS (...), cte3 AS (...)
    multi_cte_pattern = r',\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+AS'
    multi_cte_matches = re.findall(multi_cte_pattern, sql_upper, re.IGNORECASE)
    cte_names.update([cte.lower() for cte in multi_cte_matches])
    
    logger.info(f"Detected CTEs: {cte_names}")
    
    # Extract referenced tables from SQL (simple pattern matching)
    # Look for FROM and JOIN clauses
    from_matches = re.findall(r'\bFROM\s+([a-zA-Z0-9_.]+)', sql_upper, re.IGNORECASE)
    join_matches = re.findall(r'\bJOIN\s+([a-zA-Z0-9_.]+)', sql_upper, re.IGNORECASE)
    
    referenced_tables = []
    referenced_tables.extend([t.lower() for t in from_matches])
    referenced_tables.extend([t.lower() for t in join_matches])
    
    # Remove duplicates
    referenced_tables = list(set(referenced_tables))
    
    logger.info(f"Referenced tables extracted: {referenced_tables}")
    
    # Validate tables exist (but skip CTEs)
    for table in referenced_tables:
        # Skip if it's a CTE
        if table in cte_names:
            logger.info(f"Skipping CTE: {table}")
            continue
        # Skip if it has an alias (single letter or word after space)
        table_name = table.split()[0] if ' ' in table else table
        logger.info(f"Validating table: {table_name}")
        if table_name not in schema_tables:
            logger.warning(f"Table '{table_name}' not found. Available: {list(schema_tables.keys())}")
            errors.append(f"Table '{table_name}' not found in schema")
            suggestions.append(f"Available tables: {', '.join(schema_tables.keys())}")
        else:
            logger.info(f"Table '{table_name}' found in schema")
    
    # Extract column names (basic pattern)
    # This is simplified - a full SQL parser would be more robust
    select_part = sql_upper.split("FROM")[0] if "FROM" in sql_upper else sql_upper
    
    # Look for common column patterns
    column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
    potential_columns = re.findall(column_pattern, sql)
    
    # Filter out SQL keywords
    sql_keywords = {
        'select', 'from', 'where', 'group', 'by', 'order', 'limit',
        'as', 'and', 'or', 'not', 'in', 'is', 'null', 'sum', 'count',
        'avg', 'max', 'min', 'distinct', 'having', 'join', 'on', 'inner',
        'left', 'right', 'outer', 'cast', 'case', 'when', 'then', 'else', 'end'
    }
    
    potential_columns = [
        col for col in potential_columns
        if col.lower() not in sql_keywords
    ]
    
    # Validate columns exist (if we have table context)
    if referenced_tables and schema_columns:
        # Check against all available columns from referenced tables
        all_available_cols = set()
        for table in referenced_tables:
            if table in schema_columns:
                all_available_cols.update(schema_columns[table].keys())
        
        for col in potential_columns:
            col_lower = col.lower()
            if col_lower not in all_available_cols and len(all_available_cols) > 0:
                # Only warn, don't error (could be aliased or function result)
                warnings.append(f"Column '{col}' not found in referenced tables")
    
    is_valid = len(errors) == 0
    
    return SQLValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions
    )


def extract_table_names(sql: str) -> List[str]:
    """
    Extract table names from SQL query.
    
    Args:
        sql: SQL query
        
    Returns:
        List of table names
    """
    tables = []
    
    # FROM clause
    from_match = re.search(r'\bFROM\s+([a-zA-Z0-9_.]+)', sql, re.IGNORECASE)
    if from_match:
        tables.append(from_match.group(1))
    
    # JOIN clauses
    join_matches = re.findall(r'\bJOIN\s+([a-zA-Z0-9_.]+)', sql, re.IGNORECASE)
    tables.extend(join_matches)
    
    return tables


def extract_column_names(sql: str) -> List[str]:
    """
    Extract column names from SQL query.
    
    Args:
        sql: SQL query
        
    Returns:
        List of column names
    """
    # This is a simplified extraction - a full SQL parser would be more robust
    columns = []
    
    # Get SELECT clause
    if "FROM" in sql.upper():
        select_clause = sql.upper().split("FROM")[0]
    else:
        select_clause = sql
    
    # Extract identifiers
    pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
    potential_columns = re.findall(pattern, select_clause)
    
    # Filter SQL keywords
    sql_keywords = {'SELECT', 'AS', 'DISTINCT', 'ALL'}
    columns = [col for col in potential_columns if col.upper() not in sql_keywords]
    
    return columns

