"""
File Discovery Service for finding and matching files to entities
"""

import logging
import re
from typing import List, Dict, Optional
from difflib import SequenceMatcher

from ..infrastructure.minio_client_manager import MinioClientManager
from .models import FileInfo, EntityFileMatch

logger = logging.getLogger(__name__)


class FileDiscoveryService:
    """Service for discovering and matching files to entities"""
    
    def __init__(self):
        """Initialize the file discovery service"""
        self.minio_manager = MinioClientManager()
        
    async def discover_job_files(self, job_id: str, bucket_name: str = "uploads") -> List[FileInfo]:
        """
        Discover all files for a specific job
        
        Args:
            job_id: The job identifier
            bucket_name: The bucket to search in
            
        Returns:
            List of FileInfo objects for discovered files
        """
        logger.info(f"Discovering files for job {job_id} in bucket {bucket_name}")
        
        try:
            # Ensure bucket exists
            if not MinioClientManager.ensure_bucket_exists(bucket_name):
                raise Exception(f"Bucket {bucket_name} does not exist and could not be created")
            
            # List objects with job prefix
            prefix = f"jobs/{job_id}/"
            objects = MinioClientManager.list_objects(bucket_name, prefix=prefix, recursive=True)
            
            # Convert to FileInfo objects and filter supported formats
            files = []
            for obj in objects:
                file_info = FileInfo(
                    name=obj["object_name"],
                    bucket=bucket_name,
                    size=obj["size"],
                    last_modified=obj["last_modified"],
                    content_type=obj.get("content_type"),
                    etag=obj.get("etag")
                )
                
                # Only include supported file formats
                if file_info.is_supported_format:
                    files.append(file_info)
                else:
                    logger.debug(f"Skipping unsupported file format: {file_info.file_name}")
            
            logger.info(f"Discovered {len(files)} supported files for job {job_id}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to discover files for job {job_id}: {str(e)}")
            raise
    
    async def match_files_to_entities(self, files: List[FileInfo], entities: List[Dict]) -> Dict[str, EntityFileMatch]:
        """
        Match discovered files to entities based on name similarity
        
        Args:
            files: List of discovered files
            entities: List of entity definitions
            
        Returns:
            Dictionary mapping entity IDs to EntityFileMatch objects
        """
        logger.info(f"Matching {len(files)} files to {len(entities)} entities")
        
        matches = {}
        
        for entity in entities:
            entity_id = entity.get('id', entity.get('name', ''))
            entity_name = entity.get('name', entity_id)
            
            # Find matching files for this entity
            matched_files, confidence_scores = await self._find_matching_files(entity, files)
            
            if matched_files:
                matches[entity_id] = EntityFileMatch(
                    entity_name=entity_name,
                    entity_id=entity_id,
                    matched_files=matched_files,
                    confidence_scores=confidence_scores
                )
                logger.info(f"Entity '{entity_name}' matched with {len(matched_files)} files")
            else:
                logger.warning(f"No files matched for entity '{entity_name}'")
        
        return matches
    
    async def _find_matching_files(self, entity: Dict, files: List[FileInfo]) -> tuple[List[FileInfo], Dict[str, float]]:
        """
        Find files that match a specific entity
        
        Args:
            entity: Entity definition
            files: List of available files
            
        Returns:
            Tuple of (matched_files, confidence_scores)
        """
        entity_name = entity.get('name', '').lower()
        matched_files = []
        confidence_scores = {}
        
        for file_info in files:
            confidence = self._calculate_match_confidence(entity_name, file_info.file_name)
            
            # Consider it a match if confidence is above threshold
            if confidence > 0.3:  # 30% similarity threshold
                matched_files.append(file_info)
                confidence_scores[file_info.file_name] = confidence
        
        # Sort by confidence (highest first)
        matched_files.sort(key=lambda f: confidence_scores[f.file_name], reverse=True)
        
        return matched_files, confidence_scores
    
    def _calculate_match_confidence(self, entity_name: str, file_name: str) -> float:
        """
        Calculate confidence score for entity-file matching
        
        Args:
            entity_name: Name of the entity
            file_name: Name of the file
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not entity_name or not file_name:
            return 0.0
        
        # Normalize names for comparison
        entity_clean = self._normalize_name(entity_name)
        file_clean = self._normalize_name(file_name)
        
        # Exact match (highest confidence)
        if entity_clean == file_clean:
            return 1.0
        
        # Check if entity name is contained in file name
        if entity_clean in file_clean:
            return 0.9
        
        # Check if file name is contained in entity name
        if file_clean in entity_clean:
            return 0.8
        
        # Use sequence matching for similarity
        similarity = SequenceMatcher(None, entity_clean, file_clean).ratio()
        
        # Boost score if they share common words
        entity_words = set(entity_clean.split('_'))
        file_words = set(file_clean.split('_'))
        common_words = entity_words.intersection(file_words)
        
        if common_words:
            word_bonus = len(common_words) / max(len(entity_words), len(file_words))
            similarity = min(1.0, similarity + (word_bonus * 0.3))
        
        return similarity
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize a name for comparison
        
        Args:
            name: Original name
            
        Returns:
            Normalized name
        """
        # Remove file extension
        name = re.sub(r'\.[^.]+$', '', name)
        
        # Convert to lowercase
        name = name.lower()
        
        # Replace common separators with underscores
        name = re.sub(r'[-\s\.]+', '_', name)
        
        # Remove special characters
        name = re.sub(r'[^a-z0-9_]', '', name)
        
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        return name
    
    async def validate_file_accessibility(self, files: List[FileInfo]) -> List[FileInfo]:
        """
        Validate that files are accessible and readable
        
        Args:
            files: List of files to validate
            
        Returns:
            List of accessible files
        """
        logger.info(f"Validating accessibility of {len(files)} files")
        
        accessible_files = []
        
        for file_info in files:
            try:
                # Check if object exists and is accessible
                if MinioClientManager.object_exists(file_info.bucket, file_info.name):
                    # Get updated object info
                    obj_info = MinioClientManager.get_object_info(file_info.bucket, file_info.name)
                    if obj_info:
                        # Update file info with latest metadata
                        file_info.metadata = obj_info.get("metadata", {})
                        accessible_files.append(file_info)
                    else:
                        logger.warning(f"Could not get info for file: {file_info}")
                else:
                    logger.warning(f"File not accessible: {file_info}")
                    
            except Exception as e:
                logger.error(f"Error validating file {file_info}: {str(e)}")
        
        logger.info(f"Validated {len(accessible_files)} accessible files out of {len(files)}")
        return accessible_files
    
    async def get_file_statistics(self, files: List[FileInfo]) -> Dict[str, any]:
        """
        Get statistics about discovered files
        
        Args:
            files: List of files to analyze
            
        Returns:
            Dictionary with file statistics
        """
        if not files:
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "file_types": {},
                "largest_file": None,
                "smallest_file": None
            }
        
        total_size = sum(f.size for f in files)
        file_types = {}
        
        for file_info in files:
            ext = file_info.file_extension
            file_types[ext] = file_types.get(ext, 0) + 1
        
        largest_file = max(files, key=lambda f: f.size)
        smallest_file = min(files, key=lambda f: f.size)
        
        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "largest_file": {
                "name": largest_file.file_name,
                "size_bytes": largest_file.size,
                "size_mb": round(largest_file.size / (1024 * 1024), 2)
            },
            "smallest_file": {
                "name": smallest_file.file_name,
                "size_bytes": smallest_file.size,
                "size_mb": round(smallest_file.size / (1024 * 1024), 2)
            }
        }

