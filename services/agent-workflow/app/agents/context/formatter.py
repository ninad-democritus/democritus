"""
Output formatter - converts full enrichment to minimal schema
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OutputFormatter:
    """Formats enriched schema to minimal output for UI/data-pipeline"""
    
    def __init__(self, include_confidence: bool = True):
        """
        Initialize output formatter
        
        Args:
            include_confidence: Whether to include confidence scores
        """
        self.include_confidence = include_confidence
    
    def format_minimal(self, enriched_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert full enriched schema to minimal format
        
        Args:
            enriched_schema: Full enriched schema with all fields
            
        Returns:
            Minimal schema with only necessary fields
        """
        logger.info("Formatting to minimal output schema")
        
        minimal = {
            'entities': self._format_entities(enriched_schema.get('entities', [])),
            'relationships': self._format_relationships(enriched_schema.get('relationships', [])),
            'glossaries': self._format_glossaries(enriched_schema.get('glossaries', [])),
            'summary': self._format_summary(enriched_schema)
        }
        
        return minimal
    
    def _format_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format entities to minimal structure"""
        minimal_entities = []
        
        for entity in entities:
            minimal_entity = {
                'name': entity['name'],
                'displayName': entity['canonical_name'],
                'synonyms': entity.get('synonyms', []),
                'tableType': entity.get('entity_type', 'unknown').capitalize(),
                'description': entity.get('description', ''),
                'tags': [c['tag'] for c in entity.get('classifications', [])],
                'columns': self._format_columns(entity.get('column_details', []))
            }
            
            if self.include_confidence and 'alignment_confidence' in entity:
                minimal_entity['confidence'] = round(entity['alignment_confidence'], 2)
            
            minimal_entities.append(minimal_entity)
        
        return minimal_entities
    
    def _format_columns(self, columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format columns to minimal structure"""
        minimal_columns = []
        
        for col in columns:
            minimal_col = {
                'name': col['name'],
                'displayName': col.get('canonical_name', col['name']),
                'synonyms': col.get('synonyms', []),
                'description': col.get('description', ''),
                'dataType': col.get('data_type', 'VARCHAR'),
                'dataTypeDisplay': col.get('data_type_display', 'varchar'),
                'nullable': col.get('nullable', True),
                'tags': [c['tag'] for c in col.get('classifications', [])]
            }
            
            # Add type details if present
            if col.get('data_length'):
                minimal_col['dataLength'] = col['data_length']
            if col.get('precision'):
                minimal_col['precision'] = col['precision']
            if col.get('scale'):
                minimal_col['scale'] = col['scale']
            
            # Add constraint if primary key
            if col.get('is_primary_key'):
                minimal_col['constraint'] = 'PRIMARY_KEY'
            
            # Add glossary terms if present (need to extract from linking)
            glossary_terms = []
            # Note: This would be populated by checking which glossary terms link to this column
            # For now, leave empty - data-pipeline can handle the linking
            minimal_col['glossaryTerms'] = glossary_terms
            
            if self.include_confidence and 'alignment_confidence' in col:
                minimal_col['confidence'] = round(col['alignment_confidence'], 2)
            
            minimal_columns.append(minimal_col)
        
        return minimal_columns
    
    def _format_relationships(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format relationships to minimal structure"""
        minimal_relationships = []
        
        for rel in relationships:
            # Map cardinality to OpenMetadata enum
            cardinality_map = {
                'many-to-one': 'MANY_TO_ONE',
                'one-to-many': 'ONE_TO_MANY',
                'one-to-one': 'ONE_TO_ONE',
                'many-to-many': 'MANY_TO_MANY'
            }
            
            minimal_rel = {
                'fromEntity': rel['from_entity'],
                'toEntity': rel['to_entity'],
                'fromColumn': rel['from_column'],
                'toColumn': rel['to_column'],
                'relationshipType': 'CONTAINS',  # OpenMetadata relationship type
                'cardinality': cardinality_map.get(rel.get('cardinality', 'unknown'), 'MANY_TO_ONE'),
                'description': rel.get('narrative_description', rel.get('semantic_description', ''))
            }
            
            if self.include_confidence and 'confidence' in rel:
                minimal_rel['confidence'] = round(rel['confidence'], 2)
            
            minimal_relationships.append(minimal_rel)
        
        return minimal_relationships
    
    def _format_glossaries(self, glossaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format glossaries to minimal structure"""
        minimal_glossaries = []
        
        for glossary in glossaries:
            minimal_glossary = {
                'name': glossary['name'],
                'displayName': glossary.get('display_name', glossary['name']),
                'description': glossary.get('description', ''),
                'terms': self._format_glossary_terms(glossary.get('terms', []))
            }
            
            minimal_glossaries.append(minimal_glossary)
        
        return minimal_glossaries
    
    def _format_glossary_terms(self, terms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format glossary terms to minimal structure"""
        minimal_terms = []
        
        for term in terms:
            # Combine definition and contextual narrative
            description = term.get('definition', '')
            if term.get('contextual_narrative'):
                description += f"\n\n{term['contextual_narrative']}"
            
            minimal_term = {
                'name': term['canonical_name'],
                'displayName': term.get('display_name', term['canonical_name']),
                'description': description,
                'synonyms': term.get('synonyms', []),
                'relatedTerms': term.get('related_terms', []),
                'tags': term.get('classifications', []),
                'references': []
            }
            
            # Convert associations to references
            for entity_assoc in term.get('associated_entities', []):
                minimal_term['references'].append({
                    'type': 'table',
                    'name': entity_assoc.get('id')
                })
            
            for col_assoc in term.get('associated_columns', []):
                minimal_term['references'].append({
                    'type': 'column',
                    'name': col_assoc.get('id')
                })
            
            minimal_terms.append(minimal_term)
        
        return minimal_terms
    
    def _format_summary(self, enriched_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Format summary statistics"""
        entities = enriched_schema.get('entities', [])
        relationships = enriched_schema.get('relationships', [])
        glossaries = enriched_schema.get('glossaries', [])
        
        total_columns = sum(len(e.get('column_details', [])) for e in entities)
        total_terms = sum(len(g.get('terms', [])) for g in glossaries)
        
        # Calculate average confidence if available
        all_confidences = []
        for entity in entities:
            if 'alignment_confidence' in entity:
                all_confidences.append(entity['alignment_confidence'])
        
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else None
        
        summary = {
            'totalEntities': len(entities),
            'totalColumns': total_columns,
            'totalRelationships': len(relationships),
            'totalGlossaryTerms': total_terms
        }
        
        if avg_confidence and self.include_confidence:
            summary['avgConfidence'] = round(avg_confidence, 2)
        
        return summary

