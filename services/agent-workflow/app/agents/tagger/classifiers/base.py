"""
Base classifier interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
from ..models import Classification
from ..config import TaggerConfig

logger = logging.getLogger(__name__)


class BaseClassifier(ABC):
    """Base class for all classifiers"""
    
    def __init__(self, config: TaggerConfig):
        """
        Initialize classifier with configuration
        
        Args:
            config: TaggerConfig instance
        """
        self.config = config
    
    @abstractmethod
    def classify_column(self, column: Dict[str, Any], entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify a single column
        
        Args:
            column: Column dictionary with metadata
            entity: Parent entity dictionary for context
            
        Returns:
            List of Classification objects
        """
        pass
    
    def classify_entity(self, entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify an entity (default: no classifications)
        
        Args:
            entity: Entity dictionary with metadata
            
        Returns:
            List of Classification objects
        """
        return []

