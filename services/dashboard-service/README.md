# Dashboard Management Service

FastAPI-based service for managing dashboards with static and dynamic data support.

## Features

- **CRUD Operations**: Create, read, update, delete dashboards
- **Static Dashboards**: Save data snapshots with chart configurations
- **Dynamic Dashboards**: Store SQL queries and fetch live data on load
- **Access Control**: Private (owner only) or Public (all users) visibility
- **Query Service Integration**: Uses Core API for SQL validation, execution, and chart data binding

## API Endpoints

### Dashboard Operations

- `POST /api/v1/dashboards` - Create new dashboard
- `GET /api/v1/dashboards?owner_id={id}` - List user's dashboards
- `GET /api/v1/dashboards/{id}?owner_id={id}` - Get dashboard (hydrated if dynamic)
- `PUT /api/v1/dashboards/{id}?owner_id={id}` - Update dashboard
- `DELETE /api/v1/dashboards/{id}?owner_id={id}` - Delete dashboard

### Health Check

- `GET /health` - Service health status

## Environment Variables

```bash
DB_HOST=postgresql
DB_PORT=5432
DB_USER=openmetadata_user
DB_PASSWORD=openmetadata_password
DB_NAME=openmetadata_db
DB_SCHEMA=dashboards_db
QUERY_SERVICE_URL=http://query-service:8000
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
LOG_LEVEL=INFO
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn app.main:app --reload

# Access Swagger docs
# http://localhost:8000/docs
```

## Docker

```bash
# Build
docker build -t dashboard-service .

# Run
docker run -p 8000:8000 \
  -e DB_HOST=postgresql \
  -e QUERY_SERVICE_URL=http://query-service:8000 \
  dashboard-service
```

## Architecture

- **Database**: PostgreSQL (dashboards_db schema)
- **Framework**: FastAPI + SQLAlchemy
- **Dependencies**: Query Service Core API
- **No direct access to**: OpenMetadata, Trino (via Query Service only)

