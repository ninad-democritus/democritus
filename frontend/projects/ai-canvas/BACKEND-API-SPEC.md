# Backend API Specification for Dashboard Builder

## Overview

This document specifies the backend API requirements for the AI Canvas Dashboard Builder feature. The backend Query Service is responsible for:

1. **Natural Language Processing**: Parse user queries
2. **SQL Generation**: Convert NL queries to SQL using LLM
3. **Data Fetching**: Execute SQL against data warehouse
4. **Chart Configuration**: Generate ECharts configuration based on data
5. **Smart Recommendations**: Suggest chart types and sizes when not specified

---

## Endpoint: Generate Chart

### Request

```
POST /api/v1/query-service/generate-chart
Content-Type: application/json
Authorization: Bearer <token>
```

### Request Body

```typescript
interface ChartGenerationRequest {
  // Required: User's natural language query
  naturalLanguageQuery: string;
  
  // Optional: Constraints from frontend (Workflow A)
  // If present, backend MUST respect these constraints
  constraints?: {
    chartType?: string;        // 'bar', 'line', 'pie', 'area', 'scatter', 'table', 'kpi', 'heatmap'
    chartSize?: {
      cols: number;            // Grid columns (1-12)
      rows: number;            // Grid rows (1-12)
    };
    position?: {
      x: number;               // Grid x position
      y: number;               // Grid y position
    };
  };
  
  // Optional: Dashboard context for better AI understanding
  context?: {
    dashboardId?: string;
    existingCharts?: Array<{
      type: string;
      title: string;
      query: string;
    }>;
  };
}
```

### Request Examples

#### Example 1: Workflow A (With Constraints)

User dragged a bar chart and wants data:

```json
{
  "naturalLanguageQuery": "Show me sales by region for last quarter",
  "constraints": {
    "chartType": "bar",
    "chartSize": { "cols": 4, "rows": 3 },
    "position": { "x": 0, "y": 0 }
  }
}
```

**Backend behavior**: Generate bar chart matching size constraints.

#### Example 2: Workflow B (No Constraints)

User asks for chart without specifying type:

```json
{
  "naturalLanguageQuery": "Show me the trend of monthly revenue over the last year"
}
```

**Backend behavior**: AI determines best chart type (likely "line" for trends).

#### Example 3: With Context

User asks follow-up question with dashboard context:

```json
{
  "naturalLanguageQuery": "Break down by product category",
  "context": {
    "dashboardId": "dash-123",
    "existingCharts": [
      {
        "type": "line",
        "title": "Revenue Trend",
        "query": "monthly revenue over last year"
      }
    ]
  }
}
```

**Backend behavior**: AI understands to break down revenue (from context) by product category.

---

## Response

### Success Response

```
HTTP/1.1 200 OK
Content-Type: application/json
```

```typescript
interface ChartGenerationResult {
  success: true;
  
  // Actual data from database
  data: any[];
  
  // Chart configuration
  chartConfig: {
    type: string;              // Chart type: 'bar', 'line', 'pie', etc.
    title: string;             // Auto-generated title
    echartsOptions: any;       // Complete ECharts configuration object
    size?: {                   // Recommended size (if not constrained)
      cols: number;
      rows: number;
    };
  };
  
  // Metadata for transparency and debugging
  metadata: {
    sqlQuery: string;          // Generated SQL (for user visibility)
    dataSchema: any;           // Schema of returned data
    recommendedChartType?: string;  // If AI recommended (vs. constrained)
    confidence: number;        // AI confidence score (0-1)
  };
  
  // Echo back for frontend storage
  naturalLanguageQuery: string;
}
```

### Success Response Example

```json
{
  "success": true,
  "data": [
    { "region": "North", "sales": 45000 },
    { "region": "South", "sales": 38000 },
    { "region": "East", "sales": 52000 },
    { "region": "West": 41000 }
  ],
  "chartConfig": {
    "type": "bar",
    "title": "Sales by Region - Q4 2024",
    "echartsOptions": {
      "xAxis": {
        "type": "category",
        "data": ["North", "South", "East", "West"],
        "axisLabel": { "color": "#64748b" }
      },
      "yAxis": {
        "type": "value",
        "name": "Sales ($)",
        "axisLabel": { "color": "#64748b", "formatter": "${value}" }
      },
      "series": [{
        "name": "Sales",
        "type": "bar",
        "data": [45000, 38000, 52000, 41000],
        "itemStyle": {
          "color": "#14b8a6",
          "borderRadius": [4, 4, 0, 0]
        }
      }],
      "tooltip": {
        "trigger": "axis",
        "formatter": "{b}: ${c}"
      },
      "grid": {
        "left": "10%",
        "right": "10%",
        "bottom": "15%",
        "top": "15%"
      }
    },
    "size": {
      "cols": 4,
      "rows": 3
    }
  },
  "metadata": {
    "sqlQuery": "SELECT region, SUM(sales) as sales FROM sales_data WHERE quarter = 'Q4' AND year = 2024 GROUP BY region ORDER BY sales DESC",
    "dataSchema": {
      "region": "string",
      "sales": "number"
    },
    "recommendedChartType": "bar",
    "confidence": 0.95
  },
  "naturalLanguageQuery": "Show me sales by region for last quarter"
}
```

### Error Response

```
HTTP/1.1 400 Bad Request
Content-Type: application/json
```

```typescript
interface ChartGenerationError {
  success: false;
  error: string;             // Human-readable error message
  errorCode: string;         // Machine-readable error code
  details?: any;             // Additional error details
}
```

### Error Response Examples

#### No Data Found

```json
{
  "success": false,
  "error": "No data found for the specified query. The query 'sales for product XYZ999' returned 0 results.",
  "errorCode": "NO_DATA_FOUND",
  "details": {
    "sqlQuery": "SELECT * FROM sales_data WHERE product_id = 'XYZ999'",
    "suggestion": "Try checking if the product code is correct or use a broader query."
  }
}
```

#### Invalid Query

```json
{
  "success": false,
  "error": "Could not understand the query. Please rephrase or be more specific.",
  "errorCode": "INVALID_QUERY",
  "details": {
    "parsedIntent": "unknown",
    "suggestion": "Try asking: 'Show me [metric] by [dimension]' or 'What is the trend of [metric] over time?'"
  }
}
```

#### SQL Execution Error

```json
{
  "success": false,
  "error": "Database error: Table 'sales_data' does not exist",
  "errorCode": "SQL_EXECUTION_ERROR",
  "details": {
    "sqlQuery": "SELECT * FROM sales_data...",
    "dbError": "Table 'sales_data' doesn't exist in schema 'public'"
  }
}
```

---

## Backend Processing Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Receive Request                                      │
│    - naturalLanguageQuery: "sales by region"           │
│    - constraints: { chartType: "bar" }                 │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Parse Natural Language with LLM                      │
│    - Extract entities: "sales", "region"               │
│    - Identify aggregation: SUM(sales)                  │
│    - Identify grouping: GROUP BY region                │
│    - Identify filters: none specified → last quarter   │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Generate SQL                                         │
│    SELECT region, SUM(sales) as sales                  │
│    FROM sales_data                                      │
│    WHERE quarter = 'Q4' AND year = 2024                │
│    GROUP BY region                                      │
│    ORDER BY sales DESC                                  │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Execute SQL Against Data Warehouse                   │
│    Result: [                                            │
│      { region: "North", sales: 45000 },                │
│      { region: "South", sales: 38000 },                │
│      ...                                                │
│    ]                                                     │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Analyze Data Characteristics                         │
│    - Type: Categorical (region) vs Numeric (sales)     │
│    - Cardinality: 4 regions                            │
│    - Distribution: Varies by region                    │
│    - Temporal: No time dimension                       │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Determine Chart Type                                 │
│    - If constrained: use chartType = "bar"             │
│    - If not constrained: recommend based on data       │
│      • Categorical comparison → bar                    │
│      • Time series → line                              │
│      • Parts of whole → pie                            │
│      • Correlation → scatter                           │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 7. Generate ECharts Configuration                       │
│    - Map data to chart axes                            │
│    - Apply Ocean Breeze theme colors (#14b8a6)         │
│    - Configure tooltips, legends, labels               │
│    - Optimize for requested size (4x3 grid)            │
│    - Add accessibility features                        │
└───────────────────┬─────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ 8. Return Response                                      │
│    - data: raw data array                              │
│    - chartConfig: complete ECharts config              │
│    - metadata: SQL, schema, confidence                 │
└─────────────────────────────────────────────────────────┘
```

---

## LLM Requirements for Backend

### Chart Type Recommendation Logic

The backend LLM should use these heuristics when no chart type is constrained:

| Data Characteristics | Recommended Chart | Reason |
|---------------------|-------------------|---------|
| Categorical vs Numeric (no time) | Bar Chart | Compare categories |
| Time series (single metric) | Line Chart | Show trends |
| Time series (multiple metrics) | Multi-line Chart | Compare trends |
| Parts of whole | Pie Chart | Show proportions |
| Two numeric dimensions | Scatter Plot | Show correlation |
| Single metric | KPI Card | Emphasize value |
| Time x Category matrix | Heatmap | Show patterns |
| Raw data requested | Table | Display all fields |

### Chart Size Recommendation Logic

| Data Points | Chart Type | Recommended Size |
|-------------|-----------|------------------|
| 1 value | KPI Card | 2x2 or 3x2 |
| 2-5 items | Bar/Pie | 4x3 |
| 6-12 items | Bar/Line | 6x3 |
| 13-30 items | Line/Area | 8x4 |
| 30+ items | Line/Heatmap | 12x4 (full width) |
| Tabular data | Table | 6x4 or larger |

### Title Generation

Generate descriptive titles automatically:
- Include metric name: "Sales", "Revenue", "Customer Count"
- Include dimension: "by Region", "by Product", "over Time"
- Include time period if applicable: "Q4 2024", "Last 12 Months"
- Format: `{Metric} {by Dimension} - {Time Period}`

Examples:
- "Sales by Region - Q4 2024"
- "Monthly Revenue Trend - 2024"
- "Top 10 Products by Revenue"
- "Customer Distribution by Age Group"

---

## ECharts Configuration Requirements

### Theme Integration

All ECharts configs should use Ocean Breeze theme colors:

```javascript
{
  color: ['#14b8a6', '#f97316', '#0ea5e9', '#f43f5e', '#a855f7'],  // Primary, Accent, Info, Error, Secondary
  backgroundColor: '#ffffff',
  textStyle: {
    color: '#0f172a'  // Text primary
  },
  axisLabel: {
    color: '#64748b'  // Text tertiary
  },
  splitLine: {
    lineStyle: {
      color: '#e2e8f0'  // Border light
    }
  }
}
```

### Responsive Configuration

Charts should be configured to work well at different sizes:

**Small (2x2, 3x2)**
- Minimal labels
- No legend (use tooltip)
- Large fonts

**Medium (4x3, 6x3)**
- Standard labels
- Optional legend
- Normal fonts

**Large (8x4, 12x4)**
- Detailed labels
- Legend enabled
- Rich tooltips
- Zoom controls for large datasets

### Required ECharts Features

All chart configs MUST include:
1. **Tooltip**: Interactive data display on hover
2. **Responsive grid**: Margins that work at different sizes
3. **Accessibility**: Proper ARIA labels and descriptions
4. **Color theme**: Ocean Breeze palette
5. **Number formatting**: Appropriate for data type (currency, percentage, etc.)

---

## Testing Requirements

### Test Cases for Backend Team

1. **Basic NL Query**
   - Input: "show sales by region"
   - Expected: Valid SQL, bar chart, 4 data points

2. **Time Series Query**
   - Input: "revenue trend over last 12 months"
   - Expected: Line chart recommended, 12 data points

3. **Constrained Query**
   - Input: "sales by region" + constraint: {chartType: "pie"}
   - Expected: Pie chart (not bar), same data

4. **No Data Query**
   - Input: "sales for product XYZ999"
   - Expected: Error with helpful suggestion

5. **Ambiguous Query**
   - Input: "show me data"
   - Expected: Error asking for clarification

6. **Complex Query**
   - Input: "top 10 products by revenue excluding returns"
   - Expected: SQL with LIMIT, WHERE clause, ORDER BY

7. **Multi-dimensional Query**
   - Input: "sales by region and product category"
   - Expected: Grouped bar chart or heatmap

### Performance Requirements

- **Response time**: < 3 seconds for typical queries
- **Concurrent requests**: Support 10+ simultaneous users
- **Data limits**: Handle up to 10,000 data points efficiently
- **Caching**: Cache SQL results for identical queries (5 min TTL)

---

## Security & Data Access

### Authentication

All requests must include valid JWT token:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Data Access Control

Backend MUST:
1. Validate user has access to requested data sources
2. Apply row-level security based on user permissions
3. Sanitize SQL to prevent injection attacks
4. Limit query execution time (30 second timeout)
5. Limit result set size (max 10,000 rows)

### Rate Limiting

```
Rate limit: 60 requests per minute per user
Burst: 10 requests
```

---

## Future Enhancements

### Phase 2 Features

1. **Multi-step Conversations**
   - "Show sales" → "Now break down by region" → "Now as pie chart"
   
2. **Dashboard-wide Context**
   - "Compare this to last year" (referring to previous chart)
   
3. **Data Source Selection**
   - "Show sales from Salesforce" vs "from our data warehouse"
   
4. **Advanced Visualizations**
   - Combo charts (bar + line)
   - Stacked charts
   - Dual-axis charts
   
5. **Export Options**
   - Download chart as PNG/SVG
   - Export data as CSV/Excel
   
6. **Scheduled Refresh**
   - Auto-refresh charts every N minutes
   - Email alerts on metric thresholds

---

## API Versioning

Current version: `/api/v1/query-service/`

Future versions will maintain backwards compatibility. Breaking changes will increment version number (v2, v3, etc.).

---

## Contact & Support

For backend API questions:
- Documentation: This file
- Frontend examples: `WORKFLOWS.md`
- Data models: `DASHBOARD-BUILDER-DESIGN.md`

