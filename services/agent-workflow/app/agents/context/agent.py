"""
ContextAgent - Main orchestrator for narrative generation
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from .models import ContextOutput
from .config import ContextConfig
from .graph.builder import SemanticGraphBuilder
from .graph.analyzer import GraphAnalyzer
from .consolidation.entity_bundle import EntityBundleBuilder
from .consolidation.column_bundle import ColumnBundleBuilder
from .consolidation.relationship_bundle import RelationshipBundleBuilder
from .consolidation.glossary_bundle import GlossaryBundleBuilder
from .narratives.generator import NarrativeGenerator
from .formatter import OutputFormatter

try:
    from ...observability import trace_agent, observability
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


class ContextAgent:
    """
    Context Agent - Generates business-readable narratives for enriched schema
    
    Responsibilities:
    - Build semantic knowledge graph from enriched schema
    - Consolidate context bundles for entities, columns, relationships, glossaries
    - Generate LLM-powered or template-based narratives
    - Format output to minimal schema for UI/data-pipeline consumption
    """
    
    def __init__(self, config: Optional[ContextConfig] = None, llm_service=None):
        """
        Initialize ContextAgent
        
        Args:
            config: ContextConfig instance (defaults to env-based config)
            llm_service: Optional LLM service for narrative generation
        """
        self.config = config or ContextConfig.from_env()
        
        # Initialize components
        self.graph_builder = SemanticGraphBuilder() if self.config.enable_semantic_graph else None
        self.narrative_generator = NarrativeGenerator(self.config, llm_service)
        self.formatter = OutputFormatter(self.config.include_confidence)
        
        logger.info("ContextAgent initialized")
    
    @trace_agent("ContextAgent")
    def generate_context(self, enriched_schema: Dict[str, Any], 
                        output_format: str = None) -> Dict[str, Any]:
        """
        MAIN ENTRY POINT - Generate context narratives and descriptions
        
        Args:
            enriched_schema: Enriched schema from GlossaryAgent
            output_format: 'minimal' or 'full' (defaults to config)
            
        Returns:
            Schema with added descriptions (format depends on output_format)
        """
        start_time = datetime.utcnow()
        output_format = output_format or self.config.output_format
        
        span = observability.create_agent_span("ContextAgent", {
            "input_entities": len(enriched_schema.get('entities', [])),
            "input_relationships": len(enriched_schema.get('relationships', [])),
            "output_format": output_format
        })
        
        try:
            logger.info(f"Starting context generation for {len(enriched_schema.get('entities', []))} entities")
            
            # Make a copy to avoid mutation
            output_schema = self._deep_copy_schema(enriched_schema)
            
            # Phase 1: Build semantic graph (if enabled)
            graph_analyzer = None
            if self.config.enable_semantic_graph and self.graph_builder:
                logger.info("Phase 1: Building semantic graph")
                graph = self.graph_builder.build_graph(enriched_schema)
                graph_analyzer = GraphAnalyzer(graph, self.config.max_relationship_hops)
            
            # Phase 2: Initialize context builders
            entity_builder = EntityBundleBuilder(graph_analyzer)
            column_builder = ColumnBundleBuilder(graph_analyzer)
            relationship_builder = RelationshipBundleBuilder()
            glossary_builder = GlossaryBundleBuilder()
            
            # Phase 3: Generate entity and column descriptions
            logger.info("Phase 2: Generating entity and column descriptions")
            entities_processed = 0
            columns_processed = 0
            
            for entity in output_schema['entities']:
                # Build entity context
                entity_context = entity_builder.build_context(entity)
                
                # Generate entity description
                entity['description'] = self.narrative_generator.generate_entity_description(entity_context)
                entities_processed += 1
                
                # Generate column descriptions
                for column in entity['column_details']:
                    column_context = column_builder.build_context(column, entity)
                    column['description'] = self.narrative_generator.generate_column_description(column_context)
                    columns_processed += 1
            
            logger.info(f"Generated descriptions for {entities_processed} entities, {columns_processed} columns")
            
            # Phase 4: Generate relationship narratives
            logger.info("Phase 3: Generating relationship narratives")
            relationships_processed = 0
            
            for relationship in output_schema['relationships']:
                rel_context = relationship_builder.build_context(
                    relationship, 
                    enriched_schema['entities']
                )
                relationship['narrative_description'] = self.narrative_generator.generate_relationship_description(rel_context)
                relationships_processed += 1
            
            logger.info(f"Generated narratives for {relationships_processed} relationships")
            
            # Phase 5: Generate glossary descriptions
            logger.info("Phase 4: Generating glossary descriptions")
            glossaries_processed = 0
            terms_enriched = 0
            
            for glossary in output_schema['glossaries']:
                # Generate domain-level description
                glossary_context = glossary_builder.build_context(
                    glossary,
                    enriched_schema['entities'],
                    enriched_schema['relationships']
                )
                glossary['description'] = self.narrative_generator.generate_domain_description(glossary_context)
                glossaries_processed += 1
                
                # Enrich term narratives (optionally, since they already have definitions)
                for term in glossary['terms']:
                    # For now, just combine definition with any related info
                    # Could use LLM to generate contextual narrative
                    context_info = f"This term is associated with {len(term.get('associated_entities', []))} entities"
                    if term.get('related_terms'):
                        context_info += f" and related to {', '.join(term['related_terms'][:3])}"
                    term['contextual_narrative'] = context_info
                    terms_enriched += 1
            
            logger.info(f"Generated descriptions for {glossaries_processed} glossaries, enriched {terms_enriched} terms")
            
            # Phase 6: Format output
            if output_format == 'minimal':
                logger.info("Phase 5: Formatting to minimal schema")
                output_schema = self.formatter.format_minimal(output_schema)
            
            # Calculate metrics
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            metrics = {
                "entities_with_descriptions": entities_processed,
                "columns_with_descriptions": columns_processed,
                "relationships_with_narratives": relationships_processed,
                "glossary_terms_enriched": terms_enriched,
                "domains_described": glossaries_processed,
                "generation_time_seconds": round(duration, 2),
                "output_format": output_format
            }
            
            # Add context summary to output
            if output_format == 'full':
                output_schema['context_summary'] = metrics
            
            logger.info(f"Context generation complete in {duration:.2f}s")
            
            observability.log_agent_output("ContextAgent", {
                "entities_processed": entities_processed,
                "columns_processed": columns_processed
            }, metrics)
            
            observability.end_agent_span(span, {"metrics": metrics})
            
            return output_schema
            
        except Exception as e:
            logger.exception("ContextAgent failed")
            observability.end_agent_span(span, {}, str(e))
            raise
    
    def _deep_copy_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Deep copy schema to avoid mutation"""
        import copy
        return copy.deepcopy(schema)

