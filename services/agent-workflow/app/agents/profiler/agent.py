"""
ProfilerAgent - Main orchestrator
"""
from typing import List, Optional
import pandas as pd
import logging
from .models import FileProfile, ColumnProfile
from .config import ProfilerConfig
from .storage import MinIOStorage
from .loaders import CSVLoader, ExcelLoader
from .backends import DataProfilerBackend
from .stats import NullablePredictor, StatsExtractor

try:
    from ...observability import trace_agent, observability
except ImportError:
    # Fallback for when observability is not available
    def trace_agent(name):
        def decorator(func):
            return func
        return decorator
    
    class MockObservability:
        def create_agent_span(self, *args, **kwargs): return None
        def log_agent_output(self, *args, **kwargs): pass
        def end_agent_span(self, *args, **kwargs): pass
    
    observability = MockObservability()

logger = logging.getLogger(__name__)


class ProfilerAgent:
    """
    Profiler Agent: Downloads files and analyzes them using pluggable backends
    Identifies columns, infers data types, detects semantic types, and calculates statistics.
    """
    
    def __init__(self, config: Optional[ProfilerConfig] = None):
        """
        Initialize ProfilerAgent with configuration
        
        Args:
            config: ProfilerConfig instance (defaults to env-based config)
        """
        self.config = config or ProfilerConfig.from_env()
        
        # Initialize components
        self.storage = MinIOStorage(self.config)
        self.loaders = [CSVLoader(), ExcelLoader()]
        self.profiling_backend = DataProfilerBackend(self.config)
        self.nullable_predictor = NullablePredictor()
        self.stats_extractor = StatsExtractor(self.config)
        
        logger.info("ProfilerAgent initialized")
    
    @trace_agent("ProfilerAgent")
    def profile_job_files(self, job_id: str) -> List[FileProfile]:
        """
        Profile all files in a job directory
        
        Args:
            job_id: Job identifier
            
        Returns:
            List of FileProfile objects
        """
        span = observability.create_agent_span("ProfilerAgent", {
            "job_id": job_id
        })
        
        try:
            logger.info(f"Starting profiling for job {job_id}")
            
            # List files from storage
            file_paths = self.storage.list_files(f"jobs/{job_id}/")
            logger.info(f"Found {len(file_paths)} files for job {job_id}")
            
            # Profile each file
            file_profiles = []
            for file_path in file_paths:
                try:
                    profile = self._profile_file(file_path)
                    if profile:
                        file_profiles.append(profile)
                        logger.info(f"Profiled {profile.file_name}: {profile.row_count} rows, {profile.column_count} columns")
                except Exception as e:
                    logger.error(f"Failed to profile {file_path}: {e}")
                    # Continue with other files
            
            # Calculate metrics
            metrics = {
                "files_found": len(file_paths),
                "files_profiled": len(file_profiles),
                "total_rows": sum(fp.row_count for fp in file_profiles),
                "total_columns": sum(fp.column_count for fp in file_profiles)
            }
            
            logger.info(f"Profiling complete: {metrics}")
            
            observability.log_agent_output("ProfilerAgent", {
                "files_profiled": len(file_profiles),
                "file_names": [fp.file_name for fp in file_profiles]
            }, metrics)
            
            observability.end_agent_span(span, {"metrics": metrics})
            
            return file_profiles
            
        except Exception as e:
            logger.error(f"Profiling failed for job {job_id}: {e}")
            observability.end_agent_span(span, {}, str(e))
            raise
    
    def _profile_file(self, file_path: str) -> FileProfile:
        """
        Profile a single file
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            FileProfile object
        """
        logger.debug(f"Profiling file: {file_path}")
        
        # Download file from storage
        file_data, file_size = self.storage.download_file(file_path)
        
        # Extract metadata from path
        file_name = file_path.split('/')[-1]
        file_id = file_path.split('/')[-2] if len(file_path.split('/')) > 1 else "unknown"
        
        # Load DataFrame using appropriate loader
        df = self._load_dataframe(file_name, file_data)
        original_row_count = len(df)
        
        # Sample if needed
        df_sampled = self._sample_if_needed(df)
        
        # Profile with backend
        column_stats_map = self.profiling_backend.profile_dataframe(df_sampled)
        
        # Build column profiles
        column_profiles = []
        for col_name in df_sampled.columns:
            col_stats = column_stats_map.get(col_name, {})
            series = df_sampled[col_name]
            
            col_profile = self._build_column_profile(
                col_name, col_stats, series, len(df_sampled)
            )
            column_profiles.append(col_profile)
        
        return FileProfile(
            file_name=file_name,
            file_id=file_id,
            row_count=original_row_count,
            column_count=len(df.columns),
            columns=column_profiles,
            file_size_bytes=file_size,
            profile_method=self.config.profiling_backend
        )
    
    def _load_dataframe(self, file_name: str, file_data: bytes) -> pd.DataFrame:
        """
        Load file using appropriate loader
        
        Args:
            file_name: Name of the file
            file_data: Raw file bytes
            
        Returns:
            pandas DataFrame
        """
        for loader in self.loaders:
            if loader.can_load(file_name):
                return loader.load(file_data)
        
        raise ValueError(f"No loader found for file: {file_name}")
    
    def _sample_if_needed(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sample DataFrame if it exceeds threshold
        
        Args:
            df: Original DataFrame
            
        Returns:
            Sampled DataFrame (or original if below threshold)
        """
        if len(df) > self.config.max_rows:
            sample_size = min(self.config.sample_size, len(df))
            logger.info(f"Sampling {sample_size} rows from {len(df)} total rows")
            return df.sample(n=sample_size, random_state=42)
        return df
    
    def _build_column_profile(self,
                             col_name: str,
                             col_stats: dict,
                             series: pd.Series,
                             total_count: int) -> ColumnProfile:
        """
        Build complete ColumnProfile from all sources
        
        Args:
            col_name: Column name
            col_stats: Statistics from profiling backend
            series: pandas Series for this column
            total_count: Total row count
            
        Returns:
            ColumnProfile object
        """
        # Extract from profiling backend
        data_type = col_stats.get("data_type", "unknown")
        semantic_type, semantic_confidence = self._extract_semantic_type(col_stats)
        
        statistics = col_stats.get("statistics", {})
        null_count = statistics.get("null_count", 0)
        distinct_count = statistics.get("unique_count", 0)
        null_percentage = (null_count / total_count * 100) if total_count > 0 else 0.0
        
        # Predict nullable using heuristics
        nullable = self.nullable_predictor.predict(
            col_name, semantic_type, null_count, distinct_count, total_count
        )
        
        # Extract additional stats from pandas Series
        sample_values = self.stats_extractor.extract_sample_values(series)
        min_val, max_val, mean_val = self.stats_extractor.extract_numeric_stats(
            series, data_type
        )
        
        return ColumnProfile(
            name=col_name,
            data_type=data_type,
            semantic_type=semantic_type,
            semantic_type_confidence=semantic_confidence,
            null_count=int(null_count),
            total_count=total_count,
            null_percentage=round(null_percentage, 2),
            distinct_count=int(distinct_count),
            nullable=nullable,
            sample_values=sample_values,
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val
        )
    
    def _extract_semantic_type(self, col_stats: dict) -> tuple:
        """
        Extract semantic type and confidence from profiling backend output
        
        Args:
            col_stats: Column statistics dictionary
            
        Returns:
            Tuple of (semantic_type, confidence)
        """
        semantic_types = col_stats.get("data_label", [])
        probabilities = col_stats.get("data_label_probability", [])
        
        if isinstance(semantic_types, list) and len(semantic_types) > 0:
            semantic_type = semantic_types[0]
            # Get confidence from data_label_probability if available
            confidence = probabilities[0] if (isinstance(probabilities, list) and len(probabilities) > 0) else 0.5
            return (semantic_type, confidence)
        return ("unknown", 0.0)

