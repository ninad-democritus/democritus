## Agent Workflow Service - Design and Implementation

### Overview
The Agent Workflow Service orchestrates a multi-agent pipeline that ingests tabular files uploaded per job, profiles the data, identifies domain entities, designs a relational schema with relationships, and enriches it with business context. It exposes HTTP endpoints to start workflows and retrieve status, plus a WebSocket channel to stream step-by-step status updates. Execution is performed as Celery tasks with Redis as broker and result backend, and Redis pub/sub is used to push live status updates for front-end consumption.

Key components:
- FastAPI application providing REST and WebSocket APIs (`services/agent-workflow/app/main.py`)
- Celery for asynchronous job execution using Redis (`run_job_workflow` task)
- Workflow orchestrator that sequences agents (`services/agent-workflow/app/workflow.py`)
- Four agents implementing each step:
  - ProfilerAgent: file discovery and column-level profiling
  - AlignerAgent: entity identification from profiles
  - ArchitectAgent: relational schema design and relationship inference
  - TaggerAgent: business tagging and descriptions for entities/columns/relationships
- Observability integration via LangSmith (optional) (`services/agent-workflow/app/observability.py`)

### API Surface

Endpoints (in `main.py`):
- POST `/v1/workflows/start`
  - Triggers `run_workflow` (MVP placeholder), returns `workflowId` and `websocketUrl`.
- POST `/v1/workflows/start-job`
  - Triggers full agentic pipeline via `run_job_workflow`. Request: `{ jobId, sourceType }`. Response includes `workflowId` and `websocketUrl`.
- GET `/v1/workflows/status/{workflow_id}`
  - Polling endpoint reading Celery task state: PENDING, STARTED, SUCCESS, FAILURE. On SUCCESS, may return schema when status is `PENDING_VALIDATION`.
- WS `/ws/v1/workflows/status/{workflow_id}`
  - WebSocket endpoint that subscribes to Redis channel `workflow_status_{workflow_id}` and forwards JSON status updates to clients.
- POST `/v1/workflows/{workflow_id}/validate`
  - MVP approval endpoint to acknowledge schema approval. Currently returns a mocked success response.

### Execution Model

- Celery app is initialized with Redis broker/backend (`REDIS_URL` default `redis://redis:6379/0`).
- A call to `/v1/workflows/start-job` enqueues `run_job_workflow` and returns immediately with the Celery task ID as `workflowId` and corresponding WebSocket URL.
- `run_job_workflow` constructs a `SyncAgentWorkflow` orchestrator and invokes `run_job_workflow(job_id, workflow_id)` synchronously within the Celery worker process. The orchestrator internally spins a fresh asyncio event loop to run the async workflow.
- The async workflow sends step updates to Redis pub/sub channel `workflow_status_{workflow_id}`. The WebSocket server relays those messages to subscribers in real time.

### Workflow Orchestration

Implemented in `workflow.py` as `AgentWorkflow` (async) with a synchronous wrapper `SyncAgentWorkflow` for Celery integration.

State model (`WorkflowState`):
- `job_id`, `workflow_id`
- `status`, `current_step`
- `file_profiles`: output of ProfilerAgent
- `entities`: output of AlignerAgent
- `schema`: output of ArchitectAgent
- `enriched_schema`: output of TaggerAgent
- `error_message`

Happy-path steps in order:
1) PROFILING
   - Action: `ProfilerAgent.profile_job_files(job_id)`
   - Input: MinIO bucket `MINIO_BUCKET` (default `uploads`), files under `jobs/{job_id}/`.
   - Output: List of `FileProfile` objects each containing per-column `ColumnProfile` with inferred data types, null and distinct counts, sample values, and basic numeric stats.
   - Failure conditions: No files found or profiling errors cause workflow to raise and publish `ERROR`.

2) ALIGNING
   - Action: `AlignerAgent.identify_entities(file_profiles)`
   - Logic: Heuristics over file names and column names map to entity patterns (customer, order, product, etc.), determine entity type (fact vs dimension), and identify primary key candidates via ID patterns and uniqueness.
   - Output: List of `Entity` with name, type, source file, candidate PKs, and column profiles.

3) ARCHITECTING
   - Action: `ArchitectAgent.design_schema(entities)`
   - Sub-steps:
     - Create `SchemaEntity` per identified entity, choose primary key (prefer exact `id` then first candidate), map inferred types to SQL types, and attach column details (statistics preserved).
     - Relationship inference via two methods:
       - Rule-based: foreign key naming patterns referencing other entities, and common-column natural keys with confidence scoring.
       - Optional LLM augmentation (via LangChain ChatOllama) to propose additional relationships; validated and merged with deduplication and confidence thresholds.
   - Output: `{ entities: [...], relationships: [...] }` including column details.

4) TAGGING
   - Action: `TaggerAgent.enrich_schema(schema)`
   - Sub-steps:
     - Rule-based tagging of columns into categories (PII, Financial, Temporal, Contact, Identifier, Location, Measurement, Status, Audit, Categorical).
     - Auto-generate entity descriptions based on known types and fact/dimension classification.
     - Column descriptions and business context based on names, data types, keys, uniqueness, null rates, and patterns.
     - Optional LLM augmentation to enrich entities/columns with deeper business intelligence and tags; merged into the schema and a high-level `business_summary` added.
   - Output: `enriched_schema` with `businessTags`, entity/column descriptions, and relationship descriptions.

5) PENDING_VALIDATION
   - The orchestrator publishes a final status `PENDING_VALIDATION` along with the enriched schema on the WebSocket channel. Metrics are logged to observability. The Celery task returns `{ status, schema, workflow_id, metrics }`.

Status updates (`_update_status`):
- For each step, the orchestrator calls `_update_status(state, status, message, include_schema=False)` to publish a JSON payload to Redis channel `workflow_status_{workflow_id}`. The WebSocket endpoint relays these to clients.
- The final step sets `include_schema=True` so the complete enriched schema is included in the message.

### Agent Implementations

ProfilerAgent (`agents/profiler.py`):
- Connects to MinIO using `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` (defaults provided; non-SSL for typical `minio:9000`).
- Lists `jobs/{job_id}/` prefix for `.csv`, `.xlsx`, `.xls` objects.
- Downloads each file, loads into pandas, computes per-column profiles:
  - Data type inference: integer, float, datetime, boolean, identifier, or string
  - Null/total counts, null percentage, distinct count
  - Sample values and basic numeric stats (min, max, mean)
- Returns `FileProfile` list for downstream agents.

AlignerAgent (`agents/aligner.py`):
- Determines entity names from filenames and column signals using predefined pattern dictionaries.
- Classifies entity as `fact` or `dimension` using heuristics: numeric density, presence of measure/date fields, foreign key-like columns.
- Selects primary key candidates by name patterns and uniqueness, sorted by preference (`id`, `*_id`, contains `id`).

ArchitectAgent (`agents/architect.py`):
- Converts entities into `SchemaEntity` objects with table names and SQL-like column typing; chooses primary keys.
- Relationship detection:
  - Rule-based: matches FK naming patterns against variations of target entity names; confidence based on name/data type similarity and IDs.
  - Common column joins: identical column names across tables with confidence from type matches and cardinality signals; determines direction (one-to-many, many-to-one) based on distinctness and uniqueness.
  - Optional LLM: ChatOllama via `OLLAMA_HOST` and `OLLAMA_MODEL` enhances relationships; results validated, deduplicated, filtered by confidence.

TaggerAgent (`agents/tagger.py`):
- Adds business tags per column using curated category patterns; augments with Identifier tags for PKs/unique columns and Temporal for date/time types.
- Generates entity and column business descriptions and context; annotates relationships with readable descriptions.
- Optional LLM: deep business intelligence for entities and columns; merges tags/descriptions and attaches overall business summary.

### Observability and Tracing

- `observability.py` integrates with LangSmith when `LANGCHAIN_API_KEY` is present, setting `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_PROJECT`, and `LANGCHAIN_ENDPOINT` (defaults provided). When unavailable, tracing decorators no-op.
- Decorators:
  - `@trace_agent("AgentName")` wraps agent methods to emit traces and logs.
  - `@trace_workflow_step("step", metadata)` wraps workflow steps.
- Metrics and spans: agents create spans, log outputs/metrics, and close spans; workflow logs start/completion/failure metrics.

### Data Contracts and Models

Key Pydantic/Dataclass structures:
- API: `StartWorkflowRequest`, `StartJobWorkflowRequest`, `StartWorkflowResponse`, `ValidateRequest`.
- Workflow: `WorkflowState` dataclass capturing transient state.
- Profiler: `FileProfile`, `ColumnProfile` dataclasses.
- Aligner: `Entity` dataclass.
- Architect: `SchemaEntity`, `Relationship` dataclasses; final schema is a dict with `entities`, `relationships` where entities include `column_details`.

### Status Payloads

Status messages published to Redis channel contain:
```
{
  "status": "PROFILING|ALIGNING|ARCHITECTING|TAGGING|PENDING_VALIDATION|ERROR",
  "message": "Human-friendly status",
  "timestamp": "ISO-8601",
  "current_step": "profiling_complete|alignment_complete|...",
  "schema": { ... } // only on PENDING_VALIDATION
}
```

### Error Handling

- Agent and workflow exceptions are logged; workflow captures the failing step, publishes an `ERROR` status, logs failure metrics, and re-raises to mark the Celery task as failed.
- WebSocket errors and Redis pub/sub issues are logged; the WS endpoint attempts graceful cleanup.

### Configuration and Environment

Environment variables used:
- `REDIS_URL` for Celery and pub/sub (default `redis://redis:6379/0`).
- MinIO: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` (default `uploads`).
- Observability: `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` (default `democritus-agents`), `LANGCHAIN_ENDPOINT`.
- LLM (optional): `OLLAMA_HOST` (default `http://ollama:11434`), `OLLAMA_MODEL` (default `llama3.2:3b`).

### Sequence Diagram (Conceptual)

1. Client calls `/v1/workflows/start-job { jobId }` -> 202 with `workflowId`, `wsUrl`.
2. Celery runs `run_job_workflow` -> `SyncAgentWorkflow.run_job_workflow` -> `AgentWorkflow.run_workflow`.
3. For each step, orchestrator publishes status via Redis; WS endpoint pushes to client.
4. On completion, Celery result: `{ status: PENDING_VALIDATION, schema, metrics }`.
5. Client may call `/v1/workflows/{id}/validate` to approve (MVP stub).

### Limitations and Future Work

- Persistence of approved schemas to a metadata store is not implemented (MVP stub in validate endpoint).
- Relationship and tagging LLM augmentation depends on local Ollama availability; system falls back to rule-based methods.
- No retry policy per step; failures abort the workflow. Future: per-step retries/backoff and partial recovery.
- Security and multi-tenancy concerns (authn/z, per-tenant buckets) are not covered in MVP.
- Streaming of intermediate artifacts (profiles, intermediate schema) is not currently exposed via API beyond final schema.

### File Map

- `app/main.py` — API, Celery tasks, WebSocket status bridge.
- `app/workflow.py` — Orchestrator, state, step sequencing, pub/sub updates.
- `app/observability.py` — LangSmith decoractors and metrics utilities.
- `app/agents/profiler.py` — MinIO integration and pandas profiling.
- `app/agents/aligner.py` — Entity extraction heuristics.
- `app/agents/architect.py` — Schema construction and relationship inference (rule-based + optional LLM).
- `app/agents/tagger.py` — Business tagging, descriptions, and optional LLM enrichment.


