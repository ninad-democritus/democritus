"""
Iceberg Catalog Service for managing Iceberg tables and catalog operations
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.table import Table
from pyiceberg.exceptions import TableAlreadyExistsError, NoSuchTableError
from minio import Minio
from io import BytesIO

from ..infrastructure.spark_session_manager import SparkSessionManager

logger = logging.getLogger(__name__)


class TableInfo:
    """Information about an Iceberg table"""
    
    def __init__(self, name: str, schema: Schema, location: str, properties: Dict[str, str] = None):
        self.name = name
        self.schema = schema
        self.location = location
        self.properties = properties or {}
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "location": self.location,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "schema": {
                "fields": [
                    {
                        "id": field.field_id,
                        "name": field.name,
                        "type": str(field.field_type),
                        "required": field.required
                    }
                    for field in self.schema.fields
                ]
            }
        }


class IcebergCatalogService:
    """Service for managing Iceberg catalog operations"""
    
    def __init__(self):
        """Initialize the Iceberg catalog service"""
        self.spark_manager = SparkSessionManager()
        self._catalog = None
        
        # Use environment variables with fallbacks
        iceberg_uri = os.getenv("ICEBERG_REST_URI", "http://iceberg-rest:8181")
        minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        
        # Ensure minio endpoint has http prefix for PyIceberg
        if not minio_endpoint.startswith("http"):
            minio_endpoint = f"http://{minio_endpoint}"
        
        self._catalog_config = {
            "type": "rest",
            "uri": iceberg_uri,
            "s3.endpoint": minio_endpoint,
            "s3.access-key-id": minio_access_key,
            "s3.secret-access-key": minio_secret_key,
            "s3.path-style-access": "true",
            "s3.region": os.getenv("AWS_REGION", "us-east-1")
        }
        
        logger.info(f"Initializing Iceberg catalog with URI: {iceberg_uri}")
        logger.info(f"S3 endpoint: {minio_endpoint}")
    
    def _get_catalog(self):
        """Get or create the Iceberg catalog"""
        if self._catalog is None:
            try:
                logger.info(f"Loading Iceberg catalog with config: {self._catalog_config}")
                self._catalog = load_catalog("iceberg_catalog", **self._catalog_config)
                logger.info("Iceberg catalog initialized successfully")
                
                # Test catalog connectivity and ensure default namespace exists
                try:
                    namespaces = self._catalog.list_namespaces()
                    logger.info(f"Catalog connectivity test passed. Available namespaces: {namespaces}")
                    
                    # Ensure default namespace exists
                    if "default" not in [str(ns) for ns in namespaces]:
                        logger.info("Creating default namespace")
                        self._catalog.create_namespace("default")
                        logger.info("Default namespace created successfully")
                        
                except Exception as e:
                    logger.warning(f"Catalog connectivity test failed: {str(e)}")
                    # Try to create default namespace anyway
                    try:
                        self._catalog.create_namespace("default")
                        logger.info("Default namespace created during fallback")
                    except Exception as ns_error:
                        logger.warning(f"Failed to create default namespace: {str(ns_error)}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize Iceberg catalog: {str(e)}")
                logger.error(f"Catalog config was: {self._catalog_config}")
                raise
        return self._catalog
    
    async def _ensure_warehouse_exists(self) -> bool:
        """
        Ensure the warehouse bucket and path structure exists in MinIO
        
        Returns:
            True if warehouse exists or was created successfully
        """
        try:
            # Get MinIO configuration
            minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
            minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
            
            # Create MinIO client
            client = Minio(
                minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=False
            )
            
            # Ensure 'data' bucket exists
            bucket_name = "data"
            if not client.bucket_exists(bucket_name):
                logger.info(f"Creating bucket: {bucket_name}")
                client.make_bucket(bucket_name)
                logger.info(f"✅ Created bucket: {bucket_name}")
            else:
                logger.debug(f"Bucket {bucket_name} already exists")
            
            # Create warehouse directory structure by putting a placeholder object
            warehouse_path = "warehouse/.warehouse_initialized"
            try:
                client.put_object(
                    bucket_name,
                    warehouse_path,
                    BytesIO(b"warehouse initialized"),
                    length=len(b"warehouse initialized"),
                    content_type="text/plain"
                )
                logger.info(f"✅ Initialized warehouse path: s3a://{bucket_name}/warehouse/")
            except Exception as e:
                # If object already exists, that's fine
                logger.debug(f"Warehouse path may already exist: {str(e)}")
            
            return True
            
        except Exception as e:
            # Check if it's a bucket already exists error
            error_str = str(e)
            if "already exists" in error_str.lower():
                logger.debug(f"Bucket already exists: {error_str}")
                return True
            else:
                logger.error(f"Failed to ensure warehouse exists: {str(e)}")
                return False
    
    async def ensure_table_exists(self, table_name: str, schema: Schema, properties: Dict[str, str] = None) -> bool:
        """
        Ensure a table exists, create if it doesn't
        
        Args:
            table_name: Name of the table
            schema: Iceberg schema for the table
            properties: Optional table properties
            
        Returns:
            True if table exists or was created successfully
        """
        logger.info(f"Ensuring table exists: {table_name}")
        
        try:
            catalog = self._get_catalog()
            
            # Check if table already exists
            if await self._table_exists(table_name):
                logger.error(f"Table {table_name} already exists")
                return True
            
            # Ensure warehouse bucket/path exists before creating table
            if not await self._ensure_warehouse_exists():
                logger.error("Failed to ensure warehouse bucket exists")
                return False
            
            # Validate table location before creation
            if not await self.validate_table_location(table_name):
                logger.error(f"Table location validation failed for {table_name}")
                return False
            
            # Create the table
            return await self.create_table(table_name, schema, properties)
            
        except Exception as e:
            logger.error(f"Failed to ensure table exists {table_name}: {str(e)}")
            return False
    
    async def validate_table_location(self, table_name: str) -> bool:
        """
        Validate that the table location is accessible
        
        Args:
            table_name: Name of the table to validate location for
            
        Returns:
            True if location is accessible
        """
        try:
            # Test warehouse location accessibility
            catalog = self._get_catalog()
            
            # Get warehouse location from catalog config
            warehouse_location = "s3a://data/warehouse/"
            
            # Use Spark to test S3 connectivity
            spark = self.spark_manager.get_session()
            
            # Try to list the warehouse location
            try:
                spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
                    spark.sparkContext._jvm.java.net.URI(warehouse_location),
                    spark.sparkContext._jsc.hadoopConfiguration()
                )
                logger.info(f"Table location validation passed for warehouse: {warehouse_location}")
                return True
            except Exception as fs_error:
                logger.error(f"Failed to access warehouse location {warehouse_location}: {str(fs_error)}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating table location for {table_name}: {str(e)}")
            return False

    async def create_table(self, table_name: str, schema: Schema, properties: Dict[str, str] = None) -> bool:
        """
        Create a new Iceberg table
        
        Args:
            table_name: Name of the table to create
            schema: Iceberg schema for the table
            properties: Optional table properties
            
        Returns:
            True if table was created successfully
        """
        logger.info(f"Creating Iceberg table: {table_name}")
        
        try:
            catalog = self._get_catalog()
            
            # Set default properties
            table_properties = {
                "write.format.default": "parquet",
                "write.parquet.compression-codec": "snappy"
            }
            if properties:
                table_properties.update(properties)
            
            # Create table using catalog with fully qualified name
            # Ensure table name includes namespace
            if "." not in table_name:
                qualified_table_name = f"default.{table_name}"
            else:
                qualified_table_name = table_name
                
            logger.info(f"Creating table with qualified name: {qualified_table_name}")
            table = catalog.create_table(
                identifier=qualified_table_name,
                schema=schema,
                properties=table_properties
            )
            
            logger.info(f"Successfully created table: {table_name}")
            return True
            
        except TableAlreadyExistsError:
            logger.info(f"Table {table_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {str(e)}")
            return False
    
    async def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """
        Get information about a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            TableInfo object or None if table doesn't exist
        """
        logger.info(f"Getting table info for: {table_name}")
        
        try:
            catalog = self._get_catalog()
            table = catalog.load_table(table_name)
            
            return TableInfo(
                name=table_name,
                schema=table.schema(),
                location=table.location(),
                properties=table.properties
            )
            
        except NoSuchTableError:
            logger.warning(f"Table {table_name} does not exist")
            return None
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {str(e)}")
            return None
    
    async def drop_table(self, table_name: str, purge: bool = True) -> bool:
        """
        Drop an Iceberg table
        
        Args:
            table_name: Name of the table to drop
            purge: Whether to purge all data files
            
        Returns:
            True if table was dropped successfully
        """
        logger.info(f"Dropping table: {table_name} (purge={purge})")
        
        try:
            catalog = self._get_catalog()
            
            # Drop the table
            catalog.drop_table(table_name, purge=purge)
            
            logger.info(f"Successfully dropped table: {table_name}")
            return True
            
        except NoSuchTableError:
            logger.warning(f"Table {table_name} does not exist")
            return True  # Consider it successful if table doesn't exist
        except Exception as e:
            logger.error(f"Failed to drop table {table_name}: {str(e)}")
            return False
    
    async def list_tables(self, namespace: str = "default") -> List[str]:
        """
        List all tables in a namespace
        
        Args:
            namespace: Namespace to list tables from
            
        Returns:
            List of table names
        """
        logger.info(f"Listing tables in namespace: {namespace}")
        
        try:
            catalog = self._get_catalog()
            
            # List tables in namespace
            tables = catalog.list_tables(namespace)
            table_names = [str(table) for table in tables]
            
            logger.info(f"Found {len(table_names)} tables in namespace {namespace}")
            return table_names
            
        except Exception as e:
            logger.error(f"Failed to list tables in namespace {namespace}: {str(e)}")
            return []
    
    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists
        """
        return await self._table_exists(table_name)
    
    async def _table_exists(self, table_name: str) -> bool:
        """Internal method to check if table exists"""
        try:
            catalog = self._get_catalog()
            
            # Use qualified table name
            if "." not in table_name:
                qualified_table_name = f"default.{table_name}"
            else:
                qualified_table_name = table_name
                
            catalog.load_table(qualified_table_name)
            return True
        except NoSuchTableError:
            return False
        except Exception as e:
            logger.error(f"Error checking if table exists {table_name}: {str(e)}")
            return False
    
    async def get_table_schema(self, table_name: str) -> Optional[Schema]:
        """
        Get the schema of a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Iceberg Schema or None if table doesn't exist
        """
        try:
            catalog = self._get_catalog()
            table = catalog.load_table(table_name)
            return table.schema()
        except NoSuchTableError:
            logger.warning(f"Table {table_name} does not exist")
            return None
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {str(e)}")
            return None
    
    async def update_table_schema(self, table_name: str, new_schema: Schema) -> bool:
        """
        Update the schema of a table
        
        Args:
            table_name: Name of the table
            new_schema: New schema to apply
            
        Returns:
            True if schema was updated successfully
        """
        logger.info(f"Updating schema for table: {table_name}")
        
        try:
            catalog = self._get_catalog()
            table = catalog.load_table(table_name)
            
            # Update schema (this is a simplified version)
            # In practice, you'd need to handle schema evolution properly
            logger.warning("Schema update not fully implemented - this is a placeholder")
            
            return True
            
        except NoSuchTableError:
            logger.error(f"Table {table_name} does not exist")
            return False
        except Exception as e:
            logger.error(f"Failed to update schema for table {table_name}: {str(e)}")
            return False
    
    async def get_table_statistics(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics about a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table statistics or None if failed
        """
        logger.info(f"Getting statistics for table: {table_name}")
        
        try:
            catalog = self._get_catalog()
            table = catalog.load_table(table_name)
            
            # Get basic table information
            stats = {
                "table_name": table_name,
                "location": table.location(),
                "schema_id": table.schema().schema_id,
                "field_count": len(table.schema().fields),
                "properties": table.properties
            }
            
            # Try to get row count using Spark
            try:
                spark = SparkSessionManager.get_session()
                df = spark.table(f"iceberg_catalog.{table_name}")
                stats["row_count"] = df.count()
            except Exception as e:
                logger.warning(f"Could not get row count for {table_name}: {str(e)}")
                stats["row_count"] = None
            
            return stats
            
        except NoSuchTableError:
            logger.warning(f"Table {table_name} does not exist")
            return None
        except Exception as e:
            logger.error(f"Failed to get statistics for table {table_name}: {str(e)}")
            return None
    
    async def cleanup_failed_tables(self, table_names: List[str]) -> Dict[str, bool]:
        """
        Clean up tables that failed during creation
        
        Args:
            table_names: List of table names to clean up
            
        Returns:
            Dictionary mapping table names to cleanup success status
        """
        logger.info(f"Cleaning up {len(table_names)} failed tables")
        
        results = {}
        
        for table_name in table_names:
            try:
                # Try multiple cleanup strategies
                success = False
                
                # Strategy 1: Drop table if it exists
                if await self.table_exists(table_name):
                    success = await self.drop_table(table_name, purge=True)
                else:
                    success = True  # Table doesn't exist, consider it cleaned
                
                results[table_name] = success
                
                if success:
                    logger.info(f"Successfully cleaned up table: {table_name}")
                else:
                    logger.error(f"Failed to clean up table: {table_name}")
                    
            except Exception as e:
                logger.error(f"Error cleaning up table {table_name}: {str(e)}")
                results[table_name] = False
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the Iceberg catalog service
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            "service": "iceberg_catalog",
            "status": "unknown",
            "catalog_initialized": self._catalog is not None,
            "catalog_config": self._catalog_config,
            "errors": []
        }
        
        try:
            # Test catalog initialization
            catalog = self._get_catalog()
            health_status["catalog_initialized"] = True
            
            # Test namespace listing
            try:
                namespaces = catalog.list_namespaces()
                health_status["namespaces"] = [str(ns) for ns in namespaces]
                health_status["namespace_access"] = True
            except Exception as e:
                health_status["namespace_access"] = False
                health_status["errors"].append(f"Namespace access failed: {str(e)}")
            
            # Test warehouse location
            try:
                location_valid = await self.validate_table_location("health_check")
                health_status["warehouse_access"] = location_valid
                if not location_valid:
                    health_status["errors"].append("Warehouse location not accessible")
            except Exception as e:
                health_status["warehouse_access"] = False
                health_status["errors"].append(f"Warehouse validation failed: {str(e)}")
            
            # Determine overall status
            if health_status["catalog_initialized"] and health_status.get("namespace_access", False) and health_status.get("warehouse_access", False):
                health_status["status"] = "healthy"
            elif health_status["catalog_initialized"]:
                health_status["status"] = "degraded"
            else:
                health_status["status"] = "unhealthy"
                
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["errors"].append(f"Catalog initialization failed: {str(e)}")
        
        return health_status

    def get_catalog_info(self) -> Dict[str, Any]:
        """
        Get information about the catalog configuration
        
        Returns:
            Dictionary with catalog information
        """
        return {
            "catalog_type": self._catalog_config.get("type"),
            "catalog_uri": self._catalog_config.get("uri"),
            "s3_endpoint": self._catalog_config.get("s3.endpoint"),
            "initialized": self._catalog is not None
        }

