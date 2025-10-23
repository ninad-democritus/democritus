# ProfilerAgent Documentation

## Overview

The **ProfilerAgent** is the first agent in the workflow pipeline, responsible for discovering and profiling tabular files from job uploads. It performs column-level statistical analysis and semantic type detection to create comprehensive data profiles that serve as the foundation for all downstream agents.

### What It Does

1. **File Discovery**: Locates and retrieves all files associated with a job from MinIO storage
2. **Format Support**: Loads CSV and Excel files (extensible to Parquet, Avro, JSON)
3. **Data Profiling**: Analyzes each column to extract:
   - Physical data types (integer, float, string, datetime)
   - Semantic types (email, phone, UUID, SSN, credit card, etc.)
   - Statistical measures (null counts, distinct values, min/max/mean)
   - Sample values for downstream validation
   - Nullable predictions using heuristics
4. **Smart Sampling**: Handles large datasets by sampling up to 10,000 rows when datasets exceed threshold

### Why These Design Choices

- **Pluggable Architecture**: Modular design allows easy extension to new storage backends (S3, Azure Blob, GCS) and file formats
- **Dual Profiling Approach**: 
  - DataProfiler library for ML-based semantic type detection
  - Pandas for reliable sample values and numeric statistics
- **Semantic Type Detection**: Enables intelligent downstream decisions (email fields → PII classification, UUID fields → primary key candidates)
- **Nullable Prediction**: Multi-factor heuristics consider null presence, semantic types, naming patterns, and PK indicators
- **Complete Statistics**: Provides rich context for entity alignment, relationship detection, and classification
- **Backward Compatibility**: Outputs standard `FileProfile` format expected by all downstream agents

## Folder Structure

```
services/agent-workflow/app/agents/profiler/
├── __init__.py
├── agent.py                          # Main orchestrator coordinating all components
├── models.py                         # Data structures (FileProfile, ColumnProfile)
├── config.py                         # Configuration with environment variable support
├── storage/                          # Storage backend implementations
│   ├── __init__.py
│   ├── base.py                       # Abstract storage interface
│   └── minio_storage.py              # MinIO implementation (current)
├── loaders/                          # File format loaders
│   ├── __init__.py
│   ├── base.py                       # Abstract loader interface
│   ├── csv_loader.py                 # CSV file loader
│   └── excel_loader.py               # Excel file loader (xlsx, xls)
├── backends/                         # Profiling backend implementations
│   ├── __init__.py
│   ├── base.py                       # Abstract profiling interface
│   └── dataprofiler_backend.py       # DataProfiler library integration
└── stats/                            # Statistics extraction modules
    ├── __init__.py
    ├── nullable_predictor.py         # Heuristic-based nullable prediction
    └── stats_extractor.py            # Sample values and numeric stats extraction
```

### File Responsibilities

#### Core Files
- **`agent.py`**: Main orchestrator that coordinates the profiling workflow
  - Discovers files from storage
  - Selects appropriate loader based on file extension
  - Invokes profiling backend
  - Enriches profiles with statistics and nullable predictions
  - Returns list of `FileProfile` objects

- **`models.py`**: Defines data contracts
  - `FileProfile`: Container for file-level metadata and column profiles
  - `ColumnProfile`: Rich column metadata with semantic types, statistics, and sample values

- **`config.py`**: Centralized configuration management
  - Storage credentials (MinIO endpoint, access keys)
  - Profiling parameters (max rows, sample size)
  - Feature toggles

#### Storage Module (`storage/`)
- **`base.py`**: Abstract storage interface defining contract for file operations
  - `list_files(prefix)`: List files in storage
  - `download_file(file_path)`: Retrieve file as bytes
  - `get_file_size(file_path)`: Get file metadata
  
- **`minio_storage.py`**: MinIO implementation
  - Connects to MinIO using environment credentials
  - Lists files under `jobs/{job_id}/` prefix
  - Downloads files as BytesIO streams for loaders

#### Loaders Module (`loaders/`)
- **`base.py`**: Abstract loader interface
  - `load(file_bytes)`: Parse file bytes into pandas DataFrame
  - `supports_extension(ext)`: Check if loader handles file type

- **`csv_loader.py`**: CSV file parsing
  - Handles CSV with auto-detection of encoding and delimiters
  - Returns pandas DataFrame

- **`excel_loader.py`**: Excel file parsing
  - Supports .xlsx and .xls formats
  - Handles multi-sheet workbooks (currently processes first sheet)

#### Backends Module (`backends/`)
- **`base.py`**: Abstract profiling interface
  - `profile(df, file_name)`: Profile DataFrame and return structured output

- **`dataprofiler_backend.py`**: DataProfiler integration
  - Uses DataProfiler library for semantic type detection
  - Extracts ML-based semantic classifications (email, phone, UUID, etc.)
  - Provides confidence scores for semantic types
  - Implements smart sampling for large datasets

#### Stats Module (`stats/`)
- **`nullable_predictor.py`**: Predicts if columns should allow nulls
  - Multi-factor heuristics:
    - Null presence (has nulls → nullable)
    - Semantic type signals (email → nullable, UUID/SSN → not nullable)
    - Naming patterns (optional_*, preferred_* → nullable)
    - Primary key indicators (*_id, *_pk → not nullable)

- **`stats_extractor.py`**: Extracts sample values and numeric statistics
  - Sample values: Up to 5 non-null, distinct values
  - Numeric stats: min, max, mean for numeric columns
  - Essential for downstream validation and relationship detection

## Input/Output Contracts

### Input

**Function Signature:**
```python
async def profile_job_files(job_id: str) -> List[FileProfile]
```

**Parameters:**
- `job_id` (str): Unique identifier for the job whose files should be profiled

**Environment Dependencies:**
- MinIO storage configured with:
  - `MINIO_ENDPOINT`: MinIO server endpoint (default: `minio:9000`)
  - `MINIO_ACCESS_KEY`: Access key (default: `minioadmin`)
  - `MINIO_SECRET_KEY`: Secret key (default: `minioadmin`)
  - `MINIO_BUCKET`: Bucket name (default: `uploads`)
- Files must exist at path: `jobs/{job_id}/` in MinIO

### Output

**Return Type:** `List[FileProfile]`

**FileProfile Structure:**
```python
{
  "profile_method": "dataprofiler",          # Profiling backend used
  "file_name": "customers.csv",              # Original file name
  "file_id": "jobs/job123/customers.csv",    # Storage path
  "row_count": 10000,                        # Total rows in file
  "column_count": 15,                        # Total columns
  "file_size_bytes": 524288,                 # File size
  "columns": [                               # List of ColumnProfile objects
    {
      "name": "customer_email",
      "data_type": "string",                 # Physical type
      "semantic_type": "email",              # ML-detected semantic type
      "semantic_type_confidence": 0.95,      # Confidence score (0.0-1.0)
      "nullable": true,                      # Predicted nullable
      "null_count": 145,
      "total_count": 10000,
      "null_percentage": 1.45,
      "distinct_count": 9832,
      "sample_values": [                     # Up to 5 non-null samples
        "john@example.com",
        "mary@test.org",
        "bob@company.net"
      ],
      "min_value": null,                     # For numeric columns only
      "max_value": null,
      "mean_value": null
    },
    {
      "name": "order_total",
      "data_type": "float",
      "semantic_type": "currency.amount",
      "semantic_type_confidence": 0.88,
      "nullable": false,
      "null_count": 0,
      "total_count": 10000,
      "null_percentage": 0.0,
      "distinct_count": 7842,
      "sample_values": [123.45, 67.89, 450.00, 23.50, 890.25],
      "min_value": 5.00,
      "max_value": 9999.99,
      "mean_value": 245.67
    }
  ]
}
```

### Output Characteristics

**Confidence Scores:**
- `semantic_type_confidence`: From DataProfiler ML model (0.0-1.0)
  - 0.9-1.0: Very confident in semantic type
  - 0.7-0.9: High confidence
  - 0.5-0.7: Moderate confidence (may need review)
  - 0.0-0.5: Low confidence or "unknown" type

**Sample Values:**
- Non-null values only
- Up to 5 distinct values
- Used by ArchitectAgent for relationship detection
- Used by GlossaryAgent for context in LLM definitions

**Numeric Statistics:**
- Only populated for numeric columns (integer, float)
- Used by AlignerAgent for entity classification (fact vs dimension)
- Used by TaggerAgent for statistical classifications

**Nullable Predictions:**
- Based on heuristics, not always 100% accurate
- Considers actual null presence, semantic types, and naming patterns
- Can be overridden in downstream validation

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | `minio:9000` | MinIO server endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `uploads` | Storage bucket name |
| `DATAPROFILER_MAX_ROWS` | `10000` | Threshold for sampling trigger |
| `DATAPROFILER_SAMPLE_SIZE` | `10000` | Number of rows to sample |

### Profiling Behavior

- **Small Files** (≤ 10,000 rows): Profile entire dataset
- **Large Files** (> 10,000 rows): Random sample of 10,000 rows
- **Encoding**: Auto-detection with fallback to UTF-8
- **Missing Values**: Pandas interpretation (empty strings, "NA", "null", etc.)

## Dependencies

### Required Python Packages
- `minio`: MinIO client for object storage
- `pandas`: DataFrame operations and CSV/Excel loading
- `DataProfiler`: ML-based semantic type detection
- `openpyxl`: Excel file support (.xlsx)
- `xlrd`: Legacy Excel support (.xls)

### Downstream Consumers
- **AlignerAgent**: Uses all ProfilerAgent outputs
  - `semantic_type` for clustering boost
  - Statistics for entity classification
  - Sample values for validation
  - Confidence scores for quality signals

- **ArchitectAgent**: Uses ProfilerAgent outputs indirectly via AlignerAgent
  - Sample values for relationship validation
  - Data types for OpenMetadata type mapping
  - Semantic types for compatibility checking

- **TaggerAgent**: Uses semantic types and confidence scores
  - Maps semantic types to governance classifications
  - Adjusts confidence based on `semantic_type_confidence`

- **GlossaryAgent**: Uses sample values and semantic types
  - Sample values provide context for LLM definitions
  - Semantic types enrich glossary term metadata

## Error Handling

### Common Failure Scenarios

1. **No Files Found**: Raises exception if no files exist in `jobs/{job_id}/`
2. **File Download Failure**: Logs error and skips file
3. **Parsing Errors**: Logs error and skips corrupted file
4. **Profiling Failures**: Falls back to basic statistics if DataProfiler fails
5. **Memory Issues**: Smart sampling prevents OOM on large files

### Logging
- INFO: File discovery, profiling start/completion
- WARNING: Sampling triggered, parsing issues
- ERROR: Fatal failures (no files, storage unavailable)

## Future Extensions

### Planned Enhancements
1. **Additional Loaders**: Parquet, Avro, JSON support via pluggable interface
2. **Cloud Storage Backends**: AWS S3, Azure Blob, GCS implementations
3. **Advanced Sampling**: Stratified sampling for skewed distributions
4. **Embedding Cache**: Redis cache for semantic embeddings
5. **Incremental Profiling**: Update profiles for changed files only
6. **Multi-Sheet Excel**: Support for all sheets in workbooks
7. **Data Quality Metrics**: Additional quality signals (duplicates, outliers, patterns)

### Extension Points
- Add new loader: Implement `BaseLoader` interface in `loaders/`
- Add new storage: Implement `BaseStorage` interface in `storage/`
- Add new profiling backend: Implement `BaseProfiler` interface in `backends/`
- Customize nullable prediction: Modify `nullable_predictor.py` heuristics

