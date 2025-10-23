"""
Data models for TaggerAgent
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Classification:
    """A single classification tag with confidence and provenance"""
    tag: str
    confidence: float
    source: str  # What assigned this (semantic_type, pattern, stats, context, etc.)
    upstream_factors: Dict[str, float] = field(default_factory=dict)  # Upstream confidence that influenced this


@dataclass
class ClassificationResult:
    """Complete classification result for an entity or column"""
    entity_classifications: List[Classification]
    column_classifications: Dict[str, List[Classification]]  # column_name -> classifications
    summary: Dict[str, Any]

