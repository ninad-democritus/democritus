"""
Primary key detection for AlignerAgent
"""
import re
import logging
from typing import List, Dict, Any
from .models import CanonicalColumn
from .config import AlignerConfig

logger = logging.getLogger(__name__)


class PrimaryKeyDetector:
    """Detect and rank primary key candidates"""
    
    def __init__(self, config: AlignerConfig):
        """
        Initialize PK detector
        
        Args:
            config: AlignerConfig instance
        """
        self.config = config
        self.pk_patterns = [re.compile(pattern) for pattern in config.pk_name_patterns]
    
    def detect_primary_keys(self, 
                           columns: List[CanonicalColumn]) -> List[Dict[str, Any]]:
        """
        Detect and rank PK candidates
        
        Args:
            columns: List of CanonicalColumn objects
            
        Returns:
            List of PK candidates sorted by confidence
        """
        candidates = []
        
        for col in columns:
            score = self._score_as_pk(col)
            
            if score > 0.5:
                reasons = self._explain_score(col, score)
                candidates.append({
                    'column_raw': col.raw_names[0] if col.raw_names else col.canonical_name,
                    'column_canonical': col.canonical_name,
                    'confidence': round(score, 3),
                    'reasons': reasons
                })
        
        # Sort by confidence descending
        candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"Detected {len(candidates)} PK candidates")
        for candidate in candidates[:3]:  # Log top 3
            logger.debug(f"  {candidate['column_canonical']}: {candidate['confidence']} - {candidate['reasons']}")
        
        return candidates
    
    def _score_as_pk(self, col: CanonicalColumn) -> float:
        """
        Multi-factor PK scoring
        
        Returns:
            Score between 0 and 1
        """
        stats = col.stats
        
        # Calculate uniqueness ratio
        total_count = stats.get('total_count', 0)
        distinct_count = stats.get('distinct_count', 0)
        uniqueness = distinct_count / total_count if total_count > 0 else 0.0
        
        # Calculate null ratio
        null_count = stats.get('null_count', 0)
        null_ratio = null_count / total_count if total_count > 0 else 0.0
        
        # Name weight (matches PK patterns?)
        name_weight = self._calculate_name_weight(col.canonical_name)
        
        # Semantic weight
        semantic_weight = 0.5  # Default
        if col.semantic_type:
            semantic_lower = col.semantic_type.lower()
            if 'identifier' in semantic_lower or 'uuid' in semantic_lower:
                semantic_weight = 1.0
            elif 'string' in semantic_lower or 'integer' in semantic_lower:
                semantic_weight = 0.5
        
        # Weighted score
        # 60% uniqueness, 20% non-null, 20% name/semantic
        score = (
            0.6 * uniqueness +
            0.2 * (1.0 - null_ratio) +
            0.1 * name_weight +
            0.1 * semantic_weight
        )
        
        return min(score, 1.0)
    
    def _calculate_name_weight(self, name: str) -> float:
        """Calculate name matching weight"""
        name_lower = name.lower()
        
        # Check against patterns
        for pattern in self.pk_patterns:
            if pattern.search(name_lower):
                return 1.0
        
        # Partial match
        if 'id' in name_lower or 'key' in name_lower or 'code' in name_lower:
            return 0.5
        
        return 0.2
    
    def _explain_score(self, col: CanonicalColumn, score: float) -> List[str]:
        """Generate human-readable explanations"""
        reasons = []
        
        stats = col.stats
        total_count = stats.get('total_count', 0)
        distinct_count = stats.get('distinct_count', 0)
        null_count = stats.get('null_count', 0)
        
        # Uniqueness
        if total_count > 0:
            uniqueness = distinct_count / total_count
            if uniqueness > 0.98:
                reasons.append(f"High uniqueness ({uniqueness*100:.1f}%)")
            elif uniqueness > 0.8:
                reasons.append(f"Good uniqueness ({uniqueness*100:.1f}%)")
        
        # Nulls
        if null_count == 0:
            reasons.append("No nulls detected")
        elif null_count < total_count * 0.05:
            reasons.append("Very few nulls")
        
        # Name pattern
        name_weight = self._calculate_name_weight(col.canonical_name)
        if name_weight >= 1.0:
            for pattern in self.pk_patterns:
                if pattern.search(col.canonical_name.lower()):
                    reasons.append(f"Matches PK pattern '{pattern.pattern}'")
                    break
        elif name_weight > 0.2:
            reasons.append("Contains ID/key keyword")
        
        # Semantic type
        if col.semantic_type and 'identifier' in col.semantic_type.lower():
            reasons.append(f"Semantic type: {col.semantic_type}")
        
        return reasons

