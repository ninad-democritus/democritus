"""
Term clustering using embeddings
Reuses embedding service from AlignerAgent
"""
import numpy as np
import logging
from typing import List, Optional
from .models import CandidateTerm, TermCluster
from .config import GlossaryConfig

logger = logging.getLogger(__name__)


class TermClusteringService:
    """Cluster terms using semantic embeddings"""
    
    def __init__(self, config: GlossaryConfig, embedding_service, clustering_service):
        """
        Initialize with config and reused services from AlignerAgent
        
        Args:
            config: GlossaryConfig instance
            embedding_service: EmbeddingService from AlignerAgent
            clustering_service: ClusteringService from AlignerAgent
        """
        self.config = config
        self.embedding_service = embedding_service
        self.clustering_service = clustering_service
    
    def cluster_terms(self, terms: List[CandidateTerm]) -> List[TermCluster]:
        """
        Cluster terms based on semantic similarity
        
        Args:
            terms: List of CandidateTerm objects
            
        Returns:
            List of TermCluster objects
        """
        if not terms:
            logger.warning("No terms to cluster")
            return []
        
        logger.info(f"Clustering {len(terms)} terms")
        
        # Compute embeddings for normalized terms
        term_texts = [self._get_term_text(term) for term in terms]
        embeddings = self.embedding_service.compute_embeddings(term_texts)
        
        # Store embeddings in terms
        for term, embedding in zip(terms, embeddings):
            term.embedding = embedding
        
        logger.info(f"Computed embeddings with shape: {embeddings.shape}")
        
        # Prepare tokens for clustering service
        tokens = []
        for idx, term in enumerate(terms):
            tokens.append({
                'normalized': term.normalized_term,
                'raw_name': term.raw_term,
                'term_object': term,
                'embedding_idx': idx,
                'classifications': term.classifications,
                'entity_type': term.entity_type
            })
        
        # Cluster using the service (returns list of cluster-like objects)
        raw_clusters = self.clustering_service.cluster_terms(embeddings, tokens)
        
        # Convert to TermCluster objects
        term_clusters = []
        for cluster in raw_clusters:
            term_cluster = TermCluster(
                cluster_id=cluster.cluster_id,
                members=[token['term_object'] for token in cluster.members],
                centroid=cluster.centroid,
                variance=cluster.variance
            )
            
            # Select representative term (highest confidence)
            term_cluster.representative_term = self._select_representative(term_cluster.members)
            
            term_clusters.append(term_cluster)
        
        logger.info(f"Created {len(term_clusters)} term clusters")
        
        # Log cluster sizes
        cluster_sizes = [len(tc.members) for tc in term_clusters]
        if cluster_sizes:
            logger.info(f"Cluster size stats - Min: {min(cluster_sizes)}, "
                       f"Max: {max(cluster_sizes)}, "
                       f"Avg: {sum(cluster_sizes)/len(cluster_sizes):.1f}")
        
        return term_clusters
    
    def _get_term_text(self, term: CandidateTerm) -> str:
        """
        Get text representation for embedding
        Combines canonical name with context for better clustering
        """
        # Start with canonical name
        text_parts = [term.canonical_name]
        
        # Add normalized term if different
        if term.normalized_term != term.canonical_name.lower():
            text_parts.append(term.normalized_term)
        
        # Add top synonym if available
        if term.synonyms:
            text_parts.append(term.synonyms[0])
        
        return ' '.join(text_parts)
    
    def _select_representative(self, members: List[CandidateTerm]) -> Optional[CandidateTerm]:
        """
        Select the most representative term from cluster members
        Prefer entity names over columns, higher confidence, more readable names
        """
        if not members:
            return None
        
        if len(members) == 1:
            return members[0]
        
        # Score each term
        scored_terms = []
        for term in members:
            score = 0.0
            
            # Prefer entity-level terms
            if term.source_type == 'entity':
                score += 3.0
            elif term.source_type == 'pk_candidate':
                score += 2.0
            
            # Prefer higher confidence
            avg_conf = (term.alignment_confidence + 
                       term.semantic_type_confidence + 
                       term.classification_confidence) / 3
            score += avg_conf * 2.0
            
            # Prefer readable names (no underscores, proper case)
            if '_' not in term.canonical_name and term.canonical_name[0].isupper():
                score += 1.0
            
            # Prefer shorter names (more concise)
            score -= len(term.canonical_name) * 0.01
            
            scored_terms.append((score, term))
        
        # Return highest scoring term
        scored_terms.sort(key=lambda x: x[0], reverse=True)
        return scored_terms[0][1]

