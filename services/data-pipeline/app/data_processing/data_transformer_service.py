"""
Data Transformer Service for data transformation and cleaning operations
"""

import logging
from typing import Dict, Any, List, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, trim, upper, lower, regexp_replace, when, isnan, isnull,
    to_timestamp, to_date, split, concat_ws, coalesce, lit
)
from pyspark.sql.types import StringType, IntegerType, DoubleType, BooleanType, TimestampType, DateType

logger = logging.getLogger(__name__)


class DataTransformerService:
    """Service for transforming and cleaning data"""
    
    def __init__(self):
        """Initialize the data transformer service"""
        pass
    
    async def transform_data_for_entity(self, df: DataFrame, entity: Dict[str, Any]) -> Optional[DataFrame]:
        """
        Transform data according to entity specifications
        
        Args:
            df: Source DataFrame
            entity: Entity definition with transformation rules
            
        Returns:
            Transformed DataFrame or None if failed
        """
        logger.info(f"Transforming data for entity {entity.get('name', 'unknown')}")
        
        try:
            transformed_df = df
            
            # Apply column-specific transformations
            for column_def in entity.get('column_details', []):
                col_name = column_def.get('name')
                col_type = column_def.get('data_type', 'string')
                
                if col_name not in transformed_df.columns:
                    continue
                
                # Apply type-specific transformations
                transformed_df = await self._apply_column_transformations(
                    transformed_df, col_name, col_type, column_def
                )
            
            # Apply entity-level transformations
            transformed_df = await self._apply_entity_transformations(transformed_df, entity)
            
            logger.info(f"Data transformation completed for entity {entity.get('name', 'unknown')}")
            return transformed_df
            
        except Exception as e:
            logger.error(f"Data transformation failed for entity {entity.get('name', 'unknown')}: {str(e)}")
            return None
    
    async def clean_data(self, df: DataFrame, entity: Dict[str, Any]) -> Optional[DataFrame]:
        """
        Clean data by removing/fixing common data quality issues
        
        Args:
            df: DataFrame to clean
            entity: Entity definition with cleaning rules
            
        Returns:
            Cleaned DataFrame or None if failed
        """
        logger.info(f"Cleaning data for entity {entity.get('name', 'unknown')}")
        
        try:
            cleaned_df = df
            
            # Remove completely empty rows
            cleaned_df = cleaned_df.dropna(how='all')
            
            # Apply column-specific cleaning
            for column_def in entity.get('column_details', []):
                col_name = column_def.get('name')
                col_type = column_def.get('data_type', 'string')
                
                if col_name not in cleaned_df.columns:
                    continue
                
                cleaned_df = await self._clean_column(cleaned_df, col_name, col_type, column_def)
            
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
    
    async def apply_business_rules(self, df: DataFrame, rules: List[Dict[str, Any]]) -> Optional[DataFrame]:
        """
        Apply business rules to the data
        
        Args:
            df: DataFrame to apply rules to
            rules: List of business rule definitions
            
        Returns:
            DataFrame with business rules applied or None if failed
        """
        logger.info(f"Applying {len(rules)} business rules")
        
        try:
            processed_df = df
            
            for rule in rules:
                rule_type = rule.get('type')
                rule_name = rule.get('name', 'unnamed_rule')
                
                logger.debug(f"Applying business rule: {rule_name} ({rule_type})")
                
                if rule_type == 'filter':
                    processed_df = await self._apply_filter_rule(processed_df, rule)
                elif rule_type == 'transform':
                    processed_df = await self._apply_transform_rule(processed_df, rule)
                elif rule_type == 'validation':
                    processed_df = await self._apply_validation_rule(processed_df, rule)
                else:
                    logger.warning(f"Unknown business rule type: {rule_type}")
            
            logger.info("Business rules application completed")
            return processed_df
            
        except Exception as e:
            logger.error(f"Business rules application failed: {str(e)}")
            return None
    
    async def _apply_column_transformations(self, df: DataFrame, col_name: str, col_type: str, column_def: Dict[str, Any]) -> DataFrame:
        """Apply transformations specific to a column"""
        try:
            transformed_df = df
            
            # String transformations
            if col_type.lower() in ['string', 'varchar', 'text']:
                # Trim whitespace
                transformed_df = transformed_df.withColumn(col_name, trim(col(col_name)))
                
                # Apply case transformations if specified
                case_transform = column_def.get('case_transform')
                if case_transform == 'upper':
                    transformed_df = transformed_df.withColumn(col_name, upper(col(col_name)))
                elif case_transform == 'lower':
                    transformed_df = transformed_df.withColumn(col_name, lower(col(col_name)))
                
                # Remove special characters if specified
                if column_def.get('remove_special_chars', False):
                    transformed_df = transformed_df.withColumn(
                        col_name, 
                        regexp_replace(col(col_name), r'[^\w\s]', '')
                    )
            
            # Numeric transformations
            elif col_type.lower() in ['integer', 'int', 'double', 'float', 'decimal']:
                # Handle negative values if not allowed
                if not column_def.get('allow_negative', True):
                    transformed_df = transformed_df.withColumn(
                        col_name,
                        when(col(col_name) < 0, 0).otherwise(col(col_name))
                    )
                
                # Apply min/max constraints
                min_value = column_def.get('min_value')
                max_value = column_def.get('max_value')
                
                if min_value is not None:
                    transformed_df = transformed_df.withColumn(
                        col_name,
                        when(col(col_name) < min_value, min_value).otherwise(col(col_name))
                    )
                
                if max_value is not None:
                    transformed_df = transformed_df.withColumn(
                        col_name,
                        when(col(col_name) > max_value, max_value).otherwise(col(col_name))
                    )
            
            # Date/timestamp transformations
            elif col_type.lower() in ['timestamp', 'datetime', 'date']:
                date_format = column_def.get('date_format')
                if date_format:
                    if col_type.lower() == 'date':
                        transformed_df = transformed_df.withColumn(
                            col_name, 
                            to_date(col(col_name), date_format)
                        )
                    else:
                        transformed_df = transformed_df.withColumn(
                            col_name, 
                            to_timestamp(col(col_name), date_format)
                        )
            
            return transformed_df
            
        except Exception as e:
            logger.error(f"Column transformation failed for {col_name}: {str(e)}")
            return df
    
    async def _clean_column(self, df: DataFrame, col_name: str, col_type: str, column_def: Dict[str, Any]) -> DataFrame:
        """Clean a specific column"""
        try:
            cleaned_df = df
            
            # Handle null values
            nullable = column_def.get('nullable', True)
            if not nullable:
                # Provide default values for non-nullable columns
                if col_type.lower() in ['integer', 'int', 'bigint', 'long']:
                    default_value = column_def.get('default_value', 0)
                    cleaned_df = cleaned_df.fillna({col_name: default_value})
                elif col_type.lower() in ['double', 'float', 'decimal']:
                    default_value = column_def.get('default_value', 0.0)
                    cleaned_df = cleaned_df.fillna({col_name: default_value})
                elif col_type.lower() in ['string', 'varchar', 'text']:
                    default_value = column_def.get('default_value', "")
                    cleaned_df = cleaned_df.fillna({col_name: default_value})
                elif col_type.lower() in ['boolean', 'bool']:
                    default_value = column_def.get('default_value', False)
                    cleaned_df = cleaned_df.fillna({col_name: default_value})
            
            # String-specific cleaning
            if col_type.lower() in ['string', 'varchar', 'text']:
                # Remove leading/trailing whitespace
                cleaned_df = cleaned_df.withColumn(col_name, trim(col(col_name)))
                
                # Replace empty strings with null if nullable
                if nullable:
                    cleaned_df = cleaned_df.withColumn(
                        col_name,
                        when(col(col_name) == "", None).otherwise(col(col_name))
                    )
                
                # Standardize common variations
                standardizations = column_def.get('standardizations', {})
                for old_value, new_value in standardizations.items():
                    cleaned_df = cleaned_df.withColumn(
                        col_name,
                        when(col(col_name) == old_value, new_value).otherwise(col(col_name))
                    )
            
            # Numeric cleaning
            elif col_type.lower() in ['integer', 'int', 'double', 'float', 'decimal']:
                # Handle NaN values
                cleaned_df = cleaned_df.withColumn(
                    col_name,
                    when(isnan(col(col_name)), None).otherwise(col(col_name))
                )
                
                # Handle infinite values
                cleaned_df = cleaned_df.withColumn(
                    col_name,
                    when(col(col_name).isNull() | isnan(col(col_name)), None).otherwise(col(col_name))
                )
            
            return cleaned_df
            
        except Exception as e:
            logger.error(f"Column cleaning failed for {col_name}: {str(e)}")
            return df
    
    async def _apply_entity_transformations(self, df: DataFrame, entity: Dict[str, Any]) -> DataFrame:
        """Apply entity-level transformations"""
        try:
            transformed_df = df
            
            # Add computed columns if specified
            computed_columns = entity.get('computed_columns', [])
            for computed_col in computed_columns:
                col_name = computed_col.get('name')
                expression = computed_col.get('expression')
                
                if col_name and expression:
                    # Simple expression evaluation (can be extended)
                    if expression.startswith('concat('):
                        # Handle concatenation
                        columns_to_concat = expression[7:-1].split(',')
                        columns_to_concat = [c.strip().strip('"\'') for c in columns_to_concat]
                        transformed_df = transformed_df.withColumn(
                            col_name,
                            concat_ws(' ', *[col(c) for c in columns_to_concat if c in df.columns])
                        )
            
            return transformed_df
            
        except Exception as e:
            logger.error(f"Entity transformation failed: {str(e)}")
            return df
    
    async def _apply_filter_rule(self, df: DataFrame, rule: Dict[str, Any]) -> DataFrame:
        """Apply a filter business rule"""
        try:
            condition = rule.get('condition')
            if not condition:
                return df
            
            # Simple condition parsing (can be extended for complex conditions)
            column = condition.get('column')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if not all([column, operator, value]):
                return df
            
            if operator == 'equals':
                return df.filter(col(column) == value)
            elif operator == 'not_equals':
                return df.filter(col(column) != value)
            elif operator == 'greater_than':
                return df.filter(col(column) > value)
            elif operator == 'less_than':
                return df.filter(col(column) < value)
            elif operator == 'contains':
                return df.filter(col(column).contains(value))
            elif operator == 'not_null':
                return df.filter(col(column).isNotNull())
            elif operator == 'is_null':
                return df.filter(col(column).isNull())
            
            return df
            
        except Exception as e:
            logger.error(f"Filter rule application failed: {str(e)}")
            return df
    
    async def _apply_transform_rule(self, df: DataFrame, rule: Dict[str, Any]) -> DataFrame:
        """Apply a transform business rule"""
        try:
            transformation = rule.get('transformation')
            if not transformation:
                return df
            
            target_column = transformation.get('target_column')
            transform_type = transformation.get('type')
            
            if not all([target_column, transform_type]):
                return df
            
            if transform_type == 'replace':
                old_value = transformation.get('old_value')
                new_value = transformation.get('new_value')
                return df.withColumn(
                    target_column,
                    when(col(target_column) == old_value, new_value).otherwise(col(target_column))
                )
            elif transform_type == 'calculate':
                expression = transformation.get('expression')
                # Simple calculation support (can be extended)
                if expression and '+' in expression:
                    parts = expression.split('+')
                    if len(parts) == 2:
                        col1, col2 = parts[0].strip(), parts[1].strip()
                        if col1 in df.columns and col2 in df.columns:
                            return df.withColumn(target_column, col(col1) + col(col2))
            
            return df
            
        except Exception as e:
            logger.error(f"Transform rule application failed: {str(e)}")
            return df
    
    async def _apply_validation_rule(self, df: DataFrame, rule: Dict[str, Any]) -> DataFrame:
        """Apply a validation business rule"""
        try:
            validation = rule.get('validation')
            if not validation:
                return df
            
            # For now, validation rules just log warnings
            # In the future, they could mark invalid rows or reject them
            column = validation.get('column')
            rule_type = validation.get('type')
            
            if rule_type == 'range_check':
                min_val = validation.get('min_value')
                max_val = validation.get('max_value')
                
                if min_val is not None and max_val is not None:
                    invalid_count = df.filter(
                        (col(column) < min_val) | (col(column) > max_val)
                    ).count()
                    
                    if invalid_count > 0:
                        logger.warning(f"Validation rule '{rule.get('name')}': {invalid_count} rows outside range [{min_val}, {max_val}]")
            
            return df
            
        except Exception as e:
            logger.error(f"Validation rule application failed: {str(e)}")
            return df
    
    def get_transformation_summary(self, original_df: DataFrame, transformed_df: DataFrame) -> Dict[str, Any]:
        """
        Get a summary of transformations applied
        
        Args:
            original_df: Original DataFrame
            transformed_df: Transformed DataFrame
            
        Returns:
            Dictionary with transformation summary
        """
        try:
            original_count = original_df.count()
            transformed_count = transformed_df.count()
            
            return {
                "original_row_count": original_count,
                "transformed_row_count": transformed_count,
                "rows_added": max(0, transformed_count - original_count),
                "rows_removed": max(0, original_count - transformed_count),
                "original_columns": len(original_df.columns),
                "transformed_columns": len(transformed_df.columns),
                "columns_added": len(set(transformed_df.columns) - set(original_df.columns)),
                "columns_removed": len(set(original_df.columns) - set(transformed_df.columns))
            }
            
        except Exception as e:
            logger.error(f"Failed to generate transformation summary: {str(e)}")
            return {}

