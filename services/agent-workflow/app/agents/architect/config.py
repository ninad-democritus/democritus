"""
Configuration for ArchitectAgent
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ArchitectConfig:
    """Configuration for ArchitectAgent behavior"""
    
    # Relationship detection methods
    use_rule_based: bool = True
    use_statistical: bool = True
    use_llm_detection: bool = False
    use_llm_validation: bool = True
    use_llm_semantics: bool = True
    
    # Confidence thresholds
    min_confidence: float = 0.6
    llm_validation_threshold: float = 0.7        # Validate if confidence between 0.6-0.8
    
    # Cardinality analysis
    uniqueness_threshold_pk: float = 0.95        # For PK detection
    uniqueness_threshold_fk: float = 0.85        # For FK uniqueness
    many_to_one_ratio_threshold: float = 2.0     # Distinct count ratio for M:1 detection
    
    # Name similarity
    name_match_algorithm: str = "rapidfuzz"      # or "levenshtein"
    min_name_similarity: float = 0.7
    
    # Semantic type compatibility
    use_semantic_validation: bool = True
    semantic_weight: float = 0.4                 # Weight in confidence scoring
    
    # LLM settings
    llm_enabled: bool = False
    llm_batch_size: int = 5                      # Entities per LLM call
    llm_timeout: int = 30
    llm_max_retries: int = 2
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    
    @classmethod
    def from_env(cls) -> 'ArchitectConfig':
        """Create config from environment variables"""
        return cls(
            use_rule_based=os.getenv("ARCHITECT_USE_RULE_BASED", "true").lower() == "true",
            use_statistical=os.getenv("ARCHITECT_USE_STATISTICAL", "true").lower() == "true",
            use_llm_detection=os.getenv("ARCHITECT_USE_LLM_DETECTION", "false").lower() == "true",
            use_llm_validation=os.getenv("ARCHITECT_USE_LLM_VALIDATION", "true").lower() == "true",
            use_llm_semantics=os.getenv("ARCHITECT_USE_LLM_SEMANTICS", "true").lower() == "true",
            
            min_confidence=float(os.getenv("ARCHITECT_MIN_CONFIDENCE", "0.6")),
            llm_validation_threshold=float(os.getenv("ARCHITECT_LLM_VALIDATION_THRESHOLD", "0.7")),
            
            uniqueness_threshold_pk=float(os.getenv("ARCHITECT_PK_UNIQUENESS", "0.95")),
            uniqueness_threshold_fk=float(os.getenv("ARCHITECT_FK_UNIQUENESS", "0.85")),
            many_to_one_ratio_threshold=float(os.getenv("ARCHITECT_M2O_RATIO", "2.0")),
            
            name_match_algorithm=os.getenv("ARCHITECT_NAME_MATCH_ALGO", "rapidfuzz"),
            min_name_similarity=float(os.getenv("ARCHITECT_MIN_NAME_SIMILARITY", "0.7")),
            
            use_semantic_validation=os.getenv("ARCHITECT_USE_SEMANTIC", "true").lower() == "true",
            semantic_weight=float(os.getenv("ARCHITECT_SEMANTIC_WEIGHT", "0.4")),
            
            ollama_host=os.getenv("OLLAMA_HOST", "http://ollama:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        )

