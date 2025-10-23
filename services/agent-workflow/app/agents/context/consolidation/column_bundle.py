"""
Column context bundle builder
"""
import logging
from typing import Dict, Any, Optional
from ..models import ColumnContext
from ..graph.analyzer import GraphAnalyzer

logger = logging.getLogger(__name__)


class ColumnBundleBuilder:
    """Builds context bundles for columns"""
    
    def __init__(self, graph_analyzer: Optional[GraphAnalyzer] = None):
        """
        Initialize column bundle builder
        
        Args:
            graph_analyzer: Optional graph analyzer for enrichment
        """
        self.graph_analyzer = graph_analyzer
    
    def build_context(self, column: Dict[str, Any], entity: Dict[str, Any]) -> ColumnContext:
        """
        Build comprehensive context bundle for a column
        
        Args:
            column: Column dictionary from entity
            entity: Parent entity dictionary
            
        Returns:
            ColumnContext object
        """
        entity_name = entity['name']
        col_name = column['name']
        col_fqn = f"{entity_name}.{col_name}"
        
        # Get glossary term and relationships from graph
        glossary_term = None
        relationships = []
        
        if self.graph_analyzer:
            glossary_term = self.graph_analyzer.get_column_glossary_term(col_fqn)
            relationships = self.graph_analyzer.get_column_relationships(col_fqn)
        
        # Build statistics summary (if available)
        statistics = None
        if any(k in column for k in ['distinct_count', 'null_percentage', 'min_value', 'max_value']):
            statistics = {
                'distinct_count': column.get('distinct_count'),
                'null_percentage': column.get('null_percentage'),
                'min_value': column.get('min_value'),
                'max_value': column.get('max_value'),
                'mean_value': column.get('mean_value')
            }
        
        # Extract classification tags
        classifications = [c['tag'] for c in column.get('classifications', [])]
        
        return ColumnContext(
            name=col_name,
            canonical_name=column.get('canonical_name', col_name),
            entity_name=entity_name,
            fqn=col_fqn,
            semantic_type=column.get('semantic_type', 'unknown'),
            semantic_type_confidence=column.get('semantic_type_confidence', 0.0),
            data_type=column.get('data_type', 'VARCHAR'),
            data_type_display=column.get('data_type_display', 'varchar'),
            nullable=column.get('nullable', True),
            is_primary_key=column.get('is_primary_key', False),
            classifications=classifications,
            glossary_term=glossary_term,
            statistics=statistics,
            relationships=relationships
        )

