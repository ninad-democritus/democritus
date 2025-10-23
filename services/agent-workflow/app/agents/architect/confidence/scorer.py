"""
Multi-factor confidence scoring for relationships
"""
from typing import Dict, Optional, Tuple
import logging
from ..models import RelationshipCandidate
from ..config import ArchitectConfig

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculates weighted confidence scores from multiple signals"""
    
    # Default weights for different scoring factors
    WEIGHTS = {
        'name_similarity': 0.35,
        'semantic_compatibility': 0.30,
        'type_compatibility': 0.10,
        'uniqueness_signal': 0.15,
        'llm_validation': 0.10
    }
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
        
        # Adjust weights based on config
        if not config.use_semantic_validation:
            # Redistribute semantic weight to name similarity
            self.WEIGHTS['name_similarity'] = 0.50
            self.WEIGHTS['semantic_compatibility'] = 0.0
            self.WEIGHTS['uniqueness_signal'] = 0.25
        
        if not config.use_llm_validation:
            # Redistribute LLM weight proportionally
            self.WEIGHTS['llm_validation'] = 0.0
            # Normalize other weights
            total = sum(v for k, v in self.WEIGHTS.items() if k != 'llm_validation')
            for k in self.WEIGHTS:
                if k != 'llm_validation':
                    self.WEIGHTS[k] = self.WEIGHTS[k] / total
    
    def calculate_confidence(
        self,
        candidate: RelationshipCandidate,
        cardinality_confidence: float,
        llm_adjustment: Optional[float] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate weighted confidence score
        
        Args:
            candidate: RelationshipCandidate with raw_scores
            cardinality_confidence: Confidence from cardinality analysis
            llm_adjustment: Optional LLM validation score
            
        Returns:
            Tuple of (final_confidence, breakdown_dict)
        """
        raw_scores = candidate.raw_scores
        
        # Extract individual scores (with defaults)
        name_similarity = raw_scores.get('name_similarity', 0.5)
        semantic_compat = raw_scores.get('semantic_compatibility', 0.5)
        type_compat = raw_scores.get('data_type_match', 0.5)
        uniqueness = raw_scores.get('uniqueness_signal', 0.5)
        
        # Calculate weighted sum
        weighted_score = (
            name_similarity * self.WEIGHTS['name_similarity'] +
            semantic_compat * self.WEIGHTS['semantic_compatibility'] +
            type_compat * self.WEIGHTS['type_compatibility'] +
            uniqueness * self.WEIGHTS['uniqueness_signal']
        )
        
        # Factor in cardinality confidence
        # Cardinality adds up to 15% boost or penalty
        cardinality_factor = (cardinality_confidence - 0.5) * 0.3  # -0.15 to +0.15
        weighted_score = weighted_score + cardinality_factor
        
        # Apply LLM adjustment if available
        llm_score = 0.0
        if llm_adjustment is not None and self.config.use_llm_validation:
            llm_score = llm_adjustment
            weighted_score = weighted_score * (1 - self.WEIGHTS['llm_validation']) + \
                           llm_score * self.WEIGHTS['llm_validation']
        
        # Clamp to [0, 1]
        final_confidence = max(0.0, min(1.0, weighted_score))
        
        # Build breakdown for transparency
        breakdown = {
            'name_similarity': round(name_similarity, 3),
            'semantic_compatibility': round(semantic_compat, 3),
            'type_compatibility': round(type_compat, 3),
            'uniqueness_signal': round(uniqueness, 3),
            'cardinality_confidence': round(cardinality_confidence, 3),
        }
        
        if llm_score > 0:
            breakdown['llm_validation'] = round(llm_score, 3)
        
        logger.debug(
            f"Confidence calculated: {final_confidence:.3f} "
            f"(name={name_similarity:.2f}, semantic={semantic_compat:.2f}, "
            f"uniqueness={uniqueness:.2f}, cardinality={cardinality_confidence:.2f})"
        )
        
        return (final_confidence, breakdown)

