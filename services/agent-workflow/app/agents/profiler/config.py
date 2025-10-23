"""
Configuration for ProfilerAgent
"""
from dataclasses import dataclass
import os


@dataclass
class ProfilerConfig:
    """Configuration for profiling operations"""
    
    # Storage configuration
    storage_backend: str = "minio"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "uploads"
    
    # Profiling configuration
    profiling_backend: str = "dataprofiler"
    max_rows: int = 10000
    sample_size: int = 10000
    
    # Stats extraction configuration
    sample_values_count: int = 5
    extract_numeric_stats: bool = True
    
    @classmethod
    def from_env(cls) -> 'ProfilerConfig':
        """Create configuration from environment variables"""
        return cls(
            minio_endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            minio_bucket=os.getenv("MINIO_BUCKET", "uploads"),
            max_rows=int(os.getenv("DATAPROFILER_MAX_ROWS", "10000")),
            sample_size=int(os.getenv("DATAPROFILER_SAMPLE_SIZE", "10000")),
        )

