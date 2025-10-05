"""Bar chart specific prompts"""

BAR_CHART_SYSTEM_PROMPT = """Generate Apache ECharts bar chart configuration.

Theme colors: #14b8a6, #f97316, #0ea5e9, #f43f5e, #a855f7, #10b981, #8b5cf6, #ec4899

BAR CHART STRUCTURE:
1. Categorical columns → xAxis.data = ["Cat1", "Cat2", ...]
2. Numeric columns → Each becomes a series
3. SINGLE series: data = array of objects with value + itemStyle per bar
4. MULTIPLE series: data = array of numbers

COLOR RULES - CRITICAL:
- ALWAYS include global color array at root level
- Count numeric columns to determine series count
- IF only ONE numeric column → ONE series → Use special data structure with itemStyle PER BAR
- IF multiple numeric columns → multiple series → add itemStyle.color to series object

SINGLE SERIES COLOR LOGIC (MULTI-COLOR BARS):
When there is ONE numeric column, each bar needs a DIFFERENT color.
DO NOT add itemStyle to the series object.
INSTEAD, create data as array of objects with value + itemStyle for each bar.

Example - Single metric (multi-color bars):
Data: [{region: "North", sales: 120}, {region: "South", sales: 200}, {region: "East", sales: 150}]
One numeric column (sales) → ONE series → itemStyle PER data point
→ Config:
{
  "color": ["#14b8a6", "#f97316", "#0ea5e9", "#f43f5e", "#a855f7", "#10b981", "#8b5cf6", "#ec4899"],
  "title": {"text": "Sales by Region"},
  "xAxis": {"type": "category", "data": ["North", "South", "East"]},
  "yAxis": {"type": "value"},
  "series": [{
    "type": "bar",
    "name": "Sales",
    "data": [
      {"value": 120, "itemStyle": {"color": "#14b8a6"}},
      {"value": 200, "itemStyle": {"color": "#f97316"}},
      {"value": 150, "itemStyle": {"color": "#0ea5e9"}}
    ]
  }],
  "tooltip": {"trigger": "axis"},
  "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": true}
}

Note: NO legend for single series (each bar has different color, legend would be misleading)

WRONG for single series (DO NOT DO THIS):
{
  "series": [{
    "type": "bar",
    "name": "Sales",
    "data": [120, 200, 150],  ← WRONG! Use objects with itemStyle
    "itemStyle": {"color": "#14b8a6"}  ← WRONG! Don't put itemStyle on series
  }]
}

Example - Multiple metrics (consistent series colors):
Data: [{team: "A", gold: 10, silver: 8}, {team: "B", gold: 15, silver: 12}]
→ Config:
{
  "color": ["#14b8a6", "#f97316", "#0ea5e9", "#f43f5e", "#a855f7", "#10b981", "#8b5cf6", "#ec4899"],
  "title": {"text": "Medals by Team"},
  "xAxis": {"type": "category", "data": ["A", "B"]},
  "yAxis": {"type": "value"},
  "series": [
    {"type": "bar", "name": "Gold", "data": [10, 15], "itemStyle": {"color": "#14b8a6"}},
    {"type": "bar", "name": "Silver", "data": [8, 12], "itemStyle": {"color": "#f97316"}}
  ],
  "tooltip": {"trigger": "axis"},
  "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": true},
  "legend": {"show": true}
}

Return ONLY valid JSON."""


BAR_CHART_USER_PROMPT = """Title: {title}
Data ({total_rows} rows):
{data}

Columns:
- Categorical: {categorical_cols}
- Numeric: {numeric_cols}

STEP-BY-STEP:
1. Add global color array at root: "color": ["#14b8a6", "#f97316", "#0ea5e9", ...]
2. Extract categorical values → xAxis.data
3. Count numeric columns: {numeric_cols}

IF 1 numeric column (SINGLE SERIES):
   - Create series.data as ARRAY OF OBJECTS (not plain numbers)
   - Each object: {{"value": number, "itemStyle": {{"color": "color_from_palette"}}}}
   - Use different color for each data point from the color array
   - Example: [{{"value": 120, "itemStyle": {{"color": "#14b8a6"}}}}, {{"value": 200, "itemStyle": {{"color": "#f97316"}}}}]
   - DO NOT include legend (each bar has different color)

IF 2+ numeric columns (MULTIPLE SERIES):
   - Create series.data as array of plain numbers: [120, 200]
   - Add itemStyle.color to the series object (not data points)
   - Each series gets one consistent color
   - Include legend: {{"show": true, "type": "scroll"}}

4. Include: color, title, xAxis, yAxis, series, tooltip, grid
5. Legend: ONLY if multiple series (2+ numeric columns)

CRITICAL: Single series = data with objects containing value + itemStyle per bar."""
