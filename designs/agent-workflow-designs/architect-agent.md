# ArchitectAgent Documentation

## Overview

The **ArchitectAgent** is the third agent in the workflow pipeline, responsible for transforming canonical entities into a complete relational schema with OpenMetadata-compatible types, inferred relationships with semantic enrichment, and confidence scoring. It bridges the gap between raw data understanding and a production-ready schema design.

### What It Does

1. **Schema Entity Building**: Converts canonical entities into schema entities with proper table names and column definitions
2. **OpenMetadata Type Mapping**: Maps physical types + semantic types to OpenMetadata-compatible database types (VARCHAR with lengths, DECIMAL with precision/scale, UUID, TIMESTAMP, etc.)
3. **Primary Key Selection**: Chooses best PK from ranked candidates provided by AlignerAgent
4. **Relationship Detection**: Identifies foreign key relationships and natural join keys using multiple strategies:
   - **Rule-based**: Pattern matching with synonym support
   - **Statistical**: Cardinality analysis and uniqueness profiling
   - **Semantic**: Type compatibility validation (prevents email↔phone matches)
5. **Cardinality Inference**: Determines relationship cardinality (M:1, 1:M, 1:1, M:M) from statistics
6. **Confidence Scoring**: Multi-factor weighted confidence with transparent breakdown
7. **Semantic Narratives**: Generates human-readable relationship descriptions

### Why These Design Choices

- **OpenMetadata Type Mapping**: Generic types like "string" aren't useful for database implementation. Semantic types enable precise mapping (email → VARCHAR(320), credit_card → VARCHAR(19), currency → DECIMAL(19,4)).
- **Semantic Type Enrichment**: Prevents false positives in relationship detection. Email and phone are both strings, but shouldn't be matched as FKs.
- **Multi-Strategy Detection**: Rule-based catches explicit FKs, statistical catches implicit relationships, semantic validation prevents mismatches.
- **Synonym Awareness**: FK patterns must consider all source names. "customer_id" in Orders might reference "cust_id" in Customers.
- **Transparent Confidence**: Multi-factor breakdown shows why each relationship was detected and how confident we are. Essential for validation workflows.
- **Semantic Narratives**: Auto-generated descriptions like "Each Order belongs to one Customer via email address match" provide business context.
- **Cardinality Analysis**: Statistical inference from uniqueness ratios is more reliable than rules. Handles real data patterns.
- **Backward Compatibility**: Output format compatible with TaggerAgent while adding rich semantic metadata.

## Folder Structure

```
services/agent-workflow/app/agents/architect/
├── __init__.py
├── agent.py                                    # Main orchestrator
├── models.py                                   # Enhanced data structures
├── config.py                                   # Configuration management
├── schema/                                     # Schema building components
│   ├── __init__.py
│   ├── type_mapper.py                          # OpenMetadata type mapping
│   ├── entity_builder.py                       # Entity → SchemaEntity conversion
│   └── primary_key_selector.py                 # PK selection logic
├── relationships/                              # Relationship detection modules
│   ├── __init__.py
│   ├── rule_based/                             # Pattern-based detection
│   │   ├── __init__.py
│   │   ├── fk_matcher.py                       # FK pattern matching with synonyms
│   │   ├── common_column_matcher.py            # Natural join key detection
│   │   └── name_similarity.py                  # RapidFuzz-based similarity (fallback)
│   ├── statistical/                            # Statistical analysis
│   │   ├── __init__.py
│   │   ├── type_compatibility.py               # Semantic type compatibility matrix
│   │   ├── cardinality_analyzer.py             # Cardinality inference from statistics
│   │   └── uniqueness_profiler.py              # Column uniqueness analysis
│   ├── llm_based/                              # LLM validation (future)
│   │   └── __init__.py
│   └── merger.py                               # Relationship deduplication
├── confidence/                                 # Confidence scoring
│   ├── __init__.py
│   └── scorer.py                               # Multi-factor weighted confidence
├── semantics/                                  # Semantic narrative generation
│   ├── __init__.py
│   ├── templates.py                            # Cardinality-based templates
│   └── narrative_generator.py                  # Human-readable descriptions
└── graph/                                      # Future: graph-based analysis
    └── __init__.py
```

### File Responsibilities

#### Core Files
- **`agent.py`**: Main orchestrator coordinating schema design
  - Entry point: `design_schema(entities)`
  - Builds schema entities with OpenMetadata types
  - Detects relationships via rule-based and statistical strategies
  - Merges and deduplicates relationships
  - Scores confidence with detailed breakdown
  - Generates semantic narratives
  - Returns dict with entities, relationships, metadata_summary

- **`models.py`**: Enhanced data structures
  - `SchemaEntity`: Entity with OpenMetadata-compatible columns
  - `ColumnSchema`: Column with type details (length, precision, scale)
  - `Relationship`: Relationship with confidence breakdown and semantic description
  - `OpenMetadataType`: Structured type information for database schema
  - `PKCandidate`: Primary key candidate information

#### Schema Building Module (`schema/`)

- **`type_mapper.py`**: OpenMetadata type mapping
  - Maps (physical type, semantic type) → OpenMetadata type
  - **String types**:
    - `email` → VARCHAR(320)
    - `url` → VARCHAR(2048)
    - `uuid` → UUID
    - `phone_number` → VARCHAR(20)
    - `ssn` → VARCHAR(11)
    - `credit_card` → VARCHAR(19)
    - `zipcode` → VARCHAR(10)
    - Default → VARCHAR(255)
  - **Numeric types**:
    - `currency.amount` → DECIMAL(19,4)
    - `percentage` → DECIMAL(5,2)
    - Integer → BIGINT
    - Float → DECIMAL(18,2)
  - **Temporal types**:
    - `datetime` → TIMESTAMP
    - `date` → DATE
    - `time` → TIME
  - Returns `OpenMetadataType` with `data_type`, `data_type_display`, `data_length`, `precision`, `scale`

- **`entity_builder.py`**: Converts Entity → SchemaEntity
  - Creates table names (canonical name → snake_case)
  - Selects primary key using PK candidates
  - Converts columns using type_mapper
  - Preserves all upstream metadata (alignment confidence, semantic types)
  - Returns fully typed SchemaEntity

- **`primary_key_selector.py`**: PK selection logic
  - Uses ranked `primary_key_candidates` from AlignerAgent
  - Selects highest confidence candidate
  - Sets `constraint: PRIMARY_KEY` and `is_unique: true`
  - Falls back to first column if no candidates (warning logged)

#### Relationships Module (`relationships/`)

##### Rule-Based Detection (`rule_based/`)

- **`fk_matcher.py`**: Foreign key pattern matching
  - Detects patterns like: `{entity}_id`, `{entity}_key`, `id_{entity}`
  - Considers all entity variations:
    - Canonical name: "Customer"
    - Synonyms: "Client", "Cust"
    - Raw names: "customer_master", "CUST_TBL"
  - Validates semantic type compatibility (prevents email↔phone matches)
  - Returns candidate relationships with detection method
  - **Example**: `customer_id` in Orders matches entity "Customers" (via synonym "cust")

- **`common_column_matcher.py`**: Natural join key detection
  - Finds columns with identical names in different entities
  - Requires semantic type compatibility
  - Excludes primary keys (already matched as FKs)
  - Useful for implicit relationships (e.g., "region" in Sales and Territories)
  - Returns candidate relationships with detection method

- **`name_similarity.py`**: Fuzzy name matching
  - Uses RapidFuzz for similarity scoring (fallback: basic string comparison)
  - Similarity threshold: 0.85
  - Used when exact pattern matching fails
  - Handles typos and variations ("custmer_id" vs "customer_id")

##### Statistical Analysis (`statistical/`)

- **`type_compatibility.py`**: Semantic type compatibility matrix
  - Compatibility scores (0.0 to 1.0) for semantic type pairs
  - **High compatibility** (1.0):
    - Same semantic type (email↔email, uuid↔uuid)
    - Unknown types (allows matching if names match)
  - **Low compatibility** (0.1-0.3):
    - Different specific types (email↔phone, ssn↔credit_card)
  - **Zero compatibility** (0.0):
    - Incompatible types (currency↔datetime, url↔ssn)
  - Prevents false positives from name-only matching

- **`cardinality_analyzer.py`**: Infers relationship cardinality
  - Analyzes uniqueness ratios on both sides:
    - `from_uniqueness = from_distinct / from_total`
    - `to_uniqueness = to_distinct / to_total`
  - **Many-to-One** (M:1): from_uniqueness < 0.95, to_uniqueness ≥ 0.95
  - **One-to-Many** (1:M): from_uniqueness ≥ 0.95, to_uniqueness < 0.95
  - **One-to-One** (1:1): Both ≥ 0.95
  - **Many-to-Many** (M:M): Both < 0.95
  - Returns cardinality + confidence based on how clear the signal is

- **`uniqueness_profiler.py`**: Column uniqueness analysis
  - Extracts distinct_count and total_count from statistics
  - Computes uniqueness ratio
  - Used by cardinality analyzer and PK selector

##### Relationship Merger (`merger.py`)

- **Deduplication**: Merges relationships from multiple detection strategies
  - Key: (from_entity, from_column, to_entity, to_column)
  - Keeps highest confidence match
- **Metadata Merging**: Combines detection methods when relationships match
  - Example: Same FK detected by both rule-based and common columns
- **Threshold Filtering**: Removes low-confidence relationships (< 0.6 default)

#### Confidence Scoring Module (`confidence/`)

- **`scorer.py`**: Multi-factor weighted confidence calculation
  - **Name similarity** (35% weight): How well column names match entity variations
  - **Semantic compatibility** (30% weight): From type_compatibility matrix
  - **Type compatibility** (10% weight): Physical data type match (both string, both numeric)
  - **Uniqueness signal** (15% weight): Column uniqueness supports FK hypothesis
  - **Cardinality confidence** (±15% adjustment): How clear the cardinality signal is
  - **Optional LLM validation** (10% weight): Future enhancement
  - Returns confidence (0.0-1.0) + detailed breakdown dict
  - **Transparency**: Each factor visible for debugging and validation

#### Semantics Module (`semantics/`)

- **`templates.py`**: Cardinality-based narrative templates
  - **Many-to-One**: "Each {from_entity} belongs to one {to_entity}"
  - **One-to-Many**: "Each {to_entity} has many {from_entity}"
  - **One-to-One**: "Each {from_entity} corresponds to one {to_entity}"
  - **Many-to-Many**: "{from_entity} are associated with multiple {to_entity}"
  - Customizable via configuration

- **`narrative_generator.py`**: Human-readable relationship descriptions
  - Applies templates with entity names
  - Adds semantic context: "via email address match"
  - Includes confidence language: "confirmed", "likely", "possible"
  - **Example**: "Each Order belongs to one Customer via customer_id foreign key match (confirmed, 87% confidence)"

#### Configuration (`config.py`)

- Feature toggles:
  - `ARCHITECT_USE_RULE_BASED`: Enable FK pattern matching (default: true)
  - `ARCHITECT_USE_STATISTICAL`: Enable cardinality analysis (default: true)
  - `ARCHITECT_USE_SEMANTIC`: Enable semantic type validation (default: true)
  - `ARCHITECT_USE_LLM_DETECTION`: Enable LLM relationship detection (default: false, future)
  - `ARCHITECT_USE_LLM_VALIDATION`: Enable LLM relationship validation (default: true, future)
  - `ARCHITECT_USE_LLM_SEMANTICS`: Enable LLM semantic narratives (default: true, future)
- Confidence thresholds:
  - `ARCHITECT_MIN_CONFIDENCE`: Minimum relationship confidence (default: 0.6)
- Scoring weights (customizable)

## Input/Output Contracts

### Input

**Function Signature:**
```python
async def design_schema(entities: List[Entity]) -> Dict[str, Any]
```

**Parameters:**
- `entities` (List[Entity]): Output from AlignerAgent containing:
  - Canonical entity names and synonyms
  - Columns with alignment confidence, semantic types
  - Primary key candidates with rankings
  - Entity classification (fact/dimension)
  - Statistics for all columns

**Dependencies on AlignerAgent Output:**
- `name`, `original_names` (synonyms): Used for FK pattern matching
- `columns[].name`, `columns[].original_names`: Used for FK and join key detection
- `columns[].semantic_type`: Used for type compatibility validation
- `columns[].alignment_confidence`: Propagated to output
- `columns[].is_primary_key`: Used to exclude PKs from common column matching
- `columns[].distinct_count`, `total_count`: Used for cardinality analysis
- `primary_key_candidates`: Used for PK selection
- `type`: Entity classification propagated to output

### Output

**Return Type:** `Dict[str, Any]`

**Schema Structure:**
```python
{
  "entities": [                              # List of SchemaEntity objects
    {
      "entity_id": "entity_1",               # Unique entity identifier
      "canonical_name": "Customers",         # Display name
      "raw_names": [                         # All source names
        "customer_master",
        "customers",
        "client_data"
      ],
      "synonyms": ["Clients", "Custs"],      # Alternate names (AlignerAgent)
      "table_name": "customers",             # Database table name (snake_case)
      "primary_key": {                       # Selected PK
        "column": "customer_id",
        "is_unique": true
      },
      "columns": [                           # List of ColumnSchema objects
        {
          "name": "customer_id",
          "data_type": "UUID",               # OpenMetadata type
          "data_type_display": "UUID",       # Human-readable
          "data_length": null,
          "precision": null,
          "scale": null,
          "array_data_type": null,
          "semantic_type": "uuid",           # From ProfilerAgent
          "semantic_type_confidence": 0.92,  # From ProfilerAgent
          "alignment_confidence": 0.94,      # From AlignerAgent
          "nullable": false,
          "constraint": "PRIMARY_KEY",       # NEW: Constraint annotation
          "is_primary_key": true,
          "is_unique": true,
          "synonyms": ["cust_id", "customer_identifier"],
          "raw_names": ["cust_id", "customer_identifier", "client_id"],
          "distinct_count": 9832,
          "total_count": 30000,
          "null_count": 0
        },
        {
          "name": "email",
          "data_type": "VARCHAR",
          "data_type_display": "VARCHAR(320)",
          "data_length": 320,                # Email max length
          "precision": null,
          "scale": null,
          "semantic_type": "email",
          "semantic_type_confidence": 0.95,
          "alignment_confidence": 0.88,
          "nullable": true,
          "constraint": null,
          "is_primary_key": false,
          "is_unique": false,
          "synonyms": ["customer_email", "contact_email"],
          "raw_names": ["customer_email", "email_address", "contact_email"],
          "distinct_count": 9645,
          "total_count": 30000,
          "null_count": 234
        },
        {
          "name": "lifetime_value",
          "data_type": "DECIMAL",
          "data_type_display": "DECIMAL(19,4)",
          "data_length": null,
          "precision": 19,
          "scale": 4,
          "semantic_type": "currency.amount",
          "semantic_type_confidence": 0.87,
          "alignment_confidence": 0.91,
          "nullable": false,
          "constraint": null,
          "is_primary_key": false,
          "is_unique": false,
          "synonyms": ["ltv", "customer_ltv"],
          "raw_names": ["ltv", "customer_ltv", "total_lifetime_value"],
          "distinct_count": 8732,
          "total_count": 30000,
          "null_count": 0
        }
      ],
      "entity_type": "dimension",            # From AlignerAgent
      "row_count": 30000,
      "source_files": [                      # From AlignerAgent
        "customer_master.xlsx",
        "customers.csv"
      ],
      "alignment_confidence": 0.94           # From AlignerAgent
    }
  ],
  "relationships": [                         # List of Relationship objects
    {
      "relationship_id": "rel_1",            # Unique identifier
      "from_entity": "Orders",               # Source entity
      "to_entity": "Customers",              # Target entity
      "from_column": "customer_id",          # Foreign key column
      "to_column": "customer_id",            # Referenced column (usually PK)
      "cardinality": "many_to_one",          # M:1, 1:M, 1:1, M:M
      "confidence": 0.87,                    # Overall confidence
      "confidence_breakdown": {              # Transparent scoring
        "name_similarity": 0.95,             # Column name matches entity pattern
        "semantic_compatibility": 1.0,       # Both UUID type
        "type_compatibility": 1.0,           # Both string type
        "uniqueness_signal": 0.78,           # From column has low uniqueness
        "cardinality_confidence": 0.92       # Clear M:1 signal
      },
      "detection_method": [                  # How detected
        "rule_based.fk_matcher",
        "statistical.cardinality"
      ],
      "semantic_description": "Each Order belongs to one Customer via customer_id foreign key match", # NEW
      "metadata": {                          # Additional context
        "from_distinct_count": 9832,
        "from_total_count": 50000,
        "to_distinct_count": 9832,
        "to_total_count": 30000,
        "from_uniqueness": 0.197,            # 9832/50000 = low (many orders per customer)
        "to_uniqueness": 0.328               # 9832/30000 = high (unique customer IDs)
      }
    }
  ],
  "metadata_summary": {                      # Summary statistics
    "total_entities": 5,
    "fact_tables": 2,
    "dimension_tables": 3,
    "total_columns": 47,
    "total_relationships": 8,
    "avg_relationship_confidence": 0.81,
    "high_confidence_relationships": 6,     # Confidence > 0.8
    "medium_confidence_relationships": 2,   # Confidence 0.6-0.8
    "low_confidence_relationships": 0       # Confidence < 0.6 (filtered out)
  }
}
```

### Output Characteristics

**New Fields Added by ArchitectAgent:**

**Entity Level:**
1. **`table_name`**: Database-friendly table name (snake_case)
2. **`primary_key`**: Selected PK with uniqueness flag
3. **`entity_id`**: Unique identifier for entity

**Column Level:**
1. **`data_type`**: OpenMetadata-compatible type
2. **`data_type_display`**: Human-readable type with length/precision
3. **`data_length`**, **`precision`**, **`scale`**: Type parameters
4. **`constraint`**: PRIMARY_KEY or null
5. **`is_unique`**: Uniqueness constraint flag

**Relationships:**
1. **`relationships`**: Complete list of detected relationships
2. **`cardinality`**: Statistical inference (many_to_one, one_to_many, one_to_one, many_to_many)
3. **`confidence`**: Multi-factor weighted score
4. **`confidence_breakdown`**: Per-factor scores for transparency
5. **`detection_method`**: List of detection strategies that found this relationship
6. **`semantic_description`**: Human-readable narrative
7. **`metadata`**: Statistical details supporting cardinality inference

**Propagated from AlignerAgent:**
- `canonical_name`, `raw_names`, `synonyms`
- `semantic_type`, `semantic_type_confidence`
- `alignment_confidence`
- `entity_type`, `source_files`
- Column statistics (distinct_count, null_count, etc.)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARCHITECT_USE_RULE_BASED` | `true` | Enable FK pattern matching |
| `ARCHITECT_USE_STATISTICAL` | `true` | Enable cardinality analysis |
| `ARCHITECT_USE_SEMANTIC` | `true` | Enable semantic type validation |
| `ARCHITECT_USE_LLM_DETECTION` | `false` | Enable LLM relationship detection (future) |
| `ARCHITECT_USE_LLM_VALIDATION` | `true` | Enable LLM relationship validation (future) |
| `ARCHITECT_USE_LLM_SEMANTICS` | `true` | Enable LLM semantic narratives (future) |
| `ARCHITECT_MIN_CONFIDENCE` | `0.6` | Minimum relationship confidence threshold |
| `ARCHITECT_SEMANTIC_WEIGHT` | `0.4` | Weight of semantic compatibility in scoring |

### Detection Strategy Configuration

**Rule-Based Detection:**
- FK patterns: `{entity}_id`, `{entity}_key`, `id_{entity}`, `fk_{entity}`
- Considers canonical names, synonyms, and raw names from AlignerAgent
- Semantic type validation prevents false positives

**Statistical Analysis:**
- Cardinality inference from uniqueness ratios
- Threshold: 0.95 for "unique" determination
- Confidence based on signal clarity

**Semantic Validation:**
- Type compatibility matrix prevents incompatible matches
- Configurable weight in overall confidence scoring

## Algorithms

### OpenMetadata Type Mapping Algorithm

```python
def map_type(physical_type: str, semantic_type: str) -> OpenMetadataType:
    # Semantic type takes precedence
    if semantic_type == "email":
        return OpenMetadataType("VARCHAR", "VARCHAR(320)", length=320)
    elif semantic_type == "uuid":
        return OpenMetadataType("UUID", "UUID")
    elif semantic_type == "currency.amount":
        return OpenMetadataType("DECIMAL", "DECIMAL(19,4)", precision=19, scale=4)
    elif semantic_type == "url":
        return OpenMetadataType("VARCHAR", "VARCHAR(2048)", length=2048)
    # ... more semantic mappings ...
    
    # Fall back to physical type
    elif physical_type == "integer":
        return OpenMetadataType("BIGINT", "BIGINT")
    elif physical_type == "float":
        return OpenMetadataType("DECIMAL", "DECIMAL(18,2)", precision=18, scale=2)
    elif physical_type == "datetime":
        return OpenMetadataType("TIMESTAMP", "TIMESTAMP")
    # ... default mappings ...
    
    # Default
    return OpenMetadataType("VARCHAR", "VARCHAR(255)", length=255)
```

### Relationship Detection Algorithm

1. **Rule-Based Detection**:
   ```python
   for entity in entities:
       for other_entity in entities:
           if entity == other_entity:
               continue
           for column in entity.columns:
               # Check FK patterns
               for variation in [other_entity.name, *other_entity.synonyms, *other_entity.raw_names]:
                   if matches_fk_pattern(column.name, variation):
                       # Validate semantic compatibility
                       if is_semantically_compatible(column, other_entity.primary_key):
                           relationships.append(create_relationship(entity, column, other_entity))
   ```

2. **Common Column Detection**:
   ```python
   for entity_a in entities:
       for entity_b in entities:
           if entity_a == entity_b:
               continue
           common_columns = find_common_columns(entity_a, entity_b)
           for col_a, col_b in common_columns:
               # Exclude primary keys (already matched as FKs)
               if not (col_a.is_primary_key or col_b.is_primary_key):
                   # Validate semantic compatibility
                   if is_semantically_compatible(col_a, col_b):
                       relationships.append(create_relationship(entity_a, col_a, entity_b, col_b))
   ```

3. **Cardinality Analysis** (for each relationship):
   ```python
   from_uniqueness = from_column.distinct_count / from_column.total_count
   to_uniqueness = to_column.distinct_count / to_column.total_count
   
   if from_uniqueness < 0.95 and to_uniqueness >= 0.95:
       cardinality = "many_to_one"
       confidence = 0.9 + (to_uniqueness - 0.95) * 2  # Boost for very unique
   elif from_uniqueness >= 0.95 and to_uniqueness < 0.95:
       cardinality = "one_to_many"
       confidence = 0.9 + (from_uniqueness - 0.95) * 2
   elif from_uniqueness >= 0.95 and to_uniqueness >= 0.95:
       cardinality = "one_to_one"
       confidence = 0.95
   else:
       cardinality = "many_to_many"
       confidence = 0.7  # Less certain
   ```

4. **Confidence Scoring**:
   ```python
   name_similarity = calculate_name_similarity(from_column, to_entity)
   semantic_compatibility = get_semantic_compatibility(from_column.semantic_type, to_column.semantic_type)
   type_compatibility = 1.0 if from_column.data_type == to_column.data_type else 0.5
   uniqueness_signal = 1.0 - from_uniqueness  # Low uniqueness = good FK signal
   
   confidence = (
       name_similarity * 0.35 +
       semantic_compatibility * 0.30 +
       type_compatibility * 0.10 +
       uniqueness_signal * 0.15
   )
   
   # Adjust by cardinality confidence
   confidence = confidence * (0.85 + cardinality_confidence * 0.15)
   ```

5. **Deduplication**:
   ```python
   relationship_map = {}
   for rel in all_relationships:
       key = (rel.from_entity, rel.from_column, rel.to_entity, rel.to_column)
       if key not in relationship_map or rel.confidence > relationship_map[key].confidence:
           relationship_map[key] = rel
   
   final_relationships = [rel for rel in relationship_map.values() if rel.confidence >= min_confidence]
   ```

6. **Semantic Narrative Generation**:
   ```python
   template = get_cardinality_template(relationship.cardinality)
   description = template.format(
       from_entity=relationship.from_entity,
       to_entity=relationship.to_entity
   )
   
   # Add semantic context
   if relationship.detection_method includes "fk_matcher":
       description += f" via {relationship.from_column} foreign key match"
   elif relationship.detection_method includes "common_column":
       description += f" via shared {relationship.from_column} attribute"
   
   # Add confidence language
   if relationship.confidence > 0.85:
       description += " (confirmed)"
   elif relationship.confidence > 0.70:
       description += " (likely)"
   else:
       description += " (possible)"
   ```

## Dependencies

### Required Python Packages
- `pydantic`: Data models
- `rapidfuzz`: Fuzzy string matching (optional, falls back to basic)
- `numpy`: Statistical calculations

### Upstream Dependencies
- **AlignerAgent**: All outputs consumed
  - Entity names, synonyms, raw names
  - Column metadata with alignment confidence
  - Primary key candidates
  - Entity classification
  - Statistics for cardinality

### Downstream Consumers
- **TaggerAgent**: Uses ArchitectAgent outputs for classification
  - Relationships for JoinKey classification
  - Entity types for context classification
  - Confidence scores for quality signals
  - OpenMetadata types propagated

- **GlossaryAgent**: Uses ArchitectAgent outputs for term extraction
  - Relationships for related terms identification
  - Entity types for domain formation
  - Semantic descriptions for context
  - Primary keys for key identifier terms

- **ContextAgent**: Uses ArchitectAgent outputs for narrative generation
  - Relationships for entity descriptions
  - Semantic descriptions as base narratives
  - Confidence scores for confidence-aware language

## Error Handling

### Common Failure Scenarios

1. **No Primary Key Candidates**: Falls back to first column with warning
2. **No Relationships Detected**: Returns empty relationships list (valid scenario)
3. **Type Mapping Failure**: Falls back to VARCHAR(255)
4. **Cardinality Analysis Failure**: Falls back to many-to-many with low confidence

### Logging
- INFO: Schema building start/completion, relationship detection counts, cardinality inference
- WARNING: No PK candidates, low confidence relationships, type mapping fallbacks
- ERROR: Schema building failures, relationship detection errors

## Future Extensions

### Planned Enhancements
1. **LLM Relationship Detection**: Use LLM to suggest non-obvious relationships
2. **LLM Relationship Validation**: Validate detected relationships with LLM
3. **LLM Semantic Narratives**: Generate richer narratives with business context
4. **Complex Type Support**: ARRAY, MAP, STRUCT types for nested data
5. **Graph-Based Analysis**: Use graph algorithms for transitive relationship inference
6. **Multi-Hop Relationships**: Detect indirect relationships via join paths
7. **Constraint Detection**: UNIQUE, CHECK constraints beyond PRIMARY_KEY
8. **Index Recommendations**: Suggest indexes based on relationship patterns

### Extension Points
- Add new type mappings: Extend `type_mapper.py`
- Add new detection strategy: Implement in `relationships/`
- Customize confidence scoring: Modify weights in `scorer.py`
- Customize semantic narratives: Extend `templates.py`

