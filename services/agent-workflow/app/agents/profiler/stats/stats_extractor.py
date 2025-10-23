"""
Additional statistics extraction from pandas Series
"""
import pandas as pd
import numpy as np
from typing import Any, Tuple, List
import logging
from ..config import ProfilerConfig

logger = logging.getLogger(__name__)


class StatsExtractor:
    """Extract additional statistics not provided by profiling backend"""
    
    def __init__(self, config: ProfilerConfig):
        """
        Initialize stats extractor
        
        Args:
            config: ProfilerConfig instance
        """
        self.sample_values_count = config.sample_values_count
        self.extract_numeric_stats = config.extract_numeric_stats
    
    def extract_sample_values(self, series: pd.Series) -> List[Any]:
        """
        Extract sample non-null values
        
        Args:
            series: pandas Series
            
        Returns:
            List of sample values
        """
        try:
            non_null_series = series.dropna()
            sample_size = min(self.sample_values_count, len(non_null_series))
            samples = non_null_series.head(sample_size).tolist()
            logger.debug(f"Extracted {len(samples)} sample values")
            return samples
        except Exception as e:
            logger.warning(f"Failed to extract sample values: {e}")
            return []
    
    def extract_numeric_stats(self, 
                              series: pd.Series,
                              data_type: str) -> Tuple[Any, Any, Any]:
        """
        Extract min, max, mean for numeric columns
        
        Args:
            series: pandas Series
            data_type: Detected data type
            
        Returns:
            Tuple of (min_value, max_value, mean_value)
        """
        
        if not self.extract_numeric_stats:
            return None, None, None
        
        if data_type not in ['integer', 'float', 'numeric']:
            return None, None, None
        
        try:
            numeric_series = pd.to_numeric(series, errors='coerce').dropna()
            if numeric_series.empty:
                return None, None, None
            
            min_val = float(numeric_series.min())
            max_val = float(numeric_series.max())
            mean_val = float(numeric_series.mean())
            
            logger.debug(f"Numeric stats: min={min_val}, max={max_val}, mean={mean_val}")
            return min_val, max_val, mean_val
            
        except Exception as e:
            logger.warning(f"Failed to extract numeric stats: {e}")
            return None, None, None

