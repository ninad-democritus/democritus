"""
Schema Validator Service for schema creation and validation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, LongType, 
    DoubleType, BooleanType, TimestampType, DateType, DecimalType
)
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

# Iceberg types
from pyiceberg.schema import Schema
from pyiceberg.types import (
    StringType as IcebergStringType,
    IntegerType as IcebergIntegerType,
    LongType as IcebergLongType,
    DoubleType as IcebergDoubleType,
    BooleanType as IcebergBooleanType,
    TimestampType as IcebergTimestampType,
    DateType as IcebergDateType,
    DecimalType as IcebergDecimalType,
    NestedField
)

logger = logging.getLogger(__name__)


class SchemaValidatorService:
    """Service for schema creation, validation, and type conversion"""
    
    def __init__(self):
        """Initialize the schema validator service"""
        pass
    
    def create_spark_schema(self, entity: Dict[str, Any]) -> StructType:
        """
        Create a Spark StructType schema from entity definition
        
        Args:
            entity: Entity definition with column details
            
        Returns:
            Spark StructType schema
        """
        logger.info(f"Creating Spark schema for entity {entity.get('name', 'unknown')}")
        
        try:
            fields = []
            
            for column_def in entity.get('column_details', []):
                col_name = column_def.get('name')
                col_type = column_def.get('data_type', 'string')
                nullable = column_def.get('nullable', True)
                
                if not col_name:
                    logger.warning("Skipping column with no name")
                    continue
                
                spark_type = self._map_to_spark_type(col_type)
                field = StructField(col_name, spark_type, nullable)
                fields.append(field)
            
            schema = StructType(fields)
            logger.info(f"Created Spark schema with {len(fields)} fields for entity {entity.get('name', 'unknown')}")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to create Spark schema for entity {entity.get('name', 'unknown')}: {str(e)}")
            raise
    
    def create_iceberg_schema(self, entity: Dict[str, Any]) -> Schema:
        """
        Create an Iceberg Schema from entity definition
        
        Args:
            entity: Entity definition with column details
            
        Returns:
            Iceberg Schema
        """
        logger.info(f"Creating Iceberg schema for entity {entity.get('name', 'unknown')}")
        
        try:
            fields = []
            field_id = 1
            
            for column_def in entity.get('column_details', []):
                col_name = column_def.get('name')
                col_type = column_def.get('data_type', 'string')
                nullable = column_def.get('nullable', True)
                
                if not col_name:
                    logger.warning("Skipping column with no name")
                    continue
                
                iceberg_type = self._map_to_iceberg_type(col_type)
                field = NestedField(
                    field_id=field_id,
                    name=col_name,
                    field_type=iceberg_type,
                    required=not nullable
                )
                fields.append(field)
                field_id += 1
            
            schema = Schema(*fields)
            logger.info(f"Created Iceberg schema with {len(fields)} fields for entity {entity.get('name', 'unknown')}")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to create Iceberg schema for entity {entity.get('name', 'unknown')}: {str(e)}")
            raise
    
    def validate_schema_compatibility(self, source_schema: StructType, target_schema: StructType) -> Tuple[bool, List[str]]:
        """
        Validate compatibility between source and target schemas
        
        Args:
            source_schema: Source Spark schema
            target_schema: Target Spark schema
            
        Returns:
            Tuple of (is_compatible, list_of_issues)
        """
        logger.info("Validating schema compatibility")
        
        issues = []
        is_compatible = True
        
        try:
            # Create field mappings
            source_fields = {field.name: field for field in source_schema.fields}
            target_fields = {field.name: field for field in target_schema.fields}
            
            # Check for missing required fields in source
            for target_name, target_field in target_fields.items():
                if target_name not in source_fields:
                    if not target_field.nullable:
                        issues.append(f"Required field '{target_name}' missing in source schema")
                        is_compatible = False
                    else:
                        issues.append(f"Optional field '{target_name}' missing in source schema (will be null)")
            
            # Check for type compatibility
            for source_name, source_field in source_fields.items():
                if source_name in target_fields:
                    target_field = target_fields[source_name]
                    
                    if not self._are_types_compatible(source_field.dataType, target_field.dataType):
                        issues.append(f"Type mismatch for field '{source_name}': {source_field.dataType} -> {target_field.dataType}")
                        # Type conversion might still be possible, so don't mark as incompatible
                    
                    # Check nullability
                    if source_field.nullable and not target_field.nullable:
                        issues.append(f"Nullability mismatch for field '{source_name}': nullable -> non-nullable")
            
            # Check for extra fields in source
            extra_fields = set(source_fields.keys()) - set(target_fields.keys())
            if extra_fields:
                issues.append(f"Extra fields in source schema: {extra_fields}")
            
            logger.info(f"Schema compatibility check completed: {'compatible' if is_compatible else 'incompatible'}")
            return is_compatible, issues
            
        except Exception as e:
            logger.error(f"Schema compatibility validation failed: {str(e)}")
            return False, [f"Validation error: {str(e)}"]
    
    def convert_dataframe_types(self, df: DataFrame, target_schema: StructType) -> Optional[DataFrame]:
        """
        Convert DataFrame types to match target schema
        
        Args:
            df: Source DataFrame
            target_schema: Target schema to convert to
            
        Returns:
            DataFrame with converted types or None if failed
        """
        logger.info("Converting DataFrame types to match target schema")
        
        try:
            converted_df = df
            target_fields = {field.name: field for field in target_schema.fields}
            
            # Convert each column
            for col_name in df.columns:
                if col_name in target_fields:
                    target_field = target_fields[col_name]
                    current_type = dict(df.dtypes)[col_name]
                    target_type = target_field.dataType
                    
                    # Only convert if types are different
                    if str(target_type) != current_type:
                        logger.debug(f"Converting column '{col_name}' from {current_type} to {target_type}")
                        converted_df = converted_df.withColumn(col_name, col(col_name).cast(target_type))
            
            # Add missing columns with null values
            for target_name, target_field in target_fields.items():
                if target_name not in df.columns:
                    logger.debug(f"Adding missing column '{target_name}' with null values")
                    converted_df = converted_df.withColumn(target_name, col("*").cast(target_field.dataType))
            
            # Select columns in target schema order
            column_order = [field.name for field in target_schema.fields]
            converted_df = converted_df.select(*column_order)
            
            logger.info("DataFrame type conversion completed successfully")
            return converted_df
            
        except Exception as e:
            logger.error(f"DataFrame type conversion failed: {str(e)}")
            return None
    
    def _map_to_spark_type(self, data_type: str):
        """Map string data type to Spark type"""
        type_mapping = {
            'string': StringType(),
            'varchar': StringType(),
            'text': StringType(),
            'integer': IntegerType(),
            'int': IntegerType(),
            'bigint': LongType(),
            'long': LongType(),
            'double': DoubleType(),
            'float': DoubleType(),
            'decimal': DecimalType(10, 2),
            'boolean': BooleanType(),
            'bool': BooleanType(),
            'timestamp': TimestampType(),
            'datetime': TimestampType(),
            'date': DateType()
        }
        
        normalized_type = data_type.lower().strip()
        spark_type = type_mapping.get(normalized_type, StringType())
        
        if normalized_type not in type_mapping:
            logger.warning(f"Unknown data type '{data_type}', defaulting to StringType")
        
        return spark_type
    
    def _map_to_iceberg_type(self, data_type: str):
        """Map string data type to Iceberg type"""
        type_mapping = {
            'string': IcebergStringType(),
            'varchar': IcebergStringType(),
            'text': IcebergStringType(),
            'integer': IcebergIntegerType(),
            'int': IcebergIntegerType(),
            'bigint': IcebergLongType(),
            'long': IcebergLongType(),
            'double': IcebergDoubleType(),
            'float': IcebergDoubleType(),
            'decimal': IcebergDecimalType(10, 2),
            'boolean': IcebergBooleanType(),
            'bool': IcebergBooleanType(),
            'timestamp': IcebergTimestampType(),
            'datetime': IcebergTimestampType(),
            'date': IcebergDateType()
        }
        
        normalized_type = data_type.lower().strip()
        iceberg_type = type_mapping.get(normalized_type, IcebergStringType())
        
        if normalized_type not in type_mapping:
            logger.warning(f"Unknown data type '{data_type}', defaulting to IcebergStringType")
        
        return iceberg_type
    
    def _are_types_compatible(self, source_type, target_type) -> bool:
        """Check if two Spark types are compatible for conversion"""
        # Same type is always compatible
        if type(source_type) == type(target_type):
            return True
        
        # String can be converted to most types
        if isinstance(source_type, StringType):
            return True
        
        # Numeric type conversions
        numeric_types = (IntegerType, LongType, DoubleType, DecimalType)
        if isinstance(source_type, numeric_types) and isinstance(target_type, numeric_types):
            return True
        
        # Boolean conversions
        if isinstance(source_type, BooleanType) and isinstance(target_type, StringType):
            return True
        
        # Timestamp/Date conversions
        temporal_types = (TimestampType, DateType)
        if isinstance(source_type, temporal_types) and isinstance(target_type, temporal_types):
            return True
        
        return False
    
    def get_schema_summary(self, schema: StructType) -> Dict[str, Any]:
        """
        Get a summary of the schema
        
        Args:
            schema: Spark StructType schema
            
        Returns:
            Dictionary with schema summary
        """
        try:
            field_info = []
            type_counts = {}
            nullable_count = 0
            
            for field in schema.fields:
                field_type = str(field.dataType)
                field_info.append({
                    "name": field.name,
                    "type": field_type,
                    "nullable": field.nullable
                })
                
                # Count types
                type_counts[field_type] = type_counts.get(field_type, 0) + 1
                
                # Count nullable fields
                if field.nullable:
                    nullable_count += 1
            
            return {
                "total_fields": len(schema.fields),
                "nullable_fields": nullable_count,
                "required_fields": len(schema.fields) - nullable_count,
                "type_distribution": type_counts,
                "fields": field_info
            }
            
        except Exception as e:
            logger.error(f"Failed to generate schema summary: {str(e)}")
            return {}
    
    def validate_data_against_schema(self, df: DataFrame, schema: StructType) -> Dict[str, Any]:
        """
        Validate actual data against schema constraints
        
        Args:
            df: DataFrame to validate
            schema: Expected schema
            
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating data against schema constraints")
        
        try:
            validation_results = {
                "is_valid": True,
                "total_rows": df.count(),
                "field_validations": {},
                "errors": [],
                "warnings": []
            }
            
            schema_fields = {field.name: field for field in schema.fields}
            
            for col_name in df.columns:
                if col_name in schema_fields:
                    field = schema_fields[col_name]
                    
                    # Check for nulls in non-nullable fields
                    if not field.nullable:
                        null_count = df.filter(col(col_name).isNull()).count()
                        if null_count > 0:
                            validation_results["is_valid"] = False
                            validation_results["errors"].append(
                                f"Field '{col_name}' has {null_count} null values but is marked as non-nullable"
                            )
                    
                    # Store field validation info
                    validation_results["field_validations"][col_name] = {
                        "expected_type": str(field.dataType),
                        "actual_type": dict(df.dtypes)[col_name],
                        "nullable": field.nullable,
                        "null_count": df.filter(col(col_name).isNull()).count()
                    }
            
            logger.info(f"Data validation completed: {'valid' if validation_results['is_valid'] else 'invalid'}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Data validation against schema failed: {str(e)}")
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }

