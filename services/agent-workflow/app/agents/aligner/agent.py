"""
AlignerAgent - Main orchestrator with backward compatibility
"""
from typing import List, Optional, Dict, Any
import logging
from .models import CanonicalEntity, CanonicalColumn
from .config import AlignerConfig
from .preprocessing import NamePreprocessor
from .embeddings import EmbeddingService
from .clustering import ClusteringService
from .canonical_naming import CanonicalNamingService
from .entity_classifier import EntityClassifier
from .primary_key_detector import PrimaryKeyDetector
from ..profiler import FileProfile, ColumnProfile

# CanonicalEntity is now the primary output format (no legacy Entity needed)

try:
    from ...observability import trace_agent, observability
except ImportError:
    def trace_agent(name):
        def decorator(func):
            return func
        return decorator
    
    class MockObservability:
        def create_agent_span(self, *args, **kwargs): return None
        def log_agent_output(self, *args, **kwargs): pass
        def end_agent_span(self, *args, **kwargs): pass
    
    observability = MockObservability()

logger = logging.getLogger(__name__)


class AlignerAgent:
    """
    Enhanced Aligner Agent:
    - Embedding-based entity & column clustering
    - Canonical naming with synonyms
    - Cross-file entity consolidation
    - Confidence scoring at all levels
    - Optional LLM refinement
    - Backward compatible with old Entity format
    """
    
    def __init__(self, config: Optional[AlignerConfig] = None):
        """
        Initialize AlignerAgent
        
        Args:
            config: AlignerConfig instance (defaults to env-based config)
        """
        self.config = config or AlignerConfig.from_env()
        
        # Initialize services
        self.preprocessor = NamePreprocessor()
        self.embedding_service = EmbeddingService(self.config.embedding_model)
        self.clustering_service = ClusteringService(
            self.config.clustering_method,
            self.config.min_cluster_size,
            self.config.clustering_metric
        )
        self.canonical_naming = CanonicalNamingService(self.config)
        self.pk_detector = PrimaryKeyDetector(self.config)
        self.entity_classifier = EntityClassifier()
        
        logger.info("AlignerAgent initialized")
    
    @trace_agent("AlignerAgent")
    def identify_entities(self, file_profiles: List[FileProfile]) -> List[CanonicalEntity]:
        """
        Main entry point - Returns List[CanonicalEntity]
        
        Args:
            file_profiles: List of FileProfile objects from ProfilerAgent
            
        Returns:
            List of CanonicalEntity objects (rich format)
        """
        span = observability.create_agent_span("AlignerAgent", {
            "input_files": [fp.file_name for fp in file_profiles],
            "total_files": len(file_profiles)
        })
        
        try:
            logger.info(f"Starting alignment for {len(file_profiles)} files")
            
            # Internal: build enhanced canonical entities
            canonical_entities = self._align_entities_internal(file_profiles)
            
            # Return CanonicalEntity directly (no conversion needed)
            # Log metrics
            entity_metrics = {
                "entities_identified": len(canonical_entities),
                "entity_types": [e.type for e in canonical_entities],
                "entity_names": [e.canonical_name for e in canonical_entities]
            }
            
            logger.info(f"Alignment complete: {len(canonical_entities)} canonical entities identified")
            
            observability.log_agent_output("AlignerAgent", {
                "entities": [(e.canonical_name, e.type) for e in canonical_entities]
            }, entity_metrics)
            
            observability.end_agent_span(span, {
                "entities_count": len(canonical_entities),
                "metrics": entity_metrics
            })
            
            return canonical_entities
            
        except Exception as e:
            logger.error(f"Alignment failed: {e}")
            observability.end_agent_span(span, {}, str(e))
            raise
    
    def _align_entities_internal(self, 
                                 file_profiles: List[FileProfile]) -> List[CanonicalEntity]:
        """Internal enhanced alignment logic"""
        
        logger.info("Step 1: Collecting and preprocessing tokens")
        entity_tokens, column_tokens = self._collect_tokens(file_profiles)
        logger.info(f"Collected {len(entity_tokens)} entity tokens, {len(column_tokens)} column tokens")
        
        logger.info("Step 2: Computing embeddings")
        entity_embeddings = self.embedding_service.compute_embeddings(
            [t['normalized'] for t in entity_tokens]
        )
        column_embeddings = self.embedding_service.compute_embeddings(
            [t['normalized'] for t in column_tokens]
        )
        logger.info(f"Computed embeddings: entities={entity_embeddings.shape}, columns={column_embeddings.shape}")
        
        logger.info("Step 3: Clustering")
        entity_clusters = self.clustering_service.cluster_entities(
            entity_embeddings, entity_tokens
        )
        column_clusters = self.clustering_service.cluster_columns(
            column_embeddings, column_tokens
        )
        logger.info(f"Created {len(entity_clusters)} entity clusters, {len(column_clusters)} column clusters")
        
        logger.info("Step 4: Assigning columns to entities")
        column_to_entity_map = self.clustering_service.assign_columns_to_entities(
            column_clusters, entity_clusters
        )
        logger.info(f"Mapped {len(column_to_entity_map)} column clusters to entities")
        
        logger.info("Step 5: Generating canonical names")
        entity_names = self.canonical_naming.select_canonical_names(
            entity_clusters, 'entity'
        )
        column_names = self.canonical_naming.select_canonical_names(
            column_clusters, 'column'
        )
        logger.info(f"Generated {len(entity_names)} entity names, {len(column_names)} column names")
        
        logger.info("Step 6: Building canonical entities")
        entities = self._build_canonical_entities(
            entity_clusters, entity_names,
            column_clusters, column_names,
            column_to_entity_map
        )
        logger.info(f"Built {len(entities)} canonical entities")
        
        logger.info("Step 7: Classifying entities and detecting PKs")
        for entity in entities:
            entity.type, type_confidence = self.entity_classifier.classify_entity(
                entity, entity.columns
            )
            entity.primary_key_candidates = self.pk_detector.detect_primary_keys(
                entity.columns
            )
            logger.debug(f"Entity '{entity.canonical_name}': type={entity.type}, PKs={len(entity.primary_key_candidates)}")
        
        return entities
    
    def _collect_tokens(self, file_profiles: List[FileProfile]):
        """Collect and preprocess all tokens"""
        entity_tokens = []
        column_tokens = []
        
        for file_profile in file_profiles:
            # Extract entity-level tokens
            entity_token = self.preprocessor.extract_entity_tokens(file_profile)
            entity_tokens.append(entity_token)
            
            # Extract column-level tokens
            for column in file_profile.columns:
                column_token = self.preprocessor.extract_column_tokens(
                    column, file_profile.file_id
                )
                column_tokens.append(column_token)
        
        return entity_tokens, column_tokens
    
    def _build_canonical_entities(self,
                                  entity_clusters,
                                  entity_names,
                                  column_clusters,
                                  column_names,
                                  column_to_entity_map) -> List[CanonicalEntity]:
        """Build canonical entities from clusters"""
        
        entities = []
        
        for ent_cluster in entity_clusters:
            cluster_id = ent_cluster.cluster_id
            
            # Get canonical name for this cluster
            name_info = entity_names.get(cluster_id, {
                'canonical_name': 'Unknown Entity',
                'synonyms': []
            })
            
            # Collect source files and raw names
            source_files = []
            raw_names = []
            for member in ent_cluster.members:
                source_files.append(member['file_id'])
                raw_names.append(member['raw_name'])
            
            # Find columns belonging to this entity
            entity_columns = []
            for col_cluster in column_clusters:
                if column_to_entity_map.get(col_cluster.cluster_id) == cluster_id:
                    # Build canonical column
                    canonical_col = self._build_canonical_column(
                        col_cluster, column_names
                    )
                    entity_columns.append(canonical_col)
            
            # Create canonical entity
            entity = CanonicalEntity(
                entity_id=f"entity_{cluster_id}",
                canonical_name=name_info['canonical_name'],
                raw_names=list(set(raw_names)),
                synonyms=name_info['synonyms'],
                type='dimension',  # Will be updated by classifier
                confidence=1.0 - ent_cluster.variance,  # Lower variance = higher confidence
                source_files=list(set(source_files)),
                columns=entity_columns,
                primary_key_candidates=[]  # Will be populated by PK detector
            )
            
            entities.append(entity)
        
        return entities
    
    def _build_canonical_column(self, col_cluster, column_names) -> CanonicalColumn:
        """Build canonical column from cluster"""
        
        cluster_id = col_cluster.cluster_id
        
        # Get canonical name
        name_info = column_names.get(cluster_id, {
            'canonical_name': 'Unknown Column',
            'synonyms': []
        })
        
        # Collect raw names and profiles
        raw_names = []
        profiles = []
        for member in col_cluster.members:
            raw_names.append(member['raw_name'])
            profiles.append(member['column_profile'])
        
        # Merge statistics
        merged_stats = self._merge_column_stats(profiles)
        
        # Use first profile's semantic/data type (or majority vote)
        semantic_type = profiles[0].semantic_type if profiles else 'unknown'
        semantic_type_confidence = profiles[0].semantic_type_confidence if profiles else 0.0
        data_type = profiles[0].data_type if profiles else 'unknown'
        
        return CanonicalColumn(
            canonical_name=name_info['canonical_name'],
            raw_names=list(set(raw_names)),
            synonyms=name_info['synonyms'],
            semantic_type=semantic_type,
            semantic_type_confidence=semantic_type_confidence,
            data_type=data_type,
            is_pk=False,  # Will be updated by PK detector
            confidence=1.0 - col_cluster.variance,
            stats=merged_stats
        )
    
    def _merge_column_stats(self, profiles: List[ColumnProfile]) -> Dict[str, Any]:
        """Merge statistics from multiple ColumnProfiles"""
        
        if not profiles:
            return {}
        
        # Aggregate counts
        total_count = sum(p.total_count for p in profiles)
        null_count = sum(p.null_count for p in profiles)
        distinct_count = max((p.distinct_count for p in profiles), default=0)  # Conservative
        
        # Recalculate percentage
        null_percentage = (null_count / total_count * 100) if total_count > 0 else 0.0
        
        # Boolean OR for nullable
        nullable = any(p.nullable for p in profiles)
        
        # Merge sample values (unique)
        all_samples = []
        for p in profiles:
            if p.sample_values:
                all_samples.extend(p.sample_values)
        unique_samples = list(dict.fromkeys(all_samples))[:5]
        
        # Merge numeric stats
        min_value = None
        max_value = None
        mean_value = None
        
        numeric_profiles = [p for p in profiles if p.min_value is not None]
        if numeric_profiles:
            min_value = min(p.min_value for p in numeric_profiles)
            max_value = max(p.max_value for p in numeric_profiles)
            # Weighted mean
            total_sum = sum(p.mean_value * p.total_count for p in numeric_profiles)
            total_rows = sum(p.total_count for p in numeric_profiles)
            mean_value = total_sum / total_rows if total_rows > 0 else None
        
        return {
            'null_count': null_count,
            'total_count': total_count,
            'distinct_count': distinct_count,
            'null_percentage': round(null_percentage, 2),
            'nullable': nullable,
            'sample_values': unique_samples,
            'min_value': min_value,
            'max_value': max_value,
            'mean_value': mean_value
        }
    

