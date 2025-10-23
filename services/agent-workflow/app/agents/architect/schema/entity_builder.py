"""
Entity builder - converts CanonicalEntity to SchemaEntity
"""
from typing import List
import re
import logging
from ..models import SchemaEntity, ColumnSchema
from ..config import ArchitectConfig
from .type_mapper import OpenMetadataTypeMapper
from .primary_key_selector import PrimaryKeySelector

logger = logging.getLogger(__name__)


class SchemaEntityBuilder:
    """Builds SchemaEntity from CanonicalEntity with OpenMetadata types"""
    
    def __init__(self, config: ArchitectConfig):
        self.config = config
        self.type_mapper = OpenMetadataTypeMapper()
        self.pk_selector = PrimaryKeySelector(config)
    
    def build_schema_entities(self, canonical_entities: List) -> List[SchemaEntity]:
        """
        Convert CanonicalEntity list to SchemaEntity list
        
        Args:
            canonical_entities: List of CanonicalEntity from AlignerAgent
            
        Returns:
            List of SchemaEntity with OpenMetadata types
        """
        schema_entities = []
        
        for canonical_entity in canonical_entities:
            try:
                schema_entity = self._build_single_entity(canonical_entity)
                schema_entities.append(schema_entity)
            except Exception as e:
                logger.error(f"Failed to build schema entity '{canonical_entity.canonical_name}': {e}")
                # Continue with other entities
        
        logger.info(f"Built {len(schema_entities)} schema entities")
        return schema_entities
    
    def _build_single_entity(self, canonical_entity) -> SchemaEntity:
        """Build a single SchemaEntity from CanonicalEntity"""
        
        # Select primary key using PK detector's ranked candidates
        primary_key = self.pk_selector.select_primary_key(canonical_entity)
        
        # Convert CanonicalColumn → ColumnSchema with OpenMetadata types
        columns = []
        for canonical_col in canonical_entity.columns:
            column_schema = self._build_column_schema(canonical_col, primary_key)
            columns.append(column_schema)
        
        # Create clean table name
        table_name = self._create_table_name(canonical_entity.canonical_name)
        
        # Get row count from first column's stats
        row_count = 0
        if columns and canonical_entity.columns:
            row_count = canonical_entity.columns[0].stats.get('total_count', 0)
        
        return SchemaEntity(
            entity_id=canonical_entity.entity_id,
            canonical_name=canonical_entity.canonical_name,
            raw_names=canonical_entity.raw_names,
            synonyms=canonical_entity.synonyms,
            table_name=table_name,
            primary_key=primary_key,
            columns=columns,
            entity_type=canonical_entity.type,
            row_count=row_count,
            source_files=canonical_entity.source_files,
            alignment_confidence=canonical_entity.confidence
        )
    
    def _build_column_schema(self, canonical_col, primary_key: str) -> ColumnSchema:
        """Build ColumnSchema with OpenMetadata type mapping"""
        
        # Map to OpenMetadata type
        om_type = self.type_mapper.map_type(
            data_type=canonical_col.data_type,
            semantic_type=canonical_col.semantic_type,
            sample_values=canonical_col.stats.get('sample_values', []),
            distinct_count=canonical_col.stats.get('distinct_count'),
            total_count=canonical_col.stats.get('total_count')
        )
        
        # Determine if this is the primary key
        is_pk = canonical_col.canonical_name == primary_key
        
        # Determine uniqueness
        distinct_count = canonical_col.stats.get('distinct_count', 0)
        total_count = canonical_col.stats.get('total_count', 0)
        null_count = canonical_col.stats.get('null_count', 0)
        is_unique = (distinct_count == total_count and null_count == 0) if total_count > 0 else False
        
        return ColumnSchema(
            name=canonical_col.canonical_name,
            canonical_name=canonical_col.canonical_name,
            raw_names=canonical_col.raw_names,
            synonyms=canonical_col.synonyms,
            
            # OpenMetadata type fields
            data_type=om_type.data_type,
            data_type_display=om_type.data_type_display,
            data_length=om_type.data_length,
            precision=om_type.precision,
            scale=om_type.scale,
            
            semantic_type=canonical_col.semantic_type,
            semantic_type_confidence=canonical_col.semantic_type_confidence,
            alignment_confidence=canonical_col.confidence,
            nullable=canonical_col.stats.get('nullable', True),
            is_primary_key=is_pk,
            is_unique=is_unique,
            
            # Statistics
            distinct_count=canonical_col.stats.get('distinct_count', 0),
            total_count=canonical_col.stats.get('total_count', 0),
            null_percentage=canonical_col.stats.get('null_percentage', 0.0),
            sample_values=canonical_col.stats.get('sample_values', [])[:5],  # Limit to 5
            min_value=canonical_col.stats.get('min_value'),
            max_value=canonical_col.stats.get('max_value'),
            mean_value=canonical_col.stats.get('mean_value')
        )
    
    def _create_table_name(self, entity_name: str) -> str:
        """Create a clean table name from entity name"""
        # Convert to lowercase and replace spaces with underscores
        table_name = entity_name.lower().replace(' ', '_')
        
        # Remove special characters (keep only alphanumeric and underscores)
        table_name = re.sub(r'[^a-z0-9_]', '', table_name)
        
        # Ensure it starts with a letter
        if table_name and not table_name[0].isalpha():
            table_name = 'tbl_' + table_name
        
        return table_name or 'unknown_entity'

