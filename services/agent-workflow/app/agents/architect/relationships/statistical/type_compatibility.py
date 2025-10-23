"""
Semantic type compatibility checker for relationship validation
"""
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class SemanticTypeCompatibility:
    """Check if column semantic types are compatible for relationships"""
    
    def __init__(self):
        # Compatibility matrix: (type1, type2) → compatibility_score
        # Higher score = more compatible for FK relationships
        self.compatible_pairs = {
            # Exact matches (high compatibility)
            ('uuid', 'uuid'): 1.0,
            ('identifier', 'identifier'): 1.0,
            ('email', 'email'): 1.0,
            ('ssn', 'ssn'): 1.0,
            ('zipcode', 'zipcode'): 1.0,
            ('phone_number', 'phone_number'): 1.0,
            ('credit_card', 'credit_card'): 1.0,
            
            # Cross-identifier compatibility (good)
            ('uuid', 'identifier'): 0.9,
            ('identifier', 'uuid'): 0.9,
            
            # Numeric types (moderate compatibility)
            ('integer', 'integer'): 0.8,
            ('integer', 'bigint'): 0.8,
            ('bigint', 'bigint'): 0.8,
            ('float', 'float'): 0.7,
            ('float', 'double'): 0.7,
            
            # String types (moderate compatibility)
            ('string', 'string'): 0.6,
            ('string', 'varchar'): 0.6,
            ('varchar', 'varchar'): 0.6,
            ('text', 'text'): 0.6,
            
            # Temporal types (moderate)
            ('datetime', 'datetime'): 0.8,
            ('date', 'date'): 0.8,
            ('timestamp', 'timestamp'): 0.8,
            
            # Incompatible pairs (low score)
            ('email', 'phone_number'): 0.1,
            ('datetime', 'integer'): 0.3,
            ('string', 'integer'): 0.2,
            ('boolean', 'integer'): 0.1,
        }
    
    def calculate_compatibility(self, semantic_type_1: str, semantic_type_2: str) -> float:
        """
        Return compatibility score [0-1] for FK relationship
        
        Args:
            semantic_type_1: Semantic type of first column
            semantic_type_2: Semantic type of second column
            
        Returns:
            Compatibility score (0.0 = incompatible, 1.0 = perfect match)
        """
        if not semantic_type_1 or not semantic_type_2:
            # If either type is missing/unknown, return neutral
            return 0.5
        
        type1_lower = semantic_type_1.lower()
        type2_lower = semantic_type_2.lower()
        
        # Check exact match first
        if type1_lower == type2_lower:
            return 1.0
        
        # Check compatibility matrix (try both orderings)
        pair1 = (type1_lower, type2_lower)
        pair2 = (type2_lower, type1_lower)
        
        if pair1 in self.compatible_pairs:
            return self.compatible_pairs[pair1]
        
        if pair2 in self.compatible_pairs:
            return self.compatible_pairs[pair2]
        
        # Check for 'unknown' types - neutral score
        if 'unknown' in [type1_lower, type2_lower]:
            return 0.5
        
        # Check if both are identifier-like
        identifier_types = ['uuid', 'identifier', 'ssn', 'guid']
        if type1_lower in identifier_types and type2_lower in identifier_types:
            return 0.8
        
        # Check if both are contact-related
        contact_types = ['email', 'phone_number', 'address', 'url']
        if type1_lower in contact_types and type2_lower in contact_types:
            return 0.3  # Same category but different types
        
        # Default: likely incompatible
        logger.debug(f"No compatibility entry for semantic types: {type1_lower} <-> {type2_lower}, assuming low compatibility")
        return 0.2
    
    def is_compatible(self, semantic_type_1: str, semantic_type_2: str, threshold: float = 0.5) -> bool:
        """
        Check if two semantic types are compatible above threshold
        
        Args:
            semantic_type_1: First semantic type
            semantic_type_2: Second semantic type
            threshold: Minimum compatibility score (default 0.5)
            
        Returns:
            True if compatible above threshold
        """
        score = self.calculate_compatibility(semantic_type_1, semantic_type_2)
        return score >= threshold

