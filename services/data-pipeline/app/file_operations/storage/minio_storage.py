"""
MinIO storage implementation
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from minio import Minio
from minio.error import S3Error
import os
from .storage_interface import StorageInterface
from ..models import FileInfo

logger = logging.getLogger(__name__)


class MinioStorage(StorageInterface):
    """MinIO implementation of storage interface"""
    
    def __init__(self, endpoint: str = None, access_key: str = None, secret_key: str = None, secure: bool = False):
        """
        Initialize MinIO storage
        
        Args:
            endpoint: MinIO server endpoint
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            secure: Whether to use HTTPS
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.secure = secure
        
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
    
    async def list_files(self, bucket: str, prefix: str = "", recursive: bool = True) -> List[FileInfo]:
        """List files in MinIO bucket"""
        try:
            files = []
            objects = self.client.list_objects(
                bucket_name=bucket,
                prefix=prefix,
                recursive=recursive
            )
            
            for obj in objects:
                file_info = FileInfo(
                    name=obj.object_name,
                    size=obj.size,
                    last_modified=obj.last_modified,
                    content_type=obj.content_type,
                    etag=obj.etag,
                    bucket=bucket,
                    is_directory=obj.object_name.endswith('/'),
                    metadata={}
                )
                files.append(file_info)
            
            return files
            
        except S3Error as e:
            logger.error(f"MinIO error listing files in {bucket}/{prefix}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing files in {bucket}/{prefix}: {e}")
            return []
    
    async def get_file_content(self, bucket: str, file_path: str) -> bytes:
        """Get file content from MinIO"""
        try:
            response = self.client.get_object(bucket, file_path)
            content = response.read()
            response.close()
            response.release_conn()
            return content
            
        except S3Error as e:
            logger.error(f"MinIO error getting file {bucket}/{file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting file {bucket}/{file_path}: {e}")
            raise
    
    async def put_file_content(self, bucket: str, file_path: str, content: bytes) -> bool:
        """Put file content to MinIO"""
        try:
            from io import BytesIO
            
            # Ensure bucket exists
            await self.create_bucket(bucket)
            
            content_stream = BytesIO(content)
            self.client.put_object(
                bucket_name=bucket,
                object_name=file_path,
                data=content_stream,
                length=len(content)
            )
            
            logger.debug(f"Successfully uploaded file to {bucket}/{file_path}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO error putting file {bucket}/{file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error putting file {bucket}/{file_path}: {e}")
            return False
    
    async def delete_file(self, bucket: str, file_path: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(bucket, file_path)
            logger.debug(f"Successfully deleted file {bucket}/{file_path}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO error deleting file {bucket}/{file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file {bucket}/{file_path}: {e}")
            return False
    
    async def copy_file(self, source_bucket: str, source_path: str, dest_bucket: str, dest_path: str) -> bool:
        """Copy file in MinIO"""
        try:
            from minio.commonconfig import CopySource
            
            # Ensure destination bucket exists
            await self.create_bucket(dest_bucket)
            
            copy_source = CopySource(source_bucket, source_path)
            self.client.copy_object(
                bucket_name=dest_bucket,
                object_name=dest_path,
                source=copy_source
            )
            
            logger.debug(f"Successfully copied file from {source_bucket}/{source_path} to {dest_bucket}/{dest_path}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO error copying file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False
    
    async def move_file(self, source_bucket: str, source_path: str, dest_bucket: str, dest_path: str) -> bool:
        """Move file in MinIO (copy + delete)"""
        try:
            # Copy file first
            if await self.copy_file(source_bucket, source_path, dest_bucket, dest_path):
                # Delete original file
                if await self.delete_file(source_bucket, source_path):
                    logger.debug(f"Successfully moved file from {source_bucket}/{source_path} to {dest_bucket}/{dest_path}")
                    return True
                else:
                    # If delete fails, try to clean up the copy
                    await self.delete_file(dest_bucket, dest_path)
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False
    
    async def file_exists(self, bucket: str, file_path: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self.client.stat_object(bucket, file_path)
            return True
            
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            logger.error(f"MinIO error checking file existence {bucket}/{file_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking file existence {bucket}/{file_path}: {e}")
            return False
    
    async def get_file_info(self, bucket: str, file_path: str) -> Optional[FileInfo]:
        """Get file information from MinIO"""
        try:
            stat = self.client.stat_object(bucket, file_path)
            
            return FileInfo(
                name=file_path,
                size=stat.size,
                last_modified=stat.last_modified,
                content_type=stat.content_type,
                etag=stat.etag,
                bucket=bucket,
                is_directory=file_path.endswith('/'),
                metadata=stat.metadata or {}
            )
            
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            logger.error(f"MinIO error getting file info {bucket}/{file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting file info {bucket}/{file_path}: {e}")
            return None
    
    async def create_bucket(self, bucket: str) -> bool:
        """Create bucket in MinIO if it doesn't exist"""
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.debug(f"Created bucket: {bucket}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO error creating bucket {bucket}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating bucket {bucket}: {e}")
            return False
    
    async def delete_bucket(self, bucket: str, force: bool = False) -> bool:
        """Delete bucket from MinIO"""
        try:
            if force:
                # Delete all objects in bucket first
                objects = self.client.list_objects(bucket, recursive=True)
                for obj in objects:
                    self.client.remove_object(bucket, obj.object_name)
            
            self.client.remove_bucket(bucket)
            logger.debug(f"Deleted bucket: {bucket}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO error deleting bucket {bucket}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting bucket {bucket}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MinIO health"""
        try:
            start_time = datetime.now()
            
            # Try to list buckets as a health check
            buckets = self.client.list_buckets()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "healthy": True,
                "service_name": "MinIO",
                "endpoint": self.endpoint,
                "response_time_ms": response_time,
                "buckets_count": len(buckets)
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "service_name": "MinIO",
                "endpoint": self.endpoint,
                "error": str(e)
            }

