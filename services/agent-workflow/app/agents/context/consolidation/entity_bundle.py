"""
Entity context bundle builder
"""
import logging
from typing import Dict, Any, Optional
from ..models import EntityContext
from ..graph.analyzer import GraphAnalyzer

logger = logging.getLogger(__name__)


class EntityBundleBuilder:
    """Builds context bundles for entities"""
    
    def __init__(self, graph_analyzer: Optional[GraphAnalyzer] = None):
        """
        Initialize entity bundle builder
        
        Args:
            graph_analyzer: Optional graph analyzer for enrichment
        """
        self.graph_analyzer = graph_analyzer
    
    def build_context(self, entity: Dict[str, Any]) -> EntityContext:
        """
        Build comprehensive context bundle for an entity
        
        Args:
            entity: Entity dictionary from enriched schema
            
        Returns:
            EntityContext object
        """
        entity_name = entity['name']
        
        # Get relationships from graph if available
        relationships = []
        glossary_terms = []
        domain = None
        classification_summary = {}
        
        if self.graph_analyzer:
            relationships = self.graph_analyzer.get_entity_relationships(entity_name)
            glossary_terms = self.graph_analyzer.get_entity_glossary_terms(entity_name)
            domain = self.graph_analyzer.get_entity_domain(entity_name)
            classification_summary = self.graph_analyzer.get_classification_summary(entity_name)
        
        # Extract primary key info
        pk_column = entity.get('primary_key')
        pk_info = {'column': pk_column}
        
        # Find PK column details
        for col in entity.get('column_details', []):
            if col['name'] == pk_column:
                pk_info['is_unique'] = col.get('is_unique', False)
                pk_info['semantic_type'] = col.get('semantic_type')
                break
        
        # Simplify column info for context
        columns = []
        for col in entity.get('column_details', []):
            columns.append({
                'name': col['name'],
                'canonical_name': col.get('canonical_name', col['name']),
                'role': 'primary_key' if col.get('is_primary_key') else 'foreign_key' if col['name'].endswith('_id') else 'attribute',
                'semantic_type': col.get('semantic_type'),
                'classifications': [c['tag'] for c in col.get('classifications', [])],
                'data_type_display': col.get('data_type_display')
            })
        
        # Extract classification tags
        classifications = [c['tag'] for c in entity.get('classifications', [])]
        
        return EntityContext(
            canonical_name=entity['canonical_name'],
            synonyms=entity.get('synonyms', []),
            entity_type=entity.get('entity_type', 'unknown'),
            confidence=entity.get('alignment_confidence', 0.0),
            primary_key=pk_info,
            columns=columns,
            relationships=relationships,
            classifications=classifications,
            glossary_terms=glossary_terms,
            row_count=entity.get('row_count', 0),
            domain=domain
        )

