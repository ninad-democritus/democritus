"""
Configuration for AlignerAgent
"""
from dataclasses import dataclass, field
from typing import List
import os


@dataclass
class AlignerConfig:
    """Configuration for entity alignment operations"""
    
    # Embedding configuration
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Clustering configuration
    min_cluster_size: int = 2
    clustering_metric: str = "cosine"
    clustering_method: str = "hdbscan"  # or "agglomerative"
    
    # LLM configuration (Ollama only)
    use_llm: bool = True
    llm_batch_size: int = 8
    llm_variance_threshold: float = 0.15
    
    # Primary key detection
    min_pk_uniqueness: float = 0.98
    pk_name_patterns: List[str] = field(default_factory=lambda: [r'^id$', r'_id$', r'^id_'])
    
    # Entity classification (fact/dimension)
    fact_numeric_threshold: float = 0.4
    fact_measure_min_count: int = 1
    
    @classmethod
    def from_env(cls) -> 'AlignerConfig':
        """Create configuration from environment variables"""
        return cls(
            embedding_model=os.getenv("ALIGNER_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            use_llm=os.getenv("ALIGNER_USE_LLM", "true").lower() == "true",
            min_cluster_size=int(os.getenv("ALIGNER_MIN_CLUSTER_SIZE", "2")),
            clustering_method=os.getenv("ALIGNER_CLUSTERING_METHOD", "hdbscan"),
        )

