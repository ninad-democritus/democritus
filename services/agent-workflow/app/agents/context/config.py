"""
Configuration for ContextAgent
"""
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ContextConfig:
    """Configuration for ContextAgent with environment variable support"""
    
    # LLM Configuration
    llm_provider: str = "ollama"  # ollama or openai
    llm_model: str = "llama3.2:3b"
    llm_base_url: str = "http://ollama:11434"
    llm_timeout: int = 60
    llm_max_retries: int = 3
    llm_batch_size: int = 10
    
    # Narrative Generation
    use_llm_narratives: bool = True  # Use LLM for narrative generation
    fallback_to_templates: bool = True  # Fallback to templates if LLM fails
    
    # Entity narratives
    entity_description_max_length: int = 500  # Max words
    entity_description_min_length: int = 100  # Min words
    
    # Column narratives
    column_description_max_length: int = 300
    column_description_min_length: int = 50
    
    # Relationship narratives
    relationship_description_max_length: int = 200
    
    # Domain narratives
    domain_description_max_length: int = 600
    
    # Confidence Language Mapping
    confidence_thresholds: Dict[str, tuple] = field(default_factory=lambda: {
        "high": (0.85, 1.0),      # "confirmed", "established"
        "medium": (0.70, 0.85),   # "likely", "probable"
        "low": (0.0, 0.70)        # "tentative", "possible"
    })
    
    # Output Format
    output_format: str = "minimal"  # minimal or full
    include_confidence: bool = True  # Include confidence in minimal output
    
    # Graph Analysis
    enable_semantic_graph: bool = True  # Build semantic graph for context
    max_relationship_hops: int = 2  # For multi-hop context
    
    @classmethod
    def from_env(cls) -> 'ContextConfig':
        """Create configuration from environment variables"""
        return cls(
            # LLM
            llm_provider=os.getenv("CONTEXT_LLM_PROVIDER", "ollama"),
            llm_model=os.getenv("CONTEXT_LLM_MODEL", "llama3.2:3b"),
            llm_base_url=os.getenv("CONTEXT_LLM_BASE_URL", "http://ollama:11434"),
            llm_timeout=int(os.getenv("CONTEXT_LLM_TIMEOUT", "60")),
            llm_max_retries=int(os.getenv("CONTEXT_LLM_MAX_RETRIES", "3")),
            llm_batch_size=int(os.getenv("CONTEXT_LLM_BATCH_SIZE", "10")),
            
            # Narratives
            use_llm_narratives=os.getenv("CONTEXT_USE_LLM", "true").lower() == "true",
            fallback_to_templates=os.getenv("CONTEXT_FALLBACK_TEMPLATES", "true").lower() == "true",
            
            # Output
            output_format=os.getenv("CONTEXT_OUTPUT_FORMAT", "minimal"),
            include_confidence=os.getenv("CONTEXT_INCLUDE_CONFIDENCE", "true").lower() == "true",
            
            # Graph
            enable_semantic_graph=os.getenv("CONTEXT_ENABLE_GRAPH", "true").lower() == "true",
            max_relationship_hops=int(os.getenv("CONTEXT_MAX_HOPS", "2"))
        )

