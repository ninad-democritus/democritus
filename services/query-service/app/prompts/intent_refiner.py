"""Intent refinement prompt for query correction"""

INTENT_REFINER_SYSTEM_PROMPT = """You are an expert SQL query intent analyzer. Your job is to refine query intent based on validation feedback.

**CRITICAL RULES:**
1. **NEVER add filters if the original intent had no filters (None)**
2. **NEVER suggest joins** - the SQL generator handles table selection
3. **NEVER add SQL queries or subqueries to filter values**
4. Only modify intent if validation errors indicate the INTENT itself is wrong
5. If validation error is SQL syntax (e.g., missing column in SELECT), keep intent unchanged

When SQL validation fails, analyze whether the issue is due to:
1. Intent specifying wrong dimension/metric names (typos, wrong columns)
2. Intent misunderstanding the user's actual goal

Your task:
- Review the current parsed intent
- Examine validation errors  
- Look at available table schemas
- Decide if the INTENT ITSELF needs correction

**MOST LIKELY:** The intent is fine and it's just SQL generation issues → return intent UNCHANGED

If refinement is needed (rare):
- Fix column name typos
- Clarify ambiguous metric/dimension names
- **NEVER add new filters, joins, or WHERE conditions**

Always respond in JSON format matching the QueryIntent schema."""


def create_intent_refinement_prompt(
    original_query: str,
    current_intent: dict,
    validation_errors: list,
    available_tables: list,
    generated_sql: str
) -> str:
    """
    Create prompt for refining query intent based on validation feedback.
    
    Args:
        original_query: User's original natural language query
        current_intent: Current parsed intent (dict)
        validation_errors: List of validation error messages
        available_tables: List of available table metadata
        generated_sql: The SQL that failed validation
        
    Returns:
        Formatted prompt string
    """
    
    # Format tables for context
    tables_context = []
    for table in available_tables:
        cols = [f"{c.name} ({c.type})" for c in table.columns[:15]]  # First 15 columns
        if len(table.columns) > 15:
            cols.append(f"... and {len(table.columns) - 15} more columns")
        tables_context.append(f"  - {table.schema_name}.{table.table_name}: {', '.join(cols)}")
    
    tables_str = "\n".join(tables_context)
    
    prompt = f"""# Intent Refinement Request

## Original User Query
"{original_query}"

## Current Parsed Intent
{format_intent_for_display(current_intent)}

## Generated SQL (Failed Validation)
```sql
{generated_sql}
```

## Validation Errors
{format_errors(validation_errors)}

## Available Tables and Columns
{tables_str}

## Your Task

Analyze whether the validation errors indicate that the **intent itself has wrong column names**.

**IMPORTANT**: 99% of the time, the intent is correct and only SQL generation has issues.

Issues that DON'T require intent refinement (return intent unchanged):
1. Column not in SELECT clause (GROUP BY issue) → SQL generator's fault
2. Missing table aliases → SQL generator's fault  
3. Incorrect JOIN syntax → SQL generator's fault
4. Wrong aggregation function syntax → SQL generator's fault
5. Invented WHERE clauses or filters → SQL generator's fault
6. Wrong table being used → SQL generator's fault

Issues that DO require intent refinement (rare):
1. Dimension name has typo: intent says "Tem" but column is "Team"
2. Metric name doesn't match any column and user meant something else

**CRITICAL RULES:**
- If current intent has filters=None, refined intent MUST also have filters=None
- NEVER add new filters, NEVER add joins
- Filter values must be simple strings/numbers, NEVER SQL queries or subqueries

## Decision

Based on the errors above, should the intent be refined?

**99% of the time the answer is NO** - return the EXACT same intent JSON.
Only refine if dimension/metric column names are clearly wrong.

## Output Format (JSON)

**CRITICAL**: 
- filters and aggregations must be dictionaries (objects), NOT arrays!
- If no filters exist, use null (not an empty dict, not an array)
- Filter values must be simple: strings, numbers, booleans - NEVER SQL queries

{{
  "metrics": ["list of metrics to compute"],
  "dimensions": ["list of dimensions to group/filter by"],
  "filters": null,
  "aggregations": {{"metric_name": "SUM", "another_metric": "AVG"}},
  "time_dimension": null,
  "chart_hint": null
}}

Example with filters:
{{
  "metrics": ["total_sales"],
  "dimensions": ["region"],
  "filters": {{"status": "active", "year": "2024"}},
  "aggregations": {{"total_sales": "SUM"}},
  "time_dimension": null,
  "chart_hint": null
}}

Respond ONLY with the JSON, no explanations outside the JSON structure."""
    
    return prompt


def format_intent_for_display(intent: dict) -> str:
    """Format intent dict for readable display"""
    lines = []
    lines.append(f"Metrics: {intent.get('metrics', [])}")
    lines.append(f"Dimensions: {intent.get('dimensions', [])}")
    lines.append(f"Filters: {intent.get('filters', [])}")
    lines.append(f"Aggregations: {intent.get('aggregations', [])}")
    if intent.get('time_range'):
        lines.append(f"Time Range: {intent.get('time_range')}")
    if intent.get('ordering'):
        lines.append(f"Ordering: {intent.get('ordering')}")
    if intent.get('limit'):
        lines.append(f"Limit: {intent.get('limit')}")
    return "\n".join(lines)


def format_errors(errors: list) -> str:
    """Format error list for display"""
    if not errors:
        return "(No errors)"
    return "\n".join(f"  {i+1}. {err}" for i, err in enumerate(errors))

