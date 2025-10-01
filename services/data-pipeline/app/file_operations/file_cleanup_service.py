"""
Specialized service for file cleanup operations
"""

import logging
from typing import List, Dict, Any, Optional
from .storage.storage_interface import StorageInterface
from .storage.minio_storage import MinioStorage
from .models import FileInfo

logger = logging.getLogger(__name__)


class FileCleanupService:
    """
    Specialized service for handling file cleanup operations
    """
    
    def __init__(self, storage_backend: Optional[StorageInterface] = None):
        """
        Initialize the file cleanup service
        
        Args:
            storage_backend: Optional storage backend, defaults to MinIO
        """
        self.storage = storage_backend or MinioStorage()
        self.orchestrator = None  # Will be set by orchestrator
    
    async def cleanup_job_files(self, job_id: str, run_id: str, bucket: str = "uploads", websocket_manager=None) -> Dict[str, Any]:
        """
        Clean up all files for a specific job
        
        Args:
            job_id: Job identifier
            run_id: Pipeline run identifier
            bucket: Bucket name (default: uploads)
            websocket_manager: WebSocket manager for status updates
            
        Returns:
            Cleanup result summary
        """
        logger.info(f"Starting cleanup for job {job_id} (run: {run_id})")
        
        try:
            # Send initial status
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id, 
                    "Preparing to cleanup uploaded files", 
                    "cleanup_preparing"
                )
            
            # Find all files for the job
            files_to_delete = await self._find_job_files(job_id, bucket)
            
            if not files_to_delete:
                logger.info(f"No files found for cleanup in job {job_id}")
                if self.orchestrator:
                    await self.orchestrator._send_status_update(
                        websocket_manager, run_id,
                        "No source files found for cleanup",
                        "cleanup_no_files"
                    )
                return {
                    "success": True,
                    "files_found": 0,
                    "files_deleted": 0,
                    "errors": []
                }
            
            logger.info(f"Found {len(files_to_delete)} files to delete for job {job_id}")
            
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    f"Found {len(files_to_delete)} source files to cleanup",
                    "cleanup_files_found"
                )
            
            # Delete files
            deleted_count, errors = await self._delete_files(files_to_delete, bucket)
            
            logger.info(f"Successfully deleted {deleted_count}/{len(files_to_delete)} files for job {job_id}")
            
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    f"Successfully deleted {deleted_count} source files",
                    "cleanup_files_deleted"
                )
            
            # Check if job directory is empty
            remaining_files = await self._check_job_directory_status(job_id, bucket)
            
            # Send completion status
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    "Cleanup completed successfully",
                    "cleanup_completed"
                )
            
            return {
                "success": len(errors) == 0,
                "files_found": len(files_to_delete),
                "files_deleted": deleted_count,
                "remaining_files": remaining_files,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup files for job {job_id}: {str(e)}")
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    f"Cleanup failed: {str(e)}",
                    "cleanup_failed"
                )
            
            return {
                "success": False,
                "files_found": 0,
                "files_deleted": 0,
                "errors": [str(e)]
            }
    
    async def cleanup_specific_files(self, file_paths: List[str], bucket: str = "uploads") -> Dict[str, Any]:
        """
        Clean up specific files by path
        
        Args:
            file_paths: List of file paths to delete
            bucket: Bucket name (default: uploads)
            
        Returns:
            Cleanup result summary
        """
        logger.info(f"Cleaning up {len(file_paths)} specific files")
        
        try:
            deleted_count, errors = await self._delete_files(file_paths, bucket)
            
            return {
                "success": len(errors) == 0,
                "files_requested": len(file_paths),
                "files_deleted": deleted_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup specific files: {str(e)}")
            return {
                "success": False,
                "files_requested": len(file_paths),
                "files_deleted": 0,
                "errors": [str(e)]
            }
    
    async def cleanup_old_files(self, bucket: str = "uploads", days_old: int = 7) -> Dict[str, Any]:
        """
        Clean up files older than specified days
        
        Args:
            bucket: Bucket name (default: uploads)
            days_old: Delete files older than this many days
            
        Returns:
            Cleanup result summary
        """
        logger.info(f"Cleaning up files older than {days_old} days from bucket {bucket}")
        
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Get all files in bucket
            all_files = await self.storage.list_files(bucket, recursive=True)
            
            # Filter old files
            old_files = [
                f.name for f in all_files 
                if f.last_modified and f.last_modified < cutoff_date and not f.is_directory
            ]
            
            if not old_files:
                logger.info(f"No files older than {days_old} days found")
                return {
                    "success": True,
                    "files_found": 0,
                    "files_deleted": 0,
                    "errors": []
                }
            
            logger.info(f"Found {len(old_files)} files older than {days_old} days")
            
            # Delete old files
            deleted_count, errors = await self._delete_files(old_files, bucket)
            
            return {
                "success": len(errors) == 0,
                "files_found": len(old_files),
                "files_deleted": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {str(e)}")
            return {
                "success": False,
                "files_found": 0,
                "files_deleted": 0,
                "errors": [str(e)]
            }
    
    async def _find_job_files(self, job_id: str, bucket: str) -> List[str]:
        """Find all files for a job"""
        try:
            files = await self.storage.list_files(
                bucket=bucket,
                prefix=f"jobs/{job_id}/",
                recursive=True
            )
            
            # Filter for data files only
            data_files = [
                f.name for f in files 
                if not f.is_directory and f.name.lower().endswith(('.csv', '.xlsx', '.xls', '.json', '.parquet'))
            ]
            
            return data_files
            
        except Exception as e:
            logger.error(f"Failed to find files for job {job_id}: {str(e)}")
            return []
    
    async def _delete_files(self, file_paths: List[str], bucket: str) -> tuple[int, List[str]]:
        """
        Delete a list of files and return count and errors
        
        Returns:
            Tuple of (deleted_count, errors)
        """
        deleted_count = 0
        errors = []
        
        for file_path in file_paths:
            try:
                success = await self.storage.delete_file(bucket, file_path)
                if success:
                    deleted_count += 1
                    logger.debug(f"Deleted: {bucket}/{file_path}")
                else:
                    errors.append(f"Failed to delete {file_path}")
                    
            except Exception as e:
                error_msg = f"Error deleting {file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return deleted_count, errors
    
    async def _check_job_directory_status(self, job_id: str, bucket: str) -> int:
        """
        Check how many files remain in job directory after cleanup
        
        Returns:
            Number of remaining files
        """
        try:
            remaining_files = await self.storage.list_files(
                bucket=bucket,
                prefix=f"jobs/{job_id}/",
                recursive=True
            )
            
            # Count non-directory files
            file_count = sum(1 for f in remaining_files if not f.is_directory)
            
            if file_count == 0:
                logger.info(f"Job directory jobs/{job_id}/ is now empty")
            else:
                logger.info(f"Job directory jobs/{job_id}/ still contains {file_count} files")
            
            return file_count
            
        except Exception as e:
            logger.warning(f"Could not check job directory status: {str(e)}")
            return -1  # Unknown
    
    async def get_cleanup_statistics(self, bucket: str = "uploads") -> Dict[str, Any]:
        """
        Get statistics about files that could be cleaned up
        
        Args:
            bucket: Bucket name (default: uploads)
            
        Returns:
            Statistics about cleanup candidates
        """
        try:
            from datetime import datetime, timedelta
            
            all_files = await self.storage.list_files(bucket, recursive=True)
            
            # Filter out directories
            files = [f for f in all_files if not f.is_directory]
            
            now = datetime.now()
            stats = {
                "total_files": len(files),
                "total_size_bytes": sum(f.size or 0 for f in files),
                "age_distribution": {
                    "less_than_1_day": 0,
                    "1_to_7_days": 0,
                    "7_to_30_days": 0,
                    "more_than_30_days": 0
                },
                "file_types": {},
                "oldest_file": None,
                "newest_file": None
            }
            
            oldest_date = None
            newest_date = None
            
            for file_info in files:
                # Age distribution
                if file_info.last_modified:
                    age = now - file_info.last_modified
                    
                    if age < timedelta(days=1):
                        stats["age_distribution"]["less_than_1_day"] += 1
                    elif age < timedelta(days=7):
                        stats["age_distribution"]["1_to_7_days"] += 1
                    elif age < timedelta(days=30):
                        stats["age_distribution"]["7_to_30_days"] += 1
                    else:
                        stats["age_distribution"]["more_than_30_days"] += 1
                    
                    # Track oldest and newest
                    if oldest_date is None or file_info.last_modified < oldest_date:
                        oldest_date = file_info.last_modified
                        stats["oldest_file"] = file_info.name
                    
                    if newest_date is None or file_info.last_modified > newest_date:
                        newest_date = file_info.last_modified
                        stats["newest_file"] = file_info.name
                
                # File type distribution
                extension = '.' + file_info.name.split('.')[-1].lower() if '.' in file_info.name else 'no_extension'
                stats["file_types"][extension] = stats["file_types"].get(extension, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cleanup statistics: {e}")
            return {
                "error": str(e),
                "total_files": 0,
                "total_size_bytes": 0
            }

