"""
Confidence scoring for classifications
"""
from typing import List, Dict, Any
import logging
from ..models import Classification
from ..config import TaggerConfig

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculates and adjusts confidence scores for classifications"""
    
    def __init__(self, config: TaggerConfig):
        """
        Initialize confidence scorer
        
        Args:
            config: TaggerConfig instance
        """
        self.config = config
    
    def adjust_confidence_for_upstream_quality(
        self,
        classification: Classification,
        column: Dict[str, Any]
    ) -> float:
        """
        Adjust classification confidence based on upstream data quality signals
        
        Args:
            classification: Classification object
            column: Column metadata with upstream confidence scores
            
        Returns:
            Adjusted confidence score
        """
        base_confidence = classification.confidence
        
        # Get upstream confidence scores
        semantic_conf = column.get('semantic_type_confidence', 1.0)
        alignment_conf = column.get('alignment_confidence', 1.0)
        
        # Start with base confidence
        adjusted_confidence = base_confidence
        
        # Apply upstream confidence as quality multipliers
        # If any upstream step had low confidence, reduce final confidence
        
        # Semantic type confidence penalty
        if semantic_conf < self.config.semantic_confidence_threshold:
            # Calculate penalty proportional to how far below threshold
            penalty_factor = (self.config.semantic_confidence_threshold - semantic_conf) * 0.3
            multiplier = 1.0 - penalty_factor
            adjusted_confidence *= multiplier
            logger.debug(f"Applied semantic confidence penalty: {penalty_factor:.2f} "
                        f"(semantic_conf={semantic_conf:.2f})")
        
        # Alignment confidence penalty  
        if alignment_conf < self.config.alignment_confidence_threshold:
            # Calculate penalty proportional to how far below threshold
            penalty_factor = (self.config.alignment_confidence_threshold - alignment_conf) * 0.25
            multiplier = 1.0 - penalty_factor
            adjusted_confidence *= multiplier
            logger.debug(f"Applied alignment confidence penalty: {penalty_factor:.2f} "
                        f"(alignment_conf={alignment_conf:.2f})")
        
        # Clamp to valid range
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        if adjusted_confidence != base_confidence:
            logger.info(f"Adjusted confidence for {classification.tag}: "
                       f"{base_confidence:.2f} -> {adjusted_confidence:.2f}")
        
        return adjusted_confidence
    
    def calculate_aggregate_confidence(
        self,
        classifications: List[Classification],
        weights: Dict[str, float] = None
    ) -> float:
        """
        Calculate aggregate confidence across multiple classifications
        
        Args:
            classifications: List of Classification objects
            weights: Optional weights by source type
            
        Returns:
            Aggregate confidence score
        """
        if not classifications:
            return 0.0
        
        if weights is None:
            # Use default weights from config
            weights = {
                'semantic_type': self.config.semantic_type_weight,
                'name_pattern': self.config.synonym_match_weight,
                'regex_pattern': self.config.pattern_weight,
                'statistics': self.config.pattern_weight,
                'relationship_context': self.config.context_weight,
                'entity_type_context': self.config.context_weight
            }
        
        # Weight classifications by source
        weighted_sum = 0.0
        total_weight = 0.0
        
        for classification in classifications:
            source = classification.source
            weight = weights.get(source, 1.0)
            weighted_sum += classification.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight

