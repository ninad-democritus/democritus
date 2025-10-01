from typing import Dict, List, Any
import logging
import re
import os
import json
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

# LangChain imports for LLM integration
try:
    from langchain_community.chat_models import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.pydantic_v1 import BaseModel, Field
    LLM_AVAILABLE = True
except ImportError:
    logger.warning("LangChain LLM components not available - using rule-based tagging only")
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)

# Pydantic models for LLM response parsing
if LLM_AVAILABLE:
    class LLMColumnAnalysis(BaseModel):
        """Schema for LLM column analysis"""
        column_name: str = Field(description="Name of the column")
        business_tags: List[str] = Field(description="List of business tags for this column")
        business_description: str = Field(description="Business-focused description of the column")
        business_context: str = Field(description="Business context and usage implications")
        confidence: float = Field(description="Confidence in the analysis (0-1)")

    class LLMEntityAnalysis(BaseModel):
        """Schema for LLM entity analysis"""
        entity_name: str = Field(description="Name of the entity")
        business_description: str = Field(description="Business-focused description of the entity")
        business_purpose: str = Field(description="Primary business purpose and use case")
        domain_classification: str = Field(description="Business domain (e.g., Sales, HR, Finance)")
        key_business_attributes: List[str] = Field(description="Most important business attributes")
        suggested_use_cases: List[str] = Field(description="Potential business use cases")

    class LLMBusinessIntelligenceResponse(BaseModel):
        """Complete LLM response for business intelligence"""
        entities: List[LLMEntityAnalysis] = Field(description="Business analysis of entities")
        columns: List[LLMColumnAnalysis] = Field(description="Business analysis of columns")
        overall_business_summary: str = Field(description="High-level business context summary")

class TaggerAgent:
    """
    Tagger Agent: Enriches the schema with business context,
    generating user-friendly descriptions for tables and columns.
    """
    
    def __init__(self):
        # Business tag categories and their indicators
        self.tag_patterns = {
            'PII': {
                'patterns': ['email', 'phone', 'ssn', 'social_security', 'passport', 'license', 'address', 'name', 'first_name', 'last_name'],
                'description': 'Personally Identifiable Information'
            },
            'Financial': {
                'patterns': ['amount', 'price', 'cost', 'revenue', 'profit', 'salary', 'wage', 'payment', 'balance', 'credit', 'debit'],
                'description': 'Financial or monetary data'
            },
            'Temporal': {
                'patterns': ['date', 'time', 'created', 'updated', 'modified', 'timestamp', 'year', 'month', 'day'],
                'description': 'Date and time related data'
            },
            'Contact': {
                'patterns': ['email', 'phone', 'mobile', 'telephone', 'fax', 'contact', 'address', 'zip', 'postal'],
                'description': 'Contact information'
            },
            'Identifier': {
                'patterns': ['id', 'key', 'code', 'number', 'reference', 'uuid', 'guid'],
                'description': 'Unique identifiers and keys'
            },
            'Location': {
                'patterns': ['address', 'city', 'state', 'country', 'zip', 'postal', 'region', 'location', 'latitude', 'longitude'],
                'description': 'Geographic or location data'
            },
            'Measurement': {
                'patterns': ['quantity', 'count', 'total', 'sum', 'average', 'min', 'max', 'length', 'width', 'height', 'weight'],
                'description': 'Measurements and quantities'
            },
            'Status': {
                'patterns': ['status', 'state', 'active', 'inactive', 'enabled', 'disabled', 'valid', 'flag'],
                'description': 'Status and state indicators'
            },
            'Audit': {
                'patterns': ['created_by', 'updated_by', 'modified_by', 'created_at', 'updated_at', 'modified_at', 'version'],
                'description': 'Audit trail information'
            },
            'Categorical': {
                'patterns': ['category', 'type', 'class', 'group', 'classification', 'genre', 'kind'],
                'description': 'Categorical or classification data'
            }
        }
        
        # Common business descriptions for entity types
        self.entity_descriptions = {
            'customer': 'Represents customers or clients of the business',
            'order': 'Represents sales orders or purchase transactions',
            'product': 'Represents products or items in the catalog',
            'invoice': 'Represents billing documents and payment records',
            'employee': 'Represents staff members and personnel',
            'vendor': 'Represents suppliers and business partners',
            'location': 'Represents physical locations and addresses',
            'category': 'Represents classification and grouping data',
            'event': 'Represents events, activities, or log entries'
        }
        
        # Initialize LLM for enhanced business intelligence
        self.llm = None
        self.llm_enabled = False
        if LLM_AVAILABLE:
            try:
                ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
                self.llm = ChatOllama(
                    model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                    base_url=ollama_host,
                    temperature=0.2,  # Slightly higher for creative business descriptions
                    num_predict=1500   # Allow longer responses for detailed analysis
                )
                self.llm_enabled = True
                logger.info(f"LLM initialized for business intelligence: {ollama_host}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM for tagger: {e}")
                self.llm_enabled = False
    
    @trace_agent("TaggerAgent")
    def enrich_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the schema with business tags and descriptions"""
        span = observability.create_agent_span("TaggerAgent", {
            "input_entities": len(schema.get('entities', [])),
            "input_relationships": len(schema.get('relationships', []))
        })
        
        enriched_schema = schema.copy()
        
        try:
            # Phase 1: Rule-based business tagging
            logger.info("Running rule-based business tagging...")
            business_tags = {}
            total_columns = 0
            tagged_columns = 0
            tag_distribution = {}
            
            for entity in enriched_schema['entities']:
                # Add basic entity description
                entity['description'] = self._generate_entity_description(entity)
                
                # Process each column
                for i, column_detail in enumerate(entity.get('column_details', [])):
                    total_columns += 1
                    column_name = column_detail['name']
                    full_column_name = f"{entity['name']}.{column_name}"
                    
                    # Generate column tags
                    tags = self._generate_column_tags(column_name, column_detail)
                    if tags:
                        business_tags[full_column_name] = tags
                        tagged_columns += 1
                        
                        # Track tag distribution
                        for tag in tags:
                            tag_distribution[tag] = tag_distribution.get(tag, 0) + 1
                    
                    # Add column description
                    column_detail['description'] = self._generate_column_description(
                        column_name, column_detail, tags
                    )
                    
                    # Add business context
                    column_detail['business_context'] = self._generate_business_context(
                        column_name, column_detail, entity['name']
                    )
            
            # Phase 2: LLM-powered business intelligence enhancement
            if self.llm_enabled:
                logger.info("Running LLM-powered business intelligence analysis...")
                try:
                    llm_analysis = self._analyze_business_intelligence_with_llm(enriched_schema)
                    self._merge_llm_analysis(enriched_schema, business_tags, llm_analysis)
                    logger.info("LLM business intelligence analysis completed")
                except Exception as e:
                    logger.warning(f"LLM business intelligence failed: {e}")
            
            # Add business tags to the schema
            enriched_schema['businessTags'] = business_tags
            
            # Add relationship descriptions
            for relationship in enriched_schema.get('relationships', []):
                relationship['description'] = self._generate_relationship_description(relationship)
            
            # Log tagging results
            tagging_metrics = {
                "total_columns": total_columns,
                "tagged_columns": tagged_columns,
                "tagging_coverage": (tagged_columns / total_columns * 100) if total_columns > 0 else 0,
                "unique_tags": len(tag_distribution),
                "tag_distribution": tag_distribution,
                "entities_enriched": len(enriched_schema['entities']),
                "relationships_described": len(enriched_schema.get('relationships', []))
            }
            
            observability.log_agent_output("TaggerAgent", {
                "business_tags_count": len(business_tags),
                "tag_summary": tag_distribution
            }, tagging_metrics)
            
            observability.end_agent_span(span, {
                "enriched_schema_size": len(enriched_schema),
                "metrics": tagging_metrics
            })
            
            return enriched_schema
            
        except Exception as e:
            observability.end_agent_span(span, {}, str(e))
            raise
    
    def _generate_entity_description(self, entity: Dict[str, Any]) -> str:
        """Generate a business description for an entity"""
        entity_name = entity['name'].lower()
        entity_type = entity.get('entity_type', 'dimension')
        
        # Check for known entity types
        for known_type, description in self.entity_descriptions.items():
            if known_type in entity_name:
                return description
        
        # Generate based on entity type
        if entity_type == 'fact':
            return f"Fact table containing transactional data related to {entity['name']}"
        else:
            return f"Dimension table containing descriptive information about {entity['name']}"
    
    def _generate_column_tags(self, column_name: str, column_detail: Dict[str, Any]) -> List[str]:
        """Generate business tags for a column"""
        tags = []
        column_name_lower = column_name.lower()
        data_type = column_detail.get('data_type', '').lower()
        
        # Check each tag category
        for tag_name, tag_info in self.tag_patterns.items():
            for pattern in tag_info['patterns']:
                if pattern in column_name_lower:
                    tags.append(tag_name)
                    break
        
        # Additional logic based on data type
        if data_type in ['timestamp', 'datetime', 'date']:
            if 'Temporal' not in tags:
                tags.append('Temporal')
        
        if column_detail.get('primary_key', False):
            if 'Identifier' not in tags:
                tags.append('Identifier')
        
        # Check for unique constraints (potential identifiers)
        if column_detail.get('unique', False) and 'Identifier' not in tags:
            tags.append('Identifier')
        
        return list(set(tags))  # Remove duplicates
    
    def _generate_column_description(self, column_name: str, column_detail: Dict[str, Any], 
                                   tags: List[str]) -> str:
        """Generate a business description for a column"""
        data_type = column_detail.get('data_type', 'VARCHAR')
        is_primary_key = column_detail.get('primary_key', False)
        is_nullable = column_detail.get('nullable', True)
        
        # Start with basic description
        description_parts = []
        
        if is_primary_key:
            description_parts.append("Primary key identifier")
        elif 'Identifier' in tags:
            description_parts.append("Unique identifier")
        else:
            # Generate based on column name patterns
            description_parts.append(self._infer_column_purpose(column_name, tags))
        
        # Add data type information
        if data_type in ['TIMESTAMP', 'DATETIME']:
            description_parts.append("(timestamp)")
        elif data_type.startswith('VARCHAR'):
            description_parts.append("(text)")
        elif data_type in ['INTEGER', 'DECIMAL']:
            description_parts.append("(numeric)")
        
        # Add nullability information
        if not is_nullable:
            description_parts.append("- Required field")
        
        return " ".join(description_parts)
    
    def _infer_column_purpose(self, column_name: str, tags: List[str]) -> str:
        """Infer the business purpose of a column from its name"""
        column_name_lower = column_name.lower()
        
        # Common patterns
        if 'email' in column_name_lower:
            return "Email address"
        elif 'phone' in column_name_lower:
            return "Phone number"
        elif 'name' in column_name_lower:
            return "Name identifier"
        elif 'address' in column_name_lower:
            return "Address information"
        elif 'amount' in column_name_lower or 'price' in column_name_lower:
            return "Monetary amount"
        elif 'date' in column_name_lower:
            return "Date value"
        elif 'status' in column_name_lower:
            return "Status indicator"
        elif 'count' in column_name_lower or 'quantity' in column_name_lower:
            return "Quantity measurement"
        elif column_name_lower.endswith('_id'):
            return f"Reference to {column_name_lower.replace('_id', '').replace('_', ' ')}"
        
        # Use tags to infer purpose
        if 'PII' in tags:
            return "Personal information"
        elif 'Financial' in tags:
            return "Financial data"
        elif 'Contact' in tags:
            return "Contact information"
        elif 'Location' in tags:
            return "Location data"
        
        # Default description
        return f"Data field for {column_name.replace('_', ' ').lower()}"
    
    def _generate_business_context(self, column_name: str, column_detail: Dict[str, Any], 
                                 entity_name: str) -> str:
        """Generate business context for a column"""
        stats = column_detail.get('statistics', {})
        null_percentage = stats.get('null_percentage', 0)
        distinct_count = stats.get('distinct_count', 0)
        
        context_parts = []
        
        # Data quality insights
        if null_percentage > 50:
            context_parts.append("High null rate - may indicate optional or incomplete data")
        elif null_percentage == 0:
            context_parts.append("Complete data - no missing values")
        
        # Cardinality insights
        if distinct_count == 1:
            context_parts.append("Single value across all records")
        elif distinct_count < 10:
            context_parts.append("Limited set of values - likely categorical")
        
        # Business usage suggestions
        if 'id' in column_name.lower():
            context_parts.append("Can be used for joining with related tables")
        
        return ". ".join(context_parts) if context_parts else "Standard data field"
    
    def _generate_relationship_description(self, relationship: Dict[str, Any]) -> str:
        """Generate a description for a relationship"""
        from_entity = relationship['from']
        to_entity = relationship['to']
        rel_type = relationship['type']
        foreign_key = relationship['foreign_key']
        
        if rel_type == 'many_to_one':
            return f"Each {from_entity} belongs to one {to_entity} (via {foreign_key})"
        elif rel_type == 'one_to_many':
            return f"Each {to_entity} can have multiple {from_entity} records"
        elif rel_type == 'one_to_one':
            return f"One-to-one relationship between {from_entity} and {to_entity}"
        else:
            return f"Relationship between {from_entity} and {to_entity}"
    
    def _analyze_business_intelligence_with_llm(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to analyze business intelligence and generate enhanced tags and descriptions"""
        if not self.llm_enabled:
            return {}
        
        # Prepare schema information for LLM analysis
        entities_info = []
        for entity in schema.get('entities', []):
            entity_data = {
                "entity_name": entity['name'],
                "entity_type": entity.get('entity_type', 'dimension'),
                "table_name": entity.get('table_name', entity['name']),
                "current_description": entity.get('description', ''),
                "columns": []
            }
            
            for col in entity.get('column_details', []):
                column_data = {
                    "name": col['name'],
                    "data_type": col['data_type'],
                    "is_primary_key": col.get('primary_key', False),
                    "is_unique": col.get('unique', False),
                    "nullable": col.get('nullable', True),
                    "sample_values": col.get('statistics', {}).get('sample_values', [])[:3],
                    "distinct_count": col.get('statistics', {}).get('distinct_count', 0),
                    "null_percentage": col.get('statistics', {}).get('null_percentage', 0),
                    "current_description": col.get('description', '')
                }
                entity_data["columns"].append(column_data)
            
            entities_info.append(entity_data)
        
        # Create the LLM prompt for business intelligence
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a business intelligence expert and data analyst. Analyze the provided database schema and generate comprehensive business insights.

Your task is to:
1. **Business Tag Analysis**: For each column, identify relevant business tags beyond basic patterns. Consider:
   - Industry-specific tags (Healthcare, Finance, Retail, etc.)
   - Data governance tags (Sensitive, Public, Internal, etc.)
   - Business process tags (Operational, Analytical, Compliance, etc.)
   - Data quality tags (Master Data, Reference Data, Transactional, etc.)

2. **Entity Business Analysis**: For each entity, provide:
   - Rich business description explaining the real-world purpose
   - Primary business purpose and use cases
   - Business domain classification
   - Key business attributes that drive value
   - Suggested business use cases and analytics opportunities

3. **Column Business Intelligence**: For each column, provide:
   - Business-focused description (not just technical)
   - Business context and implications
   - How this data supports business decisions
   - Data quality and governance considerations

Consider the actual data characteristics (sample values, null rates, cardinality) to inform your business analysis.

Return your analysis as JSON matching this exact schema:
{
  "entities": [
    {
      "entity_name": "entity name",
      "business_description": "Rich business description of the entity",
      "business_purpose": "Primary business purpose",
      "domain_classification": "Business domain (Sales, HR, Finance, Operations, etc.)",
      "key_business_attributes": ["list", "of", "key", "attributes"],
      "suggested_use_cases": ["list", "of", "business", "use", "cases"]
    }
  ],
  "columns": [
    {
      "column_name": "entity.column format",
      "business_tags": ["tag1", "tag2", "tag3"],
      "business_description": "Business-focused description",
      "business_context": "How this supports business decisions",
      "confidence": 0.8
    }
  ],
  "overall_business_summary": "High-level summary of the business context"
}"""),
            ("human", "Analyze this database schema for business intelligence:\n\n{schema_json}")
        ])
        
        # Set up JSON output parser
        parser = JsonOutputParser(pydantic_object=LLMBusinessIntelligenceResponse)
        
        # Create the chain
        chain = prompt | self.llm | parser
        
        try:
            # Invoke LLM
            schema_json = json.dumps(entities_info, indent=2)
            result = chain.invoke({"schema_json": schema_json})
            
            logger.info(f"LLM business analysis summary: {result.get('overall_business_summary', 'No summary provided')}")
            return result
            
        except Exception as e:
            logger.error(f"LLM business intelligence analysis failed: {e}")
            return {}
    
    def _merge_llm_analysis(self, schema: Dict[str, Any], business_tags: Dict[str, List[str]], 
                           llm_analysis: Dict[str, Any]) -> None:
        """Merge LLM analysis results into the schema"""
        if not llm_analysis:
            return
        
        # Create lookup dictionaries
        llm_entities = {entity['entity_name']: entity for entity in llm_analysis.get('entities', [])}
        llm_columns = {col['column_name']: col for col in llm_analysis.get('columns', [])}
        
        # Enhance entities with LLM analysis
        for entity in schema.get('entities', []):
            entity_name = entity['name']
            if entity_name in llm_entities:
                llm_entity = llm_entities[entity_name]
                
                # Enhance entity with LLM insights
                entity['business_description'] = llm_entity.get('business_description', entity.get('description', ''))
                entity['business_purpose'] = llm_entity.get('business_purpose', '')
                entity['domain_classification'] = llm_entity.get('domain_classification', '')
                entity['key_business_attributes'] = llm_entity.get('key_business_attributes', [])
                entity['suggested_use_cases'] = llm_entity.get('suggested_use_cases', [])
                
                # Update description with business description
                entity['description'] = entity['business_description']
            
            # Enhance columns with LLM analysis
            for column_detail in entity.get('column_details', []):
                column_name = column_detail['name']
                full_column_name = f"{entity_name}.{column_name}"
                
                if full_column_name in llm_columns:
                    llm_col = llm_columns[full_column_name]
                    
                    # Enhance business tags with LLM suggestions
                    llm_tags = llm_col.get('business_tags', [])
                    if llm_tags:
                        existing_tags = business_tags.get(full_column_name, [])
                        # Merge tags, keeping unique ones
                        combined_tags = list(set(existing_tags + llm_tags))
                        business_tags[full_column_name] = combined_tags
                    
                    # Enhance column descriptions and context
                    if llm_col.get('business_description'):
                        column_detail['description'] = llm_col['business_description']
                    
                    if llm_col.get('business_context'):
                        column_detail['business_context'] = llm_col['business_context']
                    
                    # Add LLM confidence score
                    column_detail['llm_confidence'] = llm_col.get('confidence', 0.5)
        
        # Add overall business summary to schema
        if llm_analysis.get('overall_business_summary'):
            schema['business_summary'] = llm_analysis['overall_business_summary']
