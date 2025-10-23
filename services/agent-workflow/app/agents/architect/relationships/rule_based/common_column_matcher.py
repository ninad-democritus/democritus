"""
Common column matching for natural join relationships with semantic validation
"""
from typing import List
import logging
from ...models import RelationshipCandidate, SchemaEntity
from ...config import ArchitectConfig
from ..statistical.type_compatibility import SemanticTypeCompatibility

logger = logging.getLogger(__name__)


class CommonColumnMatcher:
    """Find relationships based on common column names (natural join keys)"""
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
        self.semantic_checker = SemanticTypeCompatibility()
    
    def find_common_columns(self, entities: List[SchemaEntity]) -> List[RelationshipCandidate]:
        """
        Find columns with identical names across entities with semantic validation
        
        Args:
            entities: List of SchemaEntity
            
        Returns:
            List of RelationshipCandidate
        """
        candidates = []
        
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:  # Avoid duplicate pairs
                entity_candidates = self._find_common_between_entities(entity1, entity2)
                candidates.extend(entity_candidates)
        
        logger.info(f"Common column matcher found {len(candidates)} candidates")
        return candidates
    
    def _find_common_between_entities(
        self,
        entity1: SchemaEntity,
        entity2: SchemaEntity
    ) -> List[RelationshipCandidate]:
        """Find common columns between two entities"""
        candidates = []
        
        # Build column name maps
        entity1_cols = {col.canonical_name.lower(): col for col in entity1.columns}
        entity2_cols = {col.canonical_name.lower(): col for col in entity2.columns}
        
        # Find columns with identical names
        common_names = set(entity1_cols.keys()) & set(entity2_cols.keys())
        
        for common_name in common_names:
            col1 = entity1_cols[common_name]
            col2 = entity2_cols[common_name]
            
            # Skip if both are primary keys (likely same entity or denormalized)
            if col1.is_primary_key and col2.is_primary_key:
                logger.debug(f"Skipping PK-PK match: {common_name}")
                continue
            
            # Calculate confidence
            confidence = self._calculate_common_column_confidence(col1, col2)
            
            # Check semantic compatibility
            semantic_score = 0.5
            if self.config.use_semantic_validation:
                semantic_score = self.semantic_checker.calculate_compatibility(
                    col1.semantic_type,
                    col2.semantic_type
                )
                
                # Warn if semantic types don't match well
                if semantic_score < 0.5:
                    logger.warning(
                        f"Columns '{common_name}' have same name but incompatible semantic types: "
                        f"{col1.semantic_type} vs {col2.semantic_type} (score={semantic_score:.2f})"
                    )
            
            # Adjust confidence based on semantic compatibility
            total_confidence = (confidence * 0.6) + (semantic_score * 0.4)
            
            if total_confidence >= 0.3:  # Lower threshold for common columns
                # Create bidirectional candidates (we'll dedupe later)
                candidate = RelationshipCandidate(
                    from_entity=entity1,
                    to_entity=entity2,
                    from_column=col1,
                    to_column=col2,
                    detection_source='common_column',
                    raw_scores={
                        'name_match': 1.0,  # Exact name match
                        'data_type_match': 1.0 if col1.data_type == col2.data_type else 0.5,
                        'semantic_compatibility': semantic_score,
                        'uniqueness_signal': self._get_uniqueness_signal(col1, col2),
                        'total': total_confidence
                    }
                )
                candidates.append(candidate)
                
                logger.debug(
                    f"Common column: {entity1.canonical_name}.{col1.name} "
                    f"<-> {entity2.canonical_name}.{col2.name} "
                    f"(confidence={total_confidence:.2f}, semantic={semantic_score:.2f})"
                )
        
        return candidates
    
    def _calculate_common_column_confidence(self, col1, col2) -> float:
        """Calculate confidence for common column relationship"""
        confidence = 0.6  # Base confidence for same name
        
        # Bonus for data type match
        if col1.data_type == col2.data_type:
            confidence += 0.2
        
        # Bonus for identifier-like names
        col_name_lower = col1.name.lower()
        if any(pattern in col_name_lower for pattern in ['id', 'key', 'code', 'num', 'ref']):
            confidence += 0.1
        
        # Bonus if one has higher uniqueness (likely lookup key)
        if col1.distinct_count > 0 and col2.distinct_count > 0:
            ratio = max(col1.distinct_count, col2.distinct_count) / min(col1.distinct_count, col2.distinct_count)
            if ratio > 2:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _get_uniqueness_signal(self, col1, col2) -> float:
        """Get signal from uniqueness patterns"""
        if col1.total_count == 0 or col2.total_count == 0:
            return 0.0
        
        u1 = col1.distinct_count / col1.total_count if col1.total_count > 0 else 0
        u2 = col2.distinct_count / col2.total_count if col2.total_count > 0 else 0
        
        # If one is much more unique than the other, it's a strong relationship signal
        if max(u1, u2) > 0.9 and min(u1, u2) < 0.5:
            return 0.9
        
        # If both have similar uniqueness, moderate signal
        if abs(u1 - u2) < 0.2:
            return 0.6
        
        return 0.4

