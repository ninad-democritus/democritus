# OpenMetadata Field Mapping and Ingestion Strategy

## Overview

This document details how the minimal schema output from the Context Agent maps to OpenMetadata API fields and how the data-pipeline service should perform ingestion after data loading is complete.

## Complete Minimal Schema Structure

The Context Agent outputs the following minimal structure (after workflow completes):

```json
{
  "entities": [
    {
      "name": "orders",
      "displayName": "Orders",
      "synonyms": ["Sales Orders", "Transactions"],
      "tableType": "Fact",
      "description": "The Orders table serves as the central fact table for sales transactions...",
      "tags": ["DataDomain.Fact"],
      "confidence": 0.89,
      "columns": [...]
    }
  ],
  "relationships": [
    {
      "fromEntity": "orders",
      "toEntity": "customer",
      "fromColumn": "customer_id",
      "toColumn": "customer_id",
      "relationshipType": "CONTAINS",
      "cardinality": "MANY_TO_ONE",
      "description": "Each order record is associated with exactly one customer...",
      "confidence": 0.87
    }
  ],
  "glossaries": [
    {
      "name": "SalesAndBilling",
      "displayName": "Sales & Billing",
      "description": "The Sales & Billing domain encompasses all data related to...",
      "terms": [...]
    }
  ],
  "summary": {
    "totalEntities": 4,
    "totalColumns": 32,
    "totalRelationships": 6,
    "totalGlossaryTerms": 12,
    "avgConfidence": 0.87
  }
}
```

---

## Entity (Table) Mapping

### Minimal Schema → OpenMetadata Table API

```python
# Input from Context Agent
entity = {
  "name": "orders",
  "displayName": "Orders",
  "synonyms": ["Sales Orders", "Transactions"],
  "tableType": "Fact",
  "description": "The Orders table serves as...",
  "tags": ["DataDomain.Fact"],
  "confidence": 0.89,
  "columns": [...]
}

# OpenMetadata Table Creation Payload
table_payload = {
  "name": entity["name"],                      # Technical name (lowercase, no spaces)
  "displayName": entity["displayName"],        # Human-readable name
  "description": entity["description"],        # ← From Context Agent (key value!)
  "tableType": entity["tableType"],            # Fact/Dimension
  "columns": [...],                            # See column mapping below
  "tags": [
    {"tagFQN": f"YourClassification.{tag}"}   # Map tags to OpenMetadata tag FQNs
    for tag in entity["tags"]
  ],
  "extension": {                               # Optional custom properties
    "synonyms": entity.get("synonyms", []),
    "aiGeneratedConfidence": entity.get("confidence")
  },
  "service": {                                 # Link to data source
    "id": "<your_data_service_id>",
    "type": "databaseService"
  },
  "database": {                                # Database/schema context
    "name": "<your_database_name>",
    "type": "database"
  },
  "databaseSchema": {
    "name": "<your_schema_name>",
    "type": "databaseSchema"
  }
}

# API Call
POST /api/v1/tables
Content-Type: application/json
Body: table_payload
```

### Key Points:
1. **`description`**: This is the primary value-add from Context Agent - rich business narrative
2. **`name` vs `displayName`**: Use lowercase `name` for technical identifier, `displayName` for UI
3. **`tableType`**: Maps directly from entity_type (Fact/Dimension)
4. **`tags`**: Convert tag strings to OpenMetadata tag FQNs (need to create tags first if they don't exist)
5. **`extension`**: Store synonyms and confidence as custom properties
6. **Service/Database/Schema**: You need to provide these from your data ingestion context

---

## Column Mapping

### Minimal Schema → OpenMetadata Column API

```python
# Input from Context Agent
column = {
  "name": "customer_id",
  "displayName": "Customer Identifier",
  "synonyms": ["Customer Reference", "Client ID"],
  "description": "References the customer who placed the order...",
  "dataType": "VARCHAR",
  "dataTypeDisplay": "varchar(36)",
  "dataLength": 36,
  "precision": null,
  "scale": null,
  "constraint": null,                    # or "PRIMARY_KEY"
  "nullable": false,
  "tags": ["Identifier.Foreign"],
  "glossaryTerms": [],                   # To be populated by glossary linking
  "confidence": 0.88
}

# OpenMetadata Column (inside Table payload)
column_payload = {
  "name": column["name"],
  "displayName": column["displayName"],
  "description": column["description"],         # ← From Context Agent
  "dataType": column["dataType"],              # VARCHAR, BIGINT, DECIMAL, etc.
  "dataLength": column.get("dataLength"),
  "precision": column.get("precision"),
  "scale": column.get("scale"),
  "constraint": column.get("constraint"),       # PRIMARY_KEY, UNIQUE, etc.
  "dataTypeDisplay": column["dataTypeDisplay"], # varchar(36), decimal(18,2)
  "tags": [
    {"tagFQN": f"YourClassification.{tag}"}
    for tag in column["tags"]
  ],
  "ordinalPosition": column_index,              # Column order (0-based)
  "children": None                              # For nested types (future)
}
```

### Key Points:
1. **`description`**: Rich business narrative from Context Agent
2. **`dataType`**: Already in OpenMetadata format (VARCHAR, BIGINT, DECIMAL, TIMESTAMP, etc.)
3. **`dataTypeDisplay`**: Human-readable type with length/precision
4. **`constraint`**: PRIMARY_KEY is automatically detected by Context Agent
5. **Glossary Terms**: Need to be linked separately (see glossary section)

---

## Relationship Mapping

### Minimal Schema → OpenMetadata Relationship

OpenMetadata doesn't have a first-class relationship API for table-to-table relationships. Options:

#### Option 1: Store in Table Description (Recommended for MVP)
```python
# Append relationship descriptions to table description
relationship_text = "\n\n**Relationships:**\n"
for rel in relationships:
    if rel["fromEntity"] == entity["name"]:
        relationship_text += f"- {rel['description']}\n"

table_payload["description"] += relationship_text
```

#### Option 2: Use Custom Properties Extension
```python
table_payload["extension"]["relationships"] = [
    {
        "to": rel["toEntity"],
        "type": rel["cardinality"],
        "description": rel["description"],
        "confidence": rel.get("confidence")
    }
    for rel in relationships
    if rel["fromEntity"] == entity["name"]
]
```

#### Option 3: Use Table Relationships API (OpenMetadata 1.2+)
```python
# Create explicit relationship
POST /api/v1/relationships
{
  "fromEntity": {
    "id": "<orders_table_id>",
    "type": "table"
  },
  "toEntity": {
    "id": "<customer_table_id>",
    "type": "table"
  },
  "relationshipType": "CONTAINS",        # or "UPSTREAM", "DOWNSTREAM"
  "description": relationship["description"]
}
```

### Key Points:
1. Relationship descriptions from Context Agent are valuable for documentation
2. Choose option based on OpenMetadata version and UI needs
3. Confidence can help UI highlight uncertain relationships for review

---

## Glossary Mapping

### Minimal Schema → OpenMetadata Glossary API

```python
# Input from Context Agent
glossary = {
  "name": "SalesAndBilling",
  "displayName": "Sales & Billing",
  "description": "The Sales & Billing domain encompasses...",
  "terms": [...]
}

# Step 1: Create Glossary
POST /api/v1/glossaries
{
  "name": glossary["name"],
  "displayName": glossary["displayName"],
  "description": glossary["description"],        # ← From Context Agent
  "owner": {
    "id": "<owner_user_id>",
    "type": "user"
  },
  "reviewers": []
}

# Response includes glossary ID
glossary_id = response["id"]
```

### Glossary Term Mapping

```python
# Input from Context Agent
term = {
  "name": "Customer",
  "displayName": "Customer",
  "description": "An individual or organization that purchases goods or services. In this system, customers are tracked...",
  "synonyms": ["Client", "Buyer"],
  "relatedTerms": ["Order", "Revenue"],
  "tags": ["DataDomain.Dimension"],
  "references": [
    {"type": "table", "name": "Customer"},
    {"type": "column", "name": "Orders.customer_id"}
  ]
}

# Step 2: Create Glossary Term
POST /api/v1/glossaryTerms
{
  "glossary": {
    "id": glossary_id,
    "type": "glossary"
  },
  "name": term["name"],
  "displayName": term["displayName"],
  "description": term["description"],           # ← Enriched by Context Agent
  "synonyms": term["synonyms"],
  "relatedTerms": [
    {
      "name": related_term,
      "displayName": related_term
    }
    for related_term in term["relatedTerms"]
  ],
  "tags": [
    {"tagFQN": f"YourClassification.{tag}"}
    for tag in term["tags"]
  ],
  "reviewers": [],
  "owner": {
    "id": "<owner_user_id>",
    "type": "user"
  }
}

# Response includes term ID
term_id = response["id"]
```

### Linking Terms to Tables/Columns

```python
# Step 3: Link glossary terms to entities
for reference in term["references"]:
    if reference["type"] == "table":
        # Update table with glossary term
        PATCH /api/v1/tables/{table_id}
        {
          "glossaryTerms": [
            {"id": term_id, "type": "glossaryTerm"}
          ]
        }
    
    elif reference["type"] == "column":
        # Update specific column with glossary term
        entity_name, column_name = reference["name"].split(".")
        
        # Get table, find column, update
        table = GET /api/v1/tables/name/{entity_name}
        
        for col in table["columns"]:
            if col["name"] == column_name:
                col["glossaryTerms"] = [
                    {"id": term_id, "type": "glossaryTerm"}
                ]
        
        # Update entire table
        PUT /api/v1/tables
        Body: table
```

### Key Points:
1. **Description enrichment**: Context Agent combines base definition + contextual narrative
2. **Related terms**: Automatically discovered through relationships
3. **References**: Need to look up table/column IDs after entities are created
4. **Two-phase approach**: Create glossary/terms first, then link to tables/columns

---

## Complete Ingestion Flow (data-pipeline service)

### Phase 1: Data Ingestion to Iceberg/Trino
```python
# Your existing data ingestion logic
ingest_data_to_iceberg(job_id, files)
```

### Phase 2: OpenMetadata Setup
```python
def setup_openmetadata_prerequisites(minimal_schema):
    """Create classification tags and data service if they don't exist"""
    
    # 1. Extract all unique tags
    all_tags = set()
    for entity in minimal_schema["entities"]:
        all_tags.update(entity.get("tags", []))
        for column in entity["columns"]:
            all_tags.update(column.get("tags", []))
    
    # 2. Create tag classifications if needed
    for tag in all_tags:
        classification, tag_name = tag.split(".")
        
        # Create classification (e.g., "DataDomain")
        create_classification_if_not_exists(classification)
        
        # Create tag (e.g., "Fact" under "DataDomain")
        create_tag_if_not_exists(classification, tag_name)
    
    # 3. Ensure data service exists
    service_id = get_or_create_data_service("TrinoService", "trino")
    database_id = get_or_create_database(service_id, "iceberg_db")
    schema_id = get_or_create_schema(database_id, "default")
    
    return service_id, database_id, schema_id
```

### Phase 3: Table/Column Ingestion
```python
def ingest_tables_to_openmetadata(minimal_schema, service_id, database_id, schema_id):
    """Create tables with descriptions and tags"""
    
    table_id_map = {}  # For relationship linking later
    
    for entity in minimal_schema["entities"]:
        # Build column payloads
        columns = []
        for idx, column in enumerate(entity["columns"]):
            col_payload = {
                "name": column["name"],
                "displayName": column["displayName"],
                "description": column["description"],  # Key value!
                "dataType": column["dataType"],
                "dataTypeDisplay": column["dataTypeDisplay"],
                "dataLength": column.get("dataLength"),
                "precision": column.get("precision"),
                "scale": column.get("scale"),
                "constraint": column.get("constraint"),
                "tags": [
                    {"tagFQN": f"{tag}"}  # Assuming full FQN
                    for tag in column.get("tags", [])
                ],
                "ordinalPosition": idx
            }
            columns.append(col_payload)
        
        # Build table payload
        table_payload = {
            "name": entity["name"],
            "displayName": entity["displayName"],
            "description": entity["description"],  # Key value!
            "tableType": entity["tableType"],
            "columns": columns,
            "tags": [
                {"tagFQN": tag}
                for tag in entity.get("tags", [])
            ],
            "extension": {
                "synonyms": entity.get("synonyms", []),
                "aiGeneratedConfidence": entity.get("confidence")
            },
            "service": {"id": service_id, "type": "databaseService"},
            "database": {"id": database_id, "type": "database"},
            "databaseSchema": {"id": schema_id, "type": "databaseSchema"}
        }
        
        # Create table
        response = openmetadata_client.create_or_update_table(table_payload)
        table_id_map[entity["name"]] = response["id"]
    
    return table_id_map
```

### Phase 4: Glossary Ingestion
```python
def ingest_glossaries_to_openmetadata(minimal_schema):
    """Create glossaries and terms with descriptions"""
    
    term_id_map = {}  # For linking to tables/columns
    
    for glossary in minimal_schema["glossaries"]:
        # Create glossary
        glossary_payload = {
            "name": glossary["name"],
            "displayName": glossary["displayName"],
            "description": glossary["description"],  # Key value!
            "owner": {"id": get_default_owner_id(), "type": "user"}
        }
        glossary_response = openmetadata_client.create_glossary(glossary_payload)
        glossary_id = glossary_response["id"]
        
        # Create terms
        for term in glossary["terms"]:
            term_payload = {
                "glossary": {"id": glossary_id, "type": "glossary"},
                "name": term["name"],
                "displayName": term["displayName"],
                "description": term["description"],  # Key value!
                "synonyms": term["synonyms"],
                "relatedTerms": [
                    {"name": rt, "displayName": rt}
                    for rt in term["relatedTerms"]
                ],
                "tags": [
                    {"tagFQN": tag}
                    for tag in term.get("tags", [])
                ],
                "owner": {"id": get_default_owner_id(), "type": "user"}
            }
            term_response = openmetadata_client.create_glossary_term(term_payload)
            term_id_map[term["name"]] = term_response["id"]
    
    return term_id_map
```

### Phase 5: Glossary-Table Linking
```python
def link_glossary_terms_to_tables(minimal_schema, table_id_map, term_id_map):
    """Link glossary terms to tables and columns"""
    
    for glossary in minimal_schema["glossaries"]:
        for term in glossary["terms"]:
            term_id = term_id_map.get(term["name"])
            if not term_id:
                continue
            
            # Process references
            for reference in term["references"]:
                if reference["type"] == "table":
                    table_id = table_id_map.get(reference["name"])
                    if table_id:
                        openmetadata_client.add_glossary_term_to_table(
                            table_id, term_id
                        )
                
                elif reference["type"] == "column":
                    entity_name, column_name = reference["name"].split(".")
                    table_id = table_id_map.get(entity_name)
                    if table_id:
                        openmetadata_client.add_glossary_term_to_column(
                            table_id, column_name, term_id
                        )
```

### Phase 6: Relationship Documentation
```python
def document_relationships(minimal_schema, table_id_map):
    """Add relationship descriptions to table descriptions"""
    
    for relationship in minimal_schema["relationships"]:
        from_table_id = table_id_map.get(relationship["fromEntity"])
        if from_table_id:
            # Get current table
            table = openmetadata_client.get_table(from_table_id)
            
            # Append relationship description
            rel_text = f"\n\n**Relationship**: {relationship['description']}"
            table["description"] += rel_text
            
            # Update table
            openmetadata_client.update_table(table)
```

---

## Complete Example Flow

```python
def ingest_to_openmetadata_complete(job_id, minimal_schema):
    """
    Complete ingestion flow from Context Agent output to OpenMetadata
    
    Args:
        job_id: Job identifier
        minimal_schema: Output from Context Agent
    """
    
    # Phase 1: Prerequisites
    service_id, database_id, schema_id = setup_openmetadata_prerequisites(minimal_schema)
    
    # Phase 2: Create tables and columns
    table_id_map = ingest_tables_to_openmetadata(
        minimal_schema, service_id, database_id, schema_id
    )
    
    # Phase 3: Create glossaries and terms
    term_id_map = ingest_glossaries_to_openmetadata(minimal_schema)
    
    # Phase 4: Link glossary terms to tables/columns
    link_glossary_terms_to_tables(minimal_schema, table_id_map, term_id_map)
    
    # Phase 5: Document relationships
    document_relationships(minimal_schema, table_id_map)
    
    logger.info(f"Successfully ingested {len(table_id_map)} tables to OpenMetadata for job {job_id}")
    
    return {
        "tables_created": len(table_id_map),
        "glossary_terms_created": len(term_id_map),
        "relationships_documented": len(minimal_schema["relationships"])
    }
```

---

## Key Takeaways

1. **Descriptions are the primary value**: Context Agent's narratives go into `description` fields across all entities
2. **Tags need pre-creation**: Extract all unique tags and create classification/tag hierarchy first
3. **Two-phase glossary**: Create glossaries/terms first, then link to tables/columns (need IDs)
4. **Relationships are metadata**: Store in descriptions or custom properties (no first-class API)
5. **Confidence is optional**: Can be stored in custom properties for UI highlighting
6. **IDs are required**: Build a map of names to IDs for linking
7. **Service context required**: Need to provide service/database/schema context from data ingestion

---

## Error Handling

```python
def safe_openmetadata_call(func, *args, **kwargs):
    """Wrapper for OpenMetadata API calls with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except OpenMetadataAPIError as e:
            if attempt == max_retries - 1:
                logger.error(f"OpenMetadata API call failed after {max_retries} attempts: {e}")
                raise
            logger.warning(f"OpenMetadata API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
```

---

## Next Steps

1. Implement `ingest_to_openmetadata_complete()` in data-pipeline service
2. Test with sample minimal schema from Context Agent
3. Verify descriptions, tags, and glossary links appear correctly in OpenMetadata UI
4. Add error handling and rollback logic for failed ingestions
5. Implement RAG embeddings (see `RAG-IMPLEMENTATION.md`)

