"""
Narrative generator using LLM or template fallbacks
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import asdict
from ..models import EntityContext, ColumnContext, RelationshipContext, GlossaryContext
from ..config import ContextConfig
from .templates import PromptTemplates
from .confidence_mapper import ConfidenceMapper

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """Generates business narratives using LLM with template fallbacks"""
    
    def __init__(self, config: ContextConfig, llm_service=None):
        """
        Initialize narrative generator
        
        Args:
            config: ContextConfig instance
            llm_service: Optional LLM service (from glossary agent)
        """
        self.config = config
        self.llm_service = llm_service
        self.templates = PromptTemplates()
        self.confidence_mapper = ConfidenceMapper(config.confidence_thresholds)
    
    def generate_entity_description(self, context: EntityContext) -> str:
        """
        Generate entity description
        
        Args:
            context: EntityContext bundle
            
        Returns:
            Generated description
        """
        try:
            if self.config.use_llm_narratives and self.llm_service:
                # Use LLM
                context_dict = asdict(context)
                prompt = self.templates.entity_description_prompt(context_dict)
                
                response = self.llm_service.generate_text(
                    prompt,
                    max_tokens=300,
                    temperature=0.3
                )
                
                if response and len(response.strip()) > 50:
                    return response.strip()
            
            # Fallback to template
            return self._template_entity_description(context)
            
        except Exception as e:
            logger.warning(f"LLM entity description failed: {e}, using template")
            return self._template_entity_description(context)
    
    def generate_column_description(self, context: ColumnContext) -> str:
        """
        Generate column description
        
        Args:
            context: ColumnContext bundle
            
        Returns:
            Generated description
        """
        try:
            if self.config.use_llm_narratives and self.llm_service:
                # Use LLM
                context_dict = asdict(context)
                prompt = self.templates.column_description_prompt(context_dict)
                
                response = self.llm_service.generate_text(
                    prompt,
                    max_tokens=200,
                    temperature=0.3
                )
                
                if response and len(response.strip()) > 30:
                    return response.strip()
            
            # Fallback to template
            return self._template_column_description(context)
            
        except Exception as e:
            logger.warning(f"LLM column description failed: {e}, using template")
            return self._template_column_description(context)
    
    def generate_relationship_description(self, context: RelationshipContext) -> str:
        """
        Generate relationship narrative
        
        Args:
            context: RelationshipContext bundle
            
        Returns:
            Generated description
        """
        try:
            if self.config.use_llm_narratives and self.llm_service:
                # Use LLM
                context_dict = asdict(context)
                prompt = self.templates.relationship_description_prompt(context_dict)
                
                response = self.llm_service.generate_text(
                    prompt,
                    max_tokens=150,
                    temperature=0.3
                )
                
                if response and len(response.strip()) > 20:
                    return response.strip()
            
            # Fallback to template
            return self._template_relationship_description(context)
            
        except Exception as e:
            logger.warning(f"LLM relationship description failed: {e}, using template")
            return self._template_relationship_description(context)
    
    def generate_domain_description(self, context: GlossaryContext) -> str:
        """
        Generate domain/glossary description
        
        Args:
            context: GlossaryContext bundle
            
        Returns:
            Generated description
        """
        try:
            if self.config.use_llm_narratives and self.llm_service:
                # Use LLM
                context_dict = asdict(context)
                prompt = self.templates.domain_description_prompt(context_dict)
                
                response = self.llm_service.generate_text(
                    prompt,
                    max_tokens=400,
                    temperature=0.3
                )
                
                if response and len(response.strip()) > 50:
                    return response.strip()
            
            # Fallback to template
            return self._template_domain_description(context)
            
        except Exception as e:
            logger.warning(f"LLM domain description failed: {e}, using template")
            return self._template_domain_description(context)
    
    def _template_entity_description(self, context: EntityContext) -> str:
        """Template-based entity description fallback"""
        confidence_qual = self.confidence_mapper.get_qualifier(context.confidence) if context.confidence < 0.85 else ""
        
        desc_parts = []
        
        # Opening sentence
        if context.entity_type == 'fact':
            desc_parts.append(f"The {context.canonical_name} table serves as a {'potentially ' if confidence_qual else ''}fact table")
        else:
            desc_parts.append(f"The {context.canonical_name} table maintains {'potential ' if confidence_qual else ''}reference data as a dimension table")
        
        # Row count and domain
        if context.domain:
            desc_parts.append(f"in the {context.domain} domain")
        if context.row_count > 0:
            desc_parts.append(f"with {context.row_count:,} records")
        
        desc = " ".join(desc_parts) + ". "
        
        # Key columns
        key_cols = [c for c in context.columns if c['role'] == 'primary_key' or 'PII' in str(c['classifications'])]
        if key_cols:
            col_mentions = ", ".join(c['canonical_name'] for c in key_cols[:3])
            desc += f"Key fields include {col_mentions}. "
        
        # Relationships
        if context.relationships:
            rel_count = len(context.relationships)
            desc += f"The table participates in {rel_count} relationship{'s' if rel_count > 1 else ''} with other entities. "
        
        return desc.strip()
    
    def _template_column_description(self, context: ColumnContext) -> str:
        """Template-based column description fallback"""
        desc_parts = []
        
        # Primary meaning
        if context.is_primary_key:
            desc_parts.append(f"Unique identifier for each {context.entity_name} record")
        elif 'PII' in str(context.classifications):
            desc_parts.append(f"Contains personally identifiable information of type {context.semantic_type}")
        elif context.semantic_type and context.semantic_type != 'unknown':
            desc_parts.append(f"Represents {context.canonical_name.lower()} data ({context.semantic_type})")
        else:
            desc_parts.append(f"Stores {context.canonical_name.lower()} values")
        
        # Data type
        desc_parts.append(f"as {context.data_type_display}")
        
        desc = " ".join(desc_parts) + ". "
        
        # Statistics
        if context.statistics:
            stats = context.statistics
            if stats.get('distinct_count'):
                desc += f"Contains {stats['distinct_count']:,} distinct values. "
        
        # Classifications
        if context.classifications:
            class_str = ", ".join(context.classifications[:2])
            desc += f"Classified as {class_str} for governance purposes. "
        
        return desc.strip()
    
    def _template_relationship_description(self, context: RelationshipContext) -> str:
        """Template-based relationship description fallback"""
        confidence_qual = " (confirmed)" if context.confidence > 0.85 else " (likely)" if context.confidence > 0.70 else " (tentative)"
        
        # Map cardinality to readable text
        card_map = {
            'many-to-one': 'multiple records in',
            'one-to-many': 'is referenced by multiple',
            'one-to-one': 'has a one-to-one link with',
            'many-to-many': 'has a many-to-many relationship with'
        }
        
        card_text = card_map.get(context.cardinality, 'is related to')
        
        desc = f"Each {context.from_entity} record ({card_text} {context.to_entity}) through the {context.from_column} foreign key column{confidence_qual}. "
        desc += f"This relationship enables {context.from_entity.lower()}-level analysis and supports joins between the two tables."
        
        return desc.strip()
    
    def _template_domain_description(self, context: GlossaryContext) -> str:
        """Template-based domain description fallback"""
        chars = context.data_characteristics
        
        desc = f"The {context.display_name} domain encompasses data related to key business operations. "
        desc += f"This domain contains {chars['total_entities']} core entities "
        desc += f"({chars['fact_entities']} fact table{'s' if chars['fact_entities'] != 1 else ''}, "
        desc += f"{chars['dimension_entities']} dimension table{'s' if chars['dimension_entities'] != 1 else ''}) "
        desc += f"with {chars['total_rows']:,} total records. "
        
        if chars['total_relationships'] > 0:
            desc += f"These entities are connected through {chars['total_relationships']} relationships, enabling comprehensive analytics. "
        
        if context.classification_profile:
            top_class = list(context.classification_profile.keys())[0]
            desc += f"The domain includes governance classifications such as {top_class}. "
        
        return desc.strip()

