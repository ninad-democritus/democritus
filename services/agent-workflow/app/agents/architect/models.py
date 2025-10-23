"""
Data models for ArchitectAgent
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class OpenMetadataType:
    """OpenMetadata data type with attributes"""
    data_type: str                              # Base type (VARCHAR, BIGINT, etc.)
    data_type_display: str                      # Human-readable (varchar(255), decimal(18,2))
    data_length: Optional[int] = None           # For VARCHAR, CHAR
    precision: Optional[int] = None             # For DECIMAL, NUMERIC
    scale: Optional[int] = None                 # For DECIMAL, NUMERIC
    array_data_type: Optional[str] = None       # For ARRAY types


@dataclass
class ColumnSchema:
    """Rich column schema with profiling stats and OpenMetadata types"""
    name: str
    canonical_name: str
    raw_names: List[str]
    synonyms: List[str]
    
    # OpenMetadata-compatible type fields
    data_type: str                              # OpenMetadata type (VARCHAR, BIGINT, etc.)
    data_type_display: str                      # Human-readable (varchar(255), decimal(18,2))
    data_length: Optional[int] = None           # For VARCHAR, CHAR
    precision: Optional[int] = None             # For DECIMAL, NUMERIC
    scale: Optional[int] = None                 # For DECIMAL, NUMERIC
    
    semantic_type: str                          # Semantic type (email, uuid, etc.)
    semantic_type_confidence: float             # Confidence in semantic type detection
    alignment_confidence: float                 # Confidence in column alignment (from clustering)
    nullable: bool
    is_primary_key: bool
    is_unique: bool
    
    # Statistics from profiling
    distinct_count: int
    total_count: int
    null_percentage: float
    sample_values: List[Any] = field(default_factory=list)
    min_value: Any = None
    max_value: Any = None
    mean_value: Any = None
    
    # Helper properties
    @property
    def is_identifier_type(self) -> bool:
        """Check if semantic type suggests identifier"""
        return self.semantic_type.lower() in ['uuid', 'identifier', 'ssn']
    
    @property
    def is_contact_type(self) -> bool:
        """Check if semantic type is contact info"""
        return self.semantic_type.lower() in ['email', 'phone_number', 'address']
    
    @property
    def is_temporal_type(self) -> bool:
        """Check if semantic type is temporal"""
        st = self.semantic_type.lower()
        return 'date' in st or 'time' in st


@dataclass
class SchemaEntity:
    """Enhanced schema entity with full column metadata"""
    entity_id: str
    canonical_name: str
    raw_names: List[str]
    synonyms: List[str]
    table_name: str
    primary_key: str
    columns: List[ColumnSchema]
    entity_type: str                            # fact/dimension
    row_count: int
    source_files: List[str]
    alignment_confidence: float


@dataclass
class RelationshipCandidate:
    """Intermediate candidate before final confidence calculation"""
    from_entity: SchemaEntity
    to_entity: SchemaEntity
    from_column: ColumnSchema
    to_column: ColumnSchema
    detection_source: str                       # fk_pattern, common_column, llm, semantic_hint
    raw_scores: Dict[str, float]                # name_similarity, semantic_compatibility, etc.


@dataclass
class Relationship:
    """Enhanced relationship with confidence breakdown"""
    relationship_id: str
    from_entity: str
    to_entity: str
    from_column: str
    to_column: str
    cardinality: str                            # many-to-one, one-to-many, one-to-one, many-to-many
    confidence: float
    confidence_breakdown: Dict[str, float]      # Detailed scoring factors
    detection_method: str                       # rule_based, llm, hybrid, semantic
    semantic_description: str                   # "Each Order belongs to one Customer"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaGraph:
    """Complete schema graph representation"""
    entities: List[SchemaEntity]
    relationships: List[Relationship]
    metadata_summary: Dict[str, Any] = field(default_factory=dict)

