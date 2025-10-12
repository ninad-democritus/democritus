"""Main FastAPI application for Query Service"""
import os
import json
import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from .config import settings
from .models import (
    ChartGenerationRequest,
    ChartGenerationInitiated,
    HealthCheckResponse
)
from .tasks import celery_app, process_query_task
from .core_api.routes import router as core_api_router

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Natural Language to SQL and Chart Generation Service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Core API routes
app.include_router(core_api_router)


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns service health and dependency status.
    """
    dependencies = {}
    
    # Check Redis
    try:
        redis_client = await aioredis.from_url(settings.REDIS_URL, socket_timeout=5)
        await redis_client.ping()
        await redis_client.close()
        dependencies["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        dependencies["redis"] = "unhealthy"
    
    # Check Trino
    try:
        from .services.trino_client import get_trino_client
        trino_client = get_trino_client()
        if trino_client.test_connection():
            dependencies["trino"] = "healthy"
        else:
            dependencies["trino"] = "unhealthy"
    except Exception as e:
        logger.error(f"Trino health check failed: {e}")
        dependencies["trino"] = "unhealthy"
    
    # Overall status
    status = "healthy" if all(v == "healthy" for v in dependencies.values()) else "degraded"
    
    return HealthCheckResponse(
        status=status,
        service=settings.SERVICE_NAME,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        dependencies=dependencies
    )


@app.post(
    "/generate-chart",
    response_model=ChartGenerationInitiated,
    status_code=202
)
async def generate_chart(request: ChartGenerationRequest):
    """
    Generate chart from natural language query.
    
    Returns immediately with queryId and WebSocket URL for progress updates.
    
    Args:
        request: Chart generation request with NL query and optional constraints
        
    Returns:
        Query ID and WebSocket URL for progress updates
    """
    try:
        # Generate unique query ID
        query_id = str(uuid4())
        
        logger.info(f"Received chart generation request: {query_id}")
        logger.debug(f"Query: {request.naturalLanguageQuery}")
        
        # Submit task to Celery
        task = process_query_task.apply_async(
            args=[
                query_id,
                request.naturalLanguageQuery,
                request.constraints.dict() if request.constraints else None,
                request.context.dict() if request.context else None
            ],
            task_id=query_id
        )
        
        # Build WebSocket URL (nginx will handle the /api/v1/query-service/ prefix)
        ws_url = f"/ws/v1/query-service/status/{query_id}"
        
        logger.info(f"Query {query_id} submitted to worker")
        
        return ChartGenerationInitiated(
            queryId=query_id,
            websocketUrl=ws_url,
            status="initiated"
        )
        
    except Exception as e:
        logger.error(f"Failed to initiate query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate query: {str(e)}"
        )


@app.websocket("/ws/status/{query_id}")
async def websocket_status(websocket: WebSocket, query_id: str):
    """
    WebSocket endpoint for real-time query progress updates.
    
    Subscribes to Redis pub/sub channel for the query and forwards
    all messages to the WebSocket client.
    
    Args:
        websocket: WebSocket connection
        query_id: Query ID to monitor
    """
    await websocket.accept()
    redis_client: Optional[aioredis.Redis] = None
    
    try:
        # Connect to Redis
        redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        pubsub = redis_client.pubsub()
        
        # Subscribe to query status channel
        channel = f"query_status_{query_id}"
        await pubsub.subscribe(channel)
        
        logger.info(f"WebSocket connected for query {query_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "CONNECTED",
            "queryId": query_id,
            "message": f"Connected to query service",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        # Listen for Redis messages and forward to WebSocket
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # Parse and forward the message
                    status_data = json.loads(message["data"])
                    await websocket.send_json(status_data)
                    
                    # Close connection after completion or error
                    if status_data.get("type") in ["COMPLETED", "ERROR"]:
                        logger.info(f"Query {query_id} finished, closing WebSocket")
                        break
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Redis message: {e}")
                except Exception as e:
                    logger.error(f"Error forwarding message: {e}")
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for query {query_id}")
    except Exception as e:
        logger.error(f"WebSocket error for query {query_id}: {e}")
        try:
            await websocket.send_json({
                "type": "ERROR",
                "queryId": query_id,
                "error": {
                    "success": False,
                    "error": "WebSocket connection error",
                    "errorCode": "WEBSOCKET_ERROR",
                    "details": {"message": str(e)}
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        except:
            pass
    finally:
        # Cleanup
        if redis_client:
            try:
                await redis_client.close()
            except:
                pass


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "generate_chart": "/generate-chart",
            "websocket": "/ws/status/{query_id}"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=True
    )

