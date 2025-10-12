"""Main FastAPI application for Dashboard Service"""
import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from .config import settings
from .models import HealthCheckResponse
from .routes import dashboards

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Dashboard Management Service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(dashboards.router)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    dependencies = {}
    
    # Check database
    try:
        from .db.session import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        dependencies["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        dependencies["database"] = "unhealthy"
    
    # Check Query Service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.QUERY_SERVICE_URL}/health")
            if response.status_code == 200:
                dependencies["query_service"] = "healthy"
            else:
                dependencies["query_service"] = "unhealthy"
    except Exception as e:
        logger.error(f"Query Service health check failed: {e}")
        dependencies["query_service"] = "unhealthy"
    
    status = "healthy" if all(v == "healthy" for v in dependencies.values()) else "degraded"
    
    return HealthCheckResponse(
        status=status,
        service=settings.SERVICE_NAME,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        dependencies=dependencies
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=True
    )

