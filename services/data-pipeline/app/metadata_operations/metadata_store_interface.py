"""
Abstract interface for metadata stores
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .models import (
    MetadataStorageRequest, 
    MetadataStorageResult, 
    HealthCheckResult,
    MetadataEntity,
    MetadataRelationship
)


class MetadataStoreInterface(ABC):
    """Abstract base class for metadata stores"""
    
    @abstractmethod
    async def store_metadata(self, request: MetadataStorageRequest) -> MetadataStorageResult:
        """
        Store metadata in the underlying store
        
        Args:
            request: Metadata storage request
            
        Returns:
            Result of the storage operation
        """
        pass
    
    @abstractmethod
    async def get_entity(self, entity_name: str) -> Optional[MetadataEntity]:
        """
        Retrieve an entity by name
        
        Args:
            entity_name: Name of the entity to retrieve
            
        Returns:
            Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_relationships(self, entity_name: str) -> List[MetadataRelationship]:
        """
        Get all relationships for an entity
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            List of relationships
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """
        Check the health of the metadata store
        
        Returns:
            Health check result
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the metadata store connection
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up resources and connections
        """
        pass

