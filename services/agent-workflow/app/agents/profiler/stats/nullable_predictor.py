"""
Nullable prediction heuristics
"""
import logging

logger = logging.getLogger(__name__)


class NullablePredictor:
    """Predict if a column should be nullable based on heuristics"""
    
    def __init__(self):
        """Initialize nullable predictor with heuristic rules"""
        
        # Semantic types that are typically optional
        self.optional_semantic_types = [
            "email", "phone_number", "ssn", "credit_card",
            "middle_name", "secondary", "alternate", "optional"
        ]
        
        # Name keywords that indicate optional fields
        self.optional_name_keywords = [
            "optional", "alt", "alternate", "secondary", "middle",
            "suffix", "prefix", "nickname", "maiden"
        ]
        
        # Primary key indicators (should NOT be nullable)
        self.pk_indicators = ["id", "_id", "key", "_key", "uuid", "guid"]
    
    def predict(self, 
                column_name: str,
                semantic_type: str,
                null_count: int,
                distinct_count: int,
                total_count: int) -> bool:
        """
        Predict if column should be nullable based on data characteristics
        
        Args:
            column_name: Name of the column
            semantic_type: Semantic type detected (e.g., 'email', 'identifier')
            null_count: Number of null values
            distinct_count: Number of distinct values
            total_count: Total number of rows
            
        Returns:
            True if column should be nullable, False otherwise
        """
        
        # If column has nulls, it's clearly nullable
        if null_count > 0:
            logger.debug(f"Column '{column_name}' has nulls -> nullable")
            return True
        
        # Check semantic type for typically optional fields
        if semantic_type.lower() in self.optional_semantic_types:
            logger.debug(f"Column '{column_name}' has optional semantic type '{semantic_type}' -> nullable")
            return True
        
        # Check column name for optional indicators
        col_lower = column_name.lower()
        if any(kw in col_lower for kw in self.optional_name_keywords):
            logger.debug(f"Column '{column_name}' has optional keyword -> nullable")
            return True
        
        # Check if it looks like a primary key (high uniqueness, no nulls)
        # Primary keys should NOT be nullable
        if distinct_count == total_count and total_count > 0:
            if any(ind in col_lower for ind in self.pk_indicators):
                logger.debug(f"Column '{column_name}' looks like primary key -> NOT nullable")
                return False
        
        # Default to nullable for safety (most columns accept nulls)
        logger.debug(f"Column '{column_name}' -> nullable (default)")
        return True

