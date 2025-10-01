"""
File Processor Service for advanced file processing and data quality validation
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, BooleanType, TimestampType
from pyspark.sql.functions import col, count, isnan, isnull, when, trim, length

from ..infrastructure.spark_session_manager import SparkSessionManager
from .models import FileInfo, ValidationResult
from .file_reader_service import FileReaderService

logger = logging.getLogger(__name__)


class FileProcessorService:
    """Service for processing files and validating data quality"""
    
    def __init__(self):
        """Initialize the file processor service"""
        self.spark_manager = SparkSessionManager()
        self.file_reader = FileReaderService()
    
    async def load_file_with_schema(self, file_info: FileInfo, expected_schema: StructType) -> Optional[DataFrame]:
        """
        Load a file and apply expected schema with type conversion
        
        Args:
            file_info: Information about the file to load
            expected_schema: Expected Spark schema to apply
            
        Returns:
            DataFrame with applied schema or None if failed
        """
        logger.info(f"Loading file {file_info.file_name} with expected schema")
        
        try:
            # First, read the file normally
            df = await self.file_reader.read_full_file(file_info)
            if df is None:
                logger.error(f"Could not read file {file_info.file_name}")
                return None
            
            # Apply schema transformation
            transformed_df = await self._apply_schema_transformation(df, expected_schema)
            if transformed_df is None:
                logger.error(f"Could not apply schema to {file_info.file_name}")
                return None
            
            logger.info(f"Successfully loaded {file_info.file_name} with schema")
            return transformed_df
            
        except Exception as e:
            logger.error(f"Failed to load file {file_info.file_name} with schema: {str(e)}")
            return None
    
    async def validate_data_quality(self, df: DataFrame, entity: Dict[str, Any]) -> ValidationResult:
        """
        Validate data quality of a DataFrame against entity requirements
        
        Args:
            df: DataFrame to validate
            entity: Entity definition with validation rules
            
        Returns:
            ValidationResult with quality assessment
        """
        logger.info(f"Validating data quality for entity {entity.get('name', 'unknown')}")
        
        result = ValidationResult(
            is_valid=True,
            file_info=None,  # Will be set by caller if needed
            errors=[],
            warnings=[]
        )
        
        try:
            # Basic validations
            row_count = df.count()
            if row_count == 0:
                result.add_error("DataFrame is empty")
                return result
            
            # Column validations
            expected_columns = {col.get('name') for col in entity.get('column_details', [])}
            actual_columns = set(df.columns)
            
            # Check for missing required columns
            missing_columns = expected_columns - actual_columns
            if missing_columns:
                result.add_error(f"Missing required columns: {missing_columns}")
            
            # Check for extra columns
            extra_columns = actual_columns - expected_columns
            if extra_columns:
                result.add_warning(f"Extra columns found: {extra_columns}")
            
            # Data quality checks
            quality_stats = await self._analyze_data_quality(df)
            
            # Check null percentages
            for col_name, null_pct in quality_stats.get('null_percentages', {}).items():
                if null_pct > 50:  # More than 50% nulls
                    result.add_warning(f"Column '{col_name}' has {null_pct:.1f}% null values")
                elif null_pct > 90:  # More than 90% nulls
                    result.add_error(f"Column '{col_name}' has {null_pct:.1f}% null values")
            
            # Check for completely empty columns
            for col_name, empty_pct in quality_stats.get('empty_percentages', {}).items():
                if empty_pct > 95:  # More than 95% empty
                    result.add_warning(f"Column '{col_name}' is {empty_pct:.1f}% empty")
            
            # Store quality statistics
            result.schema_info = {
                "row_count": row_count,
                "column_count": len(df.columns),
                "quality_stats": quality_stats
            }
            
            logger.info(f"Data quality validation completed for entity {entity.get('name', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Data quality validation failed: {str(e)}")
            result.add_error(f"Validation error: {str(e)}")
        
        return result
    
    async def clean_and_prepare_data(self, df: DataFrame, entity: Dict[str, Any]) -> Optional[DataFrame]:
        """
        Clean and prepare data according to entity specifications
        
        Args:
            df: DataFrame to clean
            entity: Entity definition with cleaning rules
            
        Returns:
            Cleaned DataFrame or None if failed
        """
        logger.info(f"Cleaning and preparing data for entity {entity.get('name', 'unknown')}")
        
        try:
            cleaned_df = df
            
            # Apply column-specific cleaning
            for column_def in entity.get('column_details', []):
                col_name = column_def.get('name')
                col_type = column_def.get('data_type', 'string')
                is_nullable = column_def.get('nullable', True)
                
                if col_name not in cleaned_df.columns:
                    continue
                
                # Trim string columns
                if col_type.lower() in ['string', 'varchar', 'text']:
                    cleaned_df = cleaned_df.withColumn(col_name, trim(col(col_name)))
                
                # Handle non-nullable columns
                if not is_nullable:
                    # For non-nullable columns, we might want to filter out nulls
                    # or provide default values based on type
                    if col_type.lower() in ['integer', 'int', 'bigint']:
                        cleaned_df = cleaned_df.fillna({col_name: 0})
                    elif col_type.lower() in ['double', 'float', 'decimal']:
                        cleaned_df = cleaned_df.fillna({col_name: 0.0})
                    elif col_type.lower() in ['string', 'varchar', 'text']:
                        cleaned_df = cleaned_df.fillna({col_name: ""})
                    elif col_type.lower() == 'boolean':
                        cleaned_df = cleaned_df.fillna({col_name: False})
            
            # Remove rows where all values are null
            cleaned_df = cleaned_df.dropna(how='all')
            
            # Remove duplicate rows
            initial_count = cleaned_df.count()
            cleaned_df = cleaned_df.dropDuplicates()
            final_count = cleaned_df.count()
            
            if initial_count != final_count:
                logger.info(f"Removed {initial_count - final_count} duplicate rows")
            
            logger.info(f"Data cleaning completed for entity {entity.get('name', 'unknown')}")
            return cleaned_df
            
        except Exception as e:
            logger.error(f"Data cleaning failed for entity {entity.get('name', 'unknown')}: {str(e)}")
            return None
    
    async def _apply_schema_transformation(self, df: DataFrame, expected_schema: StructType) -> Optional[DataFrame]:
        """Apply schema transformation to DataFrame"""
        try:
            # Create a mapping of expected columns
            expected_fields = {field.name: field for field in expected_schema.fields}
            
            # Start with the original DataFrame
            transformed_df = df
            
            # Process each expected column
            for field_name, field in expected_fields.items():
                if field_name in df.columns:
                    # Cast to expected type
                    transformed_df = transformed_df.withColumn(
                        field_name, 
                        col(field_name).cast(field.dataType)
                    )
                else:
                    # Add missing column with null values
                    transformed_df = transformed_df.withColumn(
                        field_name,
                        when(col(df.columns[0]).isNotNull(), None).cast(field.dataType)
                    )
            
            # Select only the expected columns in the correct order
            column_order = [field.name for field in expected_schema.fields]
            transformed_df = transformed_df.select(*column_order)
            
            return transformed_df
            
        except Exception as e:
            logger.error(f"Schema transformation failed: {str(e)}")
            return None
    
    async def _analyze_data_quality(self, df: DataFrame) -> Dict[str, Any]:
        """Analyze data quality metrics"""
        try:
            total_rows = df.count()
            if total_rows == 0:
                return {}
            
            quality_stats = {
                "total_rows": total_rows,
                "null_percentages": {},
                "empty_percentages": {},
                "unique_counts": {},
                "data_types": {}
            }
            
            for column in df.columns:
                col_type = str(df.schema[column].dataType)
                quality_stats["data_types"][column] = col_type
                
                # Calculate null percentage
                null_count = df.filter(col(column).isNull()).count()
                null_pct = (null_count / total_rows) * 100
                quality_stats["null_percentages"][column] = null_pct
                
                # Calculate empty percentage for string columns
                if "string" in col_type.lower():
                    empty_count = df.filter(
                        (col(column).isNull()) | 
                        (trim(col(column)) == "") |
                        (length(trim(col(column))) == 0)
                    ).count()
                    empty_pct = (empty_count / total_rows) * 100
                    quality_stats["empty_percentages"][column] = empty_pct
                
                # Calculate unique count (sample for large datasets)
                if total_rows > 10000:
                    # Sample for performance
                    sample_df = df.sample(0.1, seed=42)
                    unique_count = sample_df.select(column).distinct().count()
                    # Estimate total unique count
                    estimated_unique = int(unique_count * 10)
                    quality_stats["unique_counts"][column] = min(estimated_unique, total_rows)
                else:
                    unique_count = df.select(column).distinct().count()
                    quality_stats["unique_counts"][column] = unique_count
            
            return quality_stats
            
        except Exception as e:
            logger.error(f"Data quality analysis failed: {str(e)}")
            return {}
    
    async def detect_file_encoding(self, file_info: FileInfo) -> str:
        """
        Detect file encoding for text files
        
        Args:
            file_info: Information about the file
            
        Returns:
            Detected encoding (default: 'utf-8')
        """
        try:
            # For now, assume UTF-8. In the future, we could implement
            # encoding detection using chardet or similar libraries
            return 'utf-8'
            
        except Exception as e:
            logger.error(f"Encoding detection failed for {file_info.file_name}: {str(e)}")
            return 'utf-8'
    
    async def estimate_processing_time(self, file_info: FileInfo) -> Dict[str, Any]:
        """
        Estimate processing time based on file characteristics
        
        Args:
            file_info: Information about the file
            
        Returns:
            Dictionary with time estimates
        """
        try:
            # Simple heuristic based on file size
            size_mb = file_info.size / (1024 * 1024)
            
            # Base processing rate (MB per second) - adjust based on experience
            base_rate = 5.0  # 5 MB/s
            
            # Adjust rate based on file type
            if file_info.file_extension == 'csv':
                rate = base_rate * 0.8  # CSV parsing is slower
            elif file_info.file_extension in ['xlsx', 'xls']:
                rate = base_rate * 0.5  # Excel parsing is much slower
            elif file_info.file_extension == 'parquet':
                rate = base_rate * 2.0  # Parquet is faster
            else:
                rate = base_rate
            
            estimated_seconds = size_mb / rate
            
            return {
                "file_size_mb": round(size_mb, 2),
                "estimated_processing_seconds": round(estimated_seconds, 1),
                "estimated_processing_minutes": round(estimated_seconds / 60, 1),
                "processing_rate_mb_per_sec": rate
            }
            
        except Exception as e:
            logger.error(f"Processing time estimation failed for {file_info.file_name}: {str(e)}")
            return {
                "file_size_mb": 0,
                "estimated_processing_seconds": 0,
                "estimated_processing_minutes": 0,
                "processing_rate_mb_per_sec": 0
            }

