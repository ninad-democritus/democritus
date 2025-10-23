# Agent Workflow - Detailed Agent Documentation

This directory contains detailed documentation for each agent in the Agent Workflow Service pipeline. Each document provides comprehensive information about the agent's purpose, architecture, implementation details, and configuration.

## Documentation Structure

Each agent document includes:
- **Overview**: What the agent does and why design choices were made
- **Folder Structure**: Complete directory layout with file responsibilities
- **Input/Output Contracts**: Detailed examples with data structures
- **Algorithms**: Step-by-step workflow descriptions
- **Configuration**: Environment variables and customization options
- **Dependencies**: Required packages and upstream/downstream consumers
- **Error Handling**: Common failure scenarios and logging
- **Future Extensions**: Planned enhancements and extension points

## Agent Pipeline

The agents execute in the following sequence, each building on the outputs of previous agents:

```
1. ProfilerAgent → 2. AlignerAgent → 3. ArchitectAgent → 4. TaggerAgent → 5. GlossaryAgent → 6. ContextAgent
```

## Agent Documentation

### 1. [ProfilerAgent](./profiler-agent.md)
**Purpose**: File discovery and data profiling

**Key Features**:
- MinIO storage integration
- CSV and Excel file loading
- Semantic type detection (email, phone, UUID, SSN, etc.)
- Statistical profiling (null counts, distinct values, numeric stats)
- Sample value extraction

**Outputs**: `List[FileProfile]` with column-level statistics and semantic types

**When to Read**: Understanding data ingestion, profiling strategy, or extending file format support

---

### 2. [AlignerAgent](./aligner-agent.md)
**Purpose**: Entity identification and canonical naming using ML-based clustering

**Key Features**:
- Cross-file entity consolidation
- Semantic embedding-based clustering (sentence-transformers)
- Canonical name selection (rule-based + optional LLM)
- Column statistics merging
- Entity classification (fact vs dimension)
- Primary key detection

**Outputs**: `List[Entity]` with canonical names, synonyms, merged statistics, PK candidates

**When to Read**: Understanding entity alignment, clustering algorithms, or customizing name selection

---

### 3. [ArchitectAgent](./architect-agent.md)
**Purpose**: Relational schema design with OpenMetadata types and relationship detection

**Key Features**:
- OpenMetadata type mapping (semantic-aware)
- Primary key selection
- Multi-strategy relationship detection (rule-based, statistical, semantic)
- Cardinality inference (M:1, 1:M, 1:1, M:M)
- Multi-factor confidence scoring
- Semantic narrative generation

**Outputs**: Schema dict with typed entities, relationships with confidence breakdowns

**When to Read**: Understanding schema design, relationship detection algorithms, or type mapping

---

### 4. [TaggerAgent](./tagger-agent.md)
**Purpose**: Governance classification tagging (PII, Finance, Temporal, DataDomain)

**Key Features**:
- Multi-source classification (semantic types, name patterns, statistics, context)
- Upstream confidence integration
- Classification merging and deduplication
- Mutual exclusivity enforcement
- Provenance tracking

**Outputs**: Enriched schema with `classifications` arrays and `classification_summary`

**When to Read**: Understanding governance tagging, classification taxonomy, or confidence adjustment

---

### 5. [GlossaryAgent](./glossary-agent.md)
**Purpose**: Business-friendly glossary generation using LLM

**Key Features**:
- Term extraction with full context
- Term clustering (reuses AlignerAgent infrastructure)
- Classification-driven domain formation
- Batched LLM definition generation
- Entity linking (canonical names, synonyms, embeddings)
- Related terms identification (relationships, classifications, semantic similarity)

**Outputs**: Enriched schema with `glossaries` array and `glossary_summary`

**When to Read**: Understanding glossary generation, LLM integration, or domain formation

---

### 6. [ContextAgent](./context-agent.md)
**Purpose**: Business narrative generation and minimal output formatting

**Key Features**:
- Semantic graph construction (optional)
- Context bundle consolidation
- LLM-powered entity and column descriptions
- Confidence-aware language mapping
- Minimal output formatting (~56% size reduction)

**Outputs**: Minimal schema with `description` fields, ready for OpenMetadata and UI

**When to Read**: Understanding narrative generation, output formatting, or semantic graph usage

---

## Quick Reference

### Data Flow Summary

```
ProfilerAgent: Profiles files
    ↓ file_profiles (with semantic_type, statistics)
AlignerAgent: Identifies canonical entities
    ↓ entities (with canonical_name, synonyms, alignment_confidence, pk_candidates)
ArchitectAgent: Designs schema with relationships
    ↓ schema (with OpenMetadata_types, relationships, confidence_breakdown)
TaggerAgent: Applies governance classifications
    ↓ enriched_schema (with classifications, upstream_factors)
GlossaryAgent: Generates business glossaries
    ↓ enriched_schema + glossaries (with LLM_definitions, term_links)
ContextAgent: Generates narratives and formats output
    ↓ minimal_schema (with descriptions, 56% smaller)
```

### Confidence Propagation

Each agent produces confidence scores that influence downstream agents:

- **ProfilerAgent**: `semantic_type_confidence` (ML-based)
- **AlignerAgent**: `alignment_confidence` (clustering-based)
- **ArchitectAgent**: `relationship.confidence` (multi-factor)
- **TaggerAgent**: `classification.confidence` (adjusted by upstream)
- **GlossaryAgent**: `term.confidence` (aggregated)
- **ContextAgent**: Confidence → natural language ("confirmed", "likely", "tentative")

### Common Configuration Patterns

**Enable/Disable LLM**:
- `ALIGNER_USE_LLM=false` - Disable LLM canonical naming
- `GLOSSARY_USE_LLM_DEFINITIONS=true` - Required for business-friendly glossaries
- `CONTEXT_USE_LLM=true` - Enable LLM narratives

**Adjust Confidence Thresholds**:
- `ARCHITECT_MIN_CONFIDENCE=0.6` - Filter low-confidence relationships
- `TAGGER_MIN_CONFIDENCE=0.6` - Filter low-confidence classifications
- `GLOSSARY_MIN_TERM_CONFIDENCE=0.50` - Filter low-confidence terms

**Customize Clustering**:
- `ALIGNER_CLUSTERING_METHOD=hdbscan` - Use HDBSCAN (default) or `agglomerative`
- `ALIGNER_MIN_CLUSTER_SIZE=2` - Minimum cluster size for grouping
- `ALIGNER_EMBEDDING_MODEL=all-MiniLM-L6-v2` - Sentence-transformers model

**LLM Performance**:
- `GLOSSARY_LLM_BATCH_SIZE=8` - Terms per LLM call (trade-off: latency vs throughput)
- `GLOSSARY_LLM_TIMEOUT=45` - Seconds per batch
- `CONTEXT_BATCH_SIZE=10` - Entities/columns per batch

---

## Navigation Guide

**New to the Agent Workflow?**
1. Start with the main [AGENT-WORKFLOW-DESIGN.md](../AGENT-WORKFLOW-DESIGN.md) for high-level overview
2. Read [ProfilerAgent](./profiler-agent.md) to understand data ingestion
3. Read [AlignerAgent](./aligner-agent.md) to understand entity identification

**Working with Schema Design?**
1. Read [ArchitectAgent](./architect-agent.md) for relationship detection and type mapping
2. Read [TaggerAgent](./tagger-agent.md) for governance classification

**Working with Business Glossaries?**
1. Read [GlossaryAgent](./glossary-agent.md) for term generation and LLM integration
2. Read [ContextAgent](./context-agent.md) for narrative generation

**Debugging Confidence Issues?**
1. See "Confidence Score System" in main design document
2. Check `confidence_breakdown` and `upstream_factors` in each agent's output
3. Adjust confidence thresholds in agent configurations

**Extending the System?**
- Each document has an "Extension Points" section
- Check "Future Extensions" for planned features
- Review "Error Handling" for common issues

---

## Related Documentation

- [Main Design Document](../AGENT-WORKFLOW-DESIGN.md) - High-level service architecture
- [OpenMetadata Mapping](../../todos/OPENMETADATA-MAPPING.md) - Output format for ingestion
- [RAG Implementation](../../todos/RAG-IMPLEMENTATION.md) - RAG embedding strategy
- [Workflow Design](../AGENT-WORKFLOW-DESIGN.md) - Original comprehensive design (now split)

---

## Contributing

When updating agent documentation:
1. Keep the structure consistent across all agent docs
2. Update examples with realistic data
3. Include configuration defaults and ranges
4. Document error scenarios and mitigations
5. Update this README if you add new sections
6. Cross-reference related agents when relevant

---

## Questions?

For questions about:
- **Service architecture**: See main [AGENT-WORKFLOW-DESIGN.md](../AGENT-WORKFLOW-DESIGN.md)
- **Specific agent behavior**: See individual agent documentation above
- **Configuration**: Check the Configuration section in each agent doc
- **API integration**: See API Surface section in main design document
- **Deployment**: See deployment documentation (separate)

