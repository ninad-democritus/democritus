"""
Unit tests for new file operations services
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path

# Import the services to test
from app.file_operations.file_manager_service import FileManagerService
from app.file_operations.file_cleanup_service import FileCleanupService
from app.file_operations.file_archive_service import FileArchiveService
from app.file_operations.unified_file_service import UnifiedFileService
from app.file_operations.storage.minio_storage import MinioStorage
from app.file_operations.validators.file_validator import FileValidator
from app.file_operations.models import FileInfo, ValidationResult


class TestFileManagerService:
    """Test cases for FileManagerService"""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage backend"""
        storage = AsyncMock(spec=MinioStorage)
        return storage
    
    @pytest.fixture
    def file_manager(self, mock_storage):
        """Create a FileManagerService instance for testing"""
        return FileManagerService(mock_storage)
    
    @pytest.mark.asyncio
    async def test_list_job_files(self, file_manager, mock_storage):
        """Test listing files for a job"""
        # Mock storage response
        mock_files = [
            FileInfo(
                name="jobs/test_job/file1.csv",
                size=1024,
                last_modified=datetime.now(),
                content_type="text/csv",
                bucket="uploads"
            ),
            FileInfo(
                name="jobs/test_job/file2.xlsx",
                size=2048,
                last_modified=datetime.now(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                bucket="uploads"
            ),
            FileInfo(
                name="jobs/test_job/readme.txt",
                size=512,
                last_modified=datetime.now(),
                content_type="text/plain",
                bucket="uploads"
            )
        ]
        
        mock_storage.list_files.return_value = mock_files
        
        result = await file_manager.list_job_files("test_job")
        
        # Should only return supported file formats (csv, xlsx)
        assert len(result) == 2
        assert all(f.is_supported_format for f in result)
        mock_storage.list_files.assert_called_once_with(
            bucket="uploads",
            prefix="jobs/test_job/",
            recursive=True
        )
    
    @pytest.mark.asyncio
    async def test_get_file_content(self, file_manager, mock_storage):
        """Test getting file content"""
        test_content = b"test,data\n1,2\n3,4"
        mock_storage.get_file_content.return_value = test_content
        
        result = await file_manager.get_file_content("test_file.csv")
        
        assert result == test_content
        mock_storage.get_file_content.assert_called_once_with("uploads", "test_file.csv")
    
    @pytest.mark.asyncio
    async def test_validate_job_files(self, file_manager, mock_storage):
        """Test file validation for a job"""
        # Mock files
        mock_files = [
            FileInfo(
                name="jobs/test_job/valid.csv",
                size=1024,
                last_modified=datetime.now(),
                content_type="text/csv",
                bucket="uploads"
            )
        ]
        
        mock_storage.list_files.return_value = mock_files
        
        # Mock validator
        file_manager.validator = AsyncMock()
        file_manager.validator.validate_files.return_value = [
            ValidationResult(
                valid=True,
                file_path="jobs/test_job/valid.csv",
                errors=[],
                warnings=[]
            )
        ]
        
        results = await file_manager.validate_job_files("test_job")
        
        assert len(results) == 1
        assert results[0].valid
        file_manager.validator.validate_files.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self, file_manager, mock_storage):
        """Test health check functionality"""
        mock_storage.health_check.return_value = {
            "healthy": True,
            "service_name": "MinIO",
            "response_time_ms": 25.0
        }
        
        result = await file_manager.health_check()
        
        assert result["file_manager"] == "healthy"
        assert result["storage"]["healthy"]
        assert result["validator"] == "healthy"


class TestFileCleanupService:
    """Test cases for FileCleanupService"""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage backend"""
        return AsyncMock(spec=MinioStorage)
    
    @pytest.fixture
    def cleanup_service(self, mock_storage):
        """Create a FileCleanupService instance for testing"""
        return FileCleanupService(mock_storage)
    
    @pytest.mark.asyncio
    async def test_cleanup_job_files_success(self, cleanup_service, mock_storage):
        """Test successful job file cleanup"""
        # Mock files to delete
        mock_files = [
            FileInfo(
                name="jobs/test_job/file1.csv",
                size=1024,
                last_modified=datetime.now(),
                bucket="uploads"
            ),
            FileInfo(
                name="jobs/test_job/file2.xlsx",
                size=2048,
                last_modified=datetime.now(),
                bucket="uploads"
            )
        ]
        
        mock_storage.list_files.return_value = mock_files
        mock_storage.delete_file.return_value = True
        
        result = await cleanup_service.cleanup_job_files("test_job", "run_123")
        
        assert result["success"]
        assert result["files_found"] == 2
        assert result["files_deleted"] == 2
        assert len(result["errors"]) == 0
        
        # Verify delete was called for each file
        assert mock_storage.delete_file.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_job_files_partial_failure(self, cleanup_service, mock_storage):
        """Test job file cleanup with partial failures"""
        # Mock files
        mock_files = [
            FileInfo(name="jobs/test_job/file1.csv", size=1024, last_modified=datetime.now()),
            FileInfo(name="jobs/test_job/file2.csv", size=2048, last_modified=datetime.now())
        ]
        
        mock_storage.list_files.return_value = mock_files
        # First delete succeeds, second fails
        mock_storage.delete_file.side_effect = [True, False]
        
        result = await cleanup_service.cleanup_job_files("test_job", "run_123")
        
        assert not result["success"]  # Should be False due to errors
        assert result["files_found"] == 2
        assert result["files_deleted"] == 1
        assert len(result["errors"]) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, cleanup_service, mock_storage):
        """Test cleanup of old files"""
        old_date = datetime.now() - timedelta(days=10)
        recent_date = datetime.now() - timedelta(hours=1)
        
        # Mock files with different ages
        mock_files = [
            FileInfo(name="old_file.csv", size=1024, last_modified=old_date),
            FileInfo(name="recent_file.csv", size=2048, last_modified=recent_date)
        ]
        
        mock_storage.list_files.return_value = mock_files
        mock_storage.delete_file.return_value = True
        
        result = await cleanup_service.cleanup_old_files("uploads", days_old=7)
        
        assert result["success"]
        assert result["files_found"] == 1  # Only old file
        assert result["files_deleted"] == 1
        
        # Verify only old file was deleted
        mock_storage.delete_file.assert_called_once_with("uploads", "old_file.csv")
    
    @pytest.mark.asyncio
    async def test_get_cleanup_statistics(self, cleanup_service, mock_storage):
        """Test getting cleanup statistics"""
        # Mock files with various ages and types
        now = datetime.now()
        mock_files = [
            FileInfo(name="file1.csv", size=1024, last_modified=now - timedelta(hours=12)),
            FileInfo(name="file2.xlsx", size=2048, last_modified=now - timedelta(days=5)),
            FileInfo(name="file3.json", size=512, last_modified=now - timedelta(days=45))
        ]
        
        mock_storage.list_files.return_value = mock_files
        
        stats = await cleanup_service.get_cleanup_statistics()
        
        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] == 3584
        assert "age_distribution" in stats
        assert "file_types" in stats
        assert stats["file_types"]["csv"] == 1
        assert stats["file_types"]["xlsx"] == 1
        assert stats["file_types"]["json"] == 1


class TestFileArchiveService:
    """Test cases for FileArchiveService"""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage backend"""
        return AsyncMock(spec=MinioStorage)
    
    @pytest.fixture
    def archive_service(self, mock_storage):
        """Create a FileArchiveService instance for testing"""
        return FileArchiveService(mock_storage)
    
    @pytest.mark.asyncio
    async def test_archive_job_files_success(self, archive_service, mock_storage):
        """Test successful job file archiving"""
        # Mock files to archive
        mock_files = ["jobs/test_job/file1.csv", "jobs/test_job/file2.xlsx"]
        
        mock_storage.create_bucket.return_value = True
        mock_storage.list_files.return_value = [
            FileInfo(name=f, size=1024, last_modified=datetime.now()) for f in mock_files
        ]
        mock_storage.copy_file.return_value = True
        mock_storage.put_file_content.return_value = True  # For manifest
        
        result = await archive_service.archive_job_files("test_job", "run_123")
        
        assert result["success"]
        assert result["files_found"] == 2
        assert result["files_archived"] == 2
        assert result["archive_bucket"] == "archive"
        assert len(result["errors"]) == 0
        
        # Verify archive bucket was created
        mock_storage.create_bucket.assert_called_with("archive")
        
        # Verify files were copied
        assert mock_storage.copy_file.call_count == 2
    
    @pytest.mark.asyncio
    async def test_restore_job_files(self, archive_service, mock_storage):
        """Test restoring archived job files"""
        # Mock archived files
        archived_files = [
            FileInfo(
                name="archived_jobs/test_job_run_123/file1.csv",
                size=1024,
                last_modified=datetime.now()
            ),
            FileInfo(
                name="archived_jobs/test_job_run_123/file2.xlsx",
                size=2048,
                last_modified=datetime.now()
            )
        ]
        
        mock_storage.list_files.return_value = archived_files
        mock_storage.create_bucket.return_value = True
        mock_storage.copy_file.return_value = True
        
        result = await archive_service.restore_job_files("test_job", "run_123")
        
        assert result["success"]
        assert result["files_found"] == 2
        assert result["files_restored"] == 2
        assert result["target_bucket"] == "uploads"
        
        # Verify files were copied back
        assert mock_storage.copy_file.call_count == 2
    
    @pytest.mark.asyncio
    async def test_list_archived_jobs(self, archive_service, mock_storage):
        """Test listing archived jobs"""
        # Mock archived job directories
        archived_dirs = [
            FileInfo(
                name="archived_jobs/job1_run1/",
                size=0,
                last_modified=datetime.now(),
                is_directory=True
            ),
            FileInfo(
                name="archived_jobs/job2_run2/",
                size=0,
                last_modified=datetime.now(),
                is_directory=True
            )
        ]
        
        mock_storage.list_files.return_value = archived_dirs
        
        jobs = await archive_service.list_archived_jobs()
        
        assert len(jobs) == 2
        assert any(job["job_id"] == "job1" for job in jobs)
        assert any(job["job_id"] == "job2" for job in jobs)
    
    @pytest.mark.asyncio
    async def test_get_archive_statistics(self, archive_service, mock_storage):
        """Test getting archive statistics"""
        # Mock archived files
        archived_files = [
            FileInfo(
                name="archived_jobs/job1_run1/file1.csv",
                size=1024,
                last_modified=datetime.now() - timedelta(days=5)
            ),
            FileInfo(
                name="archived_jobs/job2_run2/file2.xlsx",
                size=2048,
                last_modified=datetime.now() - timedelta(days=10)
            )
        ]
        
        mock_storage.list_files.return_value = archived_files
        
        stats = await archive_service.get_archive_statistics()
        
        assert stats["total_archived_files"] == 2
        assert stats["total_size_bytes"] == 3072
        assert stats["archive_bucket"] == "archive"
        assert stats["jobs_archived"] == 2


class TestFileValidator:
    """Test cases for FileValidator"""
    
    @pytest.fixture
    def validator(self):
        """Create a FileValidator instance for testing"""
        return FileValidator()
    
    @pytest.mark.asyncio
    async def test_validate_csv_file(self, validator):
        """Test CSV file validation"""
        file_info = FileInfo(
            name="test.csv",
            size=100,
            last_modified=datetime.now(),
            content_type="text/csv"
        )
        
        csv_content = b"name,age\nJohn,25\nJane,30"
        
        result = await validator.validate_file(file_info, csv_content)
        
        assert result.valid
        assert len(result.errors) == 0
        assert result.file_path == "test.csv"
    
    @pytest.mark.asyncio
    async def test_validate_invalid_extension(self, validator):
        """Test validation of unsupported file extension"""
        file_info = FileInfo(
            name="test.txt",
            size=100,
            last_modified=datetime.now(),
            content_type="text/plain"
        )
        
        result = await validator.validate_file(file_info)
        
        assert not result.valid
        assert any("Unsupported file extension" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_empty_file(self, validator):
        """Test validation of empty file"""
        file_info = FileInfo(
            name="test.csv",
            size=0,
            last_modified=datetime.now(),
            content_type="text/csv"
        )
        
        result = await validator.validate_file(file_info)
        
        assert not result.valid
        assert any("too small" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_large_file_warning(self, validator):
        """Test validation warning for large files"""
        file_info = FileInfo(
            name="test.csv",
            size=60 * 1024 * 1024,  # 60MB
            last_modified=datetime.now(),
            content_type="text/csv"
        )
        
        result = await validator.validate_file(file_info)
        
        assert result.valid  # Should still be valid
        assert any("quite large" in warning for warning in result.warnings)
    
    def test_calculate_file_checksum(self, validator):
        """Test file checksum calculation"""
        content = b"test content"
        
        md5_checksum = validator.calculate_file_checksum(content, "md5")
        sha256_checksum = validator.calculate_file_checksum(content, "sha256")
        
        assert len(md5_checksum) == 32  # MD5 is 32 hex chars
        assert len(sha256_checksum) == 64  # SHA256 is 64 hex chars
        assert md5_checksum != sha256_checksum


class TestUnifiedFileService:
    """Test cases for UnifiedFileService"""
    
    @pytest.fixture
    def unified_service(self):
        """Create a UnifiedFileService instance for testing"""
        service = UnifiedFileService()
        # Mock the underlying services
        service.manager = AsyncMock()
        service.cleanup = AsyncMock()
        service.archive = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_cleanup_source_files_backward_compatibility(self, unified_service):
        """Test backward compatibility for cleanup_source_files"""
        # Mock cleanup service response
        unified_service.cleanup.cleanup_job_files.return_value = {
            "success": True,
            "files_found": 3,
            "files_deleted": 3,
            "errors": []
        }
        
        # Should not raise exception
        await unified_service.cleanup_source_files("run_123", "job_456")
        
        unified_service.cleanup.cleanup_job_files.assert_called_once_with(
            "job_456", "run_123", "uploads", None
        )
    
    @pytest.mark.asyncio
    async def test_list_job_files_backward_compatibility(self, unified_service):
        """Test backward compatibility for list_job_files"""
        # Mock manager response
        mock_files = [
            FileInfo(
                name="jobs/test_job/file1.csv",
                size=1024,
                last_modified=datetime.now()
            )
        ]
        
        unified_service.manager.list_job_files.return_value = mock_files
        
        result = await unified_service.list_job_files("test_job")
        
        assert len(result) == 1
        assert result[0]["name"] == "jobs/test_job/file1.csv"
        assert result[0]["size"] == 1024
        assert "is_source_file" in result[0]
    
    @pytest.mark.asyncio
    async def test_validate_job_files_new_functionality(self, unified_service):
        """Test new validation functionality"""
        # Mock validation results
        mock_results = [
            ValidationResult(
                valid=True,
                file_path="test.csv",
                errors=[],
                warnings=["File is quite large"]
            )
        ]
        
        unified_service.manager.validate_job_files.return_value = mock_results
        
        results = await unified_service.validate_job_files("test_job", validate_content=True)
        
        assert len(results) == 1
        assert results[0]["valid"]
        assert len(results[0]["warnings"]) == 1
        
        unified_service.manager.validate_job_files.assert_called_once_with(
            "test_job", "uploads", True
        )
    
    @pytest.mark.asyncio
    async def test_health_check_comprehensive(self, unified_service):
        """Test comprehensive health check"""
        # Mock manager health check
        unified_service.manager.health_check.return_value = {
            "file_manager": "healthy",
            "storage": {"healthy": True, "service_name": "MinIO"},
            "validator": "healthy"
        }
        
        result = await unified_service.health_check()
        
        assert result["unified_file_service"] == "healthy"
        assert "components" in result
        assert result["components"]["manager"]["file_manager"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__])
