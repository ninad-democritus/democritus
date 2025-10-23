"""
Name similarity calculation for relationship detection
"""
from typing import List
import logging

logger = logging.getLogger(__name__)

# Try to import rapidfuzz, fall back to basic matching
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not available, using basic string matching")


class NameSimilarityCalculator:
    """Calculate similarity between column/entity names"""
    
    def __init__(self, algorithm: str = "rapidfuzz"):
        self.algorithm = algorithm if RAPIDFUZZ_AVAILABLE else "basic"
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity score between two names
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            Similarity score [0-1], where 1.0 = identical
        """
        if not name1 or not name2:
            return 0.0
        
        name1_lower = name1.lower().strip()
        name2_lower = name2.lower().strip()
        
        # Exact match
        if name1_lower == name2_lower:
            return 1.0
        
        # Use rapidfuzz if available
        if RAPIDFUZZ_AVAILABLE and self.algorithm == "rapidfuzz":
            # Ratio method (overall similarity)
            score = fuzz.ratio(name1_lower, name2_lower) / 100.0
            return score
        else:
            # Basic similarity: substring match
            return self._basic_similarity(name1_lower, name2_lower)
    
    def _basic_similarity(self, name1: str, name2: str) -> float:
        """Basic substring-based similarity"""
        # Check if one is substring of the other
        if name1 in name2 or name2 in name1:
            shorter = min(len(name1), len(name2))
            longer = max(len(name1), len(name2))
            return shorter / longer
        
        # Check token overlap
        tokens1 = set(name1.replace('_', ' ').split())
        tokens2 = set(name2.replace('_', ' ').split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_name_variations(self, entity_name: str, synonyms: List[str] = None, raw_names: List[str] = None) -> List[str]:
        """
        Get variations of an entity name for matching
        
        Args:
            entity_name: Canonical entity name
            synonyms: Synonym names
            raw_names: Raw source names
            
        Returns:
            List of name variations
        """
        variations = [entity_name.lower()]
        
        # Add synonyms
        if synonyms:
            variations.extend([syn.lower() for syn in synonyms])
        
        # Add raw names
        if raw_names:
            variations.extend([name.lower() for name in raw_names])
        
        # Add with underscores
        variations.append(entity_name.lower().replace(' ', '_'))
        
        # Remove plural 's' if exists
        base_name = entity_name.lower()
        if base_name.endswith('s') and len(base_name) > 3:
            variations.append(base_name[:-1])
        
        # Add shortened versions (first 4 chars)
        if len(base_name) > 4:
            variations.append(base_name[:4])
        
        # Deduplicate
        return list(set(variations))

