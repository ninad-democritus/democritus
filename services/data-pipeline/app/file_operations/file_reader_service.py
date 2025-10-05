"""
File Reader Service for reading and validating files
"""

import logging
import tempfile
import os
from typing import Optional, Dict, Any, List
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType
import pandas as pd

from ..infrastructure.spark_session_manager import SparkSessionManager
from ..infrastructure.minio_client_manager import MinioClientManager
from .models import FileInfo, ValidationResult

logger = logging.getLogger(__name__)


class FileReaderService:
    """Service for reading and validating files"""
    
    def __init__(self):
        """Initialize the file reader service"""
        self.spark_manager = SparkSessionManager()
        self.minio_manager = MinioClientManager()
    
    async def read_file_sample(self, file_info: FileInfo, sample_rows: int = 5) -> Optional[DataFrame]:
        """
        Read a sample of rows from a file for preview/validation
        
        Args:
            file_info: Information about the file to read
            sample_rows: Number of rows to sample
            
        Returns:
            Spark DataFrame with sample data or None if failed
        """
        logger.info(f"Reading sample of {sample_rows} rows from {file_info.file_name}")
        
        try:
            spark = SparkSessionManager.get_session()
            
            # Download file to temporary location
            temp_file = await self._download_to_temp(file_info)
            if not temp_file:
                return None
            
            try:
                # Read based on file type
                if file_info.file_extension == 'csv':
                    # Proper CSV options to handle quotes and escaping
                    df = spark.read \
                        .option("header", "true") \
                        .option("inferSchema", "true") \
                        .option("quote", '"') \
                        .option("escape", '"') \
                        .option("multiLine", "false") \
                        .csv(temp_file)
                elif file_info.file_extension in ['xlsx', 'xls']:
                    df = self._read_excel_with_spark(temp_file)
                elif file_info.file_extension == 'parquet':
                    df = spark.read.parquet(temp_file)
                elif file_info.file_extension == 'json':
                    df = spark.read.json(temp_file)
                else:
                    logger.error(f"Unsupported file format: {file_info.file_extension}")
                    return None
                
                # Limit to sample size
                if sample_rows > 0:
                    df = df.limit(sample_rows)
                
                logger.info(f"Successfully read sample from {file_info.file_name}")
                return df
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            logger.error(f"Failed to read sample from {file_info.file_name}: {str(e)}")
            return None
    
    async def validate_file_format(self, file_info: FileInfo) -> ValidationResult:
        """
        Validate file format and basic structure
        
        Args:
            file_info: Information about the file to validate
            
        Returns:
            ValidationResult with validation details
        """
        logger.info(f"Validating file format for {file_info.file_name}")
        
        result = ValidationResult(
            is_valid=True,
            file_info=file_info,
            errors=[],
            warnings=[]
        )
        
        try:
            # Check file extension
            if not file_info.is_supported_format:
                result.add_error(f"Unsupported file format: {file_info.file_extension}")
                return result
            
            # Check file size
            if file_info.size == 0:
                result.add_error("File is empty")
                return result
            
            if file_info.size > 100 * 1024 * 1024:  # 100MB
                result.add_warning("File is larger than 100MB, processing may be slow")
            
            # Try to read a small sample to validate structure
            sample_df = await self.read_file_sample(file_info, sample_rows=1)
            if sample_df is None:
                result.add_error("Could not read file content")
                return result
            
            # Check if file has columns
            if len(sample_df.columns) == 0:
                result.add_error("File has no columns")
                return result
            
            # Store schema information
            result.schema_info = {
                "column_count": len(sample_df.columns),
                "columns": sample_df.columns,
                "dtypes": {col: str(sample_df.schema[col].dataType) for col in sample_df.columns}
            }
            
            logger.info(f"File validation successful for {file_info.file_name}")
            
        except Exception as e:
            logger.error(f"File validation failed for {file_info.file_name}: {str(e)}")
            result.add_error(f"Validation error: {str(e)}")
        
        return result
    
    async def get_file_schema(self, file_info: FileInfo) -> Optional[StructType]:
        """
        Get the schema of a file
        
        Args:
            file_info: Information about the file
            
        Returns:
            Spark StructType schema or None if failed
        """
        logger.info(f"Getting schema for {file_info.file_name}")
        
        try:
            # Read a small sample to infer schema
            sample_df = await self.read_file_sample(file_info, sample_rows=10)
            if sample_df is None:
                return None
            
            return sample_df.schema
            
        except Exception as e:
            logger.error(f"Failed to get schema for {file_info.file_name}: {str(e)}")
            return None
    
    async def read_full_file(self, file_info: FileInfo) -> Optional[DataFrame]:
        """
        Read the complete file into a DataFrame
        
        Args:
            file_info: Information about the file to read
            
        Returns:
            Spark DataFrame with all data or None if failed
        """
        logger.info(f"Reading full file: {file_info.file_name}")
        
        try:
            spark = SparkSessionManager.get_session()
            
            # For larger files, read directly from S3 if possible
            if file_info.size > 10 * 1024 * 1024:  # 10MB
                s3_path = f"s3a://{file_info.bucket}/{file_info.name}"
                return await self._read_from_s3(s3_path, file_info.file_extension)
            else:
                # For smaller files, download and read locally
                temp_file = await self._download_to_temp(file_info)
                if not temp_file:
                    return None
                
                try:
                    return await self._read_from_local(temp_file, file_info.file_extension)
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        
        except Exception as e:
            logger.error(f"Failed to read full file {file_info.file_name}: {str(e)}")
            return None
    
    async def _download_to_temp(self, file_info: FileInfo) -> Optional[str]:
        """Download file to temporary location"""
        try:
            client = MinioClientManager.get_client()
            
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=f".{file_info.file_extension}")
            os.close(temp_fd)
            
            # Download file
            client.fget_object(file_info.bucket, file_info.name, temp_path)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download {file_info.file_name} to temp: {str(e)}")
            return None
    
    async def _read_from_s3(self, s3_path: str, file_extension: str) -> Optional[DataFrame]:
        """Read file directly from S3"""
        try:
            spark = SparkSessionManager.get_session()
            
            if file_extension == 'csv':
                # Proper CSV options to handle quotes and escaping
                return spark.read \
                    .option("header", "true") \
                    .option("inferSchema", "true") \
                    .option("quote", '"') \
                    .option("escape", '"') \
                    .option("multiLine", "false") \
                    .csv(s3_path)
            elif file_extension == 'parquet':
                return spark.read.parquet(s3_path)
            elif file_extension == 'json':
                return spark.read.json(s3_path)
            else:
                logger.warning(f"Cannot read {file_extension} directly from S3, falling back to local read")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read from S3 path {s3_path}: {str(e)}")
            return None
    
    async def _read_from_local(self, file_path: str, file_extension: str) -> Optional[DataFrame]:
        """Read file from local path"""
        try:
            spark = SparkSessionManager.get_session()
            
            if file_extension == 'csv':
                # Proper CSV options to handle quotes and escaping
                return spark.read \
                    .option("header", "true") \
                    .option("inferSchema", "true") \
                    .option("quote", '"') \
                    .option("escape", '"') \
                    .option("multiLine", "false") \
                    .csv(file_path)
            elif file_extension in ['xlsx', 'xls']:
                return self._read_excel_with_spark(file_path)
            elif file_extension == 'parquet':
                return spark.read.parquet(file_path)
            elif file_extension == 'json':
                return spark.read.json(file_path)
            else:
                logger.error(f"Unsupported file format for local read: {file_extension}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to read local file {file_path}: {str(e)}")
            return None
    
    def _read_excel_with_spark(self, file_path: str) -> Optional[DataFrame]:
        """Read Excel file using pandas and convert to Spark DataFrame"""
        try:
            spark = SparkSessionManager.get_session()
            
            # Read with pandas first
            pandas_df = pd.read_excel(file_path)
            
            # Convert to Spark DataFrame
            spark_df = spark.createDataFrame(pandas_df)
            
            return spark_df
            
        except Exception as e:
            logger.error(f"Failed to read Excel file {file_path}: {str(e)}")
            return None
    
    async def get_file_statistics(self, file_info: FileInfo) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics about a file
        
        Args:
            file_info: Information about the file
            
        Returns:
            Dictionary with file statistics
        """
        logger.info(f"Getting statistics for {file_info.file_name}")
        
        try:
            # Read a sample to get basic info
            sample_df = await self.read_file_sample(file_info, sample_rows=100)
            if sample_df is None:
                return None
            
            # Try to get row count from full file (if reasonable size)
            row_count = None
            if file_info.size < 50 * 1024 * 1024:  # 50MB
                full_df = await self.read_full_file(file_info)
                if full_df is not None:
                    row_count = full_df.count()
            
            return {
                "file_name": file_info.file_name,
                "file_size_bytes": file_info.size,
                "file_size_mb": round(file_info.size / (1024 * 1024), 2),
                "file_extension": file_info.file_extension,
                "column_count": len(sample_df.columns),
                "columns": sample_df.columns,
                "estimated_row_count": row_count,
                "schema": {col: str(sample_df.schema[col].dataType) for col in sample_df.columns},
                "last_modified": file_info.last_modified.isoformat() if file_info.last_modified else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics for {file_info.file_name}: {str(e)}")
            return None

