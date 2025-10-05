from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import os
import json
from .aligner import Entity
from .profiler import ColumnProfile
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
    logger.warning("LangChain LLM components not available - using rule-based detection only")
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)

# Pydantic models for LLM response parsing
if LLM_AVAILABLE:
    class LLMRelationship(BaseModel):
        """Schema for LLM-detected relationships"""
        from_entity: str = Field(description="Source entity name")
        to_entity: str = Field(description="Target entity name")
        from_column: str = Field(description="Source column name")
        to_column: str = Field(description="Target column name")
        relationship_type: str = Field(description="Type: one_to_many, many_to_one, one_to_one, many_to_many")
        confidence: float = Field(description="Confidence score between 0 and 1")
        reasoning: str = Field(description="Explanation for why this relationship exists")

    class LLMRelationshipResponse(BaseModel):
        """Complete LLM response for relationship detection"""
        relationships: List[LLMRelationship] = Field(description="List of detected relationships")
        analysis_summary: str = Field(description="Summary of the relationship analysis")

@dataclass
class Relationship:
    from_entity: str
    to_entity: str
    from_column: str
    to_column: str
    relationship_type: str  # 'one_to_many', 'many_to_one', 'one_to_one', 'many_to_many'
    confidence: float

@dataclass
class SchemaEntity:
    name: str
    table_name: str
    columns: List[Dict[str, Any]]
    primary_key: str
    entity_type: str

class ArchitectAgent:
    """
    Architect Agent: Takes entities and defines a relational structure,
    proposing primary keys and foreign key relationships.
    """
    
    def __init__(self):
        # Common foreign key naming patterns
        self.fk_patterns = [
            '{entity_name}_id',
            '{entity_name}id', 
            '{entity_name}_key',
            '{entity_name}key',
            '{entity_name}_code',
            '{entity_name}code'
        ]
        
        # Initialize LLM for relationship detection
        self.llm = None
        self.llm_enabled = False
        if LLM_AVAILABLE:
            try:
                ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
                self.llm = ChatOllama(
                    model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                    base_url=ollama_host,
                    temperature=0.1,  # Low temperature for consistent analysis
                    num_predict=1000   # Limit response length
                )
                self.llm_enabled = True
                logger.info(f"LLM initialized for relationship detection: {ollama_host}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
                self.llm_enabled = False
        
    @trace_agent("ArchitectAgent")
    def design_schema(self, entities: List[Entity]) -> Dict[str, Any]:
        """Design a relational schema from identified entities"""
        span = observability.create_agent_span("ArchitectAgent", {
            "input_entities": [e.name for e in entities],
            "total_entities": len(entities)
        })
        
        schema_entities = []
        relationships = []
        
        try:
            # First pass: create schema entities with primary keys
            for entity in entities:
                schema_entity = self._create_schema_entity(entity)
                schema_entities.append(schema_entity)
            
            # Second pass: identify relationships between entities
            relationships = self._identify_relationships(schema_entities, entities)
            
            # Log architecture results
            arch_metrics = {
                "schema_entities_created": len(schema_entities),
                "relationships_identified": len(relationships),
                "relationship_types": [rel.relationship_type for rel in relationships],
                "entities_with_relationships": len(set([rel.from_entity for rel in relationships] + [rel.to_entity for rel in relationships]))
            }
            
            schema_result = {
                'entities': [self._entity_to_dict(entity) for entity in schema_entities],
                'relationships': [self._relationship_to_dict(rel) for rel in relationships]
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
            
            return schema_result
            
        except Exception as e:
            observability.end_agent_span(span, {}, str(e))
            raise
    
    def _create_schema_entity(self, entity: Entity) -> SchemaEntity:
        """Create a schema entity with proper column definitions"""
        # Determine primary key
        primary_key = self._select_primary_key(entity)
        
        # Create table name (clean version of entity name)
        table_name = self._create_table_name(entity.name)
        
        # Convert columns to schema format
        schema_columns = []
        for col in entity.columns:
            schema_columns.append({
                'name': col.name,
                'data_type': self._map_data_type(col.data_type),
                'nullable': col.null_count > 0,
                'unique': col.distinct_count == col.total_count and col.null_count == 0,
                'primary_key': col.name == primary_key,
                'source_column': col.name,
                'statistics': {
                    'null_percentage': col.null_percentage,
                    'distinct_count': col.distinct_count,
                    'sample_values': col.sample_values[:3]  # Limit sample values
                }
            })
        
        return SchemaEntity(
            name=entity.name,
            table_name=table_name,
            columns=schema_columns,
            primary_key=primary_key,
            entity_type=entity.entity_type
        )
    
    def _select_primary_key(self, entity: Entity) -> str:
        """Select the best primary key for the entity"""
        if entity.primary_key_candidates:
            # Prefer exact 'id' match
            for candidate in entity.primary_key_candidates:
                if candidate.lower() == 'id':
                    return candidate
            
            # Return the first candidate
            return entity.primary_key_candidates[0]
        
        # If no clear primary key, suggest creating one
        return 'id'  # Will be flagged as needing generation
    
    def _create_table_name(self, entity_name: str) -> str:
        """Create a clean table name from entity name"""
        # Convert to lowercase and replace spaces with underscores
        table_name = entity_name.lower().replace(' ', '_')
        
        # Remove special characters
        import re
        table_name = re.sub(r'[^a-z0-9_]', '', table_name)
        
        # Ensure it starts with a letter
        if table_name and not table_name[0].isalpha():
            table_name = 'tbl_' + table_name
        
        return table_name or 'unknown_entity'
    
    def _map_data_type(self, inferred_type: str) -> str:
        """Map inferred data types to SQL data types"""
        type_mapping = {
            'integer': 'INTEGER',
            'float': 'DECIMAL',
            'string': 'VARCHAR(255)',
            'datetime': 'TIMESTAMP',
            'boolean': 'BOOLEAN',
            'identifier': 'VARCHAR(50)',
            'unknown': 'VARCHAR(255)'
        }
        return type_mapping.get(inferred_type, 'VARCHAR(255)')
    
    def _identify_relationships(self, schema_entities: List[SchemaEntity], 
                              original_entities: List[Entity]) -> List[Relationship]:
        """Identify relationships between entities using both rule-based and LLM approaches"""
        relationships = []
        
        # Method 1: Rule-based relationship detection
        logger.info("Running rule-based relationship detection...")
        for i, entity1 in enumerate(schema_entities):
            for j, entity2 in enumerate(schema_entities):
                if i != j:  # Don't compare entity to itself
                    rels = self._find_relationships_between_entities(entity1, entity2)
                    relationships.extend(rels)
        
        rule_based_count = len(relationships)
        logger.info(f"Rule-based detection found {rule_based_count} potential relationships")
        
        # Method 2: LLM-powered relationship detection
        if self.llm_enabled and len(schema_entities) > 1:
            logger.info("Running LLM-powered relationship detection...")
            try:
                llm_relationships = self._detect_relationships_with_llm(schema_entities)
                relationships.extend(llm_relationships)
                logger.info(f"LLM detection found {len(llm_relationships)} additional relationships")
            except Exception as e:
                logger.warning(f"LLM relationship detection failed: {e}")
        
        # Remove duplicates and low-confidence relationships
        relationships = self._deduplicate_relationships(relationships)
        final_relationships = [rel for rel in relationships if rel.confidence > 0.3]  # Lower threshold to include LLM suggestions
        
        logger.info(f"Final relationship count: {len(final_relationships)} (after deduplication and filtering)")
        return final_relationships
    
    def _find_relationships_between_entities(self, entity1: SchemaEntity, 
                                           entity2: SchemaEntity) -> List[Relationship]:
        """Find relationships between two specific entities"""
        relationships = []
        
        # Method 1: Look for traditional foreign key patterns
        entity1_name_variations = self._get_entity_name_variations(entity1.name)
        entity2_name_variations = self._get_entity_name_variations(entity2.name)
        
        # Check if entity1 has foreign keys pointing to entity2
        for col1 in entity1.columns:
            col1_name_lower = col1['name'].lower()
            
            for variation in entity2_name_variations:
                for pattern in self.fk_patterns:
                    expected_fk = pattern.format(entity_name=variation)
                    if col1_name_lower == expected_fk.lower() or variation in col1_name_lower:
                        # Found potential foreign key
                        confidence = self._calculate_relationship_confidence(
                            col1, entity1, entity2
                        )
                        
                        if confidence > 0:
                            relationships.append(Relationship(
                                from_entity=entity1.name,
                                to_entity=entity2.name,
                                from_column=col1['name'],
                                to_column=entity2.primary_key,
                                relationship_type='many_to_one',
                                confidence=confidence
                            ))
        
        # Method 2: Look for common column names (natural join keys)
        common_column_relationships = self._find_common_column_relationships(entity1, entity2)
        relationships.extend(common_column_relationships)
        
        return relationships
    
    def _get_entity_name_variations(self, entity_name: str) -> List[str]:
        """Get different variations of an entity name for matching"""
        base_name = entity_name.lower()
        variations = [base_name]
        
        # Remove common suffixes
        if base_name.endswith('s'):
            variations.append(base_name[:-1])  # Remove plural
        
        # Add with underscores
        variations.append(base_name.replace(' ', '_'))
        
        # Add shortened versions
        if len(base_name) > 4:
            variations.append(base_name[:4])
        
        return list(set(variations))
    
    def _find_common_column_relationships(self, entity1: SchemaEntity, 
                                        entity2: SchemaEntity) -> List[Relationship]:
        """Find relationships based on common column names (natural join keys)"""
        relationships = []
        
        # Get column names from both entities
        entity1_columns = {col['name'].lower(): col for col in entity1.columns}
        entity2_columns = {col['name'].lower(): col for col in entity2.columns}
        
        # Find columns with identical names
        common_columns = set(entity1_columns.keys()) & set(entity2_columns.keys())
        
        for common_col_name in common_columns:
            col1 = entity1_columns[common_col_name]
            col2 = entity2_columns[common_col_name]
            
            # Skip if it's a primary key in both entities (likely same entity split)
            if col1.get('primary_key', False) and col2.get('primary_key', False):
                continue
            
            # Calculate confidence for this common column relationship
            confidence = self._calculate_common_column_confidence(col1, col2, entity1, entity2)
            
            if confidence > 0.3:  # Lower threshold for common columns
                # Determine relationship direction and type
                rel_type = self._determine_relationship_type(col1, col2, entity1, entity2)
                
                relationships.append(Relationship(
                    from_entity=entity1.name,
                    to_entity=entity2.name,
                    from_column=col1['name'],
                    to_column=col2['name'],
                    relationship_type=rel_type,
                    confidence=confidence
                ))
        
        return relationships
    
    def _calculate_common_column_confidence(self, col1: Dict[str, Any], col2: Dict[str, Any],
                                          entity1: SchemaEntity, entity2: SchemaEntity) -> float:
        """Calculate confidence for relationships based on common column names"""
        confidence = 0.0
        
        # Base confidence for having the same name
        confidence += 0.4
        
        # Higher confidence if data types match
        if col1['data_type'] == col2['data_type']:
            confidence += 0.3
        
        # Higher confidence if it looks like an identifier
        col_name_lower = col1['name'].lower()
        if any(pattern in col_name_lower for pattern in ['id', 'key', 'code', 'num', 'ref']):
            confidence += 0.2
        
        # Higher confidence if one column has higher uniqueness (likely a lookup key)
        col1_stats = col1.get('statistics', {})
        col2_stats = col2.get('statistics', {})
        
        col1_distinct = col1_stats.get('distinct_count', 0)
        col2_distinct = col2_stats.get('distinct_count', 0)
        
        if col1_distinct > 0 and col2_distinct > 0:
            # If one has significantly more distinct values, it's likely a lookup relationship
            ratio = max(col1_distinct, col2_distinct) / min(col1_distinct, col2_distinct)
            if ratio > 2:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _determine_relationship_type(self, col1: Dict[str, Any], col2: Dict[str, Any],
                                   entity1: SchemaEntity, entity2: SchemaEntity) -> str:
        """Determine the type of relationship based on column characteristics"""
        col1_stats = col1.get('statistics', {})
        col2_stats = col2.get('statistics', {})
        
        col1_distinct = col1_stats.get('distinct_count', 0)
        col2_distinct = col2_stats.get('distinct_count', 0)
        
        # If one entity has significantly fewer distinct values, it's likely the "one" side
        if col1_distinct > 0 and col2_distinct > 0:
            ratio = col1_distinct / col2_distinct
            if ratio > 2:
                return 'many_to_one'  # entity1 has many, entity2 has one
            elif ratio < 0.5:
                return 'one_to_many'  # entity1 has one, entity2 has many
        
        # Check if either is marked as unique
        if col1.get('unique', False) and not col2.get('unique', False):
            return 'one_to_many'
        elif col2.get('unique', False) and not col1.get('unique', False):
            return 'many_to_one'
        
        # Default to many-to-many for common attributes
        return 'many_to_many'
    
    def _detect_relationships_with_llm(self, schema_entities: List[SchemaEntity]) -> List[Relationship]:
        """Use LLM to detect relationships between entities based on schema analysis"""
        if not self.llm_enabled:
            return []
        
        # Prepare entity information for LLM analysis
        entities_info = []
        for entity in schema_entities:
            entity_data = {
                "name": entity.name,
                "entity_type": entity.entity_type,
                "columns": [
                    {
                        "name": col["name"],
                        "data_type": col["data_type"],
                        "is_primary_key": col.get("primary_key", False),
                        "is_unique": col.get("unique", False),
                        "nullable": col.get("nullable", True),
                        "sample_values": col.get("statistics", {}).get("sample_values", [])[:3],
                        "distinct_count": col.get("statistics", {}).get("distinct_count", 0)
                    }
                    for col in entity.columns
                ]
            }
            entities_info.append(entity_data)
        
        # Create the LLM prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a database schema architect expert. Analyze the provided entities and identify relationships between them.

Look for:
1. Identical column names across tables (natural join keys like 'NOC', 'customer_id', etc.)
2. Columns that semantically relate to other entities (e.g., 'department_code' relating to a 'Department' entity)
3. Foreign key patterns (columns ending in _id, _key, _code that might reference other tables)
4. Business logic relationships (e.g., Orders relate to Customers, Products relate to Categories)

Consider data characteristics:
- Column uniqueness and cardinality to determine relationship type
- Sample values to understand the data domain
- Entity types (fact vs dimension tables)

Return your analysis as JSON matching this exact schema:
{
  "relationships": [
    {
      "from_entity": "source entity name",
      "to_entity": "target entity name", 
      "from_column": "source column name",
      "to_column": "target column name",
      "relationship_type": "one_to_many|many_to_one|one_to_one|many_to_many",
      "confidence": 0.8,
      "reasoning": "Explanation of why this relationship exists"
    }
  ],
  "analysis_summary": "Overall summary of relationship analysis"
}"""),
            ("human", "Analyze these entities for relationships:\n\n{entities_json}")
        ])
        
        # Set up JSON output parser
        parser = JsonOutputParser(pydantic_object=LLMRelationshipResponse)
        
        # Create the chain
        chain = prompt | self.llm | parser
        
        try:
            # Invoke LLM
            entities_json = json.dumps(entities_info, indent=2)
            result = chain.invoke({"entities_json": entities_json})
            
            # Convert LLM response to Relationship objects
            relationships = []
            for llm_rel in result.get("relationships", []):
                # Validate the relationship makes sense
                if self._validate_llm_relationship(llm_rel, schema_entities):
                    relationships.append(Relationship(
                        from_entity=llm_rel["from_entity"],
                        to_entity=llm_rel["to_entity"],
                        from_column=llm_rel["from_column"],
                        to_column=llm_rel["to_column"],
                        relationship_type=llm_rel["relationship_type"],
                        confidence=max(0.4, float(llm_rel["confidence"]))  # Ensure minimum confidence for LLM suggestions
                    ))
            
            logger.info(f"LLM analysis summary: {result.get('analysis_summary', 'No summary provided')}")
            return relationships
            
        except Exception as e:
            logger.error(f"LLM relationship detection failed: {e}")
            return []
    
    def _validate_llm_relationship(self, llm_rel: Dict[str, Any], schema_entities: List[SchemaEntity]) -> bool:
        """Validate that an LLM-suggested relationship is valid"""
        try:
            from_entity_name = llm_rel["from_entity"]
            to_entity_name = llm_rel["to_entity"]
            from_column = llm_rel["from_column"]
            to_column = llm_rel["to_column"]
            
            # Find the entities
            from_entity = next((e for e in schema_entities if e.name == from_entity_name), None)
            to_entity = next((e for e in schema_entities if e.name == to_entity_name), None)
            
            if not from_entity or not to_entity:
                return False
            
            # Check if columns exist
            from_col_exists = any(col["name"] == from_column for col in from_entity.columns)
            to_col_exists = any(col["name"] == to_column for col in to_entity.columns)
            
            if not from_col_exists or not to_col_exists:
                return False
            
            # Basic validation passed
            return True
            
        except Exception:
            return False
    
    def _calculate_relationship_confidence(self, fk_column: Dict[str, Any], 
                                         from_entity: SchemaEntity,
                                         to_entity: SchemaEntity) -> float:
        """Calculate confidence score for a potential relationship"""
        confidence = 0.0
        
        # Higher confidence if it's clearly an ID field
        if 'id' in fk_column['name'].lower():
            confidence += 0.4
        
        # Higher confidence if data types match
        fk_type = fk_column['data_type']
        pk_column = next((col for col in to_entity.columns if col['primary_key']), None)
        if pk_column and pk_column['data_type'] == fk_type:
            confidence += 0.3
        
        # Higher confidence based on naming similarity
        to_entity_lower = to_entity.name.lower()
        fk_name_lower = fk_column['name'].lower()
        if to_entity_lower in fk_name_lower:
            confidence += 0.3
        
        return min(confidence, 1.0)
    
    def _deduplicate_relationships(self, relationships: List[Relationship]) -> List[Relationship]:
        """Remove duplicate relationships, keeping the highest confidence ones"""
        seen = {}
        for rel in relationships:
            key = (rel.from_entity, rel.to_entity, rel.from_column)
            if key not in seen or seen[key].confidence < rel.confidence:
                seen[key] = rel
        
        return list(seen.values())
    
    def _entity_to_dict(self, entity: SchemaEntity) -> Dict[str, Any]:
        """Convert SchemaEntity to dictionary format"""
        return {
            'name': entity.name,
            'table_name': entity.table_name,
            'columns': [col['name'] for col in entity.columns],
            'primary_key': entity.primary_key,
            'entity_type': entity.entity_type,
            'column_details': entity.columns
        }
    
    def _relationship_to_dict(self, relationship: Relationship) -> Dict[str, Any]:
        """Convert Relationship to dictionary format"""
        return {
            'from': relationship.from_entity,
            'to': relationship.to_entity,
            'type': relationship.relationship_type,
            'foreign_key': relationship.from_column,
            'references': relationship.to_column,
            'confidence': round(relationship.confidence, 2)
        }
