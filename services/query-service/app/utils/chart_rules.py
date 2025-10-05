"""Rule-based chart type recommendation"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def recommend_chart_type_by_rules(
    data: List[Dict[str, Any]],
    intent: dict,
    user_constraint: str = None
) -> Dict[str, Any]:
    """
    Recommend chart type using rule-based heuristics.
    
    This is used as a fallback or fast path before LLM recommendation.
    
    Args:
        data: Query result data
        intent: Parsed query intent
        user_constraint: Optional user-specified chart type
        
    Returns:
        Recommendation dict with chart_type, confidence, reasoning, size
    """
    # If user specified a chart type, use it
    if user_constraint:
        return {
            "chart_type": user_constraint,
            "confidence": 1.0,
            "reasoning": f"User specified {user_constraint} chart",
            "size": recommend_size(user_constraint, len(data))
        }
    
    # No data case
    if not data or len(data) == 0:
        return {
            "chart_type": "table",
            "confidence": 0.5,
            "reasoning": "No data returned, defaulting to table",
            "size": {"cols": 12, "rows": 6}
        }
    
    row_count = len(data)
    columns = list(data[0].keys()) if data else []
    num_columns = len(columns)
    
    # Analyze column types
    numeric_cols = []
    categorical_cols = []
    time_cols = []
    
    for col in columns:
        sample_val = data[0].get(col)
        
        if isinstance(sample_val, (int, float)):
            numeric_cols.append(col)
        elif isinstance(sample_val, str):
            # Check if it looks like a date
            if any(indicator in str(sample_val).lower() 
                   for indicator in ['2024', '2023', 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                    'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'q1', 'q2', 'q3', 'q4']):
                time_cols.append(col)
            else:
                categorical_cols.append(col)
    
    has_time = len(time_cols) > 0 or intent.get("time_dimension") is not None
    
    # Check chart hint from NL parsing
    chart_hint = intent.get("chart_hint")
    
    # Rule 1: Single value → KPI card
    if row_count == 1 and num_columns == 1:
        return {
            "chart_type": "kpi",
            "confidence": 0.95,
            "reasoning": "Single metric value best displayed as KPI card",
            "size": {"cols": 6, "rows": 4}
        }
    
    # Rule 2: Time series → Line chart
    if has_time and len(numeric_cols) >= 1:
        return {
            "chart_type": "line",
            "confidence": 0.9,
            "reasoning": "Time series data best visualized with line chart",
            "size": recommend_size("line", row_count)
        }
    
    # Rule 3: Chart hint from query
    if chart_hint in ["line", "bar", "pie", "scatter", "area", "table"]:
        return {
            "chart_type": chart_hint,
            "confidence": 0.85,
            "reasoning": f"Query suggests {chart_hint} visualization",
            "size": recommend_size(chart_hint, row_count)
        }
    
    # Rule 4: One categorical + one numeric → Bar chart
    if len(categorical_cols) == 1 and len(numeric_cols) >= 1:
        return {
            "chart_type": "bar",
            "confidence": 0.85,
            "reasoning": "Categorical comparison best shown with bar chart",
            "size": recommend_size("bar", row_count)
        }
    
    # Rule 5: Parts of whole (few categories) → Pie chart
    if len(categorical_cols) == 1 and len(numeric_cols) == 1 and row_count <= 8:
        return {
            "chart_type": "pie",
            "confidence": 0.75,
            "reasoning": "Few categories showing parts of whole, using pie chart",
            "size": {"cols": 8, "rows": 6}
        }
    
    # Rule 6: Two numeric columns → Scatter plot
    if len(numeric_cols) >= 2 and len(categorical_cols) == 0:
        return {
            "chart_type": "scatter",
            "confidence": 0.8,
            "reasoning": "Two numeric dimensions suggest correlation analysis",
            "size": {"cols": 12, "rows": 8}
        }
    
    # Rule 7: Many columns or large dataset → Table
    if num_columns > 5 or row_count > 100:
        return {
            "chart_type": "table",
            "confidence": 0.7,
            "reasoning": "Many columns or large dataset, using table",
            "size": {"cols": 16, "rows": 8}
        }
    
    # Default: Bar chart for categorical data
    return {
        "chart_type": "bar",
        "confidence": 0.6,
        "reasoning": "Default to bar chart for general categorical comparison",
        "size": recommend_size("bar", row_count)
    }


def recommend_size(chart_type: str, data_points: int) -> Dict[str, int]:
    """
    Recommend chart size based on type and data points.
    
    Args:
        chart_type: Chart type
        data_points: Number of data points
        
    Returns:
        Size dict with cols and rows
    """
    if chart_type == "kpi":
        return {"cols": 6, "rows": 4}
    
    if chart_type == "pie":
        return {"cols": 8, "rows": 6}
    
    if chart_type == "table":
        if data_points <= 10:
            return {"cols": 12, "rows": 6}
        elif data_points <= 50:
            return {"cols": 16, "rows": 8}
        else:
            return {"cols": 24, "rows": 8}
    
    # For bar, line, area, scatter
    if data_points <= 5:
        return {"cols": 8, "rows": 6}
    elif data_points <= 12:
        return {"cols": 12, "rows": 6}
    elif data_points <= 30:
        return {"cols": 16, "rows": 8}
    else:
        return {"cols": 24, "rows": 8}


def generate_chart_title(
    intent: dict,
    chart_type: str,
    data: List[Dict[str, Any]]
) -> str:
    """
    Generate a descriptive chart title.
    
    Args:
        intent: Query intent
        chart_type: Chart type
        data: Query result data
        
    Returns:
        Chart title string
    """
    metrics = intent.get("metrics", [])
    dimensions = intent.get("dimensions", [])
    filters = intent.get("filters") or {}
    
    # Build title parts
    parts = []
    
    # Add metrics
    if metrics:
        metric_str = ", ".join(metrics).title()
        parts.append(metric_str)
    
    # Add dimension
    if dimensions:
        dim_str = " by " + ", ".join(dimensions).title()
        parts.append(dim_str)
    
    # Add time filter
    time_filters = []
    if filters:
        for key, value in filters.items():
            if any(t in key.lower() for t in ['year', 'quarter', 'month', 'date', 'time']):
                time_filters.append(f"{key.title()} {value}")
    
    if time_filters:
        parts.append(" - " + ", ".join(time_filters))
    
    if parts:
        return "".join(parts)
    
    # Fallback
    return f"{chart_type.title()} Chart"

