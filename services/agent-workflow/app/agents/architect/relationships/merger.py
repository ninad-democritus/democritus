"""
Relationship deduplication and merging
"""
from typing import List, Dict, Tuple
import logging
from ..models import Relationship

logger = logging.getLogger(__name__)


class RelationshipMerger:
    """Merges and deduplicates relationships from multiple sources"""
    
    def __init__(self, min_confidence: float = 0.6):
        self.min_confidence = min_confidence
    
    def merge_and_deduplicate(self, relationships: List[Relationship]) -> List[Relationship]:
        """
        Merge and deduplicate relationships, keeping highest confidence ones
        
        Args:
            relationships: List of Relationship objects
            
        Returns:
            Deduplicated list of relationships
        """
        if not relationships:
            return []
        
        # Group by relationship key (from_entity, to_entity, from_column, to_column)
        grouped = {}
        for rel in relationships:
            key = self._make_relationship_key(rel)
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(rel)
        
        # Select best relationship from each group
        merged = []
        for key, rel_group in grouped.items():
            best_rel = self._select_best_relationship(rel_group)
            if best_rel.confidence >= self.min_confidence:
                merged.append(best_rel)
            else:
                logger.debug(f"Filtered out low-confidence relationship: {key} (confidence={best_rel.confidence:.2f})")
        
        logger.info(f"Merged {len(relationships)} relationships to {len(merged)} (filtered {len(relationships) - len(merged)})")
        return merged
    
    def _make_relationship_key(self, rel: Relationship) -> Tuple[str, str, str, str]:
        """Create unique key for relationship"""
        return (rel.from_entity, rel.to_entity, rel.from_column, rel.to_column)
    
    def _select_best_relationship(self, rel_group: List[Relationship]) -> Relationship:
        """Select the best relationship from a group (highest confidence)"""
        if len(rel_group) == 1:
            return rel_group[0]
        
        # Sort by confidence (descending)
        sorted_rels = sorted(rel_group, key=lambda r: r.confidence, reverse=True)
        best = sorted_rels[0]
        
        # If multiple sources detected same relationship, merge their metadata
        if len(rel_group) > 1:
            detection_methods = [r.detection_method for r in rel_group]
            best.detection_method = "hybrid_" + "_".join(set(detection_methods))
            best.metadata['detection_sources'] = detection_methods
            logger.debug(f"Merged relationship from {len(rel_group)} sources: {best.detection_method}")
        
        return best

