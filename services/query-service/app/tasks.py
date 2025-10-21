"""Celery tasks for async query processing"""
import logging
from typing import Optional, Dict, Any
from celery import Celery

from .config import settings

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "query_service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.QUERY_TIMEOUT,
    task_soft_time_limit=settings.QUERY_TIMEOUT - 30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    broker_connection_retry_on_startup=True,  # Celery 6.0+ compatibility
)


@celery_app.task(
    name="process_query_task",
    bind=True,
    max_retries=0  # Don't retry failed queries
)
def process_query_task(
    self,
    query_id: str,
    natural_language_query: str,
    constraints: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Process query using LangGraph workflow.
    
    This task:
    1. Creates initial workflow state
    2. Runs the LangGraph workflow
    3. Publishes progress updates via Redis
    4. Returns final result or error
    
    Args:
        query_id: Unique query identifier
        natural_language_query: User's NL query
        constraints: Optional UI constraints
        context: Optional dashboard context
        
    Returns:
        Final result or error dict
    """
    try:
        logger.info(f"[{query_id}] Starting query processing")
        
        # Import here to avoid circular dependencies
        from .workflow.state import create_initial_state
        from .workflow.query_workflow import get_workflow
        from .services.redis_publisher import get_publisher
        import asyncio
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Get publisher for error handling
            publisher = loop.run_until_complete(get_publisher())
            
            # Create initial state
            initial_state = create_initial_state(
                query_id=query_id,
                natural_language_query=natural_language_query,
                constraints=constraints,
                context=context,
                max_retries=settings.MAX_RETRIES
            )
            
            logger.info(f"[{query_id}] Running LangGraph workflow")
            
            # Get and run workflow
            workflow = get_workflow()
            
            # Run workflow (convert sync task to async execution)
            final_state = loop.run_until_complete(workflow.ainvoke(initial_state))
            
            logger.info(f"[{query_id}] Workflow completed")
            
            # Check for errors in final state
            if final_state.get("error"):
                error_result = {
                    "success": False,
                    "error": final_state["error"],
                    "errorCode": final_state.get("error_code", "WORKFLOW_ERROR"),
                    "details": {}
                }
                
                # Publish error
                loop.run_until_complete(
                    publisher.publish_error(query_id=query_id, error=error_result)
                )
                
                logger.error(f"[{query_id}] Workflow failed: {final_state['error']}")
                return error_result
            
            # Success - result already published by echarts_generator node
            final_result = final_state.get("final_result")
            
            if not final_result:
                error_result = {
                    "success": False,
                    "error": "Workflow completed but no result generated",
                    "errorCode": "NO_RESULT",
                    "details": {}
                }
                
                loop.run_until_complete(
                    publisher.publish_error(query_id=query_id, error=error_result)
                )
                
                return error_result
            
            logger.info(f"[{query_id}] Query processing successful")
            return final_result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.exception(f"[{query_id}] Query processing failed with exception")
        
        # Publish error
        try:
            from .services.redis_publisher import get_publisher
            import asyncio
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                publisher = loop.run_until_complete(get_publisher())
                error_result = {
                    "success": False,
                    "error": str(e),
                    "errorCode": "PROCESSING_ERROR",
                    "details": {"exception": type(e).__name__}
                }
                
                loop.run_until_complete(
                    publisher.publish_error(query_id=query_id, error=error_result)
                )
            finally:
                loop.close()
                
        except Exception as pub_error:
            logger.error(f"[{query_id}] Failed to publish error: {pub_error}")
        
        return {
            "success": False,
            "error": str(e),
            "errorCode": "PROCESSING_ERROR"
        }

