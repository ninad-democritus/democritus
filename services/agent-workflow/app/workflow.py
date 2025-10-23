from typing import Dict, Any, List
import logging
from dataclasses import dataclass
import asyncio
import redis
import json
import os
from datetime import datetime

from .agents.profiler import ProfilerAgent, FileProfile
from .agents.aligner import AlignerAgent, CanonicalEntity
from .agents.architect import ArchitectAgent
from .agents.tagger import TaggerAgent
from .agents.glossary import GlossaryAgent
from .agents.context import ContextAgent
try:
    from .observability import trace_workflow_step, observability
except ImportError:
    # Fallback for when observability is not available
    def trace_workflow_step(name, metadata=None):
        def decorator(func):
            return func
        return decorator
    
    class MockObservability:
        def log_workflow_metrics(self, *args, **kwargs): pass
    
    observability = MockObservability()

logger = logging.getLogger(__name__)

@dataclass
class WorkflowState:
    job_id: str
    workflow_id: str
    status: str
    current_step: str
    file_profiles: List[FileProfile] = None
    entities: List[CanonicalEntity] = None
    schema: Dict[str, Any] = None
    enriched_schema: Dict[str, Any] = None
    error_message: str = None

class AgentWorkflow:
    """
    LangGraph-style workflow orchestrator for the multi-agent schema generation pipeline.
    Coordinates Profiler -> Aligner -> Architect -> Tagger -> Glossary -> Context agents.
    """
    
    def __init__(self):
        self.profiler = ProfilerAgent()
        self.aligner = AlignerAgent()
        self.architect = ArchitectAgent()
        self.tagger = TaggerAgent()
        self.glossary = GlossaryAgent()
        self.context = ContextAgent(llm_service=self.glossary.llm_service)
        
        # Redis for WebSocket communication
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.redis_client = redis.from_url(redis_url)
        
    async def run_workflow(self, job_id: str, workflow_id: str) -> Dict[str, Any]:
        """Run the complete agentic workflow"""
        start_time = datetime.utcnow()
        
        state = WorkflowState(
            job_id=job_id,
            workflow_id=workflow_id,
            status="RECEIVED",
            current_step="initialization"
        )
        
        # Log workflow start
        observability.log_workflow_metrics(job_id, workflow_id, {
            "workflow_started": start_time.isoformat(),
            "job_id": job_id,
            "workflow_id": workflow_id
        })
        
        try:
            # Step 1: Profiler Agent
            await self._update_status(state, "PROFILING", "Profiler agent analyzing data sources")
            state = await self._run_profiler_step(state)
            
            # Step 2: Aligner Agent  
            await self._update_status(state, "ALIGNING", "Aligner agent identifying entities")
            state = await self._run_aligner_step(state)
            
            # Step 3: Architect Agent
            await self._update_status(state, "ARCHITECTING", "Architect agent designing schema structure")
            state = await self._run_architect_step(state)
            
            # Step 4: Tagger Agent
            await self._update_status(state, "TAGGING", "Tagger agent enriching with business context")
            state = await self._run_tagger_step(state)
            
            # Step 5: Glossary Agent
            await self._update_status(state, "GLOSSARY_BUILDING", "Glossary agent generating business glossary")
            state = await self._run_glossary_step(state)
            
            # Step 6: Context Agent
            await self._update_status(state, "CONTEXT_GENERATION", "Context agent generating business narratives")
            state = await self._run_context_step(state)
            
            # Step 7: Final validation
            await self._update_status(state, "PENDING_VALIDATION", "Schema with narratives ready for user review", 
                                    include_schema=True)
            state.status = "PENDING_VALIDATION"
            
            # Log workflow completion
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            final_metrics = {
                "workflow_completed": end_time.isoformat(),
                "duration_seconds": duration,
                "status": "PENDING_VALIDATION",
                "entities_generated": len(state.enriched_schema.get('entities', [])),
                "relationships_identified": len(state.enriched_schema.get('relationships', [])),
                "business_tags_applied": len(state.enriched_schema.get('classification_summary', {}).get('classification_distribution', {})),
                "glossaries_generated": len(state.enriched_schema.get('glossaries', [])),
                "glossary_terms": state.enriched_schema.get('glossary_summary', {}).get('total_terms', 0)
            }
            
            observability.log_workflow_metrics(job_id, workflow_id, final_metrics)
            
            return {
                "status": state.status,
                "schema": state.enriched_schema,
                "workflow_id": workflow_id,
                "metrics": final_metrics
            }
            
        except Exception as e:
            logger.exception(f"Workflow failed for job {job_id}")
            state.error_message = str(e)
            
            # Log workflow failure
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            observability.log_workflow_metrics(job_id, workflow_id, {
                "workflow_failed": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e),
                "failed_step": state.current_step
            })
            
            await self._update_status(state, "ERROR", f"Workflow failed: {str(e)}")
            raise
    
    @trace_workflow_step("profiler", {"component": "profiler_agent"})
    async def _run_profiler_step(self, state: WorkflowState) -> WorkflowState:
        """Execute the Profiler Agent step"""
        logger.info(f"Running Profiler Agent for job {state.job_id}")
        
        # Profile all files in the job
        file_profiles = self.profiler.profile_job_files(state.job_id)
        
        if not file_profiles:
            raise ValueError(f"No files found or failed to profile files for job {state.job_id}")
        
        state.file_profiles = file_profiles
        state.current_step = "profiling_complete"
        
        logger.info(f"Profiled {len(file_profiles)} files for job {state.job_id}")
        return state
    
    @trace_workflow_step("aligner", {"component": "aligner_agent"})
    async def _run_aligner_step(self, state: WorkflowState) -> WorkflowState:
        """Execute the Aligner Agent step"""
        logger.info(f"Running Aligner Agent for job {state.job_id}")
        
        if not state.file_profiles:
            raise ValueError("No file profiles available for entity alignment")
        
        # Identify entities from file profiles
        entities = self.aligner.identify_entities(state.file_profiles)
        
        if not entities:
            raise ValueError("No entities identified from the uploaded files")
        
        state.entities = entities
        state.current_step = "alignment_complete"
        
        logger.info(f"Identified {len(entities)} entities for job {state.job_id}")
        return state
    
    @trace_workflow_step("architect", {"component": "architect_agent"})
    async def _run_architect_step(self, state: WorkflowState) -> WorkflowState:
        """Execute the Architect Agent step"""
        logger.info(f"Running Architect Agent for job {state.job_id}")
        
        if not state.entities:
            raise ValueError("No entities available for schema architecture")
        
        # Design the relational schema
        schema = self.architect.design_schema(state.entities)
        
        state.schema = schema
        state.current_step = "architecture_complete"
        
        logger.info(f"Designed schema with {len(schema['entities'])} entities and {len(schema['relationships'])} relationships")
        return state
    
    @trace_workflow_step("tagger", {"component": "tagger_agent"})
    async def _run_tagger_step(self, state: WorkflowState) -> WorkflowState:
        """Execute the Tagger Agent step"""
        logger.info(f"Running Tagger Agent for job {state.job_id}")
        
        if not state.schema:
            raise ValueError("No schema available for business tagging")
        
        # Enrich schema with business context
        enriched_schema = self.tagger.enrich_schema(state.schema)
        
        state.enriched_schema = enriched_schema
        state.current_step = "tagging_complete"
        
        logger.info(f"Enriched schema with business tags for job {state.job_id}")
        return state
    
    @trace_workflow_step("glossary", {"component": "glossary_agent"})
    async def _run_glossary_step(self, state: WorkflowState) -> WorkflowState:
        """Execute the Glossary Agent step"""
        logger.info(f"Running Glossary Agent for job {state.job_id}")
        
        if not state.enriched_schema:
            raise ValueError("No enriched schema available for glossary generation")
        
        # Generate glossary from enriched schema
        glossary_output = self.glossary.generate_glossary(state.enriched_schema)
        
        # Add glossary to enriched schema (additive, preserves everything)
        state.enriched_schema['glossaries'] = glossary_output['glossaries']
        state.enriched_schema['glossary_summary'] = glossary_output['metadata_summary']
        state.current_step = "glossary_complete"
        
        logger.info(f"Generated {len(glossary_output['glossaries'])} glossaries with "
                   f"{glossary_output['metadata_summary']['total_terms']} terms for job {state.job_id}")
        return state
    
    @trace_workflow_step("context", {"component": "context_agent"})
    async def _run_context_step(self, state: WorkflowState) -> WorkflowState:
        """Execute the Context Agent step"""
        logger.info(f"Running Context Agent for job {state.job_id}")
        
        if not state.enriched_schema:
            raise ValueError("No enriched schema available for context generation")
        
        # Generate context narratives (returns minimal format by default)
        context_output = self.context.generate_context(state.enriched_schema)
        
        # Replace enriched schema with context-enriched minimal schema
        state.enriched_schema = context_output
        state.current_step = "context_complete"
        
        logger.info(f"Generated context for {len(context_output.get('entities', []))} entities, "
                   f"{context_output.get('summary', {}).get('totalColumns', 0)} columns for job {state.job_id}")
        return state
    
    async def _update_status(self, state: WorkflowState, status: str, message: str, 
                           include_schema: bool = False):
        """Update workflow status and send WebSocket notification"""
        state.status = status
        
        # Prepare WebSocket message
        ws_message = {
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "current_step": state.current_step
        }
        
        # Include schema in PENDING_VALIDATION status
        if include_schema and state.enriched_schema:
            ws_message["schema"] = state.enriched_schema
        
        # Send via Redis pub/sub for WebSocket delivery
        try:
            channel = f"workflow_status_{state.workflow_id}"
            self.redis_client.publish(channel, json.dumps(ws_message))
            logger.info(f"Published status update: {status} for workflow {state.workflow_id}")
        except Exception as e:
            logger.error(f"Failed to publish status update: {e}")

# Synchronous wrapper for Celery integration
class SyncAgentWorkflow:
    """Synchronous wrapper for the async workflow"""
    
    def __init__(self):
        self.workflow = AgentWorkflow()
    
    def run_job_workflow(self, job_id: str, workflow_id: str) -> Dict[str, Any]:
        """Run the workflow synchronously for Celery integration"""
        try:
            # Create new event loop for this task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the async workflow
            result = loop.run_until_complete(
                self.workflow.run_workflow(job_id, workflow_id)
            )
            
            return result
            
        finally:
            loop.close()
