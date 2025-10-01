"""
Unified file service that replaces the old file_service.py
Provides backward compatibility while using the new modular architecture
"""

import logging
from typing import List, Dict, Any, Optional
from .file_manager_service import FileManagerService
from .file_cleanup_service import FileCleanupService
from .file_archive_service import FileArchiveService
from .storage.minio_storage import MinioStorage
from .models import FileInfo

logger = logging.getLogger(__name__)


class UnifiedFileService:
    """
    Unified file service that provides backward compatibility
    with the old FileService interface while using new modular services
    """
    
    def __init__(self):
        """Initialize the unified file service"""
        # Initialize storage backend
        self.storage = MinioStorage()
        
        # Initialize specialized services
        self.manager = FileManagerService(self.storage)
        self.cleanup = FileCleanupService(self.storage)
        self.archive = FileArchiveService(self.storage)
        
        # For orchestrator compatibility
        self.orchestrator = None
    
    def set_orchestrator(self, orchestrator):
        """Set orchestrator for all services"""
        self.orchestrator = orchestrator
        self.manager.orchestrator = orchestrator
        self.cleanup.orchestrator = orchestrator
        self.archive.orchestrator = orchestrator
    
    # Backward compatibility methods (old FileService interface)
    
    async def cleanup_source_files(self, run_id: str, job_id: str, websocket_manager=None) -> None:
        """
        Clean up source files after successful processing (backward compatibility)
        
        Args:
            run_id: Pipeline run identifier
            job_id: Job identifier
            websocket_manager: WebSocket manager for status updates
        """
        try:
            result = await self.cleanup.cleanup_job_files(job_id, run_id, "uploads", websocket_manager)
            
            if not result["success"]:
                logger.error(f"Cleanup failed for job {job_id}: {result['errors']}")
                raise Exception(f"Cleanup failed: {'; '.join(result['errors'])}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup source files for job {job_id}: {str(e)}")
            raise
    
    async def list_job_files(self, job_id: str) -> List[dict]:
        """
        List all files for a specific job (backward compatibility)
        
        Args:
            job_id: Job identifier
            
        Returns:
            List of dictionaries containing file information
        """
        try:
            files = await self.manager.list_job_files(job_id, "uploads")
            
            # Convert to old format for backward compatibility
            result = []
            for file_info in files:
                result.append({
                    "name": file_info.name,
                    "size": file_info.size,
                    "last_modified": file_info.last_modified,
                    "is_source_file": file_info.is_supported_format
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list files for job {job_id}: {str(e)}")
            return []
    
    async def get_file_content(self, file_path: str) -> bytes:
        """
        Get content of a specific file (backward compatibility)
        
        Args:
            file_path: Path to the file in uploads bucket
            
        Returns:
            File content as bytes
        """
        try:
            return await self.manager.get_file_content(file_path, "uploads")
            
        except Exception as e:
            logger.error(f"Failed to get content for file {file_path}: {str(e)}")
            raise
    
    async def archive_job_files(self, job_id: str, archive_bucket: str = "archive") -> None:
        """
        Archive job files instead of deleting them (backward compatibility)
        
        Args:
            job_id: Job identifier
            archive_bucket: Bucket to move files to for archiving
        """
        try:
            # Generate a run_id for archiving
            from datetime import datetime
            run_id = f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            result = await self.archive.archive_job_files(job_id, run_id, "uploads")
            
            if not result["success"]:
                logger.error(f"Archive failed for job {job_id}: {result['errors']}")
                raise Exception(f"Archive failed: {'; '.join(result['errors'])}")
                
            logger.info(f"Successfully archived {result['files_archived']} files for job {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to archive files for job {job_id}: {str(e)}")
            raise
    
    # New enhanced methods
    
    async def validate_job_files(self, job_id: str, validate_content: bool = False) -> List[Dict[str, Any]]:
        """
        Validate all files for a job
        
        Args:
            job_id: Job identifier
            validate_content: Whether to perform content validation
            
        Returns:
            List of validation results
        """
        try:
            results = await self.manager.validate_job_files(job_id, "uploads", validate_content)
            
            # Convert to dictionary format
            return [result.dict() for result in results]
            
        except Exception as e:
            logger.error(f"Failed to validate files for job {job_id}: {str(e)}")
            return []
    
    async def get_file_statistics(self, job_id: str) -> Dict[str, Any]:
        """
        Get statistics about files for a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            File statistics
        """
        try:
            files = await self.manager.list_job_files(job_id, "uploads")
            
            if not files:
                return {
                    "total_files": 0,
                    "total_size_bytes": 0,
                    "file_types": {},
                    "supported_files": 0,
                    "unsupported_files": 0
                }
            
            stats = {
                "total_files": len(files),
                "total_size_bytes": sum(f.size or 0 for f in files),
                "file_types": {},
                "supported_files": 0,
                "unsupported_files": 0,
                "largest_file": None,
                "smallest_file": None
            }
            
            largest_size = 0
            smallest_size = float('inf')
            
            for file_info in files:
                # File type distribution
                extension = file_info.file_extension or 'no_extension'
                stats["file_types"][extension] = stats["file_types"].get(extension, 0) + 1
                
                # Supported vs unsupported
                if file_info.is_supported_format:
                    stats["supported_files"] += 1
                else:
                    stats["unsupported_files"] += 1
                
                # Size tracking
                if file_info.size:
                    if file_info.size > largest_size:
                        largest_size = file_info.size
                        stats["largest_file"] = {
                            "name": file_info.file_name,
                            "size": file_info.size,
                            "path": file_info.name
                        }
                    
                    if file_info.size < smallest_size:
                        smallest_size = file_info.size
                        stats["smallest_file"] = {
                            "name": file_info.file_name,
                            "size": file_info.size,
                            "path": file_info.name
                        }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get file statistics for job {job_id}: {str(e)}")
            return {"error": str(e)}
    
    async def cleanup_old_files(self, days_old: int = 7) -> Dict[str, Any]:
        """
        Clean up files older than specified days
        
        Args:
            days_old: Delete files older than this many days
            
        Returns:
            Cleanup result
        """
        try:
            return await self.cleanup.cleanup_old_files("uploads", days_old)
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_cleanup_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about files that could be cleaned up
        
        Returns:
            Cleanup statistics
        """
        try:
            return await self.cleanup.get_cleanup_statistics("uploads")
            
        except Exception as e:
            logger.error(f"Failed to get cleanup statistics: {str(e)}")
            return {"error": str(e)}
    
    async def get_archive_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about archived files
        
        Returns:
            Archive statistics
        """
        try:
            return await self.archive.get_archive_statistics()
            
        except Exception as e:
            logger.error(f"Failed to get archive statistics: {str(e)}")
            return {"error": str(e)}
    
    async def list_archived_jobs(self) -> List[Dict[str, Any]]:
        """
        List all archived jobs
        
        Returns:
            List of archived job information
        """
        try:
            return await self.archive.list_archived_jobs()
            
        except Exception as e:
            logger.error(f"Failed to list archived jobs: {str(e)}")
            return []
    
    async def restore_job_files(self, job_id: str, run_id: str) -> Dict[str, Any]:
        """
        Restore archived files for a job
        
        Args:
            job_id: Job identifier
            run_id: Pipeline run identifier
            
        Returns:
            Restore result
        """
        try:
            return await self.archive.restore_job_files(job_id, run_id, "uploads")
            
        except Exception as e:
            logger.error(f"Failed to restore files for job {job_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all file service components
        
        Returns:
            Health status information
        """
        try:
            manager_health = await self.manager.health_check()
            
            return {
                "unified_file_service": "healthy",
                "components": {
                    "manager": manager_health,
                    "cleanup": "healthy",
                    "archive": "healthy"
                }
            }
            
        except Exception as e:
            return {
                "unified_file_service": "unhealthy",
                "error": str(e)
            }

