"""
Term extraction from enriched schema
"""
import re
import logging
from typing import List, Dict, Any
from .models import CandidateTerm

logger = logging.getLogger(__name__)


class TermExtractor:
    """Extract candidate glossary terms from enriched schema"""
    
    def __init__(self):
        # Suffixes to remove when normalizing terms
        self.suffixes_to_remove = [
            '_id', '_flag', '_code', '_key', '_indicator',
            '_status', '_type', '_date', '_time', '_datetime',
            '_num', '_number', '_count', '_total', '_amount'
        ]
    
    def extract_terms(self, enriched_schema: Dict[str, Any]) -> List[CandidateTerm]:
        """
        Extract all candidate terms from enriched schema
        
        Args:
            enriched_schema: Complete schema from TaggerAgent
            
        Returns:
            List of CandidateTerm objects
        """
        logger.info("Extracting candidate terms from enriched schema")
        
        candidate_terms = []
        entities = enriched_schema.get('entities', [])
        relationships = enriched_schema.get('relationships', [])
        
        # Build relationship map for quick lookup
        relationship_map = self._build_relationship_map(relationships)
        
        for entity in entities:
            # Extract entity-level term
            entity_term = self._extract_entity_term(entity, relationship_map)
            if entity_term:
                candidate_terms.append(entity_term)
            
            # Extract column-level terms
            column_terms = self._extract_column_terms(entity, relationship_map)
            candidate_terms.extend(column_terms)
            
            # Extract PK candidate terms
            pk_terms = self._extract_pk_terms(entity)
            candidate_terms.extend(pk_terms)
        
        # Deduplicate by normalized_term
        unique_terms = self._deduplicate_terms(candidate_terms)
        
        logger.info(f"Extracted {len(unique_terms)} unique candidate terms from {len(candidate_terms)} total")
        return unique_terms
    
    def _extract_entity_term(self, entity: Dict[str, Any], 
                            relationship_map: Dict[str, List[Dict]]) -> CandidateTerm:
        """Extract term from entity"""
        entity_name = entity.get('name', '')
        
        # Get relationships for this entity
        entity_relationships = relationship_map.get(entity_name, [])
        related_entities = list(set(
            [rel['to'] for rel in entity_relationships if rel['from'] == entity_name] +
            [rel['from'] for rel in entity_relationships if rel['to'] == entity_name]
        ))
        
        return CandidateTerm(
            raw_term=entity_name,
            normalized_term=self._normalize_term(entity_name),
            canonical_name=entity_name,
            source_type='entity',
            source_fqn=entity_name,
            
            # From AlignerAgent
            synonyms=entity.get('synonyms', []),
            raw_names=entity.get('raw_names', []),
            entity_type=entity.get('entity_type', 'unknown'),
            alignment_confidence=entity.get('alignment_confidence', 0.0),
            
            # From TaggerAgent
            classifications=[c['tag'] for c in entity.get('classifications', [])],
            classification_confidence=self._avg_confidence(entity.get('classifications', [])),
            
            # From ArchitectAgent
            relationships=entity_relationships,
            related_entities=related_entities
        )
    
    def _extract_column_terms(self, entity: Dict[str, Any],
                             relationship_map: Dict[str, List[Dict]]) -> List[CandidateTerm]:
        """Extract terms from entity columns"""
        terms = []
        entity_name = entity.get('name', '')
        entity_type = entity.get('entity_type', 'unknown')
        entity_relationships = relationship_map.get(entity_name, [])
        
        for column in entity.get('column_details', []):
            column_name = column.get('name', '')
            
            # Skip if column is just an ID without semantic meaning
            if self._is_technical_column(column_name):
                continue
            
            # Check if column participates in relationships
            column_relationships = [
                rel for rel in entity_relationships
                if rel.get('foreign_key') == column_name or rel.get('references') == column_name
            ]
            
            term = CandidateTerm(
                raw_term=column_name,
                normalized_term=self._normalize_term(column_name),
                canonical_name=column.get('displayName', column_name),
                source_type='column',
                source_fqn=f"{entity_name}.{column_name}",
                
                # From ProfilerAgent
                sample_values=column.get('statistics', {}).get('sample_values', []),
                semantic_type=column.get('semantic_type', 'unknown'),
                semantic_type_confidence=column.get('semantic_type_confidence', 0.0),
                
                # From AlignerAgent
                alignment_confidence=column.get('alignment_confidence', 0.0),
                synonyms=column.get('synonyms', []),
                raw_names=column.get('raw_names', []),
                entity_type=entity_type,
                is_primary_key=column.get('primary_key', False),
                
                # From TaggerAgent
                classifications=[c['tag'] for c in column.get('classifications', [])],
                classification_confidence=self._avg_confidence(column.get('classifications', [])),
                
                # From ArchitectAgent
                relationships=column_relationships,
                related_entities=[rel['to'] if rel['from'] == entity_name else rel['from'] 
                                for rel in column_relationships]
            )
            
            terms.append(term)
        
        return terms
    
    def _extract_pk_terms(self, entity: Dict[str, Any]) -> List[CandidateTerm]:
        """Extract terms from primary key candidates"""
        terms = []
        entity_name = entity.get('name', '')
        entity_type = entity.get('entity_type', 'unknown')
        
        # Get PK candidates if available (from AlignerAgent)
        pk_candidates = entity.get('primary_key_candidates', [])
        
        for pk_candidate in pk_candidates:
            column_name = pk_candidate.get('column_name', '')
            confidence = pk_candidate.get('confidence', 0.0)
            explanation = pk_candidate.get('explanation', '')
            
            # Find the column details
            column_details = next(
                (col for col in entity.get('column_details', []) 
                 if col.get('name') == column_name),
                None
            )
            
            if not column_details:
                continue
            
            term = CandidateTerm(
                raw_term=column_name,
                normalized_term=self._normalize_term(column_name),
                canonical_name=column_details.get('displayName', column_name),
                source_type='pk_candidate',
                source_fqn=f"{entity_name}.{column_name}",
                
                # From ProfilerAgent
                sample_values=column_details.get('statistics', {}).get('sample_values', []),
                semantic_type=column_details.get('semantic_type', 'unknown'),
                semantic_type_confidence=column_details.get('semantic_type_confidence', 0.0),
                
                # From AlignerAgent
                alignment_confidence=column_details.get('alignment_confidence', 0.0),
                synonyms=column_details.get('synonyms', []),
                raw_names=column_details.get('raw_names', []),
                entity_type=entity_type,
                is_primary_key=True,
                pk_confidence=confidence,
                pk_explanation=explanation,
                
                # From TaggerAgent
                classifications=[c['tag'] for c in column_details.get('classifications', [])],
                classification_confidence=self._avg_confidence(column_details.get('classifications', [])),
                
                # Relationships (PK columns often appear in FK relationships)
                relationships=[],
                related_entities=[]
            )
            
            terms.append(term)
        
        return terms
    
    def _build_relationship_map(self, relationships: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Build a map of entity name to its relationships"""
        relationship_map = {}
        
        for rel in relationships:
            from_entity = rel.get('from', '')
            to_entity = rel.get('to', '')
            
            if from_entity not in relationship_map:
                relationship_map[from_entity] = []
            if to_entity not in relationship_map:
                relationship_map[to_entity] = []
            
            relationship_map[from_entity].append(rel)
            relationship_map[to_entity].append(rel)
        
        return relationship_map
    
    def _normalize_term(self, term: str) -> str:
        """Normalize term for clustering and matching"""
        if not term:
            return ""
        
        # Convert to lowercase
        normalized = term.lower()
        
        # Remove suffixes
        for suffix in self.suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        # Remove special characters, keep only alphanumeric and spaces
        normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
        
        # Remove extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    def _is_technical_column(self, column_name: str) -> bool:
        """Check if column is purely technical (e.g., just 'id')"""
        normalized = column_name.lower().strip()
        technical_names = ['id', 'pk', 'key', 'index', 'rownum', 'seq']
        return normalized in technical_names
    
    def _avg_confidence(self, classifications: List[Dict[str, Any]]) -> float:
        """Calculate average confidence from classifications"""
        if not classifications:
            return 0.0
        
        confidences = [c.get('confidence', 0.0) for c in classifications]
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _deduplicate_terms(self, terms: List[CandidateTerm]) -> List[CandidateTerm]:
        """Deduplicate terms by normalized term, keeping highest confidence"""
        term_map = {}
        
        for term in terms:
            key = term.normalized_term
            
            if key not in term_map:
                term_map[key] = term
            else:
                # Keep term with higher overall confidence
                existing = term_map[key]
                existing_conf = (existing.alignment_confidence + 
                               existing.semantic_type_confidence + 
                               existing.classification_confidence) / 3
                new_conf = (term.alignment_confidence + 
                           term.semantic_type_confidence + 
                           term.classification_confidence) / 3
                
                if new_conf > existing_conf:
                    # Merge synonyms and raw_names
                    term.synonyms = list(set(term.synonyms + existing.synonyms))
                    term.raw_names = list(set(term.raw_names + existing.raw_names))
                    term_map[key] = term
                else:
                    # Merge into existing
                    existing.synonyms = list(set(existing.synonyms + term.synonyms))
                    existing.raw_names = list(set(existing.raw_names + term.raw_names))
        
        return list(term_map.values())

