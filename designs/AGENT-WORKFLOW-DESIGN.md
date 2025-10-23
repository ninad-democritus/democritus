# Agent Workflow Service - Design Overview

## Introduction

This document provides a high-level overview of the Agent Workflow Service architecture, design decisions, and execution model. For detailed information about individual agents, please refer to the dedicated agent documentation in [`designs/agent-workflow-designs/`](./agent-workflow-designs/).

## Table of Contents

- [Service Overview](#service-overview)
- [API Surface](#api-surface)
- [Execution Model](#execution-model)
- [Workflow Orchestration](#workflow-orchestration)
- [Agent Pipeline](#agent-pipeline)
- [Confidence Score System](#confidence-score-system)
- [Observability and Tracing](#observability-and-tracing)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Future Work](#future-work)

---

## Service Overview

The Agent Workflow Service orchestrates a multi-agent pipeline that ingests tabular files uploaded per job, profiles the data, identifies domain entities, designs a relational schema with relationships, enriches it with business context, and generates a business glossary. It exposes HTTP endpoints to start workflows and retrieve status, plus a WebSocket channel to stream step-by-step status updates.

### Key Components

1. **FastAPI Application**: REST and WebSocket APIs (`services/agent-workflow/app/main.py`)
2. **Celery Task Queue**: Asynchronous job execution using Redis as broker and result backend
3. **Workflow Orchestrator**: Sequences agents and manages state (`services/agent-workflow/app/workflow.py`)
4. **Six Specialized Agents**: Each implementing a specific step in the pipeline
5. **Observability Integration**: Optional LangSmith tracing (`services/agent-workflow/app/observability.py`)

### Architecture Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP POST /v1/workflows/start-job
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 Celery Task: run_job_workflow            │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │           SyncAgentWorkflow Orchestrator           │  │  │
│  │  │                                                     │  │  │
│  │  │  1. ProfilerAgent   → file_profiles                │  │  │
│  │  │  2. AlignerAgent    → entities                     │  │  │
│  │  │  3. ArchitectAgent  → schema + relationships       │  │  │
│  │  │  4. TaggerAgent     → enriched_schema              │  │  │
│  │  │  5. GlossaryAgent   → glossaries                   │  │  │
│  │  │  6. ContextAgent    → minimal_schema + descriptions│  │  │
│  │  │                                                     │  │  │
│  │  │  Each step publishes status updates to Redis →    │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼ Redis Pub/Sub
┌─────────────────────────────────────────────────────────────────┐
│               WebSocket: /ws/v1/workflows/status/{id}           │
│  Relays status updates to connected clients in real-time        │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Surface

### REST Endpoints

**`POST /v1/workflows/start-job`**
- Triggers full agentic pipeline via `run_job_workflow` Celery task
- **Request**: `{ "jobId": "string", "sourceType": "string" }`
- **Response**: `{ "workflowId": "string", "websocketUrl": "string" }`
- Returns immediately (202 Accepted) with Celery task ID as `workflowId`

**`GET /v1/workflows/status/{workflow_id}`**
- Polling endpoint reading Celery task state
- **States**: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`
- On `SUCCESS` with status `PENDING_VALIDATION`, returns schema with descriptions

**`POST /v1/workflows/{workflow_id}/validate`**
- MVP approval endpoint to acknowledge schema approval
- Currently returns mocked success response

**`POST /v1/workflows/start`** (Legacy)
- MVP placeholder endpoint
- Returns `workflowId` and `websocketUrl`

### WebSocket Endpoint

**`WS /ws/v1/workflows/status/{workflow_id}`**
- Real-time status updates via Redis pub/sub
- Subscribes to Redis channel `workflow_status_{workflow_id}`
- Forwards JSON status payloads to connected clients

**Status Payload Format:**
```json
{
  "status": "PROFILING|ALIGNING|ARCHITECTING|TAGGING|GLOSSARY_BUILDING|CONTEXT_GENERATION|PENDING_VALIDATION|ERROR",
  "message": "Human-friendly status message",
  "timestamp": "ISO-8601",
  "current_step": "profiling_complete|alignment_complete|...",
  "schema": { ... }  // Only on PENDING_VALIDATION
}
```

---

## Execution Model

### Celery Integration

- **Broker & Backend**: Redis (`REDIS_URL` default: `redis://redis:6379/0`)
- **Task**: `run_job_workflow(job_id, source_type)`
- **Async to Sync Bridge**: `SyncAgentWorkflow` wrapper constructs fresh asyncio event loop for Celery worker

### Workflow Execution Flow

1. Client calls `/v1/workflows/start-job` with `jobId`
2. FastAPI enqueues `run_job_workflow` Celery task, returns `workflowId` (task ID)
3. Celery worker picks up task, constructs `SyncAgentWorkflow`, invokes async `run_workflow`
4. Orchestrator sequences agents, publishes status updates to Redis channel
5. WebSocket endpoint relays updates to connected clients
6. On completion, Celery task returns `{ status: PENDING_VALIDATION, schema, metrics }`
7. Client may call `/v1/workflows/{id}/validate` to approve (MVP stub)

---

## Workflow Orchestration

### State Management

The orchestrator maintains workflow state in a `WorkflowState` dataclass:

```python
@dataclass
class WorkflowState:
    job_id: str
    workflow_id: str
    status: str  # PROFILING, ALIGNING, etc.
    current_step: str
    file_profiles: List[FileProfile]  # ProfilerAgent output
    entities: List[Entity]  # AlignerAgent output
    schema: Dict[str, Any]  # ArchitectAgent output
    enriched_schema: Dict[str, Any]  # TaggerAgent → GlossaryAgent output
    minimal_schema: Dict[str, Any]  # ContextAgent output (final)
    error_message: Optional[str]
```

### Orchestration Steps

The `AgentWorkflow` class (in `workflow.py`) sequences agents in a linear pipeline:

1. **PROFILING** → `ProfilerAgent.profile_job_files(job_id)` → `file_profiles`
2. **ALIGNING** → `AlignerAgent.identify_entities(file_profiles)` → `entities`
3. **ARCHITECTING** → `ArchitectAgent.design_schema(entities)` → `schema` (with relationships)
4. **TAGGING** → `TaggerAgent.enrich_schema(schema)` → `enriched_schema` (with classifications)
5. **GLOSSARY_BUILDING** → `GlossaryAgent.generate_glossary(enriched_schema)` → enriched with glossaries
6. **CONTEXT_GENERATION** → `ContextAgent.generate_context(enriched_schema)` → `minimal_schema` (with descriptions)
7. **PENDING_VALIDATION** → Publish final status with minimal schema

Each step:
- Updates `WorkflowState` with new outputs
- Publishes status update to Redis channel via `_update_status()`
- Logs metrics to observability
- On error: publishes `ERROR` status, logs failure, raises exception

---

## Agent Pipeline

The workflow consists of six specialized agents, each building on the outputs of previous agents. Below is a brief overview of each agent's role. For detailed documentation, see the individual agent documents.

### 1. ProfilerAgent
**Purpose**: Discovers and profiles uploaded files, extracting column-level statistics and semantic types.

**Key Responsibilities**:
- File discovery from MinIO storage
- CSV and Excel file loading
- Semantic type detection (email, phone, UUID, SSN, etc.) using DataProfiler ML
- Statistical profiling (null counts, distinct values, min/max/mean, sample values)
- Nullable prediction using heuristics

**Outputs**: `List[FileProfile]` with per-column statistics and semantic types

**Documentation**: [profiler-agent.md](./agent-workflow-designs/profiler-agent.md)

---

### 2. AlignerAgent
**Purpose**: Identifies canonical entities and columns across multiple files using ML-based semantic clustering.

**Key Responsibilities**:
- Cross-file entity consolidation (e.g., "customers.csv" + "client_data.xlsx" → "Customers" entity)
- Semantic embedding-based clustering using sentence-transformers
- Canonical name selection (rule-based + optional LLM refinement)
- Column statistics merging when consolidating columns
- Entity classification (fact vs dimension)
- Primary key detection with confidence scoring

**Outputs**: `List[Entity]` with canonical names, synonyms, merged statistics, PK candidates

**Documentation**: [aligner-agent.md](./agent-workflow-designs/aligner-agent.md)

---

### 3. ArchitectAgent
**Purpose**: Designs relational schema with OpenMetadata-compatible types and infers relationships.

**Key Responsibilities**:
- OpenMetadata type mapping (semantic type → VARCHAR(320), DECIMAL(19,4), UUID, etc.)
- Primary key selection from ranked candidates
- Relationship detection (FK patterns, common columns, semantic validation)
- Cardinality inference (M:1, 1:M, 1:1, M:M) from statistics
- Multi-factor confidence scoring with transparent breakdown
- Semantic narrative generation for relationships

**Outputs**: `Dict` with entities (typed), relationships (with confidence), metadata summary

**Documentation**: [architect-agent.md](./agent-workflow-designs/architect-agent.md)

---

### 4. TaggerAgent
**Purpose**: Applies OpenMetadata governance classification tags (PII, Finance, Temporal, DataDomain, etc.).

**Key Responsibilities**:
- Multi-source classification (semantic types, name patterns, statistics, context)
- Upstream confidence integration (adjusts confidence based on ProfilerAgent and AlignerAgent quality)
- Classification merging and deduplication
- Mutual exclusivity enforcement (e.g., only one PII sub-classification)
- Provenance tracking (records upstream factors influencing each classification)

**Outputs**: Enriched schema with `classifications` arrays on entities and columns, `classification_summary`

**Documentation**: [tagger-agent.md](./agent-workflow-designs/tagger-agent.md)

---

### 5. GlossaryAgent
**Purpose**: Generates business-friendly glossary terms and domains using LLM.

**Key Responsibilities**:
- Term extraction from entities, columns, and PK candidates
- Term clustering using embeddings (reuses AlignerAgent infrastructure)
- Domain formation using TaggerAgent classifications and semantic similarity
- LLM definition generation (batched, 2-3 sentences) with full context
- LLM domain naming and descriptions
- Entity linking (canonical names, synonyms, raw names, embeddings)
- Related terms identification via relationships and semantic similarity

**Outputs**: Enriched schema with `glossaries` array and `glossary_summary`

**Documentation**: [glossary-agent.md](./agent-workflow-designs/glossary-agent.md)

---

### 6. ContextAgent
**Purpose**: Transforms enriched metadata into business narratives and produces minimal UI-friendly output.

**Key Responsibilities**:
- Semantic graph construction (optional) for multi-hop context queries
- Context bundle consolidation (entities, columns, relationships, glossaries)
- LLM narrative generation for entity and column descriptions
- Confidence-aware language mapping (high confidence → "confirmed", low → "tentative")
- Minimal output formatting (removes internal fields, ~56% smaller)

**Outputs**: Minimal schema with `description` fields, ready for OpenMetadata ingestion and UI display

**Documentation**: [context-agent.md](./agent-workflow-designs/context-agent.md)

---

## Confidence Score System

The workflow implements a comprehensive confidence tracking system where each agent produces confidence scores that propagate downstream.

### Confidence Flow

```
ProfilerAgent (semantic_type_confidence)
    ↓
AlignerAgent (alignment_confidence, type_classification_confidence, pk_confidence)
    ↓
ArchitectAgent (relationship_confidence, confidence_breakdown)
    ↓
TaggerAgent (classification_confidence, adjusted by upstream confidence)
    ↓
GlossaryAgent (term_confidence, aggregated from upstream)
    ↓
ContextAgent (confidence-aware language in descriptions)
```

### Confidence Score Types

1. **ProfilerAgent**: `semantic_type_confidence` (0.0-1.0) from DataProfiler ML model
2. **AlignerAgent**: 
   - `alignment_confidence` (entity/column): 1.0 - cluster_variance
   - `type_classification_confidence`: Multi-factor entity type scoring
   - `pk_confidence`: Multi-factor primary key scoring
3. **ArchitectAgent**: 
   - `relationship.confidence`: Weighted multi-factor (name similarity, semantic compatibility, etc.)
   - `confidence_breakdown`: Per-factor transparency
4. **TaggerAgent**: 
   - `classification.confidence`: Base confidence adjusted by upstream quality
   - `upstream_factors`: Tracks which upstream scores influenced decision
5. **GlossaryAgent**: 
   - `term.confidence`: Weighted aggregate (alignment 30%, semantic_type 20%, classification 20%, clustering 15%, definition_quality 15%)
   - `confidence_breakdown`: Per-factor transparency
6. **ContextAgent**: 
   - Confidence scores converted to natural language
   - Influences descriptions ("confirmed" vs "likely" vs "possible")

### Upstream Confidence Adjustment

**TaggerAgent Example**:
```python
# If ProfilerAgent wasn't confident about semantic type, reduce classification confidence
if semantic_type_confidence < 0.7:
    penalty = (0.7 - semantic_type_confidence) * 0.3
    classification_confidence *= (1.0 - penalty)

# If AlignerAgent wasn't confident about alignment, reduce pattern match confidence
if alignment_confidence < 0.6:
    penalty = (0.6 - alignment_confidence) * 0.25
    classification_confidence *= (1.0 - penalty)
```

### Confidence Thresholds

| Confidence Range | Interpretation | Recommended Action |
|------------------|----------------|-------------------|
| **0.9 - 1.0** | Very High | Auto-accept, minimal review |
| **0.7 - 0.9** | High | Accept with spot check |
| **0.5 - 0.7** | Medium | Flag for review |
| **0.3 - 0.5** | Low | Requires human review |
| **0.0 - 0.3** | Very Low | Manual intervention needed |

---

## Observability and Tracing

### LangSmith Integration

When `LANGCHAIN_API_KEY` is present, the service enables LangSmith tracing:
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_PROJECT` (default: `democritus-agents`)
- `LANGCHAIN_ENDPOINT` (optional)

### Decorators

- **`@trace_agent("AgentName")`**: Wraps agent methods to emit traces and logs
- **`@trace_workflow_step("step", metadata)`**: Wraps workflow steps

### Metrics

Each agent and workflow step logs:
- Start/completion timestamps
- Input/output counts (entities, columns, relationships, terms, etc.)
- Confidence statistics (average, distribution)
- Error counts and failure reasons
- Processing time

---

## Configuration

### Core Environment Variables

**Redis (Celery & Pub/Sub)**:
- `REDIS_URL`: Redis connection string (default: `redis://redis:6379/0`)

**MinIO (Storage)**:
- `MINIO_ENDPOINT`: MinIO server (default: `minio:9000`)
- `MINIO_ACCESS_KEY`: Access key (default: `minioadmin`)
- `MINIO_SECRET_KEY`: Secret key (default: `minioadmin`)
- `MINIO_BUCKET`: Bucket name (default: `uploads`)

**LLM (Ollama)**:
- `OLLAMA_HOST`: Ollama endpoint (default: `http://ollama:11434`)
- `OLLAMA_MODEL`: Model name (default: `llama3.2:3b`)

**Observability**:
- `LANGCHAIN_API_KEY`: LangSmith API key (optional)
- `LANGCHAIN_PROJECT`: Project name (default: `democritus-agents`)

### Agent-Specific Configuration

Each agent has its own configuration with environment variable support. See individual agent documentation for details:

- **ProfilerAgent**: `DATAPROFILER_MAX_ROWS`, `DATAPROFILER_SAMPLE_SIZE`
- **AlignerAgent**: `ALIGNER_EMBEDDING_MODEL`, `ALIGNER_USE_LLM`, `ALIGNER_CLUSTERING_METHOD`
- **ArchitectAgent**: `ARCHITECT_USE_RULE_BASED`, `ARCHITECT_USE_SEMANTIC`, `ARCHITECT_MIN_CONFIDENCE`
- **TaggerAgent**: `TAGGER_MIN_CONFIDENCE`, `TAGGER_SEMANTIC_CONFIDENCE_THRESHOLD`
- **GlossaryAgent**: `GLOSSARY_LLM_BATCH_SIZE`, `GLOSSARY_USE_CLASSIFICATION_DOMAINS`, `GLOSSARY_MIN_TERM_CONFIDENCE`
- **ContextAgent**: `CONTEXT_USE_LLM`, `CONTEXT_OUTPUT_FORMAT`, `CONTEXT_ENABLE_GRAPH`

---

## Dependencies

### Python Packages

**Core**:
- `fastapi`: Web framework
- `celery`: Task queue
- `redis`: Broker/backend + pub/sub
- `pydantic`: Data models
- `minio`: Object storage client
- `pandas`: Data processing
- `DataProfiler`: Semantic type detection

**ML/NLP**:
- `sentence-transformers`: Semantic embeddings (AlignerAgent, GlossaryAgent)
- `scikit-learn`: Clustering and distance metrics
- `hdbscan`: Density-based clustering (optional)

**Graph (Optional)**:
- `networkx`: Semantic graph construction (ContextAgent)

**LLM**:
- `requests`: Ollama API calls
- `openai`: OpenAI API (future)

---

## Future Work

### Short-Term
1. **Persistence**: Store approved schemas and glossaries in metadata store
2. **Validation UI**: Human-in-the-loop validation workflow
3. **OpenMetadata Ingestion**: Direct ingestion to OpenMetadata API
4. **Per-Step Retries**: Retry policy with exponential backoff for transient failures
5. **Embedding Cache**: Redis cache for embeddings to improve performance

### Medium-Term
1. **Incremental Updates**: Update schema when files change (delta processing)
2. **Multi-Language Glossaries**: Generate definitions in multiple languages
3. **Custom Classification Taxonomies**: Organization-specific classification hierarchies
4. **User Feedback Loop**: Learn from user corrections to improve ML models
5. **Advanced Graph Queries**: Complex multi-hop queries for richer context

### Long-Term
1. **Hierarchical Entities**: Support parent-child entity relationships
2. **Term Versioning**: Track glossary term changes over time
3. **Complex Type Support**: ARRAY, MAP, STRUCT types for nested data
4. **Multi-Tenancy**: Per-tenant buckets and authentication
5. **Streaming**: Real-time profiling and schema evolution

---

## Agent Documentation Index

For detailed information about each agent, including:
- Folder structure and file responsibilities
- Input/Output contracts with examples
- Algorithms and workflows
- Configuration options
- Error handling
- Extension points

Please refer to the individual agent documentation:

1. [**ProfilerAgent**](./agent-workflow-designs/profiler-agent.md) - File discovery and data profiling
2. [**AlignerAgent**](./agent-workflow-designs/aligner-agent.md) - Entity identification and alignment
3. [**ArchitectAgent**](./agent-workflow-designs/architect-agent.md) - Schema design and relationship detection
4. [**TaggerAgent**](./agent-workflow-designs/tagger-agent.md) - Governance classification tagging
5. [**GlossaryAgent**](./agent-workflow-designs/glossary-agent.md) - Business glossary generation
6. [**ContextAgent**](./agent-workflow-designs/context-agent.md) - Narrative generation and output formatting

---

## File Map

**Core Workflow**:
- `app/main.py` - FastAPI endpoints, Celery tasks, WebSocket handler
- `app/workflow.py` - Orchestrator, state management, agent sequencing
- `app/observability.py` - LangSmith decorators and metrics

**Agents**:
- `app/agents/profiler/` - [ProfilerAgent documentation](./agent-workflow-designs/profiler-agent.md)
- `app/agents/aligner/` - [AlignerAgent documentation](./agent-workflow-designs/aligner-agent.md)
- `app/agents/architect/` - [ArchitectAgent documentation](./agent-workflow-designs/architect-agent.md)
- `app/agents/tagger/` - [TaggerAgent documentation](./agent-workflow-designs/tagger-agent.md)
- `app/agents/glossary/` - [GlossaryAgent documentation](./agent-workflow-designs/glossary-agent.md)
- `app/agents/context/` - [ContextAgent documentation](./agent-workflow-designs/context-agent.md)

**Legacy Files** (Backup):
- `app/agents/profiler_legacy.py` - Original monolithic profiler
- `app/agents/aligner_legacy.py` - Original pattern-based aligner
- `app/agents/architect_legacy.py` - Original monolithic architect

---

## Design Principles

### Modularity
Each agent is independently modular with pluggable components:
- **ProfilerAgent**: Pluggable storage backends and file loaders
- **AlignerAgent**: Configurable clustering algorithms and LLM providers
- **ArchitectAgent**: Multiple relationship detection strategies
- **TaggerAgent**: Multiple classifier implementations
- **GlossaryAgent**: Reusable ML infrastructure from AlignerAgent
- **ContextAgent**: Optional graph construction, pluggable LLM service

### Extensibility
Well-defined interfaces enable easy extension:
- Add new storage backend: Implement `BaseStorage` interface
- Add new file format: Implement `BaseLoader` interface
- Add new classifier: Implement `BaseClassifier` interface
- Add new relationship detection: Extend `relationships/` modules
- Customize confidence scoring: Modify `scorer.py` in respective agents

### Backward Compatibility
Each agent maintains backward-compatible outputs while adding new fields:
- AlignerAgent outputs legacy `Entity` format for downstream compatibility
- ArchitectAgent preserves all upstream metadata
- TaggerAgent passes through all prior fields unchanged (additive)
- GlossaryAgent adds glossaries without modifying enriched_schema

### Quality Signals
Confidence scores propagate through the pipeline:
- Upstream uncertainty reduces downstream confidence appropriately
- Transparent confidence breakdown shows factor contributions
- Provenance tracking records which upstream signals influenced decisions
- UI can filter/highlight items by confidence for validation

### LLM-Aware Architecture
LLM integration is thoughtful and resilient:
- Batched LLM calls for efficiency (8 items per call)
- Retry logic with exponential backoff
- Template fallbacks when LLM fails
- Full context passed to LLM (classifications, relationships, sample values)
- Optional LLM usage (AlignerAgent canonical naming, future ArchitectAgent validation)
- Required LLM usage (GlossaryAgent definitions, ContextAgent descriptions)

---

## Workflow Sequencing Rationale

### Why This Order?

1. **ProfilerAgent First**: Must understand raw data before any analysis
2. **AlignerAgent Second**: Entity identification enables schema design
3. **ArchitectAgent Third**: Schema and relationships needed for classification context
4. **TaggerAgent Fourth**: Classifications needed for domain formation in glossary
5. **GlossaryAgent Fifth**: Business terms enrich context for descriptions
6. **ContextAgent Last**: Final step consumes all prior metadata to generate narratives

### Data Dependencies

```
ProfilerAgent
  └─> semantic_type, statistics, sample_values
      └─> AlignerAgent
          └─> canonical_name, synonyms, alignment_confidence, entity_type, pk_candidates
              └─> ArchitectAgent
                  └─> relationships, OpenMetadata_types, confidence_breakdown
                      └─> TaggerAgent
                          └─> classifications, classification_confidence
                              └─> GlossaryAgent
                                  └─> glossaries, term_definitions
                                      └─> ContextAgent
                                          └─> minimal_schema + descriptions
```

Each agent builds on prior outputs, creating a rich, layered metadata model that culminates in business-ready documentation.

---

## Summary

The Agent Workflow Service implements a sophisticated multi-agent pipeline that transforms raw uploaded files into a fully documented, business-ready schema with OpenMetadata-compatible types, governance classifications, and business glossaries. 

**Key Strengths**:
- **Modular Architecture**: Each agent is independently extensible
- **ML-Powered**: Semantic embeddings, clustering, and LLM integration
- **Quality-Aware**: Comprehensive confidence tracking and propagation
- **Production-Ready**: Async execution, real-time status updates, observability
- **Business-Friendly**: LLM-generated descriptions and glossaries
- **OpenMetadata Compatible**: Ready for ingestion into data catalogs

For detailed implementation information, algorithm descriptions, and configuration options, please refer to the individual agent documentation linked throughout this document.
