# Dashboard Management Service - Implementation Design

**Version:** 1.0  
**Date:** October 10, 2025  
**Status:** Phase 1 - Core Functionality

---

## 📋 Overview

This document outlines the implementation design for the Dashboard Management Service, enabling users to save, load, and manage dashboards with static or dynamic data capabilities.

---

## 🎯 Goals

- **Save Dashboards**: Store dashboard layouts and chart configurations
- **Static Dashboards**: Save snapshots of data with chart configs
- **Dynamic Dashboards**: Store SQL queries and fetch live data on load
- **Access Control**: Private (owner only) or Public (all users)
- **MFE Integration**: Seamless integration with AI Canvas remote app

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                  Frontend (Angular)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   AI Canvas  │  │    Header    │  │  Dashboard   │  │
│  │   Builder    │  │  (Save Btn)  │  │    Modal     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             ▼
                  ┌──────────────────────┐
                  │  Nginx (Reverse      │
                  │  Proxy)              │
                  └──────────┬───────────┘
                             │
          ┌──────────────────┴──────────────────┐
          ▼                                     ▼
┌─────────────────────┐            ┌─────────────────────┐
│ Dashboard Service   │            │  Query Service      │
│ - CRUD operations   │◄───────────│  - Core API         │
│ - Data stripping    │   Calls    │  - SQL validation   │
│ - Dashboard hydration│           │  - SQL execution    │
│                     │            │  - Chart binding    │
└──────────┬──────────┘            └──────────┬──────────┘
           │                                   │
           ▼                                   ▼
┌──────────────────────┐          ┌────────────────────┐
│   PostgreSQL         │          │  Trino + Iceberg   │
│   (dashboards_db)    │          │  OpenMetadata      │
└──────────────────────┘          └────────────────────┘
```

---

## 🗄️ Database Design

### Schema: `dashboards_db`

#### Table: `dashboards`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(255) | Dashboard name |
| `owner_id` | VARCHAR(255) | User ID (temporary in Phase 1) |
| `visibility` | VARCHAR(20) | 'private' or 'public' |
| `dashboard_type` | VARCHAR(20) | 'static' or 'dynamic' |
| `gridster_config` | JSONB | Grid configuration |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last update timestamp |

#### Table: `widgets`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `dashboard_id` | UUID | Foreign key to dashboards |
| `grid_x` | INTEGER | Grid X position |
| `grid_y` | INTEGER | Grid Y position |
| `grid_cols` | INTEGER | Widget column span |
| `grid_rows` | INTEGER | Widget row span |
| `chart_config` | JSONB | ECharts configuration |
| `metadata` | JSONB | SQL query, schema info |
| `nl_query` | TEXT | Original natural language query |
| `created_at` | TIMESTAMP | Creation timestamp |

**Key Points:**
- Cascading delete: Deleting dashboard removes all widgets
- Indexes on `owner_id`, `visibility`, and `dashboard_id`
- Widget positions stored with each widget (not in layout field)

---

## 🔌 API Design

### Query Service - Core API (`/core/v1/`)

**New stable endpoints for dashboard service integration:**

#### 1. POST `/core/v1/validate-sql`
**Purpose:** Validate SQL against schema (fetches metadata internally)

**Request:**
```json
{
  "sql": "SELECT team, COUNT(*) FROM iceberg.default.Event GROUP BY team"
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "suggestions": []
}
```

#### 2. POST `/core/v1/execute-sql`
**Purpose:** Execute SQL via Trino

**Request:**
```json
{
  "sql": "SELECT team, COUNT(*) as count FROM iceberg.default.Event GROUP BY team",
  "limit": 1000
}
```

**Response:**
```json
{
  "columns": ["team", "count"],
  "rows": [
    {"team": "India", "count": 12},
    {"team": "USA", "count": 34}
  ],
  "row_count": 2,
  "truncated": false
}
```

#### 3. POST `/core/v1/bind-chart-data`
**Purpose:** Populate chart template with data

**Request:**
```json
{
  "chart_config": {
    "type": "bar",
    "echartsOptions": {
      "xAxis": {"type": "category", "data": []},
      "series": [{"type": "bar", "data": []}]
    }
  },
  "data": {
    "rows": [{"team": "India", "count": 12}]
  },
  "chart_type": "bar"
}
```

**Response:**
```json
{
  "chart_config": {
    "type": "bar",
    "echartsOptions": {
      "xAxis": {"data": ["India", "USA"]},
      "series": [{"data": [12, 34]}]
    }
  }
}
```

---

### Dashboard Service API (`/api/v1/dashboards`)

#### 1. POST `/api/v1/dashboards`
**Purpose:** Create new dashboard

**Request:**
```json
{
  "name": "Olympic Analytics",
  "owner_id": "user-123",
  "visibility": "private",
  "dashboard_type": "dynamic",
  "widgets": [
    {
      "grid_x": 0,
      "grid_y": 0,
      "grid_cols": 6,
      "grid_rows": 4,
      "chart_config": {...},
      "metadata": {"sqlQuery": "SELECT ...", "chartType": "bar"},
      "nl_query": "Give me medal winners by team"
    }
  ]
}
```

**Response:** Full dashboard object with generated UUIDs

#### 2. GET `/api/v1/dashboards?owner_id={id}`
**Purpose:** List user's dashboards

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Olympic Analytics",
    "visibility": "private",
    "dashboard_type": "dynamic",
    "widget_count": 3,
    "created_at": "2025-10-10T12:00:00Z",
    "updated_at": "2025-10-10T12:00:00Z"
  }
]
```

#### 3. GET `/api/v1/dashboards/{id}?owner_id={id}`
**Purpose:** Get dashboard (hydrated if dynamic)

**Response:** Full dashboard with widgets (live data if dynamic)

#### 4. PUT `/api/v1/dashboards/{id}?owner_id={id}`
**Purpose:** Update dashboard

#### 5. DELETE `/api/v1/dashboards/{id}?owner_id={id}`
**Purpose:** Delete dashboard

---

## 🔄 Workflows

### Save Dashboard Workflow

```
User creates charts → Clicks "Save" in header
    ↓
Save modal opens (name, visibility, type)
    ↓
User fills form and clicks "Save Dashboard"
    ↓
Frontend collects:
  - Dashboard items from ChartDataService
  - Form data (name, visibility, type)
  - Temporary user ID from localStorage
    ↓
POST /api/v1/dashboards
    ↓
Backend (Dashboard Service):
  - Creates dashboard record
  - For each widget:
    • If static: Store chart config as-is
    • If dynamic: Strip data arrays from config
  - Stores SQL in metadata.sqlQuery
  - Saves to PostgreSQL
    ↓
Success response → Show toast notification
```

**Data Stripping (Dynamic Dashboards):**
```javascript
// Original config
{
  xAxis: { data: ['India', 'USA'] },
  series: [{ data: [12, 34] }]
}

// Stripped template (stored)
{
  xAxis: { data: [] },
  series: [{ data: [] }]
}
```

---

### Load Dashboard Workflow (Dynamic)

```
User navigates to dashboard
    ↓
GET /api/v1/dashboards/{id}
    ↓
Backend checks dashboard_type:
  - If static: Return as-is ✓
  - If dynamic: ↓
    ↓
For each widget:
    ↓
  Extract SQL from metadata.sqlQuery
    ↓
  Call Query Service /core/v1/validate-sql
    ↓
  If valid:
    Call /core/v1/execute-sql → Get live data
    Call /core/v1/bind-chart-data → Populate template
    ↓
  If invalid:
    Add error to widget config
    ↓
Return dashboard with hydrated widgets
    ↓
Frontend renders charts with live data
```

---

## 🎨 Frontend Design

### Component Structure

```
ai-canvas/
├── app.component (Header integration)
│   ├── [appNavigation] → Dashboard links
│   └── [headerActions] → Save button
│
├── services/
│   ├── dashboard-state.service
│   │   ├── triggerSave()
│   │   ├── hasUnsavedChanges$
│   │   └── onSaveTriggered()
│   │
│   └── dashboard-api.service
│       ├── createDashboard()
│       ├── listDashboards()
│       └── getDashboard()
│
└── pages/dashboard-builder/
    ├── dashboard-builder.component
    │   ├── Listens for save trigger
    │   ├── Opens save modal
    │   └── Collects data and calls API
    │
    └── components/save-dashboard-modal/
        ├── Form (name, visibility, type)
        └── Emits save event
```

### Header Integration

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ Logo  Democritus  │  ➕ Create Dashboard  │  💾 Save │ 🔔 👤│
│                                                ↑           │
│                                          App Actions       │
│                                          before Global     │
└────────────────────────────────────────────────────────────┘
```

**Content Projection:**
```html
<lib-app-header>
  <!-- Middle section -->
  <nav appNavigation>
    <a routerLink="/dashboard-builder">➕ Create Dashboard</a>
  </nav>
  
  <!-- Right section (before global actions) -->
  <div headerActions>
    <button *ngIf="showSaveButton$ | async" (click)="onSave()">
      💾 Save
    </button>
  </div>
</lib-app-header>
```

**Save Button Visibility:**
- Show: `/dashboard-builder` route
- Hide: Dashboard list or other routes
- Disabled: No charts on grid

---

## 🔧 Service Boundaries

### Dashboard Service Responsibilities
- ✅ Save/load dashboards (CRUD)
- ✅ Generic data stripping (remove data arrays)
- ✅ Call Query Service Core API
- ❌ NO OpenMetadata access
- ❌ NO Trino access
- ❌ NO chart-type specific logic

### Query Service Responsibilities
- ✅ SQL validation (fetches metadata internally)
- ✅ SQL execution (via Trino)
- ✅ Chart-type specific data binding
- ✅ OpenMetadata client
- ✅ Trino client

**Why this separation?**
- Dashboard Service stays simple (single responsibility)
- Query Service owns all data/metadata operations
- No dependency duplication
- Clean API boundaries

---

## 📦 Deployment

### Docker Services

**New service: `dashboard-service`**
```yaml
dashboard-service:
  build: ./services/dashboard-service
  environment:
    - DB_HOST=postgresql
    - QUERY_SERVICE_URL=http://query-service:8000
  depends_on:
    - postgresql
    - query-service
```

**Database initialization:**
- `init-dashboards.sql` mounted to PostgreSQL
- Creates `dashboards_db` schema on first run

**Nginx routing:**
```
/api/v1/dashboards → dashboard-service:8000
/api/v1/query-service/core → query-service:8000/core
```

---

## 🔐 Security (Phase 1)

### Temporary User ID Approach

**Why temporary?**
- Phase 1 focuses on core functionality
- JWT authentication deferred to Phase 2

**Implementation:**
```typescript
// Frontend generates and stores temp ID
const userId = localStorage.getItem('tempUserId') || generateId();
localStorage.setItem('tempUserId', userId);

// Backend uses owner_id field (VARCHAR)
// Phase 2: Replace with JWT subject from token
```

**Access Control:**
- Private dashboards: Only owner can access
- Public dashboards: All users can view
- Enforced in `GET /dashboards/{id}` query

---

## 🧪 Testing Strategy

### API Testing
1. Query Service Core API endpoints (curl/Postman)
2. Dashboard Service CRUD operations
3. Dynamic dashboard hydration flow

### Integration Testing
1. Create dashboard via UI → Verify in DB
2. Load dynamic dashboard → Check live data
3. Update dashboard → Verify changes persist

### E2E Testing
1. Full workflow: Create charts → Save → Reload → Verify

---

## 📊 Data Flow Examples

### Static Dashboard Save
```
Chart with data → Save as static
    ↓
Store complete config:
{
  chart_config: {
    echartsOptions: {
      xAxis: { data: ['A', 'B'] },  ← Data included
      series: [{ data: [10, 20] }]   ← Data included
    }
  }
}
```

### Dynamic Dashboard Save
```
Chart with data → Save as dynamic
    ↓
Strip data, store template + SQL:
{
  chart_config: {
    echartsOptions: {
      xAxis: { data: [] },  ← Empty
      series: [{ data: [] }] ← Empty
    }
  },
  metadata: {
    sqlQuery: "SELECT ...",  ← SQL stored
    chartType: "bar"
  }
}
```

### Dynamic Dashboard Load
```
Load dynamic dashboard
    ↓
For each widget:
  SQL → Execute → Get data: [{x: 'A', y: 10}]
    ↓
  Bind data to template:
    xAxis.data = ['A', 'B']
    series[0].data = [10, 20]
    ↓
Return populated config to frontend
```

---

## 🎯 Phase 1 Scope

### ✅ Included
- Dashboard CRUD operations
- Static and dynamic dashboard support
- Query Service Core API
- Frontend save modal and header integration
- PostgreSQL storage
- Basic access control (owner_id)

### ❌ Deferred to Phase 2
- JWT authentication
- Dashboard sharing/collaboration
- Dashboard versioning
- Scheduled refresh for dynamic dashboards
- Caching layer (Redis)
- Dashboard templates
- Export/import functionality
- Advanced permissions (role-based)

---

## 🚀 Deployment Steps

1. **Database**: Run init SQL script
2. **Backend**: Deploy dashboard-service and updated query-service
3. **Frontend**: Build and deploy updated ai-canvas
4. **Nginx**: Update routing configuration
5. **Testing**: Validate all flows

---

## 📚 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate Dashboard Service | Single responsibility, clean boundaries |
| Core API in Query Service | Stable contracts, reusable utilities |
| Widget positions in widgets table | Normalized, matches frontend model |
| Data stripping for dynamic dashboards | Reduces storage, ensures fresh data |
| Chart-type specific binding | Accurate data mapping per chart type |
| Temporary user IDs | Phase 1 simplification, easy migration path |
| Content projection for header | Uses existing design, MFE-friendly |

---

## 📖 Related Documentation

- **Query Service**: `services/query-service/README.md`
- **Data Pipeline**: `QUERY-SERVICE-IMPLEMENTATION-PLAN.md`
- **MFE Architecture**: `frontend/MFE-ARCHITECTURE.md`

---

**Last Updated:** October 10, 2025  
**Next Review:** After Phase 1 completion

