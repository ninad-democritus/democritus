"""Line chart specific prompts"""

LINE_CHART_SYSTEM_PROMPT = """Generate Apache ECharts line chart configuration.

Theme colors: #14b8a6, #f97316, #0ea5e9, #f43f5e, #a855f7, #10b981, #8b5cf6, #ec4899

LINE CHART STRUCTURE (same as bar, different type):
1. Categorical columns → xAxis.data = ["Cat1", "Cat2", ...]
2. Numeric columns → Each becomes a series with data = [num1, num2, ...]
3. series.data MUST be array of NUMBERS: [100, 200, 150]

COLOR RULES - CRITICAL:
- ALWAYS include global color array at root level
- Count numeric columns to determine series count
- IF only ONE numeric column → ONE series → NEVER add itemStyle or itemStyle.color
- IF multiple numeric columns → multiple series → add itemStyle.color to EACH series

SINGLE SERIES COLOR LOGIC:
When there is ONE numeric column, the line uses colors from the global array.
NEVER add itemStyle, itemStyle.color, or any color property to the series object.

Example - Single metric (multi-color line):
Data: [{month: "Jan", value: 120}, {month: "Feb", value: 200}]
→ Config:
{
  "color": ["#14b8a6", "#f97316", "#0ea5e9", "#f43f5e", "#a855f7", "#10b981", "#8b5cf6", "#ec4899"],
  "title": {"text": "Trend Over Time"},
  "xAxis": {"type": "category", "data": ["Jan", "Feb"]},
  "yAxis": {"type": "value"},
  "series": [{
    "type": "line",
    "name": "Value",
    "data": [120, 200],
    "smooth": true
  }],
  "tooltip": {"trigger": "axis"},
  "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": true}
}

Example - Multiple metrics (consistent line colors):
Data: [{month: "Jan", sales: 100, revenue: 200}, {month: "Feb", sales: 150, revenue: 300}]
→ Config:
{
  "color": ["#14b8a6", "#f97316", "#0ea5e9", "#f43f5e", "#a855f7", "#10b981", "#8b5cf6", "#ec4899"],
  "title": {"text": "Sales vs Revenue"},
  "xAxis": {"type": "category", "data": ["Jan", "Feb"]},
  "yAxis": {"type": "value"},
  "series": [
    {"type": "line", "name": "Sales", "data": [100, 150], "smooth": true, "itemStyle": {"color": "#14b8a6"}},
    {"type": "line", "name": "Revenue", "data": [200, 300], "smooth": true, "itemStyle": {"color": "#f97316"}}
  ],
  "tooltip": {"trigger": "axis"},
  "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": true},
  "legend": {"show": true}
}

Return ONLY valid JSON."""


LINE_CHART_USER_PROMPT = """Title: {title}
Data ({total_rows} rows):
{data}

Columns:
- Categorical: {categorical_cols}
- Numeric: {numeric_cols}

STEP-BY-STEP:
1. Add global color array at root: "color": ["#14b8a6", "#f97316", "#0ea5e9", ...]
2. Extract categorical values → xAxis.data
3. Count numeric columns: {numeric_cols}
   - If 1 numeric column → Create 1 series WITHOUT itemStyle or itemStyle.color
   - If 2+ numeric columns → Create multiple series, each WITH itemStyle.color
4. For single series: series object has NO itemStyle property at all
5. Add "smooth": true to each series for curved lines
6. Include: color, title, xAxis, yAxis, series, tooltip, grid, legend (if multiple series)

REMEMBER: Single series = multi-color line (no itemStyle). Multiple series = consistent colors (with itemStyle.color)."""
