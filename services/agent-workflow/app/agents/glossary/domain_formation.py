"""
Domain formation from term clusters
Uses classifications as primary signal, embeddings as fallback
"""
import numpy as np
import logging
from typing import List, Dict, Set
from collections import Counter, defaultdict
from .models import TermCluster, DomainCluster
from .config import GlossaryConfig

logger = logging.getLogger(__name__)


class DomainFormationService:
    """Form business domains from term clusters"""
    
    def __init__(self, config: GlossaryConfig, clustering_service=None):
        """
        Initialize domain formation service
        
        Args:
            config: GlossaryConfig instance
            clustering_service: Optional ClusteringService for embedding-based fallback
        """
        self.config = config
        self.clustering_service = clustering_service
    
    def form_domains(self, term_clusters: List[TermCluster]) -> List[DomainCluster]:
        """
        Form domain clusters from term clusters
        
        Args:
            term_clusters: List of TermCluster objects
            
        Returns:
            List of DomainCluster objects
        """
        logger.info(f"Forming domains from {len(term_clusters)} term clusters")
        
        # Primary strategy: Classification-based grouping
        if self.config.use_classification_domains:
            domain_clusters = self._form_domains_by_classification(term_clusters)
            
            if domain_clusters:
                logger.info(f"Formed {len(domain_clusters)} domains using classifications")
                return domain_clusters
            else:
                logger.warning("Classification-based domain formation produced no domains, trying fallback")
        
        # Fallback: Embedding-based clustering
        if self.config.use_embedding_domains and self.clustering_service:
            domain_clusters = self._form_domains_by_embedding(term_clusters)
            logger.info(f"Formed {len(domain_clusters)} domains using embeddings")
            return domain_clusters
        
        # Last resort: Single domain
        logger.warning("Falling back to single domain containing all terms")
        return [self._create_default_domain(term_clusters)]
    
    def _form_domains_by_classification(self, term_clusters: List[TermCluster]) -> List[DomainCluster]:
        """
        Form domains by grouping term clusters with similar classifications
        
        Strategy:
        1. Extract classification prefixes (e.g., Finance.*, PII.*)
        2. Group term clusters by dominant classification prefix
        3. Handle multi-classification terms
        4. Use entity_type as additional hint
        """
        # Extract classification prefixes from all term clusters
        domain_map = defaultdict(list)
        unclassified_clusters = []
        
        for term_cluster in term_clusters:
            # Collect all classifications from cluster members
            all_classifications = []
            for term in term_cluster.members:
                all_classifications.extend(term.classifications)
            
            if not all_classifications:
                unclassified_clusters.append(term_cluster)
                continue
            
            # Get classification prefixes (before the dot)
            classification_prefixes = self._extract_classification_prefixes(all_classifications)
            
            if not classification_prefixes:
                unclassified_clusters.append(term_cluster)
                continue
            
            # Use dominant classification prefix
            dominant_prefix = classification_prefixes.most_common(1)[0][0]
            
            # Use entity type as secondary grouping if enabled
            if self.config.use_entity_type_hint:
                entity_types = [term.entity_type for term in term_cluster.members]
                dominant_entity_type = Counter(entity_types).most_common(1)[0][0] if entity_types else 'unknown'
                
                # Combine classification and entity type for key
                key = f"{dominant_prefix}_{dominant_entity_type}"
            else:
                key = dominant_prefix
            
            domain_map[key].append(term_cluster)
        
        # Handle unclassified clusters
        if unclassified_clusters:
            domain_map['unclassified'].extend(unclassified_clusters)
        
        # Convert to DomainCluster objects
        domain_clusters = []
        for idx, (key, clusters) in enumerate(domain_map.items()):
            # Extract dominant classifications and entity types
            all_classifications = []
            all_entity_types = []
            
            for cluster in clusters:
                for term in cluster.members:
                    all_classifications.extend(term.classifications)
                    all_entity_types.append(term.entity_type)
            
            dominant_classifications = [
                cls for cls, _ in Counter(all_classifications).most_common(5)
            ]
            unique_entity_types = list(set(all_entity_types))
            
            # Compute centroid if embeddings available
            centroid, variance = self._compute_cluster_centroid(clusters)
            
            domain_cluster = DomainCluster(
                cluster_id=idx,
                term_clusters=clusters,
                dominant_classifications=dominant_classifications,
                entity_types=unique_entity_types,
                centroid=centroid,
                variance=variance
            )
            
            domain_clusters.append(domain_cluster)
        
        return domain_clusters
    
    def _form_domains_by_embedding(self, term_clusters: List[TermCluster]) -> List[DomainCluster]:
        """
        Form domains by clustering the term cluster centroids
        Fallback when classification-based grouping doesn't work
        """
        if not self.clustering_service:
            logger.warning("No clustering service available for embedding-based domains")
            return []
        
        # Collect centroids from term clusters
        centroids = []
        valid_clusters = []
        
        for cluster in term_clusters:
            if cluster.centroid is not None:
                centroids.append(cluster.centroid)
                valid_clusters.append(cluster)
        
        if not centroids:
            logger.warning("No centroids available for embedding-based clustering")
            return []
        
        # Stack centroids into matrix
        centroid_matrix = np.vstack(centroids)
        
        # Prepare tokens for clustering
        tokens = []
        for idx, cluster in enumerate(valid_clusters):
            # Use representative term for token
            rep_term = cluster.representative_term or cluster.members[0]
            tokens.append({
                'normalized': rep_term.normalized_term,
                'raw_name': rep_term.raw_term,
                'cluster_object': cluster,
                'embedding_idx': idx
            })
        
        # Cluster at domain level (higher min_cluster_size for broader grouping)
        original_min_size = self.clustering_service.min_cluster_size
        self.clustering_service.min_cluster_size = max(2, len(valid_clusters) // 5)
        
        try:
            raw_clusters = self.clustering_service.cluster_terms(centroid_matrix, tokens)
        finally:
            self.clustering_service.min_cluster_size = original_min_size
        
        # Convert to DomainCluster objects
        domain_clusters = []
        for domain_idx, raw_cluster in enumerate(raw_clusters):
            term_clusters_in_domain = [token['cluster_object'] for token in raw_cluster.members]
            
            # Collect classifications and entity types
            all_classifications = []
            all_entity_types = []
            
            for tc in term_clusters_in_domain:
                for term in tc.members:
                    all_classifications.extend(term.classifications)
                    all_entity_types.append(term.entity_type)
            
            dominant_classifications = [
                cls for cls, _ in Counter(all_classifications).most_common(5)
            ]
            unique_entity_types = list(set(all_entity_types))
            
            domain_cluster = DomainCluster(
                cluster_id=domain_idx,
                term_clusters=term_clusters_in_domain,
                dominant_classifications=dominant_classifications,
                entity_types=unique_entity_types,
                centroid=raw_cluster.centroid,
                variance=raw_cluster.variance
            )
            
            domain_clusters.append(domain_cluster)
        
        return domain_clusters
    
    def _extract_classification_prefixes(self, classifications: List[str]) -> Counter:
        """
        Extract classification prefixes (e.g., 'Finance' from 'Finance.Reporting')
        
        Returns:
            Counter of prefix frequencies
        """
        prefixes = Counter()
        
        for classification in classifications:
            if '.' in classification:
                prefix = classification.split('.')[0]
                prefixes[prefix] += 1
            else:
                # No dot, use full classification as prefix
                prefixes[classification] += 1
        
        return prefixes
    
    def _compute_cluster_centroid(self, clusters: List[TermCluster]) -> tuple:
        """
        Compute centroid of term clusters
        
        Returns:
            (centroid, variance) tuple
        """
        # Collect all embeddings from cluster members
        embeddings = []
        for cluster in clusters:
            for term in cluster.members:
                if term.embedding is not None:
                    embeddings.append(term.embedding)
        
        if not embeddings:
            return None, 0.0
        
        # Stack and compute centroid
        embedding_matrix = np.vstack(embeddings)
        centroid = np.mean(embedding_matrix, axis=0)
        
        # Compute variance (average distance to centroid)
        distances = np.linalg.norm(embedding_matrix - centroid, axis=1)
        variance = np.mean(distances)
        
        return centroid, float(variance)
    
    def _create_default_domain(self, term_clusters: List[TermCluster]) -> DomainCluster:
        """Create a default domain containing all term clusters"""
        # Collect all classifications and entity types
        all_classifications = []
        all_entity_types = []
        
        for cluster in term_clusters:
            for term in cluster.members:
                all_classifications.extend(term.classifications)
                all_entity_types.append(term.entity_type)
        
        dominant_classifications = [
            cls for cls, _ in Counter(all_classifications).most_common(10)
        ]
        unique_entity_types = list(set(all_entity_types))
        
        centroid, variance = self._compute_cluster_centroid(term_clusters)
        
        return DomainCluster(
            cluster_id=0,
            term_clusters=term_clusters,
            dominant_classifications=dominant_classifications,
            entity_types=unique_entity_types,
            centroid=centroid,
            variance=variance
        )

