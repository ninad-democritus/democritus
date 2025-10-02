from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import logging
import uuid
import json
import asyncio
import threading
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

from .workflows.pipeline_orchestrator import PipelineOrchestrator
from .utils.validators import PipelineRequestValidator, validate_run_id

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

class TriggerPipelineRequest(BaseModel):
    job_id: str
    schema_data: Dict[str, Any]


class TriggerPipelineResponse(BaseModel):
    pipelineRunId: str
    status: str
    airflow_dag_run_id: str


# Pre-initialize Spark session on startup
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Spark session on startup to avoid 504 timeouts"""
    logger.info("Pre-initializing services...")
    try:
        # Initialize SparkSessionManager to pre-download dependencies
        from .infrastructure.spark_session_manager import SparkSessionManager
        spark_manager = SparkSessionManager()
        spark_session = spark_manager.get_session()
        logger.info("✅ Spark session pre-initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to pre-initialize Spark session: {e}")
        # Don't fail startup, just log the error
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down services...")
    try:
        SparkSessionManager.stop_session()
        logger.info("✅ Services shut down successfully")
    except Exception as e:
        logger.error(f"❌ Error shutting down services: {e}")

app = FastAPI(title="Data Pipeline Service", lifespan=lifespan)

# CORS is handled by nginx proxy - no middleware needed here

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return {"status": "healthy", "service": "data-pipeline"}

@app.get("/v1/pipelines/stages")
async def get_pipeline_stages():
    """Get list of all pipeline stages"""
    return PipelineOrchestrator.get_pipeline_stages()

# Initialize the pipeline orchestrator lazily to avoid Spark initialization on startup
orchestrator = None

def get_orchestrator():
    """Get orchestrator instance, initializing it lazily"""
    global orchestrator
    if orchestrator is None:
        orchestrator = PipelineOrchestrator()
    return orchestrator

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, run_id: str = None):
        await websocket.accept()
        if run_id:
            if run_id not in self.active_connections:
                self.active_connections[run_id] = []
            self.active_connections[run_id].append(websocket)
        else:
            # Global connection
            if "global" not in self.active_connections:
                self.active_connections["global"] = []
            self.active_connections["global"].append(websocket)

    def disconnect(self, websocket: WebSocket, run_id: str = None):
        if run_id and run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
        else:
            # Remove from all connections
            for connections in self.active_connections.values():
                if websocket in connections:
                    connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            pass

    async def broadcast(self, message: str, run_id: str = None):
        connections_to_send = []
        
        if run_id and run_id in self.active_connections:
            connections_to_send = self.active_connections[run_id]
        else:
            # Broadcast to all connections
            for connections in self.active_connections.values():
                connections_to_send.extend(connections)
        
        disconnected = []
        for connection in connections_to_send:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


def execute_data_pipeline_sync(run_id: str, job_id: str, schema_data: Dict[str, Any]):
    """
    Execute the complete data pipeline workflow using the orchestrator (synchronous)
    """
    try:
        orchestrator = get_orchestrator()
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(orchestrator.execute_pipeline(run_id, job_id, schema_data, manager))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Pipeline execution failed for run {run_id}: {str(e)}")
        # The orchestrator handles its own error tracking

async def execute_data_pipeline(run_id: str, job_id: str, schema_data: Dict[str, Any]):
    """
    Execute the complete data pipeline workflow using the orchestrator (asynchronous wrapper)
    """
    # Run the synchronous function in a separate thread
    thread = threading.Thread(target=execute_data_pipeline_sync, args=(run_id, job_id, schema_data))
    thread.start()
    # Don't wait for the thread to complete

# All workflow logic moved to services and orchestrator

@app.post("/v1/pipelines/trigger", response_model=TriggerPipelineResponse, status_code=202)
async def trigger_pipeline(payload: TriggerPipelineRequest, background_tasks: BackgroundTasks):
    """
    Trigger the data ingestion pipeline workflow
    """
    logger.info(f"Triggering data ingestion pipeline for job {payload.job_id}")
    
    try:
        # Validate request payload
        is_valid, error_message = PipelineRequestValidator.validate_trigger_request(payload.dict())
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        # Generate run ID
        run_id = f"run_{payload.job_id}_{str(uuid.uuid4())[:8]}"
        
        # Start background task
        background_tasks.add_task(
            execute_data_pipeline,
            run_id,
            payload.job_id,
            payload.schema_data
        )
        
        logger.info(f"Successfully triggered pipeline run: {run_id}")
        
        response = TriggerPipelineResponse(
            pipelineRunId=run_id,
            status="TRIGGERED",
            airflow_dag_run_id=run_id  # Using run_id as the workflow identifier
        )
        
        logger.info(f"Returning 202 response for run: {run_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error triggering pipeline: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/v1/pipelines/status/{run_id}")
def get_pipeline_status(run_id: str):
    """
    Get the status of a pipeline run
    """
    # Validate run_id format
    if not validate_run_id(run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    
    # Get status from orchestrator
    run_info = orchestrator.get_pipeline_status(run_id)
    
    if not run_info:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline run {run_id} not found"
        )
    
    # Map internal status to external format
    status_mapping = {
        "running": "running", 
        "completed": "success",
        "failed": "failed"
    }
    
    return {
        "dag_run_id": run_id,
        "state": status_mapping.get(run_info["status"], "unknown"),
        "execution_date": run_info.get("started_at"),
        "start_date": run_info.get("started_at"),
        "end_date": run_info.get("completed_at") or run_info.get("failed_at"),
        "current_step": run_info.get("step", "unknown"),
        "job_id": run_info.get("job_id"),
        "error": run_info.get("error") if run_info["status"] == "failed" else None,
        "steps_completed": run_info.get("steps_completed", []),
        "steps_failed": run_info.get("steps_failed", [])
    }


@app.get("/v1/pipelines/runs")
def list_pipeline_runs(job_id: Optional[str] = None):
    """
    List all pipeline runs, optionally filtered by job ID
    """
    try:
        runs = orchestrator.list_pipeline_runs(job_id)
        return {
            "runs": runs,
            "total_count": len(runs),
            "filter_job_id": job_id
        }
    except Exception as e:
        logger.error(f"Failed to list pipeline runs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/pipelines/metrics")
def get_pipeline_metrics():
    """
    Get overall pipeline execution metrics
    """
    try:
        metrics = orchestrator.get_pipeline_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get pipeline metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/pipelines/cleanup")
def cleanup_old_runs(max_age_hours: int = 24):
    """
    Clean up old pipeline run data
    """
    try:
        cleaned_count = orchestrator.cleanup_old_runs(max_age_hours)
        return {
            "cleaned_runs": cleaned_count,
            "max_age_hours": max_age_hours
        }
    except Exception as e:
        logger.error(f"Failed to cleanup old runs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "data-pipeline"}


@app.websocket("/ws/v1/pipelines/status/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time pipeline status updates with run-specific URLs"""
    try:
        await websocket.accept()
        logger.info(f"WebSocket client connected to run_id: {run_id}")
        
        # Add to manager for this run_id
        if run_id not in manager.active_connections:
            manager.active_connections[run_id] = []
        manager.active_connections[run_id].append(websocket)
        
        # Send current status if available using the new format
        current_status = orchestrator.get_pipeline_status(run_id)
        if current_status:
            # Map the step to stage using the same logic as _send_status_update
            step = current_status.get("step", "unknown")
            stage_mapping = {
                "initializing": "data_processing",
                "file_discovery": "file_discovery",
                "file_validation": "file_validation", 
                "schema_validation": "schema_validation",
                "entity_mapping": "entity_mapping",
                "data_transformation": "data_transformation",
                "table_setup": "table_setup",
                "data_ingestion": "data_ingestion",
                "metadata_storage": "metadata_storage",
                "file_cleanup": "file_cleanup",
                "completed": "pipeline_complete",
                "failed": "pipeline_failed"
            }
            
            stage = stage_mapping.get(step, step)
            status = "STARTED" if current_status["status"] == "running" else current_status["status"].upper()
            
            status_message = {
                "type": "status_update",
                "run_id": run_id,
                "stage": stage,
                "status": status,
                "message": f"Pipeline {current_status['status']}",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "file_summary": current_status.get("file_summary", []),
                    "total_records": current_status.get("total_records", 0),
                    "total_files": current_status.get("total_files", 0),
                    "started_at": current_status.get("started_at"),
                    "completed_at": current_status.get("completed_at"),
                    "error": current_status.get("error"),
                    "nessie_branch": current_status.get("nessie_branch"),
                    "iceberg_success": current_status.get("iceberg_success", False)
                }
            }
            await websocket.send_text(json.dumps(status_message))
        else:
            # Send connection confirmation
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "run_id": run_id,
                "message": "Connected to pipeline status updates",
                "timestamp": datetime.now().isoformat()
            }))
            logger.info(f"✅ Sent connection confirmation to WebSocket client for run_id: {run_id}")
        
        # Keep connection alive and listen for disconnect
        while True:
            try:
                # Wait for any messages (mainly to detect disconnect)
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        # Remove from connections
        if run_id in manager.active_connections and websocket in manager.active_connections[run_id]:
            manager.active_connections[run_id].remove(websocket)
        logger.info(f"WebSocket client disconnected from run_id: {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.close()
        except:
            pass

@app.get("/")
def root():
    """Root endpoint with service information"""
    return {
        "service": "Data Pipeline Service",
        "version": "1.0.0",
        "description": "Modular data ingestion pipeline with OpenMetadata and Apache Iceberg",
        "endpoints": {
            "trigger_pipeline": "POST /v1/pipelines/trigger",
            "get_status": "GET /v1/pipelines/status/{run_id}",
            "list_runs": "GET /v1/pipelines/runs",
            "metrics": "GET /v1/pipelines/metrics",
            "websocket": "WS /ws/v1/pipelines/status/{run_id}",
            "health": "GET /health"
        }
    }


