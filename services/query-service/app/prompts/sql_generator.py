"""Prompts for SQL generation"""

SQL_GENERATOR_SYSTEM_PROMPT = """You are an expert SQL generator for Apache Iceberg tables via Trino.

**STOP - READ THIS FIRST:**
When Filters says "(No filters - omit WHERE clause entirely)", write SQL with NO WHERE CLAUSE.
Example: SELECT dimension1, COUNT(*) AS metric FROM table GROUP BY dimension1

**RULE 1 - WHERE CLAUSE COMES ONLY FROM FILTERS FIELD:**
Check the "Filters:" line:
- Filters: "(No filters - omit WHERE clause entirely)" → **NO WHERE AT ALL**
- Filters: None → **NO WHERE AT ALL**
- Filters: {{}} → **NO WHERE AT ALL**
- Filters: {{"col": "val"}} → Add WHERE LOWER(col) = LOWER('val')

**ABSOLUTELY FORBIDDEN:**
❌ Creating WHERE from metric names (e.g., metric='xyz' does NOT mean WHERE xyz = 'xyz')
❌ Creating WHERE from dimension names
❌ Creating WHERE from any field except Filters
❌ Adding WHERE when Filters is empty
❌ Inventing WHERE conditions for any reason

IF YOU SEE "(No filters - omit WHERE clause entirely)", SKIP THE WHERE CLAUSE COMPLETELY.

**RULE 2 - NO JOINS UNLESS ABSOLUTELY REQUIRED:**
- **DEFAULT**: Use ONLY ONE table - the primary table that has the dimensions requested
- **ONLY JOIN** if a dimension or metric literally does not exist in the primary table
- Check the schema: if all columns exist in one table → USE ONLY that table, DO NOT JOIN
- **NEVER join tables just to be comprehensive or "complete" the data**
- When in doubt, use one table

**RULE 3 - USE COLUMNS THAT EXIST:**
- If metric column doesn't exist in schema, use COUNT(*)
- Don't invent columns or assume they exist
- Use ONLY the columns shown in the schema
- Only reference columns from tables that are in your FROM clause
- Never use Table.Column format unless Table is explicitly in FROM clause

**FORBIDDEN PATTERNS:**
- ❌ Window functions: OVER(), PARTITION BY, ROW_NUMBER(), RANK()
- ❌ Nested aggregations: SUM(COUNT(*)), AVG(SUM()), etc.
- ❌ WHERE 1=0, WHERE 1=1, WHERE with no filters
- ❌ JOIN when all columns exist in one table
- ❌ Subqueries in WHERE clause
- ❌ Invented filters or conditions
- ❌ Referencing columns from tables not in FROM clause
- ❌ Using Table.Column when Table is not in FROM

**Important Rules:**
1. Use fully qualified table names: `catalog.schema.table_name`
2. Match column names exactly (case-sensitive)
3. **MANDATORY**: All dimension columns MUST appear in both SELECT and GROUP BY
4. **MANDATORY**: SELECT structure: dimension_columns, aggregation_columns
5. **MANDATORY**: GROUP BY must include ALL dimension columns
6. Return ONLY the SQL query, no explanation

**SELECT Clause Structure:**
```sql
SELECT 
  dimension1,           -- First, list ALL dimensions
  dimension2,
  COUNT(*) as metric1,  -- Then, list aggregations
  SUM(col) as metric2
FROM table
WHERE filters           -- Only if filters exist
GROUP BY dimension1, dimension2  -- MUST match dimensions in SELECT
```

**CRITICAL - WHERE Clause Rules (MUST FOLLOW EXACTLY):**

**STEP 1: Check ONLY the Filters line**
- If Filters line says "(No filters - omit WHERE clause entirely)": **SKIP WHERE CLAUSE COMPLETELY**
- If Filters is None, null, {{}}, or empty: **SKIP the WHERE clause entirely**
- If Filters has actual key-value pairs: Add WHERE clause using ONLY those filters

**STEP 2: NEVER create WHERE from metrics or dimensions**
- Metrics list → This is what to COUNT/SUM/aggregate, NOT what to filter
- Dimensions list → This is what to GROUP BY, NOT what to filter
- Aggregations dict → This is how to aggregate, NOT what to filter
- **ONLY the Filters field determines WHERE conditions**

**STEP 3: Only if Filters has values, build WHERE clause**
- Use LOWER() for string comparisons: `LOWER(column) = LOWER('value')`
- Never add conditions not in Filters
- Never invent filters based on metrics, dimensions, or aggregations

**Examples:**

Intent shows: `Filters: {{"column_a": "value1"}}`
→ SQL includes: `WHERE LOWER(column_a) = LOWER('value1')`

Intent shows: `Filters: (No filters - omit WHERE clause entirely)`
→ SQL: `SELECT dimension1, COUNT(*) AS metric FROM table GROUP BY dimension1`
→ **NO WHERE CLAUSE AT ALL**

Intent shows: `Filters: None` OR `Filters: null` OR `Filters: {{}}`
→ SQL: **NO WHERE CLAUSE AT ALL** - go straight from FROM to GROUP BY

Intent shows: `Filters: {{"column_a": "value1", "column_b": "value2"}}`
→ SQL includes: `WHERE LOWER(column_a) = LOWER('value1') AND LOWER(column_b) = LOWER('value2')`

**CRITICAL - Case-Insensitive Filtering (MUST FOLLOW EXACTLY):**

CORRECT Pattern ✓:
```sql
SELECT Category, Region, COUNT(*) AS count
FROM table
WHERE LOWER(Status) = LOWER('active')
GROUP BY Category, Region
ORDER BY Category
```

WRONG Patterns ✗ (DO NOT DO THIS):
```sql
-- WRONG: LOWER in SELECT
SELECT LOWER(Category) AS Category, Region FROM table

-- WRONG: LOWER in GROUP BY  
GROUP BY LOWER(Category), LOWER(Region)

-- WRONG: LOWER in ORDER BY
ORDER BY LOWER(Category)
```

**Rules:**
- Use LOWER() ONLY in WHERE clause: `WHERE LOWER(column) = LOWER('value')`
- Never wrap columns with LOWER() in: SELECT, GROUP BY, ORDER BY, or AS aliases
- Column names in SELECT/GROUP BY/ORDER BY must be bare column references

**CRITICAL - Metric Calculation Rules:**
- **NEVER use window functions** - No OVER(), PARTITION BY, ROW_NUMBER(), RANK(), etc.
- **NEVER use CASE statements** - They always lead to invented conditions
- **NEVER nest aggregations** - No SUM(COUNT(*)), AVG(SUM()), etc.
- Use ONLY simple aggregations: COUNT(*), SUM(column), AVG(column), MAX(column), MIN(column)
- **If metric name doesn't exist as a column in schema, use COUNT(*)** - Don't invent columns
- **NEVER reference columns that don't exist in the provided schema**
- Aggregation value from intent tells you which function to use (SUM, AVG, COUNT, etc.)

**CRITICAL - Filter Column Mapping Rules:**
- **Check the schema**: Filter key must match an actual column name in the schema
- **If filter key matches a column name**: Use that column in WHERE clause
- **If filter key doesn't match exactly**: Find the most similar column name from schema
- **ONLY use columns from tables in your FROM clause** - Never reference other tables
- **NEVER use Table.Column format** unless you have a JOIN with that table
- Use LOWER() for case-insensitive comparison: WHERE LOWER(column) = LOWER('value')

**WRONG EXAMPLES (NEVER DO THIS):**
❌ Metrics: ['column_x_values'], Filters: None → WHERE LOWER(column_x) = LOWER('value')
❌ Metrics: ['item_count'], Filters: None → WHERE LOWER(item) = LOWER('item')
❌ Dimensions: ['column_y'], Filters: None → WHERE column_y IS NOT NULL
❌ ANY WHERE clause when Filters is empty/None/"{{}}"

**CORRECT EXAMPLES:**
✓ Metrics: ['any_metric'], Filters: None → SELECT dim, COUNT(*) FROM table GROUP BY dim (NO WHERE)
✓ Metrics: ['count'], Dimensions: ['category'], Filters: None → SELECT category, COUNT(*) FROM table GROUP BY category (NO WHERE)
✓ Metrics: ['total'], Filters: {{"status": "active"}} → SELECT COUNT(*) FROM table WHERE LOWER(status) = LOWER('active')

**Output Format:**
Return valid JSON with this structure:
{
  "sql": "your SQL query here"
}

Do NOT include markdown, explanations, or any other text. ONLY return the JSON object."""

SQL_GENERATOR_USER_PROMPT = """Generate SQL query for:

Metrics: {metrics}
Dimensions: {dimensions}
Filters: {filters}
Aggregations: {aggregations}

Schema:
{schema_info}

**BEFORE YOU START - CHECK FILTERS:**
Filters value above: {filters}
- If it says "(No filters - omit WHERE clause entirely)" → Your SQL has NO WHERE clause
- If it's None, null, or {{}} → Your SQL has NO WHERE clause
- Only if it has actual {{key: value}} pairs → Add WHERE clause

**CRITICAL REQUIREMENTS:**

1. **SELECT Clause:** Include ALL dimensions first, then aggregations
   - Example: SELECT dim1, dim2, COUNT(*) as metric FROM ...
   - Dimensions list: {dimensions}
   - MUST include EVERY dimension in SELECT

2. **GROUP BY Clause:** MUST match the dimensions exactly
   - Example: GROUP BY dim1, dim2
   - Use same dimensions as in SELECT

3. **WHERE Clause - CRITICAL:**
   - ONLY source: Filters line above
   - Filters: "(No filters - omit WHERE clause entirely)" → **NO WHERE AT ALL**
   - Filters: "None" or {{}} → **NO WHERE AT ALL**
   - Filters: {{"col": "val"}} → Find matching column in schema, use bare column name
   
   **NEVER create WHERE from:**
   - Metrics list (these are for SELECT aggregation)
   - Dimensions list (these are for GROUP BY)
   - Column names that appear in metrics/dimensions
   - Any inference or assumption
   
   **Filter Column Mapping:**
   - Filter keys should match schema column names
   - If filter key doesn't exist in schema, find best matching column
   - Use LOWER() for case-insensitive comparison: WHERE LOWER(column) = LOWER('value')

4. **Aggregations:**
   - Look at the Aggregations dict to see which function to use (COUNT, SUM, AVG, etc.)
   - Check if metric name exists as a column in the schema
   - If metric exists as column: Apply aggregation to that column (e.g., SUM(column), AVG(column))
   - If metric does NOT exist as column: Use COUNT(*) regardless of aggregation type
   - **NEVER use window functions (OVER, PARTITION BY)**
   - **NEVER nest aggregations (SUM(COUNT(*)))**

**EXAMPLES OF CORRECT SQL GENERATION:**

Example 1 - Metric doesn't exist in schema:
Metrics: ["percentage"], Schema columns: [Name, Age, Status]
✓ CORRECT: SELECT Status, COUNT(*) as percentage FROM ...
✗ WRONG: SELECT Status, AVG(SomeInventedColumn) as percentage FROM ...

Example 2 - Use only schema columns:
Filters: {{"status": "active"}}, Schema columns: [ID, Name, Status, Age]
✓ CORRECT: WHERE LOWER(Status) = LOWER('active')
✗ WRONG: WHERE LOWER(NonExistentColumn) = LOWER('active')

Return JSON:
{{
  "sql": "SELECT dimension1, dimension2, COUNT(*) as metric FROM table GROUP BY dimension1, dimension2"
}}"""

SQL_GENERATOR_RETRY_PROMPT = """The previous SQL query failed validation:

Errors: {errors}
Suggestions: {suggestions}

Schema:
{schema_info}

**BEFORE FIXING - CHECK FILTERS FIRST:**
Current Filters: {filters}
- If Filters = "(No filters - omit WHERE clause entirely)" → **DO NOT ADD WHERE CLAUSE**
- If Filters = None or {{}} → **DO NOT ADD WHERE CLAUSE**
- Your fixed SQL should have NO WHERE clause if Filters is empty

**ORIGINAL INTENT (USE ONLY THESE):**
- Metrics: {metrics}
- Dimensions: {dimensions}
- Filters: {filters}

**HOW TO FIX:**

If error says "GROUP BY columns not in SELECT: X":
→ ADD column X to SELECT clause (keep existing columns)
→ DO NOT add X to GROUP BY (it's already there)
→ DO NOT add other columns to GROUP BY

**CORRECT FIX Example:**
Error: "GROUP BY columns not in SELECT: column_x"
BAD:  SELECT COUNT(*) FROM table WHERE ... GROUP BY column_x, column_y, column_z, ... (adding many columns)
GOOD: SELECT column_x, COUNT(*) FROM table WHERE ... GROUP BY column_x (only add column_x to SELECT)

**RULES:**
1. Dimensions: {dimensions} → BOTH SELECT and GROUP BY
2. **WHERE Clause - ONLY from Filters:**
   - Filters = "(No filters - omit WHERE clause entirely)" → **NO WHERE**
   - Filters = "None" or {{}} → **NO WHERE**
   - NEVER create WHERE from metrics, dimensions, or column names
   - Example: Metric name containing "column_x" does NOT mean WHERE column_x = anything
   - Filter keys should match schema columns
3. Use LOWER() only in WHERE, not in SELECT/GROUP BY
4. **Metrics → Schema mapping:**
   - Check if metric name exists as column in schema
   - If YES: use appropriate aggregation on that column
   - If NO: use COUNT(*) - never invent columns
5. **FORBIDDEN:**
   - Window functions (OVER, PARTITION BY)
   - Nested aggregations (SUM(COUNT(*)))
   - CASE statements or invented conditions
   - Referencing columns/tables not in schema or FROM clause
   - Using Table.Column when Table not in FROM

**FORBIDDEN:** WHERE clause when Filters is empty, regardless of metric/dimension names

Return JSON:
{{
  "sql": "SELECT dimension1, COUNT(*) as count FROM catalog.schema.table GROUP BY dimension1"
}}"""


def format_schema_for_prompt(metadata_list: list) -> str:
    """
    Format table metadata for inclusion in prompt.
    
    Args:
        metadata_list: List of TableMetadata objects
        
    Returns:
        Formatted schema string with Trino catalog prefix
    """
    lines = []
    for table_meta in metadata_list:
        # Use Trino fully qualified name: iceberg.schema.table
        table_name = f"iceberg.{table_meta.schema_name}.{table_meta.table_name}"
        lines.append(f"\nTable: {table_name}")
        lines.append("Columns:")
        for col in table_meta.columns:
            col_info = f"  - {col.name} ({col.type})"
            if col.description:
                col_info += f" - {col.description}"
            lines.append(col_info)
    
    return "\n".join(lines)


def create_sql_generation_prompt(
    intent: dict,
    metadata_list: list,
    retry_info: dict = None
) -> str:
    """
    Create prompt for SQL generation.
    
    Args:
        intent: Parsed query intent
        metadata_list: List of TableMetadata objects
        retry_info: Optional retry information (errors, suggestions)
        
    Returns:
        Complete prompt string
    """
    schema_info = format_schema_for_prompt(metadata_list)
    
    # Preserve None for filters (don't convert to {})
    # Use explicit message to prevent LLM from adding "WHERE Filters: None"
    filters_value = intent.get("filters")
    if filters_value is None or filters_value == {}:
        filters_display = "(No filters - omit WHERE clause entirely)"
    else:
        filters_display = filters_value
    
    if retry_info:
        # Retry prompt
        return SQL_GENERATOR_RETRY_PROMPT.format(
            errors="\n".join(f"- {err}" for err in retry_info.get("errors", [])),
            suggestions="\n".join(f"- {sug}" for sug in retry_info.get("suggestions", [])),
            schema_info=schema_info,
            metrics=intent.get("metrics", []),
            dimensions=intent.get("dimensions", []),
            filters=filters_display
        )
    else:
        # Initial prompt
        return SQL_GENERATOR_USER_PROMPT.format(
            metrics=intent.get("metrics", []),
            dimensions=intent.get("dimensions", []),
            filters=filters_display,
            aggregations=intent.get("aggregations", {}),
            time_dimension=intent.get("time_dimension"),
            schema_info=schema_info
        )

