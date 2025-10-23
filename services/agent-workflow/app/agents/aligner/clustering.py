"""
Clustering logic for AlignerAgent
"""
import numpy as np
from typing import List, Dict, Any
import logging
from sklearn.metrics.pairwise import cosine_distances
from .models import EntityCluster, ColumnCluster

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False
    
from sklearn.cluster import AgglomerativeClustering

logger = logging.getLogger(__name__)


class ClusteringService:
    """Cluster similar entities and columns based on embeddings"""
    
    def __init__(self, method: str, min_size: int, metric: str):
        """
        Initialize clustering service
        
        Args:
            method: Clustering method ('hdbscan' or 'agglomerative')
            min_size: Minimum cluster size
            metric: Distance metric ('cosine', 'euclidean', etc.)
        """
        self.method = method
        self.min_size = min_size
        self.metric = metric
        
        if method == "hdbscan" and not HDBSCAN_AVAILABLE:
            logger.warning("HDBSCAN not available, falling back to agglomerative clustering")
            self.method = "agglomerative"
        
        logger.info(f"Clustering initialized: method={self.method}, min_size={min_size}, metric={metric}")
    
    def cluster_entities(self, 
                        entity_embeddings: np.ndarray,
                        entity_metadata: List[Dict]) -> List[EntityCluster]:
        """
        Cluster entity-level embeddings
        
        Args:
            entity_embeddings: numpy array of embeddings
            entity_metadata: List of metadata dicts for each embedding
            
        Returns:
            List of EntityCluster objects
        """
        if len(entity_embeddings) == 0:
            return []
        
        logger.info(f"Clustering {len(entity_embeddings)} entities")
        
        # Perform clustering
        labels = self._perform_clustering(entity_embeddings)
        
        # Group into clusters
        clusters = self._group_into_clusters(
            labels, entity_embeddings, entity_metadata, EntityCluster
        )
        
        logger.info(f"Created {len(clusters)} entity clusters")
        return clusters
    
    def cluster_columns(self,
                       column_embeddings: np.ndarray,
                       column_metadata: List[Dict]) -> List[ColumnCluster]:
        """
        Cluster column-level embeddings
        
        Args:
            column_embeddings: numpy array of embeddings
            column_metadata: List of metadata dicts for each embedding
            
        Returns:
            List of ColumnCluster objects
        """
        if len(column_embeddings) == 0:
            return []
        
        logger.info(f"Clustering {len(column_embeddings)} columns")
        
        # Perform clustering
        labels = self._perform_clustering(column_embeddings)
        
        # Group into clusters
        clusters = self._group_into_clusters(
            labels, column_embeddings, column_metadata, ColumnCluster
        )
        
        logger.info(f"Created {len(clusters)} column clusters")
        return clusters
    
    def assign_columns_to_entities(self,
                                   column_clusters: List[ColumnCluster],
                                   entity_clusters: List[EntityCluster]) -> Dict[int, int]:
        """
        Assign column clusters to entity clusters
        
        Args:
            column_clusters: List of ColumnCluster objects
            entity_clusters: List of EntityCluster objects
            
        Returns:
            Dictionary mapping column_cluster_id -> entity_cluster_id
        """
        mapping = {}
        
        for col_cluster in column_clusters:
            # Use file association voting
            file_votes = {}
            for member in col_cluster.members:
                file_id = member.get('file_id', 'unknown')
                file_votes[file_id] = file_votes.get(file_id, 0) + 1
            
            # Find which entity cluster has this file
            most_common_file = max(file_votes, key=file_votes.get)
            
            for ent_cluster in entity_clusters:
                for member in ent_cluster.members:
                    if member.get('file_id') == most_common_file:
                        mapping[col_cluster.cluster_id] = ent_cluster.cluster_id
                        break
                if col_cluster.cluster_id in mapping:
                    break
            
            # If not found, use centroid distance
            if col_cluster.cluster_id not in mapping:
                mapping[col_cluster.cluster_id] = self._find_closest_entity(
                    col_cluster, entity_clusters
                )
        
        logger.info(f"Mapped {len(mapping)} column clusters to entity clusters")
        return mapping
    
    def _perform_clustering(self, embeddings: np.ndarray) -> np.ndarray:
        """Perform clustering using configured method"""
        
        if self.method == "hdbscan" and HDBSCAN_AVAILABLE:
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=self.min_size,
                metric=self.metric
            )
            labels = clusterer.fit_predict(embeddings)
            
        else:  # agglomerative
            # Compute distance matrix
            if self.metric == "cosine":
                distance_matrix = cosine_distances(embeddings)
            else:
                from sklearn.metrics.pairwise import euclidean_distances
                distance_matrix = euclidean_distances(embeddings)
            
            n_clusters = max(2, len(embeddings) // self.min_size)
            clusterer = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric='precomputed',
                linkage='average'
            )
            labels = clusterer.fit_predict(distance_matrix)
        
        return labels
    
    def _group_into_clusters(self, 
                            labels: np.ndarray,
                            embeddings: np.ndarray,
                            metadata: List[Dict],
                            cluster_class) -> List:
        """Group labeled items into cluster objects"""
        
        clusters_dict = {}
        
        for idx, label in enumerate(labels):
            if label == -1:  # Noise (HDBSCAN only)
                # Create singleton cluster for noise points
                label = f"noise_{idx}"
            
            if label not in clusters_dict:
                clusters_dict[label] = {
                    'members': [],
                    'embedding_indices': []
                }
            
            # Add metadata with embedding index
            member_data = metadata[idx].copy()
            member_data['embedding_idx'] = idx
            
            clusters_dict[label]['members'].append(member_data)
            clusters_dict[label]['embedding_indices'].append(idx)
        
        # Create cluster objects
        clusters = []
        for cluster_id, cluster_data in clusters_dict.items():
            indices = cluster_data['embedding_indices']
            cluster_embeddings = embeddings[indices]
            
            # Compute centroid and variance
            centroid = np.mean(cluster_embeddings, axis=0)
            variance = self._compute_variance(cluster_embeddings, centroid)
            
            clusters.append(cluster_class(
                cluster_id=cluster_id if isinstance(cluster_id, int) else len(clusters),
                members=cluster_data['members'],
                centroid=centroid,
                variance=variance
            ))
        
        return clusters
    
    def _compute_variance(self, embeddings: np.ndarray, centroid: np.ndarray) -> float:
        """Compute cluster variance (average distance to centroid)"""
        if len(embeddings) == 0:
            return 0.0
        
        if self.metric == "cosine":
            distances = cosine_distances(embeddings, centroid.reshape(1, -1))
        else:
            distances = np.linalg.norm(embeddings - centroid, axis=1)
        
        return float(np.mean(distances))
    
    def _find_closest_entity(self, 
                            col_cluster: ColumnCluster,
                            entity_clusters: List[EntityCluster]) -> int:
        """Find closest entity cluster based on centroid distance"""
        
        if not entity_clusters:
            return 0
        
        min_distance = float('inf')
        closest_id = entity_clusters[0].cluster_id
        
        for ent_cluster in entity_clusters:
            if self.metric == "cosine":
                distance = cosine_distances(
                    col_cluster.centroid.reshape(1, -1),
                    ent_cluster.centroid.reshape(1, -1)
                )[0][0]
            else:
                distance = np.linalg.norm(col_cluster.centroid - ent_cluster.centroid)
            
            if distance < min_distance:
                min_distance = distance
                closest_id = ent_cluster.cluster_id
        
        return closest_id

