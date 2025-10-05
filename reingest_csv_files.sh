#!/bin/bash

# Script to reingest CSV files with fixed parsing
# This will trigger the data pipeline to reload the CSV files with proper quote handling

echo "======================================"
echo "Re-ingesting CSV files with fixed parsing"
echo "======================================"

# Configuration
DATA_PIPELINE_URL="http://localhost/v1/pipelines/trigger"
FILE_UPLOAD_URL="http://localhost/v1/files/upload"

echo ""
echo "Step 1: Upload athlete_events.csv to MinIO..."
curl -X POST "$FILE_UPLOAD_URL" \
  -F "file=@test_data/athlete_events.csv" \
  -F "bucket=uploads"

echo ""
echo ""
echo "Step 2: Trigger pipeline for athlete_events.csv..."
curl -X POST "$DATA_PIPELINE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "athlete_events_reingest",
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

echo ""
echo ""
echo "======================================"
echo "Re-ingestion triggered!"
echo "======================================"
echo ""
echo "The CSV files are now being reprocessed with proper quote handling."
echo "Team names like 'Large boat, Central Naval Prep School \"Poros\"-1' "
echo "will now be stored correctly without CSV escape characters."
echo ""
echo "Monitor progress at: http://localhost/v1/pipelines/runs"
echo ""


