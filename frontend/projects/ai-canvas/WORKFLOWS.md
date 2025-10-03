# Dashboard Builder - User Workflows

## Overview
The Dashboard Builder supports two primary workflows for creating charts with AI assistance.

---

## Workflow A: Drag-Drop First, Then Populate with AI

**Use Case**: User knows what chart type they want, but needs AI help getting the data.

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: User Action - Drag Chart from Library               │
├─────────────────────────────────────────────────────────────┤
│ User sees "Bar Chart" in left panel                         │
│ User drags "Bar Chart" icon to center grid                  │
│ User drops it at desired position                           │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: System Response - Create Empty Chart Widget         │
├─────────────────────────────────────────────────────────────┤
│ Dashboard Grid creates new DashboardItem:                   │
│   - id: 'chart-1'                                           │
│   - chartType: 'bar'                                        │
│   - cols: 4, rows: 3 (default size)                        │
│   - x: 0, y: 0 (drop position)                             │
│   - config: { title: 'Untitled Chart', echartsOptions: {} }│
│                                                              │
│ Empty widget appears with placeholder:                      │
│ "Click to configure this chart"                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: User Action - Select Chart for Configuration        │
├─────────────────────────────────────────────────────────────┤
│ User clicks on the empty chart widget                       │
│                                                              │
│ Visual feedback:                                             │
│ - Chart widget gets blue border (selected state)            │
│ - AI Chat panel shows indicator:                            │
│   "📊 Bar Chart selected (4x3)"                            │
│   "What data would you like to display?"                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: User Action - Request Data via Chat                 │
├─────────────────────────────────────────────────────────────┤
│ User types in chat input:                                   │
│ "Show me sales by region for last quarter"                 │
│                                                              │
│ User presses Send or Enter                                  │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: System - Send Request to Query Service              │
├─────────────────────────────────────────────────────────────┤
│ Frontend constructs request:                                │
│ {                                                            │
│   "naturalLanguageQuery": "Show me sales by region...",    │
│   "constraints": {                                          │
│     "chartType": "bar",                                     │
│     "chartSize": { "cols": 4, "rows": 3 },                 │
│     "position": { "x": 0, "y": 0 }                         │
│   }                                                          │
│ }                                                            │
│                                                              │
│ AI Chat shows loading:                                      │
│ "🤔 Analyzing your query..."                               │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Backend Processing (Query Service)                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Parse natural language query with LLM                    │
│ 2. Generate SQL: SELECT region, SUM(sales)...               │
│ 3. Execute query against database                           │
│ 4. Get data: [{region: "North", sales: 45000}, ...]        │
│ 5. Generate ECharts config matching bar chart specs         │
│ 6. Return complete response                                 │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 7: System - Update Chart Widget                        │
├─────────────────────────────────────────────────────────────┤
│ ChartDataService updates chart-1:                           │
│ {                                                            │
│   config: {                                                 │
│     title: "Sales by Region - Q4 2024",                    │
│     naturalLanguageQuery: "Show me sales by region...",    │
│     queryTimestamp: "2024-10-02T10:30:00Z",                │
│     echartsOptions: { /* complete config */ },             │
│     queryMetadata: {                                        │
│       sqlQuery: "SELECT region...",                        │
│       confidence: 0.95                                      │
│     }                                                        │
│   }                                                          │
│ }                                                            │
│                                                              │
│ Chart widget re-renders with actual data                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 8: System - AI Chat Response                           │
├─────────────────────────────────────────────────────────────┤
│ AI Chat displays:                                           │
│ "✅ I've updated your bar chart with the requested data.   │
│  The query returned 4 regions with sales data."            │
│                                                              │
│ Chart remains selected for further refinement               │
└─────────────────────────────────────────────────────────────┘
```

### Key Features of Workflow A

✅ **User controls chart type and size** - Manual drag-drop  
✅ **AI handles data fetching** - Smart SQL generation  
✅ **Preserves user intent** - Chart type/size constraints sent to backend  
✅ **Natural language query stored** - For dashboard persistence  

---

## Workflow B: AI-Directed Chart Creation

**Use Case**: User doesn't know what chart type to use, wants AI recommendation.

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: User Action - Direct Query in Chat                  │
├─────────────────────────────────────────────────────────────┤
│ User types in chat (no chart selected):                     │
│ "Show me the trend of monthly revenue over the last year"  │
│                                                              │
│ User presses Send                                           │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: System - Send Request WITHOUT Constraints           │
├─────────────────────────────────────────────────────────────┤
│ Frontend constructs request:                                │
│ {                                                            │
│   "naturalLanguageQuery": "Show me the trend...",          │
│   "constraints": null  // No chart type specified          │
│ }                                                            │
│                                                              │
│ AI Chat shows:                                              │
│ "🤔 Analyzing your query and choosing the best chart..."   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Backend Processing (Query Service - Enhanced)       │
├─────────────────────────────────────────────────────────────┤
│ 1. Parse query with LLM                                     │
│ 2. Identify data requirements: time-series data             │
│ 3. Generate SQL: SELECT month, revenue FROM ...             │
│ 4. Execute query                                             │
│ 5. Analyze data characteristics:                            │
│    - Time-based (months)                                    │
│    - Single metric (revenue)                                │
│    - 12 data points                                         │
│ 6. AI RECOMMENDS: "line" chart (best for trends)           │
│ 7. AI RECOMMENDS: Size 6x3 (wider for time series)         │
│ 8. Generate ECharts config for line chart                   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: System - Create New Chart Automatically             │
├─────────────────────────────────────────────────────────────┤
│ AIChatService creates new DashboardItem:                    │
│ {                                                            │
│   id: 'chart-2',                                            │
│   chartType: 'line',  // AI recommended                    │
│   cols: 6, rows: 3,   // AI recommended                    │
│   x: 0, y: 0,         // Auto-positioned                   │
│   config: {                                                 │
│     title: "Monthly Revenue Trend - 2024",                 │
│     naturalLanguageQuery: "Show me the trend...",          │
│     echartsOptions: { /* line chart config */ },           │
│     queryMetadata: {                                        │
│       recommendedChartType: "line",                        │
│       confidence: 0.92                                      │
│     }                                                        │
│   }                                                          │
│ }                                                            │
│                                                              │
│ New chart appears on grid with data                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: System - AI Chat Explanation                        │
├─────────────────────────────────────────────────────────────┤
│ AI Chat displays:                                           │
│ "✅ I've created a line chart for you with 12 data points. │
│  I recommended this chart type because it's best for       │
│  showing trends over time. The chart shows monthly revenue │
│  data for 2024."                                            │
│                                                              │
│ User can click chart to refine or ask follow-up questions   │
└─────────────────────────────────────────────────────────────┘
```

### Key Features of Workflow B

✅ **AI chooses chart type** - Based on data characteristics  
✅ **AI recommends size** - Based on data density and type  
✅ **Automatic chart creation** - No drag-drop required  
✅ **Explainability** - AI explains why it chose that chart type  
✅ **Still editable** - User can click and modify afterward  

---

## Advanced Workflow: Iterative Refinement

### User can refine charts through conversation

```
User: "Show me sales by product category"
AI:   Creates bar chart with 5 categories

[User clicks the chart]

User: "Can you make this a pie chart instead?"
AI:   Recognizes chart-2 is selected
      Regenerates with chartType: "pie"
      Updates the same chart widget

User: "Show me only the top 3 categories"
AI:   Recognizes chart-2 is selected
      Adds SQL filter: LIMIT 3
      Updates chart with refined data
```

### Chart Re-query

```
[User clicks 3-day-old chart]

AI Chat shows: 
"📊 Selected: Sales by Region
 Last updated: 3 days ago
 Query: 'Show me sales by region for last quarter'"

User: "Refresh this chart"
AI:   Re-executes same NL query
      Gets fresh data
      Updates chart
      Saves new queryTimestamp
```

---

## Data Persistence

### What Gets Saved in Dashboard

When user clicks "Save Dashboard", the following is stored:

```json
{
  "dashboardId": "dash-123",
  "name": "Q4 Sales Analysis",
  "items": [
    {
      "id": "chart-1",
      "chartType": "bar",
      "x": 0, "y": 0,
      "cols": 4, "rows": 3,
      "config": {
        "title": "Sales by Region",
        "naturalLanguageQuery": "Show me sales by region for last quarter",
        "queryTimestamp": "2024-10-02T10:30:00Z",
        "echartsOptions": { /* full config */ },
        "queryMetadata": {
          "sqlQuery": "SELECT region, SUM(sales)...",
          "confidence": 0.95
        }
      }
    }
  ],
  "chatHistory": [
    {
      "sender": "user",
      "content": "Show me sales by region for last quarter",
      "timestamp": "2024-10-02T10:30:00Z",
      "chartReference": "chart-1"
    },
    {
      "sender": "ai",
      "content": "I've updated your bar chart...",
      "timestamp": "2024-10-02T10:30:15Z",
      "chartReference": "chart-1"
    }
  ]
}
```

### What Happens on Dashboard Load

1. Load dashboard JSON from backend
2. Recreate all chart widgets with saved positions
3. Render charts with saved `echartsOptions`
4. Restore chat history in AI Chat panel
5. Data is NOT re-queried (shows cached data)
6. User can click any chart and say "refresh" to re-query

---

## UI Indicators

### Chart Selection State

**Unselected Chart**
```
┌─────────────────────┐
│ Sales by Region     │
│                     │
│   [Bar Chart]       │
│                     │
└─────────────────────┘
```

**Selected Chart (for AI context)**
```
┌═════════════════════╗  ← Blue border
║ Sales by Region     ║
║                     ║
║   [Bar Chart]       ║
║                     ║
║ 🔗 Linked to chat   ║  ← Indicator
╚═════════════════════╝
```

### AI Chat Context Indicator

**No Chart Selected**
```
┌─────────────────────────┐
│ Chat with AI            │
│                         │
│ AI: How can I help?     │
│                         │
│ [Type your message...] │
└─────────────────────────┘
```

**Chart Selected**
```
┌─────────────────────────┐
│ Chat with AI            │
│ ┌─────────────────────┐ │
│ │📊 Bar Chart (4x3)   │ │ ← Context bar
│ │ Sales by Region     │ │
│ └─────────────────────┘ │
│                         │
│ AI: What data would you │
│     like to see?        │
│                         │
│ [Type your message...] │
└─────────────────────────┘
```

---

## Error Handling

### Query Service Errors

**Scenario**: SQL generation fails or query returns no data

```
User: "Show me sales for product XYZ999"
AI:   Query executes but returns 0 rows

Chat Response:
"⚠️ I couldn't find any data for 'product XYZ999'.
 This might mean:
 - The product doesn't exist
 - There are no sales for this product
 - The product code might be incorrect
 
 Would you like to try a different query?"
```

### Invalid Chart Type

**Scenario**: User requests incompatible chart type

```
User: [Selects KPI Card - single metric]
User: "Show me sales by all 50 regions"
AI:   Detects 50 data points won't fit in KPI card

Chat Response:
"⚠️ A KPI Card works best for single values, but your
 query returned 50 regions. Would you like me to:
 
 1. Show total sales across all regions (KPI Card)
 2. Create a bar chart to show all regions
 3. Show top 5 regions only (KPI Cards)?"
```

---

## Summary

| Aspect | Workflow A | Workflow B |
|--------|-----------|-----------|
| **Initiation** | Drag-drop chart | Type in chat |
| **Chart Type** | User decides | AI recommends |
| **Chart Size** | Default or manual | AI recommends |
| **Use Case** | User knows visualization | Exploratory analysis |
| **Backend Constraints** | chartType + size sent | No constraints sent |
| **AI Role** | Data fetching only | Full chart creation |
| **NL Query Storage** | ✅ Yes | ✅ Yes |

Both workflows support:
- Natural language to SQL conversion
- ECharts configuration generation
- Dashboard persistence
- Chart refinement through conversation
- Data refresh on demand

