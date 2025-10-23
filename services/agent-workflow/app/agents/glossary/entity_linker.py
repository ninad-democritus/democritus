"""
Entity and column linking for glossary terms
"""
import numpy as np
import logging
from typing import List, Dict, Any, Set, Tuple
from .models import GlossaryTerm, CandidateTerm
from .config import GlossaryConfig

logger = logging.getLogger(__name__)


class EntityLinker:
    """Link glossary terms to entities and columns"""
    
    def __init__(self, config: GlossaryConfig, embedding_service=None):
        """
        Initialize entity linker
        
        Args:
            config: GlossaryConfig instance
            embedding_service: Optional EmbeddingService for fuzzy matching
        """
        self.config = config
        self.embedding_service = embedding_service
    
    def link_terms_to_schema(self, glossary_terms: List[GlossaryTerm],
                            enriched_schema: Dict[str, Any]) -> None:
        """
        Link glossary terms to entities and columns in schema
        Modifies glossary_terms in place
        
        Args:
            glossary_terms: List of GlossaryTerm objects to link
            enriched_schema: Complete schema with entities and columns
        """
        logger.info(f"Linking {len(glossary_terms)} glossary terms to schema")
        
        entities = enriched_schema.get('entities', [])
        
        for term in glossary_terms:
            # Link to entities
            term.associated_entities = self._link_to_entities(term, entities)
            
            # Link to columns
            term.associated_columns = self._link_to_columns(term, entities)
        
        # Log linking statistics
        terms_with_entities = sum(1 for t in glossary_terms if t.associated_entities)
        terms_with_columns = sum(1 for t in glossary_terms if t.associated_columns)
        
        logger.info(f"Linked {terms_with_entities} terms to entities, "
                   f"{terms_with_columns} terms to columns")
    
    def _link_to_entities(self, term: GlossaryTerm, 
                         entities: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Link term to matching entities
        
        Returns:
            List of {id, type} dicts for associated entities
        """
        associated = []
        
        for entity in entities:
            entity_name = entity.get('name', '')
            
            # Direct match on canonical name
            if self._names_match(term.canonical_name, entity_name):
                associated.append({
                    'id': entity_name,
                    'type': 'table'
                })
                continue
            
            # Match on synonyms
            if any(self._names_match(syn, entity_name) for syn in term.synonyms):
                associated.append({
                    'id': entity_name,
                    'type': 'table'
                })
                continue
            
            # Match on entity raw_names (how users named it)
            entity_raw_names = entity.get('raw_names', [])
            if any(self._names_match(term.canonical_name, raw_name) for raw_name in entity_raw_names):
                associated.append({
                    'id': entity_name,
                    'type': 'table'
                })
                continue
            
            # Fuzzy match using embeddings if available
            if self.embedding_service and self._fuzzy_match(term.canonical_name, entity_name):
                associated.append({
                    'id': entity_name,
                    'type': 'table'
                })
                continue
        
        return associated
    
    def _link_to_columns(self, term: GlossaryTerm,
                        entities: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Link term to matching columns
        
        Returns:
            List of {id, type} dicts for associated columns
        """
        associated = []
        
        for entity in entities:
            entity_name = entity.get('name', '')
            
            for column in entity.get('column_details', []):
                column_name = column.get('name', '')
                column_display_name = column.get('displayName', column_name)
                column_fqn = f"{entity_name}.{column_name}"
                
                # Direct match on canonical name
                if self._names_match(term.canonical_name, column_name) or \
                   self._names_match(term.canonical_name, column_display_name):
                    associated.append({
                        'id': column_fqn,
                        'type': 'column'
                    })
                    continue
                
                # Match on term synonyms
                if any(self._names_match(syn, column_name) for syn in term.synonyms) or \
                   any(self._names_match(syn, column_display_name) for syn in term.synonyms):
                    associated.append({
                        'id': column_fqn,
                        'type': 'column'
                    })
                    continue
                
                # Match on column synonyms
                column_synonyms = column.get('synonyms', [])
                if any(self._names_match(term.canonical_name, syn) for syn in column_synonyms):
                    associated.append({
                        'id': column_fqn,
                        'type': 'column'
                    })
                    continue
                
                # Match on column raw_names
                column_raw_names = column.get('raw_names', [])
                if any(self._names_match(term.canonical_name, raw_name) for raw_name in column_raw_names):
                    associated.append({
                        'id': column_fqn,
                        'type': 'column'
                    })
                    continue
                
                # Fuzzy match using embeddings if available
                if self.embedding_service:
                    if self._fuzzy_match(term.canonical_name, column_name) or \
                       self._fuzzy_match(term.canonical_name, column_display_name):
                        associated.append({
                            'id': column_fqn,
                            'type': 'column'
                        })
                        continue
        
        return associated
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """
        Check if two names match (case-insensitive, normalized)
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            True if names match
        """
        if not name1 or not name2:
            return False
        
        # Normalize both names
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)
        
        return norm1 == norm2
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for matching"""
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove underscores and hyphens, replace with spaces
        normalized = normalized.replace('_', ' ').replace('-', ' ')
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    def _fuzzy_match(self, name1: str, name2: str) -> bool:
        """
        Check if names match using embedding similarity
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            True if similarity exceeds threshold
        """
        if not self.embedding_service:
            return False
        
        try:
            # Compute embeddings
            embeddings = self.embedding_service.compute_embeddings([name1, name2])
            
            # Compute cosine similarity
            emb1 = embeddings[0]
            emb2 = embeddings[1]
            
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            
            return float(similarity) >= self.config.name_match_threshold
            
        except Exception as e:
            logger.debug(f"Fuzzy match failed for '{name1}' vs '{name2}': {e}")
            return False

