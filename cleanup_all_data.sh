#!/bin/bash

echo "🧹 Complete Data Reset - Democritus Platform"
echo "=============================================="
echo ""
echo "⚠️  WARNING: This will DELETE ALL data including:"
echo "   - All Iceberg tables and data"
echo "   - All OpenMetadata tables and metadata"
echo "   - All MinIO buckets and files"
echo "   - All Redis cache"
echo "   - PostgreSQL data (OpenMetadata database)"
echo "   - Elasticsearch indices"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1: Stopping all services..."
docker compose down

if [ $? -ne 0 ]; then
    echo "❌ Failed to stop services. Exiting."
    exit 1
fi

echo ""
echo "Step 2: Removing Docker volumes (this deletes all persistent data)..."

# Remove PostgreSQL data (OpenMetadata database)
echo "  Removing postgresql_data volume..."
docker volume rm democritus_postgresql_data 2>/dev/null || echo "    (Volume not found or already removed)"

# Remove Elasticsearch data (OpenMetadata search indices)
echo "  Removing elasticsearch_data volume..."
docker volume rm democritus_elasticsearch_data 2>/dev/null || echo "    (Volume not found or already removed)"

# Remove MinIO data (all files and Iceberg data)
echo "  Removing miniodata volume..."
docker volume rm democritus_miniodata 2>/dev/null || echo "    (Volume not found or already removed)"

# Remove Ollama models (optional - uncomment if you want to re-download models)
# echo "  Removing ollama volume..."
# docker volume rm democritus_ollama 2>/dev/null || echo "    (Volume not found or already removed)"

echo ""
echo "Step 3: Starting services fresh..."
docker compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start services. Please check docker compose logs."
    exit 1
fi

echo ""
echo "✅ Complete! All data has been cleared."
echo ""
echo "📊 Services are starting up with clean state..."
echo "   This will take approximately 2-3 minutes."
echo ""
echo "⏳ Waiting for critical services to be healthy..."
sleep 10

echo ""
echo "Service Status:"
echo "  OpenMetadata Migration: $(docker compose ps execute-migrate-all --format json 2>/dev/null | jq -r '.[0].State' 2>/dev/null || echo 'checking...')"
echo "  OpenMetadata Server: $(docker compose ps openmetadata-server --format json 2>/dev/null | jq -r '.[0].Health' 2>/dev/null || echo 'starting...')"
echo "  Trino: $(docker compose ps trino --format json 2>/dev/null | jq -r '.[0].Health' 2>/dev/null || echo 'starting...')"
echo "  MinIO: $(docker compose ps minio --format json 2>/dev/null | jq -r '.[0].State' 2>/dev/null || echo 'starting...')"

echo ""
echo "Next steps:"
echo "  1. Wait for all services to be healthy:"
echo "     docker compose ps"
echo ""
echo "  2. Access the UI at: http://localhost"
echo ""
echo "  3. Upload your CSV files and trigger ingestion workflow"
echo ""
echo "  4. Check service health:"
echo "     - Main UI: http://localhost"
echo "     - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "     - OpenMetadata UI: http://localhost:8585 (admin/admin)"
echo "     - Trino UI: http://localhost:8080"
echo ""


