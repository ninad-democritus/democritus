"""
Data models for GlossaryAgent
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CandidateTerm:
    """A candidate glossary term before clustering"""
    raw_term: str
    normalized_term: str
    canonical_name: str
    source_type: str  # 'entity', 'column', 'pk_candidate'
    source_fqn: str  # Fully qualified name (e.g., "Customer.email")
    
    # From ProfilerAgent
    sample_values: List[Any] = field(default_factory=list)
    semantic_type: str = "unknown"
    semantic_type_confidence: float = 0.0
    
    # From AlignerAgent
    alignment_confidence: float = 0.0
    synonyms: List[str] = field(default_factory=list)
    raw_names: List[str] = field(default_factory=list)
    entity_type: str = "unknown"  # fact/dimension
    is_primary_key: bool = False
    pk_confidence: float = 0.0
    pk_explanation: str = ""
    
    # From TaggerAgent
    classifications: List[str] = field(default_factory=list)
    classification_confidence: float = 0.0
    
    # From ArchitectAgent
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    
    # Embeddings (computed)
    embedding: Any = None


@dataclass
class TermCluster:
    """Cluster of semantically similar terms"""
    cluster_id: int
    members: List[CandidateTerm]
    centroid: Any  # numpy array
    variance: float
    representative_term: Optional[CandidateTerm] = None


@dataclass
class GlossaryTerm:
    """Canonical glossary term with OpenMetadata compatibility"""
    term_id: str
    canonical_name: str
    display_name: str
    definition: str
    synonyms: List[str]
    confidence: float
    confidence_breakdown: Dict[str, float]
    
    # OpenMetadata associations
    associated_entities: List[Dict[str, str]]  # [{id: "Customer", type: "table"}, ...]
    associated_columns: List[Dict[str, str]]   # [{id: "Customer.email", type: "column"}, ...]
    
    # Relationships
    related_terms: List[str]  # Term IDs
    related_via_relationships: List[Dict[str, Any]]
    
    # Metadata
    classifications: List[str]
    is_key_identifier: bool
    entity_type: str
    sample_values: List[Any] = field(default_factory=list)
    
    # Provenance
    source_file_terminology: Dict[str, str] = field(default_factory=dict)
    pk_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainCluster:
    """Cluster of terms forming a business domain"""
    cluster_id: int
    term_clusters: List[TermCluster]
    dominant_classifications: List[str]
    entity_types: List[str]
    centroid: Any = None
    variance: float = 0.0


@dataclass
class Glossary:
    """OpenMetadata-compatible glossary (one per domain)"""
    glossary_id: str
    name: str  # CamelCase for API
    display_name: str
    description: str
    terms: List[GlossaryTerm]
    confidence: float
    
    # Metadata
    classification_summary: Dict[str, int] = field(default_factory=dict)
    entity_types: List[str] = field(default_factory=list)
    source_entities: List[str] = field(default_factory=list)


@dataclass
class GlossaryOutput:
    """Complete glossary agent output"""
    glossaries: List[Glossary]
    metadata_summary: Dict[str, Any]

