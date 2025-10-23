"""
Glossary/domain context bundle builder
"""
import logging
from typing import Dict, Any, List
from ..models import GlossaryContext

logger = logging.getLogger(__name__)


class GlossaryBundleBuilder:
    """Builds context bundles for glossaries/domains"""
    
    def build_context(self, glossary: Dict[str, Any],
                     entities: List[Dict[str, Any]],
                     relationships: List[Dict[str, Any]]) -> GlossaryContext:
        """
        Build comprehensive context bundle for a glossary/domain
        
        Args:
            glossary: Glossary dictionary from enriched schema
            entities: List of all entities
            relationships: List of all relationships
            
        Returns:
            GlossaryContext object
        """
        # Get source entities for this glossary
        source_entity_names = glossary.get('source_entities', [])
        entity_map = {e['name']: e for e in entities}
        
        glossary_entities = []
        for entity_name in source_entity_names:
            entity = entity_map.get(entity_name)
            if entity:
                glossary_entities.append({
                    'name': entity['name'],
                    'type': entity.get('entity_type'),
                    'row_count': entity.get('row_count', 0),
                    'primary_glossary_term': None  # Could link back to term
                })
        
        # Get relationships between entities in this domain
        domain_relationships = []
        for rel in relationships:
            if rel['from_entity'] in source_entity_names and rel['to_entity'] in source_entity_names:
                domain_relationships.append({
                    'from': rel['from_entity'],
                    'to': rel['to_entity'],
                    'type': rel.get('cardinality')
                })
        
        # Simplify terms
        terms_info = []
        for term in glossary.get('terms', []):
            terms_info.append({
                'canonical_name': term['canonical_name'],
                'definition': term.get('definition', ''),
                'associated_entities': [a['id'] for a in term.get('associated_entities', [])],
                'related_terms': term.get('related_terms', [])
            })
        
        # Data characteristics
        total_rows = sum(e['row_count'] for e in glossary_entities)
        fact_count = sum(1 for e in glossary_entities if e['type'] == 'fact')
        dim_count = sum(1 for e in glossary_entities if e['type'] == 'dimension')
        
        data_characteristics = {
            'total_entities': len(glossary_entities),
            'fact_entities': fact_count,
            'dimension_entities': dim_count,
            'total_rows': total_rows,
            'total_relationships': len(domain_relationships),
            'total_terms': len(terms_info)
        }
        
        return GlossaryContext(
            name=glossary['name'],
            display_name=glossary.get('display_name', glossary['name']),
            entities=glossary_entities,
            terms=terms_info,
            relationships=domain_relationships,
            classification_profile=glossary.get('classification_summary', {}),
            data_characteristics=data_characteristics
        )

