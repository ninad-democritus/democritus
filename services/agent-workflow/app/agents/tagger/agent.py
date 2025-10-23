"""
TaggerAgent - Main orchestrator for governance classification
"""
from typing import Dict, Any, List, Optional
import logging
from .models import Classification, ClassificationResult
from .config import TaggerConfig
from .classifiers import (
    SemanticTypeClassifier,
    NamePatternClassifier,
    StatisticalClassifier,
    ContextClassifier,
    ClassificationMerger
)
from .confidence import ConfidenceScorer

try:
    from ..observability import trace_agent, observability
except ImportError:
    # Fallback for when observability is not available
    def trace_agent(name):
        def decorator(func):
            return func
        return decorator
    
    class MockObservability:
        def create_agent_span(self, *args, **kwargs): return None
        def log_agent_output(self, *args, **kwargs): pass
        def end_agent_span(self, *args, **kwargs): pass
    
    observability = MockObservability()

logger = logging.getLogger(__name__)


class TaggerAgent:
    """
    TaggerAgent: Assigns OpenMetadata governance classifications to entities and columns
    
    Responsibilities:
    - Assign governance classifications (PII, Finance, Temporal, DataDomain, etc.)
    - Calculate confidence scores for each classification
    - Use upstream confidence to adjust classification confidence
    - Pass through all upstream enrichments unchanged
    - Provide classification summary for monitoring
    """
    
    def __init__(self, config: Optional[TaggerConfig] = None):
        """
        Initialize TaggerAgent with configuration
        
        Args:
            config: TaggerConfig instance (defaults to env-based config)
        """
        self.config = config or TaggerConfig.from_env()
        
        # Initialize classifiers
        self.semantic_classifier = SemanticTypeClassifier(self.config)
        self.name_classifier = NamePatternClassifier(self.config)
        self.stats_classifier = StatisticalClassifier(self.config)
        self.context_classifier = ContextClassifier(self.config)
        
        # Initialize merger and scorer
        self.merger = ClassificationMerger(self.config)
        self.confidence_scorer = ConfidenceScorer(self.config)
        
        logger.info("TaggerAgent initialized")
    
    @trace_agent("TaggerAgent")
    def enrich_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich schema with governance classifications
        
        Args:
            schema: Schema from ArchitectAgent with entities and relationships
            
        Returns:
            Enriched schema with classifications added
        """
        span = observability.create_agent_span("TaggerAgent", {
            "input_entities": len(schema.get('entities', [])),
            "input_relationships": len(schema.get('relationships', []))
        })
        
        try:
            logger.info(f"Starting classification for {len(schema.get('entities', []))} entities")
            
            # Create enriched schema (copy to avoid mutation)
            enriched_schema = schema.copy()
            
            # Track metrics
            total_columns = 0
            classified_columns = 0
            classified_entities = 0
            classification_distribution = {}
            
            # Process each entity
            for entity in enriched_schema.get('entities', []):
                # Classify entity
                entity_classifications = self._classify_entity(entity)
                entity['classifications'] = [self._classification_to_dict(c) for c in entity_classifications]
                
                if entity_classifications:
                    classified_entities += 1
                    for classification in entity_classifications:
                        classification_distribution[classification.tag] = \
                            classification_distribution.get(classification.tag, 0) + 1
                
                # Classify each column
                for column in entity.get('column_details', []):
                    total_columns += 1
                    
                    column_classifications = self._classify_column(column, entity)
                    column['classifications'] = [self._classification_to_dict(c) for c in column_classifications]
                    
                    if column_classifications:
                        classified_columns += 1
                        for classification in column_classifications:
                            classification_distribution[classification.tag] = \
                                classification_distribution.get(classification.tag, 0) + 1
            
            # Add classification summary
            enriched_schema['classification_summary'] = {
                'total_entities': len(enriched_schema.get('entities', [])),
                'classified_entities': classified_entities,
                'total_columns': total_columns,
                'classified_columns': classified_columns,
                'classification_coverage': (classified_columns / total_columns * 100) if total_columns > 0 else 0.0,
                'classification_distribution': classification_distribution,
                'unique_classifications': len(classification_distribution)
            }
            
            # Log results
            logger.info(f"Classification complete: {classified_entities}/{len(enriched_schema.get('entities', []))} entities, "
                       f"{classified_columns}/{total_columns} columns ({enriched_schema['classification_summary']['classification_coverage']:.1f}% coverage)")
            
            observability.log_agent_output("TaggerAgent", {
                "classified_columns": classified_columns,
                "classified_entities": classified_entities
            }, enriched_schema['classification_summary'])
            
            observability.end_agent_span(span, {
                "classified_columns": classified_columns,
                "classified_entities": classified_entities
            })
            
            return enriched_schema
            
        except Exception as e:
            observability.end_agent_span(span, {}, str(e))
            logger.exception("TaggerAgent failed")
            raise
    
    def _classify_entity(self, entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify a single entity
        
        Args:
            entity: Entity dictionary
            
        Returns:
            List of Classification objects
        """
        logger.debug(f"Classifying entity: {entity.get('name')}")
        
        # Only context classifier provides entity-level classifications
        classifications = self.context_classifier.classify_entity(entity)
        
        return classifications
    
    def _classify_column(self, column: Dict[str, Any], entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify a single column using all classifiers
        
        Args:
            column: Column dictionary
            entity: Parent entity dictionary
            
        Returns:
            List of merged Classification objects
        """
        logger.debug(f"Classifying column: {entity.get('name')}.{column.get('name')}")
        
        # Run all classifiers
        classifications_by_source = {}
        
        # Semantic type classifier
        if self.config.enable_pii_classification or self.config.enable_finance_classification or \
           self.config.enable_temporal_classification:
            semantic_classifications = self.semantic_classifier.classify_column(column, entity)
            if semantic_classifications:
                classifications_by_source['semantic_type'] = semantic_classifications
        
        # Name pattern classifier
        name_classifications = self.name_classifier.classify_column(column, entity)
        if name_classifications:
            classifications_by_source['name_pattern'] = name_classifications
        
        # Statistical classifier
        if self.config.enable_data_quality_classification:
            stats_classifications = self.stats_classifier.classify_column(column, entity)
            if stats_classifications:
                classifications_by_source['statistics'] = stats_classifications
        
        # Context classifier (relationships, entity type)
        if self.config.enable_domain_classification or self.config.enable_temporal_classification:
            context_classifications = self.context_classifier.classify_column(column, entity)
            if context_classifications:
                classifications_by_source['context'] = context_classifications
        
        # Merge classifications
        merged_classifications = self.merger.merge_classifications(classifications_by_source)
        
        # Filter by minimum confidence threshold
        final_classifications = [
            c for c in merged_classifications 
            if c.confidence >= self.config.min_classification_confidence
        ]
        
        logger.debug(f"Assigned {len(final_classifications)} classifications to {column.get('name')}")
        
        return final_classifications
    
    def _classification_to_dict(self, classification: Classification) -> Dict[str, Any]:
        """
        Convert Classification object to dictionary for JSON serialization
        
        Args:
            classification: Classification object
            
        Returns:
            Dictionary representation
        """
        return {
            'tag': classification.tag,
            'confidence': round(classification.confidence, 3),
            'source': classification.source,
            'upstream_factors': classification.upstream_factors
        }

