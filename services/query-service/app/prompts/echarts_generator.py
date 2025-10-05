"""Prompts for ECharts configuration generation"""
import logging
from .chart_types.pie_chart import PIE_CHART_SYSTEM_PROMPT, PIE_CHART_USER_PROMPT
from .chart_types.bar_chart import BAR_CHART_SYSTEM_PROMPT, BAR_CHART_USER_PROMPT
from .chart_types.line_chart import LINE_CHART_SYSTEM_PROMPT, LINE_CHART_USER_PROMPT

logger = logging.getLogger(__name__)


def should_limit_data(data: list, chart_type: str) -> tuple[bool, int]:
    """
    Determine if data should be limited based on chart type and data size.
    Only limit when rendering would be genuinely heavy.
    
    Args:
        data: Query result data
        chart_type: Type of chart to render
        
    Returns:
        Tuple of (should_limit, max_rows)
    """
    if not data:
        return False, 0
    
    row_count = len(data)
    
    # Define limits based on chart type
    # These are generous limits - only cut if truly necessary
    chart_limits = {
        'pie': 50,          # Pie charts get cluttered with too many slices
        'radar': 30,        # Radar charts have limited space
        'funnel': 40,       # Funnel charts are vertical
        'gauge': 1,         # Gauge typically shows single value
        'sankey': 100,      # Sankey can handle more nodes
        'treemap': 200,     # Treemaps can show many items
        'sunburst': 200,    # Sunburst can show hierarchies
        'bar': 100,         # Bar charts get long with many items
        'line': 500,        # Line charts can handle many points
        'scatter': 1000,    # Scatter plots can show many points
        'heatmap': 500,     # Heatmaps can show many cells
        'candlestick': 500, # Financial charts need many data points
    }
    
    # Get limit for this chart type (default to 100 if not specified)
    limit = chart_limits.get(chart_type.lower(), 100)
    
    should_limit = row_count > limit
    
    if should_limit:
        logger.info(f"Data will be limited from {row_count} to {limit} rows for {chart_type} chart")
    else:
        logger.info(f"Data size ({row_count} rows) is acceptable for {chart_type} chart, no limiting needed")
    
    return should_limit, limit


def limit_data(data: list, chart_type: str) -> list:
    """
    Intelligently limit data if needed for chart rendering.
    Sorts by numeric values (descending) to get top results when limiting.
    
    Args:
        data: Query result data
        chart_type: Type of chart
        
    Returns:
        Limited data (or original if no limiting needed), sorted by highest values
    """
    should_limit, limit = should_limit_data(data, chart_type)
    
    if not data or not isinstance(data[0], dict):
        return data
    
    # If not limiting, return data as-is (no need to sort)
    if not should_limit:
        return data
    
    # Need to limit - sort by numeric columns (descending) to get top results
    from decimal import Decimal
    
    # Find numeric columns
    first_row = data[0]
    numeric_cols = []
    for col, val in first_row.items():
        if isinstance(val, (int, float, Decimal)):
            numeric_cols.append(col)
    
    # Sort by first numeric column in descending order (highest values first)
    if numeric_cols:
        sort_col = numeric_cols[0]
        try:
            sorted_data = sorted(data, key=lambda row: float(row.get(sort_col, 0)), reverse=True)
            logger.info(f"Sorted data by '{sort_col}' (descending) to get top results")
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to sort data by '{sort_col}': {e}")
            sorted_data = data
    else:
        # No numeric columns to sort by, just use original order
        sorted_data = data
    
    # Take top N rows after sorting
    limited_data = sorted_data[:limit]
    
    logger.info(f"Limited data from {len(data)} to {len(limited_data)} rows (after sorting)")
    
    return limited_data


# NOTE: Chart-specific prompts are now in chart_types/ subdirectory
# This provides cleaner, focused prompts for each chart type


def get_prompts_for_chart_type(chart_type: str) -> tuple[str, str]:
    """
    Get the appropriate system and user prompts for the given chart type.
    
    Args:
        chart_type: Type of chart (pie, bar, line, etc.)
        
    Returns:
        Tuple of (system_prompt, user_prompt_template)
    """
    chart_type_lower = chart_type.lower()
    
    if chart_type_lower == 'pie':
        return PIE_CHART_SYSTEM_PROMPT, PIE_CHART_USER_PROMPT
    elif chart_type_lower == 'bar':
        return BAR_CHART_SYSTEM_PROMPT, BAR_CHART_USER_PROMPT
    elif chart_type_lower == 'line':
        return LINE_CHART_SYSTEM_PROMPT, LINE_CHART_USER_PROMPT
    else:
        # Fallback to bar chart prompts for unknown types
        logger.warning(f"Unknown chart type '{chart_type}', using bar chart prompts as fallback")
        return BAR_CHART_SYSTEM_PROMPT, BAR_CHART_USER_PROMPT


def create_echarts_prompt(
    chart_type: str,
    data: list,
    title: str,
    size: dict,
    intent: dict = None
) -> tuple[str, str]:
    """
    Create prompt for ECharts config generation with proper data analysis.
    Returns both system and user prompts specific to chart type.
    
    Args:
        chart_type: Type of chart to generate
        data: Query result data (should already be limited by caller)
        title: Chart title
        size: Chart size (cols, rows)
        intent: Optional query intent for context
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    import json
    
    # Get chart-specific prompts
    system_prompt, user_prompt_template = get_prompts_for_chart_type(chart_type)
    
    # Data should already be limited by the caller
    # No need to limit again here
    total_rows = len(data)
    
    # Analyze column structure from first row
    categorical_cols = []
    numeric_cols = []
    column_info = {}
    
    if data and len(data) > 0 and isinstance(data[0], dict):
        from decimal import Decimal
        
        for col, val in data[0].items():
            # Check for numeric types (including Decimal from database)
            if isinstance(val, (int, float, Decimal)):
                numeric_cols.append(col)
                column_info[col] = "numeric"
            elif isinstance(val, str):
                categorical_cols.append(col)
                # Try to detect if it's a date/time
                if any(char in str(val).lower() for char in ['2024', '2023', '2025', 'jan', 'feb', 'mar', 'apr', 'may', 'jun']):
                    column_info[col] = "time"
                else:
                    column_info[col] = "categorical"
            else:
                column_info[col] = "unknown"
    
    # Create data structure summary
    data_structure_summary = {
        "columns": column_info,
        "row_count": total_rows,
        "first_row_example": data[0] if data else {}
    }
    
    # For LLM efficiency, only send a small sample (5 rows max)
    # The LLM only needs to understand the structure, not process all data
    sample_size = min(5, len(data))
    data_sample = data[:sample_size] if data else []
    
    # Convert Decimals to floats for JSON serialization
    from ..utils.json_encoder import convert_decimals_to_float
    data_sample_converted = convert_decimals_to_float(data_sample)
    
    # Truncate long string values to reduce prompt size
    for row in data_sample_converted:
        for key, value in row.items():
            if isinstance(value, str) and len(value) > 50:
                row[key] = value[:47] + "..."
    
    # Format sample data compactly (no indentation)
    data_str = json.dumps(data_sample_converted, separators=(',', ':'))
    
    # Log data reduction for transparency
    logger.info(f"Sending {sample_size} sample rows to LLM (from {len(data)} total) - prompt size: {len(data_str)} chars")
    
    # Format column lists for prompt
    categorical_str = ", ".join(categorical_cols) if categorical_cols else "None"
    numeric_str = ", ".join(numeric_cols) if numeric_cols else "None"
    
    user_prompt = user_prompt_template.format(
        title=title,
        data=data_str,
        categorical_cols=categorical_str,
        numeric_cols=numeric_str,
        total_rows=total_rows
    )
    
    return system_prompt, user_prompt


def validate_and_fix_echarts_config(
    config: dict,
    data: list,
    chart_type: str
) -> tuple[bool, dict, list[str]]:
    """
    Validate and attempt to fix ECharts configuration.
    
    Args:
        config: Generated ECharts config
        data: Original data
        chart_type: Expected chart type
        
    Returns:
        Tuple of (is_valid, fixed_config, warnings)
    """
    import json
    
    warnings = []
    fixed_config = config.copy()
    
    # Ensure global color array exists (critical for multi-color charts)
    theme_colors = ["#14b8a6", "#f97316", "#0ea5e9", "#f43f5e", "#a855f7", 
                    "#10b981", "#8b5cf6", "#ec4899"]
    if "color" not in fixed_config:
        warnings.append("Adding global color array for multi-color support")
        fixed_config["color"] = theme_colors
    
    # Check for series
    if "series" not in fixed_config or not isinstance(fixed_config["series"], list):
        warnings.append("Missing or invalid 'series' field - adding default")
        fixed_config["series"] = []
    
    if len(fixed_config["series"]) == 0:
        warnings.append("Empty series array - attempting to reconstruct from data")
        fixed_config["series"] = reconstruct_series_from_data(data, chart_type)
    
    # Validate and fix each series (but don't handle colors yet - that comes after reconstruction)
    for i, series in enumerate(fixed_config["series"]):
        if not isinstance(series, dict):
            warnings.append(f"Series {i} is not a dict - skipping")
            continue
        
        # Check for required fields
        if "type" not in series:
            warnings.append(f"Series {i} missing 'type' - setting to {chart_type}")
            series["type"] = chart_type
        
        if "data" not in series or not isinstance(series["data"], list):
            warnings.append(f"Series {i} missing or invalid 'data' - attempting to reconstruct")
            series["data"] = []
        
        # Fix nested array structures (common LLM mistake)
        if series["data"] and isinstance(series["data"][0], list):
            warnings.append(f"Series {i} has nested arrays - flattening")
            # For bar/line charts, we need just the numbers
            if chart_type in ['bar', 'line', 'scatter']:
                # Take the first numeric value from each nested array
                flat_data = []
                for item in series["data"]:
                    if isinstance(item, list):
                        # Find first number in the list
                        for val in item:
                            if isinstance(val, (int, float)):
                                flat_data.append(val)
                                break
                    elif isinstance(val, (int, float)):
                        flat_data.append(item)
                series["data"] = flat_data
        
        # Check if series data length matches the expected data length
        if chart_type in ['bar', 'line'] and series.get("data") and len(series["data"]) != len(data):
            warnings.append(f"Series {i} has {len(series['data'])} points but data has {len(data)} rows - will need full reconstruction")
    
    # Validate series data quality and structure
    should_reconstruct_series = False
    
    # PIE CHARTS: Must have exactly ONE series with object data
    if chart_type.lower() == 'pie':
        if len(fixed_config["series"]) != 1:
            warnings.append(f"Pie chart has {len(fixed_config['series'])} series, must have exactly 1")
            should_reconstruct_series = True
        elif len(fixed_config["series"]) == 1:
            series_data = fixed_config["series"][0].get("data", [])
            # Check if data is array of objects with {value, name}
            if series_data and isinstance(series_data[0], (int, float)):
                # Data is array of numbers, not objects - WRONG for pie
                warnings.append("Pie chart series.data has numbers instead of objects {value, name}")
                should_reconstruct_series = True
            elif not series_data or len(series_data) != len(data):
                warnings.append(f"Pie chart series.data has {len(series_data)} items but data has {len(data)} rows")
                should_reconstruct_series = True
    
    # BAR/LINE CHARTS: Validate data count
    elif chart_type in ['bar', 'line']:
        # Check if any series has wrong data count
        for i, s in enumerate(fixed_config["series"]):
            if not isinstance(s, dict):
                continue
            
            series_data = s.get("data", [])
            
            # Check 1: Wrong count
            if len(series_data) != len(data):
                warnings.append(f"Series {i} has {len(series_data)} points but data has {len(data)} rows")
                should_reconstruct_series = True
                break
            
            # Check 2: Placeholder or unrealistic values
            if series_data and len(series_data) > 0:
                # Check if all values are suspiciously round numbers (multiples of 10)
                all_round = all(isinstance(v, (int, float)) and v % 10 == 0 for v in series_data)
                all_small_ints = all(isinstance(v, int) and 0 < v < 1000 for v in series_data)
                
                if all_round and all_small_ints and len(series_data) < 10:
                    # This looks like placeholder data from the LLM prompt examples
                    warnings.append(f"Series {i} contains suspiciously simple values - likely placeholder")
                    should_reconstruct_series = True
                    break
    
    if should_reconstruct_series:
        warnings.append("Reconstructing all series from data")
        fixed_config["series"] = reconstruct_series_from_data(data, chart_type)
    
    # Ensure xAxis exists and has data for bar/line charts
    should_reconstruct_xaxis = False
    if chart_type in ['bar', 'line']:
        if "xAxis" not in fixed_config:
            warnings.append("Missing xAxis - reconstructing from data")
            should_reconstruct_xaxis = True
        elif not isinstance(fixed_config["xAxis"], dict):
            warnings.append("Invalid xAxis type - reconstructing from data")
            should_reconstruct_xaxis = True
        elif "data" not in fixed_config["xAxis"] or not fixed_config["xAxis"]["data"]:
            warnings.append("xAxis has no data - reconstructing from data")
            should_reconstruct_xaxis = True
        elif len(fixed_config["xAxis"]["data"]) != len(data):
            # xAxis category count doesn't match data row count
            warnings.append(f"xAxis has {len(fixed_config['xAxis']['data'])} categories but data has {len(data)} rows")
            should_reconstruct_xaxis = True
        else:
            # CRITICAL: Validate that xAxis data actually matches real data values
            # Not just the count, but the actual values!
            llm_categories = fixed_config["xAxis"]["data"]
            real_categories = extract_categories_from_data(data)
            
            if real_categories and llm_categories != real_categories:
                # LLM generated placeholder or incorrect categories
                warnings.append(f"xAxis categories don't match real data values (e.g., {llm_categories[:2]} vs {real_categories[:2]})")
                should_reconstruct_xaxis = True
        
        # Reconstruct or fix xAxis (only for bar/line charts)
        if should_reconstruct_xaxis:
            logger.info("Forcing xAxis reconstruction from real data to ensure accuracy")
            fixed_config["xAxis"] = reconstruct_xaxis_from_data(data)
            warnings.append("Replaced xAxis with real data values")
        else:
            # xAxis data is valid, but ensure it has proper label formatting
            if "axisLabel" not in fixed_config["xAxis"]:
                # Add intelligent label configuration
                categories = fixed_config["xAxis"].get("data", [])
                max_label_length = max(len(str(cat)) for cat in categories) if categories else 0
                num_categories = len(categories)
                should_rotate = num_categories > 10 or max_label_length > 15
                
                fixed_config["xAxis"]["axisLabel"] = {
                    "rotate": 45 if should_rotate else 0,
                    "interval": "auto"
                }
                warnings.append("Added intelligent axis label configuration")
            elif "interval" not in fixed_config["xAxis"]["axisLabel"]:
                # Ensure interval is set to auto to prevent overlap
                fixed_config["xAxis"]["axisLabel"]["interval"] = "auto"
                warnings.append("Added interval: auto to axis labels")
    
    # Ensure yAxis exists for bar/line charts
    if chart_type in ['bar', 'line'] and "yAxis" not in fixed_config:
        warnings.append("Missing yAxis - adding default")
        fixed_config["yAxis"] = {"type": "value"}
    
    # Ensure tooltip exists
    if "tooltip" not in fixed_config:
        warnings.append("Missing tooltip - adding default")
        fixed_config["tooltip"] = {
            "trigger": "item" if chart_type == "pie" else "axis"
        }
    
    # Ensure grid exists for bar/line charts
    if chart_type in ['bar', 'line']:
        if "grid" not in fixed_config:
            warnings.append("Missing grid - adding default")
            fixed_config["grid"] = {
                "left": "3%",
                "right": "4%",
                "bottom": "3%",
                "containLabel": True
            }
        
        # Adjust bottom margin if labels are rotated to prevent cutoff
        if fixed_config.get("xAxis", {}).get("axisLabel", {}).get("rotate", 0) > 0:
            # Need more bottom space for rotated labels
            if fixed_config["grid"].get("bottom", "3%") == "3%":
                fixed_config["grid"]["bottom"] = "15%"
                warnings.append("Adjusted grid bottom margin for rotated labels")
    
    # Handle legend based on chart type and series count
    series_count = len(fixed_config["series"])
    
    if chart_type.lower() in ['bar', 'line']:
        # For bar/line charts with single series, remove legend (each bar has different color)
        if series_count == 1:
            if "legend" in fixed_config:
                del fixed_config["legend"]
                warnings.append("Removed legend for single-series bar/line chart with per-bar colors")
        # For multiple series, ensure legend exists
        elif series_count > 1 and "legend" not in fixed_config:
            warnings.append("Adding legend for multiple series")
            fixed_config["legend"] = {"show": True, "type": "scroll"}
    elif chart_type.lower() == 'pie':
        # Pie charts always need legend
        if "legend" not in fixed_config:
            warnings.append("Adding legend for pie chart")
            fixed_config["legend"] = {"orient": "vertical", "left": "left"}
    
    # CRITICAL: Handle itemStyle.color based on chart type and series count (AFTER all reconstructions)
    # This must happen LAST to ensure reconstructed series also get correct color treatment
    series_count = len(fixed_config["series"])
    for i, series in enumerate(fixed_config["series"]):
        if not isinstance(series, dict):
            continue
        
        # PIE CHARTS: NEVER use itemStyle.color (global color array applies to each slice)
        if chart_type.lower() == 'pie':
            if "itemStyle" in series and "color" in series["itemStyle"]:
                del series["itemStyle"]["color"]
                if not series["itemStyle"]:  # Remove empty itemStyle dict
                    del series["itemStyle"]
                warnings.append(f"Removed itemStyle.color from pie chart to enable multi-color slices")
        # BAR/LINE: Single series no color, multiple series need color
        elif series_count == 1:
            # Single series: Remove itemStyle.color to enable multi-color bars
            if "itemStyle" in series and "color" in series["itemStyle"]:
                del series["itemStyle"]["color"]
                if not series["itemStyle"]:  # Remove empty itemStyle dict
                    del series["itemStyle"]
                warnings.append(f"Removed itemStyle.color from single series to enable multi-color bars")
        else:
            # Multiple series: Ensure each has itemStyle.color for consistent coloring
            if "itemStyle" not in series:
                series["itemStyle"] = {}
            if "color" not in series["itemStyle"]:
                series["itemStyle"]["color"] = theme_colors[i % len(theme_colors)]
                warnings.append(f"Added itemStyle.color to series {i} for multi-series consistency")
    
    # Validate we have data in series
    has_data = any(
        isinstance(s, dict) and "data" in s and len(s["data"]) > 0
        for s in fixed_config["series"]
    )
    
    is_valid = has_data and len(fixed_config["series"]) > 0
    
    if warnings:
        logger.warning(f"ECharts config had {len(warnings)} issues that were fixed")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    
    return is_valid, fixed_config, warnings


def reconstruct_series_from_data(data: list, chart_type: str) -> list:
    """
    Reconstruct series from raw data when LLM fails to generate it properly.
    
    PIE CHARTS: ONE series with data = [{value, name}, ...]
    BAR/LINE: One series per numeric column with data = [numbers]
    
    COLOR LOGIC:
    - Pie charts: NEVER use itemStyle.color (global color array applies to each slice)
    - Bar/Line single series: No itemStyle.color (global color array applies to each bar)
    - Bar/Line multiple series: Each series gets itemStyle.color for consistent coloring
    
    Args:
        data: Query result data
        chart_type: Chart type
        
    Returns:
        List of series objects
    """
    if not data or not isinstance(data[0], dict):
        return []
    
    # Identify categorical and numeric columns
    from decimal import Decimal
    
    first_row = data[0]
    categorical_cols = []
    numeric_cols = []
    
    for col, val in first_row.items():
        # Handle Decimal from database queries
        if isinstance(val, (int, float, Decimal)):
            numeric_cols.append(col)
        elif isinstance(val, str):
            categorical_cols.append(col)
    
    if not numeric_cols:
        logger.error("No numeric columns found in data")
        return []
    
    logger.info(f"Found {len(categorical_cols)} categorical columns: {categorical_cols}")
    logger.info(f"Found {len(numeric_cols)} numeric columns: {numeric_cols}")
    
    theme_colors = ["#14b8a6", "#f97316", "#0ea5e9", "#f43f5e", "#a855f7", 
                    "#10b981", "#8b5cf6", "#ec4899"]
    
    # PIE CHARTS: Special handling - ONE series with object data
    if chart_type.lower() == 'pie':
        # Use first numeric column as values
        num_col = numeric_cols[0]
        
        # Build data as array of {value, name} objects
        pie_data = []
        for row in data:
            # Concatenate all categorical columns for the name
            name_parts = [str(row[col]) for col in categorical_cols if col in row]
            name = " ".join(name_parts) if name_parts else str(row.get(categorical_cols[0], "Unknown"))
            
            value = row[num_col]
            # Convert Decimal to float
            if isinstance(value, Decimal):
                value = float(value)
            
            pie_data.append({"value": value, "name": name})
        
        logger.info(f"Reconstructed pie chart series with {len(pie_data)} slices")
        logger.info(f"First 3 slices: {pie_data[:3]}")
        
        # ONE series, NO itemStyle.color (let global color array handle it)
        return [{
            "type": "pie",
            "data": pie_data
        }]
    
    # BAR/LINE CHARTS: One series per numeric column
    series = []
    for i, num_col in enumerate(numeric_cols):
        # Extract series data and convert Decimals to floats
        series_data_raw = [row[num_col] for row in data if num_col in row]
        series_data_raw = [float(val) if isinstance(val, Decimal) else val for val in series_data_raw]
        
        if series_data_raw:
            logger.info(f"Series '{num_col}': {len(series_data_raw)} points, first 3: {series_data_raw[:3]}")
        
        series_obj = {
            "type": chart_type,
            "name": num_col.replace("_", " ").title()
        }
        
        # CRITICAL COLOR FIX: Single series needs itemStyle per data point for multi-color bars
        if len(numeric_cols) == 1:
            # Single series: Create data as array of objects with individual colors
            series_data = []
            for idx, value in enumerate(series_data_raw):
                series_data.append({
                    "value": value,
                    "itemStyle": {"color": theme_colors[idx % len(theme_colors)]}
                })
            series_obj["data"] = series_data
            logger.info(f"Series '{num_col}' configured with per-bar colors (single series)")
        else:
            # Multiple series: Simple number array with series-level color
            series_obj["data"] = series_data_raw
            series_obj["itemStyle"] = {"color": theme_colors[i % len(theme_colors)]}
            logger.info(f"Series '{num_col}' assigned color {theme_colors[i % len(theme_colors)]} (multiple series)")
        
        series.append(series_obj)
    
    logger.info(f"Reconstructed {len(series)} series from data")
    return series


def extract_categories_from_data(data: list) -> list:
    """
    Extract category values from data, concatenating ALL categorical columns.
    This matches the behavior of reconstruct_xaxis_from_data().
    
    Args:
        data: Query result data
        
    Returns:
        List of composite category values from the data (e.g., ["Category1 Value1"])
    """
    if not data or not isinstance(data[0], dict):
        return []
    
    # Find ALL categorical columns (not just first)
    first_row = data[0]
    categorical_cols = []
    
    for col, val in first_row.items():
        if isinstance(val, str):
            categorical_cols.append(col)
    
    if not categorical_cols:
        return []
    
    # Concatenate ALL categorical columns to create composite labels
    # This matches the xAxis reconstruction logic
    categories = []
    for row in data:
        label_parts = [str(row[col]) for col in categorical_cols if col in row]
        composite_label = " ".join(label_parts)
        categories.append(composite_label)
    
    return categories


def reconstruct_xaxis_from_data(data: list) -> dict:
    """
    Reconstruct xAxis from raw data with intelligent label handling.
    Concatenates ALL categorical columns to preserve full grouping (e.g., "Category1 Value1").
    
    Args:
        data: Query result data
        
    Returns:
        xAxis configuration dict with proper label formatting
    """
    if not data or not isinstance(data[0], dict):
        return {"type": "category", "data": []}
    
    # Find ALL categorical columns
    first_row = data[0]
    categorical_cols = []
    
    for col, val in first_row.items():
        if isinstance(val, str):
            categorical_cols.append(col)
    
    if not categorical_cols:
        # No categorical column found, use row indices
        logger.warning("No categorical columns found, using row indices")
        return {
            "type": "category",
            "data": list(range(len(data)))
        }
    
    # Concatenate ALL categorical columns to create composite labels
    # This preserves grouping like "Argentina M", "Argentina F", etc.
    categories = []
    for row in data:
        # Combine all categorical values with a space separator
        label_parts = [str(row[col]) for col in categorical_cols if col in row]
        composite_label = " ".join(label_parts)
        categories.append(composite_label)
    
    # Debug: Log first few categories to verify data
    if categories:
        logger.info(f"Concatenating {len(categorical_cols)} categorical columns: {categorical_cols}")
        logger.info(f"First 5 composite categories: {categories[:5]}")
        logger.info(f"Last 3 composite categories: {categories[-3:]}")
    
    # Calculate max label length
    max_label_length = max(len(str(cat)) for cat in categories) if categories else 0
    num_categories = len(categories)
    
    # Determine rotation and label formatting based on data characteristics
    # Rotate if: many categories (>10) OR long labels (>15 chars)
    should_rotate = num_categories > 10 or max_label_length > 15
    rotation_angle = 45 if should_rotate else 0
    
    # Build axis label configuration
    axis_label_config = {
        "rotate": rotation_angle,
        "interval": "auto",  # Let ECharts automatically skip labels to prevent overlap
    }
    
    # Add formatter to truncate very long labels (>30 chars)
    if max_label_length > 30:
        # Use a formatter function (as string) to truncate labels
        # ECharts will evaluate this as JavaScript
        axis_label_config["formatter"] = "{value}"  # Will be enhanced below
        logger.info(f"Labels are long (max {max_label_length} chars), adding truncation hint")
    
    config = {
        "type": "category",
        "data": categories,
        "axisLabel": axis_label_config
    }
    
    logger.info(f"Built xAxis config: {num_categories} categories, max length {max_label_length}, rotation {rotation_angle}°")
    
    return config

