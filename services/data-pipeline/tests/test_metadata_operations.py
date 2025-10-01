"""
Unit tests for metadata operations services
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import the services to test
from app.metadata_operations.metadata_service import MetadataService
from app.metadata_operations.openmetadata_store import OpenMetadataStore
from app.metadata_operations.file_metadata_store import FileMetadataStore
from app.metadata_operations.authentication.openmetadata_auth import OpenMetadataAuth
from app.metadata_operations.models import (
    MetadataStorageRequest,
    MetadataEntity,
    MetadataRelationship,
    AuthenticationResult,
    AuthenticationType
)


class TestMetadataService:
    """Test cases for MetadataService"""
    
    @pytest.fixture
    def metadata_service(self):
        """Create a MetadataService instance for testing"""
        return MetadataService()
    
    @pytest.mark.asyncio
    async def test_initialization(self, metadata_service):
        """Test service initialization"""
        assert metadata_service.primary_store_type == "openmetadata"
        assert metadata_service.enable_fallback is True
        assert not metadata_service.initialized
    
    @pytest.mark.asyncio
    async def test_store_schema_metadata_success(self, metadata_service):
        """Test successful metadata storage"""
        # Mock the primary store
        mock_store = AsyncMock()
        mock_store.initialize.return_value = True
        mock_store.store_metadata.return_value = Mock(
            success=True,
            stored_entities=2,
            stored_relationships=1,
            stored_lineage=0,
            errors=None
        )
        
        metadata_service.primary_store = mock_store
        metadata_service.initialized = True
        
        # Test data
        schema_data = {
            'entities': [
                {
                    'name': 'users',
                    'description': 'User table',
                    'entity_type': 'table',
                    'column_details': [
                        {'name': 'id', 'type': 'int', 'nullable': False},
                        {'name': 'name', 'type': 'string', 'nullable': True}
                    ]
                }
            ],
            'relationships': [
                {
                    'from_entity': 'users',
                    'to_entity': 'orders',
                    'from_column': 'id',
                    'to_column': 'user_id',
                    'relationship_type': 'foreign_key'
                }
            ]
        }
        
        result = await metadata_service.store_schema_metadata(
            "run_123", "job_456", schema_data
        )
        
        assert result.success
        assert result.stored_entities == 2
        assert result.stored_relationships == 1
        mock_store.store_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_schema_metadata_fallback(self, metadata_service):
        """Test metadata storage with fallback when primary fails"""
        # Mock primary store to fail
        mock_primary = AsyncMock()
        mock_primary.initialize.return_value = True
        mock_primary.store_metadata.side_effect = Exception("Primary store failed")
        
        # Mock fallback store to succeed
        mock_fallback = AsyncMock()
        mock_fallback.store_metadata.return_value = Mock(
            success=True,
            stored_entities=1,
            stored_relationships=0,
            stored_lineage=0,
            fallback_used=True
        )
        
        metadata_service.primary_store = mock_primary
        metadata_service.fallback_store = mock_fallback
        metadata_service.initialized = True
        
        schema_data = {'entities': [], 'relationships': []}
        
        result = await metadata_service.store_schema_metadata(
            "run_123", "job_456", schema_data
        )
        
        assert result.success
        assert result.fallback_used
        mock_fallback.store_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self, metadata_service):
        """Test health check functionality"""
        # Mock stores
        mock_primary = AsyncMock()
        mock_primary.health_check.return_value = Mock(
            healthy=True,
            service_name="OpenMetadata",
            version="1.0.0",
            response_time_ms=50.0
        )
        
        mock_fallback = AsyncMock()
        mock_fallback.health_check.return_value = Mock(
            healthy=True,
            service_name="FileMetadataStore",
            version="1.0.0",
            response_time_ms=5.0
        )
        
        metadata_service.primary_store = mock_primary
        metadata_service.fallback_store = mock_fallback
        
        health_status = await metadata_service.health_check()
        
        assert health_status["metadata_service"] == "healthy"
        assert "primary" in health_status["stores"]
        assert "fallback" in health_status["stores"]
        assert health_status["stores"]["primary"]["healthy"]
        assert health_status["stores"]["fallback"]["healthy"]


class TestOpenMetadataAuth:
    """Test cases for OpenMetadataAuth"""
    
    @pytest.fixture
    def auth_provider(self):
        """Create an OpenMetadataAuth instance for testing"""
        return OpenMetadataAuth("localhost", "8585", "admin@test.com")
    
    def test_initialization(self, auth_provider):
        """Test authentication provider initialization"""
        assert auth_provider.host == "localhost"
        assert auth_provider.port == "8585"
        assert auth_provider.admin_email == "admin@test.com"
        assert auth_provider.auth_token is None
    
    @pytest.mark.asyncio
    async def test_authenticate_with_jwt_success(self, auth_provider):
        """Test successful JWT authentication"""
        with patch('requests.get') as mock_get, \
             patch('requests.put') as mock_put:
            
            # Mock bot exists
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"id": "bot_123"}
            
            # Mock JWT token generation
            mock_put.return_value.status_code = 200
            mock_put.return_value.json.return_value = {
                "config": {"JWTToken": "test_jwt_token"}
            }
            
            result = await auth_provider.authenticate()
            
            assert result.success
            assert result.auth_type == AuthenticationType.JWT
            assert result.token == "test_jwt_token"
            assert auth_provider.auth_token == "test_jwt_token"
    
    @pytest.mark.asyncio
    async def test_authenticate_fallback_to_basic(self, auth_provider):
        """Test fallback to basic auth when JWT fails"""
        with patch('requests.get') as mock_get:
            # Mock JWT failure but basic auth success
            mock_get.side_effect = [
                Mock(status_code=404),  # Bot not found
                Mock(status_code=200)   # Basic auth works
            ]
            
            result = await auth_provider.authenticate()
            
            assert result.success
            assert result.auth_type == AuthenticationType.BASIC
            assert auth_provider.auth_token.startswith("Basic ")
    
    def test_get_auth_headers(self, auth_provider):
        """Test authentication header generation"""
        # Test with JWT token
        auth_provider.auth_token = "jwt_token_123"
        headers = auth_provider.get_auth_headers()
        
        assert headers["Authorization"] == "Bearer jwt_token_123"
        assert headers["Content-Type"] == "application/json"
        
        # Test with Basic token
        auth_provider.auth_token = "Basic base64_credentials"
        headers = auth_provider.get_auth_headers()
        
        assert headers["Authorization"] == "Basic base64_credentials"


class TestFileMetadataStore:
    """Test cases for FileMetadataStore"""
    
    @pytest.fixture
    def file_store(self, tmp_path):
        """Create a FileMetadataStore instance for testing"""
        return FileMetadataStore(str(tmp_path / "metadata"))
    
    @pytest.mark.asyncio
    async def test_initialization(self, file_store):
        """Test file store initialization"""
        result = await file_store.initialize()
        
        assert result
        assert file_store.initialized
        assert file_store.storage_path.exists()
        assert (file_store.storage_path / "entities").exists()
        assert (file_store.storage_path / "relationships").exists()
        assert (file_store.storage_path / "jobs").exists()
    
    @pytest.mark.asyncio
    async def test_health_check(self, file_store):
        """Test health check functionality"""
        await file_store.initialize()
        
        health_result = await file_store.health_check()
        
        assert health_result.healthy
        assert health_result.service_name == "FileMetadataStore"
        assert health_result.version == "1.0.0"
        assert health_result.response_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_store_metadata(self, file_store):
        """Test metadata storage in files"""
        await file_store.initialize()
        
        # Create test request
        entities = [
            MetadataEntity(
                name="test_table",
                description="Test table",
                entity_type="table",
                schema_data={"columns": [{"name": "id", "type": "int"}]}
            )
        ]
        
        relationships = [
            MetadataRelationship(
                from_entity="table1",
                to_entity="table2",
                from_column="id",
                to_column="ref_id",
                relationship_type="foreign_key"
            )
        ]
        
        request = MetadataStorageRequest(
            run_id="run_123",
            job_id="job_456",
            entities=entities,
            relationships=relationships
        )
        
        result = await file_store.store_metadata(request)
        
        assert result.success
        assert result.stored_entities == 1
        assert result.stored_relationships == 1
        assert result.fallback_used
        
        # Verify files were created
        job_file = file_store.storage_path / "jobs" / "job_456_run_123_metadata.json"
        assert job_file.exists()
        
        entity_file = file_store.storage_path / "entities" / "test_table.json"
        assert entity_file.exists()
    
    @pytest.mark.asyncio
    async def test_get_entity(self, file_store):
        """Test entity retrieval"""
        await file_store.initialize()
        
        # First store an entity
        entities = [
            MetadataEntity(
                name="test_entity",
                description="Test entity",
                entity_type="table",
                schema_data={"columns": []}
            )
        ]
        
        request = MetadataStorageRequest(
            run_id="run_123",
            job_id="job_456",
            entities=entities,
            relationships=[]
        )
        
        await file_store.store_metadata(request)
        
        # Now retrieve it
        entity = await file_store.get_entity("test_entity")
        
        assert entity is not None
        assert entity.name == "test_entity"
        assert entity.description == "Test entity"
        assert entity.entity_type == "table"
    
    def test_list_stored_jobs(self, file_store):
        """Test listing stored jobs"""
        # This would require async setup, but demonstrates the concept
        jobs = file_store.list_stored_jobs()
        assert isinstance(jobs, list)


class TestMetadataModels:
    """Test cases for metadata models"""
    
    def test_metadata_entity_creation(self):
        """Test MetadataEntity model creation"""
        entity = MetadataEntity(
            name="users",
            description="User table",
            entity_type="table",
            schema_data={"columns": [{"name": "id", "type": "int"}]},
            tags=["important", "pii"]
        )
        
        assert entity.name == "users"
        assert entity.description == "User table"
        assert entity.entity_type == "table"
        assert "columns" in entity.schema_data
        assert len(entity.tags) == 2
    
    def test_metadata_relationship_creation(self):
        """Test MetadataRelationship model creation"""
        relationship = MetadataRelationship(
            from_entity="users",
            to_entity="orders",
            from_column="id",
            to_column="user_id",
            relationship_type="foreign_key",
            description="User to orders relationship"
        )
        
        assert relationship.from_entity == "users"
        assert relationship.to_entity == "orders"
        assert relationship.from_column == "id"
        assert relationship.to_column == "user_id"
        assert relationship.relationship_type == "foreign_key"
    
    def test_authentication_result_creation(self):
        """Test AuthenticationResult model creation"""
        result = AuthenticationResult(
            success=True,
            auth_type=AuthenticationType.JWT,
            token="test_token",
            expires_at=datetime.now()
        )
        
        assert result.success
        assert result.auth_type == AuthenticationType.JWT
        assert result.token == "test_token"
        assert result.expires_at is not None


if __name__ == "__main__":
    pytest.main([__file__])

