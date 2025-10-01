"""
Unit tests for catalog operations services
"""

import pytest
import unittest.mock as mock
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.catalog_operations.iceberg_catalog_service import IcebergCatalogService, TableInfo
from app.catalog_operations.iceberg_writer_service import IcebergWriterService, WriteResult
from app.catalog_operations.nessie_transaction_service import NessieTransactionService, BranchStatus


class TestTableInfo:
    """Test cases for TableInfo model"""
    
    def test_table_info_creation(self):
        """Test creating TableInfo object"""
        mock_schema = Mock()
        mock_schema.fields = [
            Mock(field_id=1, name="id", field_type="int", required=True),
            Mock(field_id=2, name="name", field_type="string", required=False)
        ]
        
        table_info = TableInfo(
            name="test_table",
            schema=mock_schema,
            location="s3://bucket/table/",
            properties={"format": "parquet"}
        )
        
        assert table_info.name == "test_table"
        assert table_info.schema is mock_schema
        assert table_info.location == "s3://bucket/table/"
        assert table_info.properties["format"] == "parquet"
        assert table_info.created_at is not None
    
    def test_table_info_to_dict(self):
        """Test converting TableInfo to dictionary"""
        mock_schema = Mock()
        mock_schema.fields = [
            Mock(field_id=1, name="id", field_type="int", required=True),
            Mock(field_id=2, name="name", field_type="string", required=False)
        ]
        
        table_info = TableInfo("test_table", mock_schema, "s3://bucket/table/")
        result = table_info.to_dict()
        
        assert result["name"] == "test_table"
        assert result["location"] == "s3://bucket/table/"
        assert "created_at" in result
        assert "schema" in result
        assert len(result["schema"]["fields"]) == 2


class TestIcebergCatalogService:
    """Test cases for IcebergCatalogService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = IcebergCatalogService()
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    def test_get_catalog(self, mock_load_catalog):
        """Test getting catalog instance"""
        mock_catalog = Mock()
        mock_load_catalog.return_value = mock_catalog
        
        catalog = self.service._get_catalog()
        
        assert catalog is mock_catalog
        mock_load_catalog.assert_called_once_with("iceberg_catalog", **self.service._catalog_config)
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_ensure_table_exists_table_exists(self, mock_load_catalog):
        """Test ensuring table exists when table already exists"""
        mock_catalog = Mock()
        mock_load_catalog.return_value = mock_catalog
        
        with patch.object(self.service, '_table_exists', return_value=True):
            mock_schema = Mock()
            result = await self.service.ensure_table_exists("test_table", mock_schema)
            
            assert result is True
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_ensure_table_exists_creates_table(self, mock_load_catalog):
        """Test ensuring table exists when table needs to be created"""
        mock_catalog = Mock()
        mock_load_catalog.return_value = mock_catalog
        
        with patch.object(self.service, '_table_exists', return_value=False), \
             patch.object(self.service, 'create_table', return_value=True):
            
            mock_schema = Mock()
            result = await self.service.ensure_table_exists("test_table", mock_schema)
            
            assert result is True
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_create_table_success(self, mock_load_catalog):
        """Test successful table creation"""
        mock_catalog = Mock()
        mock_table = Mock()
        mock_catalog.create_table.return_value = mock_table
        mock_load_catalog.return_value = mock_catalog
        
        mock_schema = Mock()
        result = await self.service.create_table("test_table", mock_schema)
        
        assert result is True
        mock_catalog.create_table.assert_called_once()
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_create_table_already_exists(self, mock_load_catalog):
        """Test creating table when it already exists"""
        from pyiceberg.exceptions import TableAlreadyExistsError
        
        mock_catalog = Mock()
        mock_catalog.create_table.side_effect = TableAlreadyExistsError("Table exists")
        mock_load_catalog.return_value = mock_catalog
        
        mock_schema = Mock()
        result = await self.service.create_table("test_table", mock_schema)
        
        assert result is True  # Should return True even if table exists
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_get_table_info_success(self, mock_load_catalog):
        """Test getting table info successfully"""
        mock_catalog = Mock()
        mock_table = Mock()
        mock_table.schema.return_value = Mock()
        mock_table.location.return_value = "s3://bucket/table/"
        mock_table.properties = {"format": "parquet"}
        mock_catalog.load_table.return_value = mock_table
        mock_load_catalog.return_value = mock_catalog
        
        result = await self.service.get_table_info("test_table")
        
        assert result is not None
        assert isinstance(result, TableInfo)
        assert result.name == "test_table"
        assert result.location == "s3://bucket/table/"
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_get_table_info_not_found(self, mock_load_catalog):
        """Test getting table info when table doesn't exist"""
        from pyiceberg.exceptions import NoSuchTableError
        
        mock_catalog = Mock()
        mock_catalog.load_table.side_effect = NoSuchTableError("Table not found")
        mock_load_catalog.return_value = mock_catalog
        
        result = await self.service.get_table_info("nonexistent_table")
        
        assert result is None
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_drop_table_success(self, mock_load_catalog):
        """Test successful table drop"""
        mock_catalog = Mock()
        mock_load_catalog.return_value = mock_catalog
        
        result = await self.service.drop_table("test_table")
        
        assert result is True
        mock_catalog.drop_table.assert_called_once_with("test_table", purge=True)
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_drop_table_not_found(self, mock_load_catalog):
        """Test dropping table when it doesn't exist"""
        from pyiceberg.exceptions import NoSuchTableError
        
        mock_catalog = Mock()
        mock_catalog.drop_table.side_effect = NoSuchTableError("Table not found")
        mock_load_catalog.return_value = mock_catalog
        
        result = await self.service.drop_table("nonexistent_table")
        
        assert result is True  # Should return True even if table doesn't exist
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_list_tables(self, mock_load_catalog):
        """Test listing tables"""
        mock_catalog = Mock()
        mock_catalog.list_tables.return_value = ["table1", "table2", "table3"]
        mock_load_catalog.return_value = mock_catalog
        
        tables = await self.service.list_tables("default")
        
        assert len(tables) == 3
        assert "table1" in tables
        mock_catalog.list_tables.assert_called_once_with("default")
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_table_exists_true(self, mock_load_catalog):
        """Test checking if table exists - exists"""
        mock_catalog = Mock()
        mock_catalog.load_table.return_value = Mock()
        mock_load_catalog.return_value = mock_catalog
        
        result = await self.service.table_exists("test_table")
        
        assert result is True
    
    @patch('app.catalog_operations.iceberg_catalog_service.load_catalog')
    @pytest.mark.asyncio
    async def test_table_exists_false(self, mock_load_catalog):
        """Test checking if table exists - doesn't exist"""
        from pyiceberg.exceptions import NoSuchTableError
        
        mock_catalog = Mock()
        mock_catalog.load_table.side_effect = NoSuchTableError("Table not found")
        mock_load_catalog.return_value = mock_catalog
        
        result = await self.service.table_exists("nonexistent_table")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cleanup_failed_tables(self):
        """Test cleaning up failed tables"""
        table_names = ["table1", "table2", "table3"]
        
        with patch.object(self.service, 'table_exists') as mock_exists, \
             patch.object(self.service, 'drop_table') as mock_drop:
            
            # Mock table existence and drop results
            mock_exists.side_effect = [True, False, True]  # table1 and table3 exist
            mock_drop.side_effect = [True, True]  # Both drops succeed
            
            results = await self.service.cleanup_failed_tables(table_names)
            
            assert len(results) == 3
            assert results["table1"] is True
            assert results["table2"] is True  # Doesn't exist, considered cleaned
            assert results["table3"] is True
            
            # Should only call drop_table for existing tables
            assert mock_drop.call_count == 2
    
    def test_get_catalog_info(self):
        """Test getting catalog information"""
        info = self.service.get_catalog_info()
        
        assert info["catalog_type"] == "rest"
        assert info["catalog_uri"] == "http://iceberg-rest:8181"
        assert info["s3_endpoint"] == "http://minio:9000"
        assert "initialized" in info


class TestWriteResult:
    """Test cases for WriteResult model"""
    
    def test_write_result_creation(self):
        """Test creating WriteResult object"""
        result = WriteResult(
            success=True,
            table_name="test_table",
            records_written=100,
            duration_seconds=5.5
        )
        
        assert result.success is True
        assert result.table_name == "test_table"
        assert result.records_written == 100
        assert result.duration_seconds == 5.5
        assert result.error_message is None
        assert result.timestamp is not None
    
    def test_write_result_to_dict(self):
        """Test converting WriteResult to dictionary"""
        result = WriteResult(False, "test_table", 0, "Error occurred", 2.0)
        result_dict = result.to_dict()
        
        assert result_dict["success"] is False
        assert result_dict["table_name"] == "test_table"
        assert result_dict["records_written"] == 0
        assert result_dict["error_message"] == "Error occurred"
        assert result_dict["duration_seconds"] == 2.0
        assert "timestamp" in result_dict


class TestIcebergWriterService:
    """Test cases for IcebergWriterService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = IcebergWriterService()
    
    @patch('app.catalog_operations.iceberg_writer_service.SparkSessionManager')
    @pytest.mark.asyncio
    async def test_write_data_to_table_success(self, mock_spark_manager):
        """Test successful data write"""
        mock_df = Mock()
        mock_df.count.return_value = 100
        mock_df.writeTo.return_value.append.return_value = None
        
        mock_spark = Mock()
        mock_spark_manager.get_session.return_value = mock_spark
        
        with patch.object(self.service.catalog_service, 'table_exists', return_value=True):
            result = await self.service.write_data_to_table(mock_df, "test_table", "append")
            
            assert result.success is True
            assert result.records_written == 100
            assert result.table_name == "test_table"
            assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_write_data_to_table_none_dataframe(self):
        """Test writing None DataFrame"""
        result = await self.service.write_data_to_table(None, "test_table")
        
        assert result.success is False
        assert result.error_message == "DataFrame is None"
    
    @pytest.mark.asyncio
    async def test_write_data_to_table_empty_dataframe(self):
        """Test writing empty DataFrame"""
        mock_df = Mock()
        mock_df.count.return_value = 0
        
        result = await self.service.write_data_to_table(mock_df, "test_table")
        
        assert result.success is True
        assert result.records_written == 0
        assert result.error_message == "DataFrame is empty"
    
    @pytest.mark.asyncio
    async def test_write_data_to_table_table_not_exists(self):
        """Test writing to non-existent table"""
        mock_df = Mock()
        mock_df.count.return_value = 100
        
        with patch.object(self.service.catalog_service, 'table_exists', return_value=False):
            result = await self.service.write_data_to_table(mock_df, "nonexistent_table")
            
            assert result.success is False
            assert "does not exist" in result.error_message
    
    @pytest.mark.asyncio
    async def test_write_data_to_table_unsupported_mode(self):
        """Test writing with unsupported mode"""
        mock_df = Mock()
        mock_df.count.return_value = 100
        
        with patch.object(self.service.catalog_service, 'table_exists', return_value=True):
            result = await self.service.write_data_to_table(mock_df, "test_table", "unsupported_mode")
            
            assert result.success is False
            assert "Unsupported write mode" in result.error_message
    
    @pytest.mark.asyncio
    async def test_append_data_to_table(self):
        """Test appending data to table"""
        mock_df = Mock()
        
        with patch.object(self.service, 'write_data_to_table') as mock_write:
            mock_write.return_value = WriteResult(True, "test_table", 100)
            
            result = await self.service.append_data_to_table(mock_df, "test_table")
            
            assert result.success is True
            mock_write.assert_called_once_with(mock_df, "test_table", write_mode="append")
    
    @pytest.mark.asyncio
    async def test_validate_write_success_within_tolerance(self):
        """Test validating write success within tolerance"""
        with patch.object(self.service.catalog_service, 'get_table_statistics') as mock_stats:
            mock_stats.return_value = {"row_count": 102}  # 2% difference from expected 100
            
            result = await self.service.validate_write_success("test_table", 100, tolerance=0.05)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_write_success_outside_tolerance(self):
        """Test validating write success outside tolerance"""
        with patch.object(self.service.catalog_service, 'get_table_statistics') as mock_stats:
            mock_stats.return_value = {"row_count": 110}  # 10% difference from expected 100
            
            result = await self.service.validate_write_success("test_table", 100, tolerance=0.05)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_write_success_no_stats(self):
        """Test validating write success when stats unavailable"""
        with patch.object(self.service.catalog_service, 'get_table_statistics') as mock_stats:
            mock_stats.return_value = None
            
            result = await self.service.validate_write_success("test_table", 100)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_batch_write_data(self):
        """Test batch writing data"""
        mock_df1 = Mock()
        mock_df2 = Mock()
        
        data_batches = [
            {"df": mock_df1, "table_name": "table1", "write_mode": "append"},
            {"df": mock_df2, "table_name": "table2", "write_mode": "overwrite"}
        ]
        
        with patch.object(self.service, 'write_data_to_table') as mock_write:
            mock_write.side_effect = [
                WriteResult(True, "table1", 100),
                WriteResult(True, "table2", 50)
            ]
            
            results = await self.service.batch_write_data(data_batches)
            
            assert len(results) == 2
            assert results["table1"].success is True
            assert results["table2"].success is True
            assert mock_write.call_count == 2
    
    def test_get_write_statistics(self):
        """Test getting write statistics"""
        results = [
            WriteResult(True, "table1", 100, duration_seconds=2.0),
            WriteResult(True, "table2", 50, duration_seconds=1.0),
            WriteResult(False, "table3", 0, "Error occurred", 0.5)
        ]
        
        stats = self.service.get_write_statistics(results)
        
        assert stats["total_operations"] == 3
        assert stats["successful_operations"] == 2
        assert stats["failed_operations"] == 1
        assert stats["success_rate"] == (2/3) * 100
        assert stats["total_records_written"] == 150
        assert stats["total_duration_seconds"] == 3.5
        assert stats["average_duration_seconds"] == 3.5 / 3
        assert "table3" in stats["failed_tables"]


class TestBranchStatus:
    """Test cases for BranchStatus model"""
    
    def test_branch_status_creation(self):
        """Test creating BranchStatus object"""
        status = BranchStatus(
            name="test_branch",
            hash="abc123",
            exists=True,
            created_at=datetime.now(),
            commit_count=5
        )
        
        assert status.name == "test_branch"
        assert status.hash == "abc123"
        assert status.exists is True
        assert status.commit_count == 5
    
    def test_branch_status_to_dict(self):
        """Test converting BranchStatus to dictionary"""
        created_at = datetime.now()
        status = BranchStatus("test_branch", "abc123", True, created_at, 5)
        result = status.to_dict()
        
        assert result["name"] == "test_branch"
        assert result["hash"] == "abc123"
        assert result["exists"] is True
        assert result["created_at"] == created_at.isoformat()
        assert result["commit_count"] == 5


class TestNessieTransactionService:
    """Test cases for NessieTransactionService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = NessieTransactionService("http://test-nessie:19120/api/v1")
    
    @patch('requests.Session.get')
    @patch('requests.Session.put')
    @pytest.mark.asyncio
    async def test_create_branch_success(self, mock_put, mock_get):
        """Test successful branch creation"""
        # Mock getting source branch
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"hash": "source_hash"}
        
        # Mock branch creation
        mock_put.return_value.status_code = 201
        
        result = await self.service.create_branch("test_branch", "main")
        
        assert result is True
        mock_get.assert_called_once()
        mock_put.assert_called_once()
    
    @patch('requests.Session.get')
    @pytest.mark.asyncio
    async def test_create_branch_source_not_found(self, mock_get):
        """Test branch creation when source branch not found"""
        mock_get.return_value.status_code = 404
        
        result = await self.service.create_branch("test_branch", "nonexistent")
        
        assert result is False
    
    @patch('requests.Session.get')
    @patch('requests.Session.post')
    @pytest.mark.asyncio
    async def test_merge_branch_success(self, mock_post, mock_get):
        """Test successful branch merge"""
        # Mock getting branch
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"hash": "branch_hash"}
        
        # Mock merge
        mock_post.return_value.status_code = 200
        
        result = await self.service.merge_branch("test_branch", "main")
        
        assert result is True
        mock_get.assert_called_once()
        mock_post.assert_called_once()
    
    @patch('requests.Session.get')
    @pytest.mark.asyncio
    async def test_merge_branch_not_found(self, mock_get):
        """Test merging non-existent branch"""
        mock_get.return_value.status_code = 404
        
        result = await self.service.merge_branch("nonexistent_branch", "main")
        
        assert result is False
    
    @patch('requests.Session.delete')
    @pytest.mark.asyncio
    async def test_delete_branch_success(self, mock_delete):
        """Test successful branch deletion"""
        mock_delete.return_value.status_code = 200
        
        result = await self.service.delete_branch("test_branch")
        
        assert result is True
        mock_delete.assert_called_once()
    
    @patch('requests.Session.delete')
    @pytest.mark.asyncio
    async def test_delete_branch_not_found(self, mock_delete):
        """Test deleting non-existent branch"""
        mock_delete.return_value.status_code = 404
        
        result = await self.service.delete_branch("nonexistent_branch")
        
        assert result is True  # Should return True even if branch doesn't exist
    
    @patch('requests.Session.get')
    def test_get_branch_status_exists(self, mock_get):
        """Test getting status of existing branch"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"hash": "branch_hash"}
        
        status = self.service.get_branch_status("test_branch")
        
        assert status.name == "test_branch"
        assert status.hash == "branch_hash"
        assert status.exists is True
    
    @patch('requests.Session.get')
    def test_get_branch_status_not_exists(self, mock_get):
        """Test getting status of non-existent branch"""
        mock_get.return_value.status_code = 404
        
        status = self.service.get_branch_status("nonexistent_branch")
        
        assert status.name == "nonexistent_branch"
        assert status.hash == ""
        assert status.exists is False
    
    @patch('requests.Session.get')
    @pytest.mark.asyncio
    async def test_list_branches(self, mock_get):
        """Test listing branches"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "references": [
                {"type": "BRANCH", "name": "main"},
                {"type": "BRANCH", "name": "feature1"},
                {"type": "TAG", "name": "v1.0"}  # Should be filtered out
            ]
        }
        
        branches = await self.service.list_branches()
        
        assert len(branches) == 2
        assert "main" in branches
        assert "feature1" in branches
        assert "v1.0" not in branches  # Tags should be filtered out
    
    @pytest.mark.asyncio
    async def test_create_transaction_branch(self):
        """Test creating transaction branch"""
        with patch.object(self.service, 'create_branch', return_value=True):
            branch_name = await self.service.create_transaction_branch("job123")
            
            assert branch_name == "transaction-job123"
    
    @pytest.mark.asyncio
    async def test_commit_transaction(self):
        """Test committing transaction"""
        with patch.object(self.service, 'merge_branch', return_value=True), \
             patch.object(self.service, 'delete_branch', return_value=True):
            
            result = await self.service.commit_transaction("transaction-job123")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_rollback_transaction(self):
        """Test rolling back transaction"""
        with patch.object(self.service, 'delete_branch', return_value=True):
            result = await self.service.rollback_transaction("transaction-job123")
            
            assert result is True
    
    @patch('requests.Session.get')
    def test_test_connection_success(self, mock_get):
        """Test successful connection test"""
        mock_get.return_value.status_code = 200
        
        result = self.service.test_connection()
        
        assert result is True
    
    @patch('requests.Session.get')
    def test_test_connection_failure(self, mock_get):
        """Test failed connection test"""
        mock_get.return_value.status_code = 500
        
        result = self.service.test_connection()
        
        assert result is False
    
    def test_get_service_info(self):
        """Test getting service information"""
        with patch.object(self.service, 'test_connection', return_value=True):
            info = self.service.get_service_info()
            
            assert info["nessie_uri"] == "http://test-nessie:19120/api/v1"
            assert info["connected"] is True
            assert info["service_status"] == "available"

