# Data Cleanup Guide

This guide explains how to completely reset all data in the Democritus platform and start fresh with ingestion.

## What Gets Deleted

Running the cleanup scripts will delete **ALL** data:

- ✅ **Iceberg Catalog**: All tables and data files stored in MinIO
- ✅ **OpenMetadata**: All metadata, tables, schemas, and relationships
- ✅ **MinIO**: All buckets and files (`uploads`, `data`, `testupload`, `testdata`)
- ✅ **Redis Cache**: All cached data (agent-workflow and query-service)
- ✅ **PostgreSQL**: OpenMetadata database
- ✅ **Elasticsearch**: OpenMetadata search indices

## Running the Cleanup

### On Windows (PowerShell)

```powershell
# Navigate to the project root
cd C:\Code\democritus

# Run the PowerShell script
.\cleanup_all_data.ps1
```

### On Linux/Mac or Windows Git Bash

```bash
# Navigate to the project root
cd ~/democritus  # or your path

# Make script executable (first time only)
chmod +x cleanup_all_data.sh

# Run the script
./cleanup_all_data.sh
```

### What Happens

1. **Stop Services**: All Docker containers are stopped gracefully
2. **Delete Volumes**: Named volumes containing persistent data are removed:
   - `democritus_postgresql_data`
   - `democritus_elasticsearch_data`
   - `democritus_miniodata`
3. **Start Fresh**: All services restart with clean state
4. **Wait for Health**: Script waits 10 seconds and shows service status

## After Cleanup

### 1. Wait for Services to Be Ready (~2-3 minutes)

```bash
# Check service status
docker compose ps

# All services should show "healthy" or "running"
```

Key services to watch:
- `execute-migrate-all` should complete successfully
- `openmetadata-server` should be healthy
- `trino` should be healthy
- `minio` should be running

### 2. Verify Clean State

**Check MinIO Console:**
- URL: http://localhost:9001
- Login: `minioadmin` / `minioadmin`
- You should see buckets created but empty

**Check OpenMetadata:**
- URL: http://localhost:8585
- Login: `admin` / `admin`
- You should see no tables or data sources

**Check Trino:**
```bash
# Connect to Trino and verify no tables
docker exec -it democritus-trino-1 trino --catalog iceberg --schema default

# Inside Trino shell:
SHOW TABLES;  # Should return empty
```

### 3. Start Fresh Ingestion

#### Option A: Via UI
1. Go to http://localhost
2. Upload your CSV files
3. Trigger the ingestion workflow
4. Monitor progress

#### Option B: Via API
```bash
# Example: Ingest athlete_events.csv
curl -X POST "http://localhost/v1/pipelines/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "fresh_ingestion",
    "schema_data": {
      "source": {
        "type": "file",
        "bucket": "uploads",
        "file_name": "athlete_events.csv",
        "file_type": "csv"
      },
      "destination": {
        "catalog": "iceberg",
        "database": "default",
        "table": "Event"
      },
      "options": {
        "mode": "overwrite",
        "validate": true
      }
    }
  }'
```

## Troubleshooting

### Script Fails to Remove Volumes

If you see errors like `volume is in use`, make sure all containers are stopped:

```bash
docker compose down -v
docker volume prune
```

### Services Won't Start

Check logs for specific services:

```bash
# Check all logs
docker compose logs

# Check specific service
docker compose logs openmetadata-server
docker compose logs trino
```

### OpenMetadata Migration Fails

The `execute-migrate-all` container must complete successfully before OpenMetadata starts. Check its logs:

```bash
docker compose logs execute-migrate-all
```

### Containers Keep Restarting

This usually means a dependency isn't ready. Wait a bit longer or check:

```bash
# PostgreSQL should be healthy first
docker compose ps postgresql

# Elasticsearch should be healthy next
docker compose ps elasticsearch
```

## Manual Cleanup (If Script Fails)

If the automated script fails, you can manually clean up:

```bash
# Stop everything
docker compose down

# Remove volumes manually
docker volume rm democritus_postgresql_data
docker volume rm democritus_elasticsearch_data
docker volume rm democritus_miniodata

# Remove any orphaned volumes
docker volume prune

# Start fresh
docker compose up -d
```

## Preserving Ollama Models

The cleanup scripts preserve the Ollama models volume (`democritus_ollama`) to avoid re-downloading large model files (~2GB for llama3.2:3b).

If you want to clear models too (to force re-download), uncomment this line in the script:

```bash
# In .sh script
docker volume rm democritus_ollama

# In .ps1 script
docker volume rm democritus_ollama
```

## Selective Cleanup (Advanced)

If you only want to clear specific data:

### Clear Only MinIO Files
```bash
docker exec democritus-minio-1 mc alias set local http://localhost:9000 minioadmin minioadmin
docker exec democritus-minio-1 mc rm --recursive --force local/uploads/
docker exec democritus-minio-1 mc rm --recursive --force local/data/
```

### Clear Only Iceberg Tables
```bash
docker exec -it democritus-trino-1 trino --catalog iceberg --schema default --execute "DROP TABLE IF EXISTS table_name"
```

### Clear Only Redis
```bash
docker exec democritus-redis-1 redis-cli FLUSHALL
```

## See Also

- [README.md](README.md) - Main project documentation
- [docker-compose.yml](docker-compose.yml) - Service configuration
- [reingest_csv_files.sh](reingest_csv_files.sh) - Example ingestion script


