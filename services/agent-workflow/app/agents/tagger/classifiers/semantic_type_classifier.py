"""
Semantic type-based classifier
Maps semantic types from ProfilerAgent to classification tags
"""
from typing import List, Dict, Any
import logging
from .base import BaseClassifier
from ..models import Classification
from ..taxonomy import SEMANTIC_TYPE_MAPPINGS

logger = logging.getLogger(__name__)


class SemanticTypeClassifier(BaseClassifier):
    """Classifies columns based on semantic type from ProfilerAgent"""
    
    def classify_column(self, column: Dict[str, Any], entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify column based on semantic type
        
        Args:
            column: Column metadata including semantic_type and semantic_type_confidence
            entity: Parent entity for context
            
        Returns:
            List of Classification objects
        """
        semantic_type = column.get('semantic_type', '').lower()
        semantic_confidence = column.get('semantic_type_confidence', 0.5)
        alignment_confidence = column.get('alignment_confidence', 1.0)
        
        # Skip if semantic type is unknown or confidence is too low
        if semantic_type in ['unknown', ''] or semantic_confidence < self.config.min_semantic_type_confidence:
            logger.debug(f"Skipping semantic classification for {column.get('name')} - "
                        f"semantic_type='{semantic_type}', confidence={semantic_confidence:.2f}")
            return []
        
        # Get classification tags for this semantic type
        tags = SEMANTIC_TYPE_MAPPINGS.get(semantic_type, [])
        
        if not tags:
            logger.debug(f"No classification mapping for semantic_type '{semantic_type}'")
            return []
        
        classifications = []
        for tag in tags:
            # Start with high base confidence since semantic type is typically reliable
            base_confidence = 0.92
            
            # Adjust based on upstream confidence
            # If ProfilerAgent wasn't confident, reduce our confidence
            if semantic_confidence < self.config.semantic_confidence_threshold:
                confidence_penalty = (self.config.semantic_confidence_threshold - semantic_confidence) * 0.3
                base_confidence *= (1.0 - confidence_penalty)
                logger.debug(f"Reduced confidence for {tag} due to low semantic_type_confidence: "
                           f"{semantic_confidence:.2f} -> penalty={confidence_penalty:.2f}")
            
            # Also factor in alignment confidence (to a lesser degree)
            if alignment_confidence < self.config.alignment_confidence_threshold:
                confidence_penalty = (self.config.alignment_confidence_threshold - alignment_confidence) * 0.15
                base_confidence *= (1.0 - confidence_penalty)
                logger.debug(f"Reduced confidence for {tag} due to low alignment_confidence: "
                           f"{alignment_confidence:.2f} -> penalty={confidence_penalty:.2f}")
            
            # Clamp to reasonable range
            final_confidence = max(0.5, min(0.98, base_confidence))
            
            classifications.append(Classification(
                tag=tag,
                confidence=final_confidence,
                source='semantic_type',
                upstream_factors={
                    'semantic_type': semantic_type,
                    'semantic_type_confidence': semantic_confidence,
                    'alignment_confidence': alignment_confidence
                }
            ))
            
            logger.info(f"Classified {column.get('name')} as {tag} with confidence {final_confidence:.2f} "
                       f"(semantic_type={semantic_type}, semantic_conf={semantic_confidence:.2f})")
        
        return classifications

