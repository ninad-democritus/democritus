"""
Data models for file operations
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel


class FileInfo(BaseModel):
    """Information about a file in storage"""
    name: str  # Full path/object name
    size: Optional[int] = None
    last_modified: Optional[datetime] = None
    content_type: Optional[str] = None
    etag: Optional[str] = None
    bucket: Optional[str] = None
    is_directory: bool = False
    metadata: Dict[str, Any] = {}
    
    @property
    def file_name(self) -> str:
        """Get the file name without path"""
        return self.name.split('/')[-1]
    
    @property
    def file_extension(self) -> str:
        """Get the file extension"""
        return self.file_name.split('.')[-1].lower() if '.' in self.file_name else ''
    
    @property
    def is_supported_format(self) -> bool:
        """Check if file format is supported"""
        supported_formats = {'csv', 'xlsx', 'xls', 'parquet', 'json'}
        return self.file_extension in supported_formats
    
    def __str__(self) -> str:
        bucket_part = f"{self.bucket}/" if self.bucket else ""
        return f"FileInfo({bucket_part}{self.name})"


# Keep the old dataclass for backward compatibility
@dataclass
class LegacyFileInfo:
    """Legacy file info for backward compatibility"""
    object_name: str
    bucket_name: str
    size: int
    last_modified: datetime
    content_type: Optional[str] = None
    etag: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def file_name(self) -> str:
        """Get the file name without path"""
        return self.object_name.split('/')[-1]
    
    @property
    def file_extension(self) -> str:
        """Get the file extension"""
        return self.file_name.split('.')[-1].lower() if '.' in self.file_name else ''
    
    @property
    def is_supported_format(self) -> bool:
        """Check if file format is supported"""
        supported_formats = {'csv', 'xlsx', 'xls', 'parquet', 'json'}
        return self.file_extension in supported_formats
    
    def __str__(self) -> str:
        return f"FileInfo({self.bucket_name}/{self.object_name})"


@dataclass
class EntityFileMatch:
    """Represents a match between an entity and files"""
    entity_name: str
    entity_id: str
    matched_files: list[FileInfo]
    confidence_scores: Dict[str, float]  # file_name -> confidence score
    
    def get_best_match(self) -> Optional[FileInfo]:
        """Get the file with the highest confidence score"""
        if not self.matched_files:
            return None
        
        best_file = max(
            self.matched_files, 
            key=lambda f: self.confidence_scores.get(f.file_name, 0.0)
        )
        return best_file
    
    def get_average_confidence(self) -> float:
        """Get the average confidence score for all matched files"""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)


class ValidationResult(BaseModel):
    """Result of file validation"""
    valid: bool
    file_path: str
    errors: List[str] = []
    warnings: List[str] = []
    metadata: Dict[str, Any] = {}
    
    def add_error(self, error: str) -> None:
        """Add an error to the validation result"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result"""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0


# Keep legacy validation result for backward compatibility
@dataclass
class LegacyValidationResult:
    """Legacy validation result for backward compatibility"""
    is_valid: bool
    file_info: LegacyFileInfo
    errors: list[str]
    warnings: list[str]
    schema_info: Optional[Dict[str, Any]] = None
    
    def add_error(self, error: str) -> None:
        """Add an error to the validation result"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result"""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0
