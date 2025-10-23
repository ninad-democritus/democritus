"""
Graph analysis utilities for context enrichment
"""
import networkx as nx
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)


class GraphAnalyzer:
    """Analyzes semantic graph to extract contextual information"""
    
    def __init__(self, graph: nx.DiGraph, max_hops: int = 2):
        """
        Initialize graph analyzer
        
        Args:
            graph: Semantic graph from SemanticGraphBuilder
            max_hops: Maximum relationship hops for context
        """
        self.graph = graph
        self.max_hops = max_hops
    
    def get_entity_relationships(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for an entity
        
        Args:
            entity_name: Entity node name
            
        Returns:
            List of relationship details
        """
        relationships = []
        
        # Outgoing relationships
        for target in self.graph.successors(entity_name):
            edge_data = self.graph.get_edge_data(entity_name, target)
            if edge_data and edge_data.get('type') == 'relationship':
                relationships.append({
                    'direction': 'outgoing',
                    'to_entity': target,
                    'cardinality': edge_data.get('cardinality'),
                    'description': edge_data.get('semantic_description'),
                    'confidence': edge_data.get('confidence'),
                    'via_column': edge_data.get('from_column')
                })
        
        # Incoming relationships
        for source in self.graph.predecessors(entity_name):
            edge_data = self.graph.get_edge_data(source, entity_name)
            if edge_data and edge_data.get('type') == 'relationship':
                relationships.append({
                    'direction': 'incoming',
                    'from_entity': source,
                    'cardinality': edge_data.get('cardinality'),
                    'description': edge_data.get('semantic_description'),
                    'confidence': edge_data.get('confidence')
                })
        
        return relationships
    
    def get_column_glossary_term(self, column_fqn: str) -> str:
        """
        Find glossary term linked to a column
        
        Args:
            column_fqn: Fully qualified column name (Entity.column)
            
        Returns:
            Glossary term name or None
        """
        for pred in self.graph.predecessors(column_fqn):
            node_data = self.graph.nodes.get(pred, {})
            if node_data.get('type') == 'glossary_term':
                return node_data.get('canonical_name')
        return None
    
    def get_entity_glossary_terms(self, entity_name: str) -> List[str]:
        """
        Find all glossary terms associated with an entity
        
        Args:
            entity_name: Entity node name
            
        Returns:
            List of glossary term names
        """
        terms = []
        for pred in self.graph.predecessors(entity_name):
            node_data = self.graph.nodes.get(pred, {})
            if node_data.get('type') == 'glossary_term':
                terms.append(node_data.get('canonical_name'))
        return terms
    
    def get_entity_domain(self, entity_name: str) -> str:
        """
        Find domain for an entity through glossary terms
        
        Args:
            entity_name: Entity node name
            
        Returns:
            Domain name or None
        """
        for pred in self.graph.predecessors(entity_name):
            node_data = self.graph.nodes.get(pred, {})
            if node_data.get('type') == 'glossary_term':
                return node_data.get('domain')
        return None
    
    def get_classification_summary(self, entity_name: str) -> Dict[str, List[str]]:
        """
        Get summary of all classifications for entity and its columns
        
        Args:
            entity_name: Entity node name
            
        Returns:
            Dict mapping classification tags to column names
        """
        summary = {}
        
        # Get entity-level classifications
        entity_data = self.graph.nodes.get(entity_name, {})
        entity_classifications = entity_data.get('classifications', [])
        if entity_classifications:
            summary['entity_level'] = entity_classifications
        
        # Get column-level classifications grouped by tag
        for successor in self.graph.successors(entity_name):
            edge_data = self.graph.get_edge_data(entity_name, successor)
            if edge_data and edge_data.get('type') == 'has_column':
                col_data = self.graph.nodes.get(successor, {})
                col_classifications = col_data.get('classifications', [])
                col_name = col_data.get('name')
                
                for tag in col_classifications:
                    if tag not in summary:
                        summary[tag] = []
                    summary[tag].append(col_name)
        
        return summary
    
    def get_column_relationships(self, column_fqn: str) -> List[Dict[str, Any]]:
        """
        Find relationships where this column is involved (FK references)
        
        Args:
            column_fqn: Fully qualified column name
            
        Returns:
            List of relationship details
        """
        relationships = []
        entity_name = column_fqn.split('.')[0] if '.' in column_fqn else None
        
        if not entity_name:
            return relationships
        
        # Check all relationships from this entity
        for target in self.graph.successors(entity_name):
            edge_data = self.graph.get_edge_data(entity_name, target)
            if edge_data and edge_data.get('type') == 'relationship':
                from_col = edge_data.get('from_column')
                if from_col and column_fqn.endswith(from_col):
                    relationships.append({
                        'referenced_in': f"{target}.{edge_data.get('to_column')}",
                        'relationship': f"{entity_name} references {target}",
                        'cardinality': edge_data.get('cardinality')
                    })
        
        return relationships

