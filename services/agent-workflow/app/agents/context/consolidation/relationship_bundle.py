"""
Relationship context bundle builder
"""
import logging
from typing import Dict, Any, List
from ..models import RelationshipContext

logger = logging.getLogger(__name__)


class RelationshipBundleBuilder:
    """Builds context bundles for relationships"""
    
    def build_context(self, relationship: Dict[str, Any], 
                     entities: List[Dict[str, Any]]) -> RelationshipContext:
        """
        Build comprehensive context bundle for a relationship
        
        Args:
            relationship: Relationship dictionary from enriched schema
            entities: List of all entities for lookups
            
        Returns:
            RelationshipContext object
        """
        from_entity_name = relationship['from_entity']
        to_entity_name = relationship['to_entity']
        
        # Find entity details
        entity_map = {e['name']: e for e in entities}
        from_entity = entity_map.get(from_entity_name, {})
        to_entity = entity_map.get(to_entity_name, {})
        
        # Get entity types
        entity_types = {
            'from_entity_type': from_entity.get('entity_type', 'unknown'),
            'to_entity_type': to_entity.get('entity_type', 'unknown')
        }
        
        # Find column details
        from_column_name = relationship['from_column']
        to_column_name = relationship['to_column']
        
        from_column = next((c for c in from_entity.get('column_details', []) 
                           if c['name'] == from_column_name), {})
        to_column = next((c for c in to_entity.get('column_details', []) 
                         if c['name'] == to_column_name), {})
        
        column_semantics = {
            'from_column_semantic_type': from_column.get('semantic_type'),
            'to_column_semantic_type': to_column.get('semantic_type'),
            'from_column_nullable': from_column.get('nullable', True),
            'to_column_unique': to_column.get('is_unique', False)
        }
        
        return RelationshipContext(
            from_entity=from_entity_name,
            to_entity=to_entity_name,
            from_column=from_column_name,
            to_column=to_column_name,
            cardinality=relationship.get('cardinality', 'unknown'),
            confidence=relationship.get('confidence', 0.0),
            confidence_factors=relationship.get('confidence_breakdown', {}),
            detection_method=relationship.get('detection_method', 'unknown'),
            entity_types=entity_types,
            column_semantics=column_semantics
        )

