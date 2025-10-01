"""
Validation utilities for pipeline data and requests
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validator for schema data structure and content"""
    
    @staticmethod
    def validate_schema_data(schema_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate the structure and content of schema data
        
        Args:
            schema_data: Schema data dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if schema_data is a dictionary
            if not isinstance(schema_data, dict):
                return False, "Schema data must be a dictionary"
            
            # Check for required top-level keys
            if 'entities' not in schema_data:
                return False, "Schema data must contain 'entities' key"
            
            entities = schema_data['entities']
            
            # Validate entities
            is_valid, error = SchemaValidator._validate_entities(entities)
            if not is_valid:
                return False, f"Invalid entities: {error}"
            
            # Validate relationships if present
            if 'relationships' in schema_data:
                relationships = schema_data['relationships']
                is_valid, error = SchemaValidator._validate_relationships(relationships, entities)
                if not is_valid:
                    return False, f"Invalid relationships: {error}"
            
            # Validate business tags if present
            if 'businessTags' in schema_data:
                business_tags = schema_data['businessTags']
                is_valid, error = SchemaValidator._validate_business_tags(business_tags)
                if not is_valid:
                    return False, f"Invalid business tags: {error}"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def _validate_entities(entities: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """Validate entities structure"""
        if not isinstance(entities, list):
            return False, "Entities must be a list"
        
        if len(entities) == 0:
            return False, "At least one entity is required"
        
        for i, entity in enumerate(entities):
            if not isinstance(entity, dict):
                return False, f"Entity {i} must be a dictionary"
            
            # Check required fields
            required_fields = ['name']
            for field in required_fields:
                if field not in entity:
                    return False, f"Entity {i} missing required field: {field}"
            
            # Validate column details if present
            if 'column_details' in entity:
                columns = entity['column_details']
                is_valid, error = SchemaValidator._validate_columns(columns, i)
                if not is_valid:
                    return False, error
        
        return True, None
    
    @staticmethod
    def _validate_columns(columns: List[Dict[str, Any]], entity_index: int) -> tuple[bool, Optional[str]]:
        """Validate columns structure"""
        if not isinstance(columns, list):
            return False, f"Entity {entity_index} column_details must be a list"
        
        for j, column in enumerate(columns):
            if not isinstance(column, dict):
                return False, f"Entity {entity_index} column {j} must be a dictionary"
            
            # Check required column fields
            required_fields = ['name', 'data_type']
            for field in required_fields:
                if field not in column:
                    return False, f"Entity {entity_index} column {j} missing required field: {field}"
            
            # Validate data type
            data_type = column['data_type']
            if not isinstance(data_type, str) or len(data_type.strip()) == 0:
                return False, f"Entity {entity_index} column {j} data_type must be a non-empty string"
        
        return True, None
    
    @staticmethod
    def _validate_relationships(relationships: List[Dict[str, Any]], entities: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """Validate relationships structure with flexible field names"""
        if not isinstance(relationships, list):
            return False, "Relationships must be a list"
        
        entity_names = {entity['name'] for entity in entities}
        
        for i, relationship in enumerate(relationships):
            if not isinstance(relationship, dict):
                return False, f"Relationship {i} must be a dictionary"
            
            # Check required fields - support multiple formats
            if 'from' not in relationship or 'to' not in relationship:
                return False, f"Relationship {i} missing required fields: 'from' and 'to'"
            
            # Check for column fields - support multiple formats
            has_from_to_columns = 'from_column' in relationship and 'to_column' in relationship
            has_foreign_key_ref = 'foreign_key' in relationship and 'references' in relationship
            
            if not (has_from_to_columns or has_foreign_key_ref):
                return False, f"Relationship {i} must have either (from_column, to_column) or (foreign_key, references). Found keys: {list(relationship.keys())}"
            
            # Check for relationship type field - support both formats
            relationship_type = relationship.get('relationship_type') or relationship.get('type')
            if not relationship_type:
                return False, f"Relationship {i} missing relationship type field (relationship_type or type)"
            
            # Validate entity references
            from_entity = relationship['from']
            to_entity = relationship['to']
            
            if from_entity not in entity_names:
                return False, f"Relationship {i} references unknown from entity: {from_entity}"
            
            if to_entity not in entity_names:
                return False, f"Relationship {i} references unknown to entity: {to_entity}"
            
            # Validate relationship type
            valid_types = ['one_to_one', 'one_to_many', 'many_to_one', 'many_to_many']
            if relationship_type not in valid_types:
                return False, f"Relationship {i} has invalid type '{relationship_type}'. Must be one of: {valid_types}"
        
        return True, None
    
    @staticmethod
    def _validate_business_tags(business_tags: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate business tags structure"""
        if not isinstance(business_tags, dict):
            return False, "Business tags must be a dictionary"
        
        for tag_name, tagged_items in business_tags.items():
            if not isinstance(tag_name, str):
                return False, f"Business tag name must be a string, got: {type(tag_name)}"
            
            if not isinstance(tagged_items, list):
                return False, f"Business tag '{tag_name}' value must be a list"
        
        return True, None


class PipelineRequestValidator:
    """Validator for pipeline API requests"""
    
    @staticmethod
    def validate_trigger_request(request_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate pipeline trigger request
        
        Args:
            request_data: Request data dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check required fields
            required_fields = ['job_id', 'schema_data']
            for field in required_fields:
                if field not in request_data:
                    return False, f"Missing required field: {field}"
            
            # Validate job_id
            job_id = request_data['job_id']
            if not isinstance(job_id, str) or len(job_id.strip()) == 0:
                return False, "job_id must be a non-empty string"
            
            # Validate schema_data
            schema_data = request_data['schema_data']
            is_valid, error = SchemaValidator.validate_schema_data(schema_data)
            if not is_valid:
                return False, f"Invalid schema_data: {error}"
            
            return True, None
            
        except Exception as e:
            return False, f"Request validation error: {str(e)}"


def validate_run_id(run_id: str) -> bool:
    """
    Validate pipeline run ID format
    
    Args:
        run_id: Run ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(run_id, str):
        return False
    
    if len(run_id.strip()) == 0:
        return False
    
    # Additional format validation can be added here
    # For example, checking for specific patterns or length
    
    return True


def validate_job_id(job_id: str) -> bool:
    """
    Validate job ID format
    
    Args:
        job_id: Job ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(job_id, str):
        return False
    
    if len(job_id.strip()) == 0:
        return False
    
    # Additional format validation can be added here
    
    return True
