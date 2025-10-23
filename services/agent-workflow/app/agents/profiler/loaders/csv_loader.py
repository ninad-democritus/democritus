"""
CSV file loader implementation
"""
import pandas as pd
import io
import logging
from .base import FileLoader

logger = logging.getLogger(__name__)


class CSVLoader(FileLoader):
    """CSV file loader"""
    
    def can_load(self, file_name: str) -> bool:
        """Check if file is CSV"""
        return file_name.lower().endswith('.csv')
    
    def load(self, file_data: bytes) -> pd.DataFrame:
        """Load CSV file into DataFrame"""
        try:
            df = pd.read_csv(io.BytesIO(file_data))
            logger.debug(f"Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
            return df
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            raise

