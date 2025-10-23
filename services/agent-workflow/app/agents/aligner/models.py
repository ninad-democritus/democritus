"""
Data models for AlignerAgent
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class CanonicalColumn:
    """Canonical column representation after alignment"""
    canonical_name: str
    raw_names: List[str]  # All source column names that clustered together
    synonyms: List[str]
    semantic_type: str
    semantic_type_confidence: float
    data_type: str
    is_pk: bool
    confidence: float  # Alignment confidence (clustering quality)
    stats: Dict[str, Any]  # Merged statistics


@dataclass
class CanonicalEntity:
    """Canonical entity representation after alignment"""
    entity_id: str
    canonical_name: str
    raw_names: List[str]  # All source file/entity names
    synonyms: List[str]
    type: str  # 'fact' or 'dimension'
    confidence: float
    source_files: List[str]
    columns: List[CanonicalColumn]
    primary_key_candidates: List[Dict[str, Any]]


@dataclass
class EntityCluster:
    """Cluster of entity-level names"""
    cluster_id: int
    members: List[Dict[str, Any]]  # Each: {raw_name, file_id, normalized, embedding_idx, file_profile}
    centroid: Any  # numpy array
    variance: float


@dataclass
class ColumnCluster:
    """Cluster of column-level names"""
    cluster_id: int
    members: List[Dict[str, Any]]  # Each: {raw_name, fqn, file_id, column_profile, embedding_idx, ...}
    centroid: Any  # numpy array
    variance: float

