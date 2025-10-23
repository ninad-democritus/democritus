# ContextAgent Documentation

## Overview

The **ContextAgent** is the sixth and final agent in the workflow pipeline, responsible for transforming structured enriched metadata into business-ready narratives and producing minimal, UI-friendly output suitable for OpenMetadata ingestion and frontend display. It bridges the gap between technical metadata and human-readable documentation.

### What It Does

1. **Semantic Graph Construction** (Optional): Builds a multi-modal knowledge graph for contextual analysis with entities, columns, glossary terms, relationships, and classifications as nodes/edges
2. **Context Bundle Consolidation**: Gathers comprehensive context for each entity, column, relationship, and glossary term
3. **Narrative Generation**: Creates business-friendly descriptions using LLM or template fallbacks:
   - Entity descriptions (purpose, role, key columns, relationships, governance)
   - Column descriptions (business meaning, data type, statistics, classifications, glossary linkage)
   - Relationship narratives (semantic description with confidence levels)
   - Glossary/domain summaries (high-level domain description with data characteristics)
4. **Minimal Output Formatting**: Strips internal fields and produces lean output (~56% smaller) for UI and data-pipeline consumption

### Why These Design Choices

- **Business Narratives vs Technical Metadata**: TaggerAgent provides governance tags; ContextAgent provides human-readable explanations. Different audiences (compliance vs business users).
- **Semantic Graph**: Multi-hop context queries enable richer descriptions. "Find all PII columns in Sales domain" or "What glossary terms link Customer to Order?"
- **Comprehensive Context Bundles**: Entity descriptions need full context (columns, relationships, classifications, glossary terms, statistics). Passing partial context produces poor LLM descriptions.
- **Confidence-Aware Language**: Descriptions should reflect confidence levels. High confidence relationships use "confirmed", low confidence use "tentative".
- **Minimal Output**: 56% size reduction by removing internal fields (raw_names, confidence_breakdown, sample statistics, provenance). Essential for UI performance and OpenMetadata ingestion.
- **LLM-First with Template Fallback**: LLM produces natural language that templates can't match. But templates provide reliability when LLM fails.
- **Reuses LLM Service**: Shares GlossaryAgent's LLM service for consistency and efficiency.
- **Replaces Enriched Schema**: Final step produces minimal schema with descriptions, replacing enriched_schema for data-pipeline consumption.

## Folder Structure

```
services/agent-workflow/app/agents/context/
├── __init__.py
├── agent.py                          # Main orchestrator
├── models.py                         # Context bundle and output models
├── config.py                         # Environment-based configuration
├── graph/                            # Semantic graph construction
│   ├── __init__.py
│   ├── builder.py                    # NetworkX graph construction
│   └── analyzer.py                   # Graph traversal and analysis utilities
├── consolidation/                    # Context bundle builders
│   ├── __init__.py
│   ├── entity_bundle.py              # Entity context builder
│   ├── column_bundle.py              # Column context builder
│   ├── relationship_bundle.py        # Relationship context builder
│   └── glossary_bundle.py            # Domain/glossary context builder
├── narratives/                       # Narrative generation
│   ├── __init__.py
│   ├── templates.py                  # LLM prompt templates
│   ├── generator.py                  # LLM-powered narrative generation
│   └── confidence_mapper.py          # Confidence-to-language mapping
└── formatter.py                      # Minimal output formatter
```

### File Responsibilities

#### Core Files
- **`agent.py`**: Main orchestrator coordinating context generation
  - Entry point: `generate_context(enriched_schema)`
  - Optionally builds semantic graph
  - Consolidates context bundles for all targets
  - Generates narratives via LLM or templates
  - Formats minimal output
  - Returns minimal schema with descriptions
  - **Replaces** enriched_schema in workflow state

- **`models.py`**: Context bundle and output structures
  - `EntityContext`: Comprehensive entity context bundle
  - `ColumnContext`: Comprehensive column context bundle
  - `RelationshipContext`: Relationship context bundle
  - `GlossaryContext`: Glossary/domain context bundle
  - `MinimalEntity`: Minimal entity output format
  - `MinimalColumn`: Minimal column output format
  - `MinimalRelationship`: Minimal relationship output format
  - `MinimalGlossary`: Minimal glossary output format

- **`config.py`**: Centralized configuration
  - LLM provider configuration (shared with GlossaryAgent)
  - Feature toggles (enable LLM, enable graph, output format)
  - Confidence thresholds

#### Graph Module (`graph/`)

- **`builder.py`**: Semantic graph construction using NetworkX
  - **Node Types**:
    - Entity nodes: `{type: "entity", name, entity_type, classifications, pk, confidence}`
    - Column nodes: `{type: "column", name, entity, semantic_type, classifications, confidence}`
    - Glossary term nodes: `{type: "term", name, definition, domain, confidence}`
  - **Edge Types**:
    - Entity-Entity: Relationships with cardinality and confidence
    - Entity-Column: Column membership
    - Term-Entity: Glossary associations
    - Term-Column: Glossary associations
    - Entity/Column-Classification: Classification tags
  - **Graph Construction**:
    ```python
    G = nx.DiGraph()
    
    # Add entity nodes
    for entity in enriched_schema['entities']:
        G.add_node(entity['canonical_name'], 
                   type='entity', 
                   entity_type=entity['entity_type'],
                   confidence=entity['alignment_confidence'],
                   ...)
    
    # Add column nodes and membership edges
    for entity in enriched_schema['entities']:
        for column in entity['columns']:
            col_id = f"{entity['canonical_name']}.{column['name']}"
            G.add_node(col_id, type='column', ...)
            G.add_edge(entity['canonical_name'], col_id, edge_type='has_column')
    
    # Add relationship edges
    for rel in enriched_schema['relationships']:
        G.add_edge(rel['from_entity'], rel['to_entity'], 
                   edge_type='relationship',
                   cardinality=rel['cardinality'],
                   confidence=rel['confidence'],
                   ...)
    
    # Add glossary term nodes and association edges
    for glossary in enriched_schema['glossaries']:
        for term in glossary['terms']:
            G.add_node(term['canonical_name'], type='term', ...)
            for assoc in term['associated_entities']:
                G.add_edge(term['canonical_name'], assoc['entity_name'], 
                           edge_type='describes')
    
    # Add classification edges
    for entity in enriched_schema['entities']:
        for classification in entity['classifications']:
            G.add_edge(entity['canonical_name'], classification['tag'],
                       edge_type='classified_as',
                       confidence=classification['confidence'])
    ```
  - **Benefits**: Enables multi-hop queries like "Find all PII columns in Customer-related entities"

- **`analyzer.py`**: Graph traversal and analysis utilities
  - **Path Finding**: Find shortest paths between entities
  - **Neighborhood Queries**: Get all nodes within N hops
  - **Classification Filtering**: Find all nodes with specific classifications
  - **Confidence Filtering**: Filter by confidence thresholds
  - **Subgraph Extraction**: Extract subgraphs for specific domains
  - **Example Queries**:
    ```python
    # Find all columns linked to a glossary term
    term_columns = analyzer.get_neighbors(graph, "Customer", edge_type='describes', depth=2)
    
    # Find all PII columns in Sales domain entities
    pii_columns = analyzer.find_nodes(graph, 
                                      node_type='column',
                                      classification='PII.Sensitive',
                                      domain='Sales')
    
    # Find relationship path between two entities
    path = analyzer.shortest_path(graph, "Orders", "Products")
    ```

#### Consolidation Module (`consolidation/`)

- **`entity_bundle.py`**: Entity context builder
  - **Gathers**:
    - Entity metadata (name, synonyms, type, confidence)
    - Primary key details (column, uniqueness, confidence)
    - Column list (simplified: name, semantic type, classifications)
    - Relationships (incoming/outgoing with cardinality and confidence)
    - Classifications (all entity-level tags)
    - Glossary terms linked to entity
    - Row count and data characteristics
    - Domain (from glossary or classifications)
  - **Output**: `EntityContext` object
  - **Example**:
    ```python
    EntityContext(
        canonical_name="Orders",
        synonyms=["Sales Orders", "Transactions"],
        entity_type="fact",
        confidence=0.92,
        primary_key={"column": "order_id", "is_unique": True, "confidence": 0.96},
        columns=[
            {"name": "order_id", "semantic_type": "uuid", "classifications": ["Identity.UUID"]},
            {"name": "customer_id", "semantic_type": "uuid", "classifications": ["DataDomain.JoinKey"]},
            {"name": "amount", "semantic_type": "currency.amount", "classifications": ["Finance.Revenue"]}
        ],
        relationships=[
            {"to_entity": "Customers", "cardinality": "many_to_one", "confidence": 0.87, "description": "..."}
        ],
        classifications=["DataDomain.Fact"],
        glossary_terms=["Order", "Revenue", "Transaction"],
        row_count=50000,
        domain="Sales & Billing"
    )
    ```

- **`column_bundle.py`**: Column context builder
  - **Gathers**:
    - Column metadata (name, canonical_name)
    - Entity name (parent entity)
    - Semantic type and data type
    - Classifications (all column-level tags)
    - Glossary term linked to column
    - Statistics (min, max, distinct count)
    - Relationships (if column is FK or PK)
  - **Output**: `ColumnContext` object
  - **Example**:
    ```python
    ColumnContext(
        name="amount",
        canonical_name="Order Amount",
        entity_name="Orders",
        semantic_type="currency.amount",
        data_type_display="DECIMAL(19,4)",
        classifications=["Finance.Revenue"],
        glossary_term="Revenue",
        statistics={"min": 5.00, "max": 10000.00, "distinct_count": 8732},
        relationships=[
            {"type": "foreign_key", "to_entity": "Customers", "confidence": 0.87}
        ],
        is_primary_key=False,
        is_nullable=False
    )
    ```

- **`relationship_bundle.py`**: Relationship context builder
  - **Gathers**:
    - Relationship metadata (from_entity, to_entity, cardinality)
    - Column details (from_column, to_column)
    - Confidence and confidence breakdown
    - Existing semantic description (from ArchitectAgent)
    - Entity types (fact/dimension)
    - Classifications on both sides
  - **Output**: `RelationshipContext` object

- **`glossary_bundle.py`**: Glossary/domain context builder
  - **Gathers**:
    - Glossary metadata (name, domain)
    - Term list with definitions
    - Classification distribution
    - Entity types in domain
    - Source entities
  - **Output**: `GlossaryContext` object

#### Narratives Module (`narratives/`)

- **`templates.py`**: LLM prompt templates and fallback templates
  - **Entity Description Prompt**:
    ```
    Generate a business-friendly description for this entity:
    
    Entity: {canonical_name} (synonyms: {synonyms})
    Type: {entity_type} (confidence: {confidence_language})
    Domain: {domain}
    
    Key Columns ({column_count}):
    {columns_with_semantic_types_and_classifications}
    
    Relationships ({relationship_count}):
    {relationships_with_cardinality_and_confidence}
    
    Classifications: {classifications}
    Glossary Terms: {glossary_terms}
    Row Count: {row_count}
    
    Requirements:
    - 3-4 sentences
    - Explain the entity's purpose and role in the business
    - Mention key data characteristics and relationships
    - Include governance context (PII, financial, etc.)
    - Use confidence-appropriate language ({confidence_language})
    ```
  - **Column Description Prompt**:
    ```
    Generate a business-friendly description for this column:
    
    Column: {name} (canonical: {canonical_name})
    Entity: {entity_name}
    Semantic Type: {semantic_type}
    Data Type: {data_type_display}
    Glossary Term: {glossary_term}
    
    Classifications: {classifications}
    Statistics: {statistics}
    Relationships: {relationships}
    
    Requirements:
    - 2-3 sentences
    - Explain what the column represents and its business meaning
    - Mention data type and any constraints
    - Include governance context if applicable
    ```
  - **Fallback Templates** (when LLM fails):
    ```python
    entity_template = (
        "The {canonical_name} {entity_type} serves as {purpose_description} in the {domain} domain. "
        "It contains {column_count} columns including {key_columns}. "
        "{relationship_description} "
        "{governance_description}"
    )
    
    column_template = (
        "{canonical_name} is a {semantic_type} column in the {entity_name} entity. "
        "It stores {data_type_display} data {constraint_description}. "
        "{classification_description}"
    )
    ```

- **`generator.py`**: LLM-powered narrative generation
  - **Reuses GlossaryAgent LLM Service**: Shared infrastructure for consistency
  - **Batched Generation**: Entities and columns processed in batches
  - **Retry Logic**: 3 attempts with exponential backoff
  - **Fallback to Templates**: Automatic fallback on LLM failure
  - **Caching**: Optional caching of generated descriptions (future)
  - **Functions**:
    ```python
    async def generate_entity_description(entity_context, llm_service):
        prompt = build_entity_prompt(entity_context)
        try:
            description = await llm_service.call(prompt, timeout=30)
            return description
        except Exception:
            return generate_entity_template(entity_context)
    
    async def generate_column_description(column_context, llm_service):
        prompt = build_column_prompt(column_context)
        try:
            description = await llm_service.call(prompt, timeout=20)
            return description
        except Exception:
            return generate_column_template(column_context)
    ```

- **`confidence_mapper.py`**: Confidence-to-language mapping
  - **Confidence Ranges → Language**:
    - **High (> 0.85)**: "confirmed", "established", "verified", "clear"
    - **Medium (0.70-0.85)**: "likely", "probable", "strongly indicated", "expected"
    - **Low (< 0.70)**: "possible", "tentative", "preliminary", "suggested"
  - **Used in Descriptions**:
    - Relationships: "Each Order **likely** belongs to one Customer" (confidence: 0.75)
    - Classifications: "This entity **confirmed** contains PII data" (confidence: 0.92)
    - Entity types: "This **established** fact table tracks transactions" (confidence: 0.88)
  - **Function**:
    ```python
    def confidence_to_language(confidence: float) -> str:
        if confidence > 0.85:
            return random.choice(["confirmed", "established", "verified"])
        elif confidence > 0.70:
            return random.choice(["likely", "probable", "expected"])
        else:
            return random.choice(["possible", "tentative", "preliminary"])
    ```

#### Formatter Module (`formatter.py`)

- **Minimal Output Formatting**: Strips internal fields and produces lean schema
  - **Removed Fields**:
    - Internal IDs: `entity_id`, `term_id`, `relationship_id`
    - Alignment artifacts: `raw_names`, `alignment_confidence`, `confidence_breakdown`
    - Profiling statistics: `distinct_count`, `null_percentage`, `min_value`, `max_value`, `mean_value`
    - Semantic metadata: `semantic_type` (already in classifications/descriptions)
    - Provenance: `upstream_factors`, `source`, `detection_method`
    - Sample values: Privacy risk + not needed for metadata
  - **Kept Fields**:
    - Core identifiers: `name`, `displayName`, `synonyms`
    - **NEW** Descriptions: `description` fields (entity, column, relationship, glossary)
    - Data types: `dataType`, `dataTypeDisplay`, `dataLength`, `precision`, `scale`
    - Constraints: `nullable`, `constraint` (PRIMARY_KEY)
    - Tags: Simplified tag list (just tag names, not full classification objects)
    - Optional: Simple `confidence` float for UI highlighting
  - **Size Reduction**: ~56% smaller payload
  - **Format**:
    ```python
    def format_minimal_entity(entity_with_description):
        return {
            "name": entity['canonical_name'],
            "displayName": entity['canonical_name'],
            "synonyms": entity.get('synonyms', []),
            "tableType": entity['entity_type'].capitalize(),
            "description": entity['description'],  # NEW from ContextAgent
            "tags": [c['tag'] for c in entity.get('classifications', [])],
            "confidence": entity.get('alignment_confidence'),  # Optional for UI
            "columns": [format_minimal_column(col) for col in entity['columns']]
        }
    
    def format_minimal_column(column_with_description):
        return {
            "name": column['name'],
            "displayName": column['name'],
            "dataType": column['data_type'],
            "dataTypeDisplay": column.get('data_type_display'),
            "dataLength": column.get('data_length'),
            "precision": column.get('precision'),
            "scale": column.get('scale'),
            "nullable": column.get('nullable'),
            "constraint": column.get('constraint'),  # PRIMARY_KEY or null
            "description": column['description'],  # NEW from ContextAgent
            "tags": [c['tag'] for c in column.get('classifications', [])]
        }
    ```

## Input/Output Contracts

### Input

**Function Signature:**
```python
async def generate_context(enriched_schema: Dict[str, Any]) -> Dict[str, Any]
```

**Parameters:**
- `enriched_schema` (Dict): Output from GlossaryAgent containing:
  - `entities`: With classifications from TaggerAgent
  - `relationships`: From ArchitectAgent
  - `glossaries`: From GlossaryAgent
  - `classification_summary`: From TaggerAgent
  - `glossary_summary`: From GlossaryAgent

**Dependencies on All Upstream Outputs:**
- **ProfilerAgent** (via downstream agents):
  - Sample values (used in glossary context, stripped from output)
  - Statistics (used in column context, stripped from output)
- **AlignerAgent**:
  - Canonical names, synonyms (kept in output)
  - Alignment confidence (used for confidence language, stripped from output)
  - Entity types (used in descriptions, converted to tableType)
- **ArchitectAgent**:
  - Relationships with semantic descriptions (enhanced with confidence language)
  - OpenMetadata types (kept in output)
  - Confidence breakdowns (used for language, stripped from output)
- **TaggerAgent**:
  - Classifications (converted to simple tag lists)
  - Classification confidence (used for language, stripped from output)
- **GlossaryAgent**:
  - Glossary terms with definitions (kept, enhanced with domain context)
  - Domain descriptions (kept)

### Output

**Return Type:** `Dict[str, Any]` (minimal schema with descriptions)

**Minimal Schema Structure:**
```python
{
  "entities": [
    {
      "name": "Customers",
      "displayName": "Customers",
      "synonyms": ["Clients", "Custs"],
      "tableType": "Dimension",
      "description": "The Customers table serves as the central dimension for customer information in the Sales & Billing domain. It contains unique customer records identified by customer_id (UUID), including contact details like email addresses (PII-sensitive) and lifetime value metrics. The table links to Orders through a confirmed many-to-one relationship (87% confidence), enabling customer purchase history analysis and revenue tracking.",
      "tags": ["DataDomain.Dimension"],
      "confidence": 0.94,  # Optional for UI highlighting
      "columns": [
        {
          "name": "customer_id",
          "displayName": "Customer ID",
          "dataType": "UUID",
          "dataTypeDisplay": "UUID",
          "dataLength": null,
          "precision": null,
          "scale": null,
          "nullable": false,
          "constraint": "PRIMARY_KEY",
          "description": "Customer ID is the unique identifier for each customer record, implemented as a UUID to ensure global uniqueness. It serves as the primary key for customer data and appears as a foreign key in related entities like Orders and Invoices, enabling reliable customer tracking across all transactions.",
          "tags": ["Identity.UUID"]
        },
        {
          "name": "email",
          "displayName": "Email",
          "dataType": "VARCHAR",
          "dataTypeDisplay": "VARCHAR(320)",
          "dataLength": 320,
          "precision": null,
          "scale": null,
          "nullable": true,
          "constraint": null,
          "description": "Email stores customer email addresses for communication and account identification. This field contains personally identifiable information (PII) and requires appropriate access controls. The data type accommodates standard email formats up to 320 characters, and the field allows null values for customers without email addresses.",
          "tags": ["PII.Sensitive", "Contact.Email", "DataQuality.Nullable"]
        },
        {
          "name": "lifetime_value",
          "displayName": "Lifetime Value",
          "dataType": "DECIMAL",
          "dataTypeDisplay": "DECIMAL(19,4)",
          "dataLength": null,
          "precision": 19,
          "scale": 4,
          "nullable": false,
          "constraint": null,
          "description": "Lifetime Value represents the total revenue generated by a customer over their entire relationship with the business. This financial metric is calculated as a sum of all order amounts and is used for customer segmentation and marketing analysis. Values range from $0.00 to $45,000.00 with high precision for accurate financial reporting.",
          "tags": ["Finance.Revenue"]
        }
      ]
    }
  ],
  "relationships": [
    {
      "fromEntity": "Orders",
      "toEntity": "Customers",
      "fromColumn": "customer_id",
      "toColumn": "customer_id",
      "cardinality": "many_to_one",
      "confidence": 0.87,
      "description": "Each Order belongs to one Customer via customer_id foreign key match (confirmed). This established relationship enables customer purchase history tracking and supports revenue analysis by customer segment."
    }
  ],
  "glossaries": [
    {
      "name": "financial_data",
      "displayName": "Financial Data",
      "description": "Financial metrics, revenue, and cost tracking data including sales amounts, expenses, and profitability measures. This domain encompasses all monetary transactions and financial reporting elements used for business performance analysis and compliance reporting.",
      "terms": [
        {
          "name": "Revenue",
          "displayName": "Revenue",
          "definition": "Revenue represents the total income generated from sales transactions before any deductions. It serves as a key financial metric for measuring business performance and appears in Orders and Invoices entities. Revenue data is typically aggregated monthly and annually for financial reporting and is classified as sensitive financial information requiring appropriate access controls.",
          "synonyms": ["Sales", "Income", "Total Sales"],
          "confidence": 0.87,
          "associatedEntities": ["Orders", "Invoices"],
          "associatedColumns": [
            {"entity": "Orders", "column": "order_total"}
          ],
          "relatedTerms": ["Cost", "Customer"],
          "tags": ["Finance.Revenue", "DataQuality.Nullable"]
        }
      ],
      "tags": ["Finance.Revenue", "Finance.Cost"]
    }
  ],
  "metadata": {
    "totalEntities": 5,
    "totalColumns": 47,
    "totalRelationships": 8,
    "totalGlossaryTerms": 47,
    "outputFormat": "minimal",
    "sizeReduction": "56%"
  }
}
```

### Output Characteristics

**New Fields Added by ContextAgent:**

**Entity Level:**
1. **`description`**: LLM-generated business-friendly description (3-4 sentences)

**Column Level:**
1. **`description`**: LLM-generated business-friendly description (2-3 sentences)

**Relationship Level:**
1. **`description`**: Enhanced semantic description with confidence language

**Glossary Level:**
1. **`description`**: Enhanced domain description (if not already present)

**Format Changes:**
- `canonical_name` → `name`
- `entity_type` → `tableType` (capitalized)
- `classifications` array → `tags` array (simplified to tag names only)
- `data_type_display` kept (important for UI)
- `confidence` simplified to single float (optional for UI)

**Removed Fields** (present in enriched_schema):
- `entity_id`, `relationship_id`, `term_id`
- `raw_names`, `alignment_confidence`, `confidence_breakdown`
- `semantic_type`, `semantic_type_confidence`
- `distinct_count`, `null_percentage`, `null_count`, `total_count`
- `min_value`, `max_value`, `mean_value`
- `sample_values`
- `upstream_factors`, `source`, `detection_method`
- `source_file_terminology`, `pk_metadata`

**Size Reduction Example:**
- Enriched schema: ~500 KB
- Minimal schema: ~220 KB
- Reduction: 56%

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTEXT_LLM_PROVIDER` | `ollama` | LLM provider: `ollama` or `openai` |
| `CONTEXT_LLM_MODEL` | `llama3.2:3b` | LLM model name (shared with GlossaryAgent) |
| `CONTEXT_LLM_BASE_URL` | `http://ollama:11434` | LLM endpoint |
| `CONTEXT_USE_LLM` | `true` | Enable LLM narratives |
| `CONTEXT_FALLBACK_TEMPLATES` | `true` | Use templates if LLM fails |
| `CONTEXT_OUTPUT_FORMAT` | `minimal` | Output format: `minimal` or `full` |
| `CONTEXT_INCLUDE_CONFIDENCE` | `true` | Include confidence scores in output |
| `CONTEXT_ENABLE_GRAPH` | `true` | Build semantic graph for analysis |
| `CONTEXT_ENTITY_DESCRIPTION_TIMEOUT` | `30` | Entity description LLM timeout (seconds) |
| `CONTEXT_COLUMN_DESCRIPTION_TIMEOUT` | `20` | Column description LLM timeout (seconds) |
| `CONTEXT_BATCH_SIZE` | `10` | Entities/columns per batch |

### Output Format Options

**Minimal Format** (default):
- Strips internal fields
- ~56% smaller
- Optimized for UI and OpenMetadata ingestion
- Includes descriptions

**Full Format** (future):
- Keeps all enriched_schema fields
- Adds descriptions
- For debugging and advanced use cases

## Algorithms

### Context Generation Workflow

1. **Semantic Graph Construction** (Optional):
   ```python
   if config.ENABLE_GRAPH:
       graph = GraphBuilder.build_graph(enriched_schema)
       analyzer = GraphAnalyzer(graph)
   ```

2. **Entity Context Consolidation**:
   ```python
   entity_contexts = []
   for entity in enriched_schema['entities']:
       # Gather comprehensive context
       entity_context = EntityBundle.build(
           entity=entity,
           relationships=get_entity_relationships(entity, enriched_schema['relationships']),
           glossaries=get_entity_glossary_terms(entity, enriched_schema['glossaries']),
           graph_analyzer=analyzer if graph else None
       )
       entity_contexts.append(entity_context)
   ```

3. **Column Context Consolidation**:
   ```python
   column_contexts = []
   for entity in enriched_schema['entities']:
       for column in entity['columns']:
           column_context = ColumnBundle.build(
               column=column,
               entity_name=entity['canonical_name'],
               relationships=get_column_relationships(column, enriched_schema['relationships']),
               glossary_terms=get_column_glossary_terms(column, enriched_schema['glossaries']),
               graph_analyzer=analyzer if graph else None
           )
           column_contexts.append(column_context)
   ```

4. **Entity Description Generation** (Batched):
   ```python
   entity_descriptions = {}
   
   for i in range(0, len(entity_contexts), config.BATCH_SIZE):
       batch = entity_contexts[i:i+config.BATCH_SIZE]
       
       for entity_context in batch:
           prompt = Templates.build_entity_prompt(entity_context)
           
           try:
               description = await llm_service.call(
                   prompt, 
                   timeout=config.ENTITY_DESCRIPTION_TIMEOUT
               )
               entity_descriptions[entity_context.canonical_name] = description
           except Exception:
               if config.FALLBACK_TEMPLATES:
                   description = Templates.generate_entity_template(entity_context)
                   entity_descriptions[entity_context.canonical_name] = description
   ```

5. **Column Description Generation** (Batched):
   ```python
   column_descriptions = {}
   
   for i in range(0, len(column_contexts), config.BATCH_SIZE):
       batch = column_contexts[i:i+config.BATCH_SIZE]
       
       for column_context in batch:
           prompt = Templates.build_column_prompt(column_context)
           
           try:
               description = await llm_service.call(
                   prompt,
                   timeout=config.COLUMN_DESCRIPTION_TIMEOUT
               )
               column_descriptions[f"{column_context.entity_name}.{column_context.name}"] = description
           except Exception:
               if config.FALLBACK_TEMPLATES:
                   description = Templates.generate_column_template(column_context)
                   column_descriptions[f"{column_context.entity_name}.{column_context.name}"] = description
   ```

6. **Relationship Description Enhancement**:
   ```python
   for relationship in enriched_schema['relationships']:
       # Enhance existing semantic_description with confidence language
       confidence_lang = ConfidenceMapper.confidence_to_language(relationship['confidence'])
       enhanced_description = (
           f"{relationship['semantic_description']} ({confidence_lang}). "
           f"This {confidence_lang} relationship enables {business_context}."
       )
       relationship['description'] = enhanced_description
   ```

7. **Minimal Output Formatting**:
   ```python
   minimal_schema = {
       "entities": [
           Formatter.format_minimal_entity(entity, entity_descriptions[entity['canonical_name']])
           for entity in enriched_schema['entities']
       ],
       "relationships": [
           Formatter.format_minimal_relationship(rel)
           for rel in enriched_schema['relationships']
       ],
       "glossaries": [
           Formatter.format_minimal_glossary(glossary)
           for glossary in enriched_schema['glossaries']
       ],
       "metadata": {
           "totalEntities": len(enriched_schema['entities']),
           "totalColumns": sum(len(e['columns']) for e in enriched_schema['entities']),
           "totalRelationships": len(enriched_schema['relationships']),
           "totalGlossaryTerms": sum(len(g['terms']) for g in enriched_schema['glossaries']),
           "outputFormat": "minimal",
           "sizeReduction": "56%"
       }
   }
   
   return minimal_schema
   ```

### Template Generation Examples

**Entity Template**:
```python
def generate_entity_template(entity_context):
    purpose = "transactional data" if entity_context.entity_type == "fact" else "descriptive reference data"
    
    description = (
        f"The {entity_context.canonical_name} {entity_context.entity_type} serves as {purpose} "
        f"in the {entity_context.domain} domain. "
    )
    
    if entity_context.primary_key:
        description += f"It is uniquely identified by {entity_context.primary_key['column']}. "
    
    if entity_context.columns:
        key_columns = [c['name'] for c in entity_context.columns[:3]]
        description += f"Key columns include {', '.join(key_columns)}. "
    
    if entity_context.relationships:
        rel_count = len(entity_context.relationships)
        description += f"The entity has {rel_count} relationship(s) to other entities. "
    
    if entity_context.classifications:
        gov_tags = [c for c in entity_context.classifications if c.startswith('PII') or c.startswith('Finance')]
        if gov_tags:
            description += f"Governance classifications include {', '.join(gov_tags)}."
    
    return description
```

**Column Template**:
```python
def generate_column_template(column_context):
    description = (
        f"{column_context.canonical_name} is a {column_context.semantic_type or column_context.data_type_display} "
        f"column in the {column_context.entity_name} entity. "
    )
    
    if column_context.is_primary_key:
        description += "It serves as the primary key for unique record identification. "
    elif column_context.relationships:
        rel = column_context.relationships[0]
        description += f"It establishes a relationship to {rel['to_entity']}. "
    
    if not column_context.is_nullable:
        description += "This field is required (not nullable). "
    
    if column_context.classifications:
        pii_tags = [c for c in column_context.classifications if c.startswith('PII')]
        if pii_tags:
            description += "Contains personally identifiable information (PII) requiring access controls."
    
    return description
```

## Dependencies

### Required Python Packages
- `networkx`: Graph construction and analysis (optional)
- LLM service (shared with GlossaryAgent)

### Upstream Dependencies
- **All Agents**: ContextAgent consumes outputs from all prior agents
  - ProfilerAgent: Statistics and sample values (used, then stripped)
  - AlignerAgent: Canonical names, synonyms, confidence
  - ArchitectAgent: Relationships, OpenMetadata types
  - TaggerAgent: Classifications
  - GlossaryAgent: Glossary terms and definitions

### Downstream Consumers
- **Data Pipeline**: Uses minimal schema for OpenMetadata ingestion
  - Entity descriptions displayed in OpenMetadata UI
  - Column descriptions displayed in data catalog
  - Glossary terms linked to entities
- **Frontend**: Uses minimal schema for UI display
  - Entity cards show descriptions
  - Column tooltips show descriptions
  - Relationship graphs show semantic descriptions
  - Confidence scores for visual highlighting

## Error Handling

### Common Failure Scenarios

1. **LLM Service Unavailable**: Falls back to template-based descriptions
2. **LLM Timeout**: Retries with exponential backoff, then falls back to templates
3. **Graph Construction Failure**: Continues without graph (consolidation still works)
4. **Context Bundle Empty**: Skips description generation for that item
5. **Format Conversion Failure**: Logs error and skips problematic entity

### Logging
- INFO: Context generation start/completion, description counts, graph construction, LLM call status
- WARNING: LLM fallback to templates, graph construction disabled, missing context
- ERROR: LLM service failures, format conversion errors

## Metrics

Logged to observability:
- `entities_with_descriptions`: Count of entities with generated descriptions
- `columns_with_descriptions`: Count of columns with generated descriptions
- `relationships_with_narratives`: Count of relationships with enhanced narratives
- `glossary_terms_enriched`: Count of enriched glossary terms
- `domains_described`: Count of domains with descriptions
- `generation_time_seconds`: Total processing time
- `output_format`: `minimal` or `full`
- `llm_calls_total`: Total LLM API calls
- `llm_calls_failed`: Failed LLM calls
- `template_fallbacks`: Count of template fallbacks

## Future Extensions

### Planned Enhancements
1. **Advanced Graph Queries**: Complex multi-hop queries for richer context
2. **Description Caching**: Redis cache for generated descriptions
3. **Incremental Updates**: Only regenerate descriptions for changed entities
4. **Multi-Language Descriptions**: Generate descriptions in multiple languages
5. **Custom Description Templates**: Organization-specific templates
6. **User Feedback Loop**: Learn from user edits to improve descriptions
7. **Confidence-Based Prioritization**: Generate descriptions for high-confidence items first
8. **Rich Text Formatting**: Markdown or HTML formatting for descriptions

### Extension Points
- Add new narrative generator: Extend `generator.py`
- Customize templates: Modify `templates.py`
- Add graph queries: Extend `analyzer.py`
- Customize formatter: Modify `formatter.py`

