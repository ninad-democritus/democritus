"""
DataProfiler library backend implementation
"""
from dataprofiler import Profiler, Data
import pandas as pd
import logging
from typing import Dict, Any
from .base import ProfilingBackend
from ..config import ProfilerConfig

logger = logging.getLogger(__name__)


class DataProfilerBackend(ProfilingBackend):
    """DataProfiler library integration"""
    
    def __init__(self, config: ProfilerConfig):
        """
        Initialize DataProfiler backend
        
        Args:
            config: ProfilerConfig instance
        """
        self.config = config
        logger.info("DataProfiler backend initialized")
    
    def profile_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Profile DataFrame using DataProfiler library
        
        Args:
            df: pandas DataFrame to profile
            
        Returns:
            Dictionary mapping column names to statistics
        """
        try:
            logger.debug(f"Profiling DataFrame: {len(df)} rows, {len(df.columns)} columns")
            
            # Create Data object and profile
            data = Data(df)
            profiler = Profiler(data)
            report = profiler.report()
            
            # Transform to our standard format (column name -> stats)
            column_stats = {}
            for col_stat in report.get("data_stats", []):
                col_name = col_stat.get("column_name", "unknown")
                column_stats[col_name] = col_stat
            
            logger.debug(f"Profiled {len(column_stats)} columns")
            return column_stats
            
        except Exception as e:
            logger.error(f"DataProfiler failed: {e}")
            raise

