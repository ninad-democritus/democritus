"""
Unit tests for data processing services
"""

import pytest
import unittest.mock as mock
from unittest.mock import Mock, patch
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from app.data_processing.schema_validator_service import SchemaValidatorService
from app.data_processing.data_transformer_service import DataTransformerService
from app.data_processing.data_mapper_service import DataMapperService
from app.file_operations.models import FileInfo, EntityFileMatch
from datetime import datetime


class TestSchemaValidatorService:
    """Test cases for SchemaValidatorService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = SchemaValidatorService()
    
    def test_create_spark_schema(self):
        """Test creating Spark schema from entity"""
        entity = {
            "name": "users",
            "column_details": [
                {"name": "id", "data_type": "integer", "nullable": False},
                {"name": "name", "data_type": "string", "nullable": True},
                {"name": "email", "data_type": "string", "nullable": False}
            ]
        }
        
        schema = self.service.create_spark_schema(entity)
        
        assert isinstance(schema, StructType)
        assert len(schema.fields) == 3
        
        # Check field details
        id_field = schema.fields[0]
        assert id_field.name == "id"
        assert isinstance(id_field.dataType, IntegerType)
        assert not id_field.nullable
        
        name_field = schema.fields[1]
        assert name_field.name == "name"
        assert isinstance(name_field.dataType, StringType)
        assert name_field.nullable
    
    def test_create_iceberg_schema(self):
        """Test creating Iceberg schema from entity"""
        entity = {
            "name": "users",
            "column_details": [
                {"name": "id", "data_type": "integer", "nullable": False},
                {"name": "name", "data_type": "string", "nullable": True}
            ]
        }
        
        schema = self.service.create_iceberg_schema(entity)
        
        assert len(schema.fields) == 2
        
        # Check field details
        id_field = schema.fields[0]
        assert id_field.name == "id"
        assert id_field.field_id == 1
        assert id_field.required is True
        
        name_field = schema.fields[1]
        assert name_field.name == "name"
        assert name_field.field_id == 2
        assert name_field.required is False
    
    def test_validate_schema_compatibility_compatible(self):
        """Test schema compatibility validation - compatible schemas"""
        source_schema = StructType([
            StructField("id", IntegerType(), False),
            StructField("name", StringType(), True)
        ])
        
        target_schema = StructType([
            StructField("id", IntegerType(), False),
            StructField("name", StringType(), True)
        ])
        
        is_compatible, issues = self.service.validate_schema_compatibility(source_schema, target_schema)
        
        assert is_compatible is True
        assert len(issues) == 0
    
    def test_validate_schema_compatibility_missing_required_field(self):
        """Test schema compatibility validation - missing required field"""
        source_schema = StructType([
            StructField("name", StringType(), True)
        ])
        
        target_schema = StructType([
            StructField("id", IntegerType(), False),  # Required field missing in source
            StructField("name", StringType(), True)
        ])
        
        is_compatible, issues = self.service.validate_schema_compatibility(source_schema, target_schema)
        
        assert is_compatible is False
        assert any("Required field 'id' missing" in issue for issue in issues)
    
    def test_validate_schema_compatibility_extra_fields(self):
        """Test schema compatibility validation - extra fields in source"""
        source_schema = StructType([
            StructField("id", IntegerType(), False),
            StructField("name", StringType(), True),
            StructField("extra", StringType(), True)  # Extra field
        ])
        
        target_schema = StructType([
            StructField("id", IntegerType(), False),
            StructField("name", StringType(), True)
        ])
        
        is_compatible, issues = self.service.validate_schema_compatibility(source_schema, target_schema)
        
        assert is_compatible is True  # Extra fields don't make it incompatible
        assert any("Extra fields in source schema" in issue for issue in issues)
    
    def test_map_to_spark_type(self):
        """Test mapping string types to Spark types"""
        # Test various type mappings
        assert isinstance(self.service._map_to_spark_type("string"), StringType)
        assert isinstance(self.service._map_to_spark_type("integer"), IntegerType)
        assert isinstance(self.service._map_to_spark_type("varchar"), StringType)
        assert isinstance(self.service._map_to_spark_type("unknown_type"), StringType)  # Default
    
    def test_get_schema_summary(self):
        """Test getting schema summary"""
        schema = StructType([
            StructField("id", IntegerType(), False),
            StructField("name", StringType(), True),
            StructField("email", StringType(), False)
        ])
        
        summary = self.service.get_schema_summary(schema)
        
        assert summary["total_fields"] == 3
        assert summary["nullable_fields"] == 1
        assert summary["required_fields"] == 2
        assert len(summary["fields"]) == 3
        assert summary["fields"][0]["name"] == "id"
        assert summary["fields"][0]["nullable"] is False


class TestDataTransformerService:
    """Test cases for DataTransformerService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = DataTransformerService()
    
    @pytest.mark.asyncio
    async def test_transform_data_for_entity(self):
        """Test transforming data for entity"""
        mock_df = Mock()
        mock_df.columns = ["id", "name"]
        
        entity = {
            "name": "users",
            "column_details": [
                {"name": "id", "data_type": "integer"},
                {"name": "name", "data_type": "string", "case_transform": "upper"}
            ]
        }
        
        with patch.object(self.service, '_apply_column_transformations', return_value=mock_df), \
             patch.object(self.service, '_apply_entity_transformations', return_value=mock_df):
            
            result = await self.service.transform_data_for_entity(mock_df, entity)
            
            assert result is mock_df
    
    @pytest.mark.asyncio
    async def test_clean_data(self):
        """Test cleaning data"""
        mock_df = Mock()
        mock_df.columns = ["id", "name"]
        mock_df.dropna.return_value = mock_df
        mock_df.dropDuplicates.return_value = mock_df
        mock_df.count.side_effect = [100, 95]  # Before and after deduplication
        
        entity = {
            "name": "users",
            "column_details": [
                {"name": "id", "data_type": "integer", "nullable": False},
                {"name": "name", "data_type": "string", "nullable": True}
            ]
        }
        
        with patch.object(self.service, '_clean_column', return_value=mock_df):
            result = await self.service.clean_data(mock_df, entity)
            
            assert result is mock_df
            mock_df.dropna.assert_called_with(how='all')
            mock_df.dropDuplicates.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_business_rules_filter(self):
        """Test applying filter business rules"""
        mock_df = Mock()
        mock_df.filter.return_value = mock_df
        
        rules = [
            {
                "type": "filter",
                "name": "age_filter",
                "condition": {
                    "column": "age",
                    "operator": "greater_than",
                    "value": 18
                }
            }
        ]
        
        with patch.object(self.service, '_apply_filter_rule', return_value=mock_df):
            result = await self.service.apply_business_rules(mock_df, rules)
            
            assert result is mock_df
    
    @pytest.mark.asyncio
    async def test_apply_column_transformations_string(self):
        """Test applying string column transformations"""
        mock_df = Mock()
        mock_df.withColumn.return_value = mock_df
        
        column_def = {
            "name": "name",
            "data_type": "string",
            "case_transform": "upper",
            "remove_special_chars": True
        }
        
        result = await self.service._apply_column_transformations(mock_df, "name", "string", column_def)
        
        assert result is mock_df
        # Should have called withColumn multiple times for different transformations
        assert mock_df.withColumn.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_apply_column_transformations_numeric(self):
        """Test applying numeric column transformations"""
        mock_df = Mock()
        mock_df.withColumn.return_value = mock_df
        
        column_def = {
            "name": "age",
            "data_type": "integer",
            "allow_negative": False,
            "min_value": 0,
            "max_value": 120
        }
        
        result = await self.service._apply_column_transformations(mock_df, "age", "integer", column_def)
        
        assert result is mock_df
        # Should have called withColumn for negative handling, min/max constraints
        assert mock_df.withColumn.call_count >= 3
    
    def test_get_transformation_summary(self):
        """Test getting transformation summary"""
        original_df = Mock()
        original_df.count.return_value = 100
        original_df.columns = ["col1", "col2"]
        
        transformed_df = Mock()
        transformed_df.count.return_value = 95
        transformed_df.columns = ["col1", "col2", "col3"]
        
        summary = self.service.get_transformation_summary(original_df, transformed_df)
        
        assert summary["original_row_count"] == 100
        assert summary["transformed_row_count"] == 95
        assert summary["rows_removed"] == 5
        assert summary["original_columns"] == 2
        assert summary["transformed_columns"] == 3
        assert summary["columns_added"] == 1


class TestDataMapperService:
    """Test cases for DataMapperService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = DataMapperService()
    
    @pytest.mark.asyncio
    async def test_map_entities_to_files(self):
        """Test mapping entities to files"""
        entities = [
            {"id": "users", "name": "Users"},
            {"id": "products", "name": "Products"}
        ]
        
        files = [
            FileInfo("users.csv", "uploads", 1024, datetime.now()),
            FileInfo("products.xlsx", "uploads", 2048, datetime.now()),
            FileInfo("orders.json", "uploads", 512, datetime.now())
        ]
        
        with patch.object(self.service, 'fuzzy_match_entity_files') as mock_match:
            # Mock return values for each entity
            mock_match.side_effect = [
                ([files[0]], {"users.csv": 0.9}),  # Users entity matches users.csv
                ([files[1]], {"products.xlsx": 0.8})  # Products entity matches products.xlsx
            ]
            
            mappings = await self.service.map_entities_to_files(entities, files)
            
            assert len(mappings) == 2
            assert "users" in mappings
            assert "products" in mappings
            assert mappings["users"].matched_files[0].file_name == "users.csv"
            assert mappings["products"].matched_files[0].file_name == "products.xlsx"
    
    @pytest.mark.asyncio
    async def test_fuzzy_match_entity_files(self):
        """Test fuzzy matching entity files"""
        entity = {"id": "users", "name": "Users"}
        files = [
            FileInfo("users.csv", "uploads", 1024, datetime.now()),
            FileInfo("user_data.xlsx", "uploads", 2048, datetime.now()),
            FileInfo("products.json", "uploads", 512, datetime.now())
        ]
        
        matched_files, confidence_scores = await self.service.fuzzy_match_entity_files(entity, files)
        
        # Should match users.csv and user_data.xlsx, but not products.json
        assert len(matched_files) >= 1
        assert "users.csv" in confidence_scores
        assert confidence_scores["users.csv"] > 0.8  # High confidence for exact match
        
        # Files should be sorted by confidence (highest first)
        if len(matched_files) > 1:
            assert confidence_scores[matched_files[0].file_name] >= confidence_scores[matched_files[1].file_name]
    
    def test_calculate_match_confidence(self):
        """Test calculating match confidence"""
        # Exact match
        confidence = self.service.calculate_match_confidence("users", "users.csv")
        assert confidence == 1.0
        
        # Entity name contained in file name
        confidence = self.service.calculate_match_confidence("user", "users.csv")
        assert confidence == 0.9
        
        # File name contained in entity name
        confidence = self.service.calculate_match_confidence("users", "user.csv")
        assert confidence == 0.8
        
        # Similar names
        confidence = self.service.calculate_match_confidence("user_data", "user_info.csv")
        assert confidence > 0.3
        
        # No match
        confidence = self.service.calculate_match_confidence("orders", "users.csv")
        assert confidence < 0.3
    
    def test_get_entity_alternative_names(self):
        """Test getting alternative names for entity"""
        entity = {"id": "user_data", "name": "Users"}
        
        alternatives = self.service._get_entity_alternative_names(entity)
        
        assert "users" in alternatives
        assert "user_data" in alternatives
        # Should include plural/singular variations
        assert any("user" in alt for alt in alternatives)
        # Should include variations with different separators
        assert any("user data" in alt or "user-data" in alt for alt in alternatives)
    
    def test_normalize_name(self):
        """Test name normalization"""
        # Test various normalizations
        assert self.service._normalize_name("User Data.csv") == "user_data"
        assert self.service._normalize_name("user-info.xlsx") == "user_info"
        assert self.service._normalize_name("PRODUCTS_TABLE") == "products_table"
        assert self.service._normalize_name("  spaced  name  ") == "spaced_name"
        assert self.service._normalize_name("special@chars#removed") == "specialcharsremoved"
    
    @pytest.mark.asyncio
    async def test_validate_entity_file_mappings(self):
        """Test validating entity file mappings"""
        file1 = FileInfo("users.csv", "uploads", 1024, datetime.now())
        file2 = FileInfo("products.xlsx", "uploads", 2048, datetime.now())
        
        mappings = {
            "users": EntityFileMatch("Users", "users", [file1], {"users.csv": 0.9}),
            "products": EntityFileMatch("Products", "products", [file2], {"products.xlsx": 0.4}),  # Low confidence
            "orders": EntityFileMatch("Orders", "orders", [], {})  # No files
        }
        
        validation = await self.service.validate_entity_file_mappings(mappings)
        
        assert validation["total_entities"] == 3
        assert validation["mapped_entities"] == 2
        assert len(validation["unmapped_entities"]) == 1
        assert len(validation["low_confidence_mappings"]) == 1
        assert validation["low_confidence_mappings"][0]["entity_id"] == "products"
        assert validation["unmapped_entities"][0]["entity_id"] == "orders"
    
    @pytest.mark.asyncio
    async def test_suggest_entity_file_mappings(self):
        """Test suggesting entity file mappings"""
        unmapped_entities = [
            {"id": "customers", "name": "Customers"}
        ]
        
        unmatched_files = [
            FileInfo("customer_data.csv", "uploads", 1024, datetime.now()),
            FileInfo("client_info.xlsx", "uploads", 2048, datetime.now())
        ]
        
        suggestions = await self.service.suggest_entity_file_mappings(unmapped_entities, unmatched_files)
        
        assert len(suggestions) == 1
        assert suggestions[0]["entity_id"] == "customers"
        assert len(suggestions[0]["suggested_files"]) > 0
        # Should suggest customer_data.csv with higher confidence than client_info.xlsx
        assert suggestions[0]["suggested_files"][0]["confidence"] > 0.2
    
    def test_get_mapping_statistics(self):
        """Test getting mapping statistics"""
        file1 = FileInfo("users.csv", "uploads", 1024, datetime.now())
        file2 = FileInfo("products.xlsx", "uploads", 2048, datetime.now())
        
        mappings = {
            "users": EntityFileMatch("Users", "users", [file1], {"users.csv": 0.9}),
            "products": EntityFileMatch("Products", "products", [file2], {"products.xlsx": 0.6}),
            "orders": EntityFileMatch("Orders", "orders", [], {})
        }
        
        stats = self.service.get_mapping_statistics(mappings)
        
        assert stats["total_entities"] == 3
        assert stats["mapped_entities"] == 2
        assert stats["unmapped_entities"] == 1
        assert stats["mapping_rate"] == (2/3) * 100
        assert stats["total_matched_files"] == 2
        assert stats["average_confidence"] == 0.75  # (0.9 + 0.6) / 2
        assert stats["confidence_distribution"]["high_confidence"] == 1  # 0.9 >= 0.8
        assert stats["confidence_distribution"]["medium_confidence"] == 1  # 0.6 in [0.5, 0.8)
        assert stats["confidence_distribution"]["low_confidence"] == 0

