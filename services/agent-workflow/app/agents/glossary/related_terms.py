"""
Related term identification using relationships and semantic similarity
"""
import numpy as np
import logging
from typing import List, Dict, Any, Set
from .models import GlossaryTerm
from .config import GlossaryConfig

logger = logging.getLogger(__name__)


class RelatedTermsService:
    """Identify related terms using relationships and semantic similarity"""
    
    def __init__(self, config: GlossaryConfig):
        self.config = config
    
    def identify_related_terms(self, glossary_terms: List[GlossaryTerm],
                              enriched_schema: Dict[str, Any]) -> None:
        """
        Identify related terms and populate related_terms and related_via_relationships
        Modifies glossary_terms in place
        
        Args:
            glossary_terms: List of GlossaryTerm objects
            enriched_schema: Complete schema with relationships
        """
        logger.info(f"Identifying related terms for {len(glossary_terms)} glossary terms")
        
        relationships = enriched_schema.get('relationships', [])
        
        # Build term lookup maps
        entity_to_term = self._build_entity_to_term_map(glossary_terms)
        column_to_term = self._build_column_to_term_map(glossary_terms)
        
        for term in glossary_terms:
            related_terms_set = set()
            relationship_links = []
            
            # Find relationship-based related terms
            if self.config.use_relationship_links:
                rel_terms, rel_links = self._find_relationship_based_terms(
                    term, relationships, entity_to_term, column_to_term
                )
                related_terms_set.update(rel_terms)
                relationship_links.extend(rel_links)
            
            # Find semantic similarity based related terms
            if self.config.use_semantic_links:
                semantic_terms = self._find_semantic_similar_terms(term, glossary_terms)
                related_terms_set.update(semantic_terms)
            
            # Limit to max related terms
            term.related_terms = list(related_terms_set)[:self.config.max_related_terms]
            term.related_via_relationships = relationship_links[:self.config.max_related_terms]
        
        # Log statistics
        terms_with_relationships = sum(1 for t in glossary_terms if t.related_via_relationships)
        terms_with_related = sum(1 for t in glossary_terms if t.related_terms)
        
        logger.info(f"Found {terms_with_relationships} terms with relationship links, "
                   f"{terms_with_related} terms with related terms")
    
    def _find_relationship_based_terms(self, term: GlossaryTerm,
                                      relationships: List[Dict[str, Any]],
                                      entity_to_term: Dict[str, str],
                                      column_to_term: Dict[str, str]) -> tuple:
        """
        Find related terms via relationships
        
        Returns:
            (related_term_ids, relationship_links) tuple
        """
        related_terms = set()
        relationship_links = []
        
        # Get entities and columns associated with this term
        term_entities = {assoc['id'] for assoc in term.associated_entities}
        term_columns = {assoc['id'] for assoc in term.associated_columns}
        
        # Find relationships involving this term's entities/columns
        for rel in relationships:
            from_entity = rel.get('from', '')
            to_entity = rel.get('to', '')
            from_column = rel.get('foreign_key', '')
            to_column = rel.get('references', '')
            from_fqn = f"{from_entity}.{from_column}"
            to_fqn = f"{to_entity}.{to_column}"
            
            # Check if this relationship involves the term
            term_involved = False
            related_entity = None
            related_column = None
            
            # Check entity involvement
            if from_entity in term_entities:
                term_involved = True
                related_entity = to_entity
                related_column = to_fqn
            elif to_entity in term_entities:
                term_involved = True
                related_entity = from_entity
                related_column = from_fqn
            
            # Check column involvement
            if from_fqn in term_columns:
                term_involved = True
                related_entity = to_entity
                related_column = to_fqn
            elif to_fqn in term_columns:
                term_involved = True
                related_entity = from_entity
                related_column = from_fqn
            
            if not term_involved:
                continue
            
            # Find glossary terms for related entities/columns
            related_term_id = None
            
            if related_entity and related_entity in entity_to_term:
                related_term_id = entity_to_term[related_entity]
            elif related_column and related_column in column_to_term:
                related_term_id = column_to_term[related_column]
            
            if related_term_id and related_term_id != term.term_id:
                related_terms.add(related_term_id)
                
                # Record relationship link
                relationship_links.append({
                    'relationship_id': f"{from_entity}_{to_entity}_{from_column}",
                    'semantic_description': rel.get('semantic', ''),
                    'related_term': related_term_id,
                    'cardinality': rel.get('type', 'unknown')
                })
        
        return list(related_terms), relationship_links
    
    def _find_semantic_similar_terms(self, term: GlossaryTerm,
                                    all_terms: List[GlossaryTerm]) -> List[str]:
        """
        Find semantically similar terms using embeddings
        
        Returns:
            List of related term IDs
        """
        # This would require embeddings for terms
        # For now, use classification-based similarity as a simpler approach
        related_terms = []
        
        for other_term in all_terms:
            if other_term.term_id == term.term_id:
                continue
            
            # Check classification overlap
            common_classifications = set(term.classifications) & set(other_term.classifications)
            
            if common_classifications:
                # Calculate similarity based on classification overlap
                similarity = len(common_classifications) / max(len(term.classifications), 
                                                               len(other_term.classifications))
                
                if similarity >= 0.5:  # At least 50% overlap
                    related_terms.append(other_term.term_id)
        
        return related_terms
    
    def _build_entity_to_term_map(self, glossary_terms: List[GlossaryTerm]) -> Dict[str, str]:
        """
        Build map from entity name to term ID
        
        Returns:
            Dict mapping entity name to term_id
        """
        entity_map = {}
        
        for term in glossary_terms:
            for assoc in term.associated_entities:
                entity_id = assoc.get('id')
                if entity_id:
                    entity_map[entity_id] = term.term_id
        
        return entity_map
    
    def _build_column_to_term_map(self, glossary_terms: List[GlossaryTerm]) -> Dict[str, str]:
        """
        Build map from column FQN to term ID
        
        Returns:
            Dict mapping column FQN to term_id
        """
        column_map = {}
        
        for term in glossary_terms:
            for assoc in term.associated_columns:
                column_fqn = assoc.get('id')
                if column_fqn:
                    column_map[column_fqn] = term.term_id
        
        return column_map

