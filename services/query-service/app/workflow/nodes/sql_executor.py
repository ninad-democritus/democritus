"""SQL execution node"""
import logging
from typing import Dict, Any

from ...services.trino_client import get_trino_client
from ...services.redis_publisher import publish_progress
from ...config import settings
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def execute_sql(state: WorkflowState) -> Dict[str, Any]:
    """
    Execute SQL query via Trino.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with query_results
    """
    query_id = state["query_id"]
    sql = state["generated_sql"]
    
    logger.info(f"[{query_id}] ===== SQL EXECUTOR START =====")
    logger.info(f"[{query_id}] SQL to execute ({len(sql)} chars): {sql[:500]}")
    
    try:
        # Publish progress
        await publish_progress(
            query_id=query_id,
            stage="executing_query",
            message="Executing query against data warehouse..."
        )
        
        # Get Trino client
        trino_client = get_trino_client()
        
        logger.info(f"[{query_id}] Trino client config: catalog={settings.TRINO_CATALOG}, schema={settings.TRINO_SCHEMA}")
        logger.info(f"[{query_id}] Executing query against Trino...")
        
        # Execute query with row limit
        results = trino_client.execute_query(
            sql=sql,
            limit=settings.MAX_RESULT_ROWS
        )
        
        logger.info(f"[{query_id}] Query returned {len(results)} rows")
        
        if len(results) > 0:
            # Log first row structure
            first_row = results[0]
            logger.info(f"[{query_id}] Result columns: {list(first_row.keys())}")
            logger.info(f"[{query_id}] First row sample: {first_row}")
        
        if len(results) == 0:
            logger.warning(f"[{query_id}] Query returned no results")
            return {
                "error": "Query executed successfully but returned no results. Try adjusting your query or filters.",
                "error_code": "NO_DATA_FOUND",
                "query_results": []
            }
        
        if len(results) >= settings.MAX_RESULT_ROWS:
            logger.warning(f"[{query_id}] Results truncated to {settings.MAX_RESULT_ROWS} rows")
        
        logger.info(f"[{query_id}] ===== SQL EXECUTOR END (SUCCESS) =====")
        
        return {
            "query_results": results
        }
        
    except Exception as e:
        logger.error(f"[{query_id}] ===== SQL EXECUTOR END (ERROR) =====")
        logger.exception(f"[{query_id}] SQL execution failed: {e}")
        
        error_msg = str(e)
        
        # Log full error details
        logger.error(f"[{query_id}] Error type: {type(e).__name__}")
        logger.error(f"[{query_id}] Error message: {error_msg}")
        
        # Parse common Trino errors
        if "Table" in error_msg and "does not exist" in error_msg:
            return {
                "error": f"Table not found: {error_msg}",
                "error_code": "TABLE_NOT_FOUND"
            }
        elif "Column" in error_msg and "cannot be resolved" in error_msg:
            return {
                "error": f"Column not found: {error_msg}",
                "error_code": "COLUMN_NOT_FOUND"
            }
        else:
            return {
                "error": f"Query execution failed: {error_msg}",
                "error_code": "SQL_EXECUTION_ERROR"
            }

