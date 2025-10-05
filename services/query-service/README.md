# Query Service

Natural Language to SQL and Chart Generation Service using LangGraph and Ollama.

## Overview

This service converts natural language queries into SQL, executes them against Iceberg tables via Trino, and generates ECharts visualization configs.

## Features

- 🔍 Natural language query parsing
- 📊 Automatic chart type recommendation
- ⚡ Async processing with WebSocket progress updates
- 🔄 Intelligent retry logic for SQL validation
- 🎨 ECharts configuration generation
- 📚 OpenMetadata integration for schema discovery

## Architecture

- **FastAPI**: REST API and WebSocket endpoints
- **Celery**: Async task processing
- **LangGraph**: Workflow orchestration with retry logic
- **Redis**: Message broker and pub/sub
- **Trino**: SQL execution over Iceberg tables
- **Ollama**: Self-hosted LLM (Llama 3.1)
- **OpenMetadata**: Schema and metadata catalog

## API Endpoints

### POST /api/v1/query-service/generate-chart

Initiate chart generation from natural language query.

**Request:**
```json
{
  "naturalLanguageQuery": "Show me sales by region for last quarter",
  "constraints": {
    "chartType": "bar",
    "chartSize": { "cols": 4, "rows": 3 }
  }
}
```

**Response (202 Accepted):**
```json
{
  "queryId": "550e8400-e29b-41d4-a716-446655440000",
  "websocketUrl": "/ws/v1/query-service/status/550e8400-...",
  "status": "initiated"
}
```

### WebSocket /ws/v1/query-service/status/{queryId}

Receive real-time progress updates and final result.

## Development

### Prerequisites

- Python 3.11+
- Redis
- Trino
- Ollama with Llama 3.1 models
- OpenMetadata

### Local Setup

```bash
# Install dependencies
cd services/query-service
pip install -r requirements.txt

# Run service
uvicorn app.main:app --reload

# Run worker (separate terminal)
celery -A app.tasks:celery_app worker -l info
```

### Docker Setup

```bash
# Build and run
docker compose up -d query-service query-service-worker
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## Environment Variables

See `app/config.py` for full list of configuration options.

Key variables:
- `REDIS_URL`: Redis connection URL
- `TRINO_HOST`: Trino server host
- `OLLAMA_HOST`: Ollama API URL
- `OPENMETADATA_API_ENDPOINT`: OpenMetadata API URL

## Implementation Status

- ✅ Phase 1: Foundation (service structure, Docker, basic API)
- ⏳ Phase 2: Core workflow (NL parsing, SQL generation)
- ⏳ Phase 3: Execution & charting
- ⏳ Phase 4: API & WebSocket
- ⏳ Phase 5: Integration & testing

## Related Documentation

- [Implementation Plan](../../QUERY-SERVICE-IMPLEMENTATION-PLAN.md)
- [API Changes](../../BACKEND-API-SPEC-CHANGES.md)
- [Backend API Spec](../../frontend/projects/ai-canvas/BACKEND-API-SPEC.md)

