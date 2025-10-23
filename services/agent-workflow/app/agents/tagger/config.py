"""
Configuration for TaggerAgent
"""
import os
from dataclasses import dataclass


@dataclass
class TaggerConfig:
    """Configuration for TaggerAgent"""
    
    # Confidence thresholds
    min_classification_confidence: float = 0.6
    min_semantic_type_confidence: float = 0.5  # Lower threshold for semantic type influence
    min_alignment_confidence: float = 0.4       # Lower threshold for alignment influence
    
    # Confidence weights (how much each factor contributes)
    semantic_type_weight: float = 0.40
    synonym_match_weight: float = 0.25
    pattern_weight: float = 0.20
    context_weight: float = 0.15
    
    # Upstream confidence multiplier thresholds
    # If upstream confidence is below these, reduce final confidence
    semantic_confidence_threshold: float = 0.7
    alignment_confidence_threshold: float = 0.6
    
    # Feature flags
    enable_pii_classification: bool = True
    enable_finance_classification: bool = True
    enable_temporal_classification: bool = True
    enable_domain_classification: bool = True
    enable_data_quality_classification: bool = True
    
    # Pattern matching
    fuzzy_match_threshold: float = 0.7
    
    @classmethod
    def from_env(cls) -> 'TaggerConfig':
        """Create config from environment variables"""
        return cls(
            min_classification_confidence=float(os.getenv("TAGGER_MIN_CONFIDENCE", "0.6")),
            min_semantic_type_confidence=float(os.getenv("TAGGER_MIN_SEMANTIC_CONFIDENCE", "0.5")),
            min_alignment_confidence=float(os.getenv("TAGGER_MIN_ALIGNMENT_CONFIDENCE", "0.4")),
            
            semantic_type_weight=float(os.getenv("TAGGER_SEMANTIC_WEIGHT", "0.40")),
            synonym_match_weight=float(os.getenv("TAGGER_SYNONYM_WEIGHT", "0.25")),
            pattern_weight=float(os.getenv("TAGGER_PATTERN_WEIGHT", "0.20")),
            context_weight=float(os.getenv("TAGGER_CONTEXT_WEIGHT", "0.15")),
            
            enable_pii_classification=os.getenv("TAGGER_ENABLE_PII", "true").lower() == "true",
            enable_finance_classification=os.getenv("TAGGER_ENABLE_FINANCE", "true").lower() == "true",
            enable_temporal_classification=os.getenv("TAGGER_ENABLE_TEMPORAL", "true").lower() == "true",
            enable_domain_classification=os.getenv("TAGGER_ENABLE_DOMAIN", "true").lower() == "true",
            enable_data_quality_classification=os.getenv("TAGGER_ENABLE_DATA_QUALITY", "true").lower() == "true",
            
            fuzzy_match_threshold=float(os.getenv("TAGGER_FUZZY_THRESHOLD", "0.7"))
        )

