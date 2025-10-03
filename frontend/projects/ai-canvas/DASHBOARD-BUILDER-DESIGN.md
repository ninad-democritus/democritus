# Dashboard Builder - Technical Design Document

## Overview
The Dashboard Builder is a feature within the AI Canvas app that allows users to create interactive dashboards by:
- Selecting charts from a library and dragging them to a grid
- Interacting with an AI chat assistant to generate charts
- Arranging charts in a responsive grid layout

## Architecture

### Component Structure

```
ai-canvas/
└── src/app/
    ├── pages/
    │   └── dashboard-builder/
    │       ├── dashboard-builder.component.ts
    │       ├── dashboard-builder.component.html
    │       ├── dashboard-builder.component.scss
    │       └── components/
    │           ├── chart-library/
    │           │   ├── chart-library.component.ts
    │           │   ├── chart-library.component.html
    │           │   ├── chart-library.component.scss
    │           │   └── models/
    │           │       └── chart-type.model.ts
    │           ├── ai-chat/
    │           │   ├── ai-chat.component.ts
    │           │   ├── ai-chat.component.html
    │           │   ├── ai-chat.component.scss
    │           │   └── models/
    │           │       └── chat-message.model.ts
    │           └── dashboard-grid/
    │               ├── dashboard-grid.component.ts
    │               ├── dashboard-grid.component.html
    │               ├── dashboard-grid.component.scss
    │               ├── components/
    │               │   ├── chart-widget/
    │               │   │   ├── chart-widget.component.ts
    │               │   │   ├── chart-widget.component.html
    │               │   │   └── chart-widget.component.scss
    │               └── models/
    │                   └── dashboard-item.model.ts
    └── services/
        ├── chart-data.service.ts
        └── ai-chat.service.ts
```

## Component Specifications

### 1. Dashboard Builder (Main Container)

**Responsibility**: Main page component that coordinates the three panels

**Layout**:
- CSS Grid or Flexbox layout with three columns
- Header from shared-ui at the top
- No routing initially (can be added later)
- Full viewport height minus header

**File**: `dashboard-builder.component.ts`
```typescript
@Component({
  selector: 'app-dashboard-builder',
  templateUrl: './dashboard-builder.component.html',
  styleUrl: './dashboard-builder.component.scss'
})
```

### 2. Chart Library Component (Left Panel)

**Dimensions**: 
- Width: 250px max
- Height: 100vh (minus header)
- No gap with sidebar

**Features**:
- List of available chart types
- Draggable chart cards
- Search/filter functionality (future)
- Collapsible sections by category

**Chart Types**:
- Bar Chart
- Line Chart
- Pie Chart
- Area Chart
- Scatter Plot
- Table
- KPI Card
- Heatmap

**Drag Implementation**: 
- Use Angular CDK Drag & Drop
- Each chart type card is draggable
- Preview on drag

**File**: `chart-library.component.ts`

### 3. AI Chat Component (Right Panel)

**Dimensions**:
- Width: 350px max
- Height: 100vh (minus header)
- Touch right edge of viewport

**Layout**:
- Header: "Chat with AI" title
- Body: Chat message list (auto-scroll to bottom)
- Footer: Input textbox with send button

**Chat Library Recommendation**: 
**Option 1 (Recommended)**: Build custom component
- More control over styling
- Matches theme perfectly
- Lightweight
- Use CSS flexbox for layout

**Option 2**: Use existing library (if needed)
- `@ctrl/ngx-emoji-mart` for emoji support
- `ngx-markdown` for markdown rendering in messages

**Features**:
- Message bubbles (user vs AI)
- Timestamp display
- Auto-scroll to latest message
- Loading indicator for AI responses
- Message history persistence

**File**: `ai-chat.component.ts`

### 4. Dashboard Grid Component (Center Panel)

**Dimensions**:
- Width: calc(100% - 250px - 350px)
- Height: 100vh (minus header)
- Responsive to window resize

**Grid Library Recommendation**:
**angular-gridster2** - Most popular and actively maintained
```bash
npm install angular-gridster2 --save
```

**Grid Configuration**:
```typescript
{
  gridType: 'fit',
  displayGrid: 'onDrag&Resize',
  pushItems: true,
  swap: false,
  draggable: {
    enabled: true
  },
  resizable: {
    enabled: true
  },
  minCols: 12,
  maxCols: 12,
  minRows: 1,
  margin: 16,
  outerMargin: true,
  mobileBreakpoint: 640
}
```

**Chart Widget**:
- Reusable component to display individual charts
- Takes chart type and configuration as input
- Toolbar with edit/delete actions
- Chart rendering using a charting library

**File**: `dashboard-grid.component.ts`

## Data Models

### Chart Type Model
```typescript
export interface ChartType {
  id: string;
  name: string;
  icon: string; // SVG icon or icon class
  category: 'basic' | 'advanced' | 'statistical';
  description: string;
  defaultSize: { cols: number; rows: number };
}
```

### Dashboard Item Model
```typescript
export interface DashboardItem {
  id: string;
  chartType: ChartType;
  x: number;
  y: number;
  cols: number;
  rows: number;
  config: ChartConfig;
  isSelected?: boolean; // For chat context
}

export interface ChartConfig {
  title: string;
  naturalLanguageQuery?: string; // CRITICAL: Store user's NL query for persistence
  queryTimestamp?: Date; // When the query was executed
  dataSource?: string;
  echartsOptions: any; // ECharts configuration from backend
  queryMetadata?: QueryMetadata; // Additional info from Query Service
}

export interface QueryMetadata {
  sqlQuery?: string; // Generated SQL (for debugging/transparency)
  dataSchema?: any; // Schema of returned data
  recommendedChartType?: string; // AI's recommendation if user didn't specify
  confidence?: number; // AI confidence in the result
}
```

### Chat Message Model
```typescript
export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: Date;
  chartReference?: string; // ID of chart this message relates to
  chartSuggestion?: ChartGenerationResult; // Full result from Query Service
  queryInProgress?: boolean; // Show loading state
}
```

### Query Service Models
```typescript
// Request to Query Service
export interface ChartGenerationRequest {
  naturalLanguageQuery: string;
  
  // Optional constraints from existing chart or user preference
  constraints?: {
    chartType?: string; // 'bar', 'line', 'pie', etc.
    chartSize?: { cols: number; rows: number };
    position?: { x: number; y: number };
  };
  
  // Context for better AI understanding
  context?: {
    dashboardId?: string;
    existingCharts?: Array<{ type: string; title: string; query: string }>;
  };
}

// Response from Query Service
export interface ChartGenerationResult {
  success: boolean;
  data: any[]; // Actual data from DB
  chartConfig: {
    type: string; // Recommended or specified chart type
    title: string; // Generated title
    echartsOptions: any; // Complete ECharts configuration
    size?: { cols: number; rows: number }; // Recommended size
  };
  metadata: QueryMetadata;
  naturalLanguageQuery: string; // Echo back for storage
  error?: string;
}
```

## Charting Library

**Recommendation**: **Apache ECharts** (via `ngx-echarts`)
- Highly performant
- Rich chart types
- Beautiful default themes
- Good Angular integration
- Free and open source

**Installation**:
```bash
npm install echarts ngx-echarts --save
```

**Alternative**: Chart.js with ng2-charts (simpler but less features)

## State Management

For MVP, use **Angular Services** with RxJS:

### Chart Data Service
```typescript
@Injectable({ providedIn: 'root' })
export class ChartDataService {
  private dashboardItemsSubject = new BehaviorSubject<DashboardItem[]>([]);
  dashboardItems$ = this.dashboardItemsSubject.asObservable();
  
  private selectedChartIdSubject = new BehaviorSubject<string | null>(null);
  selectedChartId$ = this.selectedChartIdSubject.asObservable();
  
  addChart(item: DashboardItem): void;
  removeChart(id: string): void;
  updateChart(id: string, updates: Partial<DashboardItem>): void;
  
  // NEW: Chart selection for AI context
  selectChart(id: string | null): void;
  getSelectedChart(): DashboardItem | null;
  
  // NEW: Update chart with AI-generated config
  updateChartFromAI(id: string, result: ChartGenerationResult): void;
  
  saveDashboard(dashboardId: string): Observable<void>;
  loadDashboard(dashboardId: string): Observable<DashboardItem[]>;
}
```

### Query Service Client
```typescript
@Injectable({ providedIn: 'root' })
export class QueryService {
  private apiUrl = '/api/v1/query-service';
  
  constructor(private http: HttpClient) {}
  
  /**
   * Generate chart from natural language query
   * Workflow A: With existing chart context
   * Workflow B: Without context (AI recommends everything)
   */
  generateChart(request: ChartGenerationRequest): Observable<ChartGenerationResult> {
    return this.http.post<ChartGenerationResult>(
      `${this.apiUrl}/generate-chart`,
      request
    ).pipe(
      catchError(this.handleError)
    );
  }
  
  /**
   * Regenerate chart with different constraints
   */
  regenerateChart(
    originalQuery: string,
    newConstraints: ChartGenerationRequest['constraints']
  ): Observable<ChartGenerationResult> {
    return this.generateChart({ 
      naturalLanguageQuery: originalQuery, 
      constraints: newConstraints 
    });
  }
  
  private handleError(error: any): Observable<never> {
    console.error('Query Service Error:', error);
    return throwError(() => new Error(error.message || 'Query service failed'));
  }
}
```

### AI Chat Service
```typescript
@Injectable({ providedIn: 'root' })
export class AIChatService {
  private messagesSubject = new BehaviorSubject<ChatMessage[]>([]);
  messages$ = this.messagesSubject.asObservable();
  
  constructor(
    private queryService: QueryService,
    private chartDataService: ChartDataService
  ) {}
  
  /**
   * Send user message and get AI response
   * Handles both workflows:
   * - With selected chart (Workflow A)
   * - Without selected chart (Workflow B)
   */
  sendMessage(content: string): Observable<ChatMessage> {
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: this.generateId(),
      sender: 'user',
      content,
      timestamp: new Date()
    };
    this.addMessage(userMessage);
    
    // Get selected chart context if any
    const selectedChart = this.chartDataService.getSelectedChart();
    
    // Prepare request
    const request: ChartGenerationRequest = {
      naturalLanguageQuery: content,
      constraints: selectedChart ? {
        chartType: selectedChart.chartType.id,
        chartSize: { 
          cols: selectedChart.cols, 
          rows: selectedChart.rows 
        },
        position: { x: selectedChart.x, y: selectedChart.y }
      } : undefined
    };
    
    // Add loading message
    const loadingMessage: ChatMessage = {
      id: this.generateId(),
      sender: 'ai',
      content: 'Analyzing your query...',
      timestamp: new Date(),
      queryInProgress: true,
      chartReference: selectedChart?.id
    };
    this.addMessage(loadingMessage);
    
    // Call Query Service
    return this.queryService.generateChart(request).pipe(
      tap(result => {
        // Remove loading message
        this.removeMessage(loadingMessage.id);
        
        // Add AI response
        const aiMessage: ChatMessage = {
          id: this.generateId(),
          sender: 'ai',
          content: this.generateResponseText(result, selectedChart),
          timestamp: new Date(),
          chartSuggestion: result,
          chartReference: selectedChart?.id
        };
        this.addMessage(aiMessage);
        
        // Update chart or create new one
        if (selectedChart) {
          // Workflow A: Update existing chart
          this.chartDataService.updateChartFromAI(selectedChart.id, result);
        } else {
          // Workflow B: Create new chart
          this.createChartFromAI(result);
        }
      }),
      catchError(error => {
        this.removeMessage(loadingMessage.id);
        const errorMessage: ChatMessage = {
          id: this.generateId(),
          sender: 'ai',
          content: `Sorry, I encountered an error: ${error.message}`,
          timestamp: new Date()
        };
        this.addMessage(errorMessage);
        return throwError(() => error);
      })
    );
  }
  
  private generateResponseText(
    result: ChartGenerationResult, 
    selectedChart?: DashboardItem | null
  ): string {
    if (selectedChart) {
      return `I've updated your ${result.chartConfig.type} chart with the requested data. 
              The query returned ${result.data.length} records.`;
    } else {
      return `I've created a ${result.chartConfig.type} chart for you with ${result.data.length} records. 
              ${result.metadata.recommendedChartType ? 
                `I recommended this chart type based on your data.` : ''}`;
    }
  }
  
  private createChartFromAI(result: ChartGenerationResult): void {
    const newItem: DashboardItem = {
      id: this.generateId(),
      chartType: this.getChartType(result.chartConfig.type),
      x: 0,
      y: 0,
      cols: result.chartConfig.size?.cols || 4,
      rows: result.chartConfig.size?.rows || 3,
      config: {
        title: result.chartConfig.title,
        naturalLanguageQuery: result.naturalLanguageQuery,
        queryTimestamp: new Date(),
        echartsOptions: result.chartConfig.echartsOptions,
        queryMetadata: result.metadata
      }
    };
    this.chartDataService.addChart(newItem);
  }
  
  private addMessage(message: ChatMessage): void {
    const messages = this.messagesSubject.value;
    this.messagesSubject.next([...messages, message]);
  }
  
  private removeMessage(id: string): void {
    const messages = this.messagesSubject.value.filter(m => m.id !== id);
    this.messagesSubject.next(messages);
  }
  
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  
  private getChartType(typeId: string): ChartType {
    // Implementation to get ChartType from registry
    return CHART_TYPES.find(ct => ct.id === typeId) || CHART_TYPES[0];
  }
}
```

## Drag & Drop Flow

1. **User drags chart from library**:
   - `cdkDragStarted` event fires
   - Visual feedback shows dragging state
   
2. **User drops chart on grid**:
   - `cdkDropped` event fires
   - Calculate grid position from drop coordinates
   - Create new `DashboardItem` with default configuration
   - Add to `ChartDataService`
   
3. **Grid updates**:
   - Subscribe to `dashboardItems$` observable
   - Gridster automatically arranges items
   - Chart widget renders based on type

## Styling Approach

### Theme Consistency
- Use CSS variables from Ocean Breeze theme
- Match existing card styles
- Consistent spacing using `--spacing-*` variables
- Use `--shadow-card` for elevations

### Responsive Behavior
- Left panel: Collapsible on mobile (< 768px)
- Right panel: Toggle on/off with floating button on mobile
- Grid: Full width on mobile with panels hidden

### Key CSS Classes
```scss
.dashboard-builder {
  display: flex;
  height: calc(100vh - var(--header-height, 64px));
  background: var(--bg-page-solid);
}

.chart-library {
  width: 250px;
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
  overflow-y: auto;
}

.ai-chat {
  width: 350px;
  background: var(--bg-card);
  border-left: 1px solid var(--border-light);
  overflow: hidden;
}

.dashboard-grid {
  flex: 1;
  overflow: auto;
  padding: var(--spacing-xl);
}
```

## Implementation Phases

### Phase 1: Core Structure (Week 1)
- [ ] Create component structure
- [ ] Implement main layout with three panels
- [ ] Install and configure angular-gridster2
- [ ] Basic styling matching theme

### Phase 2: Chart Library (Week 1-2)
- [ ] Define chart type models
- [ ] Create chart type data/configuration
- [ ] Implement chart library UI
- [ ] Add drag functionality with Angular CDK

### Phase 3: Dashboard Grid (Week 2)
- [ ] Configure gridster options
- [ ] Implement drop zone
- [ ] Create chart widget component
- [ ] Add chart rendering (placeholder first)

### Phase 4: AI Chat (Week 2-3)
- [ ] Create chat UI components
- [ ] Implement message display
- [ ] Add input handling
- [ ] Create AI chat service (mock initially)

### Phase 5: Integration (Week 3)
- [ ] Connect drag-drop to grid
- [ ] Integrate AI suggestions with grid
- [ ] Add chart editing capabilities
- [ ] Implement save/load dashboard

### Phase 6: Chart Rendering (Week 3-4)
- [ ] Install and configure ECharts
- [ ] Implement chart renderers for each type
- [ ] Connect to data sources
- [ ] Add chart configuration UI

### Phase 7: Polish (Week 4)
- [ ] Responsive design
- [ ] Animations and transitions
- [ ] Error handling
- [ ] Loading states
- [ ] Documentation

## Dependencies to Install

```bash
# Grid
npm install angular-gridster2 --save

# Drag & Drop (already included in Angular)
# @angular/cdk

# Charts
npm install echarts ngx-echarts --save

# Optional: Markdown support for chat
npm install ngx-markdown --save
```

## Routing Configuration

Add route to `app-routing.module.ts`:
```typescript
const routes: Routes = [
  { 
    path: '', 
    redirectTo: '/dashboard-builder', 
    pathMatch: 'full' 
  },
  { 
    path: 'dashboard-builder', 
    component: DashboardBuilderComponent 
  }
];
```

## API Endpoints

### Query Service (To Be Developed)

```
POST   /api/v1/query-service/generate-chart
```

**Request:**
```json
{
  "naturalLanguageQuery": "Show me sales by region for last quarter",
  "constraints": {
    "chartType": "bar",
    "chartSize": { "cols": 4, "rows": 3 },
    "position": { "x": 0, "y": 0 }
  },
  "context": {
    "dashboardId": "dash-123",
    "existingCharts": [
      {
        "type": "line",
        "title": "Revenue Trend",
        "query": "monthly revenue over time"
      }
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    { "region": "North", "sales": 45000 },
    { "region": "South", "sales": 38000 },
    { "region": "East", "sales": 52000 },
    { "region": "West", "sales": 41000 }
  ],
  "chartConfig": {
    "type": "bar",
    "title": "Sales by Region - Q4 2024",
    "echartsOptions": {
      "xAxis": { "type": "category", "data": ["North", "South", "East", "West"] },
      "yAxis": { "type": "value", "name": "Sales ($)" },
      "series": [{
        "name": "Sales",
        "type": "bar",
        "data": [45000, 38000, 52000, 41000],
        "itemStyle": { "color": "#14b8a6" }
      }],
      "tooltip": { "trigger": "axis" },
      "grid": { "left": "10%", "right": "10%", "bottom": "15%", "top": "15%" }
    },
    "size": { "cols": 4, "rows": 3 }
  },
  "metadata": {
    "sqlQuery": "SELECT region, SUM(sales) as sales FROM sales_data WHERE quarter = 'Q4' AND year = 2024 GROUP BY region",
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

### Dashboard Persistence

```
GET    /api/v1/dashboards          - List user's dashboards
GET    /api/v1/dashboards/:id      - Get dashboard with all configs
POST   /api/v1/dashboards          - Create new dashboard
PUT    /api/v1/dashboards/:id      - Update dashboard (save layout + NL queries)
DELETE /api/v1/dashboards/:id      - Delete dashboard
```

**Dashboard Save Payload:**
```json
{
  "id": "dash-123",
  "name": "Q4 Sales Dashboard",
  "description": "Quarterly sales analysis",
  "items": [
    {
      "id": "chart-1",
      "chartType": { "id": "bar", "name": "Bar Chart", ... },
      "x": 0,
      "y": 0,
      "cols": 4,
      "rows": 3,
      "config": {
        "title": "Sales by Region",
        "naturalLanguageQuery": "Show me sales by region for last quarter",
        "queryTimestamp": "2024-10-02T10:30:00Z",
        "echartsOptions": { ... },
        "queryMetadata": {
          "sqlQuery": "SELECT ...",
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
    }
  ],
  "createdAt": "2024-10-02T10:00:00Z",
  "updatedAt": "2024-10-02T10:30:00Z"
}
```

## Testing Strategy

- Unit tests for services
- Component tests for UI components
- E2E tests for drag-drop workflow
- Visual regression tests for chart rendering

## Performance Considerations

1. **Virtual Scrolling**: For chart library if list grows large
2. **Lazy Loading**: Load chart data only when widget is visible
3. **Debouncing**: For chat input and grid resize events
4. **Memoization**: Cache chart configurations
5. **Web Workers**: For heavy chart calculations (if needed)

## Accessibility

- Keyboard navigation for chart library
- ARIA labels for drag-drop actions
- Focus management for chat input
- Screen reader announcements for AI responses
- Keyboard shortcuts for common actions

## Next Steps

1. Review and approve this design
2. Install required dependencies
3. Create component scaffolding
4. Begin Phase 1 implementation

