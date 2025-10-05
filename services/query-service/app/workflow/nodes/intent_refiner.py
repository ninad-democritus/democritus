"""Intent refinement node"""
import json
import logging
from typing import Dict, Any

from ...services.ollama_client import get_llm
from ...services.redis_publisher import publish_progress
from ...prompts.intent_refiner import (
    INTENT_REFINER_SYSTEM_PROMPT,
    create_intent_refinement_prompt
)
from ...models import QueryIntent
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def refine_intent(state: WorkflowState) -> Dict[str, Any]:
    """
    Refine query intent based on validation feedback.
    
    This node is called when SQL validation fails and we suspect the intent
    itself may be too narrow or incorrect. It uses an LLM to analyze:
    - Original user query
    - Current parsed intent
    - Validation errors
    - Available table schemas
    - Generated SQL that failed
    
    The LLM decides if the intent needs broadening/correction or if the
    issue is purely SQL syntax.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with refined parsed_intent (or unchanged if no refinement needed)
    """
    query_id = state["query_id"]
    original_query = state["natural_language_query"]
    current_intent = state["parsed_intent"]
    validation_result = state["validation_result"]
    metadata = state["metadata"]
    generated_sql = state["generated_sql"]
    refinement_count = state.get("intent_refinement_count", 0)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    logger.info(f"[{query_id}] ===== INTENT REFINER START =====")
    logger.info(f"[{query_id}] Attempt: {retry_count}/{max_retries + 1}")
    logger.info(f"[{query_id}] Current intent: {current_intent}")
    logger.info(f"[{query_id}] Validation errors: {validation_result.errors}")
    
    try:
        # Publish progress
        await publish_progress(
            query_id=query_id,
            stage="refining_intent",
            message=f"Analyzing query intent to resolve validation errors... (attempt {retry_count}/{max_retries + 1})"
        )
        
        # Preserve original intent on first refinement
        original_intent = state.get("original_parsed_intent")
        if original_intent is None:
            original_intent = current_intent
            logger.info(f"[{query_id}] Preserving original intent for context")
        
        # Get LLM with JSON mode
        llm = get_llm(model=None, temperature=0.2, json_mode=True)
        
        # Create refinement prompt
        user_prompt = create_intent_refinement_prompt(
            original_query=original_query,
            current_intent=current_intent.dict() if hasattr(current_intent, 'dict') else current_intent,
            validation_errors=validation_result.errors,
            available_tables=metadata,
            generated_sql=generated_sql
        )
        
        logger.info(f"[{query_id}] Refinement prompt length: {len(user_prompt)} chars")
        logger.debug(f"[{query_id}] Refinement prompt preview: {user_prompt[:300]}...")
        
        # Invoke LLM
        messages = [
            {"role": "system", "content": INTENT_REFINER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info(f"[{query_id}] Calling LLM for intent refinement...")
        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"[{query_id}] LLM response ({len(response_text)} chars)")
        logger.debug(f"[{query_id}] Response preview: {response_text[:300]}...")
        
        # Parse JSON response
        try:
            intent_data = json.loads(response_text)
            refined_intent = QueryIntent(**intent_data)
            
            # Check if intent actually changed
            current_dict = current_intent.dict() if hasattr(current_intent, 'dict') else current_intent
            refined_dict = refined_intent.dict()
            
            # Compare key fields
            intent_changed = (
                current_dict.get('metrics') != refined_dict.get('metrics') or
                current_dict.get('dimensions') != refined_dict.get('dimensions') or
                current_dict.get('filters') != refined_dict.get('filters') or
                current_dict.get('aggregations') != refined_dict.get('aggregations')
            )
            
            if intent_changed:
                logger.info(f"[{query_id}] ✓ Intent was REFINED:")
                logger.info(f"[{query_id}]   Original metrics: {current_dict.get('metrics')}")
                logger.info(f"[{query_id}]   Refined metrics:  {refined_dict.get('metrics')}")
                logger.info(f"[{query_id}]   Original dimensions: {current_dict.get('dimensions')}")
                logger.info(f"[{query_id}]   Refined dimensions:  {refined_dict.get('dimensions')}")
                logger.info(f"[{query_id}]   Original filters: {current_dict.get('filters')}")
                logger.info(f"[{query_id}]   Refined filters:  {refined_dict.get('filters')}")
                
                # Log reasoning if provided
                additional_context = refined_dict.get('additional_context', {})
                if additional_context.get('reasoning'):
                    logger.info(f"[{query_id}]   Reasoning: {additional_context['reasoning']}")
                
            else:
                logger.info(f"[{query_id}] ℹ Intent unchanged (issue is SQL syntax, not intent)")
            
            logger.info(f"[{query_id}] ===== INTENT REFINER END (SUCCESS) =====")
            
            # Increment retry_count here so it persists in state
            return {
                "parsed_intent": refined_intent,
                "original_parsed_intent": original_intent,
                "intent_refinement_count": refinement_count + 1,
                "retry_count": retry_count + 1
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[{query_id}] Failed to parse LLM JSON response: {e}")
            logger.error(f"[{query_id}] Response was: {response_text}")
            
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                json_match = response_text.split("```json")[1].split("```")[0]
                intent_data = json.loads(json_match.strip())
                refined_intent = QueryIntent(**intent_data)
                logger.info(f"[{query_id}] Extracted intent from markdown: {refined_intent}")
                logger.info(f"[{query_id}] ===== INTENT REFINER END (SUCCESS) =====")
                return {
                    "parsed_intent": refined_intent,
                    "original_parsed_intent": original_intent,
                    "intent_refinement_count": refinement_count + 1,
                    "retry_count": retry_count + 1
                }
            else:
                # If we can't parse, keep original intent and let normal retry logic handle it
                logger.warning(f"[{query_id}] Could not parse refined intent, keeping original")
                logger.info(f"[{query_id}] ===== INTENT REFINER END (FALLBACK) =====")
                return {
                    "intent_refinement_count": refinement_count + 1,
                    "retry_count": retry_count + 1
                }
                
    except Exception as e:
        logger.exception(f"[{query_id}] ===== INTENT REFINER END (ERROR) =====")
        logger.exception(f"[{query_id}] Intent refinement failed: {e}")
        
        # Don't fail the whole workflow, just keep original intent
        logger.info(f"[{query_id}] Continuing with original intent despite refinement error")
        return {
            "intent_refinement_count": refinement_count + 1,
            "retry_count": retry_count + 1
        }

