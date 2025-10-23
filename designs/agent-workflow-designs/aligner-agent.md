# AlignerAgent Documentation

## Overview

The **AlignerAgent** is the second agent in the workflow pipeline, responsible for entity identification and canonical naming across multiple files. It uses ML-based semantic clustering to consolidate entities and columns that represent the same logical concept, even when they have different names across source files.

### What It Does

1. **Cross-File Entity Consolidation**: Identifies when multiple files contain the same entity (e.g., `customer_master.xlsx`, `customers.csv`, `client_data.xlsx` → single "Customers" entity)
2. **Semantic Clustering**: Uses sentence embeddings to group similar entity and column names based on semantic meaning
3. **Canonical Naming**: Selects best representative name for each entity/column cluster, optionally refined with LLM
4. **Column Statistics Merging**: Intelligently combines statistics when multiple source columns map to one canonical column
5. **Entity Classification**: Determines if each entity is a fact or dimension table using multi-factor scoring
6. **Primary Key Detection**: Identifies best PK candidates using uniqueness, null ratios, naming patterns, and semantic types

### Why These Design Choices

- **Embedding-Based Clustering**: Traditional pattern matching fails on semantically similar but syntactically different names ("cust_id" vs "customer_identifier"). Sentence embeddings capture semantic meaning.
- **ML Over Rules**: Rule-based approaches require constant maintenance and fail on edge cases. HDBSCAN/Agglomerative clustering adapts to data patterns.
- **Optional LLM Refinement**: For complex clusters with high variance, LLM can pick better canonical names than rule-based scoring. But optional for performance.
- **Synonyms Preservation**: Keeps all source names as synonyms for downstream matching (ArchitectAgent uses for FK detection, GlossaryAgent uses for user terminology)
- **Statistics Merging**: When consolidating columns from multiple files, naive merging would lose information. Conservative estimates maintain accuracy:
  - Distinct count: Take max (underestimate is safer than overestimate)
  - Total/null counts: Sum across sources
  - Numeric stats: Min/max across all, weighted mean
- **Confidence Scoring**: Cluster variance indicates alignment quality. Low variance = tight cluster = high confidence.
- **Backward Compatibility**: Outputs legacy `Entity` format for seamless integration with ArchitectAgent and TaggerAgent.

## Folder Structure

```
services/agent-workflow/app/agents/aligner/
├── __init__.py
├── agent.py                          # Main orchestrator with backward-compatible output
├── models.py                         # Rich data structures (CanonicalEntity, CanonicalColumn, clusters)
├── config.py                         # Configuration with environment variable support
├── preprocessing.py                  # Name normalization and tokenization
├── embeddings.py                     # Sentence embedding computation (sentence-transformers)
├── clustering.py                     # Similarity-based clustering (HDBSCAN/Agglomerative)
├── canonical_naming.py               # Canonical name selection (rules + optional LLM)
├── entity_classifier.py              # Fact/dimension classification with confidence
└── primary_key_detector.py           # Multi-factor PK detection with explanations
```

### File Responsibilities

#### Core Files
- **`agent.py`**: Main orchestrator coordinating the alignment workflow
  - Entry point: `identify_entities(file_profiles)`
  - Extracts entities and columns from file profiles
  - Orchestrates clustering and canonical naming
  - Merges statistics across consolidated columns
  - Classifies entity types (fact/dimension)
  - Detects primary key candidates
  - Converts to backward-compatible `Entity` format
  - Returns list of canonical entities

- **`models.py`**: Rich data structures for internal processing
  - `CanonicalEntity`: Primary output format with all metadata
  - `CanonicalColumn`: Column-level metadata with merged statistics
  - `EntityCluster`: Entity clustering information
  - `ColumnCluster`: Column clustering information
  - `PKCandidate`: Primary key candidate with confidence and explanation

#### Processing Modules

- **`preprocessing.py`**: Name normalization pipeline
  - Removes common prefixes (tbl_, dim_, fact_)
  - Splits camelCase and PascalCase
  - Replaces separators (_, -, .) with spaces
  - Lowercases and strips whitespace
  - Tokenizes for embedding
  - **Why**: Raw names like "TBL_CustomerMaster" → normalized "customer master" for better clustering

- **`embeddings.py`**: Semantic embedding computation
  - Uses `sentence-transformers` (`all-MiniLM-L6-v2` by default)
  - Computes 384-dimensional embeddings for entity/column names
  - Caching for repeated computations within session
  - **Why**: Transforms text into vector space where semantically similar names are close together

- **`clustering.py`**: Similarity-based clustering
  - HDBSCAN (default): Density-based, handles noise, finds natural clusters
  - Agglomerative (fallback): Hierarchical clustering with distance threshold
  - Cosine distance metric for embeddings
  - Configurable minimum cluster size (default: 2)
  - Computes cluster variance for confidence scoring
  - **Why**: Groups "customer", "customers", "client", "cust" into one cluster

- **`canonical_naming.py`**: Best name selection
  - **Rule-based scoring**:
    - Prefers readable names (spaces, proper formatting)
    - Penalizes very short or very long names
    - Prefers singular forms
    - Considers formatting quality
  - **Optional LLM refinement** (when cluster variance > threshold):
    - Batched LLM calls (8 clusters/call) to Ollama
    - Generates synonyms and alternate names
    - Falls back to rules if LLM fails
  - **Why**: "Customer" is better than "cust_tbl" or "CUSTOMER_MASTER_DATA_2024"

- **`entity_classifier.py`**: Fact/dimension classification
  - **Multi-factor scoring**:
    - Numeric column ratio (0.3 weight): Facts have many numeric measures
    - Measure keywords (0.3 weight): amount, total, count, quantity
    - Temporal fields (0.2 weight): Facts usually have timestamps
    - Foreign key count (0.2 weight): Facts typically have more FKs
  - Returns classification + confidence score
  - **Why**: Distinguishes transactional data (facts) from descriptive data (dimensions)

- **`primary_key_detector.py`**: PK candidate identification
  - **Multi-factor scoring**:
    - Uniqueness ratio (0.6 weight): distinct_count / total_count
    - Non-null ratio (0.2 weight): Must have few/no nulls
    - Name pattern match (0.1 weight): *_id, *_pk, id, pk regex patterns
    - Semantic type (0.1 weight): UUID, unique_identifier boost
  - Returns ranked candidates with confidence + human-readable explanation
  - **Example explanation**: "High uniqueness (98.5%) with 'id' suffix and UUID semantic type"
  - **Why**: Transparent PK selection helps ArchitectAgent choose best PK and informs relationship detection

#### Configuration
- **`config.py`**: Centralized configuration
  - Embedding model selection
  - Clustering algorithm and parameters
  - LLM configuration for canonical naming
  - Feature toggles (use_llm, min_cluster_size)

## Input/Output Contracts

### Input

**Function Signature:**
```python
async def identify_entities(file_profiles: List[FileProfile]) -> List[Entity]
```

**Parameters:**
- `file_profiles` (List[FileProfile]): Output from ProfilerAgent containing:
  - File metadata (name, path, row count)
  - Column profiles with semantic types, statistics, sample values
  - ProfilerAgent confidence scores

**Dependencies on ProfilerAgent Output:**
- `file_name`: Used as entity source file reference
- `columns[].name`: Entity and column names for clustering
- `columns[].semantic_type`: Used for PK detection and entity classification
- `columns[].semantic_type_confidence`: Propagated to output
- `columns[].data_type`: Used for entity classification (numeric detection)
- `columns[].distinct_count`, `total_count`, `null_count`: Used for PK detection and statistics merging
- `columns[].sample_values`: Propagated for downstream agents
- `columns[].min_value`, `max_value`, `mean_value`: Merged for numeric columns

### Output

**Return Type:** `List[Entity]` (backward-compatible format)

**Entity Structure:**
```python
{
  "name": "Customers",                       # Canonical entity name
  "original_names": [                        # All source names (synonyms)
    "customer_master",
    "customers",
    "client_data"
  ],
  "type": "dimension",                       # Entity classification
  "source_files": [                          # Source file references
    "customer_master.xlsx",
    "customers.csv",
    "client_data.xlsx"
  ],
  "columns": [                               # List of canonical columns
    {
      "name": "customer_id",                 # Canonical column name
      "original_names": [                    # All source column names
        "cust_id",
        "customer_identifier",
        "client_id"
      ],
      "data_type": "string",                 # Physical data type
      "semantic_type": "uuid",               # Semantic type from ProfilerAgent
      "semantic_type_confidence": 0.92,      # ProfilerAgent confidence (propagated)
      "nullable": false,                     # Nullable prediction
      "distinct_count": 9832,                # Merged: max across sources
      "total_count": 30000,                  # Merged: sum across sources
      "null_count": 0,                       # Merged: sum across sources
      "null_percentage": 0.0,                # Recalculated after merge
      "sample_values": [                     # Merged: deduplicated union (up to 5)
        "550e8400-e29b-41d4-a716-446655440000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "f47ac10b-58cc-4372-a567-0e02b2c3d479"
      ],
      "min_value": null,                     # Merged: min across all sources (numeric only)
      "max_value": null,                     # Merged: max across all sources (numeric only)
      "mean_value": null,                    # Merged: weighted mean (numeric only)
      "is_primary_key": true,                # Best PK candidate (from primary_key_candidates[0])
      "alignment_confidence": 0.94           # NEW: Clustering quality (1.0 - variance)
    },
    {
      "name": "email",
      "original_names": ["customer_email", "email_address", "contact_email"],
      "data_type": "string",
      "semantic_type": "email",
      "semantic_type_confidence": 0.95,
      "nullable": true,
      "distinct_count": 9645,
      "total_count": 30000,
      "null_count": 234,
      "null_percentage": 0.78,
      "sample_values": ["john@example.com", "mary@test.org", "bob@company.net"],
      "min_value": null,
      "max_value": null,
      "mean_value": null,
      "is_primary_key": false,
      "alignment_confidence": 0.88
    },
    {
      "name": "lifetime_value",
      "original_names": ["ltv", "customer_ltv", "total_lifetime_value"],
      "data_type": "float",
      "semantic_type": "currency.amount",
      "semantic_type_confidence": 0.87,
      "nullable": false,
      "distinct_count": 8732,
      "total_count": 30000,
      "null_count": 0,
      "null_percentage": 0.0,
      "sample_values": [1234.56, 567.89, 8900.12],
      "min_value": 0.0,                      # Merged: global min
      "max_value": 45000.00,                 # Merged: global max
      "mean_value": 2456.78,                 # Merged: weighted mean
      "is_primary_key": false,
      "alignment_confidence": 0.91
    }
  ],
  "primary_key_candidates": [                # NEW: Ranked PK candidates
    {
      "column_name": "customer_id",
      "confidence": 0.96,
      "uniqueness_ratio": 0.985,
      "non_null_ratio": 1.0,
      "has_id_pattern": true,
      "semantic_type_match": true,
      "explanation": "High uniqueness (98.5%) with 'id' suffix and UUID semantic type"
    },
    {
      "column_name": "email",
      "confidence": 0.72,
      "uniqueness_ratio": 0.961,
      "non_null_ratio": 0.992,
      "has_id_pattern": false,
      "semantic_type_match": false,
      "explanation": "High uniqueness (96.1%) with email semantic type, but 'email' pattern not typical for PKs"
    }
  ],
  "alignment_confidence": 0.94,              # NEW: Entity-level clustering confidence
  "type_classification_confidence": 0.83     # NEW: Fact/dimension confidence
}
```

### Output Characteristics

**New Fields Added by AlignerAgent:**
1. **`alignment_confidence`** (entity level): How tightly clustered the entity names are
2. **`alignment_confidence`** (column level): How tightly clustered the column names are
3. **`type_classification_confidence`**: Confidence in fact vs dimension classification
4. **`primary_key_candidates`**: Ranked list of PK candidates with detailed scoring

**Propagated from ProfilerAgent:**
- `semantic_type`, `semantic_type_confidence`
- `data_type`, `nullable`
- `sample_values`, `min_value`, `max_value`, `mean_value`

**Transformed/Merged:**
- `name`: Canonical name selected via clustering + naming algorithm
- `original_names`: All source names collected as synonyms
- `distinct_count`: Max across merged sources (conservative estimate)
- `total_count`, `null_count`: Sum across merged sources
- `null_percentage`: Recalculated after merge
- `is_primary_key`: Best PK candidate selected

**Confidence Score Meanings:**

| Confidence Range | Interpretation | Quality Signal |
|------------------|----------------|----------------|
| **0.9 - 1.0** | Very tight cluster, highly confident alignment | Auto-accept |
| **0.7 - 0.9** | Good cluster, confident alignment | Review spot-check |
| **0.5 - 0.7** | Moderate cluster, uncertain alignment | Flag for review |
| **0.3 - 0.5** | Loose cluster, low confidence | Likely needs manual adjustment |
| **0.0 - 0.3** | Very loose cluster, very uncertain | Manual intervention required |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALIGNER_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for embeddings |
| `ALIGNER_USE_LLM` | `true` | Enable LLM refinement for canonical naming |
| `ALIGNER_MIN_CLUSTER_SIZE` | `2` | Minimum cluster size for grouping |
| `ALIGNER_CLUSTERING_METHOD` | `hdbscan` | Clustering algorithm: `hdbscan` or `agglomerative` |
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama endpoint for LLM refinement |
| `OLLAMA_MODEL` | `llama3.2:3b` | LLM model for canonical naming |

### Clustering Behavior

**HDBSCAN (Default):**
- Density-based clustering
- Automatically determines number of clusters
- Handles noise (outliers assigned to cluster -1)
- Best for: Diverse datasets with varying cluster sizes

**Agglomerative (Fallback):**
- Hierarchical clustering
- Distance threshold determines clusters
- All points assigned to a cluster
- Best for: HDBSCAN not available or uniform cluster sizes

**LLM Refinement:**
- Only invoked for high-variance clusters (variance > 0.3)
- Batched calls (8 clusters per request) for efficiency
- 3 retries with exponential backoff
- Falls back to rule-based scoring on failure

## Dependencies

### Required Python Packages
- `sentence-transformers`: Embedding model (`all-MiniLM-L6-v2`)
- `scikit-learn`: Distance metrics, Agglomerative clustering
- `hdbscan`: Density-based clustering (optional, falls back to Agglomerative)
- `numpy`: Array operations and statistics
- `requests`: Ollama API calls (optional LLM refinement)

### Upstream Dependencies
- **ProfilerAgent**: All outputs consumed
  - Uses all column profiles
  - Uses all statistics
  - Uses semantic types and confidence scores

### Downstream Consumers
- **ArchitectAgent**: Uses all AlignerAgent outputs
  - `original_names` (synonyms) for FK pattern matching
  - `alignment_confidence` for quality signals
  - `primary_key_candidates` for PK selection
  - Statistics for cardinality analysis
  - Entity classification for relationship scoring

- **TaggerAgent**: Uses AlignerAgent outputs for classification
  - `alignment_confidence` adjusts classification confidence
  - `original_names` for name pattern matching
  - Entity classification for context classification
  - Semantic types for semantic classification

- **GlossaryAgent**: Uses AlignerAgent outputs for term extraction
  - `original_names` captured as user terminology
  - `alignment_confidence` for term quality filtering
  - Entity classification for domain formation
  - Primary key candidates for key identifier terms

## Algorithms

### Entity Clustering Algorithm

1. **Extraction Phase**:
   - Extract entity names from file profiles (file names minus extensions)
   - Extract column names from each file
   - Build entity → [columns] mapping

2. **Preprocessing Phase**:
   - Normalize entity names: `TBL_CustomerMaster` → `customer master`
   - Normalize column names: `cust_ID` → `cust id`
   - Store original names for synonyms

3. **Embedding Phase**:
   - Compute embeddings for all unique entity names
   - Compute embeddings for all unique column names
   - Cache embeddings for reuse

4. **Clustering Phase** (Entity Level):
   - Cluster entity embeddings using HDBSCAN or Agglomerative
   - Calculate cluster variance from pairwise distances
   - Group entities by cluster ID

5. **Canonical Naming Phase**:
   - For each entity cluster:
     - If variance > 0.3 and LLM enabled: Use LLM refinement
     - Else: Use rule-based scoring
     - Select best name as canonical
     - Keep all names as synonyms

6. **Column Clustering Phase** (Per Canonical Entity):
   - Collect all columns from entities in cluster
   - Cluster column embeddings
   - Calculate cluster variance
   - Select canonical column names

7. **Statistics Merging Phase**:
   - For each canonical column:
     - Sum total_count and null_count across sources
     - Take max distinct_count (conservative)
     - Recalculate null_percentage
     - Merge sample_values (deduplicate, limit 5)
     - For numeric: min(mins), max(maxs), weighted_mean

8. **Entity Classification Phase**:
   - Calculate numeric column ratio
   - Detect measure keywords
   - Check for temporal fields
   - Count potential foreign keys
   - Weighted scoring → fact or dimension

9. **Primary Key Detection Phase**:
   - For each column:
     - Calculate uniqueness ratio
     - Calculate non-null ratio
     - Check name patterns (regex)
     - Check semantic type
     - Weighted scoring
   - Sort by confidence
   - Generate explanations

10. **Output Conversion Phase**:
    - Convert CanonicalEntity → Entity (backward-compatible)
    - Set is_primary_key on best PK candidate
    - Populate all confidence fields

### Statistics Merging Formulas

**Distinct Count** (conservative estimate):
```python
merged_distinct = max(distinct_count_1, distinct_count_2, ...)
```

**Total Count** (sum):
```python
merged_total = sum(total_count_1, total_count_2, ...)
```

**Null Count** (sum):
```python
merged_null = sum(null_count_1, null_count_2, ...)
```

**Null Percentage** (recalculate):
```python
merged_null_pct = (merged_null / merged_total) * 100
```

**Sample Values** (deduplicated union, limit 5):
```python
merged_samples = list(set(samples_1 + samples_2 + ...))[:5]
```

**Numeric Statistics**:
```python
merged_min = min(min_1, min_2, ...)
merged_max = max(max_1, max_2, ...)
merged_mean = sum(mean_i * total_count_i) / merged_total
```

### Primary Key Scoring Formula

```python
# Calculate individual factors
uniqueness_score = distinct_count / total_count
non_null_score = (total_count - null_count) / total_count
name_pattern_score = 1.0 if matches_id_pattern else 0.0
semantic_type_score = 1.0 if semantic_type in ['uuid', 'unique_identifier'] else 0.0

# Weighted sum
confidence = (
    uniqueness_score * 0.6 +
    non_null_score * 0.2 +
    name_pattern_score * 0.1 +
    semantic_type_score * 0.1
)
```

## Error Handling

### Common Failure Scenarios

1. **No Entities Found**: Returns empty list if no files in input
2. **Embedding Model Load Failure**: Falls back to rule-based clustering (exact name matching)
3. **HDBSCAN Not Available**: Falls back to Agglomerative clustering
4. **LLM Service Unavailable**: Falls back to rule-based canonical naming
5. **Cluster Variance Too High**: Flags entity with low confidence score

### Logging
- INFO: Clustering start/completion, entity counts, canonical name selection
- WARNING: LLM fallback, high variance clusters, low confidence entities
- ERROR: Embedding model failures, clustering failures

## Future Extensions

### Planned Enhancements
1. **Embedding Cache**: Redis cache for computed embeddings across runs
2. **User Feedback Loop**: Learn from user corrections to improve clustering
3. **Hierarchical Entities**: Support parent-child entity relationships
4. **Advanced Merging**: HyperLogLog for precise distinct count estimation
5. **Multi-Language Support**: Multilingual embeddings for international datasets
6. **Temporal Alignment**: Track entity name changes over time (versioning)
7. **Confidence Calibration**: Calibrate confidence scores against user validation data

### Extension Points
- Add new clustering algorithm: Implement in `clustering.py`
- Customize canonical naming: Modify scoring in `canonical_naming.py`
- Add entity classification rules: Extend `entity_classifier.py`
- Customize PK detection: Modify weights in `primary_key_detector.py`

