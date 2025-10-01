"""
Data models for metadata operations
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class MetadataStoreType(str, Enum):
    """Types of metadata stores"""
    OPENMETADATA = "openmetadata"
    FILE_BASED = "file_based"
    ATLAS = "atlas"  # Future implementation
    DATAHUB = "datahub"  # Future implementation


class AuthenticationType(str, Enum):
    """Types of authentication"""
    BASIC = "basic"
    JWT = "jwt"
    OAUTH = "oauth"
    NO_AUTH = "no_auth"


class MetadataEntity(BaseModel):
    """Represents a metadata entity"""
    name: str
    description: Optional[str] = None
    entity_type: str
    schema_data: Dict[str, Any]
    business_metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None


class MetadataRelationship(BaseModel):
    """Represents a relationship between entities"""
    from_entity: str
    to_entity: str
    from_column: str
    to_column: str
    relationship_type: str
    description: Optional[str] = None


class MetadataLineage(BaseModel):
    """Represents data lineage information"""
    source_entity: str
    target_entity: str
    transformation_logic: Optional[str] = None
    created_at: datetime
    created_by: str


class MetadataStorageRequest(BaseModel):
    """Request model for storing metadata"""
    run_id: str
    job_id: str
    entities: List[MetadataEntity]
    relationships: List[MetadataRelationship]
    lineage: Optional[List[MetadataLineage]] = None
    pipeline_metadata: Optional[Dict[str, Any]] = None


class MetadataStorageResult(BaseModel):
    """Result of metadata storage operation"""
    success: bool
    store_type: MetadataStoreType
    stored_entities: int
    stored_relationships: int
    stored_lineage: int
    errors: Optional[List[str]] = None
    fallback_used: bool = False
    storage_location: Optional[str] = None


class AuthenticationResult(BaseModel):
    """Result of authentication attempt"""
    success: bool
    auth_type: AuthenticationType
    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class HealthCheckResult(BaseModel):
    """Result of health check"""
    healthy: bool
    service_name: str
    version: Optional[str] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None

