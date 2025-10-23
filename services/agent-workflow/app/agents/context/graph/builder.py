"""
Semantic graph builder for context analysis
"""
import networkx as nx
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SemanticGraphBuilder:
    """Builds a semantic knowledge graph from enriched schema"""
    
    def build_graph(self, enriched_schema: Dict[str, Any]) -> nx.DiGraph:
        """
        Build semantic graph with entities, columns, glossary terms, and relationships
        
        Args:
            enriched_schema: Fully enriched schema from GlossaryAgent
            
        Returns:
            NetworkX directed graph
        """
        G = nx.DiGraph()
        
        # Add entity nodes
        for entity in enriched_schema.get('entities', []):
            entity_name = entity['name']
            G.add_node(entity_name, 
                      type='entity',
                      canonical_name=entity['canonical_name'],
                      synonyms=entity.get('synonyms', []),
                      entity_type=entity.get('entity_type', 'unknown'),
                      confidence=entity.get('alignment_confidence', 0.0),
                      classifications=[c['tag'] for c in entity.get('classifications', [])],
                      primary_key=entity.get('primary_key'),
                      row_count=entity.get('row_count', 0))
            
            # Add column nodes and edges
            for column in entity.get('column_details', []):
                col_name = column['name']
                col_fqn = f"{entity_name}.{col_name}"
                
                G.add_node(col_fqn,
                          type='column',
                          name=col_name,
                          canonical_name=column.get('canonical_name', col_name),
                          entity=entity_name,
                          semantic_type=column.get('semantic_type', 'unknown'),
                          semantic_type_confidence=column.get('semantic_type_confidence', 0.0),
                          data_type=column.get('data_type'),
                          data_type_display=column.get('data_type_display'),
                          nullable=column.get('nullable', True),
                          is_primary_key=column.get('is_primary_key', False),
                          classifications=[c['tag'] for c in column.get('classifications', [])])
                
                # Link column to entity
                G.add_edge(entity_name, col_fqn, 
                          type='has_column',
                          is_primary_key=column.get('is_primary_key', False))
        
        # Add relationship edges
        for rel in enriched_schema.get('relationships', []):
            G.add_edge(rel['from_entity'], rel['to_entity'],
                      type='relationship',
                      from_column=rel['from_column'],
                      to_column=rel['to_column'],
                      cardinality=rel['cardinality'],
                      confidence=rel['confidence'],
                      semantic_description=rel.get('semantic_description', ''),
                      detection_method=rel.get('detection_method', 'unknown'))
        
        # Add glossary term nodes
        for glossary in enriched_schema.get('glossaries', []):
            domain_name = glossary['name']
            
            for term in glossary.get('terms', []):
                term_name = f"term:{term['canonical_name']}"
                
                G.add_node(term_name,
                          type='glossary_term',
                          canonical_name=term['canonical_name'],
                          display_name=term.get('display_name', term['canonical_name']),
                          definition=term.get('definition', ''),
                          domain=domain_name,
                          confidence=term.get('confidence', 0.0),
                          is_key_identifier=term.get('is_key_identifier', False))
                
                # Link terms to entities
                for assoc in term.get('associated_entities', []):
                    entity_id = assoc.get('id')
                    if entity_id and G.has_node(entity_id):
                        G.add_edge(term_name, entity_id, type='glossary_link', link_type='entity')
                
                # Link terms to columns
                for assoc in term.get('associated_columns', []):
                    col_fqn = assoc.get('id')
                    if col_fqn and G.has_node(col_fqn):
                        G.add_edge(term_name, col_fqn, type='glossary_link', link_type='column')
                
                # Link related terms
                for related_term_name in term.get('related_terms', []):
                    related_node = f"term:{related_term_name}"
                    if G.has_node(related_node):
                        G.add_edge(term_name, related_node, type='related_term')
        
        logger.info(f"Built semantic graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        
        return G

