"""
Statistical classifier
Uses column statistics to assign classifications
"""
from typing import List, Dict, Any
import logging
from .base import BaseClassifier
from ..models import Classification

logger = logging.getLogger(__name__)


class StatisticalClassifier(BaseClassifier):
    """Classifies columns based on statistical properties"""
    
    def classify_column(self, column: Dict[str, Any], entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify column based on statistics
        
        Args:
            column: Column metadata with statistics
            entity: Parent entity for context
            
        Returns:
            List of Classification objects
        """
        classifications = []
        statistics = column.get('statistics', {})
        
        # Get key statistics
        distinct_count = statistics.get('distinct_count', 0)
        null_percentage = statistics.get('null_percentage', 0.0)
        
        # Cardinality-based classification
        if distinct_count > 0:
            if distinct_count < 10:
                # Low cardinality - likely categorical
                classifications.append(Classification(
                    tag='Categorical.LowCardinality',
                    confidence=0.85,
                    source='statistics',
                    upstream_factors={
                        'distinct_count': distinct_count,
                        'basis': 'low_cardinality'
                    }
                ))
                logger.debug(f"{column.get('name')} classified as LowCardinality ({distinct_count} distinct)")
            
            elif distinct_count > 1000:
                # High cardinality
                classifications.append(Classification(
                    tag='Categorical.HighCardinality',
                    confidence=0.80,
                    source='statistics',
                    upstream_factors={
                        'distinct_count': distinct_count,
                        'basis': 'high_cardinality'
                    }
                ))
                logger.debug(f"{column.get('name')} classified as HighCardinality ({distinct_count} distinct)")
        
        # Data quality - completeness
        if null_percentage > 50.0:
            classifications.append(Classification(
                tag='DataQuality.Completeness',
                confidence=0.90,
                source='statistics',
                upstream_factors={
                    'null_percentage': null_percentage,
                    'basis': 'high_null_rate'
                }
            ))
            logger.info(f"{column.get('name')} has high null rate: {null_percentage:.1f}%")
        
        return classifications

