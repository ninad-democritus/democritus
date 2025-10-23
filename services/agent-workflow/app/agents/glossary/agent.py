"""
GlossaryAgent - Main orchestrator for business glossary generation
"""
from typing import Dict, Any, List, Optional
import logging
from .models import GlossaryTerm, Glossary, GlossaryOutput, CandidateTerm
from .config import GlossaryConfig
from .term_extraction import TermExtractor
from .term_clustering import TermClusteringService
from .domain_formation import DomainFormationService
from .llm_service import LLMService
from .entity_linker import EntityLinker
from .related_terms import RelatedTermsService

# Import services from AlignerAgent for reuse
try:
    from ..aligner.embeddings import EmbeddingService
    from ..aligner.clustering import ClusteringService
except ImportError:
    EmbeddingService = None
    ClusteringService = None

try:
    from ...observability import trace_agent, observability
except ImportError:
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


class GlossaryAgent:
    """
    GlossaryAgent: Generates business glossary from enriched schema
    
    Responsibilities:
    - Extract candidate terms from entities, columns, and PK candidates
    - Cluster terms semantically
    - Form business domains from term clusters
    - Generate business-friendly definitions using LLM
    - Generate domain names and descriptions using LLM
    - Link terms to entities and columns
    - Identify related terms via relationships and semantic similarity
    - Calculate confidence scores with full upstream traceability
    - Output OpenMetadata-compatible glossary structure
    """
    
    def __init__(self, config: Optional[GlossaryConfig] = None):
        """
        Initialize GlossaryAgent with configuration
        
        Args:
            config: GlossaryConfig instance (defaults to env-based config)
        """
        self.config = config or GlossaryConfig.from_env()
        
        # Initialize extractors and services
        self.term_extractor = TermExtractor()
        
        # Initialize embedding and clustering services (reused from AlignerAgent)
        if EmbeddingService and ClusteringService:
            self.embedding_service = EmbeddingService(self.config.embedding_model)
            self.clustering_service = ClusteringService(
                self.config.clustering_method,
                self.config.min_cluster_size,
                self.config.clustering_metric
            )
        else:
            logger.warning("EmbeddingService or ClusteringService not available")
            self.embedding_service = None
            self.clustering_service = None
        
        # Initialize clustering and domain services
        self.term_clustering = TermClusteringService(
            self.config, self.embedding_service, self.clustering_service
        )
        self.domain_formation = DomainFormationService(
            self.config, self.clustering_service
        )
        
        # Initialize LLM service
        self.llm_service = LLMService(self.config)
        
        # Initialize linking and related terms services
        self.entity_linker = EntityLinker(self.config, self.embedding_service)
        self.related_terms_service = RelatedTermsService(self.config)
        
        logger.info("GlossaryAgent initialized")
    
    @trace_agent("GlossaryAgent")
    def generate_glossary(self, enriched_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate business glossary from enriched schema
        
        Args:
            enriched_schema: Complete schema from TaggerAgent (READ-ONLY)
            
        Returns:
            Dict with 'glossaries' and 'metadata_summary'
        """
        span = observability.create_agent_span("GlossaryAgent", {
            "input_entities": len(enriched_schema.get('entities', [])),
            "input_relationships": len(enriched_schema.get('relationships', []))
        })
        
        try:
            logger.info("Starting glossary generation")
            
            # Step 1: Extract candidate terms
            logger.info("Step 1: Extracting candidate terms...")
            candidate_terms = self.term_extractor.extract_terms(enriched_schema)
            logger.info(f"Extracted {len(candidate_terms)} candidate terms")
            
            if not candidate_terms:
                logger.warning("No candidate terms extracted, returning empty glossary")
                return self._empty_glossary_output()
            
            # Step 2: Cluster terms
            logger.info("Step 2: Clustering terms...")
            term_clusters = self.term_clustering.cluster_terms(candidate_terms)
            logger.info(f"Created {len(term_clusters)} term clusters")
            
            if not term_clusters:
                logger.warning("No term clusters created, returning empty glossary")
                return self._empty_glossary_output()
            
            # Step 3: Generate term definitions (LLM)
            logger.info("Step 3: Generating term definitions with LLM...")
            term_definitions = self.llm_service.generate_term_definitions(term_clusters)
            logger.info(f"Generated {len(term_definitions)} definitions")
            
            # Step 4: Form domains
            logger.info("Step 4: Forming business domains...")
            domain_clusters = self.domain_formation.form_domains(term_clusters)
            logger.info(f"Formed {len(domain_clusters)} domain clusters")
            
            # Step 5: Generate domain names (LLM)
            logger.info("Step 5: Generating domain names with LLM...")
            domain_names = self.llm_service.generate_domain_names(domain_clusters)
            logger.info(f"Generated {len(domain_names)} domain names")
            
            # Step 6: Build glossary terms
            logger.info("Step 6: Building glossary terms...")
            glossary_terms = self._build_glossary_terms(
                term_clusters, term_definitions, enriched_schema
            )
            logger.info(f"Built {len(glossary_terms)} glossary terms")
            
            # Step 7: Link terms to entities and columns
            logger.info("Step 7: Linking terms to entities and columns...")
            self.entity_linker.link_terms_to_schema(glossary_terms, enriched_schema)
            
            # Step 8: Identify related terms
            logger.info("Step 8: Identifying related terms...")
            self.related_terms_service.identify_related_terms(glossary_terms, enriched_schema)
            
            # Step 9: Build glossaries (one per domain)
            logger.info("Step 9: Building glossary objects...")
            glossaries = self._build_glossaries(
                domain_clusters, domain_names, glossary_terms, enriched_schema
            )
            logger.info(f"Built {len(glossaries)} glossary objects")
            
            # Step 10: Build metadata summary
            metadata_summary = self._build_metadata_summary(glossaries, glossary_terms)
            
            # Log completion
            logger.info(f"Glossary generation complete: {len(glossaries)} glossaries, "
                       f"{len(glossary_terms)} terms")
            
            result = {
                'glossaries': [self._glossary_to_dict(g) for g in glossaries],
                'metadata_summary': metadata_summary
            }
            
            observability.log_agent_output("GlossaryAgent", {
                "glossaries": len(glossaries),
                "total_terms": len(glossary_terms)
            }, metadata_summary)
            
            observability.end_agent_span(span, {
                "glossaries": len(glossaries),
                "total_terms": len(glossary_terms)
            })
            
            return result
            
        except Exception as e:
            observability.end_agent_span(span, {}, str(e))
            logger.exception("GlossaryAgent failed")
            raise
    
    def _build_glossary_terms(self, term_clusters, term_definitions, 
                             enriched_schema) -> List[GlossaryTerm]:
        """Build GlossaryTerm objects from clusters and definitions"""
        glossary_terms = []
        
        for cluster in term_clusters:
            rep_term = cluster.representative_term or cluster.members[0]
            
            # Get definition from LLM or fallback
            definition_info = term_definitions.get(cluster.cluster_id, {})
            definition = definition_info.get('definition', 'No definition available')
            llm_synonyms = definition_info.get('business_synonyms', [])
            definition_quality = definition_info.get('quality_score', 0.5)
            
            # Merge synonyms from multiple sources
            all_synonyms = list(set(
                rep_term.synonyms +
                llm_synonyms +
                [m.canonical_name for m in cluster.members if m != rep_term]
            ))
            
            # Calculate confidence
            confidence, confidence_breakdown = self._calculate_term_confidence(
                rep_term, cluster, definition_quality
            )
            
            # Build source file terminology map
            source_terminology = {}
            for term in cluster.members:
                for raw_name in term.raw_names:
                    # Extract file name from source if available
                    if term.source_fqn:
                        source_terminology[raw_name] = term.source_fqn
            
            # Build PK metadata if applicable
            pk_metadata = {}
            if rep_term.is_primary_key:
                pk_metadata = {
                    'confidence': rep_term.pk_confidence,
                    'explanation': rep_term.pk_explanation
                }
            
            glossary_term = GlossaryTerm(
                term_id=f"term_{cluster.cluster_id}",
                canonical_name=rep_term.canonical_name,
                display_name=rep_term.canonical_name,
                definition=definition,
                synonyms=all_synonyms[:10],  # Limit to 10
                confidence=confidence,
                confidence_breakdown=confidence_breakdown,
                
                # Will be populated by entity_linker
                associated_entities=[],
                associated_columns=[],
                
                # Will be populated by related_terms_service
                related_terms=[],
                related_via_relationships=[],
                
                # Metadata
                classifications=list(set(rep_term.classifications)),
                is_key_identifier=rep_term.is_primary_key,
                entity_type=rep_term.entity_type,
                sample_values=rep_term.sample_values[:5],
                
                # Provenance
                source_file_terminology=source_terminology,
                pk_metadata=pk_metadata
            )
            
            glossary_terms.append(glossary_term)
        
        return glossary_terms
    
    def _build_glossaries(self, domain_clusters, domain_names, 
                         glossary_terms, enriched_schema) -> List[Glossary]:
        """Build Glossary objects from domain clusters"""
        glossaries = []
        
        # Map term IDs to terms
        term_map = {term.term_id: term for term in glossary_terms}
        
        # Map cluster IDs to term IDs
        cluster_to_term = {}
        for term in glossary_terms:
            # Extract cluster ID from term_id
            cluster_id = int(term.term_id.split('_')[1])
            cluster_to_term[cluster_id] = term.term_id
        
        for domain_cluster in domain_clusters:
            # Get domain name from LLM or fallback
            domain_info = domain_names.get(domain_cluster.cluster_id, {
                'domain_name': 'Business Data',
                'description': 'General business data and information'
            })
            
            domain_name = domain_info['domain_name']
            description = domain_info['description']
            
            # Get terms in this domain
            domain_term_ids = []
            for term_cluster in domain_cluster.term_clusters:
                term_id = cluster_to_term.get(term_cluster.cluster_id)
                if term_id:
                    domain_term_ids.append(term_id)
            
            domain_terms = [term_map[tid] for tid in domain_term_ids if tid in term_map]
            
            if not domain_terms:
                logger.warning(f"Domain {domain_name} has no terms, skipping")
                continue
            
            # Calculate domain confidence (average of term confidences)
            domain_confidence = sum(t.confidence for t in domain_terms) / len(domain_terms)
            
            # Build classification summary
            classification_summary = {}
            for term in domain_terms:
                for classification in term.classifications:
                    classification_summary[classification] = \
                        classification_summary.get(classification, 0) + 1
            
            # Get source entities
            source_entities = list(set(
                assoc['id'] for term in domain_terms 
                for assoc in term.associated_entities
            ))
            
            # Create glossary ID (CamelCase, no spaces)
            glossary_id = domain_name.replace(' ', '').replace('&', 'And').replace('-', '')
            glossary_id = glossary_id[:1].lower() + glossary_id[1:]
            
            glossary = Glossary(
                glossary_id=glossary_id,
                name=''.join(word.capitalize() for word in domain_name.split()),
                display_name=domain_name,
                description=description,
                terms=domain_terms,
                confidence=domain_confidence,
                classification_summary=classification_summary,
                entity_types=domain_cluster.entity_types,
                source_entities=source_entities
            )
            
            glossaries.append(glossary)
        
        return glossaries
    
    def _calculate_term_confidence(self, term: CandidateTerm, cluster, 
                                   definition_quality: float) -> tuple:
        """
        Calculate overall confidence for a glossary term
        
        Returns:
            (confidence, confidence_breakdown) tuple
        """
        weights = self.config.confidence_weights
        
        # Clustering confidence (based on cluster variance)
        clustering_confidence = max(0.0, 1.0 - cluster.variance)
        
        # Calculate weighted confidence
        confidence = (
            term.alignment_confidence * weights['alignment_confidence'] +
            term.semantic_type_confidence * weights['semantic_type_confidence'] +
            term.classification_confidence * weights['classification_confidence'] +
            clustering_confidence * weights['clustering_confidence'] +
            definition_quality * weights['definition_quality']
        )
        
        confidence_breakdown = {
            'alignment_confidence': round(term.alignment_confidence, 3),
            'semantic_type_confidence': round(term.semantic_type_confidence, 3),
            'classification_confidence': round(term.classification_confidence, 3),
            'clustering_confidence': round(clustering_confidence, 3),
            'definition_quality': round(definition_quality, 3)
        }
        
        return round(confidence, 3), confidence_breakdown
    
    def _build_metadata_summary(self, glossaries, glossary_terms) -> Dict[str, Any]:
        """Build metadata summary for glossary output"""
        terms_with_relationships = sum(
            1 for term in glossary_terms if term.related_via_relationships
        )
        
        all_classifications = []
        for term in glossary_terms:
            all_classifications.extend(term.classifications)
        
        classification_distribution = {}
        for classification in all_classifications:
            classification_distribution[classification] = \
                classification_distribution.get(classification, 0) + 1
        
        return {
            'total_glossaries': len(glossaries),
            'total_terms': len(glossary_terms),
            'terms_with_relationships': terms_with_relationships,
            'terms_with_entities': sum(1 for t in glossary_terms if t.associated_entities),
            'terms_with_columns': sum(1 for t in glossary_terms if t.associated_columns),
            'avg_confidence': round(
                sum(t.confidence for t in glossary_terms) / len(glossary_terms), 2
            ) if glossary_terms else 0.0,
            'key_identifiers': sum(1 for t in glossary_terms if t.is_key_identifier),
            'classification_distribution': classification_distribution
        }
    
    def _glossary_to_dict(self, glossary: Glossary) -> Dict[str, Any]:
        """Convert Glossary object to dictionary"""
        return {
            'glossary_id': glossary.glossary_id,
            'name': glossary.name,
            'displayName': glossary.display_name,
            'description': glossary.description,
            'confidence': glossary.confidence,
            'terms': [self._term_to_dict(term) for term in glossary.terms],
            'metadata': {
                'classification_summary': glossary.classification_summary,
                'entity_types': glossary.entity_types,
                'source_entities': glossary.source_entities,
                'term_count': len(glossary.terms)
            }
        }
    
    def _term_to_dict(self, term: GlossaryTerm) -> Dict[str, Any]:
        """Convert GlossaryTerm object to dictionary"""
        return {
            'termId': term.term_id,
            'name': term.canonical_name,
            'displayName': term.display_name,
            'definition': term.definition,
            'synonyms': term.synonyms,
            'confidence': term.confidence,
            'confidenceBreakdown': term.confidence_breakdown,
            'associatedEntities': term.associated_entities,
            'associatedColumns': term.associated_columns,
            'relatedTerms': term.related_terms,
            'relatedViaRelationships': term.related_via_relationships,
            'classifications': term.classifications,
            'isKeyIdentifier': term.is_key_identifier,
            'entityType': term.entity_type,
            'sampleValues': term.sample_values,
            'metadata': {
                'sourceFileTerminology': term.source_file_terminology,
                'pkMetadata': term.pk_metadata if term.is_key_identifier else None
            }
        }
    
    def _empty_glossary_output(self) -> Dict[str, Any]:
        """Return empty glossary output"""
        return {
            'glossaries': [],
            'metadata_summary': {
                'total_glossaries': 0,
                'total_terms': 0,
                'terms_with_relationships': 0,
                'terms_with_entities': 0,
                'terms_with_columns': 0,
                'avg_confidence': 0.0,
                'key_identifiers': 0,
                'classification_distribution': {}
            }
        }

