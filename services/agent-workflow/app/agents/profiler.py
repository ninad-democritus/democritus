import pandas as pd
import numpy as np
from typing import Dict, List, Any
from minio import Minio
import io
import os
import logging
from dataclasses import dataclass
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
    null_count: int
    total_count: int
    null_percentage: float
    distinct_count: int
    sample_values: List[Any]
    min_value: Any = None
    max_value: Any = None
    mean_value: Any = None

@dataclass
class FileProfile:
    file_name: str
    file_id: str
    row_count: int
    column_count: int
    columns: List[ColumnProfile]
    file_size_bytes: int

class ProfilerAgent:
    """
    Profiler Agent: Downloads files from MinIO and analyzes them to identify columns,
    infer data types, and calculate basic statistics.
    """
    
    def __init__(self):
        self.minio_client = self._get_minio_client()
        
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
        """Profile a single file"""
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
            
            # Profile each column
            column_profiles = []
            for col in df.columns:
                profile = self._profile_column(df, col)
                column_profiles.append(profile)
            
            return FileProfile(
                file_name=file_name,
                file_id=file_id,
                row_count=len(df),
                column_count=len(df.columns),
                columns=column_profiles,
                file_size_bytes=file_size
            )
            
        except Exception as e:
            logger.error(f"Error profiling file {object_name}: {e}")
            raise
        finally:
            response.close()
    
    def _profile_column(self, df: pd.DataFrame, column_name: str) -> ColumnProfile:
        """Profile a single column"""
        series = df[column_name]
        
        # Basic stats
        total_count = len(series)
        null_count = series.isnull().sum()
        null_percentage = (null_count / total_count) * 100 if total_count > 0 else 0
        distinct_count = series.nunique()
        
        # Infer data type
        data_type = self._infer_data_type(series)
        
        # Sample values (non-null)
        non_null_series = series.dropna()
        sample_size = min(5, len(non_null_series))
        sample_values = non_null_series.head(sample_size).tolist()
        
        # Numeric statistics
        min_value = None
        max_value = None
        mean_value = None
        
        if data_type in ['integer', 'float', 'numeric']:
            try:
                numeric_series = pd.to_numeric(series, errors='coerce').dropna()
                if not numeric_series.empty:
                    min_value = float(numeric_series.min())
                    max_value = float(numeric_series.max())
                    mean_value = float(numeric_series.mean())
            except Exception:
                pass
        
        return ColumnProfile(
            name=column_name,
            data_type=data_type,
            null_count=int(null_count),
            total_count=total_count,
            null_percentage=round(null_percentage, 2),
            distinct_count=distinct_count,
            sample_values=sample_values,
            min_value=min_value,
            max_value=max_value,
            mean_value=mean_value
        )
    
    def _infer_data_type(self, series: pd.Series) -> str:
        """Infer the data type of a pandas Series"""
        # Remove nulls for type inference
        non_null_series = series.dropna()
        
        if non_null_series.empty:
            return 'unknown'
        
        # Check if it's numeric
        try:
            numeric_series = pd.to_numeric(non_null_series, errors='coerce')
            if not numeric_series.isnull().any():
                # Check if it's integer
                if (numeric_series % 1 == 0).all():
                    return 'integer'
                else:
                    return 'float'
        except Exception:
            pass
        
        # Check if it's datetime
        try:
            pd.to_datetime(non_null_series, errors='raise')
            return 'datetime'
        except Exception:
            pass
        
        # Check if it's boolean
        unique_values = set(str(v).lower() for v in non_null_series.unique())
        if unique_values.issubset({'true', 'false', '1', '0', 'yes', 'no', 't', 'f', 'y', 'n'}):
            return 'boolean'
        
        # Check if it looks like an ID
        if series.name and any(keyword in series.name.lower() for keyword in ['id', '_id', 'key', '_key']):
            if non_null_series.nunique() / len(non_null_series) > 0.95:  # High uniqueness
                return 'identifier'
        
        # Default to string
        return 'string'
