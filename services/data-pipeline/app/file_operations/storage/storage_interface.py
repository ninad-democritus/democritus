"""
Abstract interface for storage backends
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
from ..models import FileInfo


class StorageInterface(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def list_files(self, bucket: str, prefix: str = "", recursive: bool = True) -> List[FileInfo]:
        """
        List files in a bucket with optional prefix
        
        Args:
            bucket: Bucket name
            prefix: Optional prefix to filter files
            recursive: Whether to list files recursively
            
        Returns:
            List of file information objects
        """
        pass
    
    @abstractmethod
    async def get_file_content(self, bucket: str, file_path: str) -> bytes:
        """
        Get content of a specific file
        
        Args:
            bucket: Bucket name
            file_path: Path to the file
            
        Returns:
            File content as bytes
        """
        pass
    
    @abstractmethod
    async def put_file_content(self, bucket: str, file_path: str, content: bytes) -> bool:
        """
        Put content to a specific file
        
        Args:
            bucket: Bucket name
            file_path: Path to the file
            content: Content to write
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_file(self, bucket: str, file_path: str) -> bool:
        """
        Delete a specific file
        
        Args:
            bucket: Bucket name
            file_path: Path to the file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def copy_file(self, source_bucket: str, source_path: str, dest_bucket: str, dest_path: str) -> bool:
        """
        Copy a file from source to destination
        
        Args:
            source_bucket: Source bucket name
            source_path: Source file path
            dest_bucket: Destination bucket name
            dest_path: Destination file path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def move_file(self, source_bucket: str, source_path: str, dest_bucket: str, dest_path: str) -> bool:
        """
        Move a file from source to destination
        
        Args:
            source_bucket: Source bucket name
            source_path: Source file path
            dest_bucket: Destination bucket name
            dest_path: Destination file path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def file_exists(self, bucket: str, file_path: str) -> bool:
        """
        Check if a file exists
        
        Args:
            bucket: Bucket name
            file_path: Path to the file
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_file_info(self, bucket: str, file_path: str) -> Optional[FileInfo]:
        """
        Get information about a specific file
        
        Args:
            bucket: Bucket name
            file_path: Path to the file
            
        Returns:
            File information if file exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def create_bucket(self, bucket: str) -> bool:
        """
        Create a bucket if it doesn't exist
        
        Args:
            bucket: Bucket name
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_bucket(self, bucket: str, force: bool = False) -> bool:
        """
        Delete a bucket
        
        Args:
            bucket: Bucket name
            force: Whether to force delete non-empty bucket
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the storage backend
        
        Returns:
            Health status information
        """
        pass

