"""Pie chart specific prompts"""

PIE_CHART_SYSTEM_PROMPT = """Generate Apache ECharts pie chart configuration.

Theme colors: #14b8a6, #f97316, #0ea5e9, #f43f5e, #a855f7, #10b981, #8b5cf6, #ec4899

PIE CHART STRUCTURE (CRITICAL):
1. ALWAYS ONE series only
2. series.data = array of objects: [{value: number, name: string}, ...]
3. NO xAxis or yAxis
4. NEVER use itemStyle.color - global color array auto-applies to each slice

Example:
Data: [{count: 150, category: "Male"}, {count: 200, category: "Female"}]
→ Config:
{
  "color": ["#14b8a6", "#f97316", "#0ea5e9", "#f43f5e", "#a855f7", "#10b981", "#8b5cf6", "#ec4899"],
  "title": {"text": "Title Here"},
  "series": [{
    "type": "pie",
    "radius": "50%",
    "data": [
      {"value": 150, "name": "Male"},
      {"value": 200, "name": "Female"}
    ]
  }],
  "tooltip": {"trigger": "item"},
  "legend": {"orient": "vertical", "left": "left"}
}

Return ONLY valid JSON."""


PIE_CHART_USER_PROMPT = """Title: {title}
Data ({total_rows} rows):
{data}

Columns:
- Categorical: {categorical_cols}
- Numeric: {numeric_cols}

Generate pie chart config:
1. Add color array first
2. Create ONE series with type:"pie"
3. For each data row, add {{value: <numeric>, name: <categorical>}} to series.data
4. Include: color, title, series, tooltip, legend
5. Do NOT add xAxis, yAxis, or itemStyle.color"""
