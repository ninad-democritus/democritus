"""Custom JSON encoder for handling special types"""
import json
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Any

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles:
    - Decimal objects (from database queries)
    - datetime/date objects
    - Other non-serializable types
    """
    
    def default(self, obj: Any) -> Any:
        """
        Convert non-serializable objects to JSON-serializable types.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, Decimal):
            # Convert Decimal to float for JSON serialization
            # Use float() to avoid precision issues with small decimals
            return float(obj)
        elif isinstance(obj, (datetime, date)):
            # Convert datetime/date to ISO format string
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            # For custom objects, try to serialize their dict
            return obj.__dict__
        else:
            # Fall back to default behavior (will raise TypeError)
            return super().default(obj)


def json_dumps(obj: Any, **kwargs) -> str:
    """
    JSON dumps with custom encoder for handling Decimal and other special types.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps
        
    Returns:
        JSON string
    """
    return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)


def convert_decimals_to_float(obj: Any) -> Any:
    """
    Recursively convert all Decimal objects in a data structure to floats.
    This is useful for pre-processing data before JSON serialization.
    
    Args:
        obj: Data structure to convert (dict, list, or primitive)
        
    Returns:
        Data structure with Decimals converted to floats
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj

