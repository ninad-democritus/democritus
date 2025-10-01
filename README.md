AI-Powered Data Platform (MVP1)

Monorepo for MVP1: file ingestion and AI-driven schema generation with a human-in-the-loop validation UI.

## Services
- **Frontend**: Angular application with multi-file upload and schema approval UI  
- **File Upload Service**: Generates pre-signed MinIO URLs for batch uploads
- **Agent Workflow Service**: Orchestrates AI agents via LangGraph with real-time WebSocket updates
- **Agent Worker**: Celery workers running the agentic pipeline (Profiler → Aligner → Architect → Tagger)
- **Data Pipeline Service**: Triggers Airflow DAG for data ingestion (mock)
- **Gateway**: Nginx reverse proxy with CORS handling
- **Infrastructure**: Redis, Postgres, MinIO, Ollama (LLM), DataHub (metadata), Airflow

## Quickstart
Prerequisites: Docker Desktop or Rancher Desktop (Windows), ~6GB free RAM.

```bash
# From repo root
docker compose up --build
```

Open UI: http://localhost/
1. **Upload**: Select multiple CSV/Excel files and click "Start Upload & Analysis"
2. **Monitor**: Watch real-time progress through agent pipeline via WebSocket
3. **Approve**: Review generated unified schema with business tags and approve for data ingestion

## Agent Pipeline
The system uses a sophisticated 4-agent workflow:
- **🔍 Profiler Agent**: Analyzes files, infers data types, calculates statistics
- **🎯 Aligner Agent**: Identifies business entities (Customer, Order, Product, etc.)
- **🏗️ Architect Agent**: Designs relational schema with primary/foreign keys
- **🏷️ Tagger Agent**: Enriches with business context and descriptions (PII, Financial, etc.)

API Contracts (MVP1)
- POST /v1/files/generate-upload-url
- POST /v1/workflows/start
- WS  /ws/v1/workflows/status/{workflowId}
- POST /v1/workflows/{workflowId}/validate
- POST /v1/pipelines/trigger

## LangSmith Observability Setup

To enable detailed agent tracing and monitoring:

1. **Create LangSmith Account**: Go to [smith.langchain.com](https://smith.langchain.com) and sign up
2. **Get API Key**: Navigate to Settings → API Keys and create a new key
3. **Set Environment Variable**: Create a `.env` file in the project root:
   ```bash
   LANGCHAIN_API_KEY=your_langsmith_api_key_here
   ```
4. **View Traces**: After running workflows, visit your LangSmith project dashboard to see:
   - Agent execution timelines and performance metrics
   - Input/output traces for each agent step
   - Error tracking and debugging information
   - Workflow success rates and bottlenecks

**Dashboard URL**: [smith.langchain.com/projects/democritus-agents](https://smith.langchain.com/projects/democritus-agents)

## Configuration

Environment variables (most have defaults):
- `MINIO_ENDPOINT=minio:9000`
- `MINIO_ACCESS_KEY=minioadmin` 
- `MINIO_SECRET_KEY=minioadmin`
- `MINIO_BUCKET=uploads`
- `REDIS_URL=redis://redis:6379/0`
- `LANGCHAIN_API_KEY=` (set for observability)
- `LANGCHAIN_PROJECT=democritus-agents`

## Service Dashboards
- **Main UI**: http://localhost/
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **LangSmith Traces**: https://smith.langchain.com/projects/democritus-agents
- **DataHub** (when enabled): http://localhost:9002

## Architecture Notes
- **Real-time Updates**: WebSocket integration with Redis pub/sub for live agent progress
- **Batch Processing**: Multi-file uploads handled as single job with unified schema generation  
- **Error Handling**: Comprehensive error tracking and recovery at each agent step
- **Observability**: Full LangSmith integration for agent performance monitoring


