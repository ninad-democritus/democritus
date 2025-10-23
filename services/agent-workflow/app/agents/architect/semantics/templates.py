"""
Template-based semantic descriptions for relationships
"""
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class SemanticTemplates:
    """Provides templates for generating semantic relationship descriptions"""
    
    def __init__(self):
        # Cardinality-based templates
        self.cardinality_templates = {
            'many-to-one': [
                "Each {from_entity} belongs to one {to_entity}",
                "Each {from_entity} is associated with one {to_entity}",
                "Each {from_entity} references one {to_entity}"
            ],
            'one-to-many': [
                "Each {to_entity} has many {from_entity_plural}",
                "Each {to_entity} contains multiple {from_entity_plural}",
                "Each {to_entity} is associated with multiple {from_entity_plural}"
            ],
            'one-to-one': [
                "Each {from_entity} has exactly one {to_entity}",
                "Each {from_entity} corresponds to one {to_entity}",
                "Each {from_entity} is paired with one {to_entity}"
            ],
            'many-to-many': [
                "Multiple {from_entity_plural} relate to multiple {to_entity_plural}",
                "{from_entity_plural} and {to_entity_plural} have a many-to-many relationship",
                "Each {from_entity} can relate to many {to_entity_plural} and vice versa"
            ]
        }
        
        # Semantic type context additions
        self.semantic_contexts = {
            ('email', 'email'): 'via email address match',
            ('uuid', 'uuid'): 'via unique identifier',
            ('uuid', 'identifier'): 'via unique identifier',
            ('ssn', 'ssn'): 'via social security number',
            ('zipcode', 'zipcode'): 'via geographic location',
            ('phone_number', 'phone_number'): 'via phone number',
            ('datetime', 'datetime'): 'via timestamp correlation',
            ('credit_card', 'credit_card'): 'via credit card number',
        }
    
    def get_template(self, cardinality: str, from_entity: str, to_entity: str) -> str:
        """
        Get semantic template for relationship
        
        Args:
            cardinality: Relationship cardinality
            from_entity: Source entity name
            to_entity: Target entity name
            
        Returns:
            Formatted semantic description
        """
        templates = self.cardinality_templates.get(cardinality, self.cardinality_templates['many-to-one'])
        template = templates[0]  # Use primary template
        
        # Simple pluralization
        from_entity_plural = self._pluralize(from_entity)
        to_entity_plural = self._pluralize(to_entity)
        
        return template.format(
            from_entity=from_entity,
            to_entity=to_entity,
            from_entity_plural=from_entity_plural,
            to_entity_plural=to_entity_plural
        )
    
    def get_semantic_context(self, from_semantic: str, to_semantic: str) -> str:
        """
        Get contextual description based on semantic types
        
        Args:
            from_semantic: Source column semantic type
            to_semantic: Target column semantic type
            
        Returns:
            Context string (empty if no special context)
        """
        if not from_semantic or not to_semantic:
            return ""
        
        # Try exact pair
        pair = (from_semantic.lower(), to_semantic.lower())
        if pair in self.semantic_contexts:
            return self.semantic_contexts[pair]
        
        # Try reverse pair
        reverse_pair = (to_semantic.lower(), from_semantic.lower())
        if reverse_pair in self.semantic_contexts:
            return self.semantic_contexts[reverse_pair]
        
        return ""
    
    def _pluralize(self, word: str) -> str:
        """Simple pluralization (good enough for most entity names)"""
        word_lower = word.lower()
        
        # Already plural or uncountable
        if word_lower.endswith('s') or word_lower.endswith('data') or word_lower.endswith('information'):
            return word
        
        # Special cases
        if word_lower.endswith('y'):
            return word[:-1] + 'ies'
        elif word_lower.endswith(('ch', 'sh', 'x', 'z')):
            return word + 'es'
        else:
            return word + 's'

