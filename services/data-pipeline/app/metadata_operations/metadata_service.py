"""
Unified metadata service with pluggable stores and intelligent fallback
"""

import logging
import os
from typing import Dict, Any, List, Optional
from .metadata_store_interface import MetadataStoreInterface
from .openmetadata_store import OpenMetadataStore
from .file_metadata_store import FileMetadataStore
from .models import (
    MetadataStorageRequest,
    MetadataStorageResult,
    MetadataStoreType,
    MetadataEntity,
    MetadataRelationship
)

logger = logging.getLogger(__name__)


class MetadataService:
    """
    Unified metadata service that manages multiple metadata stores
    with intelligent fallback and retry mechanisms
    """
    
    def __init__(self):
        """Initialize the metadata service with configured stores"""
        self.primary_store: Optional[MetadataStoreInterface] = None
        self.fallback_store: Optional[MetadataStoreInterface] = None
        self.initialized = False
        
        # Configuration - use OpenMetadata as primary with file fallback until JWT is fixed
        self.primary_store_type = os.getenv("METADATA_STORE_TYPE", "openmetadata").lower()
        self.enable_fallback = True  # Keep fallback until OpenMetadata JWT is properly configured
        self.fallback_path = os.getenv("METADATA_FALLBACK_PATH", "/tmp/metadata")
        
        # OpenMetadata configuration
        self.openmetadata_host = os.getenv("OPENMETADATA_HOST", "openmetadata-server")
        self.openmetadata_port = os.getenv("OPENMETADATA_PORT", "8585")
        self.openmetadata_admin_email = os.getenv("OPENMETADATA_ADMIN_EMAIL", "admin@open-metadata.org")
    
    async def initialize(self) -> bool:
        """Initialize the metadata service with OpenMetadata only"""
        try:
            logger.info("Initializing metadata service...")
            
            # Initialize OpenMetadata store only
            if self.primary_store_type == "openmetadata":
                self.primary_store = OpenMetadataStore(
                    self.openmetadata_host,
                    self.openmetadata_port,
                    self.openmetadata_admin_email
                )
                
                # Initialize the store
                primary_initialized = await self.primary_store.initialize()
                
                if primary_initialized:
                    self.initialized = True
                    logger.info("✅ OpenMetadata store initialized successfully")
                    return True
                else:
                    logger.error("❌ OpenMetadata store initialization failed")
                    return False
            else:
                logger.error(f"❌ Unsupported store type: {self.primary_store_type}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to initialize metadata service: {e}")
            return False
    
    async def store_schema_metadata(self, run_id: str, job_id: str, schema_data: Dict[str, Any], websocket_manager=None) -> MetadataStorageResult:
        """
        Store schema metadata using the configured stores with intelligent fallback
        
        Args:
            run_id: Pipeline run identifier
            job_id: Job identifier 
            schema_data: Schema data with entities, relationships, and business metadata
            websocket_manager: WebSocket manager for status updates
            
        Returns:
            Result of the metadata storage operation
        """
        if not self.initialized:
            if not await self.initialize():
                return MetadataStorageResult(
                    success=False,
                    store_type=MetadataStoreType.FILE_BASED,
                    stored_entities=0,
                    stored_relationships=0,
                    stored_lineage=0,
                    errors=["Metadata service not initialized"]
                )
        
        logger.info(f"Storing metadata for job {job_id} (run: {run_id})")
        
        # Convert schema_data to structured request
        request = self._convert_schema_data_to_request(run_id, job_id, schema_data)
        
        # Store in OpenMetadata only
        if self.primary_store:
            try:
                logger.info(f"Storing metadata in OpenMetadata")
                result = await self.primary_store.store_metadata(request)
                
                if result.success:
                    logger.info(f"✅ Metadata successfully stored in OpenMetadata")
                    return result
                else:
                    logger.error(f"OpenMetadata storage failed: {result.errors}")
                    return result
                    
            except Exception as e:
                logger.error(f"OpenMetadata storage error: {e}")
                return MetadataStorageResult(
                    success=False,
                    store_type=MetadataStoreType.OPENMETADATA,
                    stored_entities=0,
                    stored_relationships=0,
                    stored_lineage=0,
                    errors=[f"OpenMetadata error: {str(e)}"]
                )
        
        # No store available
        return MetadataStorageResult(
            success=False,
            store_type=MetadataStoreType.OPENMETADATA,
            stored_entities=0,
            stored_relationships=0,
            stored_lineage=0,
            errors=["No metadata store available"]
        )
    
    def _convert_schema_data_to_request(self, run_id: str, job_id: str, schema_data: Dict[str, Any]) -> MetadataStorageRequest:
        """Convert legacy schema_data format to structured request"""
        entities = []
        relationships = []
        
        # Convert entities
        for entity_data in schema_data.get('entities', []):
            entity = MetadataEntity(
                name=entity_data.get('name', ''),
                description=entity_data.get('description'),
                entity_type=entity_data.get('entity_type', 'table'),
                schema_data={
                    'columns': entity_data.get('column_details', []),
                    'primary_keys': entity_data.get('primary_keys', []),
                    'business_metadata': entity_data.get('business_metadata', {})
                },
                business_metadata=entity_data.get('business_metadata'),
                tags=entity_data.get('tags', []),
                owner=entity_data.get('owner')
            )
            entities.append(entity)
        
        # Convert relationships
        logger.info(f"All schema data relationships: {schema_data.get('relationships')}")
        for rel_data in schema_data.get('relationships', []):
            relationship = MetadataRelationship(
                from_entity=rel_data.get('from_entity') or rel_data.get('from', ''),
                to_entity=rel_data.get('to_entity') or rel_data.get('to', ''),
                from_column=rel_data.get('from_column') or rel_data.get('foreign_key', ''),
                to_column=rel_data.get('to_column') or rel_data.get('references', ''),
                relationship_type=rel_data.get('relationship_type') or rel_data.get('type', 'foreign_key'),
                description=rel_data.get('description')
            )
            relationships.append(relationship)
        
        return MetadataStorageRequest(
            run_id=run_id,
            job_id=job_id,
            entities=entities,
            relationships=relationships,
            pipeline_metadata={
                'pipeline_run_id': run_id,
                'job_id': job_id,
                'original_schema_data': schema_data
            }
        )
    
    async def get_entity(self, entity_name: str) -> Optional[MetadataEntity]:
        """Retrieve an entity by name from available stores"""
        if not self.initialized:
            await self.initialize()
        
        # Try primary store first
        if self.primary_store:
            try:
                entity = await self.primary_store.get_entity(entity_name)
                if entity:
                    return entity
            except Exception as e:
                logger.warning(f"Primary store error retrieving entity {entity_name}: {e}")
        
        # Try fallback store
        if self.fallback_store:
            try:
                return await self.fallback_store.get_entity(entity_name)
            except Exception as e:
                logger.warning(f"Fallback store error retrieving entity {entity_name}: {e}")
        
        return None
    
    async def get_relationships(self, entity_name: str) -> List[MetadataRelationship]:
        """Get all relationships for an entity from available stores"""
        if not self.initialized:
            await self.initialize()
        
        relationships = []
        
        # Try primary store first
        if self.primary_store:
            try:
                primary_relationships = await self.primary_store.get_relationships(entity_name)
                relationships.extend(primary_relationships)
            except Exception as e:
                logger.warning(f"Primary store error retrieving relationships for {entity_name}: {e}")
        
        # Try fallback store if primary didn't return results
        if not relationships and self.fallback_store:
            try:
                fallback_relationships = await self.fallback_store.get_relationships(entity_name)
                relationships.extend(fallback_relationships)
            except Exception as e:
                logger.warning(f"Fallback store error retrieving relationships for {entity_name}: {e}")
        
        return relationships
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all configured stores"""
        health_status = {
            "metadata_service": "healthy",
            "stores": {}
        }
        
        if self.primary_store:
            try:
                primary_health = await self.primary_store.health_check()
                health_status["stores"]["primary"] = {
                    "type": self.primary_store_type,
                    "healthy": primary_health.healthy,
                    "service_name": primary_health.service_name,
                    "version": primary_health.version,
                    "response_time_ms": primary_health.response_time_ms,
                    "error": primary_health.error_message
                }
            except Exception as e:
                health_status["stores"]["primary"] = {
                    "type": self.primary_store_type,
                    "healthy": False,
                    "error": str(e)
                }
        
        if self.fallback_store:
            try:
                fallback_health = await self.fallback_store.health_check()
                health_status["stores"]["fallback"] = {
                    "type": "file_based",
                    "healthy": fallback_health.healthy,
                    "service_name": fallback_health.service_name,
                    "version": fallback_health.version,
                    "response_time_ms": fallback_health.response_time_ms,
                    "error": fallback_health.error_message
                }
            except Exception as e:
                health_status["stores"]["fallback"] = {
                    "type": "file_based",
                    "healthy": False,
                    "error": str(e)
                }
        
        # Overall health
        all_stores_healthy = all(
            store.get("healthy", False) 
            for store in health_status["stores"].values()
        )
        
        if not all_stores_healthy:
            # Check if at least one store is healthy
            any_store_healthy = any(
                store.get("healthy", False) 
                for store in health_status["stores"].values()
            )
            health_status["metadata_service"] = "degraded" if any_store_healthy else "unhealthy"
        
        return health_status
    
    async def cleanup(self) -> None:
        """Clean up all stores and resources"""
        logger.info("Cleaning up metadata service...")
        
        if self.primary_store:
            await self.primary_store.cleanup()
        
        if self.fallback_store:
            await self.fallback_store.cleanup()
        
        self.initialized = False

