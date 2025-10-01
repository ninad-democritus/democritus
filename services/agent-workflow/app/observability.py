import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

try:
    from langsmith import Client, traceable
    from langsmith.run_trees import RunTree
    LANGSMITH_AVAILABLE = True
except ImportError:
    logger.warning("LangSmith not available - tracing disabled")
    LANGSMITH_AVAILABLE = False

class ObservabilityManager:
    """
    Manages LangSmith observability for the agentic workflow.
    Provides tracing, logging, and monitoring capabilities.
    """
    
    def __init__(self):
        self.enabled = self._setup_langsmith()
        self.session_name = f"democritus-workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
    def _setup_langsmith(self) -> bool:
        """Setup LangSmith client and configuration"""
        if not LANGSMITH_AVAILABLE:
            return False
            
        # Check for required environment variables
        api_key = os.getenv("LANGCHAIN_API_KEY")
        project = os.getenv("LANGCHAIN_PROJECT", "democritus-agents")
        endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        
        if not api_key:
            logger.warning("LANGCHAIN_API_KEY not set - LangSmith tracing disabled")
            return False
            
        try:
            # Set environment variables for langsmith
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = project
            os.environ["LANGCHAIN_ENDPOINT"] = endpoint
            
            # Initialize client
            self.client = Client(api_url=endpoint, api_key=api_key)
            
            # Test connection
            self.client.list_runs(limit=1)
            
            logger.info(f"LangSmith tracing enabled - Project: {project}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup LangSmith: {e}")
            return False
    
    def trace_agent(self, agent_name: str, inputs: Dict[str, Any] = None):
        """Decorator to trace agent execution"""
        def decorator(func):
            if not self.enabled:
                return func
                
            @wraps(func)
            @traceable(name=agent_name, metadata={"agent_type": agent_name})
            def wrapper(*args, **kwargs):
                try:
                    # Log start
                    logger.info(f"Starting {agent_name} with inputs: {inputs}")
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Log success
                    logger.info(f"Completed {agent_name} successfully")
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    logger.error(f"Error in {agent_name}: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    raise
                    
            return wrapper
        return decorator
    
    def trace_workflow_step(self, step_name: str, metadata: Dict[str, Any] = None):
        """Decorator to trace workflow steps"""
        def decorator(func):
            if not self.enabled:
                return func
                
            @wraps(func)
            @traceable(
                name=f"workflow_step_{step_name}",
                metadata={
                    "step_type": "workflow_step",
                    "step_name": step_name,
                    **(metadata or {})
                }
            )
            def wrapper(*args, **kwargs):
                try:
                    logger.info(f"Executing workflow step: {step_name}")
                    result = func(*args, **kwargs)
                    logger.info(f"Completed workflow step: {step_name}")
                    return result
                except Exception as e:
                    logger.error(f"Error in workflow step {step_name}: {str(e)}")
                    raise
                    
            return wrapper
        return decorator
    
    def log_agent_output(self, agent_name: str, output: Any, metrics: Dict[str, Any] = None):
        """Log agent output and metrics"""
        if not self.enabled:
            return
            
        try:
            # Create a run for logging
            with self.client.trace(
                name=f"{agent_name}_output",
                metadata={
                    "agent": agent_name,
                    "session": self.session_name,
                    **(metrics or {})
                }
            ) as run:
                run.end(outputs={"result": str(output)[:1000]})  # Truncate large outputs
                
        except Exception as e:
            logger.error(f"Failed to log output for {agent_name}: {e}")
    
    def log_workflow_metrics(self, job_id: str, workflow_id: str, metrics: Dict[str, Any]):
        """Log workflow-level metrics"""
        if not self.enabled:
            return
            
        try:
            with self.client.trace(
                name="workflow_metrics",
                metadata={
                    "job_id": job_id,
                    "workflow_id": workflow_id,
                    "session": self.session_name,
                    **metrics
                }
            ) as run:
                run.end(outputs={"metrics": metrics})
                
        except Exception as e:
            logger.error(f"Failed to log workflow metrics: {e}")
    
    def create_agent_span(self, agent_name: str, inputs: Dict[str, Any]) -> Optional[RunTree]:
        """Create a manual span for detailed agent tracing"""
        if not self.enabled:
            return None
            
        try:
            run = RunTree(
                name=agent_name,
                run_type="chain",
                inputs=inputs,
                session_name=self.session_name,
                extra={
                    "agent_type": agent_name,
                    "framework": "democritus",
                    "version": "1.0"
                }
            )
            run.post()
            return run
            
        except Exception as e:
            logger.error(f"Failed to create span for {agent_name}: {e}")
            return None
    
    def end_agent_span(self, span: RunTree, outputs: Dict[str, Any], error: Optional[str] = None):
        """End an agent span with outputs"""
        if not span:
            return
            
        try:
            if error:
                span.end(outputs=outputs, error=error)
            else:
                span.end(outputs=outputs)
            span.patch()
            
        except Exception as e:
            logger.error(f"Failed to end agent span: {e}")

# Global observability manager instance
observability = ObservabilityManager()

# Convenience decorators
def trace_agent(agent_name: str, inputs: Dict[str, Any] = None):
    """Convenience decorator for agent tracing"""
    return observability.trace_agent(agent_name, inputs)

def trace_workflow_step(step_name: str, metadata: Dict[str, Any] = None):
    """Convenience decorator for workflow step tracing"""
    return observability.trace_workflow_step(step_name, metadata)

