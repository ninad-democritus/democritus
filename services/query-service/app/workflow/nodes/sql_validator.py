"""SQL validation node"""
import logging
from typing import Dict, Any

from ...services.redis_publisher import publish_progress
from ...utils.validators import validate_sql_against_schema
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def validate_sql(state: WorkflowState) -> Dict[str, Any]:
    """
    Validate generated SQL against schema.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with validation_result
    """
    query_id = state["query_id"]
    sql = state["generated_sql"]
    metadata = state["metadata"]
    
    logger.info(f"[{query_id}] Validating SQL")
    
    try:
        # Publish progress
        await publish_progress(
            query_id=query_id,
            stage="validating_sql",
            message="Validating SQL query..."
        )
        
        # Validate SQL
        validation_result = validate_sql_against_schema(sql, metadata)
        
        if validation_result.is_valid:
            logger.info(f"[{query_id}] SQL validation passed")
            
            # Publish SQL (for transparency)
            await publish_progress(
                query_id=query_id,
                stage="sql_generated",
                message="SQL query generated successfully",
                message_type="SQL_GENERATED",
                extra_data={"sqlQuery": sql}
            )
        else:
            logger.warning(f"[{query_id}] SQL validation failed: {validation_result.errors}")
            
        return {
            "validation_result": validation_result
        }
        
    except Exception as e:
        logger.exception(f"[{query_id}] SQL validation failed")
        return {
            "error": f"Failed to validate SQL: {str(e)}",
            "error_code": "SQL_VALIDATION_ERROR"
        }

