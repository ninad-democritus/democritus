"""
Foreign key pattern matching with semantic enrichment
"""
from typing import List
import logging
from ...models import RelationshipCandidate, SchemaEntity
from ...config import ArchitectConfig
from ..statistical.type_compatibility import SemanticTypeCompatibility
from .name_similarity import NameSimilarityCalculator

logger = logging.getLogger(__name__)


class ForeignKeyMatcher:
    """Detect FK relationships via naming patterns and semantic validation"""
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
        self.semantic_checker = SemanticTypeCompatibility()
        self.name_similarity = NameSimilarityCalculator(config.name_match_algorithm)
        
        # FK naming patterns
        self.fk_patterns = [
            '{entity}_id',
            '{entity}id',
            '{entity}_key',
            '{entity}key',
            'fk_{entity}',
            '{entity}_fk',
            '{entity}_code',
            '{entity}code'
        ]
    
    def find_fk_candidates(self, entities: List[SchemaEntity]) -> List[RelationshipCandidate]:
        """
        Detect FK patterns across entities with semantic validation
        
        Args:
            entities: List of SchemaEntity
            
        Returns:
            List of RelationshipCandidate
        """
        candidates = []
        
        for entity1 in entities:
            for entity2 in entities:
                if entity1.entity_id == entity2.entity_id:
                    continue  # Skip self-relationships
                
                # Try to match entity2's columns as FK in entity1
                entity_candidates = self._find_fk_between_entities(entity1, entity2)
                candidates.extend(entity_candidates)
        
        logger.info(f"FK matcher found {len(candidates)} candidates")
        return candidates
    
    def _find_fk_between_entities(
        self, 
        from_entity: SchemaEntity, 
        to_entity: SchemaEntity
    ) -> List[RelationshipCandidate]:
        """Find FK relationships from from_entity to to_entity"""
        candidates = []
        
        # Get name variations for target entity (including synonyms and raw names)
        target_variations = self.name_similarity.get_name_variations(
            to_entity.canonical_name,
            to_entity.synonyms,
            to_entity.raw_names
        )
        
        # Find target entity's PK column
        pk_col = next((col for col in to_entity.columns if col.is_primary_key), None)
        if not pk_col:
            logger.debug(f"Entity '{to_entity.canonical_name}' has no PK, skipping FK detection")
            return candidates
        
        # Check each column in from_entity for FK patterns
        for fk_candidate_col in from_entity.columns:
            if fk_candidate_col.is_primary_key:
                continue  # PKs typically aren't FKs (except in inheritance)
            
            col_name_lower = fk_candidate_col.name.lower()
            
            # Check FK naming patterns against target entity variations
            for variation in target_variations:
                for pattern in self.fk_patterns:
                    expected_fk = pattern.format(entity=variation)
                    
                    # Check if column matches FK pattern
                    if col_name_lower == expected_fk or variation in col_name_lower:
                        # Calculate name similarity score
                        name_score = self._calculate_name_match_score(
                            col_name_lower, expected_fk, variation
                        )
                        
                        # Semantic type compatibility check
                        semantic_score = 0.5
                        if self.config.use_semantic_validation:
                            semantic_score = self.semantic_checker.calculate_compatibility(
                                fk_candidate_col.semantic_type,
                                pk_col.semantic_type
                            )
                        
                        # Combined score (weighted)
                        total_score = (name_score * 0.6) + (semantic_score * 0.4)
                        
                        if total_score >= self.config.min_name_similarity:
                            candidate = RelationshipCandidate(
                                from_entity=from_entity,
                                to_entity=to_entity,
                                from_column=fk_candidate_col,
                                to_column=pk_col,
                                detection_source='fk_pattern',
                                raw_scores={
                                    'name_similarity': name_score,
                                    'semantic_compatibility': semantic_score,
                                    'total': total_score
                                }
                            )
                            candidates.append(candidate)
                            logger.debug(
                                f"FK candidate: {from_entity.canonical_name}.{fk_candidate_col.name} "
                                f"-> {to_entity.canonical_name}.{pk_col.name} "
                                f"(score={total_score:.2f}, semantic={semantic_score:.2f})"
                            )
                            break  # Found match, don't check other patterns
        
        return candidates
    
    def _calculate_name_match_score(self, col_name: str, expected_fk: str, variation: str) -> float:
        """Calculate name matching score"""
        # Exact match
        if col_name == expected_fk:
            return 1.0
        
        # Contains entity variation
        if variation in col_name:
            # Bonus for ID/key suffix
            if col_name.endswith('_id') or col_name.endswith('id') or col_name.endswith('_key'):
                return 0.9
            return 0.75
        
        # Fuzzy similarity
        return self.name_similarity.calculate_similarity(col_name, expected_fk)

