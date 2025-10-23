"""
Abstract base class for storage backends
"""
from abc import ABC, abstractmethod
from typing import List, Tuple


class StorageBackend(ABC):
    """Abstract storage backend interface"""
    
    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        """
        List all files matching prefix
        
        Args:
            prefix: Path prefix to search for files
            
        Returns:
            List of file paths
        """
        pass
    
    @abstractmethod
    def download_file(self, path: str) -> Tuple[bytes, int]:
        """
        Download file and return data with size
        
        Args:
            path: File path to download
            
        Returns:
            Tuple of (file_data, file_size)
        """
        pass

