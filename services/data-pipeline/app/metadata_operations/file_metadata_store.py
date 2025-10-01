"""
File-based metadata store implementation for fallback scenarios
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from .metadata_store_interface import MetadataStoreInterface
from .models import (
    MetadataStorageRequest,
    MetadataStorageResult,
    MetadataStoreType,
    HealthCheckResult,
    MetadataEntity,
    MetadataRelationship
)

logger = logging.getLogger(__name__)


class FileMetadataStore(MetadataStoreInterface):
    """File-based implementation of metadata store for fallback scenarios"""
    
    def __init__(self, storage_path: str = "/tmp/metadata"):
        """
        Initialize file-based metadata store
        
        Args:
            storage_path: Directory path for storing metadata files
        """
        self.storage_path = Path(storage_path)
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the file-based metadata store"""
        try:
            logger.info(f"Initializing file-based metadata store at {self.storage_path}")
            
            # Create storage directory if it doesn't exist
            self.storage_path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories for organization
            (self.storage_path / "entities").mkdir(exist_ok=True)
            (self.storage_path / "relationships").mkdir(exist_ok=True)
            (self.storage_path / "lineage").mkdir(exist_ok=True)
            (self.storage_path / "jobs").mkdir(exist_ok=True)
            
            self.initialized = True
            logger.info("✅ File-based metadata store initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize file-based metadata store: {e}")
            return False
    
    async def health_check(self) -> HealthCheckResult:
        """Check the health of file-based storage"""
        try:
            start_time = datetime.now()
            
            # Check if storage path is accessible
            if not self.storage_path.exists():
                return HealthCheckResult(
                    healthy=False,
                    service_name="FileMetadataStore",
                    error_message=f"Storage path does not exist: {self.storage_path}"
                )
            
            # Check if we can write to the storage path
            test_file = self.storage_path / "health_check.tmp"
            try:
                test_file.write_text("health_check")
                test_file.unlink()
            except Exception as e:
                return HealthCheckResult(
                    healthy=False,
                    service_name="FileMetadataStore",
                    error_message=f"Cannot write to storage path: {e}"
                )
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                healthy=True,
                service_name="FileMetadataStore",
                version="1.0.0",
                response_time_ms=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                service_name="FileMetadataStore",
                error_message=str(e)
            )
    
    async def store_metadata(self, request: MetadataStorageRequest) -> MetadataStorageResult:
        """Store metadata in files"""
        if not self.initialized:
            if not await self.initialize():
                return MetadataStorageResult(
                    success=False,
                    store_type=MetadataStoreType.FILE_BASED,
                    stored_entities=0,
                    stored_relationships=0,
                    stored_lineage=0,
                    errors=["File-based store not initialized"]
                )
        
        try:
            logger.info(f"Storing metadata for job {request.job_id} in file-based store")
            
            # Create job-specific metadata record
            job_metadata = {
                "run_id": request.run_id,
                "job_id": request.job_id,
                "timestamp": datetime.now().isoformat(),
                "entities": [entity.dict() for entity in request.entities],
                "relationships": [rel.dict() for rel in request.relationships],
                "lineage": [lineage.dict() for lineage in request.lineage] if request.lineage else [],
                "pipeline_metadata": request.pipeline_metadata,
                "entities_count": len(request.entities),
                "relationships_count": len(request.relationships),
                "lineage_count": len(request.lineage) if request.lineage else 0,
                "status": "stored_successfully"
            }
            
            # Store main job metadata
            job_file = self.storage_path / "jobs" / f"{request.job_id}_{request.run_id}_metadata.json"
            with open(job_file, 'w') as f:
                json.dump(job_metadata, f, indent=2, default=str)
            
            # Store individual entities
            stored_entities = 0
            for entity in request.entities:
                try:
                    entity_file = self.storage_path / "entities" / f"{entity.name}.json"
                    entity_data = entity.dict()
                    entity_data["last_updated"] = datetime.now().isoformat()
                    entity_data["job_id"] = request.job_id
                    entity_data["run_id"] = request.run_id
                    
                    with open(entity_file, 'w') as f:
                        json.dump(entity_data, f, indent=2, default=str)
                    stored_entities += 1
                except Exception as e:
                    logger.error(f"Failed to store entity {entity.name}: {e}")
            
            # Store relationships
            stored_relationships = 0
            for relationship in request.relationships:
                try:
                    rel_file = self.storage_path / "relationships" / f"{relationship.from_entity}_{relationship.to_entity}.json"
                    rel_data = relationship.dict()
                    rel_data["last_updated"] = datetime.now().isoformat()
                    rel_data["job_id"] = request.job_id
                    rel_data["run_id"] = request.run_id
                    
                    with open(rel_file, 'w') as f:
                        json.dump(rel_data, f, indent=2, default=str)
                    stored_relationships += 1
                except Exception as e:
                    logger.error(f"Failed to store relationship: {e}")
            
            # Store lineage
            stored_lineage = 0
            if request.lineage:
                for lineage in request.lineage:
                    try:
                        lineage_file = self.storage_path / "lineage" / f"{lineage.source_entity}_{lineage.target_entity}_{request.run_id}.json"
                        lineage_data = lineage.dict()
                        lineage_data["job_id"] = request.job_id
                        lineage_data["run_id"] = request.run_id
                        
                        with open(lineage_file, 'w') as f:
                            json.dump(lineage_data, f, indent=2, default=str)
                        stored_lineage += 1
                    except Exception as e:
                        logger.error(f"Failed to store lineage: {e}")
            
            logger.info(f"✅ Metadata stored to file: {job_file}")
            logger.info(f"Stored: {stored_entities} entities, {stored_relationships} relationships, {stored_lineage} lineage")
            
            return MetadataStorageResult(
                success=True,
                store_type=MetadataStoreType.FILE_BASED,
                stored_entities=stored_entities,
                stored_relationships=stored_relationships,
                stored_lineage=stored_lineage,
                fallback_used=True,
                storage_location=str(job_file)
            )
            
        except Exception as e:
            logger.error(f"Failed to store metadata in file-based store: {e}")
            return MetadataStorageResult(
                success=False,
                store_type=MetadataStoreType.FILE_BASED,
                stored_entities=0,
                stored_relationships=0,
                stored_lineage=0,
                errors=[str(e)]
            )
    
    async def get_entity(self, entity_name: str) -> Optional[MetadataEntity]:
        """Retrieve an entity by name"""
        try:
            entity_file = self.storage_path / "entities" / f"{entity_name}.json"
            if not entity_file.exists():
                return None
            
            with open(entity_file, 'r') as f:
                data = json.load(f)
            
            return MetadataEntity(
                name=data["name"],
                description=data.get("description"),
                entity_type=data["entity_type"],
                schema_data=data["schema_data"],
                business_metadata=data.get("business_metadata"),
                tags=data.get("tags"),
                owner=data.get("owner")
            )
            
        except Exception as e:
            logger.error(f"Error retrieving entity {entity_name}: {e}")
            return None
    
    async def get_relationships(self, entity_name: str) -> List[MetadataRelationship]:
        """Get all relationships for an entity"""
        try:
            relationships = []
            relationships_dir = self.storage_path / "relationships"
            
            if not relationships_dir.exists():
                return relationships
            
            # Find all relationship files that involve this entity
            for rel_file in relationships_dir.glob("*.json"):
                try:
                    with open(rel_file, 'r') as f:
                        data = json.load(f)
                    
                    if data.get("from_entity") == entity_name or data.get("to_entity") == entity_name:
                        relationships.append(MetadataRelationship(
                            from_entity=data["from_entity"],
                            to_entity=data["to_entity"],
                            from_column=data["from_column"],
                            to_column=data["to_column"],
                            relationship_type=data["relationship_type"],
                            description=data.get("description")
                        ))
                except Exception as e:
                    logger.warning(f"Error reading relationship file {rel_file}: {e}")
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error retrieving relationships for {entity_name}: {e}")
            return []
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up file-based metadata store resources")
        self.initialized = False
    
    def list_stored_jobs(self) -> List[Dict[str, Any]]:
        """List all stored job metadata"""
        try:
            jobs = []
            jobs_dir = self.storage_path / "jobs"
            
            if not jobs_dir.exists():
                return jobs
            
            for job_file in jobs_dir.glob("*_metadata.json"):
                try:
                    with open(job_file, 'r') as f:
                        data = json.load(f)
                    jobs.append({
                        "job_id": data.get("job_id"),
                        "run_id": data.get("run_id"),
                        "timestamp": data.get("timestamp"),
                        "entities_count": data.get("entities_count", 0),
                        "relationships_count": data.get("relationships_count", 0),
                        "file_path": str(job_file)
                    })
                except Exception as e:
                    logger.warning(f"Error reading job file {job_file}: {e}")
            
            return sorted(jobs, key=lambda x: x.get("timestamp", ""), reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing stored jobs: {e}")
            return []

