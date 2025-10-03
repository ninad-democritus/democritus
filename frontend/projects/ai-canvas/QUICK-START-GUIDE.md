# Dashboard Builder - Quick Start Guide

## 🎯 What We're Building

A powerful AI-driven dashboard builder with three panels:
- **Left**: Chart Library (250px) - Drag chart templates to the grid
- **Center**: Dashboard Grid (flexible) - Drop, arrange, and display data-driven charts
- **Right**: AI Chat (350px) - Natural language interface to Query Service backend

### Two Primary Workflows

**Workflow A: Drag-Drop + AI Data Population**
1. User drags chart type from library (e.g., "Bar Chart")
2. Empty chart widget appears on grid
3. User clicks chart and asks AI: "show sales by region"
4. Backend Query Service: NL → SQL → Data → ECharts Config
5. Chart populates with actual data

**Workflow B: Direct AI Chart Creation**
1. User types: "show me revenue trend over time"
2. AI analyzes query → recommends line chart
3. Chart automatically created and populated
4. Natural language query saved for dashboard persistence

## 📦 Required Packages

```bash
npm install angular-gridster2 echarts ngx-echarts --save
```

## 🏗️ Architecture Overview

### Key Technologies
| Technology | Purpose | Why? |
|-----------|---------|------|
| **angular-gridster2** | Grid layout | Most popular, actively maintained, flexible |
| **ECharts + ngx-echarts** | Chart rendering | Rich features, beautiful, performant |
| **Angular CDK Drag-Drop** | Drag & drop | Built-in, lightweight, well-integrated |
| **RxJS + Services** | State management | Simple, no extra dependencies |

### Component Hierarchy
```
DashboardBuilderComponent (Main Page)
├── ChartLibraryComponent (Left Panel)
│   └── Draggable chart type cards
├── DashboardGridComponent (Center Panel)
│   ├── Angular Gridster2
│   └── ChartWidgetComponent (Repeated)
│       └── ECharts instance
└── AIChatComponent (Right Panel)
    ├── Message list
    └── Input box
```

## 🎨 Design Principles

### Layout
```scss
.dashboard-builder {
  display: flex;
  height: calc(100vh - 64px); // Minus header
  
  .chart-library { width: 250px; }
  .dashboard-grid { flex: 1; }
  .ai-chat { width: 350px; }
}
```

### Theme Consistency
- Use Ocean Breeze theme CSS variables
- Match existing card styles and shadows
- Consistent spacing with `--spacing-*`
- Colors from `--color-primary-*` palette

### Responsive Strategy
- **Desktop (>1024px)**: All three panels visible
- **Tablet (768-1024px)**: Narrower panels
- **Mobile (<768px)**: Stack panels, toggle sidebar/chat

## 🚀 Implementation Steps

### Phase 1: Foundation (Start Here)
```bash
# 1. Install dependencies
npm install angular-gridster2 echarts ngx-echarts --save

# 2. Create folder structure
cd frontend/projects/ai-canvas/src/app
mkdir -p pages/dashboard-builder/components/{chart-library,ai-chat,dashboard-grid}
mkdir -p pages/dashboard-builder/components/dashboard-grid/components/chart-widget
mkdir -p models services
```

### Phase 2: Models & Services
Create these files:
- `models/chart-type.model.ts`
- `models/dashboard-item.model.ts`
- `models/chat-message.model.ts`
- `services/chart-data.service.ts`
- `services/ai-chat.service.ts`

### Phase 3: Components
Generate with Angular CLI:
```bash
ng g c pages/dashboard-builder --skip-tests
ng g c pages/dashboard-builder/components/chart-library --skip-tests
ng g c pages/dashboard-builder/components/ai-chat --skip-tests
ng g c pages/dashboard-builder/components/dashboard-grid --skip-tests
ng g c pages/dashboard-builder/components/dashboard-grid/components/chart-widget --skip-tests
```

### Phase 4: Integration
- Add routing
- Connect drag-drop
- Wire up services
- Test data flow

## 📋 Chart Types to Support

### Basic Charts (MVP)
1. **Bar Chart** - Compare categories
2. **Line Chart** - Show trends
3. **Pie Chart** - Display proportions
4. **Table** - Raw data display

### Advanced Charts (Phase 2)
5. **Area Chart** - Filled line chart
6. **Scatter Plot** - Correlation analysis
7. **KPI Card** - Single metric display
8. **Heatmap** - Matrix visualization

## 🎯 Detailed User Workflows

### Workflow A: Drag-Drop First, Then AI Populates Data
```
User Action:      Drag "Bar Chart" → Drop on grid
System:           Empty chart widget created at position
User Action:      Click chart widget (becomes selected)
System:           AI Chat shows: "Chart selected. What data?"
User Action:      Type: "sales by product category"
System:           → Query Service backend
Backend:          NL → SQL → Execute → Generate ECharts config
System:           ← Chart populated with data
Result:           Bar chart showing sales data, NL query saved
```

**Key Point**: User controls chart type/size, AI fetches data

### Workflow B: AI Creates Everything
```
User Action:      Type: "show revenue trend as line chart"
System:           → Query Service backend (no constraints)
Backend:          NL → SQL → Execute → Recommend chart type
Backend:          AI determines: "line" chart, size 6x3
System:           ← New chart auto-created on grid
Result:           Line chart with data, positioned automatically
```

**Key Point**: AI recommends chart type/size based on data

### Workflow C: Iterative Refinement
```
User Action:      Click existing chart
User Action:      Type: "make this a pie chart instead"
System:           → Query Service with new chartType constraint
Backend:          Same SQL, different ECharts config
System:           ← Chart updates to pie chart
Result:           Same data, different visualization
```

### Workflow D: Dashboard Persistence
```
User Action:      Click "Save Dashboard"
System:           Saves all chart configs + NL queries + positions
---
Later...
User Action:      Click "Load Dashboard"
System:           Restores all charts with cached data
User Action:      Click chart → "refresh this"
System:           Re-executes original NL query for fresh data
```

## 🔧 Configuration Examples

### Gridster Config
```typescript
options: GridsterConfig = {
  gridType: GridType.Fit,
  displayGrid: DisplayGrid.OnDragAndResize,
  pushItems: true,
  draggable: { enabled: true },
  resizable: { enabled: true },
  minCols: 12,
  maxCols: 12,
  margin: 16
};
```

### ECharts Bar Chart
```typescript
option = {
  xAxis: { type: 'category', data: ['Mon', 'Tue', 'Wed'] },
  yAxis: { type: 'value' },
  series: [{
    data: [120, 200, 150],
    type: 'bar',
    itemStyle: {
      color: 'var(--color-primary-500)'
    }
  }]
};
```

## 📊 Data Structure with Backend Integration

### Dashboard Item (Persisted)
```typescript
{
  id: 'chart-1',
  chartType: 'bar',
  x: 0, y: 0,
  cols: 4, rows: 3,
  config: {
    title: 'Sales by Region - Q4 2024',
    
    // CRITICAL: Natural language query stored for:
    // 1. Dashboard reload
    // 2. Data refresh
    // 3. User reference
    naturalLanguageQuery: "Show me sales by region for last quarter",
    queryTimestamp: "2024-10-02T10:30:00Z",
    
    // Complete ECharts config from backend
    echartsOptions: {
      xAxis: { type: 'category', data: ['North', 'South', 'East', 'West'] },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: [45000, 38000, 52000, 41000] }]
    },
    
    // Metadata from Query Service
    queryMetadata: {
      sqlQuery: "SELECT region, SUM(sales)...",
      confidence: 0.95,
      recommendedChartType: "bar"
    }
  }
}
```

### Query Service Request
```typescript
{
  naturalLanguageQuery: "Show me sales by region for last quarter",
  
  // Optional: from Workflow A (drag-drop first)
  constraints: {
    chartType: "bar",
    chartSize: { cols: 4, rows: 3 },
    position: { x: 0, y: 0 }
  },
  
  // Optional: for better AI context
  context: {
    dashboardId: "dash-123",
    existingCharts: [
      { type: "line", title: "Revenue Trend", query: "monthly revenue" }
    ]
  }
}
```

### Query Service Response
```typescript
{
  success: true,
  data: [
    { region: "North", sales: 45000 },
    { region: "South", sales: 38000 },
    { region: "East", sales: 52000 },
    { region: "West", sales: 41000 }
  ],
  chartConfig: {
    type: "bar",  // Respects constraint or AI recommends
    title: "Sales by Region - Q4 2024",
    echartsOptions: { /* complete config */ },
    size: { cols: 4, rows: 3 }  // Respects constraint or AI recommends
  },
  metadata: {
    sqlQuery: "SELECT region, SUM(sales) FROM sales_data WHERE quarter = 'Q4' AND year = 2024 GROUP BY region",
    dataSchema: { region: "string", sales: "number" },
    recommendedChartType: "bar",
    confidence: 0.95
  },
  naturalLanguageQuery: "Show me sales by region for last quarter"  // Echo back
}
```

## 🎨 Styling Reference

### Colors (Ocean Breeze Theme)
- **Primary**: `#14b8a6` (Teal)
- **Accent**: `#f97316` (Orange)
- **Background**: `#f8fafc` (Blue-gray 50)
- **Card**: `#ffffff`
- **Border**: `#e2e8f0` (Blue-gray 200)
- **Text**: `#0f172a` (Blue-gray 900)

### Shadows
- Card: `var(--shadow-card)`
- Hover: `var(--shadow-card-hover)`
- Modal: `var(--shadow-modal)`

### Spacing
- xs: 4px
- sm: 8px
- md: 12px
- lg: 16px
- xl: 24px
- 2xl: 32px

## ⚡ Performance Tips

1. Use `ChangeDetectionStrategy.OnPush`
2. Add `trackBy` to all `*ngFor`
3. Lazy load chart data
4. Debounce grid resize events
5. Use async pipe for observables

## 🧪 Testing Checklist

- [ ] Chart library displays all chart types
- [ ] Dragging chart shows visual feedback
- [ ] Dropping chart creates widget on grid
- [ ] Grid items can be resized
- [ ] Grid items can be repositioned
- [ ] Chat sends messages
- [ ] AI responds to messages
- [ ] Charts render correctly
- [ ] Layout responsive on mobile
- [ ] Dashboard persists on refresh

## 📚 Additional Resources

- [Angular Gridster2 Docs](https://tiberiuzuld.github.io/angular-gridster2/)
- [ECharts Examples](https://echarts.apache.org/examples/en/index.html)
- [Angular CDK Drag-Drop](https://material.angular.io/cdk/drag-drop/overview)

## 🎯 Success Criteria

### MVP Complete When:
✅ User can drag charts from library to grid  
✅ User can resize and reposition charts  
✅ User can chat with AI  
✅ At least 3 chart types render correctly  
✅ Layout is responsive  
✅ Theme matches Ocean Breeze  

### Production Ready When:
✅ All 8 chart types supported  
✅ Charts connect to real data sources  
✅ AI generates working chart configs  
✅ Dashboard save/load implemented  
✅ Full test coverage  
✅ Performance optimized  

## 🚦 Getting Started Now

1. **Review Documentation**
   - Technical design: `DASHBOARD-BUILDER-DESIGN.md`
   - Implementation plan: `IMPLEMENTATION-PLAN.md`
   - User workflows: `WORKFLOWS.md` ← **NEW** - Detailed workflow diagrams

2. **Install Dependencies**
   ```bash
   npm install angular-gridster2 echarts ngx-echarts --save
   ```

3. **Coordinate with Backend Team**
   - Query Service API endpoint: `POST /api/v1/query-service/generate-chart`
   - Request/response format documented in `DASHBOARD-BUILDER-DESIGN.md`
   - Backend handles: NL parsing, SQL generation, ECharts config creation

4. **Create Folder Structure**
   ```bash
   cd frontend/projects/ai-canvas/src/app
   mkdir -p pages/dashboard-builder/components/{chart-library,ai-chat,dashboard-grid}
   mkdir -p models services
   ```

5. **Implementation Order**
   - Models (including Query Service models)
   - Services (Chart Data, AI Chat, Query Service client)
   - Chart Library component (drag source)
   - Dashboard Grid component (drop target + chart widgets)
   - AI Chat component (backend integration)
   - Chart selection mechanism
   - Dashboard persistence

**Estimated Timeline**: 
- Frontend MVP (mock backend): 2 weeks
- Backend Query Service: 2-3 weeks (parallel development)
- Full integration: 3-4 weeks total

---

**Questions?** Refer to the detailed design documents or ask for clarification on specific components.

