"""
Abstract base class for profiling backends
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any


class ProfilingBackend(ABC):
    """Abstract profiling backend interface"""
    
    @abstractmethod
    def profile_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Profile DataFrame and return statistics.
        
        Args:
            df: pandas DataFrame to profile
            
        Returns:
            Dictionary mapping column names to their statistics:
            {
                "column_name": {
                    "data_type": str,
                    "semantic_type": str,
                    "statistics": {
                        "null_count": int,
                        "unique_count": int,
                        ...
                    },
                    "data_label": [...]
                }
            }
        """
        pass

