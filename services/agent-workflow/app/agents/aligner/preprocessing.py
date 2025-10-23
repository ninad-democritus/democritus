"""
Name preprocessing and normalization for AlignerAgent
"""
import re
import logging
from typing import List, Dict, Any
from ..profiler import FileProfile, ColumnProfile

logger = logging.getLogger(__name__)


class NamePreprocessor:
    """Normalize and tokenize entity and column names"""
    
    def __init__(self):
        """Initialize preprocessor with common prefixes/suffixes to remove"""
        self.entity_prefixes = ['tbl_', 'dim_', 'fact_', 'stg_', 'raw_', 'src_']
        self.file_extensions = ['.csv', '.xlsx', '.xls', '.parquet', '.avro']
    
    def normalize_entity_name(self, raw_name: str) -> str:
        """
        Normalize entity names (files, sheets, table names)
        
        Args:
            raw_name: Original entity name
            
        Returns:
            Normalized entity name
        """
        name = raw_name.lower()
        
        # Remove file extensions
        for ext in self.file_extensions:
            if name.endswith(ext):
                name = name[:-len(ext)]
        
        # Replace separators with spaces
        name = re.sub(r'[-_.]', ' ', name)
        
        # Split camelCase
        name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
        
        # Remove common prefixes
        for prefix in self.entity_prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
        
        # Remove multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        logger.debug(f"Normalized entity '{raw_name}' -> '{name}'")
        return name
    
    def normalize_column_name(self, raw_name: str) -> str:
        """
        Normalize column names
        
        Args:
            raw_name: Original column name
            
        Returns:
            Normalized column name
        """
        name = raw_name.lower()
        
        # Replace separators with spaces
        name = re.sub(r'[-_.]', ' ', name)
        
        # Split camelCase
        name = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
        
        # Remove multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def tokenize(self, name: str) -> List[str]:
        """
        Split normalized name into tokens
        
        Args:
            name: Normalized name
            
        Returns:
            List of tokens
        """
        return name.split()
    
    def extract_entity_tokens(self, file_profile: FileProfile) -> Dict[str, Any]:
        """
        Extract entity-level information from file profile
        
        Args:
            file_profile: FileProfile object
            
        Returns:
            Dictionary with entity tokens and metadata
        """
        raw_name = file_profile.file_name
        normalized = self.normalize_entity_name(raw_name)
        
        return {
            'raw_name': raw_name,
            'normalized': normalized,
            'tokens': self.tokenize(normalized),
            'file_id': file_profile.file_id,
            'file_profile': file_profile
        }
    
    def extract_column_tokens(self, 
                             column: ColumnProfile, 
                             file_context: str) -> Dict[str, Any]:
        """
        Extract column-level information
        
        Args:
            column: ColumnProfile object
            file_context: File ID or name for context
            
        Returns:
            Dictionary with column tokens and metadata
        """
        raw_name = column.name
        normalized = self.normalize_column_name(raw_name)
        fqn = f"{file_context}::{raw_name}"  # Fully qualified name
        
        return {
            'raw_name': raw_name,
            'normalized': normalized,
            'tokens': self.tokenize(normalized),
            'fqn': fqn,
            'file_id': file_context,
            'column_profile': column
        }

