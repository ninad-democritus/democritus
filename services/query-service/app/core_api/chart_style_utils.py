"""
Chart styling utilities for consistent color application.
Extracted from echarts_generator.py to be reusable during hydration.
"""

# Color palette used across chart generation and hydration
# Must match the palette in echarts_generator.py
COLOR_PALETTE = [
    "#14b8a6",  # Teal
    "#f97316",  # Orange
    "#0ea5e9",  # Blue
    "#f43f5e",  # Red/Pink
    "#a855f7",  # Purple
    "#10b981",  # Green
    "#8b5cf6",  # Violet
    "#ec4899"   # Pink
]


def get_color_for_index(index: int) -> str:
    """
    Get color for a given index (wraps around if index > palette size).
    
    Args:
        index: Zero-based index
        
    Returns:
        Hex color string
    """
    return COLOR_PALETTE[index % len(COLOR_PALETTE)]


def should_show_legend(chart_type: str, series_count: int) -> bool:
    """
    Determine if legend should be shown based on chart type and series count.
    
    Rules (from echarts_generator.py):
    - Bar/Line single-series: NO (each bar has different color)
    - Bar/Line multi-series: YES (need to distinguish series)
    - Pie: ALWAYS (shows what each slice represents)
    - Scatter: Based on series count
    
    Args:
        chart_type: Type of chart (bar, line, pie, scatter)
        series_count: Number of series in the chart
        
    Returns:
        True if legend should be shown
    """
    chart_type = chart_type.lower()
    
    if chart_type == 'pie':
        return True
    
    if chart_type in ['bar', 'line']:
        return series_count > 1
    
    if chart_type == 'scatter':
        return series_count > 1
    
    # Default
    return series_count > 1

