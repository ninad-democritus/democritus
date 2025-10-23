"""
Excel file loader implementation
"""
import pandas as pd
import io
import logging
from .base import FileLoader

logger = logging.getLogger(__name__)


class ExcelLoader(FileLoader):
    """Excel file loader (xlsx, xls)"""
    
    def can_load(self, file_name: str) -> bool:
        """Check if file is Excel"""
        return file_name.lower().endswith(('.xlsx', '.xls'))
    
    def load(self, file_data: bytes) -> pd.DataFrame:
        """Load Excel file into DataFrame"""
        try:
            df = pd.read_excel(io.BytesIO(file_data))
            logger.debug(f"Loaded Excel: {len(df)} rows, {len(df.columns)} columns")
            return df
        except Exception as e:
            logger.error(f"Failed to load Excel: {e}")
            raise

