"""
Context-based classifier
Uses entity context (relationships, entity type) for classification
"""
from typing import List, Dict, Any
import logging
from .base import BaseClassifier
from ..models import Classification

logger = logging.getLogger(__name__)


class ContextClassifier(BaseClassifier):
    """Classifies columns based on entity context"""
    
    def classify_column(self, column: Dict[str, Any], entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify column based on entity context
        
        Args:
            column: Column metadata
            entity: Parent entity with relationships and type
            
        Returns:
            List of Classification objects
        """
        classifications = []
        column_name = column.get('name')
        
        # Check if this column is a foreign key (used in relationships)
        relationships = entity.get('relationships', [])
        for rel in relationships:
            # Check if this column is the foreign key
            if rel.get('foreign_key') == column_name:
                rel_confidence = rel.get('confidence', 0.5)
                
                # Only classify as JoinKey if relationship confidence is reasonable
                if rel_confidence >= 0.6:
                    # Use relationship confidence as basis
                    final_confidence = rel_confidence * 0.92
                    
                    classifications.append(Classification(
                        tag='DataDomain.JoinKey',
                        confidence=final_confidence,
                        source='relationship_context',
                        upstream_factors={
                            'relationship_to': rel.get('to'),
                            'relationship_confidence': rel_confidence,
                            'cardinality': rel.get('type')
                        }
                    ))
                    
                    logger.info(f"{column_name} classified as JoinKey based on relationship to {rel.get('to')} "
                               f"(confidence={final_confidence:.2f})")
                    break  # Only classify once as JoinKey
        
        # Temporal classification based on entity type
        semantic_type = column.get('semantic_type', '')
        if 'date' in semantic_type.lower() or 'time' in semantic_type.lower():
            entity_type = entity.get('entity_type', '')
            
            if entity_type == 'fact':
                classifications.append(Classification(
                    tag='Temporal.Fact',
                    confidence=0.85,
                    source='entity_type_context',
                    upstream_factors={
                        'entity_type': entity_type,
                        'semantic_type': semantic_type
                    }
                ))
                logger.debug(f"{column_name} classified as Temporal.Fact (in fact table)")
            
            elif entity_type == 'dimension':
                classifications.append(Classification(
                    tag='Temporal.Dimension',
                    confidence=0.85,
                    source='entity_type_context',
                    upstream_factors={
                        'entity_type': entity_type,
                        'semantic_type': semantic_type
                    }
                ))
                logger.debug(f"{column_name} classified as Temporal.Dimension (in dimension table)")
        
        return classifications
    
    def classify_entity(self, entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify entity based on its type
        
        Args:
            entity: Entity metadata
            
        Returns:
            List of Classification objects
        """
        classifications = []
        entity_type = entity.get('entity_type', '')
        alignment_confidence = entity.get('alignment_confidence', 1.0)
        
        if entity_type == 'fact':
            # Use alignment confidence as basis
            final_confidence = alignment_confidence * 0.95
            
            classifications.append(Classification(
                tag='DataDomain.Fact',
                confidence=final_confidence,
                source='entity_type',
                upstream_factors={
                    'entity_type': entity_type,
                    'alignment_confidence': alignment_confidence
                }
            ))
            logger.info(f"Entity {entity.get('name')} classified as Fact (confidence={final_confidence:.2f})")
        
        elif entity_type == 'dimension':
            final_confidence = alignment_confidence * 0.95
            
            classifications.append(Classification(
                tag='DataDomain.Dimension',
                confidence=final_confidence,
                source='entity_type',
                upstream_factors={
                    'entity_type': entity_type,
                    'alignment_confidence': alignment_confidence
                }
            ))
            logger.info(f"Entity {entity.get('name')} classified as Dimension (confidence={final_confidence:.2f})")
        
        return classifications

