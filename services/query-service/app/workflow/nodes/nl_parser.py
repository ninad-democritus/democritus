"""Natural language parsing node"""
import json
import logging
from typing import Dict, Any

from ...services.ollama_client import get_llm
from ...services.redis_publisher import publish_progress
from ...prompts.nl_parser import NL_PARSER_SYSTEM_PROMPT, create_nl_parser_prompt
from ...models import QueryIntent
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def parse_natural_language(state: WorkflowState) -> Dict[str, Any]:
    """
    Parse natural language query into structured intent.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with parsed_intent
    """
    query_id = state["query_id"]
    nl_query = state["natural_language_query"]
    context = state.get("context")
    
    logger.info(f"[{query_id}] ===== NL PARSER START =====")
    logger.info(f"[{query_id}] NL query: {nl_query}")
    
    try:
        # Publish progress
        await publish_progress(
            query_id=query_id,
            stage="parsing_query",
            message="Parsing natural language query..."
        )
        
        # Get LLM with JSON mode for structured output
        llm = get_llm(model=None, temperature=0.1, json_mode=True)
        
        # Create prompt
        user_prompt = create_nl_parser_prompt(nl_query, context)
        
        logger.info(f"[{query_id}] Calling LLM for NL parsing...")
        
        # Invoke LLM
        messages = [
            {"role": "system", "content": NL_PARSER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"[{query_id}] LLM response ({len(response_text)} chars): {response_text[:200]}...")
        
        # Parse JSON response
        try:
            intent_data = json.loads(response_text)
            intent = QueryIntent(**intent_data)
            
            logger.info(f"[{query_id}] Parsed intent:")
            logger.info(f"[{query_id}]   - Metrics: {intent.metrics}")
            logger.info(f"[{query_id}]   - Dimensions: {intent.dimensions}")
            logger.info(f"[{query_id}]   - Filters: {intent.filters}")
            logger.info(f"[{query_id}]   - Aggregations: {intent.aggregations}")
            logger.info(f"[{query_id}] ===== NL PARSER END (SUCCESS) =====")
            
            return {
                "parsed_intent": intent
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[{query_id}] Failed to parse LLM JSON response: {e}")
            logger.error(f"[{query_id}] Response was: {response_text}")
            
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                json_match = response_text.split("```json")[1].split("```")[0]
                intent_data = json.loads(json_match.strip())
                intent = QueryIntent(**intent_data)
                logger.info(f"[{query_id}] Extracted intent from markdown: {intent}")
                logger.info(f"[{query_id}] ===== NL PARSER END (SUCCESS) =====")
                return {"parsed_intent": intent}
            else:
                raise
                
    except Exception as e:
        logger.exception(f"[{query_id}] ===== NL PARSER END (ERROR) =====")
        logger.exception(f"[{query_id}] NL parsing failed: {e}")
        return {
            "error": f"Failed to parse natural language query: {str(e)}",
            "error_code": "NL_PARSING_ERROR"
        }

