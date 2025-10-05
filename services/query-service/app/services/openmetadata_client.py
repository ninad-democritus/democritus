"""OpenMetadata client for fetching schema and metadata"""
import logging
from typing import List, Optional, Dict, Any
import httpx

from ..config import settings
from ..models import TableMetadata, TableColumn

logger = logging.getLogger(__name__)


class OpenMetadataClient:
    """Client for interacting with OpenMetadata API"""
    
    def __init__(self):
        self.api_endpoint = settings.OPENMETADATA_API_ENDPOINT
        self.jwt_token = settings.OPENMETADATA_JWT_TOKEN
        self.timeout = settings.OPENMETADATA_TIMEOUT
        
        self.headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json"
        }
    
    async def list_tables(
        self,
        database: Optional[str] = None,
        schema: Optional[str] = None,
        service: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all tables in OpenMetadata by calling the tables API directly.
        
        Args:
            database: Optional database filter
            schema: Optional schema filter
            service: Optional service filter (e.g., 'data-pipeline-service')
            
        Returns:
            List of table summaries
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use the direct tables API endpoint instead of search
                url = f"{self.api_endpoint}/v1/tables"
                
                params = {
                    "limit": 100
                }
                
                # Add service filter if provided
                if service:
                    params["service"] = service
                if database:
                    params["database"] = database
                
                logger.info(f"Listing tables from service: {service or 'all'}")
                
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                tables = data.get("data", [])
                logger.info(f"List tables returned {len(tables)} results")
                
                # Convert to same format as search results for compatibility
                return [{"_source": table} for table in tables]
                
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    async def get_table_metadata(
        self,
        table_fqn: str
    ) -> Optional[TableMetadata]:
        """
        Get detailed metadata for a specific table.
        
        Args:
            table_fqn: Fully qualified table name (e.g., data-pipeline-service.default.default.table_name)
            
        Returns:
            TableMetadata with Trino-compatible schema name or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.api_endpoint}/v1/tables/name/{table_fqn}"
                params = {"fields": "columns,databaseSchema,database,service"}
                
                logger.info(f"Fetching table metadata for: {table_fqn}")
                
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Parse columns
                columns = []
                for col in data.get("columns", []):
                    columns.append(TableColumn(
                        name=col["name"],
                        type=col["dataType"],
                        description=col.get("description", "")
                    ))
                
                # Extract schema and table name from OpenMetadata
                # OpenMetadata FQN: data-pipeline-service.default.default.table_name
                # But Trino uses: iceberg.default.table_name
                om_schema_name = data.get("databaseSchema", {}).get("name", "default")
                table_name = data.get("name", "")
                
                # Map to Trino schema - use 'default' from the database schema name
                # This assumes tables are in iceberg.default schema in Trino
                trino_schema = "default"
                
                logger.info(f"Parsed table: {table_name}, OM schema: {om_schema_name}, Trino schema: {trino_schema}, columns: {len(columns)}")
                
                return TableMetadata(
                    table_name=table_name,
                    schema_name=trino_schema,  # Use Trino schema name, not OpenMetadata schema
                    columns=columns,
                    relationships=[]  # TODO: Parse relationships if available
                )
                
        except Exception as e:
            logger.error(f"Failed to get table metadata for {table_fqn}: {e}")
            return None
    
    async def search_tables(
        self,
        query: str,
        limit: int = 10
    ) -> List[TableMetadata]:
        """
        Search for tables by name or description.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching tables
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.api_endpoint}/v1/search/query"
                params = {
                    "q": query,
                    "index": "table_search_index",
                    "from": 0,
                    "size": limit
                }
                
                response = await client.get(
                    url,
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                hits = data.get("hits", {}).get("hits", [])
                
                # Fetch full metadata for each table
                tables = []
                for hit in hits:
                    source = hit.get("_source", {})
                    fqn = source.get("fullyQualifiedName", "")
                    if fqn:
                        table_meta = await self.get_table_metadata(fqn)
                        if table_meta:
                            tables.append(table_meta)
                
                return tables
                
        except Exception as e:
            logger.error(f"Failed to search tables: {e}")
            return []
    
    def test_connection(self) -> bool:
        """
        Test OpenMetadata connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            import requests
            url = f"{self.api_endpoint}/v1/system/version"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenMetadata connection test failed: {e}")
            return False


# Global client instance
_client: Optional[OpenMetadataClient] = None


def get_openmetadata_client() -> OpenMetadataClient:
    """Get global OpenMetadata client instance"""
    global _client
    if _client is None:
        _client = OpenMetadataClient()
    return _client

