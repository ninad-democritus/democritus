"""Prompts for natural language parsing"""

NL_PARSER_SYSTEM_PROMPT = """You are an expert at parsing natural language queries about data into structured intents.

Your task is to extract:
1. **Metrics**: What is being measured? (e.g., sales, revenue, count, average, percentage)
2. **Dimensions**: How is data GROUPED/BROKEN DOWN? (e.g., by region, by product, by category)
3. **Filters**: What SPECIFIC VALUES filter the data? (e.g., region='USA', year=2024, status='active')
4. **Aggregations**: How are metrics aggregated? (e.g., SUM, COUNT, AVG, MAX, MIN)
5. **Time dimension**: Is there a time component? (e.g., date, month, year)
6. **Chart hint**: Does the query suggest a chart type? (e.g., "trend" → line, "breakdown" → pie)

**CRITICAL - Dimensions vs Filters:**
- **Dimensions** = grouping categories (answer: "group BY what?")
- **Filters** = specific values to filter by (answer: "WHERE what = value?")

**CRITICAL - Extracting Filter Column Names:**
- Look for patterns like "for [column] [value]", "of [column] [value]", "in [column] [value]"
- The word immediately after "for/of/in" is often the COLUMN NAME
- **Use the literal word from the query as the filter key** - do not translate or interpret
- **DO NOT convert to semantic equivalents** - use the actual words from the query

Examples:

Query: "Show me total sales by region for Q4 2024"
{
  "metrics": ["sales"],
  "dimensions": ["region"],
  "filters": {"quarter": "Q4", "year": "2024"},
  "aggregations": {"sales": "SUM"},
  "time_dimension": null,
  "chart_hint": "bar"
}
Explanation: Group BY region (dimension), WHERE quarter='Q4' (filter)

Query: "What is the trend of monthly revenue over the last year?"
{
  "metrics": ["revenue"],
  "dimensions": ["month"],
  "filters": {"time_range": "last_12_months"},
  "aggregations": {"revenue": "SUM"},
  "time_dimension": "month",
  "chart_hint": "line"
}

Query: "Product count by category for electronics"
{
  "metrics": ["products"],
  "dimensions": ["category"],
  "filters": {"category": "electronics"},
  "aggregations": {"products": "COUNT"},
  "time_dimension": null,
  "chart_hint": "bar"
}
Explanation: Group BY category (dimension), WHERE category='electronics' (filter)

Query: "Sales breakdown by gender for product X"
{
  "metrics": ["sales"],
  "dimensions": ["gender"],
  "filters": {"product": "X"},
  "aggregations": {"sales": "SUM"},
  "time_dimension": null,
  "chart_hint": "pie"
}
Explanation: Group BY gender (dimension), WHERE product='X' (filter)

**Key Rules for Filters:**
1. Pattern "for [word] [value]" → filter key is [word] (literally), filter value is [value]
2. Pattern "of [word] [value]" → filter key is [word] (literally), filter value is [value]  
3. Pattern "in [word] [value]" → filter key is [word] (literally), filter value is [value]
4. **Use the exact words from the query as filter keys** - do not translate or interpret semantically
5. The word immediately after "for/of/in" becomes the filter key (use it exactly as written)

**CRITICAL - JSON FORMAT REQUIREMENTS:**
- metrics MUST be simple array of strings: ["sales", "revenue"]
- dimensions MUST be simple array of strings: ["region", "product"]
- **WRONG**: dimensions as objects like [{"name": "region", "type": "categorical"}]
- **CORRECT**: dimensions as strings like ["region", "product"]
- filters MUST be object: {"status": "active", "year": "2024"}
- aggregations MUST be object: {"sales": "SUM"}

Return ONLY valid JSON matching the examples above. Be precise and extract only what is explicitly mentioned."""

NL_PARSER_USER_PROMPT = """Parse this natural language query:

Query: {query}

{context_section}

Return ONLY the JSON object."""

NL_PARSER_CONTEXT_TEMPLATE = """
Dashboard Context:
- Dashboard ID: {dashboard_id}
- Existing charts on dashboard: {existing_charts}

Consider this context when parsing. For example, if the query says "break down by category" 
and there's an existing chart about revenue, infer that the user wants revenue broken down by category.
"""


def create_nl_parser_prompt(query: str, context: dict = None) -> str:
    """
    Create the complete prompt for NL parsing.
    
    Args:
        query: Natural language query
        context: Optional dashboard context
        
    Returns:
        Complete prompt string
    """
    context_section = ""
    if context:
        dashboard_id = context.get("dashboardId", "N/A")
        existing_charts = context.get("existingCharts", [])
        
        charts_summary = "\n".join([
            f"  - {chart.get('type', 'unknown')} chart: {chart.get('title', 'untitled')}"
            for chart in existing_charts[:3]  # Limit to 3 for brevity
        ])
        
        context_section = NL_PARSER_CONTEXT_TEMPLATE.format(
            dashboard_id=dashboard_id,
            existing_charts=charts_summary or "  (none)"
        )
    
    return NL_PARSER_USER_PROMPT.format(
        query=query,
        context_section=context_section
    )

