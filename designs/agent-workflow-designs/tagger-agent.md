# TaggerAgent Documentation

## Overview

The **TaggerAgent** is the fourth agent in the workflow pipeline, responsible for applying OpenMetadata governance classification tags to entities and columns. It focuses on data governance, privacy, and compliance tagging (PII, Finance, Temporal, DataDomain) rather than business intelligence descriptions.

### What It Does

1. **Governance Classification**: Assigns OpenMetadata classification tags for governance and compliance
2. **Multi-Source Classification**: Combines evidence from:
   - **Semantic types**: Maps semantic types to classifications (email → PII.Sensitive)
   - **Name patterns**: Analyzes canonical names and synonyms for classification keywords
   - **Statistics**: Uses cardinality and data quality metrics for classification
   - **Context**: Leverages entity types and relationships for domain classification
3. **Upstream Confidence Integration**: Adjusts classification confidence based on upstream quality signals from ProfilerAgent and AlignerAgent
4. **Classification Merging**: Deduplicates and merges classifications from multiple sources
5. **Mutual Exclusivity Enforcement**: Ensures only one classification per category (e.g., only one PII sub-classification)
6. **Provenance Tracking**: Records which upstream confidence scores influenced each classification decision

### Why These Design Choices

- **Governance Focus, Not Business Descriptions**: OpenMetadata has separate fields for governance tags vs business descriptions. TaggerAgent handles governance; ContextAgent handles descriptions later.
- **Upstream Confidence Integration**: If ProfilerAgent is uncertain about semantic type (low confidence), we should be uncertain about PII classification. Cascading quality is essential.
- **Multi-Source Evidence**: Single-source classification is fragile. Combining semantic types, name patterns, statistics, and context provides robust classification.
- **Provenance Tracking**: For audit and validation, we need to know WHY each classification was applied and which upstream signals influenced it.
- **Mutual Exclusivity**: Data can't be both PII.Sensitive and PII.NonSensitive. Enforcement prevents contradictions.
- **Pure Passthrough**: All upstream metadata (semantic types, relationships, statistics, confidence scores) must pass through unchanged for downstream agents.
- **Classification Taxonomy**: Full OpenMetadata-compatible hierarchy ensures interoperability with OpenMetadata ingestion.

## Folder Structure

```
services/agent-workflow/app/agents/tagger/
├── __init__.py
├── agent.py                                # Main orchestrator coordinating classifiers
├── models.py                               # Data structures (Classification, ClassificationResult)
├── config.py                               # Configuration with confidence thresholds
├── taxonomy/                               # OpenMetadata classification taxonomy
│   ├── __init__.py
│   ├── definitions.py                      # Classification hierarchy and mutual exclusivity rules
│   └── keywords.py                         # Semantic type mappings and keyword dictionaries
├── classifiers/                            # Classification assignment logic
│   ├── __init__.py
│   ├── base.py                             # Abstract classifier interface
│   ├── semantic_type_classifier.py         # Maps semantic types to classifications
│   ├── name_pattern_classifier.py          # Pattern-based classification matching
│   ├── statistical_classifier.py           # Statistics-based classification
│   ├── context_classifier.py               # Entity type and relationship context
│   └── merger.py                           # Classification merging and deduplication
├── confidence/                             # Confidence scoring
│   ├── __init__.py
│   └── scorer.py                           # Multi-factor confidence calculation
├── rules/                                  # Business rules and heuristics (reserved)
│   └── __init__.py
└── utils/                                  # Helper utilities (reserved)
    └── __init__.py
```

### File Responsibilities

#### Core Files
- **`agent.py`**: Main orchestrator coordinating classification workflow
  - Entry point: `enrich_schema(schema)`
  - Invokes all classifiers (semantic, name pattern, statistical, context)
  - Merges classifications from multiple sources
  - Enforces mutual exclusivity rules
  - Adjusts confidence based on upstream quality signals
  - Adds `classifications` to entities and columns
  - Adds `classification_summary` to schema
  - Returns enriched schema (additive, preserves all upstream data)

- **`models.py`**: Data structures for classification
  - `Classification`: Single classification with tag, confidence, source, upstream_factors
  - `ClassificationResult`: Complete classification output with summary
  - `ConfidenceBreakdown`: Detailed confidence factor breakdown

- **`config.py`**: Configuration management
  - Confidence thresholds (semantic_type, alignment, classification minimum)
  - Classifier weights
  - Feature toggles

#### Taxonomy Module (`taxonomy/`)

- **`definitions.py`**: OpenMetadata classification taxonomy
  - **Classification Hierarchy**:
    ```
    PII
      ├── PII.Sensitive (SSN, credit card, medical records)
      └── PII.NonSensitive (name, address, phone)
    Finance
      ├── Finance.Revenue (sales, revenue, income)
      ├── Finance.Cost (expenses, costs)
      └── Finance.Reporting (financial statements, KPIs)
    Temporal
      ├── Temporal.Transaction (order date, transaction timestamp)
      ├── Temporal.Effective (start date, end date, valid from/to)
      └── Temporal.Reporting (fiscal period, reporting date)
    DataDomain
      ├── DataDomain.Fact (transactional data)
      ├── DataDomain.Dimension (descriptive data)
      └── DataDomain.JoinKey (foreign key relationships)
    DataQuality
      ├── DataQuality.Nullable (high null percentage)
      ├── DataQuality.Categorical (low cardinality)
      └── DataQuality.Unique (high uniqueness)
    Contact
      ├── Contact.Email (email addresses)
      └── Contact.Phone (phone numbers)
    Identity
      ├── Identity.UUID (UUID identifiers)
      └── Identity.NaturalKey (business identifiers)
    Geographical
      └── Geographical.Location (address, zipcode, region)
    ```
  - **Mutual Exclusivity Rules**:
    - Only one PII sub-classification (Sensitive XOR NonSensitive)
    - Only one DataDomain per entity (Fact XOR Dimension)
    - Multiple classifications allowed across categories

- **`keywords.py`**: Classification keyword dictionaries
  - **Semantic Type Mappings**:
    ```python
    SEMANTIC_TYPE_CLASSIFICATION_MAP = {
        "email": ["PII.Sensitive", "Contact.Email"],
        "ssn": ["PII.Sensitive", "Identity.NaturalKey"],
        "credit_card": ["PII.Sensitive", "Finance.Revenue"],
        "phone_number": ["PII.NonSensitive", "Contact.Phone"],
        "uuid": ["Identity.UUID"],
        "currency.amount": ["Finance.Revenue"],
        ...
    }
    ```
  - **Name Pattern Keywords**:
    ```python
    CLASSIFICATION_KEYWORDS = {
        "PII.Sensitive": ["ssn", "social_security", "credit_card", "password", "medical"],
        "Finance.Revenue": ["revenue", "sales", "income", "amount", "price"],
        "Finance.Cost": ["cost", "expense", "fee", "charge"],
        "Temporal.Transaction": ["date", "timestamp", "time", "created_at", "updated_at"],
        ...
    }
    ```
  - **Fuzzy Matching**: Uses partial string matching with confidence adjustment

#### Classifiers Module (`classifiers/`)

- **`base.py`**: Abstract classifier interface
  - `classify_entity(entity)`: Returns list of Classifications
  - `classify_column(column)`: Returns list of Classifications
  - All classifiers implement this interface

- **`semantic_type_classifier.py`**: Semantic type-based classification
  - Maps `semantic_type` from ProfilerAgent to classifications
  - **Base confidence**: 0.92 (high because ML-based)
  - **Adjustment**: Reduces confidence if `semantic_type_confidence` < 0.7
    ```python
    if semantic_type_confidence < 0.7:
        penalty = (0.7 - semantic_type_confidence) * 0.3
        classification_confidence *= (1.0 - penalty)
    ```
  - **Upstream factors tracked**: `semantic_type`, `semantic_type_confidence`
  - **Example**: email semantic type → [PII.Sensitive, Contact.Email] at 0.92 confidence

- **`name_pattern_classifier.py`**: Name pattern-based classification
  - Analyzes canonical names and synonyms from AlignerAgent
  - Fuzzy matches against keyword dictionaries
  - **Base confidence**: 0.70-0.90 based on match quality
    - Exact match: 0.90
    - Partial match: 0.70-0.85 (based on match percentage)
  - **Adjustment**: Reduces confidence if `alignment_confidence` < 0.6
    ```python
    if alignment_confidence < 0.6:
        penalty = (0.6 - alignment_confidence) * 0.25
        classification_confidence *= (1.0 - penalty)
    ```
  - **Upstream factors tracked**: `alignment_confidence`
  - **Example**: column "customer_ssn" → PII.Sensitive at 0.85 confidence

- **`statistical_classifier.py`**: Statistics-based classification
  - Uses column statistics for classification hints
  - **Cardinality-based**:
    - Low cardinality (< 50 distinct) → DataQuality.Categorical at 0.80
    - High uniqueness (> 95%) → DataQuality.Unique at 0.85
  - **Null percentage-based**:
    - High nulls (> 20%) → DataQuality.Nullable at 0.80
  - **No upstream adjustment** (statistics are reliable)
  - **Example**: Column with 15 distinct values → DataQuality.Categorical at 0.80

- **`context_classifier.py`**: Entity type and relationship context-based
  - Uses entity classification from AlignerAgent
  - Uses relationships from ArchitectAgent
  - **Entity type classification**:
    - Entity type "fact" → DataDomain.Fact at (alignment_confidence * 0.95)
    - Entity type "dimension" → DataDomain.Dimension at (alignment_confidence * 0.95)
  - **Relationship classification**:
    - Column in relationship → DataDomain.JoinKey at (relationship.confidence * 0.92)
  - **Upstream factors tracked**: `entity_type`, `alignment_confidence`, `relationship.confidence`
  - **Example**: Column "customer_id" in FK relationship → DataDomain.JoinKey at 0.80 (from relationship confidence 0.87)

- **`merger.py`**: Classification merging and deduplication
  - Deduplicates classifications from multiple sources
  - Keeps highest confidence when duplicate tags found
  - Enforces mutual exclusivity rules:
    - If both PII.Sensitive and PII.NonSensitive: keep Sensitive (higher priority)
    - If multiple DataDomain tags: keep highest confidence
  - Merges upstream_factors when combining same classification from multiple sources
  - Filters out classifications below minimum confidence threshold

#### Confidence Module (`confidence/`)

- **`scorer.py`**: Multi-factor confidence calculation
  - Adjusts base classification confidence based on upstream quality
  - **Algorithm**:
    ```python
    adjusted_confidence = base_confidence
    
    # Semantic type confidence penalty
    if semantic_type_confidence < 0.7:
        penalty = (0.7 - semantic_type_confidence) * 0.3
        adjusted_confidence *= (1.0 - penalty)
    
    # Alignment confidence penalty
    if alignment_confidence < 0.6:
        penalty = (0.6 - alignment_confidence) * 0.25
        adjusted_confidence *= (1.0 - penalty)
    
    # Clamp to [0.0, 1.0]
    adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
    ```
  - Records all upstream factors that influenced adjustment
  - Provides transparent confidence breakdown for audit

## Input/Output Contracts

### Input

**Function Signature:**
```python
async def enrich_schema(schema: Dict[str, Any]) -> Dict[str, Any]
```

**Parameters:**
- `schema` (Dict): Output from ArchitectAgent containing:
  - `entities`: List of SchemaEntity with columns
  - `relationships`: List of Relationship objects
  - `metadata_summary`: Schema summary statistics

**Dependencies on Upstream Outputs:**
- **ProfilerAgent** (via AlignerAgent):
  - `semantic_type`: For semantic type classification
  - `semantic_type_confidence`: For confidence adjustment
- **AlignerAgent**:
  - `canonical_name`, `synonyms`, `raw_names`: For name pattern matching
  - `alignment_confidence`: For confidence adjustment
  - `entity_type`: For context classification
- **ArchitectAgent**:
  - `relationships`: For JoinKey classification
  - `relationship.confidence`: For confidence scoring
  - All column statistics: For statistical classification

### Output

**Return Type:** `Dict[str, Any]` (enriched schema)

**Enriched Schema Structure:**
```python
{
  "entities": [
    {
      # All ArchitectAgent fields preserved...
      "entity_id": "entity_1",
      "canonical_name": "Customers",
      "table_name": "customers",
      "primary_key": {...},
      "columns": [...],
      "entity_type": "dimension",
      "alignment_confidence": 0.94,
      
      # NEW: Entity-level classifications
      "classifications": [
        {
          "tag": "DataDomain.Dimension",
          "confidence": 0.89,
          "source": "entity_type",
          "upstream_factors": {
            "entity_type": "dimension",
            "alignment_confidence": 0.94
          }
        }
      ]
    }
  ],
  "relationships": [
    # All ArchitectAgent relationships preserved unchanged
  ],
  "metadata_summary": {
    # All ArchitectAgent metadata preserved...
  },
  
  # NEW: Classification summary
  "classification_summary": {
    "total_entities": 5,
    "total_columns": 47,
    "entities_with_classifications": 5,
    "columns_with_classifications": 43,
    "classification_distribution": {
      "PII.Sensitive": 8,
      "PII.NonSensitive": 12,
      "Finance.Revenue": 6,
      "Temporal.Transaction": 10,
      "DataDomain.Fact": 2,
      "DataDomain.Dimension": 3,
      "DataDomain.JoinKey": 8,
      "Contact.Email": 5,
      "Identity.UUID": 6,
      "DataQuality.Nullable": 15,
      "DataQuality.Categorical": 9
    },
    "avg_classification_confidence": 0.84,
    "high_confidence_classifications": 38,  # > 0.8
    "medium_confidence_classifications": 5,  # 0.6-0.8
    "low_confidence_classifications": 0     # < 0.6 (filtered out)
  }
}
```

**Column-Level Classifications Example:**
```python
{
  "name": "customer_email",
  "data_type": "VARCHAR",
  "data_type_display": "VARCHAR(320)",
  "semantic_type": "email",
  "semantic_type_confidence": 0.95,
  "alignment_confidence": 0.88,
  "nullable": true,
  # ... other fields ...
  
  # NEW: Column classifications
  "classifications": [
    {
      "tag": "PII.Sensitive",
      "confidence": 0.93,
      "source": "semantic_type",
      "upstream_factors": {
        "semantic_type": "email",
        "semantic_type_confidence": 0.95,
        "alignment_confidence": 0.88
      }
    },
    {
      "tag": "Contact.Email",
      "confidence": 0.93,
      "source": "semantic_type",
      "upstream_factors": {
        "semantic_type": "email",
        "semantic_type_confidence": 0.95
      }
    },
    {
      "tag": "DataDomain.JoinKey",
      "confidence": 0.80,
      "source": "relationship",
      "upstream_factors": {
        "relationship_confidence": 0.87,
        "relationship_id": "rel_3"
      }
    },
    {
      "tag": "DataQuality.Nullable",
      "confidence": 0.80,
      "source": "statistical",
      "upstream_factors": {
        "null_percentage": 23.5
      }
    }
  ]
}
```

### Output Characteristics

**New Fields Added by TaggerAgent:**

**Entity Level:**
1. **`classifications`**: Array of Classification objects
   - Governance tags (DataDomain.Fact, DataDomain.Dimension)
   - Context-based classifications

**Column Level:**
1. **`classifications`**: Array of Classification objects
   - PII classifications (Sensitive/NonSensitive)
   - Finance classifications (Revenue/Cost/Reporting)
   - Temporal classifications
   - Contact classifications
   - Identity classifications
   - Data Quality classifications
   - Domain classifications (JoinKey)

**Schema Level:**
1. **`classification_summary`**: Comprehensive statistics
   - Coverage metrics
   - Classification distribution
   - Confidence statistics

**Propagated Unchanged:**
- All ProfilerAgent outputs (semantic types, confidence, statistics)
- All AlignerAgent outputs (alignment confidence, synonyms, entity types)
- All ArchitectAgent outputs (relationships, OpenMetadata types, confidence breakdowns)

**Classification Confidence Meanings:**

| Confidence Range | Interpretation | Source Type |
|------------------|----------------|-------------|
| **0.9 - 1.0** | Very high confidence | Semantic type with high upstream confidence |
| **0.8 - 0.9** | High confidence | Semantic type or strong pattern match |
| **0.7 - 0.8** | Good confidence | Pattern match or relationship-based |
| **0.6 - 0.7** | Medium confidence | Weak pattern match or statistical |
| **< 0.6** | Low confidence (filtered out) | Unreliable signal |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TAGGER_MIN_CONFIDENCE` | `0.6` | Minimum classification confidence threshold |
| `TAGGER_SEMANTIC_CONFIDENCE_THRESHOLD` | `0.7` | Threshold for semantic type confidence penalty |
| `TAGGER_ALIGNMENT_CONFIDENCE_THRESHOLD` | `0.6` | Threshold for alignment confidence penalty |
| `TAGGER_ENABLE_SEMANTIC_CLASSIFIER` | `true` | Enable semantic type classifier |
| `TAGGER_ENABLE_NAME_PATTERN_CLASSIFIER` | `true` | Enable name pattern classifier |
| `TAGGER_ENABLE_STATISTICAL_CLASSIFIER` | `true` | Enable statistical classifier |
| `TAGGER_ENABLE_CONTEXT_CLASSIFIER` | `true` | Enable context classifier |

### Classifier Weights

**Confidence Adjustment Weights:**
- Semantic type confidence penalty weight: 0.3
- Alignment confidence penalty weight: 0.25

**Base Confidence by Source:**
- Semantic type match: 0.92
- Exact name pattern match: 0.90
- Partial name pattern match: 0.70-0.85
- Statistical classification: 0.80-0.85
- Relationship-based: relationship.confidence * 0.92
- Entity type-based: alignment_confidence * 0.95

## Algorithms

### Classification Workflow

1. **Entity Classification**:
   ```python
   for entity in schema['entities']:
       entity_classifications = []
       
       # Context classifier: entity type
       if entity['entity_type'] == 'fact':
           entity_classifications.append(Classification(
               tag="DataDomain.Fact",
               confidence=entity['alignment_confidence'] * 0.95,
               source="entity_type",
               upstream_factors={"entity_type": "fact", "alignment_confidence": entity['alignment_confidence']}
           ))
       
       # Merge and deduplicate
       entity['classifications'] = merge_classifications(entity_classifications)
   ```

2. **Column Classification**:
   ```python
   for entity in schema['entities']:
       for column in entity['columns']:
           column_classifications = []
           
           # Semantic type classifier
           if column['semantic_type'] in SEMANTIC_TYPE_MAP:
               base_confidence = 0.92
               adjusted_confidence = adjust_for_semantic_confidence(base_confidence, column['semantic_type_confidence'])
               adjusted_confidence = adjust_for_alignment_confidence(adjusted_confidence, column['alignment_confidence'])
               
               for tag in SEMANTIC_TYPE_MAP[column['semantic_type']]:
                   column_classifications.append(Classification(
                       tag=tag,
                       confidence=adjusted_confidence,
                       source="semantic_type",
                       upstream_factors={
                           "semantic_type": column['semantic_type'],
                           "semantic_type_confidence": column['semantic_type_confidence'],
                           "alignment_confidence": column['alignment_confidence']
                       }
                   ))
           
           # Name pattern classifier
           for tag, keywords in CLASSIFICATION_KEYWORDS.items():
               if matches_pattern(column['name'], keywords):
                   match_quality = calculate_match_quality(column['name'], keywords)
                   base_confidence = 0.70 + (match_quality * 0.20)  # 0.70-0.90
                   adjusted_confidence = adjust_for_alignment_confidence(base_confidence, column['alignment_confidence'])
                   
                   column_classifications.append(Classification(
                       tag=tag,
                       confidence=adjusted_confidence,
                       source="name_pattern",
                       upstream_factors={"alignment_confidence": column['alignment_confidence']}
                   ))
           
           # Statistical classifier
           if column['null_percentage'] > 20:
               column_classifications.append(Classification(
                   tag="DataQuality.Nullable",
                   confidence=0.80,
                   source="statistical",
                   upstream_factors={"null_percentage": column['null_percentage']}
               ))
           
           if column['distinct_count'] < 50:
               column_classifications.append(Classification(
                   tag="DataQuality.Categorical",
                   confidence=0.80,
                   source="statistical",
                   upstream_factors={"distinct_count": column['distinct_count']}
               ))
           
           # Context classifier: relationship-based
           for rel in get_relationships_for_column(column, schema['relationships']):
               column_classifications.append(Classification(
                   tag="DataDomain.JoinKey",
                   confidence=rel['confidence'] * 0.92,
                   source="relationship",
                   upstream_factors={
                       "relationship_confidence": rel['confidence'],
                       "relationship_id": rel['relationship_id']
                   }
               ))
           
           # Merge, deduplicate, enforce mutual exclusivity
           column['classifications'] = merge_classifications(column_classifications)
   ```

3. **Confidence Adjustment Algorithm**:
   ```python
   def adjust_for_semantic_confidence(base_confidence, semantic_type_confidence):
       if semantic_type_confidence < 0.7:
           penalty = (0.7 - semantic_type_confidence) * 0.3
           return base_confidence * (1.0 - penalty)
       return base_confidence
   
   def adjust_for_alignment_confidence(base_confidence, alignment_confidence):
       if alignment_confidence < 0.6:
           penalty = (0.6 - alignment_confidence) * 0.25
           return base_confidence * (1.0 - penalty)
       return base_confidence
   ```

4. **Mutual Exclusivity Enforcement**:
   ```python
   def enforce_mutual_exclusivity(classifications):
       # PII: Keep only Sensitive or NonSensitive (prefer Sensitive)
       pii_tags = [c for c in classifications if c.tag.startswith("PII.")]
       if len(pii_tags) > 1:
           if any(c.tag == "PII.Sensitive" for c in pii_tags):
               classifications = [c for c in classifications if c.tag != "PII.NonSensitive"]
           else:
               # Keep highest confidence
               highest_pii = max(pii_tags, key=lambda c: c.confidence)
               classifications = [c for c in classifications if not c.tag.startswith("PII.") or c.tag == highest_pii.tag]
       
       # DataDomain at entity level: Keep only one
       domain_tags = [c for c in classifications if c.tag.startswith("DataDomain.") and c.tag in ["DataDomain.Fact", "DataDomain.Dimension"]]
       if len(domain_tags) > 1:
           highest_domain = max(domain_tags, key=lambda c: c.confidence)
           classifications = [c for c in classifications if c.tag != highest_domain.tag or c == highest_domain]
       
       return classifications
   ```

5. **Classification Summary Generation**:
   ```python
   def generate_summary(schema):
       summary = {
           "total_entities": len(schema['entities']),
           "total_columns": sum(len(e['columns']) for e in schema['entities']),
           "entities_with_classifications": 0,
           "columns_with_classifications": 0,
           "classification_distribution": {},
           "avg_classification_confidence": 0.0,
           "high_confidence_classifications": 0,
           "medium_confidence_classifications": 0,
           "low_confidence_classifications": 0
       }
       
       all_confidences = []
       
       for entity in schema['entities']:
           if entity.get('classifications'):
               summary['entities_with_classifications'] += 1
           
           for classification in entity.get('classifications', []):
               summary['classification_distribution'][classification['tag']] = \
                   summary['classification_distribution'].get(classification['tag'], 0) + 1
               all_confidences.append(classification['confidence'])
               
               if classification['confidence'] > 0.8:
                   summary['high_confidence_classifications'] += 1
               elif classification['confidence'] >= 0.6:
                   summary['medium_confidence_classifications'] += 1
               else:
                   summary['low_confidence_classifications'] += 1
           
           for column in entity['columns']:
               if column.get('classifications'):
                   summary['columns_with_classifications'] += 1
               
               for classification in column.get('classifications', []):
                   summary['classification_distribution'][classification['tag']] = \
                       summary['classification_distribution'].get(classification['tag'], 0) + 1
                   all_confidences.append(classification['confidence'])
                   
                   if classification['confidence'] > 0.8:
                       summary['high_confidence_classifications'] += 1
                   elif classification['confidence'] >= 0.6:
                       summary['medium_confidence_classifications'] += 1
                   else:
                       summary['low_confidence_classifications'] += 1
       
       summary['avg_classification_confidence'] = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
       
       return summary
   ```

## Dependencies

### Required Python Packages
- `pydantic`: Data models
- `rapidfuzz`: Fuzzy string matching (optional)

### Upstream Dependencies
- **ProfilerAgent** (via AlignerAgent):
  - Semantic types and confidence scores
- **AlignerAgent**:
  - Alignment confidence
  - Canonical names, synonyms
  - Entity types
- **ArchitectAgent**:
  - Relationships with confidence
  - All column statistics
  - Entity structure

### Downstream Consumers
- **GlossaryAgent**: Uses TaggerAgent classifications
  - Classifications for domain formation (Finance.*, PII.*)
  - Classification confidence for term quality
  - PII tags for privacy-aware glossary generation

- **ContextAgent**: Uses TaggerAgent classifications
  - Classifications for governance-aware descriptions
  - Confidence scores for confidence language

- **Data Pipeline**: Uses TaggerAgent classifications
  - PII tags for data masking
  - Finance tags for financial reporting
  - Temporal tags for time-series analysis

## Error Handling

### Common Failure Scenarios

1. **No Classifications Detected**: Valid scenario, returns empty classifications array
2. **Low Upstream Confidence**: Reduces classification confidence appropriately
3. **Conflicting Classifications**: Mutual exclusivity rules resolve conflicts
4. **Missing Upstream Data**: Gracefully skips classifiers that depend on missing data

### Logging
- INFO: Classification start/completion, classification counts per entity/column
- WARNING: Low confidence classifications, mutual exclusivity conflicts resolved
- ERROR: Classifier failures, configuration errors

## Future Extensions

### Planned Enhancements
1. **Custom Classification Taxonomies**: Support organization-specific classification hierarchies
2. **LLM-Based Classification**: Use LLM for complex classification decisions
3. **User Feedback Loop**: Learn from user corrections to improve classification accuracy
4. **Classification Rules Engine**: Allow custom classification rules beyond keywords
5. **Classification Confidence Calibration**: Calibrate confidence scores based on validation data
6. **Privacy Risk Scoring**: Calculate privacy risk scores based on PII classifications
7. **Compliance Mapping**: Map classifications to compliance frameworks (GDPR, CCPA, HIPAA)

### Extension Points
- Add new classification category: Extend `definitions.py`
- Add new classifier: Implement `BaseClassifier` in `classifiers/`
- Customize confidence adjustment: Modify `scorer.py`
- Add classification keywords: Extend `keywords.py`

