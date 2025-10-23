"""
Abstract base class for file loaders
"""
from abc import ABC, abstractmethod
import pandas as pd


class FileLoader(ABC):
    """Abstract file loader interface"""
    
    @abstractmethod
    def can_load(self, file_name: str) -> bool:
        """
        Check if this loader can handle the file
        
        Args:
            file_name: Name of the file
            
        Returns:
            True if this loader can handle the file
        """
        pass
    
    @abstractmethod
    def load(self, file_data: bytes) -> pd.DataFrame:
        """
        Load file data into DataFrame
        
        Args:
            file_data: Raw file bytes
            
        Returns:
            pandas DataFrame
        """
        pass

