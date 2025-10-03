# AI Canvas Dashboard Builder - Complete Documentation Index

## 📚 Documentation Overview

This folder contains complete technical specifications for the AI-powered Dashboard Builder feature. Start here for navigation.

---

## 🎯 Start Here

### For Product Managers / Stakeholders
**Read First**: [`WORKFLOWS.md`](./WORKFLOWS.md)
- Visual workflow diagrams
- User journey examples
- UI mockups and interactions
- Feature demonstrations

### For Frontend Developers
**Read First**: [`QUICK-START-GUIDE.md`](./QUICK-START-GUIDE.md)
- Quick overview and setup
- Technology stack decisions
- Installation instructions
- Code examples

**Then**: [`IMPLEMENTATION-PLAN.md`](./IMPLEMENTATION-PLAN.md)
- Step-by-step development guide
- Component structure
- File checklist
- Development timeline

### For Backend Developers
**Read First**: [`BACKEND-API-SPEC.md`](./BACKEND-API-SPEC.md)
- Complete API specification
- Request/response examples
- LLM requirements
- Chart generation logic
- Error handling
- Testing requirements

### For System Architects
**Read First**: [`DASHBOARD-BUILDER-DESIGN.md`](./DASHBOARD-BUILDER-DESIGN.md)
- Complete technical architecture
- Data models
- Service layer design
- State management
- Integration patterns

---

## 📖 Document Guide

| Document | Purpose | Audience | Key Content |
|----------|---------|----------|-------------|
| **WORKFLOWS.md** | User journey documentation | PM, UX, Dev | Step-by-step user flows, UI states, edge cases |
| **QUICK-START-GUIDE.md** | Developer onboarding | Frontend Dev | Quick setup, tech stack, code examples |
| **IMPLEMENTATION-PLAN.md** | Development roadmap | Frontend Dev | Folder structure, development phases, checklist |
| **BACKEND-API-SPEC.md** | API contract | Backend Dev | Endpoint specs, request/response formats, LLM logic |
| **DASHBOARD-BUILDER-DESIGN.md** | Technical spec | Architect, Lead Dev | Full architecture, models, services, integrations |

---

## 🏗️ Architecture Summary

### Frontend Stack
- **Framework**: Angular 17
- **Grid System**: angular-gridster2 (drag-drop-resize)
- **Charts**: ngx-echarts + Apache ECharts
- **Drag & Drop**: Angular CDK
- **State**: RxJS Services
- **Styling**: SCSS + Tailwind + Ocean Breeze theme

### Backend Stack (To Be Developed)
- **API**: RESTful (`/api/v1/query-service/generate-chart`)
- **NL Processing**: LLM for query parsing
- **SQL Generation**: LLM-based NL to SQL
- **Data Access**: Data warehouse connection
- **Chart Config**: LLM generates ECharts configuration

### Integration Flow

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │◄───────►│  Query API   │◄───────►│  Data Warehouse
│   (Angular)  │   JSON  │   (Backend)  │   SQL   │  (Database)  │
│              │         │              │         │              │
│ - AI Chat UI │ sends   │ - NL to SQL  │ queries │ - Sales data │
│ - Dashboard  │ NL      │ - LLM gen    │ data    │ - Analytics  │
│ - Grid       │ query   │ - ECharts    │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
```

---

## 🎯 Key Features

### Two Primary Workflows

#### Workflow A: Drag-Drop + AI Data Population
1. User drags chart template (e.g., "Bar Chart") to grid
2. Empty chart widget created
3. User clicks chart, asks AI: "show sales by region"
4. Backend: NL → SQL → Data → ECharts Config
5. Chart populates with data
6. Natural language query saved with chart

**User Controls**: Chart type, size, position  
**AI Provides**: Data, configuration

#### Workflow B: Direct AI Chart Creation
1. User types in chat: "show revenue trend over time"
2. AI determines best chart type (likely "line")
3. AI recommends optimal size (6x3 for time series)
4. Chart auto-created and populated
5. Natural language query saved

**User Controls**: Query only  
**AI Provides**: Chart type, size, data, configuration

---

## 💾 Data Persistence

### Critical Requirements

**Natural Language Query Storage**  
Every chart MUST store the original NL query:
```typescript
config: {
  naturalLanguageQuery: "Show me sales by region for last quarter",
  queryTimestamp: "2024-10-02T10:30:00Z",
  echartsOptions: { /* config from backend */ }
}
```

**Why?**
1. **Dashboard Reload**: Re-render charts from saved configs
2. **Data Refresh**: Re-execute query for fresh data
3. **User Reference**: Show what data the chart displays
4. **Audit Trail**: Track what queries were run

**Dashboard Save Format**
```json
{
  "dashboardId": "dash-123",
  "name": "Q4 Sales Dashboard",
  "items": [
    {
      "id": "chart-1",
      "chartType": "bar",
      "x": 0, "y": 0, "cols": 4, "rows": 3,
      "config": {
        "title": "Sales by Region",
        "naturalLanguageQuery": "Show me sales by region for last quarter",
        "echartsOptions": { /* complete config */ }
      }
    }
  ],
  "chatHistory": [ /* conversation */ ]
}
```

---

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  App Header (from shared-ui) - 64px                         │
├──────────┬──────────────────────────────────┬───────────────┤
│          │                                  │               │
│  Chart   │  Dashboard Grid                  │   AI Chat     │
│  Library │  (Angular Gridster2)             │   Panel       │
│          │                                  │               │
│  250px   │  Flexible Width                  │   350px       │
│  width   │  (100vw - 600px)                │   width       │
│          │                                  │               │
│  ┌────┐  │  ┌──────┐  ┌──────┐  ┌──────┐  │ ┌───────────┐ │
│  │Bar │  │  │Chart │  │Chart │  │Chart │  │ │ AI: Hello │ │
│  └────┘  │  │  1   │  │  2   │  │  3   │  │ └───────────┘ │
│          │  └──────┘  └──────┘  └──────┘  │               │
│  ┌────┐  │                                  │ ┌───────────┐ │
│  │Line│  │  [Drag charts here]             │ │User: Show │ │
│  └────┘  │                                  │ │ sales...  │ │
│          │  [Click charts to select]       │ └───────────┘ │
│  ┌────┐  │                                  │               │
│  │Pie │  │  [Selected chart has blue       │ [Type here...]│
│  └────┘  │   border and links to chat]     │ [Send Button ]│
│          │                                  │               │
└──────────┴──────────────────────────────────┴───────────────┘
```

---

## 🔄 Development Workflow

### Phase 1: Foundation (Week 1)
- [ ] Install dependencies
- [ ] Create folder structure
- [ ] Define data models (including Query Service models)
- [ ] Create service skeletons

### Phase 2: Core Components (Week 2)
- [ ] Chart Library component (drag source)
- [ ] Dashboard Grid component (drop target + gridster)
- [ ] Chart Widget component (display individual charts)
- [ ] Chart selection mechanism

### Phase 3: AI Integration (Week 2-3)
- [ ] AI Chat component UI
- [ ] Query Service HTTP client
- [ ] AI Chat Service (orchestration)
- [ ] Connect chat to grid (both workflows)

### Phase 4: Persistence (Week 3)
- [ ] Dashboard save/load functionality
- [ ] Chat history persistence
- [ ] Data refresh capability

### Phase 5: Polish (Week 3-4)
- [ ] ECharts theme integration
- [ ] Responsive design
- [ ] Error handling
- [ ] Loading states
- [ ] Animations

---

## 🧪 Testing Strategy

### Frontend Tests
- **Unit Tests**: Services, data models, utilities
- **Component Tests**: UI components, event handling
- **Integration Tests**: Drag-drop flow, chart selection, AI chat
- **E2E Tests**: Complete user journeys (Workflow A & B)

### Backend Tests
- **Unit Tests**: NL parsing, SQL generation, chart recommendations
- **Integration Tests**: Database queries, LLM API calls
- **E2E Tests**: Full request-response cycles
- **Performance Tests**: Response time < 3s, concurrent users

### Test Data
See `BACKEND-API-SPEC.md` for complete test case specifications.

---

## 📦 Dependencies

### Frontend
```bash
npm install angular-gridster2 echarts ngx-echarts --save
```

### Backend
- LLM API (e.g., OpenAI GPT-4, Anthropic Claude)
- Database connector (based on data warehouse)
- SQL parser/validator
- ECharts server-side renderer (optional)

---

## 🚀 Getting Started Checklist

### Frontend Team
- [ ] Read `QUICK-START-GUIDE.md`
- [ ] Read `IMPLEMENTATION-PLAN.md`
- [ ] Install dependencies
- [ ] Create component scaffolding
- [ ] Implement with mock backend first
- [ ] Integrate with real backend when ready

### Backend Team
- [ ] Read `BACKEND-API-SPEC.md`
- [ ] Review request/response examples
- [ ] Set up LLM integration
- [ ] Implement NL to SQL conversion
- [ ] Implement ECharts config generation
- [ ] Create test suite
- [ ] Deploy API endpoint

### Integration
- [ ] Coordinate API contract
- [ ] Test with sample queries
- [ ] Handle error scenarios
- [ ] Performance testing
- [ ] Security review

---

## 🔗 Related Documentation

- **Angular Gridster2**: [https://tiberiuzuld.github.io/angular-gridster2/](https://tiberiuzuld.github.io/angular-gridster2/)
- **Apache ECharts**: [https://echarts.apache.org/](https://echarts.apache.org/)
- **ECharts Examples**: [https://echarts.apache.org/examples/en/index.html](https://echarts.apache.org/examples/en/index.html)
- **Angular CDK Drag-Drop**: [https://material.angular.io/cdk/drag-drop/overview](https://material.angular.io/cdk/drag-drop/overview)

---

## ❓ FAQ

### Q: Can users edit charts manually after AI generates them?
**A**: Yes, in future phases. Charts can be clicked to open configuration panel for manual editing.

### Q: What happens if the backend is down?
**A**: Frontend shows error message in chat. Existing charts remain visible (using cached data).

### Q: Can dashboards be shared with other users?
**A**: Not in MVP. This is a Phase 2 feature requiring permissions system.

### Q: How are natural language queries validated?
**A**: Backend LLM attempts to parse query. If ambiguous, it returns error asking for clarification.

### Q: What chart types are supported?
**A**: MVP: Bar, Line, Pie, Table. Future: Area, Scatter, KPI, Heatmap, and more.

### Q: Can users query across multiple data sources?
**A**: Not in MVP. Future enhancement will support multi-source queries with JOINs.

### Q: How is performance handled for large datasets?
**A**: Backend limits results to 10,000 rows. For larger datasets, aggregation is required.

### Q: Can dashboards auto-refresh?
**A**: Not in MVP. Users must manually click chart and say "refresh". Scheduled refresh is Phase 2.

---

## 📞 Support

For questions or clarifications:
- **Frontend Architecture**: See `DASHBOARD-BUILDER-DESIGN.md`
- **Workflow Questions**: See `WORKFLOWS.md`
- **API Questions**: See `BACKEND-API-SPEC.md`
- **Implementation Help**: See `IMPLEMENTATION-PLAN.md`

---

## 📝 Version History

**v1.0** (Current) - Initial design with backend integration requirements
- Two-workflow system (drag-drop + direct AI)
- Natural language query persistence
- Query Service API specification
- Complete frontend architecture

---

**Last Updated**: October 2, 2025  
**Status**: Ready for Implementation  
**Estimated Completion**: 3-4 weeks (frontend + backend parallel development)

