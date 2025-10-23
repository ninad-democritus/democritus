import pandas as pd
import numpy as np
from typing import Dict, List, Any
from minio import Minio
import io
import os
import logging
from dataclasses import dataclass
from dataprofiler import Profiler, Data

try:
    from ..observability import trace_agent, observability
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

@dataclass
class ColumnProfile:
    name: str
    data_type: str
    semantic_type: str
    null_count: int
    total_count: int
    null_percentage: float
    distinct_count: int
    nullable: bool

@dataclass
class FileProfile:
    file_name: str
    file_id: str
    row_count: int
    column_count: int
    columns: List[ColumnProfile]
    file_size_bytes: int
    profile_method: str = "dataprofiler"

class ProfilerAgent:
    """
    Profiler Agent: Downloads files from MinIO and analyzes them using DataProfiler
    to identify columns, infer data types, detect semantic types, and calculate statistics.
    """
    
    def __init__(self):
        self.minio_client = self._get_minio_client()
        self.max_rows = int(os.environ.get("DATAPROFILER_MAX_ROWS", "10000"))
        self.sample_size = int(os.environ.get("DATAPROFILER_SAMPLE_SIZE", "10000"))
        
    def _get_minio_client(self) -> Minio:
        endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
        access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
        secure = False if ":9000" in endpoint or endpoint.startswith("minio") else True
        return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
    
    @trace_agent("ProfilerAgent")
    def profile_job_files(self, job_id: str) -> List[FileProfile]:
        """Profile all files in a job directory"""
        bucket = os.environ.get("MINIO_BUCKET", "uploads")
        file_profiles = []
        
        # Create detailed tracing span
        span = observability.create_agent_span("ProfilerAgent", {"job_id": job_id, "bucket": bucket})
        
        try:
            # List all objects in the job directory
            objects = self.minio_client.list_objects(bucket, prefix=f"jobs/{job_id}/", recursive=True)
            
            files_found = []
            for obj in objects:
                if obj.object_name.endswith(('.csv', '.xlsx', '.xls')):
                    files_found.append(obj.object_name)
                    try:
                        profile = self._profile_file(bucket, obj.object_name)
                        if profile:
                            file_profiles.append(profile)
                    except Exception as e:
                        logger.error(f"Failed to profile file {obj.object_name}: {e}")
            
            # Log metrics
            metrics = {
                "files_found": len(files_found),
                "files_profiled": len(file_profiles),
                "total_rows": sum(fp.row_count for fp in file_profiles),
                "total_columns": sum(fp.column_count for fp in file_profiles)
            }
            
            observability.log_agent_output("ProfilerAgent", {
                "files_profiled": len(file_profiles),
                "file_names": [fp.file_name for fp in file_profiles]
            }, metrics)
            
            observability.end_agent_span(span, {
                "file_profiles_count": len(file_profiles),
                "metrics": metrics
            })
                        
        except Exception as e:
            logger.error(f"Failed to list objects for job {job_id}: {e}")
            observability.end_agent_span(span, {}, str(e))
            raise
            
        return file_profiles
    
    def _profile_file(self, bucket: str, object_name: str) -> FileProfile:
        """Profile a single file using DataProfiler"""
        try:
            # Download file
            response = self.minio_client.get_object(bucket, object_name)
            file_data = response.read()
            file_size = len(file_data)
            
            # Extract file info
            file_name = object_name.split('/')[-1]
            file_id = object_name.split('/')[-2]
            
            # Read file based on extension
            if file_name.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_data))
            elif file_name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(file_data))
            else:
                raise ValueError(f"Unsupported file type: {file_name}")
            
            # Store original row count
            original_row_count = len(df)
            
            # Sample DataFrame if it's too large
            df_sampled = self._sample_dataframe(df)
            
            # Profile with DataProfiler
            column_profiles = self._profile_with_dataprofiler(df_sampled, file_name)
            
            return FileProfile(
                file_name=file_name,
                file_id=file_id,
                row_count=original_row_count,
                column_count=len(df.columns),
                columns=column_profiles,
                file_size_bytes=file_size,
                profile_method="dataprofiler"
            )
            
        except Exception as e:
            logger.error(f"Error profiling file {object_name}: {e}")
            raise
        finally:
            response.close()
    
    def _sample_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sample DataFrame if it exceeds max_rows threshold"""
        if len(df) > self.max_rows:
            logger.info(f"Sampling {self.sample_size} rows from {len(df)} total rows")
            return df.sample(n=min(self.sample_size, len(df)), random_state=42)
        return df
    
    def _profile_with_dataprofiler(self, df: pd.DataFrame, file_name: str) -> List[ColumnProfile]:
        """Profile DataFrame using DataProfiler library"""
        try:
            # Create Data object and profile
            data = Data(df)
            profiler = Profiler(data)
            report = profiler.report()
            
            column_profiles = []
            
            # Extract column statistics from report
            for column_stats in report.get("data_stats", []):
                col_profile = self._build_column_profile(column_stats, len(df))
                column_profiles.append(col_profile)
            
            return column_profiles
            
        except Exception as e:
            logger.error(f"DataProfiler failed for {file_name}: {e}")
            raise
    
    def _build_column_profile(self, column_stats: Dict[str, Any], total_count: int) -> ColumnProfile:
        """Build ColumnProfile from DataProfiler column statistics"""
        
        # Extract basic information
        column_name = column_stats.get("column_name", "unknown")
        data_type = column_stats.get("data_type", "unknown")
        
        # Extract semantic type (first from list, or "unknown")
        semantic_type = self._extract_semantic_type(column_stats)
        
        # Extract statistics
        statistics = column_stats.get("statistics", {})
        null_count = statistics.get("null_count", 0)
        distinct_count = statistics.get("unique_count", 0)
        
        # Calculate null percentage
        null_percentage = (null_count / total_count * 100) if total_count > 0 else 0.0
        
        # Predict nullable
        nullable = self._predict_nullable(column_stats, column_name, null_count, distinct_count, total_count, semantic_type)
        
        return ColumnProfile(
            name=column_name,
            data_type=data_type,
            semantic_type=semantic_type,
            null_count=int(null_count),
            total_count=total_count,
            null_percentage=round(null_percentage, 2),
            distinct_count=int(distinct_count),
            nullable=nullable
        )
    
    def _extract_semantic_type(self, column_stats: Dict[str, Any]) -> str:
        """Extract the first semantic type from DataProfiler results"""
        semantic_types = column_stats.get("data_label", [])
        
        if isinstance(semantic_types, list) and len(semantic_types) > 0:
            return semantic_types[0]
        
        return "unknown"
    
    def _predict_nullable(
        self, 
        column_stats: Dict[str, Any],
        column_name: str, 
        null_count: int,
        distinct_count: int,
        total_count: int,
        semantic_type: str
    ) -> bool:
        """
        Predict whether a column should be nullable based on data characteristics
        and semantic meaning.
        """
        
        # If column has nulls, it's clearly nullable
        if null_count > 0:
            return True
        
        # Check semantic type for fields that are typically optional
        optional_semantic_types = [
            "email", "phone_number", "ssn", "credit_card",
            "middle_name", "secondary", "alternate", "optional"
        ]
        
        if semantic_type.lower() in optional_semantic_types:
            return True
        
        # Check column name for optional indicators
        optional_name_keywords = [
            "optional", "alt", "alternate", "secondary", "middle",
            "suffix", "prefix", "nickname", "maiden"
        ]
        
        if any(keyword in column_name.lower() for keyword in optional_name_keywords):
            return True
        
        # Check if it looks like a primary key (high uniqueness, no nulls)
        # Primary keys should not be nullable
        if distinct_count == total_count and total_count > 0:
            # Possible primary key pattern
            pk_indicators = ["id", "_id", "key", "_key", "uuid", "guid"]
            if any(indicator in column_name.lower() for indicator in pk_indicators):
                return False
        
        # Default to nullable for safety (most columns accept nulls)
        return True
