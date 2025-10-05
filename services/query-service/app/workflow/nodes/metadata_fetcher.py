"""Metadata fetching node"""
import logging
from typing import Dict, Any, List

from ...services.openmetadata_client import get_openmetadata_client
from ...services.redis_publisher import publish_progress
from ...models import TableMetadata
from ..state import WorkflowState

logger = logging.getLogger(__name__)


async def fetch_metadata(state: WorkflowState) -> Dict[str, Any]:
    """
    Fetch ALL table metadata and relationships from OpenMetadata.
    
    This provides the LLM with complete schema information to generate accurate SQL.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with metadata (all tables and relationships)
    """
    query_id = state["query_id"]
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"[{query_id}] ===== METADATA FETCHER START =====")
    logger.info(f"[{query_id}] Fetching ALL tables from data-pipeline-service")
    logger.info(f"[{query_id}] Retry count: {retry_count}")
    
    try:
        # Publish progress
        await publish_progress(
            query_id=query_id,
            stage="fetching_metadata",
            message="Fetching all table metadata from OpenMetadata..."
        )
        
        # Get OpenMetadata client
        om_client = get_openmetadata_client()
        
        # Get ALL tables from data-pipeline-service
        logger.info(f"[{query_id}] Listing all tables from data-pipeline-service...")
        table_list = await om_client.list_tables(service="data-pipeline-service")
        
        logger.info(f"[{query_id}] Found {len(table_list)} table(s) in data-pipeline-service")
        
        if not table_list:
            logger.error(f"[{query_id}] NO TABLES FOUND in data-pipeline-service!")
            return {
                "error": "No tables found in data-pipeline-service. Please ensure tables are ingested first.",
                "error_code": "NO_METADATA_FOUND"
            }
        
        # Fetch detailed metadata for each table
        tables: List[TableMetadata] = []
        for idx, table_summary in enumerate(table_list):
            fqn = table_summary.get("_source", {}).get("fullyQualifiedName")
            if fqn:
                logger.info(f"[{query_id}] Fetching metadata for table {idx+1}/{len(table_list)}: {fqn}")
                table_meta = await om_client.get_table_metadata(fqn)
                if table_meta:
                    tables.append(table_meta)
                    logger.info(f"[{query_id}]   ✓ Got {len(table_meta.columns)} columns")
                else:
                    logger.warning(f"[{query_id}]   ✗ Failed to get metadata for {fqn}")
        
        if not tables:
            logger.error(f"[{query_id}] Failed to fetch metadata for any table!")
            return {
                "error": "Could not retrieve detailed metadata for any tables.",
                "error_code": "METADATA_FETCH_ERROR"
            }
        
        # Log detailed table information
        logger.info(f"[{query_id}] Successfully fetched metadata for {len(tables)} table(s):")
        for idx, table in enumerate(tables):
            logger.info(f"[{query_id}]   Table {idx+1}: {table.schema_name}.{table.table_name}")
            logger.info(f"[{query_id}]     Columns ({len(table.columns)}):")
            for col in table.columns[:10]:  # Log first 10 columns
                logger.info(f"[{query_id}]       - {col.name} ({col.type})")
            if len(table.columns) > 10:
                logger.info(f"[{query_id}]       ... and {len(table.columns) - 10} more columns")
            
            # Log relationships if available
            if table.relationships:
                logger.info(f"[{query_id}]     Relationships ({len(table.relationships)}):")
                for rel in table.relationships:
                    logger.info(f"[{query_id}]       - {rel}")
        
        logger.info(f"[{query_id}] ===== METADATA FETCHER END (SUCCESS) =====")
        
        return {
            "metadata": tables
        }
        
    except Exception as e:
        logger.exception(f"[{query_id}] ===== METADATA FETCHER END (ERROR) =====")
        logger.exception(f"[{query_id}] Metadata fetching failed: {e}")
        return {
            "error": f"Failed to fetch metadata: {str(e)}",
            "error_code": "METADATA_FETCH_ERROR"
        }

