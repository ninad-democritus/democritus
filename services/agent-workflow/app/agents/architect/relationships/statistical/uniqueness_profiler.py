"""
Uniqueness profiler for column analysis
"""
import logging
from ...config import ArchitectConfig

logger = logging.getLogger(__name__)


class UniquenessProfiler:
    """Analyzes column uniqueness for relationship detection"""
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
    
    def calculate_uniqueness_ratio(self, column_schema) -> float:
        """
        Calculate uniqueness ratio for a column
        
        Args:
            column_schema: ColumnSchema object
            
        Returns:
            Uniqueness ratio [0-1], where 1.0 = all values unique
        """
        distinct_count = column_schema.distinct_count
        total_count = column_schema.total_count
        
        if total_count == 0:
            return 0.0
        
        return distinct_count / total_count
    
    def is_likely_primary_key(self, column_schema) -> bool:
        """
        Check if column is likely a primary key based on uniqueness
        
        Args:
            column_schema: ColumnSchema object
            
        Returns:
            True if likely a PK
        """
        uniqueness = self.calculate_uniqueness_ratio(column_schema)
        
        # Must be highly unique and non-null
        return (uniqueness >= self.config.uniqueness_threshold_pk and 
                column_schema.null_percentage < 5.0)
    
    def is_likely_foreign_key(self, column_schema) -> bool:
        """
        Check if column is likely a foreign key (not unique, but many duplicates)
        
        Args:
            column_schema: ColumnSchema object
            
        Returns:
            True if likely an FK
        """
        uniqueness = self.calculate_uniqueness_ratio(column_schema)
        
        # FK should have duplicates (not unique) but still have reasonable distinct values
        return (uniqueness < 0.9 and uniqueness > 0.05 and 
                column_schema.distinct_count > 1)

