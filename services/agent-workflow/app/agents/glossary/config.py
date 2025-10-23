"""
Configuration for GlossaryAgent
"""
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class GlossaryConfig:
    """Configuration for GlossaryAgent with environment variable support"""
    
    # Clustering
    clustering_method: str = "hdbscan"  # or "agglomerative"
    min_cluster_size: int = 2
    clustering_metric: str = "cosine"
    
    # Embeddings (reuse from AlignerAgent)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # LLM (required for definitions and domains)
    use_llm_definitions: bool = True  # Always True in production
    use_llm_domain_descriptions: bool = True
    use_llm_synonyms: bool = True
    use_llm_term_refinement: bool = True  # Optional for complex cases
    
    llm_provider: str = "ollama"  # ollama or openai
    llm_model: str = "llama3.2:3b"
    llm_base_url: str = "http://ollama:11434"
    llm_batch_size: int = 8
    llm_timeout: int = 45
    llm_max_retries: int = 3
    
    # Domain formation
    use_classification_domains: bool = True  # Primary strategy
    use_embedding_domains: bool = True  # Fallback
    use_entity_type_hint: bool = True
    
    # Linking
    name_match_threshold: float = 0.85
    semantic_similarity_threshold: float = 0.80
    
    # Related terms
    use_relationship_links: bool = True
    use_semantic_links: bool = True
    max_related_terms: int = 5
    
    # Confidence
    min_term_confidence: float = 0.50
    confidence_weights: Dict[str, float] = field(default_factory=lambda: {
        "alignment_confidence": 0.30,
        "semantic_type_confidence": 0.20,
        "classification_confidence": 0.20,
        "clustering_confidence": 0.15,
        "definition_quality": 0.15
    })
    
    # Fallbacks
    fallback_to_template_definitions: bool = True
    fallback_to_rule_based_domains: bool = True
    
    @classmethod
    def from_env(cls) -> 'GlossaryConfig':
        """Create configuration from environment variables"""
        return cls(
            # Clustering
            clustering_method=os.getenv("GLOSSARY_CLUSTERING_METHOD", "hdbscan"),
            min_cluster_size=int(os.getenv("GLOSSARY_MIN_CLUSTER_SIZE", "2")),
            clustering_metric=os.getenv("GLOSSARY_CLUSTERING_METRIC", "cosine"),
            
            # Embeddings
            embedding_model=os.getenv("GLOSSARY_EMBEDDING_MODEL", 
                                     "sentence-transformers/all-MiniLM-L6-v2"),
            
            # LLM
            use_llm_definitions=os.getenv("GLOSSARY_USE_LLM_DEFINITIONS", "true").lower() == "true",
            use_llm_domain_descriptions=os.getenv("GLOSSARY_USE_LLM_DOMAINS", "true").lower() == "true",
            use_llm_synonyms=os.getenv("GLOSSARY_USE_LLM_SYNONYMS", "true").lower() == "true",
            use_llm_term_refinement=os.getenv("GLOSSARY_USE_LLM_REFINEMENT", "true").lower() == "true",
            
            llm_provider=os.getenv("GLOSSARY_LLM_PROVIDER", "ollama"),
            llm_model=os.getenv("GLOSSARY_LLM_MODEL", "llama3.2:3b"),
            llm_base_url=os.getenv("GLOSSARY_LLM_BASE_URL", "http://ollama:11434"),
            llm_batch_size=int(os.getenv("GLOSSARY_LLM_BATCH_SIZE", "8")),
            llm_timeout=int(os.getenv("GLOSSARY_LLM_TIMEOUT", "45")),
            llm_max_retries=int(os.getenv("GLOSSARY_LLM_MAX_RETRIES", "3")),
            
            # Domain formation
            use_classification_domains=os.getenv("GLOSSARY_USE_CLASSIFICATION_DOMAINS", "true").lower() == "true",
            use_embedding_domains=os.getenv("GLOSSARY_USE_EMBEDDING_DOMAINS", "true").lower() == "true",
            use_entity_type_hint=os.getenv("GLOSSARY_USE_ENTITY_TYPE_HINT", "true").lower() == "true",
            
            # Linking
            name_match_threshold=float(os.getenv("GLOSSARY_NAME_MATCH_THRESHOLD", "0.85")),
            semantic_similarity_threshold=float(os.getenv("GLOSSARY_SEMANTIC_SIMILARITY_THRESHOLD", "0.80")),
            
            # Related terms
            use_relationship_links=os.getenv("GLOSSARY_USE_RELATIONSHIP_LINKS", "true").lower() == "true",
            use_semantic_links=os.getenv("GLOSSARY_USE_SEMANTIC_LINKS", "true").lower() == "true",
            max_related_terms=int(os.getenv("GLOSSARY_MAX_RELATED_TERMS", "5")),
            
            # Confidence
            min_term_confidence=float(os.getenv("GLOSSARY_MIN_TERM_CONFIDENCE", "0.50")),
            
            # Fallbacks
            fallback_to_template_definitions=os.getenv("GLOSSARY_FALLBACK_DEFINITIONS", "true").lower() == "true",
            fallback_to_rule_based_domains=os.getenv("GLOSSARY_FALLBACK_DOMAINS", "true").lower() == "true"
        )

