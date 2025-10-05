# PowerShell script for Windows
# Complete Data Reset - Democritus Platform

Write-Host "Complete Data Reset - Democritus Platform" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This will DELETE ALL data including:" -ForegroundColor Yellow
Write-Host "   - All Iceberg tables and data"
Write-Host "   - All OpenMetadata tables and metadata"
Write-Host "   - All MinIO buckets and files"
Write-Host "   - All Redis cache"
Write-Host "   - PostgreSQL data (OpenMetadata database)"
Write-Host "   - Elasticsearch indices"
Write-Host ""

$confirm = Read-Host "Are you sure you want to continue? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Step 1: Stopping all services..." -ForegroundColor Green
docker compose down

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to stop services. Exiting." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Removing Docker volumes (this deletes all persistent data)..." -ForegroundColor Green

# Remove PostgreSQL data (OpenMetadata database)
Write-Host "  Removing postgresql_data volume..."
docker volume rm democritus_postgresql_data 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "    (Volume not found or already removed)" -ForegroundColor Gray
}

# Remove Elasticsearch data (OpenMetadata search indices)
Write-Host "  Removing elasticsearch_data volume..."
docker volume rm democritus_elasticsearch_data 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "    (Volume not found or already removed)" -ForegroundColor Gray
}

# Remove MinIO data (all files and Iceberg data)
Write-Host "  Removing miniodata volume..."
docker volume rm democritus_miniodata 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "    (Volume not found or already removed)" -ForegroundColor Gray
}

# Remove Ollama models (optional - uncomment if you want to re-download models)
# Write-Host "  Removing ollama volume..."
# docker volume rm democritus_ollama 2>$null

Write-Host ""
Write-Host "Step 3: Starting services fresh..." -ForegroundColor Green
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start services. Please check docker compose logs." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Complete! All data has been cleared." -ForegroundColor Green
Write-Host ""
Write-Host "Services are starting up with clean state..." -ForegroundColor Cyan
Write-Host "   This will take approximately 2-3 minutes."
Write-Host ""
Write-Host "Waiting for critical services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Wait for all services to be healthy:"
Write-Host "     docker compose ps"
Write-Host ""
Write-Host "  2. Access the UI at: http://localhost"
Write-Host ""
Write-Host "  3. Upload your CSV files and trigger ingestion workflow"
Write-Host ""
Write-Host "  4. Check service health:"
Write-Host "     - Main UI: http://localhost"
Write-Host "     - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
Write-Host "     - OpenMetadata UI: http://localhost:8585 (admin/admin)"
Write-Host "     - Trino UI: http://localhost:8080"
Write-Host ""

