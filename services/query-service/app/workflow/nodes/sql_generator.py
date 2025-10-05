"""SQL generation node"""
import logging
from typing import Dict, Any

from ...services.ollama_client import get_llm
from ...services.redis_publisher import publish_progress
from ...prompts.sql_generator import (
    SQL_GENERATOR_SYSTEM_PROMPT,
    create_sql_generation_prompt
)
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def generate_sql(state: WorkflowState) -> Dict[str, Any]:
    """
    Generate SQL from parsed intent and metadata.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with generated_sql
    """
    query_id = state["query_id"]
    intent = state["parsed_intent"]
    metadata = state["metadata"]
    retry_count = state.get("retry_count", 0)
    validation_result = state.get("validation_result")
    
    logger.info(f"[{query_id}] ===== SQL GENERATOR START =====")
    logger.info(f"[{query_id}] Retry count: {retry_count}")
    logger.info(f"[{query_id}] Received {len(metadata) if metadata else 0} metadata entries")
    
    try:
        # Publish progress
        if retry_count > 0:
            await publish_progress(
                query_id=query_id,
                stage="retrying_sql",
                message=f"SQL validation failed. Retrying with corrections... (attempt {retry_count + 1})"
            )
        else:
            await publish_progress(
                query_id=query_id,
                stage="generating_sql",
                message="Generating SQL query..."
            )
        
        # Validate we have metadata
        if not metadata or len(metadata) == 0:
            logger.error(f"[{query_id}] NO METADATA available for SQL generation!")
            return {
                "error": "No table metadata available for SQL generation",
                "error_code": "NO_METADATA"
            }
        
        # Log metadata details
        logger.info(f"[{query_id}] Metadata for SQL generation:")
        for idx, table in enumerate(metadata):
            logger.info(f"[{query_id}]   Table {idx+1}: {table.schema_name}.{table.table_name} with {len(table.columns)} columns")
        
        # Get LLM with JSON mode to ensure clean output
        llm = get_llm(model=None, temperature=0.3, json_mode=True)
        
        # Build retry info if this is a retry
        retry_info = None
        if retry_count > 0 and validation_result:
            retry_info = {
                "errors": validation_result.errors,
                "suggestions": validation_result.suggestions
            }
            logger.info(f"[{query_id}] Retry info: {retry_info}")
        
        # Create prompt
        user_prompt = create_sql_generation_prompt(
            intent=intent.dict(),
            metadata_list=metadata,
            retry_info=retry_info
        )
        
        logger.info(f"[{query_id}] User prompt length: {len(user_prompt)} chars")
        logger.info(f"[{query_id}] User prompt preview (first 500 chars):")
        logger.info(f"[{query_id}] {user_prompt[:500]}")
        
        # Invoke LLM
        messages = [
            {"role": "system", "content": SQL_GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info(f"[{query_id}] Calling LLM for SQL generation...")
        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"[{query_id}] LLM returned {len(response_text)} chars")
        
        # Parse JSON response
        try:
            import json
            response_json = json.loads(response_text)
            sql_query = response_json.get("sql", "").strip()
            
            if not sql_query:
                raise ValueError("No 'sql' field in JSON response")
                
            logger.info(f"[{query_id}] Extracted SQL from JSON: {sql_query[:200]}")
            
        except json.JSONDecodeError as e:
            logger.error(f"[{query_id}] Failed to parse JSON response: {e}")
            logger.error(f"[{query_id}] Response was: {response_text[:500]}")
            
            # Fallback: try to extract from markdown
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
                response_json = json.loads(json_text)
                sql_query = response_json.get("sql", "").strip()
                logger.info(f"[{query_id}] Extracted SQL from markdown JSON")
            else:
                raise ValueError(f"LLM did not return valid JSON: {response_text[:200]}")
        
        # Remove trailing semicolon if present
        if sql_query.endswith(";"):
            sql_query = sql_query[:-1].strip()
        
        # Log the cleaned SQL (limit to 500 chars for safety)
        logger.info(f"[{query_id}] Final SQL length: {len(sql_query)} chars")
        if len(sql_query) > 1000:
            logger.warning(f"[{query_id}] SQL is suspiciously long ({len(sql_query)} chars)!")
            logger.info(f"[{query_id}] SQL preview: {sql_query[:500]}...")
        else:
            logger.info(f"[{query_id}] Generated SQL: {sql_query}")
        
        logger.info(f"[{query_id}] ===== SQL GENERATOR END (SUCCESS) =====")
        
        return {
            "generated_sql": sql_query
        }
        
    except Exception as e:
        logger.exception(f"[{query_id}] ===== SQL GENERATOR END (ERROR) =====")
        logger.exception(f"[{query_id}] SQL generation failed: {e}")
        return {
            "error": f"Failed to generate SQL: {str(e)}",
            "error_code": "SQL_GENERATION_ERROR"
        }

