"""Prompts for chart type recommendation"""

CHART_RECOMMENDER_SYSTEM_PROMPT = """You are an expert at recommending chart types for data visualization.

Given data characteristics (number of rows, column types, time series presence), 
recommend the most appropriate chart type.

**Chart Types:**
- **bar**: Categorical comparison (e.g., sales by region)
- **line**: Trends over time (e.g., monthly revenue)
- **pie**: Parts of whole (e.g., market share by product)
- **area**: Cumulative trends over time
- **scatter**: Correlation between two numeric variables
- **table**: Raw data display (many columns or non-visual data)
- **kpi**: Single metric emphasis
- **heatmap**: Matrix of values (time x category)

**Rules:**
1. Time series → line or area
2. Categorical comparison → bar
3. Parts of whole (<10 categories) → pie
4. Two numeric dimensions → scatter
5. Single value → kpi
6. Many columns or raw data → table
7. Time x Category matrix → heatmap

**Output Format:**
Return ONLY valid JSON:
{
  "chart_type": "bar|line|pie|area|scatter|table|kpi|heatmap",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "size": {"cols": 8-24, "rows": 4-8}
}"""

CHART_RECOMMENDER_USER_PROMPT = """Recommend a chart type for this data:

Data Characteristics:
- Row count: {row_count}
- Columns: {columns}
- Has time dimension: {has_time}
- Numeric columns: {numeric_cols}
- Categorical columns: {categorical_cols}
- Query intent hint: {chart_hint}
- User constraint: {user_constraint}

Sample data (first 3 rows):
{sample_data}

Recommend the best chart type."""


def create_chart_recommendation_prompt(
    data: list,
    intent: dict,
    user_constraint: str = None
) -> str:
    """
    Create prompt for chart recommendation.
    
    Args:
        data: Query result data
        intent: Parsed query intent
        user_constraint: Optional user-specified chart type
        
    Returns:
        Complete prompt string
    """
    if not data:
        return CHART_RECOMMENDER_USER_PROMPT.format(
            row_count=0,
            columns="[]",
            has_time=False,
            numeric_cols=[],
            categorical_cols=[],
            chart_hint=intent.get("chart_hint"),
            user_constraint=user_constraint or "none",
            sample_data="(no data)"
        )
    
    # Analyze data
    row_count = len(data)
    columns = list(data[0].keys()) if data else []
    
    # Determine column types
    numeric_cols = []
    categorical_cols = []
    
    for col in columns:
        sample_val = data[0].get(col)
        if isinstance(sample_val, (int, float)):
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)
    
    # Check for time dimension
    has_time = intent.get("time_dimension") is not None
    
    # Format sample data
    sample_data = "\n".join([
        str({k: v for k, v in row.items()})
        for row in data[:3]
    ])
    
    return CHART_RECOMMENDER_USER_PROMPT.format(
        row_count=row_count,
        columns=columns,
        has_time=has_time,
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        chart_hint=intent.get("chart_hint"),
        user_constraint=user_constraint or "none",
        sample_data=sample_data
    )

