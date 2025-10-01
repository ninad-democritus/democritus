"""
File integrity and validation service
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models import FileInfo, ValidationResult

logger = logging.getLogger(__name__)


class FileValidator:
    """Service for validating file integrity and properties"""
    
    def __init__(self):
        """Initialize the file validator"""
        self.supported_extensions = {'.csv', '.xlsx', '.xls', '.json', '.parquet'}
        self.max_file_size = 100 * 1024 * 1024  # 100MB default
        self.min_file_size = 1  # 1 byte minimum
    
    async def validate_file(self, file_info: FileInfo, content: Optional[bytes] = None) -> ValidationResult:
        """
        Validate a single file
        
        Args:
            file_info: File information object
            content: Optional file content for content-based validation
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        try:
            # Basic file property validation
            basic_validation = self._validate_basic_properties(file_info)
            errors.extend(basic_validation.get('errors', []))
            warnings.extend(basic_validation.get('warnings', []))
            
            # Extension validation
            extension_validation = self._validate_file_extension(file_info.name)
            errors.extend(extension_validation.get('errors', []))
            warnings.extend(extension_validation.get('warnings', []))
            
            # Size validation
            size_validation = self._validate_file_size(file_info.size)
            errors.extend(size_validation.get('errors', []))
            warnings.extend(size_validation.get('warnings', []))
            
            # Content validation if content is provided
            if content:
                content_validation = await self._validate_file_content(file_info.name, content)
                errors.extend(content_validation.get('errors', []))
                warnings.extend(content_validation.get('warnings', []))
            
            return ValidationResult(
                valid=len(errors) == 0,
                file_path=file_info.name,
                errors=errors,
                warnings=warnings,
                metadata={
                    'file_size': file_info.size,
                    'last_modified': file_info.last_modified.isoformat() if file_info.last_modified else None,
                    'content_type': file_info.content_type,
                    'validation_timestamp': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error validating file {file_info.name}: {e}")
            return ValidationResult(
                valid=False,
                file_path=file_info.name,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                metadata={}
            )
    
    async def validate_files(self, files: List[FileInfo], contents: Optional[Dict[str, bytes]] = None) -> List[ValidationResult]:
        """
        Validate multiple files
        
        Args:
            files: List of file information objects
            contents: Optional dictionary of file contents keyed by file path
            
        Returns:
            List of validation results
        """
        results = []
        
        for file_info in files:
            content = contents.get(file_info.name) if contents else None
            result = await self.validate_file(file_info, content)
            results.append(result)
        
        return results
    
    def _validate_basic_properties(self, file_info: FileInfo) -> Dict[str, List[str]]:
        """Validate basic file properties"""
        errors = []
        warnings = []
        
        # Check if file name is valid
        if not file_info.name or file_info.name.strip() == '':
            errors.append("File name is empty or invalid")
        
        # Check for potentially problematic characters
        problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in file_info.name for char in problematic_chars):
            warnings.append(f"File name contains potentially problematic characters: {file_info.name}")
        
        # Check if file is a directory
        if file_info.is_directory:
            errors.append("Path points to a directory, not a file")
        
        # Check last modified date
        if file_info.last_modified and file_info.last_modified > datetime.now():
            warnings.append("File has a future modification date")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_file_extension(self, file_name: str) -> Dict[str, List[str]]:
        """Validate file extension"""
        errors = []
        warnings = []
        
        # Extract extension
        if '.' not in file_name:
            errors.append("File has no extension")
            return {'errors': errors, 'warnings': warnings}
        
        extension = '.' + file_name.split('.')[-1].lower()
        
        if extension not in self.supported_extensions:
            errors.append(f"Unsupported file extension: {extension}. Supported: {', '.join(self.supported_extensions)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_file_size(self, file_size: Optional[int]) -> Dict[str, List[str]]:
        """Validate file size"""
        errors = []
        warnings = []
        
        if file_size is None:
            warnings.append("File size information not available")
            return {'errors': errors, 'warnings': warnings}
        
        if file_size < self.min_file_size:
            errors.append(f"File is too small: {file_size} bytes (minimum: {self.min_file_size} bytes)")
        
        if file_size > self.max_file_size:
            errors.append(f"File is too large: {file_size} bytes (maximum: {self.max_file_size} bytes)")
        
        # Warning for very large files
        if file_size > 50 * 1024 * 1024:  # 50MB
            warnings.append(f"File is quite large: {file_size / (1024*1024):.1f}MB - processing may take longer")
        
        return {'errors': errors, 'warnings': warnings}
    
    async def _validate_file_content(self, file_name: str, content: bytes) -> Dict[str, List[str]]:
        """Validate file content"""
        errors = []
        warnings = []
        
        try:
            # Check if content is empty
            if len(content) == 0:
                errors.append("File content is empty")
                return {'errors': errors, 'warnings': warnings}
            
            # Get file extension
            extension = '.' + file_name.split('.')[-1].lower() if '.' in file_name else ''
            
            # Content-specific validation based on file type
            if extension == '.csv':
                csv_validation = self._validate_csv_content(content)
                errors.extend(csv_validation.get('errors', []))
                warnings.extend(csv_validation.get('warnings', []))
            
            elif extension in ['.xlsx', '.xls']:
                excel_validation = self._validate_excel_content(content)
                errors.extend(excel_validation.get('errors', []))
                warnings.extend(excel_validation.get('warnings', []))
            
            elif extension == '.json':
                json_validation = self._validate_json_content(content)
                errors.extend(json_validation.get('errors', []))
                warnings.extend(json_validation.get('warnings', []))
            
        except Exception as e:
            errors.append(f"Content validation error: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_csv_content(self, content: bytes) -> Dict[str, List[str]]:
        """Validate CSV file content"""
        errors = []
        warnings = []
        
        try:
            import csv
            from io import StringIO
            
            # Try to decode content
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = content.decode('latin-1')
                    warnings.append("File encoding detected as latin-1, UTF-8 preferred")
                except UnicodeDecodeError:
                    errors.append("Unable to decode file content - unsupported encoding")
                    return {'errors': errors, 'warnings': warnings}
            
            # Try to parse as CSV
            csv_reader = csv.reader(StringIO(text_content))
            rows = list(csv_reader)
            
            if len(rows) == 0:
                errors.append("CSV file contains no data")
            elif len(rows) == 1:
                warnings.append("CSV file contains only header row, no data rows")
            
            # Check for consistent column count
            if len(rows) > 1:
                header_cols = len(rows[0])
                inconsistent_rows = []
                
                for i, row in enumerate(rows[1:], 1):
                    if len(row) != header_cols:
                        inconsistent_rows.append(i)
                
                if inconsistent_rows:
                    if len(inconsistent_rows) > 5:
                        warnings.append(f"Multiple rows have inconsistent column count (first 5: rows {inconsistent_rows[:5]})")
                    else:
                        warnings.append(f"Rows with inconsistent column count: {inconsistent_rows}")
            
        except Exception as e:
            errors.append(f"CSV validation error: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_excel_content(self, content: bytes) -> Dict[str, List[str]]:
        """Validate Excel file content"""
        errors = []
        warnings = []
        
        try:
            import pandas as pd
            from io import BytesIO
            
            # Try to read Excel file
            excel_file = BytesIO(content)
            
            # Check if file can be opened
            try:
                sheets = pd.ExcelFile(excel_file).sheet_names
                if len(sheets) == 0:
                    errors.append("Excel file contains no sheets")
                elif len(sheets) > 1:
                    warnings.append(f"Excel file contains multiple sheets ({len(sheets)}), only first sheet will be processed")
                
                # Try to read first sheet
                df = pd.read_excel(excel_file, sheet_name=0)
                if df.empty:
                    errors.append("Excel sheet contains no data")
                
            except Exception as e:
                errors.append(f"Cannot read Excel file: {str(e)}")
        
        except ImportError:
            warnings.append("Excel validation skipped - pandas not available")
        except Exception as e:
            errors.append(f"Excel validation error: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_json_content(self, content: bytes) -> Dict[str, List[str]]:
        """Validate JSON file content"""
        errors = []
        warnings = []
        
        try:
            import json
            
            # Try to decode and parse JSON
            try:
                text_content = content.decode('utf-8')
                json_data = json.loads(text_content)
                
                # Check if JSON is empty
                if not json_data:
                    warnings.append("JSON file is empty or contains null data")
                
            except UnicodeDecodeError:
                errors.append("JSON file has invalid UTF-8 encoding")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON format: {str(e)}")
        
        except Exception as e:
            errors.append(f"JSON validation error: {str(e)}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def calculate_file_checksum(self, content: bytes, algorithm: str = 'md5') -> str:
        """
        Calculate checksum for file content
        
        Args:
            content: File content as bytes
            algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
            
        Returns:
            Hexadecimal checksum string
        """
        try:
            if algorithm == 'md5':
                return hashlib.md5(content).hexdigest()
            elif algorithm == 'sha1':
                return hashlib.sha1(content).hexdigest()
            elif algorithm == 'sha256':
                return hashlib.sha256(content).hexdigest()
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        except Exception as e:
            logger.error(f"Error calculating checksum: {e}")
            return ""

