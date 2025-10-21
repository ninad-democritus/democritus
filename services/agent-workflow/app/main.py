import os
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from celery import Celery
from uuid import uuid4

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("agent_workflow", broker=redis_url, backend=redis_url)

# Configure Celery for Celery 6.0+ compatibility
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
)


class StartWorkflowRequest(BaseModel):
  fileId: str
  fileName: str
  sourceType: str


class StartJobWorkflowRequest(BaseModel):
  jobId: str
  sourceType: str


class StartWorkflowResponse(BaseModel):
  workflowId: str
  websocketUrl: str


class UnifiedSchema(BaseModel):
  entities: list
  relationships: list
  businessTags: dict


app = FastAPI(title="Agent Workflow Service")


@app.post("/v1/workflows/start", response_model=StartWorkflowResponse, status_code=202)
def start_workflow(payload: StartWorkflowRequest):
  task = run_workflow.delay(payload.model_dump())
  ws_url = f"/ws/v1/workflows/status/{task.id}"
  return StartWorkflowResponse(workflowId=task.id, websocketUrl=ws_url)


@app.post("/v1/workflows/start-job", response_model=StartWorkflowResponse, status_code=202)
def start_job_workflow(payload: StartJobWorkflowRequest):
  task = run_job_workflow.delay(payload.model_dump())
  ws_url = f"/ws/v1/workflows/status/{task.id}"
  return StartWorkflowResponse(workflowId=task.id, websocketUrl=ws_url)


@app.get("/v1/workflows/status/{workflow_id}")
def get_workflow_status(workflow_id: str):
  """Get the current status of a workflow (HTTP endpoint for polling)"""
  try:
    # Get task result from Celery
    task = celery_app.AsyncResult(workflow_id)
    
    if task.state == 'PENDING':
      return {
        "status": "pending",
        "message": "Workflow is queued and waiting to start",
        "workflowId": workflow_id
      }
    elif task.state == 'STARTED':
      return {
        "status": "processing", 
        "message": "AI agents are processing your data...",
        "workflowId": workflow_id
      }
    elif task.state == 'SUCCESS':
      result = task.result
      if result and 'status' in result:
        if result['status'] == 'PENDING_VALIDATION':
          return {
            "status": "completed",
            "message": "Schema generation completed. Ready for approval.",
            "schema": result.get('schema', {}),
            "workflowId": workflow_id
          }
        else:
          return {
            "status": "completed",
            "message": "Workflow completed successfully",
            "schema": result.get('schema', {}),
            "workflowId": workflow_id
          }
      else:
        return {
          "status": "completed",
          "message": "Workflow completed",
          "workflowId": workflow_id
        }
    elif task.state == 'FAILURE':
      return {
        "status": "failed",
        "message": f"Workflow failed: {str(task.info)}",
        "workflowId": workflow_id
      }
    else:
      return {
        "status": "unknown",
        "message": f"Unknown workflow state: {task.state}",
        "workflowId": workflow_id
      }
      
  except Exception as e:
    logger.error(f"Error getting workflow status for {workflow_id}: {e}")
    raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")


@app.websocket("/ws/v1/workflows/status/{workflow_id}")
async def ws_status(websocket: WebSocket, workflow_id: str):
  import asyncio
  import redis.asyncio as aioredis
  import json
  
  await websocket.accept()
  redis_client = None
  
  try:
    # Connect to Redis for pub/sub
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = aioredis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    
    # Subscribe to workflow status channel
    channel = f"workflow_status_{workflow_id}"
    await pubsub.subscribe(channel)
    
    # Send initial connection confirmation
    await websocket.send_json({
      "status": "CONNECTED",
      "message": f"Connected to workflow {workflow_id}",
      "timestamp": "2024-01-01T00:00:00Z"
    })
    
    # Listen for Redis messages
    async for message in pubsub.listen():
      if message["type"] == "message":
        try:
          # Parse and forward the message
          status_data = json.loads(message["data"])
          await websocket.send_json(status_data)
        except Exception as e:
          logger.error(f"Error processing Redis message: {e}")
          
  except WebSocketDisconnect:
    logger.info(f"WebSocket disconnected for workflow {workflow_id}")
  except Exception as e:
    logger.error(f"WebSocket error for workflow {workflow_id}: {e}")
  finally:
    if redis_client:
      await redis_client.close()


class ValidateRequest(BaseModel):
  action: str
  schema: dict


@app.post("/v1/workflows/{workflow_id}/validate")
def validate_schema(workflow_id: str, payload: ValidateRequest):
  if payload.action != "APPROVE":
    raise HTTPException(status_code=400, detail="Only APPROVE supported in MVP1")
  # In MVP1 we mock persistence and pipeline trigger
  return JSONResponse({
    "status": "SUCCESS",
    "message": "Schema approved. Persisting to metadata store."
  })


@celery_app.task(name="run_workflow")
def run_workflow(context: dict):
  # Placeholder Celery task for MVP1
  return {"status": "PENDING_VALIDATION", "schema": {"entities": [], "relationships": []}}


@celery_app.task(name="run_job_workflow")
def run_job_workflow(context: dict):
  # Real agentic workflow execution
  from .workflow import SyncAgentWorkflow
  
  job_id = context.get("jobId")
  # Generate workflow ID from Celery task ID
  workflow_id = run_job_workflow.request.id
  
  try:
    workflow = SyncAgentWorkflow()
    result = workflow.run_job_workflow(job_id, workflow_id)
    return result
  except Exception as e:
    logger.exception(f"Job workflow failed for job {job_id}")
    return {"status": "ERROR", "error": str(e)}


