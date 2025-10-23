"""
Cardinality analyzer for relationship direction
"""
from typing import Tuple
import logging
from ...models import RelationshipCandidate
from ...config import ArchitectConfig
from .uniqueness_profiler import UniquenessProfiler

logger = logging.getLogger(__name__)


class CardinalityAnalyzer:
    """Infers cardinality (1:N, N:1, etc.) using statistical profiling"""
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
        self.uniqueness_profiler = UniquenessProfiler(config)
    
    def infer_cardinality(self, candidate: RelationshipCandidate) -> Tuple[str, float]:
        """
        Determine cardinality using profiling data
        
        Args:
            candidate: RelationshipCandidate
            
        Returns:
            Tuple of (cardinality_type, confidence)
            cardinality_type: 'many-to-one', 'one-to-many', 'one-to-one', 'many-to-many'
        """
        from_col = candidate.from_column
        to_col = candidate.to_column
        
        # Calculate uniqueness ratios
        from_uniqueness = self.uniqueness_profiler.calculate_uniqueness_ratio(from_col)
        to_uniqueness = self.uniqueness_profiler.calculate_uniqueness_ratio(to_col)
        
        logger.debug(
            f"Cardinality analysis: {from_col.name} (u={from_uniqueness:.2f}) "
            f"-> {to_col.name} (u={to_uniqueness:.2f})"
        )
        
        # Determine cardinality based on uniqueness patterns
        
        # Case 1: to_col is unique (likely PK), from_col is not → many-to-one
        if to_uniqueness >= 0.95 and from_uniqueness < 0.9:
            confidence = self._calculate_cardinality_confidence(from_uniqueness, to_uniqueness, 'many-to-one')
            return ('many-to-one', confidence)
        
        # Case 2: from_col is unique, to_col is not → one-to-many
        elif from_uniqueness >= 0.95 and to_uniqueness < 0.9:
            confidence = self._calculate_cardinality_confidence(from_uniqueness, to_uniqueness, 'one-to-many')
            return ('one-to-many', confidence)
        
        # Case 3: Both highly unique → one-to-one
        elif from_uniqueness >= 0.95 and to_uniqueness >= 0.95:
            confidence = min(from_uniqueness, to_uniqueness)
            return ('one-to-one', confidence)
        
        # Case 4: Neither unique, check distinct count ratio
        elif from_uniqueness < 0.9 and to_uniqueness < 0.9:
            ratio = from_col.distinct_count / to_col.distinct_count if to_col.distinct_count > 0 else 1.0
            
            if ratio > self.config.many_to_one_ratio_threshold:
                # from has many more distinct values → likely many-to-one
                confidence = min(0.7, to_uniqueness)
                return ('many-to-one', confidence)
            elif ratio < (1.0 / self.config.many_to_one_ratio_threshold):
                # to has many more distinct values → likely one-to-many
                confidence = min(0.7, from_uniqueness)
                return ('one-to-many', confidence)
            else:
                # Similar distinct counts → many-to-many (rare in normalized schemas)
                confidence = 0.5
                logger.warning(
                    f"Detected potential many-to-many: {from_col.name} <-> {to_col.name} "
                    f"(ratio={ratio:.2f})"
                )
                return ('many-to-many', confidence)
        
        # Default: assume many-to-one with low confidence
        return ('many-to-one', 0.5)
    
    def _calculate_cardinality_confidence(
        self, 
        from_uniqueness: float, 
        to_uniqueness: float, 
        cardinality_type: str
    ) -> float:
        """Calculate confidence score for cardinality determination"""
        
        if cardinality_type == 'many-to-one':
            # Confidence based on how unique the "one" side is
            confidence = to_uniqueness
        elif cardinality_type == 'one-to-many':
            # Confidence based on how unique the "one" side is
            confidence = from_uniqueness
        elif cardinality_type == 'one-to-one':
            # Confidence is minimum of both uniqueness
            confidence = min(from_uniqueness, to_uniqueness)
        else:
            # many-to-many has lower confidence
            confidence = 0.5
        
        return min(confidence, 1.0)

