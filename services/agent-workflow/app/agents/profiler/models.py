"""
Data models for ProfilerAgent
"""
from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class ColumnProfile:
    """Complete column profile with all statistics"""
    name: str
    data_type: str
    semantic_type: str
    semantic_type_confidence: float
    null_count: int
    total_count: int
    null_percentage: float
    distinct_count: int
    nullable: bool
    sample_values: List[Any] = field(default_factory=list)
    min_value: Any = None
    max_value: Any = None
    mean_value: Any = None


@dataclass
class FileProfile:
    """Complete file profile"""
    file_name: str
    file_id: str
    row_count: int
    column_count: int
    columns: List[ColumnProfile]
    file_size_bytes: int
    profile_method: str = "dataprofiler"

