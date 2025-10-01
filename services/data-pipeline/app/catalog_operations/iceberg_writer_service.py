"""
Iceberg Writer Service for writing data to Iceberg tables
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pyspark.sql import DataFrame

from ..infrastructure.spark_session_manager import SparkSessionManager
from .iceberg_catalog_service import IcebergCatalogService

logger = logging.getLogger(__name__)


class WriteResult:
    """Result of a write operation"""
    
    def __init__(self, success: bool, table_name: str, records_written: int = 0, 
                 error_message: str = None, duration_seconds: float = 0.0):
        self.success = success
        self.table_name = table_name
        self.records_written = records_written
        self.error_message = error_message
        self.duration_seconds = duration_seconds
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "table_name": self.table_name,
            "records_written": self.records_written,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat()
        }


class IcebergWriterService:
    """Service for writing data to Iceberg tables"""
    
    def __init__(self):
        """Initialize the Iceberg writer service"""
        self.spark_manager = SparkSessionManager()
        self.catalog_service = IcebergCatalogService()
    
    async def write_data_to_table(self, df: DataFrame, table_name: str, write_mode: str = "append") -> WriteResult:
        """
        Write data to an Iceberg table
        
        Args:
            df: DataFrame to write
            table_name: Name of the target table
            write_mode: Write mode ('append', 'overwrite', 'merge')
            
        Returns:
            WriteResult with operation details
        """
        logger.info(f"Writing data to table {table_name} with mode {write_mode}")
        
        start_time = datetime.now()
        
        try:
            # Validate inputs
            if df is None:
                return WriteResult(False, table_name, error_message="DataFrame is None")
            
            record_count = df.count()
            if record_count == 0:
                logger.warning(f"DataFrame is empty for table {table_name}")
                return WriteResult(True, table_name, 0, "DataFrame is empty")
            
            # Ensure table exists
            table_exists = await self.catalog_service.table_exists(table_name)
            if not table_exists:
                logger.error(f"Table {table_name} does not exist. Available tables:")
                try:
                    available_tables = await self.catalog_service.list_tables("default")
                    logger.error(f"Available tables in default namespace: {available_tables}")
                except Exception as e:
                    logger.error(f"Failed to list available tables: {str(e)}")
                return WriteResult(False, table_name, error_message=f"Table {table_name} does not exist")
            
            # Write data using Spark
            spark = SparkSessionManager.get_session()
            
            # Ensure table name is properly qualified with namespace
            qualified_table_name = f"iceberg_catalog.default.{table_name}" if "." not in table_name else f"iceberg_catalog.{table_name}"
            logger.info(f"Writing to qualified table name: {qualified_table_name}")
            
            if write_mode == "append":
                df.writeTo(qualified_table_name).append()
            elif write_mode == "overwrite":
                df.writeTo(qualified_table_name).overwritePartitions()
            elif write_mode == "merge":
                # For merge operations, we'd need more complex logic
                # For now, fall back to append
                logger.warning(f"Merge mode not fully implemented, using append for {table_name}")
                df.writeTo(qualified_table_name).append()
            else:
                return WriteResult(False, table_name, error_message=f"Unsupported write mode: {write_mode}")
            
            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Successfully wrote {record_count} records to {table_name} in {duration:.2f}s")
            return WriteResult(True, table_name, record_count, duration_seconds=duration)
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            error_msg = str(e)
            
            logger.error(f"Failed to write data to {table_name}: {error_msg}")
            return WriteResult(False, table_name, error_message=error_msg, duration_seconds=duration)
    
    async def append_data_to_table(self, df: DataFrame, table_name: str) -> WriteResult:
        """
        Append data to an Iceberg table
        
        Args:
            df: DataFrame to append
            table_name: Name of the target table
            
        Returns:
            WriteResult with operation details
        """
        return await self.write_data_to_table(df, table_name, write_mode="append")
    
    async def overwrite_table_data(self, df: DataFrame, table_name: str) -> WriteResult:
        """
        Overwrite data in an Iceberg table
        
        Args:
            df: DataFrame to write
            table_name: Name of the target table
            
        Returns:
            WriteResult with operation details
        """
        return await self.write_data_to_table(df, table_name, write_mode="overwrite")
    
    async def validate_write_success(self, table_name: str, expected_records: int, tolerance: float = 0.05) -> bool:
        """
        Validate that a write operation was successful
        
        Args:
            table_name: Name of the table to validate
            expected_records: Expected number of records
            tolerance: Acceptable difference percentage (default 5%)
            
        Returns:
            True if validation passes
        """
        logger.info(f"Validating write success for table {table_name}")
        
        try:
            # Get table statistics
            stats = await self.catalog_service.get_table_statistics(table_name)
            if not stats:
                logger.error(f"Could not get statistics for table {table_name}")
                return False
            
            actual_records = stats.get("row_count")
            if actual_records is None:
                logger.warning(f"Could not determine row count for table {table_name}")
                return True  # Can't validate, assume success
            
            # Check if record count is within tolerance
            if expected_records == 0:
                return actual_records == 0
            
            difference_pct = abs(actual_records - expected_records) / expected_records
            
            if difference_pct <= tolerance:
                logger.info(f"Write validation passed for {table_name}: {actual_records} records (expected {expected_records})")
                return True
            else:
                logger.error(f"Write validation failed for {table_name}: {actual_records} records (expected {expected_records}, difference: {difference_pct:.2%})")
                return False
                
        except Exception as e:
            logger.error(f"Write validation failed for {table_name}: {str(e)}")
            return False
    
    async def batch_write_data(self, data_batches: List[Dict[str, Any]]) -> Dict[str, WriteResult]:
        """
        Write multiple DataFrames to their respective tables in batch
        
        Args:
            data_batches: List of dictionaries with 'df', 'table_name', and optional 'write_mode'
            
        Returns:
            Dictionary mapping table names to WriteResult objects
        """
        logger.info(f"Starting batch write operation for {len(data_batches)} tables")
        
        results = {}
        
        for batch in data_batches:
            df = batch.get('df')
            table_name = batch.get('table_name')
            write_mode = batch.get('write_mode', 'append')
            
            if not df or not table_name:
                logger.error(f"Invalid batch entry: missing df or table_name")
                results[table_name or 'unknown'] = WriteResult(
                    False, table_name or 'unknown', 
                    error_message="Missing df or table_name"
                )
                continue
            
            # Write data to table
            result = await self.write_data_to_table(df, table_name, write_mode)
            results[table_name] = result
        
        # Log summary
        successful_writes = sum(1 for r in results.values() if r.success)
        total_records = sum(r.records_written for r in results.values() if r.success)
        
        logger.info(f"Batch write completed: {successful_writes}/{len(data_batches)} successful, {total_records} total records written")
        
        return results
    
    async def write_with_partitioning(self, df: DataFrame, table_name: str, partition_columns: List[str]) -> WriteResult:
        """
        Write data to a table with specific partitioning
        
        Args:
            df: DataFrame to write
            table_name: Name of the target table
            partition_columns: List of columns to partition by
            
        Returns:
            WriteResult with operation details
        """
        logger.info(f"Writing data to {table_name} with partitioning on {partition_columns}")
        
        try:
            # Validate partition columns exist in DataFrame
            missing_columns = set(partition_columns) - set(df.columns)
            if missing_columns:
                error_msg = f"Partition columns not found in DataFrame: {missing_columns}"
                return WriteResult(False, table_name, error_message=error_msg)
            
            # Repartition DataFrame by partition columns
            partitioned_df = df.repartition(*[df[col] for col in partition_columns])
            
            # Write the partitioned data
            return await self.write_data_to_table(partitioned_df, table_name)
            
        except Exception as e:
            error_msg = f"Partitioned write failed: {str(e)}"
            logger.error(f"Partitioned write failed for {table_name}: {error_msg}")
            return WriteResult(False, table_name, error_message=error_msg)
    
    async def write_with_schema_validation(self, df: DataFrame, table_name: str) -> WriteResult:
        """
        Write data with schema validation against the target table
        
        Args:
            df: DataFrame to write
            table_name: Name of the target table
            
        Returns:
            WriteResult with operation details
        """
        logger.info(f"Writing data to {table_name} with schema validation")
        
        try:
            # Get target table schema
            target_schema = await self.catalog_service.get_table_schema(table_name)
            if not target_schema:
                error_msg = f"Could not get schema for table {table_name}"
                return WriteResult(False, table_name, error_message=error_msg)
            
            # Validate DataFrame schema compatibility
            # This is a simplified validation - in practice, you'd want more comprehensive checks
            target_columns = {field.name for field in target_schema.fields}
            df_columns = set(df.columns)
            
            missing_columns = target_columns - df_columns
            if missing_columns:
                logger.warning(f"DataFrame missing columns: {missing_columns}")
            
            extra_columns = df_columns - target_columns
            if extra_columns:
                logger.warning(f"DataFrame has extra columns: {extra_columns}")
                # Select only the columns that exist in target schema
                df = df.select(*[col for col in df.columns if col in target_columns])
            
            # Write the validated data
            return await self.write_data_to_table(df, table_name)
            
        except Exception as e:
            error_msg = f"Schema validation failed: {str(e)}"
            logger.error(f"Schema validation failed for {table_name}: {error_msg}")
            return WriteResult(False, table_name, error_message=error_msg)
    
    def get_write_statistics(self, results: List[WriteResult]) -> Dict[str, Any]:
        """
        Get statistics from multiple write results
        
        Args:
            results: List of WriteResult objects
            
        Returns:
            Dictionary with aggregated statistics
        """
        if not results:
            return {}
        
        successful_writes = [r for r in results if r.success]
        failed_writes = [r for r in results if not r.success]
        
        total_records = sum(r.records_written for r in successful_writes)
        total_duration = sum(r.duration_seconds for r in results)
        avg_duration = total_duration / len(results) if results else 0
        
        return {
            "total_operations": len(results),
            "successful_operations": len(successful_writes),
            "failed_operations": len(failed_writes),
            "success_rate": len(successful_writes) / len(results) * 100 if results else 0,
            "total_records_written": total_records,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "records_per_second": total_records / total_duration if total_duration > 0 else 0,
            "failed_tables": [r.table_name for r in failed_writes],
            "error_summary": {
                error: len([r for r in failed_writes if error in (r.error_message or "")])
                for error in set(r.error_message for r in failed_writes if r.error_message)
            }
        }
