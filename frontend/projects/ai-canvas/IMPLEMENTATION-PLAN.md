# Dashboard Builder - Implementation Plan

## Quick Reference

### Layout Specifications
```
┌─────────────────────────────────────────────────────────────────┐
│  App Header (from shared-ui)                                    │
├────────┬────────────────────────────────────────┬───────────────┤
│        │                                        │               │
│ Chart  │      Dashboard Grid                    │   AI Chat     │
│ Library│      (Angular Gridster2)               │   Panel       │
│        │                                        │               │
│ 250px  │      Flexible Width                    │   350px       │
│        │      (calc(100vw - 600px))            │               │
│        │                                        │               │
│ ┌────┐ │  ┌──────┐  ┌──────┐  ┌──────┐        │ ┌───────────┐ │
│ │Bar │ │  │Chart │  │Chart │  │Chart │        │ │ AI: Hello │ │
│ │Chart│ │  │  1   │  │  2   │  │  3   │        │ └───────────┘ │
│ └────┘ │  └──────┘  └──────┘  └──────┘        │               │
│        │                                        │ ┌───────────┐ │
│ ┌────┐ │  ┌──────┐  ┌─────────────────┐       │ │User: Create│ │
│ │Line│ │  │Chart │  │    Chart 5       │       │ │a bar chart│ │
│ │Chart│ │  │  4   │  │   (2x size)     │       │ └───────────┘ │
│ └────┘ │  └──────┘  └─────────────────┘       │               │
│        │                                        │ [Input Box  ]│
│ ┌────┐ │                                        │ [Send Button]│
│ │Pie │ │                                        │               │
│ └────┘ │                                        │               │
└────────┴────────────────────────────────────────┴───────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Layout | CSS Flexbox | Three-column layout |
| Drag & Drop | Angular CDK | Drag charts from library |
| Grid System | angular-gridster2 | Responsive dashboard grid |
| Charts | ngx-echarts + ECharts | Chart rendering |
| State Management | RxJS + Services | Data flow |
| Styling | SCSS + CSS Variables | Theme consistency |

## Step-by-Step Implementation Guide

### Step 1: Install Dependencies

```bash
cd frontend
npm install angular-gridster2 echarts ngx-echarts --save
```

### Step 2: Create Folder Structure

```bash
# From frontend/projects/ai-canvas/src/app/
mkdir -p pages/dashboard-builder/components/{chart-library,ai-chat,dashboard-grid}/models
mkdir -p pages/dashboard-builder/components/dashboard-grid/components/chart-widget
mkdir -p services
mkdir -p models
```

### Step 3: Create Model Files

Create these interfaces in `models/` directory:

**chart-type.model.ts**
```typescript
export interface ChartType {
  id: string;
  name: string;
  icon: string;
  category: 'basic' | 'advanced' | 'statistical';
  description: string;
  defaultSize: { cols: number; rows: number };
}
```

**dashboard-item.model.ts**
```typescript
export interface DashboardItem {
  id: string;
  chartType: ChartType;
  x: number;
  y: number;
  cols: number;
  rows: number;
  config: ChartConfig;
}

export interface ChartConfig {
  title: string;
  dataSource?: string;
  options: any;
}
```

**chat-message.model.ts**
```typescript
export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: Date;
  chartSuggestion?: ChartType;
}
```

### Step 4: Create Services

**services/chart-data.service.ts**
- Manages dashboard items
- Provides observables for reactive updates
- Handles CRUD operations on charts

**services/ai-chat.service.ts**
- Manages chat messages
- Communicates with AI backend (mock initially)
- Generates chart suggestions

### Step 5: Create Components

#### Main Container
**pages/dashboard-builder/dashboard-builder.component.ts**
- Orchestrates the three panels
- Handles drag-drop coordination
- Manages overall state

#### Left Panel
**components/chart-library/chart-library.component.ts**
- Displays available chart types
- Implements drag source
- Categorizes charts

#### Right Panel
**components/ai-chat/ai-chat.component.ts**
- Chat message display
- Input handling
- AI interaction

#### Center Panel
**components/dashboard-grid/dashboard-grid.component.ts**
- Gridster integration
- Drop zone implementation
- Grid item management

**components/dashboard-grid/components/chart-widget/chart-widget.component.ts**
- Individual chart rendering
- Chart configuration
- Edit/delete actions

### Step 6: Implement Drag & Drop

1. Add `DragDropModule` from `@angular/cdk/drag-drop` to imports
2. Make chart library items draggable with `cdkDrag`
3. Make grid a drop zone with `cdkDropList`
4. Handle `cdkDropped` event to create new dashboard items

### Step 7: Configure Angular Gridster2

In `dashboard-grid.component.ts`:
```typescript
options: GridsterConfig = {
  gridType: GridType.Fit,
  displayGrid: DisplayGrid.OnDragAndResize,
  pushItems: true,
  swap: false,
  draggable: { enabled: true },
  resizable: { enabled: true },
  minCols: 12,
  maxCols: 12,
  margin: 16,
  outerMargin: true
};
```

### Step 8: Style Components

Each component should have its own `.scss` file using:
- CSS variables from theme
- BEM naming convention
- Consistent spacing and shadows

Key theme variables to use:
- `--bg-card`: Card backgrounds
- `--border-light`: Borders
- `--shadow-card`: Shadows
- `--text-primary`: Primary text
- `--color-primary-500`: Accent colors
- `--spacing-*`: Spacing units

### Step 9: Add Routing

Update `app-routing.module.ts`:
```typescript
const routes: Routes = [
  { path: '', redirectTo: '/dashboard-builder', pathMatch: 'full' },
  { path: 'dashboard-builder', component: DashboardBuilderComponent }
];
```

### Step 10: Integrate ECharts

1. Import `NgxEchartsModule` in component/module
2. Configure ECharts options for each chart type
3. Create chart renderers in chart-widget component
4. Use `echarts` instance for dynamic updates

## Component Communication Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                  Dashboard Builder (Parent Component)                 │
│                                                                        │
│  ┌──────────────┐  ┌─────────────────────┐  ┌─────────────────┐    │
│  │Chart Library │  │  Dashboard Grid     │  │   AI Chat       │    │
│  │              │  │                     │  │                 │    │
│  │  Drag ───────┼─>│  Drop creates chart │<─│  Sends query    │    │
│  │              │  │                     │  │  to backend     │    │
│  │              │  │  Click chart ───────┼─>│  Sets context   │    │
│  └──────────────┘  └─────────────────────┘  └─────────────────┘    │
│                              │                         │              │
└──────────────────────────────┼─────────────────────────┼──────────────┘
                               │                         │
                               ▼                         ▼
                    ┌──────────────────┐    ┌──────────────────┐
                    │ ChartDataService │    │  AIChatService   │
                    │                  │    │                  │
                    │ - dashboardItems$│◄───┤ - messages$      │
                    │ - selectedChart$ │    │ - sendMessage()  │
                    │ - addChart()     │    └────────┬─────────┘
                    │ - selectChart()  │             │
                    │ - updateFromAI() │             │
                    └──────────────────┘             │
                                                     ▼
                                          ┌─────────────────────┐
                                          │   Query Service     │
                                          │   (Backend API)     │
                                          │                     │
                                          │ - NL to SQL         │
                                          │ - LLM generates     │
                                          │   ECharts config    │
                                          │ - Returns data      │
                                          └─────────────────────┘
```

### Workflow A: Drag-Drop + AI Data Population
1. User drags chart from library → drops on grid
2. Empty chart widget created
3. User clicks chart widget → becomes "selected"
4. Selected chart ID stored in ChartDataService
5. AI Chat shows: "Chart selected. What data would you like to see?"
6. User types: "show sales by region"
7. AI Chat sends request with chart type/size constraints
8. Query Service returns data + ECharts config
9. Chart widget updates with data

### Workflow B: Direct AI Query
1. User types in chat: "show me revenue trend as line chart"
2. AI Chat sends request without constraints
3. Query Service returns data + recommended chart type/size
4. New chart automatically added to grid
5. Natural language query saved with chart config

## File Checklist

### Models
- [ ] `models/chart-type.model.ts`
- [ ] `models/dashboard-item.model.ts`
- [ ] `models/chat-message.model.ts`
- [ ] `models/query-service.model.ts` (Request/Response interfaces)

### Services
- [ ] `services/chart-data.service.ts` (with selection tracking)
- [ ] `services/ai-chat.service.ts` (with Query Service integration)
- [ ] `services/query.service.ts` (HTTP client for backend API)

### Components
- [ ] `pages/dashboard-builder/dashboard-builder.component.{ts,html,scss}`
- [ ] `pages/dashboard-builder/components/chart-library/chart-library.component.{ts,html,scss}`
- [ ] `pages/dashboard-builder/components/ai-chat/ai-chat.component.{ts,html,scss}`
- [ ] `pages/dashboard-builder/components/dashboard-grid/dashboard-grid.component.{ts,html,scss}`
- [ ] `pages/dashboard-builder/components/dashboard-grid/components/chart-widget/chart-widget.component.{ts,html,scss}`

### Configuration
- [ ] Update `app-routing.module.ts`
- [ ] Update `app.module.ts` with new imports

## Mock Data for Development

### Chart Types
```typescript
const CHART_TYPES: ChartType[] = [
  {
    id: 'bar',
    name: 'Bar Chart',
    icon: 'chart-bar',
    category: 'basic',
    description: 'Compare values across categories',
    defaultSize: { cols: 4, rows: 3 }
  },
  {
    id: 'line',
    name: 'Line Chart',
    icon: 'chart-line',
    category: 'basic',
    description: 'Show trends over time',
    defaultSize: { cols: 6, rows: 3 }
  },
  {
    id: 'pie',
    name: 'Pie Chart',
    icon: 'chart-pie',
    category: 'basic',
    description: 'Show proportions',
    defaultSize: { cols: 4, rows: 3 }
  }
  // Add more chart types...
];
```

## Development Order

1. **Day 1-2**: Setup + Models + Services
   - Install dependencies
   - Create folder structure
   - Implement models
   - Create service skeletons

2. **Day 3-4**: Chart Library Component
   - Build UI
   - Add chart type data
   - Implement drag functionality

3. **Day 5-6**: Dashboard Grid Component
   - Integrate Gridster
   - Create chart widget
   - Implement drop handling

4. **Day 7-8**: AI Chat Component
   - Build chat UI
   - Message display
   - Input handling

5. **Day 9-10**: Integration
   - Connect all components
   - Data flow implementation
   - State management

6. **Day 11-12**: Chart Rendering
   - ECharts integration
   - Chart type renderers
   - Configuration UI

7. **Day 13-14**: Polish
   - Responsive design
   - Animations
   - Error handling
   - Testing

## Testing Strategy

### Unit Tests
- Service methods (add/remove/update charts)
- Model validations
- Utility functions

### Component Tests
- Component rendering
- Event emission
- Input/Output bindings

### Integration Tests
- Drag-drop workflow
- Chart creation flow
- AI chat integration

### E2E Tests
- Complete user journey
- Dashboard save/load
- Responsive behavior

## Performance Optimization

1. **ChangeDetectionStrategy.OnPush** for all components
2. **trackBy** functions for *ngFor loops
3. **Async pipe** for observables
4. **Lazy loading** for chart data
5. **Virtual scrolling** if chart library grows

## Responsive Breakpoints

| Breakpoint | Behavior |
|------------|----------|
| < 768px (Mobile) | Stack panels, hide library/chat by default |
| 768px - 1024px (Tablet) | Reduce panel widths |
| > 1024px (Desktop) | Full layout as designed |

## Next Steps After Approval

1. Run dependency installation
2. Generate component scaffolding with Angular CLI
3. Create initial models and services
4. Begin component implementation following the order above

Would you like me to proceed with the implementation?

