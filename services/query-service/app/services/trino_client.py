"""Trino client for executing SQL queries against Iceberg tables"""
import logging
from typing import List, Dict, Any, Optional
import trino
from trino.auth import BasicAuthentication
import pandas as pd

from ..config import settings

logger = logging.getLogger(__name__)


class TrinoClient:
    """Client for interacting with Trino query engine"""
    
    def __init__(self):
        self.host = settings.TRINO_HOST
        self.port = settings.TRINO_PORT
        self.catalog = settings.TRINO_CATALOG
        self.schema = settings.TRINO_SCHEMA
        self.user = settings.TRINO_USER
        self.auth_type = settings.TRINO_AUTH_TYPE
        self.timeout = settings.TRINO_TIMEOUT
        self._connection: Optional[trino.dbapi.Connection] = None
    
    def get_connection(self) -> trino.dbapi.Connection:
        """
        Get or create Trino connection.
        
        Returns:
            Trino connection
        """
        if self._connection is None:
            auth = None
            if self.auth_type == "basic":
                # For production, use basic auth
                auth = BasicAuthentication(self.user, "")
            
            self._connection = trino.dbapi.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                catalog=self.catalog,
                schema=self.schema,
                auth=auth,
                http_scheme="http",  # Use https in production
                verify=False  # Set to True in production with valid certs
            )
            
            logger.info(f"Connected to Trino at {self.host}:{self.port}")
        
        return self._connection
    
    def close(self):
        """Close Trino connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def execute_query(
        self,
        sql: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dictionaries.
        
        Args:
            sql: SQL query to execute
            limit: Optional limit on number of rows returned
            
        Returns:
            List of row dictionaries
            
        Raises:
            Exception: If query execution fails
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Apply limit if specified and not already in query
            if limit and "LIMIT" not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT {limit}"
            
            logger.info(f"Executing Trino query: {sql[:200]}...")
            
            # Execute query
            cursor.execute(sql)
            
            # Fetch results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # Convert to list of dicts
            results = [
                dict(zip(columns, row))
                for row in rows
            ]
            
            logger.info(f"Query returned {len(results)} rows")
            
            return results
            
        except Exception as e:
            logger.error(f"Trino query failed: {e}")
            raise
    
    def execute_query_to_dataframe(
        self,
        sql: str,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Execute SQL query and return results as pandas DataFrame.
        
        Args:
            sql: SQL query to execute
            limit: Optional limit on number of rows
            
        Returns:
            pandas DataFrame with query results
        """
        results = self.execute_query(sql, limit)
        return pd.DataFrame(results)
    
    def test_connection(self) -> bool:
        """
        Test Trino connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result[0] == 1
        except Exception as e:
            logger.error(f"Trino connection test failed: {e}")
            return False
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the configured catalog and schema.
        
        Returns:
            List of table names
        """
        try:
            sql = f"SHOW TABLES FROM {self.catalog}.{self.schema}"
            results = self.execute_query(sql)
            return [row["Table"] for row in results]
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """
        Get schema (columns) for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column definitions with name, type, and comment
        """
        try:
            sql = f"DESCRIBE {self.catalog}.{self.schema}.{table_name}"
            results = self.execute_query(sql)
            return results
        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return []


# Global client instance
_client: Optional[TrinoClient] = None


def get_trino_client() -> TrinoClient:
    """Get global Trino client instance"""
    global _client
    if _client is None:
        _client = TrinoClient()
    return _client

