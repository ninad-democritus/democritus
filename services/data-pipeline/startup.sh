#!/bin/bash
set -e

echo "Starting data-pipeline service..."
echo "Starting FastAPI server with Spark pre-initialization..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
