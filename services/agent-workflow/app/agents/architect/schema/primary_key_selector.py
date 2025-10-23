"""
Primary key selection logic for SchemaEntity
"""
from typing import Optional, List, Dict, Any
import logging
from ..config import ArchitectConfig

logger = logging.getLogger(__name__)


class PrimaryKeySelector:
    """Selects the best primary key for an entity"""
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
    
    def select_primary_key(self, canonical_entity) -> str:
        """
        Select the best primary key for the entity
        
        Args:
            canonical_entity: CanonicalEntity with primary_key_candidates
            
        Returns:
            Primary key column name
        """
        pk_candidates = canonical_entity.primary_key_candidates
        
        if not pk_candidates:
            logger.warning(f"Entity '{canonical_entity.canonical_name}' has no PK candidates, defaulting to 'id'")
            return 'id'
        
        # pk_candidates is List[Dict] with:
        # - column_canonical: str
        # - confidence: float
        # - explanation: str
        
        # Sort by confidence (descending)
        sorted_candidates = sorted(
            pk_candidates, 
            key=lambda x: x.get('confidence', 0.0), 
            reverse=True
        )
        
        best_pk = sorted_candidates[0]
        logger.info(
            f"Selected PK '{best_pk['column_canonical']}' for '{canonical_entity.canonical_name}' "
            f"(confidence: {best_pk.get('confidence', 0.0):.2f})"
        )
        
        return best_pk['column_canonical']

