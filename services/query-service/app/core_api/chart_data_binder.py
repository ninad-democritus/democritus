"""
Chart data binding utilities.
Populates chart templates with fresh data while preserving structure.
"""
from typing import List, Dict, Any
import logging
import copy
from decimal import Decimal

from .chart_styling_engine import get_styling_engine

logger = logging.getLogger(__name__)


def bind_data_to_chart(
    chart_config: dict,
    data: List[Dict[str, Any]],
    chart_type: str
) -> dict:
    """
    Bind data to chart configuration based on chart type.
    
    Args:
        chart_config: Template config (structure without data)
        data: Query results as list of dicts
        chart_type: Type of chart (bar, line, pie, etc.)
    
    Returns:
        Complete chart config with data populated
    """
    if not data:
        logger.warning("No data provided for chart binding")
        return chart_config
    
    # Dispatch to chart-type specific binder
    binders = {
        "bar": bind_bar_chart,
        "line": bind_line_chart,
        "pie": bind_pie_chart,
        "scatter": bind_scatter_chart,
    }
    
    binder = binders.get(chart_type, bind_generic_chart)
    return binder(chart_config, data)


def bind_bar_chart(config: dict, data: List[Dict]) -> dict:
    """
    Bind data to bar chart.
    Assumes structure: xAxis = categories, series = values
    """
    result = copy.deepcopy(config)
    echarts = result.get("echartsOptions", {})
    
    if not data:
        logger.warning("No data provided for bar chart binding")
        return result
    
    # Infer data structure
    columns = list(data[0].keys())
    logger.info(f"Bar chart data columns: {columns}")
    
    # Separate category columns (strings) from value columns (numbers)
    category_col = None
    value_cols = []
    
    for col in columns:
        sample_val = data[0][col]
        if isinstance(sample_val, str):
            category_col = col
        elif isinstance(sample_val, (int, float, Decimal)):
            value_cols.append(col)
    
    logger.info(f"Identified category_col={category_col}, value_cols={value_cols}")
    
    # Populate xAxis data (categories)
    if category_col and "xAxis" in echarts:
        categories = [row[category_col] for row in data]
        if isinstance(echarts["xAxis"], dict):
            echarts["xAxis"]["data"] = categories
        elif isinstance(echarts["xAxis"], list):
            echarts["xAxis"][0]["data"] = categories
        logger.info(f"Set xAxis categories: {categories}")
    
    # Populate series data with PLAIN values (styling comes next)
    if "series" in echarts and value_cols:
        for i, series in enumerate(echarts["series"]):
            if i < len(value_cols):
                col = value_cols[i]
                # Use plain values - styling engine will convert to objects if needed
                series["data"] = [
                    float(row[col]) if isinstance(row[col], Decimal) else row[col]
                    for row in data
                ]
                
                # Update series name if needed
                if "name" not in series or not series["name"]:
                    series["name"] = col.replace("_", " ").title()
                
                logger.info(f"Bound series {i} ({series['name']}): {len(series['data'])} points")
    
    # Apply intelligent styling based on current data structure
    styling_engine = get_styling_engine()
    styled_echarts = styling_engine.style_bar_chart(echarts, data)
    
    # CRITICAL: Update result with styled echarts
    result["echartsOptions"] = styled_echarts
    logger.info("✓ Updated result with styled echarts config")
    
    logger.info(f"Completed bar chart binding: {len(data)} rows, {len(value_cols)} series")
    return result


def bind_line_chart(config: dict, data: List[Dict]) -> dict:
    """
    Bind data to line chart.
    Similar structure to bar chart.
    """
    # Line charts have same data structure as bar charts
    return bind_bar_chart(config, data)


def bind_pie_chart(config: dict, data: List[Dict]) -> dict:
    """
    Bind data to pie chart.
    Format: [{name: "Category", value: 123}, ...]
    """
    result = copy.deepcopy(config)
    echarts = result.get("echartsOptions", {})
    
    if not data:
        logger.warning("No data provided for pie chart binding")
        return result
    
    columns = list(data[0].keys())
    logger.info(f"Pie chart data columns: {columns}")
    logger.info(f"Sample data row: {data[0]}")
    
    # Find name and value columns
    name_col = None
    value_col = None
    
    for col in columns:
        sample_val = data[0][col]
        if isinstance(sample_val, str) and not name_col:
            name_col = col
            logger.info(f"Identified name column: {col}")
        elif isinstance(sample_val, (int, float, Decimal)) and not value_col:
            value_col = col
            logger.info(f"Identified value column: {col}")
    
    if not name_col or not value_col:
        logger.error(f"Could not identify name/value columns. name_col={name_col}, value_col={value_col}")
        return result
    
    # Populate series data (pie format) - WITHOUT colors yet
    if "series" in echarts:
        pie_data = [
            {
                "name": row[name_col],
                "value": float(row[value_col]) if isinstance(row[value_col], Decimal) else row[value_col]
            }
            for row in data
        ]
        
        logger.info(f"Created pie data with {len(pie_data)} slices")
        logger.info(f"Pie slice names: {[item['name'] for item in pie_data]}")
        
        echarts["series"][0]["data"] = pie_data
        
        # Apply intelligent styling (colors and legend) based on current data
        styling_engine = get_styling_engine()
        styled_echarts = styling_engine.style_pie_chart(echarts, data)
        
        # CRITICAL: Update result with styled echarts
        result["echartsOptions"] = styled_echarts
        logger.info("✓ Updated result with styled echarts config")
    else:
        logger.error("No series found in echarts config")
    
    logger.info(f"Completed pie chart binding: {len(data)} rows, name_col={name_col}, value_col={value_col}")
    return result


def bind_scatter_chart(config: dict, data: List[Dict]) -> dict:
    """
    Bind data to scatter chart.
    Scatter needs pairs of values [x, y]
    """
    result = copy.deepcopy(config)
    echarts = result.get("echartsOptions", {})
    
    if not data:
        logger.warning("No data provided for scatter chart binding")
        return result
    
    columns = list(data[0].keys())
    numeric_cols = [
        col for col in columns
        if isinstance(data[0][col], (int, float, Decimal))
    ]
    
    logger.info(f"Scatter chart numeric columns: {numeric_cols}")
    
    # Scatter needs pairs of values [x, y]
    if "series" in echarts and len(numeric_cols) >= 2:
        x_col, y_col = numeric_cols[0], numeric_cols[1]
        
        scatter_data = [
            [
                float(row[x_col]) if isinstance(row[x_col], Decimal) else row[x_col],
                float(row[y_col]) if isinstance(row[y_col], Decimal) else row[y_col]
            ]
            for row in data
        ]
        
        echarts["series"][0]["data"] = scatter_data
        logger.info(f"Bound scatter data: {len(scatter_data)} points")
        
        # Apply styling
        styling_engine = get_styling_engine()
        styled_echarts = styling_engine.style_scatter_chart(echarts, data)
        
        # CRITICAL: Update result with styled echarts
        result["echartsOptions"] = styled_echarts
        logger.info("✓ Updated result with styled echarts config")
    
    logger.info(f"Completed scatter chart binding: {len(data)} rows")
    return result


def bind_generic_chart(config: dict, data: List[Dict]) -> dict:
    """
    Generic fallback binding.
    Tries to intelligently map data to any chart structure.
    """
    logger.warning("Using generic chart binder - chart type not recognized")
    # Default to bar chart logic
    return bind_bar_chart(config, data)

