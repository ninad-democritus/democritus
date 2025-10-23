"""
Embedding computation for AlignerAgent
"""
import numpy as np
from typing import List
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Compute embeddings for entity and column names"""
    
    def __init__(self, model_name: str):
        """
        Initialize embedding service
        
        Args:
            model_name: Name of sentence-transformers model
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info(f"Embedding model loaded: {model_name}")
    
    def compute_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Batch compute embeddings
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])
        
        logger.debug(f"Computing embeddings for {len(texts)} texts")
        embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        logger.debug(f"Computed embeddings shape: {embeddings.shape}")
        
        return embeddings
    
    def compute_embedding(self, text: str) -> np.ndarray:
        """
        Compute single embedding
        
        Args:
            text: Text string to embed
            
        Returns:
            numpy array of shape (embedding_dim,)
        """
        return self.model.encode([text], show_progress_bar=False, convert_to_numpy=True)[0]

