"""
Entity classification (fact vs dimension) for AlignerAgent
"""
import logging
from typing import Tuple, Dict, Any, List
from .models import CanonicalEntity, CanonicalColumn

logger = logging.getLogger(__name__)


class EntityClassifier:
    """Classify entities as fact or dimension tables"""
    
    def __init__(self):
        """Initialize entity classifier with heuristic rules"""
        self.measure_keywords = [
            'amount', 'quantity', 'count', 'total', 'sum', 'value', 
            'price', 'cost', 'revenue', 'sales', 'profit', 'balance'
        ]
        
    def classify_entity(self, 
                       entity: CanonicalEntity,
                       columns: List[CanonicalColumn]) -> Tuple[str, float]:
        """
        Classify entity as fact or dimension with confidence
        
        Args:
            entity: CanonicalEntity object
            columns: List of CanonicalColumn objects
            
        Returns:
            Tuple of (entity_type, confidence)
        """
        features = self._extract_features(entity, columns)
        
        # Multi-factor scoring
        fact_score = 0.0
        
        # Factor 1: Numeric density (0.3 weight)
        if features['numeric_ratio'] > 0.4:
            fact_score += 0.3
        
        # Factor 2: Measure columns (0.3 weight)
        if features['measure_count'] >= 1:
            fact_score += 0.3
        
        # Factor 3: Temporal presence (0.2 weight)
        if features['has_temporal']:
            fact_score += 0.2
        
        # Factor 4: Foreign key count (0.2 weight)
        if features['fk_count'] > 2:
            fact_score += 0.2
        
        # Determine type and confidence
        if fact_score > 0.5:
            entity_type = 'fact'
            confidence = fact_score
        else:
            entity_type = 'dimension'
            confidence = 1.0 - fact_score
        
        logger.debug(f"Classified '{entity.canonical_name}' as {entity_type} (confidence: {confidence:.2f})")
        logger.debug(f"Features: {features}")
        
        return entity_type, confidence
    
    def _extract_features(self, 
                         entity: CanonicalEntity,
                         columns: List[CanonicalColumn]) -> Dict[str, Any]:
        """Extract classification features"""
        
        if not columns:
            return {
                'numeric_ratio': 0.0,
                'measure_count': 0,
                'has_temporal': False,
                'fk_count': 0,
                'avg_cardinality': 0
            }
        
        # Count numeric columns
        numeric_count = sum(
            1 for col in columns 
            if col.data_type in ['integer', 'float', 'numeric']
        )
        numeric_ratio = numeric_count / len(columns)
        
        # Count measure columns (by name and semantic type)
        measure_count = 0
        for col in columns:
            col_name_lower = col.canonical_name.lower()
            if any(kw in col_name_lower for kw in self.measure_keywords):
                measure_count += 1
            elif col.semantic_type and 'currency' in col.semantic_type.lower():
                measure_count += 1
        
        # Check for temporal columns
        has_temporal = any(
            col.data_type == 'datetime' or 
            (col.semantic_type and 'date' in col.semantic_type.lower())
            for col in columns
        )
        
        # Count foreign key-like columns (excluding PK)
        fk_count = 0
        for col in columns:
            if col.is_pk:
                continue
            col_name_lower = col.canonical_name.lower()
            if '_id' in col_name_lower or col_name_lower.endswith(' id'):
                fk_count += 1
        
        # Average cardinality
        avg_cardinality = sum(
            col.stats.get('distinct_count', 0) 
            for col in columns
        ) / len(columns)
        
        return {
            'numeric_ratio': numeric_ratio,
            'measure_count': measure_count,
            'has_temporal': has_temporal,
            'fk_count': fk_count,
            'avg_cardinality': avg_cardinality
        }

