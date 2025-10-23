# GlossaryAgent Documentation

## Overview

The **GlossaryAgent** is the fifth agent in the workflow pipeline, responsible for generating business-friendly glossary terms and domains that help non-technical users understand the data. It uses LLM to create clear, contextualized definitions organized into business domains.

### What It Does

1. **Term Extraction**: Identifies candidate terms from entities, columns, and primary key candidates with full context
2. **Term Normalization**: Removes technical suffixes, deduplicates, and merges synonyms
3. **Term Clustering**: Uses semantic embeddings (reusing AlignerAgent infrastructure) to cluster similar terms
4. **Domain Formation**: Groups term clusters into business domains using classification prefixes and semantic similarity
5. **LLM Definition Generation**: Creates business-friendly 2-3 sentence definitions with full context (classifications, relationships, sample values)
6. **LLM Domain Naming**: Generates domain names and descriptions
7. **Entity Linking**: Links terms to entities and columns using canonical names, synonyms, and embeddings
8. **Related Terms**: Identifies related terms via relationships (FK connections) and classification overlap
9. **Confidence Propagation**: Aggregates upstream confidence scores with transparent breakdown

### Why These Design Choices

- **LLM-First Approach**: Business glossaries require human-friendly language that template generation can't match. LLM is essential, not optional.
- **Comprehensive Context**: LLM definitions need all available metadata (classifications, relationships, sample values, entity types) to generate accurate, useful definitions.
- **Classification-Driven Domains**: TaggerAgent classifications provide strong signal for domain organization (Finance.*, PII.*, etc.). More reliable than pure clustering.
- **Relationship-Aware**: ArchitectAgent relationships are essential for identifying related terms ("Customer" relates to "Order" via FK relationship).
- **PK-Aware Terms**: Primary key candidates from AlignerAgent become special "key identifier" terms with enhanced metadata.
- **User Terminology Capture**: raw_names from source files represent how users actually refer to data. Essential for synonyms.
- **Reuses ML Infrastructure**: Shares embedding service and clustering service with AlignerAgent for consistency and efficiency.
- **Confidence Propagation**: Continues upstream confidence tracking pattern. Low alignment confidence → low glossary term confidence.
- **Additive Pattern**: Adds glossaries without modifying existing enriched_schema fields. Downstream agents can use all prior metadata.
- **OpenMetadata-Compatible**: Output format matches OpenMetadata's Glossary → GlossaryTerm → associatedEntities structure.

## Folder Structure

```
services/agent-workflow/app/agents/glossary/
├── __init__.py
├── agent.py                          # Main orchestrator coordinating all components
├── models.py                         # Data structures (CandidateTerm, TermCluster, GlossaryTerm, Glossary)
├── config.py                         # Configuration with environment variable support
├── term_extraction.py                # Extract and normalize candidate terms
├── term_clustering.py                # Cluster terms using embeddings (reuses AlignerAgent services)
├── domain_formation.py               # Form business domains from term clusters
├── llm_service.py                    # LLM service for definitions and domain naming (Ollama/OpenAI)
├── entity_linker.py                  # Link terms to entities and columns in schema
└── related_terms.py                  # Identify related terms via relationships and similarity
```

### File Responsibilities

#### Core Files
- **`agent.py`**: Main orchestrator coordinating glossary generation
  - Entry point: `generate_glossary(enriched_schema)`
  - Extracts candidate terms from enriched schema
  - Clusters terms semantically
  - Forms business domains
  - Generates LLM definitions (batched)
  - Generates LLM domain descriptions
  - Links terms to entities/columns
  - Identifies related terms
  - Calculates confidence with breakdown
  - Adds `glossaries` and `glossary_summary` to enriched_schema
  - Returns enriched schema (additive)

- **`models.py`**: Rich data structures for glossary generation
  - `CandidateTerm`: Extracted term with full upstream context
  - `TermCluster`: Semantically similar terms clustered together
  - `DomainCluster`: Business domain containing term clusters
  - `GlossaryTerm`: Final term with LLM-generated definition
  - `Glossary`: Domain-level glossary with terms
  - `GlossaryOutput`: Complete output with summary

- **`config.py`**: Centralized configuration
  - LLM provider selection (Ollama/OpenAI)
  - Embedding model configuration
  - Feature toggles for LLM usage
  - Confidence thresholds
  - Similarity thresholds for linking

#### Processing Modules

- **`term_extraction.py`**: Term extraction and normalization
  - **Extraction**:
    - Entity names → Terms with entity type context
    - Column names → Terms with semantic type, classifications
    - PK candidates → Special "key identifier" terms
  - **Context Capture** (for each term):
    - Canonical name and all synonyms/raw_names
    - Sample values (up to 5)
    - Semantic type and confidence
    - Alignment confidence
    - Classifications and classification confidence
    - Entity type (fact/dimension)
    - Relationships (FK connections)
    - Related entities
    - PK metadata (if PK candidate)
  - **Normalization**:
    - Remove technical suffixes (_id, _flag, _code, _key)
    - Deduplicate by normalized name
    - Merge synonyms and raw_names across duplicates
    - Preserve highest confidence when merging
  - **Example**:
    ```python
    CandidateTerm(
        canonical_name="Customer",
        normalized_term="customer",
        source_type="entity",
        source_fqn="entity.Customers",
        sample_values=None,  # Entities don't have samples
        semantic_type=None,
        semantic_type_confidence=None,
        alignment_confidence=0.94,
        synonyms=["Client", "Cust"],
        raw_names=["customer_master", "customers", "client_data"],
        entity_type="dimension",
        is_primary_key=False,
        classifications=["DataDomain.Dimension"],
        classification_confidence=0.89,
        relationships=[{"to_entity": "Orders", "cardinality": "one_to_many", "confidence": 0.87}],
        related_entities=["Orders", "Invoices"]
    )
    ```

- **`term_clustering.py`**: Semantic term clustering
  - **Reuses AlignerAgent Infrastructure**:
    - `EmbeddingService` from `aligner/embeddings.py`
    - `ClusteringService` from `aligner/clustering.py`
  - **Process**:
    - Compute embeddings for normalized terms
    - Cluster using HDBSCAN or Agglomerative (same config as AlignerAgent)
    - Calculate cluster variance for confidence
    - Select representative term per cluster
  - **Output**: List of `TermCluster` objects
  - **Why Reuse**: Consistency with entity alignment, proven approach

- **`domain_formation.py`**: Business domain formation
  - **Primary Strategy**: Classification-based grouping
    - Finance.* classifications → "Financial Data" domain
    - PII.* classifications → "Personal Information" domain
    - Contact.* classifications → "Contact Information" domain
    - Temporal.* classifications → "Temporal Data" domain
    - Identity.* classifications → "Identifiers" domain
  - **Secondary Strategy**: Embedding-based clustering
    - For terms without strong classification signal
    - Cluster term clusters into domain clusters
  - **Output**: List of `DomainCluster` objects
  - **Configuration**: `GLOSSARY_USE_CLASSIFICATION_DOMAINS` (default: true)

- **`llm_service.py`**: LLM integration for definitions and domain naming
  - **Providers**:
    - Ollama (default): Local LLM deployment
    - OpenAI (future): Cloud LLM API
  - **Definition Generation**:
    - Batched LLM calls (8 terms per request for efficiency)
    - Structured prompt with full context:
      ```
      Generate business-friendly definitions for these terms:
      
      Term: Customer (synonyms: Client, Cust)
      Type: Dimension entity
      Classifications: DataDomain.Dimension
      Sample values: N/A (entity)
      Relationships: Has many Orders (M:1, confidence: 0.87)
      Related entities: Orders, Invoices
      
      Requirements:
      - 2-3 sentences
      - Business language, not technical jargon
      - Include domain context and relationships
      - Explain what the term represents and why it's important
      ```
    - Retry logic (3 attempts with exponential backoff)
    - Timeout handling (45 seconds default)
    - Falls back to template on failure
  - **Domain Description Generation**:
    - Prompt includes:
      - Domain classification prefix (Finance.*, PII.*)
      - List of terms in domain
      - Entity types represented
    - Generates domain name and description
  - **Batching Benefits**: Reduces LLM calls from N to N/8, significant performance improvement

- **`entity_linker.py`**: Links terms to entities and columns
  - **Linking Strategies** (in order):
    1. **Exact canonical name match** (confidence: 1.0)
    2. **Synonym match** (confidence: 0.95)
    3. **Raw name match** (confidence: 0.90)
    4. **Embedding similarity** (threshold: 0.85, confidence: similarity_score)
  - **Output**: `associated_entities` and `associated_columns` for each term
  - **Example**:
    ```python
    GlossaryTerm.associated_entities = [
        {"entity_name": "Customers", "match_type": "canonical_name", "confidence": 1.0},
        {"entity_name": "CustomerOrders", "match_type": "embedding", "confidence": 0.88}
    ]
    ```

- **`related_terms.py`**: Identifies related terms
  - **Relationship-Based** (primary):
    - Terms linked via FK relationships from ArchitectAgent
    - Includes semantic relationship description
    - Example: "Customer" relates to "Order" via "Each Order belongs to one Customer" relationship
    - Configuration: `GLOSSARY_USE_RELATIONSHIP_LINKS` (default: true)
  - **Classification-Based** (secondary):
    - Terms with overlapping classifications
    - Example: "Email" and "Phone" both have Contact.* classifications
  - **Embedding-Based** (tertiary):
    - Semantic similarity above threshold (default: 0.80)
    - Example: "Revenue" and "Sales" are semantically similar
  - **Output**: `related_terms` array with relationship type and confidence
  - **Example**:
    ```python
    GlossaryTerm.related_terms = [
        {
            "term": "Order",
            "relationship_type": "foreign_key",
            "confidence": 0.87,
            "description": "Each Order belongs to one Customer via customer_id"
        },
        {
            "term": "Invoice",
            "relationship_type": "semantic_similarity",
            "confidence": 0.82,
            "description": "Semantically related billing concept"
        }
    ]
    ```

## Input/Output Contracts

### Input

**Function Signature:**
```python
async def generate_glossary(enriched_schema: Dict[str, Any]) -> Dict[str, Any]
```

**Parameters:**
- `enriched_schema` (Dict): Output from TaggerAgent containing:
  - `entities`: With classifications
  - `relationships`: With confidence and semantic descriptions
  - `classification_summary`: Coverage statistics

**Dependencies on Upstream Outputs:**
- **ProfilerAgent** (via AlignerAgent and ArchitectAgent):
  - Sample values for context in LLM definitions
  - Semantic types for term metadata
- **AlignerAgent**:
  - Canonical names, synonyms, raw_names (essential for term extraction and linking)
  - Alignment confidence (propagated to glossary confidence)
  - Entity types (used for term context and domain formation)
  - Primary key candidates (special key identifier terms)
- **ArchitectAgent**:
  - Relationships (essential for related terms identification)
  - Semantic descriptions (used in LLM prompts)
- **TaggerAgent**:
  - Classifications (primary signal for domain formation)
  - Classification confidence (affects glossary confidence)

### Output

**Return Type:** `Dict[str, Any]` (enriched schema with glossaries)

**Enriched Schema Structure:**
```python
{
  "entities": [
    # All TaggerAgent entities preserved unchanged...
  ],
  "relationships": [
    # All ArchitectAgent relationships preserved unchanged...
  ],
  "classification_summary": {
    # All TaggerAgent classification_summary preserved unchanged...
  },
  
  # NEW: Glossaries array
  "glossaries": [
    {
      "glossary_id": "glossary_financial",
      "name": "financial_data",
      "display_name": "Financial Data",
      "description": "Financial metrics, revenue, and cost tracking data including sales amounts, expenses, and profitability measures. This domain encompasses all monetary transactions and financial reporting elements.",
      "terms": [
        {
          "term_id": "term_revenue",
          "canonical_name": "Revenue",
          "display_name": "Revenue",
          "definition": "Revenue represents the total income generated from sales transactions before any deductions. It serves as a key financial metric for measuring business performance and appears in Orders and Invoices entities. Revenue data is typically aggregated monthly and annually for financial reporting and is classified as sensitive financial information requiring appropriate access controls.",
          "synonyms": ["Sales", "Income", "Total Sales"],
          "confidence": 0.87,
          "confidence_breakdown": {
            "alignment_confidence": 0.91,
            "semantic_type_confidence": 0.87,
            "classification_confidence": 0.92,
            "clustering_confidence": 0.89,
            "definition_quality": 0.85
          },
          "associated_entities": [
            {
              "entity_name": "Orders",
              "match_type": "canonical_name",
              "confidence": 1.0
            },
            {
              "entity_name": "Invoices",
              "match_type": "synonym",
              "confidence": 0.95
            }
          ],
          "associated_columns": [
            {
              "entity_name": "Orders",
              "column_name": "order_total",
              "match_type": "embedding",
              "confidence": 0.88
            }
          ],
          "related_terms": [
            {
              "term": "Cost",
              "relationship_type": "classification_overlap",
              "confidence": 0.75,
              "description": "Related financial metric in same domain"
            },
            {
              "term": "Customer",
              "relationship_type": "foreign_key",
              "confidence": 0.87,
              "description": "Each Order belongs to one Customer via customer_id"
            }
          ],
          "related_via_relationships": [
            {
              "from_entity": "Orders",
              "to_entity": "Customers",
              "relationship_type": "many_to_one",
              "confidence": 0.87,
              "semantic_description": "Each Order belongs to one Customer via customer_id foreign key match"
            }
          ],
          "classifications": ["Finance.Revenue", "DataQuality.Nullable"],
          "is_key_identifier": false,
          "entity_type": null,  # Column term
          "sample_values": [123.45, 567.89, 8900.12],
          "source_file_terminology": {
            "customer_master.xlsx": ["ltv", "customer_ltv"],
            "sales_data.csv": ["total_sales", "revenue_amount"]
          },
          "pk_metadata": null
        },
        {
          "term_id": "term_customer_id",
          "canonical_name": "Customer ID",
          "display_name": "Customer ID",
          "definition": "Customer ID is a unique identifier assigned to each customer record, serving as the primary key for customer data. It enables reliable customer tracking across transactions and maintains referential integrity in the database. This identifier appears in multiple entities including Orders and Invoices to establish customer relationships.",
          "synonyms": ["Cust ID", "Customer Identifier", "Client ID"],
          "confidence": 0.94,
          "confidence_breakdown": {
            "alignment_confidence": 0.94,
            "semantic_type_confidence": 0.92,
            "classification_confidence": 0.88,
            "clustering_confidence": 0.95,
            "definition_quality": 0.90
          },
          "associated_entities": [
            {
              "entity_name": "Customers",
              "match_type": "canonical_name",
              "confidence": 1.0
            }
          ],
          "associated_columns": [
            {
              "entity_name": "Customers",
              "column_name": "customer_id",
              "match_type": "canonical_name",
              "confidence": 1.0
            },
            {
              "entity_name": "Orders",
              "column_name": "customer_id",
              "match_type": "canonical_name",
              "confidence": 1.0
            }
          ],
          "related_terms": [
            {
              "term": "Customer",
              "relationship_type": "entity_column",
              "confidence": 1.0,
              "description": "Primary key of Customer entity"
            }
          ],
          "related_via_relationships": [
            {
              "from_entity": "Orders",
              "to_entity": "Customers",
              "relationship_type": "many_to_one",
              "confidence": 0.87,
              "semantic_description": "Each Order belongs to one Customer via customer_id foreign key match"
            }
          ],
          "classifications": ["Identity.UUID", "DataDomain.JoinKey"],
          "is_key_identifier": true,  # PK candidate
          "entity_type": null,
          "sample_values": [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
          ],
          "source_file_terminology": {
            "customer_master.xlsx": ["cust_id"],
            "customers.csv": ["customer_identifier"],
            "client_data.xlsx": ["client_id"]
          },
          "pk_metadata": {
            "confidence": 0.96,
            "uniqueness_ratio": 0.985,
            "explanation": "High uniqueness (98.5%) with 'id' suffix and UUID semantic type"
          }
        }
      ],
      "confidence": 0.88,  # Average term confidence
      "classification_summary": {
        "Finance.Revenue": 3,
        "Finance.Cost": 2,
        "PII.Sensitive": 1
      },
      "entity_types": ["fact", "dimension"],
      "source_entities": ["Orders", "Invoices", "Products"]
    }
  ],
  
  # NEW: Glossary summary
  "glossary_summary": {
    "total_glossaries": 4,
    "total_terms": 47,
    "terms_with_relationships": 32,
    "terms_with_entities": 45,
    "terms_with_columns": 43,
    "avg_confidence": 0.84,
    "key_identifiers": 8,  # Terms marked as is_key_identifier
    "classification_distribution": {
      "Finance.Revenue": 6,
      "Finance.Cost": 4,
      "PII.Sensitive": 8,
      "Contact.Email": 5,
      "Identity.UUID": 8,
      "DataDomain.JoinKey": 12
    }
  }
}
```

### Output Characteristics

**New Fields Added by GlossaryAgent:**

**Schema Level:**
1. **`glossaries`**: Array of business domain glossaries
2. **`glossary_summary`**: High-level statistics

**Glossary Level:**
- `glossary_id`, `name`, `display_name`: Identification
- `description`: LLM-generated domain description
- `terms`: Array of glossary terms in this domain
- `confidence`: Average term confidence
- `classification_summary`: Classification distribution in domain
- `entity_types`: Fact/dimension representation
- `source_entities`: Entities contributing terms

**Term Level:**
- `term_id`, `canonical_name`, `display_name`: Identification
- `definition`: LLM-generated business-friendly definition (2-3 sentences)
- `synonyms`: All alternate names (from raw_names and AlignerAgent synonyms)
- `confidence`: Aggregated confidence score
- `confidence_breakdown`: Transparent factor breakdown
- `associated_entities`: Linked entities with match type and confidence
- `associated_columns`: Linked columns with match type and confidence
- `related_terms`: Related terms with relationship type
- `related_via_relationships`: FK relationships from ArchitectAgent
- `classifications`: From TaggerAgent
- `is_key_identifier`: PK candidate flag
- `entity_type`: fact/dimension (if entity term)
- `sample_values`: From ProfilerAgent
- `source_file_terminology`: Map of source file → raw names (captures user terminology)
- `pk_metadata`: PK candidate details if applicable

**Propagated Unchanged:**
- All TaggerAgent outputs (entities, classifications, summary)
- All ArchitectAgent outputs (relationships)
- All upstream metadata in entities and columns

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GLOSSARY_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model (reuses AlignerAgent) |
| `GLOSSARY_USE_LLM_DEFINITIONS` | `true` | Enable LLM definitions (required for business-friendly output) |
| `GLOSSARY_USE_LLM_DOMAINS` | `true` | Enable LLM domain naming |
| `GLOSSARY_USE_LLM_SYNONYMS` | `true` | Augment synonyms with LLM |
| `GLOSSARY_LLM_PROVIDER` | `ollama` | LLM provider: `ollama` or `openai` |
| `GLOSSARY_LLM_MODEL` | `llama3.2:3b` | LLM model name |
| `GLOSSARY_LLM_BASE_URL` | `http://ollama:11434` | LLM endpoint |
| `GLOSSARY_LLM_BATCH_SIZE` | `8` | Terms per LLM call |
| `GLOSSARY_LLM_TIMEOUT` | `45` | LLM call timeout (seconds) |
| `GLOSSARY_LLM_MAX_RETRIES` | `3` | Max retry attempts |
| `GLOSSARY_USE_CLASSIFICATION_DOMAINS` | `true` | Use classifications for domain formation |
| `GLOSSARY_USE_RELATIONSHIP_LINKS` | `true` | Link related terms via relationships |
| `GLOSSARY_MIN_TERM_CONFIDENCE` | `0.50` | Minimum term confidence threshold |
| `GLOSSARY_NAME_MATCH_THRESHOLD` | `0.85` | Embedding similarity for fuzzy name matching |
| `GLOSSARY_SEMANTIC_SIMILARITY_THRESHOLD` | `0.80` | Threshold for related terms via embedding |

### LLM Behavior

**Definition Generation:**
- Batched: 8 terms per call (configurable)
- Timeout: 45 seconds per batch
- Retries: 3 attempts with exponential backoff (1s, 2s, 4s)
- Fallback: Template-based definitions if LLM fails

**Template Fallback Example:**
```
{canonical_name} is a {entity_type or "column"} in the {domain} domain. 
It represents {semantic_type or data_type} data and is used in {entity_count} entities. 
{If relationships: "It relates to {related_entities} via {relationship_type} relationships."}
```

## Algorithms

### Glossary Generation Workflow

1. **Term Extraction**:
   ```python
   candidate_terms = []
   
   # Extract entity terms
   for entity in enriched_schema['entities']:
       candidate_terms.append(CandidateTerm(
           canonical_name=entity['canonical_name'],
           normalized_term=normalize(entity['canonical_name']),
           source_type='entity',
           source_fqn=f"entity.{entity['canonical_name']}",
           alignment_confidence=entity['alignment_confidence'],
           synonyms=entity['synonyms'],
           raw_names=entity['raw_names'],
           entity_type=entity['entity_type'],
           classifications=[c['tag'] for c in entity['classifications']],
           classification_confidence=avg([c['confidence'] for c in entity['classifications']]),
           relationships=get_entity_relationships(entity),
           related_entities=get_related_entities(entity)
       ))
   
   # Extract column terms
   for entity in enriched_schema['entities']:
       for column in entity['columns']:
           candidate_terms.append(CandidateTerm(
               canonical_name=column['name'],
               normalized_term=normalize_remove_suffixes(column['name']),
               source_type='column',
               source_fqn=f"column.{entity['canonical_name']}.{column['name']}",
               sample_values=column.get('sample_values'),
               semantic_type=column.get('semantic_type'),
               semantic_type_confidence=column.get('semantic_type_confidence'),
               alignment_confidence=column.get('alignment_confidence'),
               synonyms=column.get('synonyms'),
               raw_names=column.get('raw_names'),
               is_primary_key=column.get('is_primary_key'),
               pk_confidence=get_pk_confidence(entity, column),
               pk_explanation=get_pk_explanation(entity, column),
               classifications=[c['tag'] for c in column.get('classifications', [])],
               classification_confidence=avg([c['confidence'] for c in column.get('classifications', [])]),
               relationships=get_column_relationships(column),
               related_entities=get_column_related_entities(column)
           ))
   
   # Normalize and deduplicate
   normalized_terms = deduplicate_by_normalized_name(candidate_terms)
   ```

2. **Term Clustering**:
   ```python
   # Reuse AlignerAgent services
   embedding_service = EmbeddingService(model=config.EMBEDDING_MODEL)
   clustering_service = ClusteringService(method=config.CLUSTERING_METHOD)
   
   # Compute embeddings
   term_names = [term.normalized_term for term in normalized_terms]
   embeddings = embedding_service.compute_embeddings(term_names)
   
   # Cluster
   clusters = clustering_service.cluster(embeddings, min_cluster_size=2)
   
   # Create TermCluster objects with variance
   term_clusters = []
   for cluster_id, member_indices in clusters.items():
       members = [normalized_terms[i] for i in member_indices]
       centroid = compute_centroid([embeddings[i] for i in member_indices])
       variance = compute_variance([embeddings[i] for i in member_indices], centroid)
       representative = select_representative_term(members)  # Highest alignment confidence
       
       term_clusters.append(TermCluster(
           cluster_id=cluster_id,
           members=members,
           centroid=centroid,
           variance=variance,
           representative_term=representative
       ))
   ```

3. **Domain Formation**:
   ```python
   # Primary strategy: Classification-based
   classification_domains = {}
   for term_cluster in term_clusters:
       dominant_classification = get_dominant_classification_prefix(term_cluster)
       if dominant_classification:
           domain_key = dominant_classification  # e.g., "Finance", "PII"
           if domain_key not in classification_domains:
               classification_domains[domain_key] = []
           classification_domains[domain_key].append(term_cluster)
   
   # Secondary strategy: Embedding-based for remaining
   unclassified_clusters = [tc for tc in term_clusters if tc not in classified]
   if unclassified_clusters:
       cluster_embeddings = [tc.centroid for tc in unclassified_clusters]
       domain_clusters = clustering_service.cluster(cluster_embeddings, min_cluster_size=1)
       
       for domain_id, cluster_indices in domain_clusters.items():
           domain_name = f"domain_{domain_id}"
           classification_domains[domain_name] = [unclassified_clusters[i] for i in cluster_indices]
   
   # Create DomainCluster objects
   domain_clusters = []
   for domain_key, clusters in classification_domains.items():
       domain_clusters.append(DomainCluster(
           cluster_id=domain_key,
           term_clusters=clusters,
           dominant_classifications=get_all_classifications(clusters),
           entity_types=get_entity_types(clusters),
           centroid=compute_domain_centroid(clusters),
           variance=compute_domain_variance(clusters)
       ))
   ```

4. **LLM Definition Generation (Batched)**:
   ```python
   async def generate_definitions_batched(terms, batch_size=8):
       definitions = {}
       
       for i in range(0, len(terms), batch_size):
           batch = terms[i:i+batch_size]
           
           # Build prompt with full context for batch
           prompt = "Generate business-friendly definitions (2-3 sentences) for these terms:\n\n"
           for term in batch:
               prompt += f"Term: {term.canonical_name} (synonyms: {', '.join(term.synonyms)})\n"
               if term.entity_type:
                   prompt += f"Type: {term.entity_type.capitalize()} entity\n"
               else:
                   prompt += f"Type: Column (semantic type: {term.semantic_type})\n"
               prompt += f"Classifications: {', '.join(term.classifications)}\n"
               if term.sample_values:
                   prompt += f"Sample values: {', '.join(map(str, term.sample_values[:3]))}\n"
               if term.relationships:
                   prompt += f"Relationships: {format_relationships(term.relationships)}\n"
               if term.related_entities:
                   prompt += f"Related entities: {', '.join(term.related_entities)}\n"
               prompt += "\n"
           
           prompt += "Requirements:\n"
           prompt += "- 2-3 sentences per term\n"
           prompt += "- Business language, not technical jargon\n"
           prompt += "- Include domain context and relationships\n"
           prompt += "- Explain what the term represents and why it's important\n"
           
           # Call LLM with retry
           for attempt in range(config.MAX_RETRIES):
               try:
                   response = await llm_service.call(prompt, timeout=config.LLM_TIMEOUT)
                   batch_definitions = parse_llm_response(response, batch)
                   definitions.update(batch_definitions)
                   break
               except Exception as e:
                   if attempt == config.MAX_RETRIES - 1:
                       # Fallback to templates
                       for term in batch:
                           definitions[term.canonical_name] = generate_template_definition(term)
                   else:
                       await asyncio.sleep(2 ** attempt)  # Exponential backoff
       
       return definitions
   ```

5. **Entity Linking**:
   ```python
   def link_term_to_entities(term, entities, embedding_service):
       associated_entities = []
       associated_columns = []
       
       for entity in entities:
           # Strategy 1: Canonical name match
           if term.normalized_term == normalize(entity['canonical_name']):
               associated_entities.append({
                   "entity_name": entity['canonical_name'],
                   "match_type": "canonical_name",
                   "confidence": 1.0
               })
               continue
           
           # Strategy 2: Synonym match
           for synonym in entity.get('synonyms', []):
               if term.normalized_term == normalize(synonym):
                   associated_entities.append({
                       "entity_name": entity['canonical_name'],
                       "match_type": "synonym",
                       "confidence": 0.95
                   })
                   break
           
           # Strategy 3: Raw name match
           for raw_name in entity.get('raw_names', []):
               if term.normalized_term == normalize(raw_name):
                   associated_entities.append({
                       "entity_name": entity['canonical_name'],
                       "match_type": "raw_name",
                       "confidence": 0.90
                   })
                   break
           
           # Strategy 4: Embedding similarity
           term_embedding = embedding_service.compute_embedding(term.normalized_term)
           entity_embedding = embedding_service.compute_embedding(entity['canonical_name'])
           similarity = cosine_similarity(term_embedding, entity_embedding)
           if similarity >= config.NAME_MATCH_THRESHOLD:
               associated_entities.append({
                   "entity_name": entity['canonical_name'],
                   "match_type": "embedding",
                   "confidence": similarity
               })
           
           # Link to columns
           for column in entity['columns']:
               if term.normalized_term == normalize_remove_suffixes(column['name']):
                   associated_columns.append({
                       "entity_name": entity['canonical_name'],
                       "column_name": column['name'],
                       "match_type": "canonical_name",
                       "confidence": 1.0
                   })
               # ... similar synonym, raw_name, embedding strategies for columns
       
       return associated_entities, associated_columns
   ```

6. **Related Terms Identification**:
   ```python
   def identify_related_terms(term, all_terms, relationships, embedding_service):
       related_terms = []
       
       # Strategy 1: Relationship-based (primary)
       for rel in relationships:
           if term_in_relationship(term, rel):
               related_term = get_other_term_in_relationship(term, rel, all_terms)
               if related_term:
                   related_terms.append({
                       "term": related_term.canonical_name,
                       "relationship_type": "foreign_key",
                       "confidence": rel['confidence'],
                       "description": rel.get('semantic_description', '')
                   })
       
       # Strategy 2: Classification overlap
       for other_term in all_terms:
           if other_term == term:
               continue
           overlapping_classes = set(term.classifications) & set(other_term.classifications)
           if overlapping_classes:
               related_terms.append({
                   "term": other_term.canonical_name,
                   "relationship_type": "classification_overlap",
                   "confidence": 0.75,
                   "description": f"Related via {', '.join(overlapping_classes)} classifications"
               })
       
       # Strategy 3: Embedding similarity
       term_embedding = embedding_service.compute_embedding(term.normalized_term)
       for other_term in all_terms:
           if other_term == term:
               continue
           other_embedding = embedding_service.compute_embedding(other_term.normalized_term)
           similarity = cosine_similarity(term_embedding, other_embedding)
           if similarity >= config.SEMANTIC_SIMILARITY_THRESHOLD:
               related_terms.append({
                   "term": other_term.canonical_name,
                   "relationship_type": "semantic_similarity",
                   "confidence": similarity,
                   "description": "Semantically related terms"
               })
       
       # Deduplicate and limit
       return deduplicate_related_terms(related_terms)[:10]  # Top 10
   ```

7. **Confidence Calculation**:
   ```python
   def calculate_term_confidence(term):
       # Weighted aggregate of upstream confidences
       confidence_factors = {
           'alignment_confidence': (term.alignment_confidence or 0.5, 0.30),
           'semantic_type_confidence': (term.semantic_type_confidence or 0.5, 0.20),
           'classification_confidence': (term.classification_confidence or 0.5, 0.20),
           'clustering_confidence': (1.0 - term.cluster_variance, 0.15),
           'definition_quality': (estimate_definition_quality(term.definition), 0.15)
       }
       
       weighted_sum = sum(conf * weight for conf, weight in confidence_factors.values())
       
       return {
           'confidence': weighted_sum,
           'confidence_breakdown': {
               name: conf for name, (conf, weight) in confidence_factors.items()
           }
       }
   ```

## Dependencies

### Required Python Packages
- `sentence-transformers`: Embeddings (shared with AlignerAgent)
- `scikit-learn`: Clustering (shared with AlignerAgent)
- `hdbscan`: Density-based clustering (optional, shared with AlignerAgent)
- `requests`: Ollama API calls
- `openai`: OpenAI API (future)
- `numpy`: Array operations

### Upstream Dependencies
- **ProfilerAgent** (via AlignerAgent):
  - Sample values for LLM context
  - Semantic types for term metadata
- **AlignerAgent**:
  - Canonical names, synonyms, raw_names (essential)
  - Alignment confidence (for confidence scoring)
  - Entity types (for domain formation)
  - Primary key candidates (for key identifier terms)
  - Embedding and clustering infrastructure (reused)
- **ArchitectAgent**:
  - Relationships (for related terms)
  - Semantic descriptions (for LLM prompts)
- **TaggerAgent**:
  - Classifications (primary signal for domain formation)
  - Classification confidence (for confidence scoring)

### Downstream Consumers
- **ContextAgent**: Uses GlossaryAgent glossaries
  - Glossary terms for entity/column descriptions
  - Domain descriptions for context
  - Confidence scores for confidence language

- **Data Pipeline**: Uses glossaries for ingestion
  - Glossaries ingested to OpenMetadata
  - Terms linked to entities and columns
  - Definitions displayed in UI

## Error Handling

### Common Failure Scenarios

1. **LLM Service Unavailable**: Falls back to template-based definitions
2. **LLM Timeout**: Retries with exponential backoff, then falls back to templates
3. **No Terms Extracted**: Returns empty glossaries array (valid scenario)
4. **Low Confidence Terms**: Filtered out if below minimum threshold (0.50)
5. **Clustering Failure**: Falls back to individual terms (no clustering)

### Logging
- INFO: Glossary generation start/completion, term counts, domain counts, LLM call status
- WARNING: LLM fallback to templates, low confidence terms filtered, clustering issues
- ERROR: LLM service failures, term extraction errors

## Future Extensions

### Planned Enhancements
1. **OpenAI Provider**: Full OpenAI API integration for cloud LLM
2. **Hierarchical Terms**: Support parent/child term relationships
3. **Term Versioning**: Track glossary term changes over time
4. **Custom Domain Taxonomies**: Organization-specific domain hierarchies
5. **Multi-Language Glossaries**: Generate definitions in multiple languages
6. **User Feedback Loop**: Learn from user edits to improve definitions
7. **Glossary Approval Workflow**: Human-in-the-loop validation before publishing
8. **Embedding Cache**: Redis cache for term embeddings across runs

### Extension Points
- Add new LLM provider: Implement in `llm_service.py`
- Customize domain formation: Modify `domain_formation.py`
- Customize entity linking: Extend strategies in `entity_linker.py`
- Add new related term strategies: Extend `related_terms.py`

