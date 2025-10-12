"""
Chart Styling Engine - Applies colors and legends dynamically based on current data.

This module extracts the styling logic from echarts_generator.py and makes it
reusable during chart hydration. It applies the same rules but works with
fresh data that may have changed since chart creation.
"""
import logging
from typing import Dict, List, Any
from decimal import Decimal

from .chart_style_utils import COLOR_PALETTE, get_color_for_index, should_show_legend

logger = logging.getLogger(__name__)


class ChartStylingEngine:
    """
    Applies styling (colors, legends) to chart configurations based on
    current data structure. Handles dynamic data changes intelligently.
    """
    
    def __init__(self):
        self.color_palette = COLOR_PALETTE
    
    def style_bar_chart(self, echarts_config: Dict[str, Any], data: List[Dict]) -> Dict[str, Any]:
        """
        Apply styling to bar chart based on current data structure.
        
        Logic:
        - Single series (1 value column): Each bar gets different color, no legend
        - Multi series (2+ value columns): Each series gets one color, show legend
        
        Args:
            echarts_config: ECharts options dict (will be modified in place)
            data: Current data rows
            
        Returns:
            Modified echarts_config
        """
        if not echarts_config.get("series"):
            logger.warning("No series found in bar chart config")
            return echarts_config
        
        series_count = len(echarts_config["series"])
        logger.info(f"Styling bar chart with {series_count} series")
        
        if series_count == 1:
            # Single series: Apply different color to each bar
            self._apply_per_item_colors(echarts_config["series"][0], data)
            
            # Remove legend for single-series bar charts
            if "legend" in echarts_config:
                del echarts_config["legend"]
                logger.info("Removed legend for single-series bar chart")
        
        elif series_count > 1:
            # Multi series: Each series keeps default color behavior
            # ECharts will use the global color palette for series
            
            # Ensure legend exists and is populated
            series_names = [s.get("name", f"Series {i+1}") for i, s in enumerate(echarts_config["series"])]
            
            if "legend" not in echarts_config:
                echarts_config["legend"] = {"show": True, "type": "scroll"}
            
            echarts_config["legend"]["data"] = series_names
            logger.info(f"Set legend for multi-series bar chart: {series_names}")
        
        # Ensure global color array is set
        if "color" not in echarts_config:
            echarts_config["color"] = self.color_palette
        
        return echarts_config
    
    def style_line_chart(self, echarts_config: Dict[str, Any], data: List[Dict]) -> Dict[str, Any]:
        """
        Apply styling to line chart (same logic as bar chart).
        
        Args:
            echarts_config: ECharts options dict
            data: Current data rows
            
        Returns:
            Modified echarts_config
        """
        return self.style_bar_chart(echarts_config, data)
    
    def style_pie_chart(self, echarts_config: Dict[str, Any], data: List[Dict]) -> Dict[str, Any]:
        """
        Apply styling to pie chart based on current data structure.
        
        Logic:
        - Colors applied via GLOBAL color array (NOT per-item itemStyle)
        - Legend always shown with slice names
        - Labels enabled by default to show slice names with leader lines
        
        Args:
            echarts_config: ECharts options dict
            data: Current data rows
            
        Returns:
            Modified echarts_config
        """
        logger.info("=== PIE CHART STYLING START ===")
        logger.info(f"Input echarts_config keys: {echarts_config.keys()}")
        
        if not echarts_config.get("series") or len(echarts_config["series"]) == 0:
            logger.error("No series found in pie chart config")
            return echarts_config
        
        series = echarts_config["series"][0]
        logger.info(f"Series before styling: type={series.get('type')}, has_label={'label' in series}, has_data={'data' in series}")
        
        pie_data = series.get("data", [])
        
        if not pie_data:
            logger.error("No data in pie chart series - cannot style")
            return echarts_config
        
        logger.info(f"Styling pie chart with {len(pie_data)} slices")
        logger.info(f"First slice: {pie_data[0] if pie_data else 'none'}")
        
        # Collect slice names (DON'T add itemStyle - let global colors work)
        slice_names = []
        for i, item in enumerate(pie_data):
            if isinstance(item, dict):
                name = item.get("name", f"Slice {i+1}")
                slice_names.append(name)
                logger.debug(f"  Slice {i}: name='{name}', value={item.get('value')}")
            else:
                logger.warning(f"Pie data item {i} is not a dict: {type(item)}, value={item}")
        
        logger.info(f"Collected {len(slice_names)} slice names: {slice_names}")
        
        # CRITICAL: Ensure series has proper label configuration
        # This needs to be in the series object that's IN the echarts_config
        logger.info(f"Label config before: {series.get('label', 'MISSING')}")
        
        if "label" not in series:
            echarts_config["series"][0]["label"] = {
                "show": True,
                "position": "outside",
                "formatter": "{b}"  # {b} shows the slice name
            }
            logger.info("✓ Added NEW label configuration to pie series")
        else:
            # Label exists - ensure it's enabled
            existing_label = echarts_config["series"][0]["label"]
            logger.info(f"Label exists: {existing_label}")
            
            if not existing_label.get("show", True):
                echarts_config["series"][0]["label"]["show"] = True
                logger.info("✓ Enabled show in existing label")
            
            if "formatter" not in existing_label:
                echarts_config["series"][0]["label"]["formatter"] = "{b}"
                logger.info("✓ Added formatter to existing label")
        
        logger.info(f"Label config after: {echarts_config['series'][0].get('label')}")
        
        # Always add/update legend for pie charts
        if "legend" not in echarts_config:
            echarts_config["legend"] = {"orient": "vertical", "left": "left"}
            logger.info("✓ Added NEW legend config")
        else:
            logger.info(f"Legend exists: {echarts_config['legend']}")
        
        echarts_config["legend"]["data"] = slice_names
        logger.info(f"✓ Set legend.data to {len(slice_names)} items: {slice_names}")
        
        # Ensure global color array is set (this is how pie charts get colors)
        if "color" not in echarts_config:
            echarts_config["color"] = self.color_palette
            logger.info(f"✓ Set global color palette ({len(self.color_palette)} colors)")
        else:
            logger.info(f"Color array already exists: {len(echarts_config.get('color', []))} colors")
        
        logger.info("=== PIE CHART STYLING END ===")
        logger.info(f"Final series[0] keys: {echarts_config['series'][0].keys()}")
        
        return echarts_config
    
    def style_scatter_chart(self, echarts_config: Dict[str, Any], data: List[Dict]) -> Dict[str, Any]:
        """
        Apply styling to scatter chart.
        
        Args:
            echarts_config: ECharts options dict
            data: Current data rows
            
        Returns:
            Modified echarts_config
        """
        series_count = len(echarts_config.get("series", []))
        
        # Show legend if multiple series
        if series_count > 1:
            series_names = [s.get("name", f"Series {i+1}") for i, s in enumerate(echarts_config["series"])]
            if "legend" not in echarts_config:
                echarts_config["legend"] = {"show": True}
            echarts_config["legend"]["data"] = series_names
        
        # Ensure global color array is set
        if "color" not in echarts_config:
            echarts_config["color"] = self.color_palette
        
        return echarts_config
    
    def _apply_per_item_colors(self, series: Dict[str, Any], data: List[Dict]) -> None:
        """
        Apply different color to each data item in a series.
        Modifies the series data array to use object format with itemStyle.
        
        Args:
            series: Series object to modify
            data: Original data rows (for logging)
        """
        series_data = series.get("data", [])
        if not series_data:
            logger.warning("No data in series to style")
            return
        
        styled_data = []
        for i, value in enumerate(series_data):
            color = get_color_for_index(i)
            
            if isinstance(value, dict):
                # Already an object, just add/update itemStyle
                if "itemStyle" not in value:
                    value["itemStyle"] = {}
                value["itemStyle"]["color"] = color
                styled_data.append(value)
            else:
                # Plain value, convert to object with itemStyle
                styled_data.append({
                    "value": float(value) if isinstance(value, Decimal) else value,
                    "itemStyle": {"color": color}
                })
        
        series["data"] = styled_data
        logger.info(f"Applied per-item colors to {len(styled_data)} data points")


# Global instance
_styling_engine = None


def get_styling_engine() -> ChartStylingEngine:
    """Get global styling engine instance"""
    global _styling_engine
    if _styling_engine is None:
        _styling_engine = ChartStylingEngine()
    return _styling_engine

