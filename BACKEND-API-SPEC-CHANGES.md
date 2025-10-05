# Backend API Spec Changes - WebSocket Async Flow

## 📋 Overview

This document outlines the specific changes to the BACKEND-API-SPEC to support asynchronous query processing with WebSocket progress updates.

---

## 🔄 Flow Comparison

### Before (Synchronous)
```
User → POST /api/v1/query-service/generate-chart
         ↓ (Wait 3-15 seconds)
         ↓
User ← 200 OK with complete data + chart config
```

**Issues:**
- Long wait times (3-15 seconds)
- No visibility into progress
- Poor user experience for complex queries
- HTTP timeout risks

### After (Asynchronous with WebSocket)
```
User → POST /api/v1/query-service/generate-chart
User ← 202 Accepted (immediate, < 100ms)
       {
         "queryId": "uuid",
         "websocketUrl": "/ws/v1/query-service/status/{queryId}"
       }

User → Connect to WebSocket

User ← Progress Update: "Parsing natural language query..."
User ← Progress Update: "Fetching metadata..."
User ← Progress Update: "Generating SQL..."
User ← Progress Update: "Validating SQL..."
User ← Progress Update: "Executing query..."
User ← Progress Update: "Generating chart configuration..."
User ← Final Result: Complete data + chart config
```

**Benefits:**
- Immediate response (no waiting)
- Real-time progress updates
- Better user experience (can show loading states)
- No timeout issues
- Can cancel queries if needed

---

## 📝 API Changes

### 1. POST /api/v1/query-service/generate-chart

#### Request (Unchanged)
```typescript
interface ChartGenerationRequest {
  naturalLanguageQuery: string;
  constraints?: {
    chartType?: string;
    chartSize?: { cols: number; rows: number };
    position?: { x: number; y: number };
  };
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

#### Response (Changed)

**Old Response (200 OK):**
```typescript
interface ChartGenerationResult {
  success: true;
  data: any[];
  chartConfig: {
    type: string;
    title: string;
    echartsOptions: any;
    size?: { cols: number; rows: number };
  };
  metadata: {
    sqlQuery: string;
    dataSchema: any;
    recommendedChartType?: string;
    confidence: number;
  };
  naturalLanguageQuery: string;
}
```

**New Response (202 Accepted):**
```typescript
interface ChartGenerationInitiated {
  queryId: string;              // UUID for tracking
  websocketUrl: string;         // WebSocket endpoint
  status: "initiated";          // Status indicator
}
```

**Example:**
```json
{
  "queryId": "550e8400-e29b-41d4-a716-446655440000",
  "websocketUrl": "/ws/v1/query-service/status/550e8400-e29b-41d4-a716-446655440000",
  "status": "initiated"
}
```

---

### 2. WebSocket /ws/v1/query-service/status/{queryId} (New)

#### Message Types

##### 1. Connection Confirmation
Sent immediately upon WebSocket connection.

```typescript
interface ConnectedMessage {
  type: "CONNECTED";
  queryId: string;
  message: string;
  timestamp: string;
}
```

**Example:**
```json
{
  "type": "CONNECTED",
  "queryId": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Connected to query service",
  "timestamp": "2024-10-03T10:30:00Z"
}
```

##### 2. Progress Updates
Sent for each workflow stage.

```typescript
interface ProgressMessage {
  type: "PROGRESS";
  queryId: string;
  stage: ProgressStage;
  message: string;
  timestamp: string;
}

type ProgressStage =
  | "parsing_query"
  | "fetching_metadata"
  | "generating_sql"
  | "validating_sql"
  | "retrying_sql"
  | "executing_query"
  | "recommending_chart"
  | "generating_chart_config"
  | "completed";
```

**Examples:**
```json
{
  "type": "PROGRESS",
  "queryId": "550e8400-...",
  "stage": "parsing_query",
  "message": "Parsing natural language query...",
  "timestamp": "2024-10-03T10:30:01Z"
}
```

```json
{
  "type": "PROGRESS",
  "queryId": "550e8400-...",
  "stage": "fetching_metadata",
  "message": "Fetching metadata from OpenMetadata...",
  "timestamp": "2024-10-03T10:30:03Z"
}
```

```json
{
  "type": "PROGRESS",
  "queryId": "550e8400-...",
  "stage": "generating_sql",
  "message": "Generating SQL query...",
  "timestamp": "2024-10-03T10:30:05Z"
}
```

```json
{
  "type": "PROGRESS",
  "queryId": "550e8400-...",
  "stage": "retrying_sql",
  "message": "SQL validation failed. Retrying with corrections...",
  "timestamp": "2024-10-03T10:30:12Z"
}
```

##### 3. SQL Generated (Transparency)
Sent when SQL is successfully generated and validated.

```typescript
interface SQLGeneratedMessage {
  type: "SQL_GENERATED";
  queryId: string;
  sqlQuery: string;
  timestamp: string;
}
```

**Example:**
```json
{
  "type": "SQL_GENERATED",
  "queryId": "550e8400-...",
  "sqlQuery": "SELECT region, SUM(sales) as sales FROM sales_data WHERE quarter = 'Q4' AND year = 2024 GROUP BY region ORDER BY sales DESC",
  "timestamp": "2024-10-03T10:30:08Z"
}
```

##### 4. Completed (Final Result)
Sent when query completes successfully. Contains the original response format.

```typescript
interface CompletedMessage {
  type: "COMPLETED";
  queryId: string;
  result: ChartGenerationResult;  // Same as old 200 OK response
  timestamp: string;
}
```

**Example:**
```json
{
  "type": "COMPLETED",
  "queryId": "550e8400-...",
  "result": {
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
      "echartsOptions": { /* ECharts config */ },
      "size": { "cols": 4, "rows": 3 }
    },
    "metadata": {
      "sqlQuery": "SELECT region, SUM(sales)...",
      "dataSchema": { "region": "string", "sales": "number" },
      "recommendedChartType": "bar",
      "confidence": 0.95
    },
    "naturalLanguageQuery": "Show me sales by region for last quarter"
  },
  "timestamp": "2024-10-03T10:30:15Z"
}
```

##### 5. Error
Sent when query fails at any stage.

```typescript
interface ErrorMessage {
  type: "ERROR";
  queryId: string;
  error: ChartGenerationError;  // Same as old 400/500 error response
  timestamp: string;
}
```

**Example:**
```json
{
  "type": "ERROR",
  "queryId": "550e8400-...",
  "error": {
    "success": false,
    "error": "Column 'region' not found in schema",
    "errorCode": "SQL_VALIDATION_ERROR",
    "details": {
      "sqlQuery": "SELECT region, SUM(sales)...",
      "availableColumns": ["area", "product", "revenue"],
      "suggestion": "Try using 'area' instead of 'region'"
    }
  },
  "timestamp": "2024-10-03T10:30:05Z"
}
```

---

## 🎨 UI Integration Changes

### Angular Frontend (AI Canvas)

#### Old Code (Synchronous)
```typescript
// Old approach - blocking HTTP call
generateChart(query: string) {
  this.loading = true;
  
  this.http.post('/api/v1/query-service/generate-chart', {
    naturalLanguageQuery: query
  }).subscribe({
    next: (result) => {
      this.loading = false;
      this.renderChart(result);
    },
    error: (err) => {
      this.loading = false;
      this.showError(err);
    }
  });
}
```

#### New Code (Asynchronous with WebSocket)
```typescript
// New approach - async with progress updates
generateChart(query: string) {
  // Step 1: Initiate query
  this.http.post<ChartGenerationInitiated>(
    '/api/v1/query-service/generate-chart',
    { naturalLanguageQuery: query }
  ).subscribe({
    next: (response) => {
      // Step 2: Connect to WebSocket
      this.connectWebSocket(response.queryId, response.websocketUrl);
    },
    error: (err) => {
      this.showError(err);
    }
  });
}

connectWebSocket(queryId: string, wsUrl: string) {
  const ws = new WebSocket(`ws://localhost${wsUrl}`);
  
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch (message.type) {
      case 'CONNECTED':
        console.log('Connected to query service');
        break;
        
      case 'PROGRESS':
        // Show progress in chat UI
        this.updateProgress(message.stage, message.message);
        break;
        
      case 'SQL_GENERATED':
        // Show SQL in chat (optional, for transparency)
        this.showSQL(message.sqlQuery);
        break;
        
      case 'COMPLETED':
        // Render final chart
        this.renderChart(message.result);
        ws.close();
        break;
        
      case 'ERROR':
        // Show error
        this.showError(message.error);
        ws.close();
        break;
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    this.showError({ message: 'Connection lost' });
  };
}

updateProgress(stage: string, message: string) {
  // Add progress message to chat UI
  this.chatMessages.push({
    type: 'progress',
    icon: this.getIconForStage(stage),
    message: message,
    timestamp: new Date()
  });
}

getIconForStage(stage: string): string {
  const icons = {
    'parsing_query': '🔍',
    'fetching_metadata': '📚',
    'generating_sql': '⚙️',
    'validating_sql': '✅',
    'retrying_sql': '🔄',
    'executing_query': '🚀',
    'recommending_chart': '📊',
    'generating_chart_config': '🎨',
    'completed': '✨'
  };
  return icons[stage] || '⏳';
}
```

---

## 📊 Progress Stage Details

### Complete Stage Sequence

| Order | Stage | Duration | Message | Icon |
|-------|-------|----------|---------|------|
| 1 | `parsing_query` | 2-4s | "Parsing natural language query..." | 🔍 |
| 2 | `fetching_metadata` | 0.5-1s | "Fetching metadata from OpenMetadata..." | 📚 |
| 3 | `generating_sql` | 3-5s | "Generating SQL query..." | ⚙️ |
| 4 | `validating_sql` | 0.2-0.5s | "Validating SQL query..." | ✅ |
| 4a | `retrying_sql` | 3-5s | "SQL validation failed. Retrying..." | 🔄 |
| 5 | `executing_query` | 1-10s | "Executing query against data warehouse..." | 🚀 |
| 6 | `recommending_chart` | 0.5-2s | "Analyzing data and recommending chart type..." | 📊 |
| 7 | `generating_chart_config` | 2-4s | "Generating chart configuration..." | 🎨 |
| 8 | `completed` | - | "Query completed successfully!" | ✨ |

**Total Time:** 9-27 seconds (typical: 12-15s)

---

## 🔧 Backend Implementation Notes

### Progress Publishing Pattern

```python
# app/services/redis_publisher.py
import redis.asyncio as aioredis
import json
from datetime import datetime

async def publish_progress(
    query_id: str,
    stage: str,
    message: str,
    message_type: str = "PROGRESS"
):
    """Publish progress update to Redis channel"""
    redis_client = aioredis.from_url(os.getenv("REDIS_URL"))
    channel = f"query_status_{query_id}"
    
    payload = {
        "type": message_type,
        "queryId": query_id,
        "stage": stage,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    await redis_client.publish(channel, json.dumps(payload))
    await redis_client.close()
```

### Usage in Workflow Nodes

```python
# In each LangGraph node
async def parse_natural_language(state: WorkflowState) -> WorkflowState:
    # Publish progress
    await publish_progress(
        state["query_id"],
        "parsing_query",
        "Parsing natural language query..."
    )
    
    # Do work...
    result = await llm.ainvoke(prompt)
    
    return state
```

---

## ✅ Migration Checklist

### Backend Changes
- [ ] Update `/generate-chart` endpoint to return 202 with queryId + websocketUrl
- [ ] Implement WebSocket endpoint `/ws/v1/query-service/status/{queryId}`
- [ ] Add Redis pub/sub for progress broadcasting
- [ ] Update each workflow node to publish progress
- [ ] Publish SQL_GENERATED message after validation
- [ ] Publish COMPLETED message with final result
- [ ] Publish ERROR message on failures

### Frontend Changes (AI Canvas)
- [ ] Update chart generation service to handle async flow
- [ ] Implement WebSocket client
- [ ] Add progress indicator to chat UI
- [ ] Display stage-specific icons and messages
- [ ] Handle SQL display (optional transparency feature)
- [ ] Handle WebSocket reconnection logic
- [ ] Handle error states gracefully

### Testing
- [ ] Test POST endpoint returns 202 immediately
- [ ] Test WebSocket connection establishment
- [ ] Test all progress stages are sent
- [ ] Test final COMPLETED message contains correct data
- [ ] Test ERROR handling for each failure scenario
- [ ] Test concurrent queries (multiple WebSockets)
- [ ] Test WebSocket cleanup on disconnect

---

## 🎯 Benefits Summary

### User Experience
✅ **Immediate Feedback**: No waiting for HTTP response  
✅ **Progress Visibility**: See exactly what's happening  
✅ **Better Context**: Stage-specific messages keep users informed  
✅ **No Timeouts**: WebSocket persists for long queries  
✅ **Cancelable**: Can close WebSocket to cancel query (future)

### Technical Benefits
✅ **Scalability**: Non-blocking async processing  
✅ **Debuggability**: Each stage logged and visible  
✅ **Resilience**: Failures don't block other queries  
✅ **Monitoring**: Easy to track bottlenecks per stage  
✅ **Extensibility**: Easy to add new progress stages

### Developer Experience
✅ **Clear Contract**: Well-defined message types  
✅ **Type Safety**: TypeScript interfaces for all messages  
✅ **Testability**: Each stage can be tested independently  
✅ **Observability**: Progress updates provide built-in telemetry

---

## 🚀 Rollout Plan

### Phase 1: Backend (Week 4)
- Implement async endpoint (202 response)
- Implement WebSocket endpoint
- Add Redis pub/sub
- Update workflow nodes with progress publishing

### Phase 2: Frontend (Week 5)
- Implement WebSocket client
- Add progress UI to chat
- Test integration with backend
- Handle edge cases

### Phase 3: Testing & Polish (Week 5)
- E2E testing
- Load testing (concurrent queries)
- UI polish (animations, better messaging)
- Documentation

### Phase 4: Deployment
- Deploy to staging
- User acceptance testing
- Deploy to production
- Monitor and iterate

---

## 📚 Reference: WebSocket Message Flow Example

```
Client                                  Server
  |                                       |
  |-- POST /generate-chart ------------→ |
  |                                       |
  |←- 202 Accepted                        |
  |   { queryId, websocketUrl }           |
  |                                       |
  |-- WS Connect /ws/.../status/{id} --→ |
  |                                       |
  |←- CONNECTED -------------------------|
  |                                       |
  |←- PROGRESS: parsing_query ----------|
  |                                       |
  |←- PROGRESS: fetching_metadata -------|
  |                                       |
  |←- PROGRESS: generating_sql ----------|
  |                                       |
  |←- PROGRESS: validating_sql ----------|
  |                                       |
  |←- SQL_GENERATED --------------------|
  |                                       |
  |←- PROGRESS: executing_query ---------|
  |                                       |
  |←- PROGRESS: recommending_chart ------|
  |                                       |
  |←- PROGRESS: generating_chart_config -|
  |                                       |
  |←- COMPLETED { result } --------------|
  |                                       |
  |-- WS Close ------------------------→ |
```

---

**Document Version:** 1.0  
**Last Updated:** October 3, 2025  
**Related Documents:**
- QUERY-SERVICE-IMPLEMENTATION-PLAN.md
- BACKEND-API-SPEC.md (original)
- frontend/projects/ai-canvas/WORKFLOWS.md

