"""
MinIO storage backend implementation
"""
from typing import List, Tuple
from minio import Minio
import logging
from .base import StorageBackend
from ..config import ProfilerConfig

logger = logging.getLogger(__name__)


class MinIOStorage(StorageBackend):
    """MinIO object storage implementation"""
    
    def __init__(self, config: ProfilerConfig):
        """
        Initialize MinIO storage backend
        
        Args:
            config: ProfilerConfig with MinIO connection details
        """
        self.endpoint = config.minio_endpoint
        self.bucket = config.minio_bucket
        self.client = self._create_client(config)
        logger.info(f"MinIO storage initialized: {self.endpoint}, bucket: {self.bucket}")
    
    def _create_client(self, config: ProfilerConfig) -> Minio:
        """Create MinIO client"""
        secure = False if ":9000" in config.minio_endpoint or config.minio_endpoint.startswith("minio") else True
        return Minio(
            config.minio_endpoint,
            access_key=config.minio_access_key,
            secret_key=config.minio_secret_key,
            secure=secure
        )
    
    def list_files(self, prefix: str) -> List[str]:
        """List all supported files in the given prefix"""
        try:
            objects = self.client.list_objects(
                self.bucket, 
                prefix=prefix, 
                recursive=True
            )
            
            file_paths = [
                obj.object_name 
                for obj in objects 
                if obj.object_name.endswith(('.csv', '.xlsx', '.xls'))
            ]
            
            logger.info(f"Found {len(file_paths)} files in {prefix}")
            return file_paths
            
        except Exception as e:
            logger.error(f"Failed to list files in {prefix}: {e}")
            raise
    
    def download_file(self, path: str) -> Tuple[bytes, int]:
        """Download file from MinIO"""
        try:
            response = self.client.get_object(self.bucket, path)
            data = response.read()
            size = len(data)
            response.close()
            
            logger.debug(f"Downloaded {path}: {size} bytes")
            return data, size
            
        except Exception as e:
            logger.error(f"Failed to download {path}: {e}")
            raise

