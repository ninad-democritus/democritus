"""
Data models for ContextAgent
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class EntityContext:
    """Context bundle for entity narrative generation"""
    canonical_name: str
    synonyms: List[str]
    entity_type: str  # fact/dimension
    confidence: float
    primary_key: Dict[str, Any]
    columns: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    classifications: List[str]
    glossary_terms: List[str]
    row_count: int
    domain: Optional[str] = None


@dataclass
class ColumnContext:
    """Context bundle for column narrative generation"""
    name: str
    canonical_name: str
    entity_name: str
    fqn: str
    semantic_type: str
    semantic_type_confidence: float
    data_type: str
    data_type_display: str
    nullable: bool
    is_primary_key: bool
    classifications: List[str]
    glossary_term: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None
    relationships: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RelationshipContext:
    """Context bundle for relationship narrative generation"""
    from_entity: str
    to_entity: str
    from_column: str
    to_column: str
    cardinality: str
    confidence: float
    confidence_factors: Dict[str, float]
    detection_method: str
    entity_types: Dict[str, str]
    column_semantics: Dict[str, Any]


@dataclass
class GlossaryContext:
    """Context bundle for glossary/domain narrative generation"""
    name: str
    display_name: str
    entities: List[Dict[str, Any]]
    terms: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    classification_profile: Dict[str, int]
    data_characteristics: Dict[str, Any]


@dataclass
class MinimalEntity:
    """Minimal entity representation for output"""
    name: str
    displayName: str
    synonyms: List[str]
    tableType: str
    description: str
    tags: List[str]
    columns: List['MinimalColumn']
    confidence: Optional[float] = None


@dataclass
class MinimalColumn:
    """Minimal column representation for output"""
    name: str
    displayName: str
    synonyms: List[str]
    description: str
    dataType: str
    dataTypeDisplay: str
    dataLength: Optional[int]
    precision: Optional[int]
    scale: Optional[int]
    constraint: Optional[str]
    nullable: bool
    tags: List[str]
    glossaryTerms: List[str] = field(default_factory=list)
    confidence: Optional[float] = None


@dataclass
class MinimalRelationship:
    """Minimal relationship representation for output"""
    fromEntity: str
    toEntity: str
    fromColumn: str
    toColumn: str
    relationshipType: str
    cardinality: str
    description: str
    confidence: Optional[float] = None


@dataclass
class MinimalGlossaryTerm:
    """Minimal glossary term representation for output"""
    name: str
    displayName: str
    description: str
    synonyms: List[str]
    relatedTerms: List[str]
    tags: List[str]
    references: List[Dict[str, str]]


@dataclass
class MinimalGlossary:
    """Minimal glossary representation for output"""
    name: str
    displayName: str
    description: str
    terms: List[MinimalGlossaryTerm]


@dataclass
class ContextOutput:
    """Complete context agent output (minimal format)"""
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    glossaries: List[Dict[str, Any]]
    summary: Dict[str, Any]

