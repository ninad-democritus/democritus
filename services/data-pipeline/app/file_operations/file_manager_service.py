"""
Main file management service that coordinates all file operations
"""

import logging
from typing import List, Dict, Any, Optional
from .storage.storage_interface import StorageInterface
from .storage.minio_storage import MinioStorage
from .validators.file_validator import FileValidator
from .models import FileInfo, ValidationResult

logger = logging.getLogger(__name__)


class FileManagerService:
    """
    Main service for coordinating all file operations
    Provides a unified interface for file management across different storage backends
    """
    
    def __init__(self, storage_backend: Optional[StorageInterface] = None):
        """
        Initialize the file manager service
        
        Args:
            storage_backend: Optional storage backend, defaults to MinIO
        """
        self.storage = storage_backend or MinioStorage()
        self.validator = FileValidator()
        self.orchestrator = None  # Will be set by orchestrator
    
    async def list_job_files(self, job_id: str, bucket: str = "uploads") -> List[FileInfo]:
        """
        List all files for a specific job
        
        Args:
            job_id: Job identifier
            bucket: Bucket name (default: uploads)
            
        Returns:
            List of file information objects
        """
        try:
            logger.info(f"Listing files for job {job_id} in bucket {bucket}")
            
            files = await self.storage.list_files(
                bucket=bucket,
                prefix=f"jobs/{job_id}/",
                recursive=True
            )
            
            # Filter out directories and non-data files
            data_files = [
                f for f in files 
                if not f.is_directory and f.name.lower().endswith(('.csv', '.xlsx', '.xls', '.json', '.parquet'))
            ]
            
            logger.info(f"Found {len(data_files)} data files for job {job_id}")
            return data_files
            
        except Exception as e:
            logger.error(f"Error listing files for job {job_id}: {e}")
            return []
    
    async def get_file_content(self, file_path: str, bucket: str = "uploads") -> bytes:
        """
        Get content of a specific file
        
        Args:
            file_path: Path to the file
            bucket: Bucket name (default: uploads)
            
        Returns:
            File content as bytes
        """
        try:
            logger.debug(f"Getting content for file {bucket}/{file_path}")
            return await self.storage.get_file_content(bucket, file_path)
            
        except Exception as e:
            logger.error(f"Error getting file content {bucket}/{file_path}: {e}")
            raise
    
    async def validate_job_files(self, job_id: str, bucket: str = "uploads", validate_content: bool = False) -> List[ValidationResult]:
        """
        Validate all files for a job
        
        Args:
            job_id: Job identifier
            bucket: Bucket name (default: uploads)
            validate_content: Whether to perform content validation (slower)
            
        Returns:
            List of validation results
        """
        try:
            logger.info(f"Validating files for job {job_id}")
            
            # Get all files for the job
            files = await self.list_job_files(job_id, bucket)
            
            if not files:
                logger.warning(f"No files found for job {job_id}")
                return []
            
            # Validate files
            if validate_content:
                # Get file contents for content validation
                contents = {}
                for file_info in files:
                    try:
                        content = await self.get_file_content(file_info.name, bucket)
                        contents[file_info.name] = content
                    except Exception as e:
                        logger.warning(f"Could not read content for {file_info.name}: {e}")
                
                results = await self.validator.validate_files(files, contents)
            else:
                results = await self.validator.validate_files(files)
            
            # Log validation summary
            valid_files = sum(1 for r in results if r.valid)
            invalid_files = len(results) - valid_files
            
            logger.info(f"Validation complete for job {job_id}: {valid_files} valid, {invalid_files} invalid files")
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating files for job {job_id}: {e}")
            return []
    
    async def get_file_info(self, file_path: str, bucket: str = "uploads") -> Optional[FileInfo]:
        """
        Get information about a specific file
        
        Args:
            file_path: Path to the file
            bucket: Bucket name (default: uploads)
            
        Returns:
            File information if file exists, None otherwise
        """
        try:
            return await self.storage.get_file_info(bucket, file_path)
            
        except Exception as e:
            logger.error(f"Error getting file info {bucket}/{file_path}: {e}")
            return None
    
    async def file_exists(self, file_path: str, bucket: str = "uploads") -> bool:
        """
        Check if a file exists
        
        Args:
            file_path: Path to the file
            bucket: Bucket name (default: uploads)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            return await self.storage.file_exists(bucket, file_path)
            
        except Exception as e:
            logger.error(f"Error checking file existence {bucket}/{file_path}: {e}")
            return False
    
    async def copy_file(self, source_path: str, dest_path: str, source_bucket: str = "uploads", dest_bucket: str = "uploads") -> bool:
        """
        Copy a file from source to destination
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            source_bucket: Source bucket name (default: uploads)
            dest_bucket: Destination bucket name (default: uploads)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Copying file from {source_bucket}/{source_path} to {dest_bucket}/{dest_path}")
            return await self.storage.copy_file(source_bucket, source_path, dest_bucket, dest_path)
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    async def move_file(self, source_path: str, dest_path: str, source_bucket: str = "uploads", dest_bucket: str = "uploads") -> bool:
        """
        Move a file from source to destination
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            source_bucket: Source bucket name (default: uploads)
            dest_bucket: Destination bucket name (default: uploads)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.debug(f"Moving file from {source_bucket}/{source_path} to {dest_bucket}/{dest_path}")
            return await self.storage.move_file(source_bucket, source_path, dest_bucket, dest_path)
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of file management components
        
        Returns:
            Health status information
        """
        try:
            storage_health = await self.storage.health_check()
            
            return {
                "file_manager": "healthy",
                "storage": storage_health,
                "validator": "healthy"
            }
            
        except Exception as e:
            return {
                "file_manager": "unhealthy",
                "error": str(e)
            }

