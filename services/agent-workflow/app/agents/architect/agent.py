"""
ArchitectAgent - Main orchestrator with backward compatibility
Enhanced with OpenMetadata types, semantic validation, and modular architecture
"""
from typing import List, Dict, Any, Optional
import logging
from .models import SchemaEntity, Relationship, RelationshipCandidate, SchemaGraph
from .config import ArchitectConfig
from .schema import SchemaEntityBuilder
from .relationships.rule_based import ForeignKeyMatcher, CommonColumnMatcher
from .relationships.statistical import CardinalityAnalyzer
from .relationships.merger import RelationshipMerger
from .confidence import ConfidenceScorer
from .semantics import SemanticNarrativeGenerator

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


class ArchitectAgent:
    """
    Architect Agent - Schema intelligence layer
    
    Features:
    - Builds schema entities from CanonicalEntity (AlignerAgent output)
    - Maps to OpenMetadata-compatible data types
    - Detects relationships (rule-based + statistical + semantic validation)
    - Infers cardinality with confidence scoring
    - Generates semantic narratives for relationships
    - Backward compatible output for TaggerAgent
    """
    
    def __init__(self, config: Optional[ArchitectConfig] = None):
        """
        Initialize ArchitectAgent
        
        Args:
            config: ArchitectConfig instance (defaults to env-based config)
        """
        self.config = config or ArchitectConfig.from_env()
        
        # Schema building
        self.entity_builder = SchemaEntityBuilder(self.config)
        
        # Relationship detection
        self.fk_matcher = ForeignKeyMatcher(self.config)
        self.common_matcher = CommonColumnMatcher(self.config)
        
        # Statistical analysis
        self.cardinality_analyzer = CardinalityAnalyzer(self.config)
        
        # Confidence & semantics
        self.confidence_scorer = ConfidenceScorer(self.config)
        self.semantic_generator = SemanticNarrativeGenerator(self.config)
        
        # Merging
        self.merger = RelationshipMerger(self.config.min_confidence)
        
        logger.info("ArchitectAgent initialized (modular version)")
    
    @trace_agent("ArchitectAgent")
    def design_schema(self, entities: List) -> Dict[str, Any]:
        """
        MAIN ENTRY POINT - Backward compatible
        
        Args:
            entities: List[CanonicalEntity] from AlignerAgent
            
        Returns:
            Dict with 'entities' and 'relationships' for TaggerAgent
        """
        span = observability.create_agent_span("ArchitectAgent", {
            "input_entities": [e.canonical_name for e in entities],
            "total_entities": len(entities)
        })
        
        try:
            logger.info(f"Designing schema for {len(entities)} canonical entities")
            
            # Phase 1: Build schema entities with OpenMetadata types
            logger.info("Phase 1: Building schema entities...")
            schema_entities = self.entity_builder.build_schema_entities(entities)
            logger.info(f"Built {len(schema_entities)} schema entities")
            
            # Phase 2: Detect relationship candidates
            logger.info("Phase 2: Detecting relationships...")
            candidates = []
            
            # 2a. Rule-based FK detection
            if self.config.use_rule_based:
                logger.info("Running FK pattern matching...")
                fk_candidates = self.fk_matcher.find_fk_candidates(schema_entities)
                candidates.extend(fk_candidates)
                logger.info(f"FK matcher found {len(fk_candidates)} candidates")
            
            # 2b. Common column detection
            if self.config.use_rule_based:
                logger.info("Running common column matching...")
                common_candidates = self.common_matcher.find_common_columns(schema_entities)
                candidates.extend(common_candidates)
                logger.info(f"Common matcher found {len(common_candidates)} candidates")
            
            logger.info(f"Total candidates: {len(candidates)}")
            
            # Phase 3: Analyze cardinality and calculate confidence for each candidate
            logger.info("Phase 3: Analyzing cardinality and confidence...")
            relationships = []
            
            for candidate in candidates:
                try:
                    # Determine cardinality
                    cardinality, card_confidence = self.cardinality_analyzer.infer_cardinality(candidate)
                    
                    # Calculate overall confidence
                    confidence, breakdown = self.confidence_scorer.calculate_confidence(
                        candidate, card_confidence, llm_adjustment=None
                    )
                    
                    # Create relationship ID
                    rel_id = f"{candidate.from_entity.canonical_name}_{candidate.to_entity.canonical_name}_{candidate.from_column.name}"
                    
                    # Create Relationship object
                    rel = Relationship(
                        relationship_id=rel_id,
                        from_entity=candidate.from_entity.canonical_name,
                        to_entity=candidate.to_entity.canonical_name,
                        from_column=candidate.from_column.name,
                        to_column=candidate.to_column.name,
                        cardinality=cardinality,
                        confidence=confidence,
                        confidence_breakdown=breakdown,
                        detection_method=candidate.detection_source,
                        semantic_description="",  # Will be filled in next phase
                        metadata={
                            'from_synonyms': candidate.from_entity.synonyms,
                            'to_synonyms': candidate.to_entity.synonyms
                        }
                    )
                    
                    # Generate semantic description
                    rel.semantic_description = self.semantic_generator.generate_semantic_with_columns(
                        rel,
                        candidate.from_column,
                        candidate.to_column
                    )
                    
                    relationships.append(rel)
                    
                except Exception as e:
                    logger.error(f"Failed to process candidate: {e}")
                    continue
            
            logger.info(f"Processed {len(relationships)} relationships")
            
            # Phase 4: Deduplicate and merge
            logger.info("Phase 4: Merging and deduplicating...")
            relationships = self.merger.merge_and_deduplicate(relationships)
            logger.info(f"Final relationship count: {len(relationships)}")
            
            # Phase 5: Build output (backward compatible format)
            logger.info("Phase 5: Building output...")
            result = {
                'entities': [self._entity_to_dict(e) for e in schema_entities],
                'relationships': [self._relationship_to_dict(r) for r in relationships],
                'metadata_summary': {
                    'relationships_detected': len(relationships),
                    'rule_based': sum(1 for r in relationships if 'fk' in r.detection_method or 'common' in r.detection_method),
                    'llm_validated': 0,  # Not yet implemented
                    'entities': len(schema_entities),
                    'avg_confidence': round(sum(r.confidence for r in relationships) / len(relationships), 2) if relationships else 0
                }
            }
            
            # Log architecture results
            arch_metrics = {
                "schema_entities_created": len(schema_entities),
                "relationships_identified": len(relationships),
                "relationship_types": [rel.cardinality for rel in relationships],
                "entities_with_relationships": len(set([rel.from_entity for rel in relationships] + [rel.to_entity for rel in relationships])),
                "avg_confidence": result['metadata_summary']['avg_confidence']
            }
            
            observability.log_agent_output("ArchitectAgent", {
                "schema_summary": {
                    "entities": len(schema_entities),
                    "relationships": len(relationships)
                }
            }, arch_metrics)
            
            observability.end_agent_span(span, {
                "schema_entities": len(schema_entities),
                "relationships": len(relationships),
                "metrics": arch_metrics
            })
            
            logger.info(f"Schema design complete: {len(schema_entities)} entities, {len(relationships)} relationships")
            return result
            
        except Exception as e:
            observability.end_agent_span(span, {}, str(e))
            logger.error(f"Schema design failed: {e}")
            raise
    
    def _entity_to_dict(self, entity: SchemaEntity) -> Dict[str, Any]:
        """
        Convert SchemaEntity to dictionary format (backward compatible + enhanced)
        
        Compatible with TaggerAgent expectations while adding new fields
        """
        return {
            # Backward compatible fields
            'name': entity.canonical_name,
            'table_name': entity.table_name,
            'columns': [col.name for col in entity.columns],
            'primary_key': entity.primary_key,
            'entity_type': entity.entity_type,
            'column_details': [
                {
                    'name': col.name,
                    'displayName': col.canonical_name,
                    
                    # OpenMetadata type structure
                    'dataType': col.data_type,
                    'dataTypeDisplay': col.data_type_display,
                    'dataLength': col.data_length,
                    'precision': col.precision,
                    'scale': col.scale,
                    
                    # Additional metadata
                    'semantic_type': col.semantic_type,
                    'semantic_type_confidence': col.semantic_type_confidence,
                    'alignment_confidence': col.alignment_confidence,
                    'nullable': col.nullable,
                    'unique': col.is_unique,
                    'primary_key': col.is_primary_key,
                    
                    # Statistics
                    'statistics': {
                        'null_percentage': col.null_percentage,
                        'distinct_count': col.distinct_count,
                        'sample_values': col.sample_values[:3]
                    },
                    
                    # Enhanced fields
                    'synonyms': col.synonyms,
                    'raw_names': col.raw_names
                }
                for col in entity.columns
            ],
            
            # Enhanced fields (NEW - backward compatible additions)
            'synonyms': entity.synonyms,
            'raw_names': entity.raw_names,
            'source_files': entity.source_files,
            'alignment_confidence': entity.alignment_confidence,
            'row_count': entity.row_count
        }
    
    def _relationship_to_dict(self, relationship: Relationship) -> Dict[str, Any]:
        """
        Convert Relationship to dictionary format (backward compatible + enhanced)
        """
        return {
            # Backward compatible fields
            'from': relationship.from_entity,
            'to': relationship.to_entity,
            'type': relationship.cardinality,
            'foreign_key': relationship.from_column,
            'references': relationship.to_column,
            'confidence': round(relationship.confidence, 2),
            
            # Enhanced fields (NEW - backward compatible additions)
            'semantic': relationship.semantic_description,
            'confidence_breakdown': relationship.confidence_breakdown,
            'detection_method': relationship.detection_method,
            'from_synonyms': relationship.metadata.get('from_synonyms', []),
            'to_synonyms': relationship.metadata.get('to_synonyms', [])
        }

