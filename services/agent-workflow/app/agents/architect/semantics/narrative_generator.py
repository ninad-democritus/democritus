"""
Semantic narrative generation for relationships
"""
import logging
from ..models import Relationship
from ..config import ArchitectConfig
from .templates import SemanticTemplates

logger = logging.getLogger(__name__)


class SemanticNarrativeGenerator:
    """Generates human-readable semantic descriptions for relationships"""
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
        self.templates = SemanticTemplates()
    
    def generate_semantic(self, relationship: Relationship, from_col_semantic: str = None, to_col_semantic: str = None) -> str:
        """
        Generate semantic description for relationship
        
        Args:
            relationship: Relationship object
            from_col_semantic: Semantic type of from_column (optional)
            to_col_semantic: Semantic type of to_column (optional)
            
        Returns:
            Human-readable semantic description
        """
        # Step 1: Get template-based description
        base_text = self.templates.get_template(
            relationship.cardinality,
            relationship.from_entity,
            relationship.to_entity
        )
        
        # Step 2: Add semantic context if available
        if from_col_semantic and to_col_semantic:
            context = self.templates.get_semantic_context(from_col_semantic, to_col_semantic)
            if context:
                enriched_text = f"{base_text} {context}"
                logger.debug(f"Enriched semantic: {enriched_text}")
                return enriched_text
        
        return base_text
    
    def generate_semantic_with_columns(
        self,
        relationship: Relationship,
        from_column_obj=None,
        to_column_obj=None
    ) -> str:
        """
        Generate semantic description with full column objects
        
        Args:
            relationship: Relationship object
            from_column_obj: ColumnSchema object for from_column
            to_column_obj: ColumnSchema object for to_column
            
        Returns:
            Human-readable semantic description
        """
        from_semantic = from_column_obj.semantic_type if from_column_obj else None
        to_semantic = to_column_obj.semantic_type if to_column_obj else None
        
        return self.generate_semantic(relationship, from_semantic, to_semantic)

