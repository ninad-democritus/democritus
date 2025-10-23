"""
OpenMetadata-compatible type mapper
Maps profiler data types + semantic types to OpenMetadata data types
"""
from typing import List, Optional, Tuple, Dict, Any
import logging
from ..models import OpenMetadataType

logger = logging.getLogger(__name__)


class OpenMetadataTypeMapper:
    """
    Maps profiler data types + semantic types to OpenMetadata-compatible types
    
    Considers both:
    - Physical data_type (integer, float, string, datetime)
    - Semantic semantic_type (email, uuid, phone_number, etc.)
    
    Returns OpenMetadataType with appropriate attributes
    """
    
    def __init__(self):
        # Base type mappings (profiler data_type → OpenMetadata)
        self.base_type_map = {
            'integer': 'BIGINT',      # Use BIGINT as safe default for integers
            'float': 'DOUBLE',        # DOUBLE for floating point
            'string': 'VARCHAR',      # VARCHAR as default string type
            'datetime': 'TIMESTAMP',  # TIMESTAMP for datetime
            'boolean': 'BOOLEAN',     # Direct mapping
            'date': 'DATE',           # Date only
            'time': 'TIME',           # Time only
            'binary': 'BINARY',       # Binary data
            'unknown': 'STRING',      # Generic STRING for unknown
        }
        
        # Semantic type overrides (semantic_type → OpenMetadata type)
        # These take precedence when semantic_type is specific
        self.semantic_type_overrides = {
            # Identifiers
            'uuid': 'UUID',
            'identifier': 'VARCHAR',
            
            # Contact info
            'email': 'VARCHAR',
            'phone_number': 'VARCHAR',
            'url': 'TEXT',
            
            # Personal data
            'ssn': 'VARCHAR',
            'person_name': 'VARCHAR',
            'address': 'TEXT',
            
            # Financial
            'credit_card': 'VARCHAR',
            'currency': 'DECIMAL',
            
            # Geographic
            'zipcode': 'VARCHAR',
            'latitude': 'DOUBLE',
            'longitude': 'DOUBLE',
            
            # Binary
            'binary': 'BINARY',
            
            # Complex
            'json': 'JSON',
        }
        
        # Default lengths for string types based on semantic type
        self.semantic_length_hints = {
            'email': 320,           # Max email length per RFC
            'phone_number': 20,     # International phone format
            'uuid': 36,             # UUID string representation
            'ssn': 11,              # XXX-XX-XXXX
            'zipcode': 10,          # US ZIP+4
            'credit_card': 19,      # Max card number length
            'person_name': 100,     # Reasonable name length
            'identifier': 50,       # Generic ID
            'url': 2048,            # Max URL length
            'address': 500,         # Full address
        }
        
        # Default precision/scale for numeric semantic types
        self.semantic_numeric_hints = {
            'currency': (19, 4),    # (precision, scale) for money
            'latitude': (10, 8),    # Lat/long precision
            'longitude': (11, 8),
        }
    
    def map_type(
        self,
        data_type: str,
        semantic_type: str,
        sample_values: List[Any] = None,
        distinct_count: int = None,
        total_count: int = None
    ) -> OpenMetadataType:
        """
        Map profiler types to OpenMetadata types
        
        Args:
            data_type: Physical data type from profiler (integer, float, string, etc.)
            semantic_type: Semantic type from profiler (email, uuid, etc.)
            sample_values: Sample values to infer length/precision
            distinct_count: For determining if ENUM is appropriate
            total_count: Total rows
            
        Returns:
            OpenMetadataType with type and attributes
        """
        
        # Step 1: Check semantic type override (most specific)
        if semantic_type and semantic_type.lower() in self.semantic_type_overrides:
            base_type = self.semantic_type_overrides[semantic_type.lower()]
        else:
            # Step 2: Use physical data type mapping
            base_type = self.base_type_map.get(data_type.lower(), 'STRING')
        
        # Step 3: Determine type attributes based on base type
        data_type_display = base_type.lower()
        data_length = None
        precision = None
        scale = None
        
        # VARCHAR/CHAR: Determine length
        if base_type in ['VARCHAR', 'CHAR']:
            data_length = self._infer_string_length(semantic_type, sample_values)
            data_type_display = f"{base_type.lower()}({data_length})"
        
        # TEXT: No length needed
        elif base_type == 'TEXT':
            data_type_display = "text"
        
        # DECIMAL/NUMERIC: Determine precision and scale
        elif base_type in ['DECIMAL', 'NUMERIC']:
            precision, scale = self._infer_numeric_precision(semantic_type, sample_values)
            data_type_display = f"{base_type.lower()}({precision},{scale})"
        
        # UUID: No additional attributes
        elif base_type == 'UUID':
            data_type_display = "uuid"
        
        # JSON: No additional attributes
        elif base_type == 'JSON':
            data_type_display = "json"
        
        # Other types
        else:
            data_type_display = base_type.lower()
        
        # Consider ENUM for low-cardinality string columns
        if self._should_be_enum(base_type, distinct_count, total_count):
            logger.debug(f"Column could be ENUM (distinct={distinct_count}, total={total_count})")
            # Keep base type but log suggestion
        
        return OpenMetadataType(
            data_type=base_type,
            data_type_display=data_type_display,
            data_length=data_length,
            precision=precision,
            scale=scale
        )
    
    def _infer_string_length(
        self,
        semantic_type: str,
        sample_values: List[Any]
    ) -> int:
        """Infer appropriate VARCHAR length"""
        
        # Step 1: Use semantic type hint if available
        if semantic_type and semantic_type.lower() in self.semantic_length_hints:
            return self.semantic_length_hints[semantic_type.lower()]
        
        # Step 2: Analyze sample values if available
        if sample_values:
            try:
                max_sample_length = max(
                    (len(str(val)) for val in sample_values if val is not None),
                    default=0
                )
                if max_sample_length > 0:
                    # Add 20% buffer, round up to nearest 50
                    suggested_length = int(max_sample_length * 1.2)
                    suggested_length = ((suggested_length // 50) + 1) * 50
                    return min(suggested_length, 2000)  # Cap at 2000
            except Exception as e:
                logger.debug(f"Error analyzing sample values: {e}")
        
        # Step 3: Default fallback
        return 255  # Standard VARCHAR default
    
    def _infer_numeric_precision(
        self,
        semantic_type: str,
        sample_values: List[Any]
    ) -> Tuple[int, int]:
        """Infer DECIMAL precision and scale"""
        
        # Step 1: Use semantic type hint if available
        if semantic_type and semantic_type.lower() in self.semantic_numeric_hints:
            return self.semantic_numeric_hints[semantic_type.lower()]
        
        # Step 2: Analyze sample values if available
        if sample_values:
            try:
                max_precision = 0
                max_scale = 0
                
                for val in sample_values:
                    if val is None:
                        continue
                    
                    val_str = str(val)
                    if '.' in val_str:
                        parts = val_str.split('.')
                        integer_part = parts[0].replace('-', '').replace('+', '')
                        decimal_part = parts[1] if len(parts) > 1 else ''
                        
                        total_digits = len(integer_part) + len(decimal_part)
                        decimal_digits = len(decimal_part)
                        
                        max_precision = max(max_precision, total_digits)
                        max_scale = max(max_scale, decimal_digits)
                    else:
                        integer_digits = len(val_str.replace('-', '').replace('+', ''))
                        max_precision = max(max_precision, integer_digits)
                
                if max_precision > 0:
                    # Add small buffer for precision
                    return (min(max_precision + 2, 38), max_scale)
            except Exception as e:
                logger.debug(f"Error analyzing numeric sample values: {e}")
        
        # Step 3: Default fallback
        return (18, 2)  # Standard decimal(18,2)
    
    def _should_be_enum(
        self,
        base_type: str,
        distinct_count: int,
        total_count: int
    ) -> bool:
        """Determine if column should be ENUM"""
        if base_type not in ['VARCHAR', 'CHAR', 'STRING']:
            return False
        
        if distinct_count is None or total_count is None or total_count == 0:
            return False
        
        # ENUM candidates: very low cardinality (< 50 distinct, < 5% of total)
        if distinct_count <= 50 and (distinct_count / total_count) < 0.05:
            return True
        
        return False
    
    def to_dict(self, om_type: OpenMetadataType) -> Dict[str, Any]:
        """
        Convert OpenMetadataType to dictionary format for output
        
        Returns dict with OpenMetadata schema structure
        """
        result = {
            "dataType": om_type.data_type,
            "dataTypeDisplay": om_type.data_type_display
        }
        
        if om_type.data_length is not None:
            result["dataLength"] = om_type.data_length
        
        if om_type.precision is not None:
            result["precision"] = om_type.precision
        
        if om_type.scale is not None:
            result["scale"] = om_type.scale
        
        if om_type.array_data_type is not None:
            result["arrayDataType"] = om_type.array_data_type
        
        return result

