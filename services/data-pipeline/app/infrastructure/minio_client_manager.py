"""
MinIO Client Manager for centralized MinIO client management
"""

import logging
from typing import Optional, List, Dict, Any
from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import MaxRetryError
import os

logger = logging.getLogger(__name__)


class MinioClientManager:
    """Singleton manager for MinIO client connections"""
    
    _instance: Optional['MinioClientManager'] = None
    _client: Optional[Minio] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MinioClientManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the MinIO client manager"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._config = self._get_config()
            logger.info("Initializing MinioClientManager")
    
    def _get_config(self) -> Dict[str, str]:
        """Get MinIO configuration from environment variables"""
        return {
            "endpoint": os.getenv("MINIO_ENDPOINT", "minio:9000"),
            "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            "secure": os.getenv("MINIO_SECURE", "false").lower() == "true"
        }
    
    @classmethod
    def get_client(cls) -> Minio:
        """Get or create the MinIO client"""
        instance = cls()
        if instance._client is None:
            instance._client = instance._create_client()
        return instance._client
    
    def _create_client(self) -> Minio:
        """Create a new MinIO client"""
        logger.info(f"Creating MinIO client for endpoint: {self._config['endpoint']}")
        
        try:
            client = Minio(
                endpoint=self._config["endpoint"],
                access_key=self._config["access_key"],
                secret_key=self._config["secret_key"],
                secure=self._config["secure"]
            )
            
            # Test connection
            if self._test_connection(client):
                logger.info("MinIO client created and connection verified")
                return client
            else:
                raise Exception("MinIO connection test failed")
                
        except Exception as e:
            logger.error(f"Failed to create MinIO client: {e}")
            raise
    
    def _test_connection(self, client: Minio) -> bool:
        """Test MinIO connection"""
        try:
            # Try to list buckets to test connection
            list(client.list_buckets())
            return True
        except (S3Error, MaxRetryError, Exception) as e:
            logger.error(f"MinIO connection test failed: {e}")
            return False
    
    @classmethod
    def ensure_bucket_exists(cls, bucket_name: str) -> bool:
        """Ensure a bucket exists, create if it doesn't"""
        client = cls.get_client()
        
        try:
            if not client.bucket_exists(bucket_name):
                logger.info(f"Creating bucket: {bucket_name}")
                client.make_bucket(bucket_name)
                logger.info(f"Bucket created successfully: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to ensure bucket exists {bucket_name}: {e}")
            return False
    
    @classmethod
    def list_objects(cls, bucket_name: str, prefix: str = "", recursive: bool = True) -> List[Dict[str, Any]]:
        """List objects in a bucket with optional prefix"""
        client = cls.get_client()
        
        try:
            objects = []
            for obj in client.list_objects(bucket_name, prefix=prefix, recursive=recursive):
                objects.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified,
                    "content_type": obj.content_type
                })
            return objects
        except S3Error as e:
            logger.error(f"Failed to list objects in bucket {bucket_name}: {e}")
            return []
    
    @classmethod
    def object_exists(cls, bucket_name: str, object_name: str) -> bool:
        """Check if an object exists in a bucket"""
        client = cls.get_client()
        
        try:
            client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False
    
    @classmethod
    def get_object_info(cls, bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
        """Get information about an object"""
        client = cls.get_client()
        
        try:
            stat = client.stat_object(bucket_name, object_name)
            return {
                "object_name": object_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
        except S3Error as e:
            logger.error(f"Failed to get object info for {bucket_name}/{object_name}: {e}")
            return None
    
    @classmethod
    def delete_object(cls, bucket_name: str, object_name: str) -> bool:
        """Delete an object from a bucket"""
        client = cls.get_client()
        
        try:
            client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted object: {bucket_name}/{object_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete object {bucket_name}/{object_name}: {e}")
            return False
    
    @classmethod
    def delete_objects(cls, bucket_name: str, object_names: List[str]) -> Dict[str, bool]:
        """Delete multiple objects from a bucket"""
        client = cls.get_client()
        results = {}
        
        try:
            # MinIO supports batch delete
            from minio.deleteobjects import DeleteObject
            delete_objects = [DeleteObject(name) for name in object_names]
            
            errors = client.remove_objects(bucket_name, delete_objects)
            
            # Process results
            for name in object_names:
                results[name] = True
            
            # Mark failed deletions
            for error in errors:
                results[error.object_name] = False
                logger.error(f"Failed to delete {error.object_name}: {error}")
                
        except Exception as e:
            logger.error(f"Batch delete failed: {e}")
            # Fallback to individual deletions
            for name in object_names:
                results[name] = cls.delete_object(bucket_name, name)
        
        return results
    
    @classmethod
    def get_presigned_url(cls, bucket_name: str, object_name: str, expires_in_seconds: int = 3600) -> Optional[str]:
        """Get a presigned URL for an object"""
        client = cls.get_client()
        
        try:
            from datetime import timedelta
            url = client.presigned_get_object(
                bucket_name, 
                object_name, 
                expires=timedelta(seconds=expires_in_seconds)
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {bucket_name}/{object_name}: {e}")
            return None
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get information about the MinIO client configuration"""
        return {
            "endpoint": self._config["endpoint"],
            "secure": self._config["secure"],
            "connected": self._client is not None,
            "connection_test": self._test_connection(self._client) if self._client else False
        }
    
    @classmethod
    def reset_client(cls) -> None:
        """Reset the MinIO client (force reconnection)"""
        instance = cls()
        if instance._client is not None:
            logger.info("Resetting MinIO client")
            instance._client = None

