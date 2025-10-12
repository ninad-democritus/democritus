"""Core service utilities - reusable by both LangGraph and REST API"""
import logging
from typing import List, Dict, Any
from decimal import Decimal

from ..models import SQLValidationResult, TableMetadata
from ..utils.validators import validate_sql_against_schema, extract_table_names
from ..services.trino_client import get_trino_client
from ..services.openmetadata_client import get_openmetadata_client
from ..config import settings

logger = logging.getLogger(__name__)


async def validate_sql_with_metadata(sql: str) -> SQLValidationResult:
    """
    Validate SQL query - fetches metadata internally.
    
    Args:
        sql: SQL query to validate
        
    Returns:
        Validation result
    """
    try:
        # Extract table names from SQL
        table_names = extract_table_names(sql)
        logger.info(f"Extracted tables from SQL: {table_names}")
        
        # Fetch metadata for referenced tables
        metadata_client = get_openmetadata_client()
        table_metadata: List[TableMetadata] = []
        
        for table_name in table_names:
            # Parse fully qualified name (e.g., iceberg.default.event)
            parts = table_name.split('.')
            if len(parts) == 3:
                catalog, schema, table = parts
            elif len(parts) == 2:
                catalog = settings.TRINO_CATALOG
                schema, table = parts
            else:
                catalog = settings.TRINO_CATALOG
                schema = settings.TRINO_SCHEMA
                table = table_name
            
            # Construct OpenMetadata FQN
            # Trino format: iceberg.default.table_name
            # OpenMetadata FQN format: data-pipeline-service.default.default.table_name
            # Format: {service}.{database}.{schema}.{table}
            om_fqn = f"{settings.OPENMETADATA_SERVICE_NAME}.{schema}.{schema}.{table}"
            
            logger.info(f"Fetching metadata for table: {table_name} -> OpenMetadata FQN: {om_fqn}")
            
            metadata = await metadata_client.get_table_metadata(table_fqn=om_fqn)
            if metadata:
                table_metadata.append(metadata)
            else:
                logger.warning(f"No metadata found for table: {table_name} (FQN: {om_fqn})")
        
        # Validate SQL against schema
        validation_result = validate_sql_against_schema(sql, table_metadata)
        
        return validation_result
        
    except Exception as e:
        logger.exception("SQL validation failed")
        return SQLValidationResult(
            is_valid=False,
            errors=[str(e)],
            warnings=[],
            suggestions=[]
        )


def execute_sql_query(sql: str, limit: int = None) -> Dict[str, Any]:
    """
    Execute SQL query via Trino.
    
    Args:
        sql: SQL query to execute
        limit: Maximum rows to return
        
    Returns:
        Dictionary with columns, rows, row_count, truncated
    """
    try:
        trino_client = get_trino_client()
        
        # Execute query
        results = trino_client.execute_query(
            sql=sql,
            limit=limit or settings.MAX_RESULT_ROWS
        )
        
        # Extract columns
        columns = list(results[0].keys()) if results else []
        
        # Convert Decimal to float for JSON serialization
        cleaned_rows = []
        for row in results:
            cleaned_row = {}
            for key, value in row.items():
                if isinstance(value, Decimal):
                    cleaned_row[key] = float(value)
                else:
                    cleaned_row[key] = value
            cleaned_rows.append(cleaned_row)
        
        return {
            "columns": columns,
            "rows": cleaned_rows,
            "row_count": len(cleaned_rows),
            "truncated": len(cleaned_rows) >= (limit or settings.MAX_RESULT_ROWS)
        }
        
    except Exception as e:
        logger.exception("SQL execution failed")
        raise

