"""
Specialized service for file archiving operations
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .storage.storage_interface import StorageInterface
from .storage.minio_storage import MinioStorage
from .models import FileInfo

logger = logging.getLogger(__name__)


class FileArchiveService:
    """
    Specialized service for handling file archiving operations
    """
    
    def __init__(self, storage_backend: Optional[StorageInterface] = None):
        """
        Initialize the file archive service
        
        Args:
            storage_backend: Optional storage backend, defaults to MinIO
        """
        self.storage = storage_backend or MinioStorage()
        self.archive_bucket = "archive"
        self.orchestrator = None  # Will be set by orchestrator
    
    async def archive_job_files(self, job_id: str, run_id: str, source_bucket: str = "uploads", websocket_manager=None) -> Dict[str, Any]:
        """
        Archive all files for a specific job
        
        Args:
            job_id: Job identifier
            run_id: Pipeline run identifier
            source_bucket: Source bucket name (default: uploads)
            websocket_manager: WebSocket manager for status updates
            
        Returns:
            Archive result summary
        """
        logger.info(f"Starting archive for job {job_id} (run: {run_id})")
        
        try:
            # Send initial status
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    "Preparing to archive job files",
                    "archive_preparing"
                )
            
            # Ensure archive bucket exists
            await self.storage.create_bucket(self.archive_bucket)
            
            # Find all files for the job
            files_to_archive = await self._find_job_files(job_id, source_bucket)
            
            if not files_to_archive:
                logger.info(f"No files found to archive for job {job_id}")
                if self.orchestrator:
                    await self.orchestrator._send_status_update(
                        websocket_manager, run_id,
                        "No files found to archive",
                        "archive_no_files"
                    )
                return {
                    "success": True,
                    "files_found": 0,
                    "files_archived": 0,
                    "errors": []
                }
            
            logger.info(f"Found {len(files_to_archive)} files to archive for job {job_id}")
            
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    f"Found {len(files_to_archive)} files to archive",
                    "archive_files_found"
                )
            
            # Archive files
            archived_count, errors = await self._archive_files(files_to_archive, job_id, run_id, source_bucket)
            
            logger.info(f"Successfully archived {archived_count}/{len(files_to_archive)} files for job {job_id}")
            
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    f"Successfully archived {archived_count} files",
                    "archive_files_completed"
                )
            
            # Create archive manifest
            manifest_path = await self._create_archive_manifest(job_id, run_id, files_to_archive, archived_count)
            
            # Send completion status
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    "Archive completed successfully",
                    "archive_completed"
                )
            
            return {
                "success": len(errors) == 0,
                "files_found": len(files_to_archive),
                "files_archived": archived_count,
                "archive_bucket": self.archive_bucket,
                "manifest_path": manifest_path,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to archive files for job {job_id}: {str(e)}")
            if self.orchestrator:
                await self.orchestrator._send_status_update(
                    websocket_manager, run_id,
                    f"Archive failed: {str(e)}",
                    "archive_failed"
                )
            
            return {
                "success": False,
                "files_found": 0,
                "files_archived": 0,
                "errors": [str(e)]
            }
    
    async def archive_specific_files(self, file_paths: List[str], archive_prefix: str, source_bucket: str = "uploads") -> Dict[str, Any]:
        """
        Archive specific files by path
        
        Args:
            file_paths: List of file paths to archive
            archive_prefix: Prefix for archived files (e.g., "manual_archive/2024-01-01")
            source_bucket: Source bucket name (default: uploads)
            
        Returns:
            Archive result summary
        """
        logger.info(f"Archiving {len(file_paths)} specific files with prefix {archive_prefix}")
        
        try:
            # Ensure archive bucket exists
            await self.storage.create_bucket(self.archive_bucket)
            
            archived_count = 0
            errors = []
            
            for file_path in file_paths:
                try:
                    # Create archive path
                    file_name = file_path.split('/')[-1]
                    archive_path = f"{archive_prefix}/{file_name}"
                    
                    # Copy to archive
                    success = await self.storage.copy_file(source_bucket, file_path, self.archive_bucket, archive_path)
                    
                    if success:
                        archived_count += 1
                        logger.debug(f"Archived: {source_bucket}/{file_path} -> {self.archive_bucket}/{archive_path}")
                    else:
                        errors.append(f"Failed to archive {file_path}")
                        
                except Exception as e:
                    error_msg = f"Error archiving {file_path}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                "success": len(errors) == 0,
                "files_requested": len(file_paths),
                "files_archived": archived_count,
                "archive_bucket": self.archive_bucket,
                "archive_prefix": archive_prefix,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to archive specific files: {str(e)}")
            return {
                "success": False,
                "files_requested": len(file_paths),
                "files_archived": 0,
                "errors": [str(e)]
            }
    
    async def restore_job_files(self, job_id: str, run_id: str, target_bucket: str = "uploads") -> Dict[str, Any]:
        """
        Restore archived files for a job back to the target bucket
        
        Args:
            job_id: Job identifier
            run_id: Pipeline run identifier
            target_bucket: Target bucket for restored files (default: uploads)
            
        Returns:
            Restore result summary
        """
        logger.info(f"Restoring archived files for job {job_id} (run: {run_id})")
        
        try:
            # Find archived files for this job
            archive_prefix = f"archived_jobs/{job_id}_{run_id}"
            archived_files = await self.storage.list_files(
                bucket=self.archive_bucket,
                prefix=archive_prefix,
                recursive=True
            )
            
            if not archived_files:
                logger.info(f"No archived files found for job {job_id} run {run_id}")
                return {
                    "success": True,
                    "files_found": 0,
                    "files_restored": 0,
                    "errors": []
                }
            
            # Filter out directories and manifest files
            files_to_restore = [
                f for f in archived_files 
                if not f.is_directory and not f.name.endswith('_manifest.json')
            ]
            
            logger.info(f"Found {len(files_to_restore)} archived files to restore for job {job_id}")
            
            # Ensure target bucket exists
            await self.storage.create_bucket(target_bucket)
            
            restored_count = 0
            errors = []
            
            for file_info in files_to_restore:
                try:
                    # Determine original path (remove archive prefix)
                    original_path = file_info.name.replace(f"{archive_prefix}/", f"jobs/{job_id}/")
                    
                    # Copy back to original location
                    success = await self.storage.copy_file(
                        self.archive_bucket, file_info.name,
                        target_bucket, original_path
                    )
                    
                    if success:
                        restored_count += 1
                        logger.debug(f"Restored: {self.archive_bucket}/{file_info.name} -> {target_bucket}/{original_path}")
                    else:
                        errors.append(f"Failed to restore {file_info.name}")
                        
                except Exception as e:
                    error_msg = f"Error restoring {file_info.name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                "success": len(errors) == 0,
                "files_found": len(files_to_restore),
                "files_restored": restored_count,
                "target_bucket": target_bucket,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to restore files for job {job_id}: {str(e)}")
            return {
                "success": False,
                "files_found": 0,
                "files_restored": 0,
                "errors": [str(e)]
            }
    
    async def list_archived_jobs(self) -> List[Dict[str, Any]]:
        """
        List all archived jobs
        
        Returns:
            List of archived job information
        """
        try:
            archived_files = await self.storage.list_files(
                bucket=self.archive_bucket,
                prefix="archived_jobs/",
                recursive=False
            )
            
            jobs = {}
            
            for file_info in archived_files:
                if file_info.is_directory:
                    # Extract job_id and run_id from directory name
                    dir_name = file_info.name.rstrip('/').split('/')[-1]
                    if '_' in dir_name:
                        parts = dir_name.split('_')
                        if len(parts) >= 2:
                            job_id = '_'.join(parts[:-1])  # Handle job IDs with underscores
                            run_id = parts[-1]
                            
                            if job_id not in jobs:
                                jobs[job_id] = {
                                    "job_id": job_id,
                                    "runs": [],
                                    "total_runs": 0
                                }
                            
                            jobs[job_id]["runs"].append({
                                "run_id": run_id,
                                "archive_path": file_info.name,
                                "archived_at": file_info.last_modified.isoformat() if file_info.last_modified else None
                            })
                            jobs[job_id]["total_runs"] += 1
            
            return list(jobs.values())
            
        except Exception as e:
            logger.error(f"Error listing archived jobs: {e}")
            return []
    
    async def _find_job_files(self, job_id: str, bucket: str) -> List[str]:
        """Find all files for a job"""
        try:
            files = await self.storage.list_files(
                bucket=bucket,
                prefix=f"jobs/{job_id}/",
                recursive=True
            )
            
            # Return all files (not just data files) for complete archiving
            return [f.name for f in files if not f.is_directory]
            
        except Exception as e:
            logger.error(f"Failed to find files for job {job_id}: {str(e)}")
            return []
    
    async def _archive_files(self, file_paths: List[str], job_id: str, run_id: str, source_bucket: str) -> tuple[int, List[str]]:
        """
        Archive a list of files and return count and errors
        
        Returns:
            Tuple of (archived_count, errors)
        """
        archived_count = 0
        errors = []
        
        # Create archive directory path
        archive_prefix = f"archived_jobs/{job_id}_{run_id}"
        
        for file_path in file_paths:
            try:
                # Create archive path preserving original structure
                relative_path = file_path.replace(f"jobs/{job_id}/", "")
                archive_path = f"{archive_prefix}/{relative_path}"
                
                # Copy to archive bucket
                success = await self.storage.copy_file(source_bucket, file_path, self.archive_bucket, archive_path)
                
                if success:
                    archived_count += 1
                    logger.debug(f"Archived: {source_bucket}/{file_path} -> {self.archive_bucket}/{archive_path}")
                else:
                    errors.append(f"Failed to archive {file_path}")
                    
            except Exception as e:
                error_msg = f"Error archiving {file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return archived_count, errors
    
    async def _create_archive_manifest(self, job_id: str, run_id: str, original_files: List[str], archived_count: int) -> str:
        """
        Create a manifest file for the archive
        
        Returns:
            Path to the created manifest file
        """
        try:
            import json
            
            manifest_data = {
                "job_id": job_id,
                "run_id": run_id,
                "archived_at": datetime.now().isoformat(),
                "total_files": len(original_files),
                "successfully_archived": archived_count,
                "files": original_files,
                "archive_bucket": self.archive_bucket,
                "archive_prefix": f"archived_jobs/{job_id}_{run_id}"
            }
            
            manifest_content = json.dumps(manifest_data, indent=2).encode('utf-8')
            manifest_path = f"archived_jobs/{job_id}_{run_id}_manifest.json"
            
            success = await self.storage.put_file_content(
                self.archive_bucket, 
                manifest_path, 
                manifest_content
            )
            
            if success:
                logger.debug(f"Created archive manifest: {self.archive_bucket}/{manifest_path}")
                return manifest_path
            else:
                logger.warning(f"Failed to create archive manifest for job {job_id}")
                return ""
                
        except Exception as e:
            logger.error(f"Error creating archive manifest: {e}")
            return ""
    
    async def get_archive_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about archived files
        
        Returns:
            Statistics about archived files
        """
        try:
            archived_files = await self.storage.list_files(self.archive_bucket, recursive=True)
            
            # Filter out directories
            files = [f for f in archived_files if not f.is_directory]
            
            stats = {
                "total_archived_files": len(files),
                "total_size_bytes": sum(f.size or 0 for f in files),
                "archive_bucket": self.archive_bucket,
                "jobs_archived": 0,
                "oldest_archive": None,
                "newest_archive": None
            }
            
            # Count unique jobs
            jobs = set()
            oldest_date = None
            newest_date = None
            
            for file_info in files:
                # Extract job info from path
                if file_info.name.startswith("archived_jobs/"):
                    path_parts = file_info.name.split('/')
                    if len(path_parts) >= 2:
                        job_run = path_parts[1]
                        if '_' in job_run and not job_run.endswith('_manifest.json'):
                            jobs.add(job_run)
                
                # Track dates
                if file_info.last_modified:
                    if oldest_date is None or file_info.last_modified < oldest_date:
                        oldest_date = file_info.last_modified
                    
                    if newest_date is None or file_info.last_modified > newest_date:
                        newest_date = file_info.last_modified
            
            stats["jobs_archived"] = len(jobs)
            stats["oldest_archive"] = oldest_date.isoformat() if oldest_date else None
            stats["newest_archive"] = newest_date.isoformat() if newest_date else None
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting archive statistics: {e}")
            return {
                "error": str(e),
                "total_archived_files": 0,
                "total_size_bytes": 0
            }

