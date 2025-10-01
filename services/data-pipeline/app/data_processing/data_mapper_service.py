"""
Data Mapper Service for mapping entities to files and data relationships
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher

from ..file_operations.models import FileInfo, EntityFileMatch

logger = logging.getLogger(__name__)


class DataMapperService:
    """Service for mapping entities to files and managing data relationships"""
    
    def __init__(self):
        """Initialize the data mapper service"""
        pass
    
    async def map_entities_to_files(self, entities: List[Dict[str, Any]], files: List[FileInfo]) -> Dict[str, EntityFileMatch]:
        """
        Map entities to their corresponding files
        
        Args:
            entities: List of entity definitions
            files: List of available files
            
        Returns:
            Dictionary mapping entity IDs to EntityFileMatch objects
        """
        logger.info(f"Mapping {len(entities)} entities to {len(files)} files")
        
        mappings = {}
        
        for entity in entities:
            entity_id = entity.get('id', entity.get('name', ''))
            entity_name = entity.get('name', entity_id)
            
            # Find matching files for this entity
            matched_files, confidence_scores = await self.fuzzy_match_entity_files(entity, files)
            
            if matched_files:
                mappings[entity_id] = EntityFileMatch(
                    entity_name=entity_name,
                    entity_id=entity_id,
                    matched_files=matched_files,
                    confidence_scores=confidence_scores
                )
                logger.info(f"Entity '{entity_name}' mapped to {len(matched_files)} files")
            else:
                logger.warning(f"No files found for entity '{entity_name}'")
        
        return mappings
    
    async def fuzzy_match_entity_files(self, entity: Dict[str, Any], files: List[FileInfo]) -> Tuple[List[FileInfo], Dict[str, float]]:
        """
        Find files that match an entity using fuzzy matching
        
        Args:
            entity: Entity definition
            files: List of available files
            
        Returns:
            Tuple of (matched_files, confidence_scores)
        """
        entity_name = entity.get('name', '').lower()
        entity_id = entity.get('id', '').lower()
        
        matched_files = []
        confidence_scores = {}
        
        # Get alternative names for the entity
        alternative_names = self._get_entity_alternative_names(entity)
        
        for file_info in files:
            # Calculate confidence using multiple strategies
            confidence = self._calculate_comprehensive_match_confidence(
                entity, file_info, alternative_names
            )
            
            # Consider it a match if confidence is above threshold
            if confidence > 0.3:  # 30% similarity threshold
                matched_files.append(file_info)
                confidence_scores[file_info.file_name] = confidence
        
        # Sort by confidence (highest first)
        matched_files.sort(key=lambda f: confidence_scores[f.file_name], reverse=True)
        
        return matched_files, confidence_scores
    
    def calculate_match_confidence(self, entity_name: str, file_name: str) -> float:
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
    
    def _get_entity_alternative_names(self, entity: Dict[str, Any]) -> List[str]:
        """Get alternative names for an entity"""
        alternatives = []
        
        # Primary name and ID
        name = entity.get('name', '')
        entity_id = entity.get('id', '')
        
        if name:
            alternatives.append(name.lower())
        if entity_id and entity_id != name:
            alternatives.append(entity_id.lower())
        
        # Add plural/singular variations
        if name:
            if name.endswith('s'):
                alternatives.append(name[:-1].lower())  # Remove 's' for singular
            else:
                alternatives.append((name + 's').lower())  # Add 's' for plural
        
        # Add common variations
        for alt in alternatives.copy():
            # Replace underscores with spaces and vice versa
            alternatives.append(alt.replace('_', ' '))
            alternatives.append(alt.replace(' ', '_'))
            alternatives.append(alt.replace('-', '_'))
            alternatives.append(alt.replace('_', '-'))
        
        # Remove duplicates and empty strings
        alternatives = list(set(alt for alt in alternatives if alt))
        
        return alternatives
    
    def _calculate_comprehensive_match_confidence(self, entity: Dict[str, Any], file_info: FileInfo, alternative_names: List[str]) -> float:
        """Calculate comprehensive match confidence using multiple strategies"""
        max_confidence = 0.0
        
        # Strategy 1: Direct name matching
        entity_name = entity.get('name', '')
        if entity_name:
            confidence = self.calculate_match_confidence(entity_name, file_info.file_name)
            max_confidence = max(max_confidence, confidence)
        
        # Strategy 2: Alternative name matching
        for alt_name in alternative_names:
            confidence = self.calculate_match_confidence(alt_name, file_info.file_name)
            max_confidence = max(max_confidence, confidence)
        
        # Strategy 3: Column-based matching
        column_confidence = self._calculate_column_based_confidence(entity, file_info)
        max_confidence = max(max_confidence, column_confidence * 0.8)  # Weight column matching less
        
        # Strategy 4: Pattern-based matching
        pattern_confidence = self._calculate_pattern_based_confidence(entity, file_info)
        max_confidence = max(max_confidence, pattern_confidence * 0.6)  # Weight pattern matching less
        
        return max_confidence
    
    def _calculate_column_based_confidence(self, entity: Dict[str, Any], file_info: FileInfo) -> float:
        """Calculate confidence based on expected columns in the entity"""
        # This would require reading the file to get column names
        # For now, return 0.0 as this is computationally expensive
        # In the future, we could cache file schemas or use metadata
        return 0.0
    
    def _calculate_pattern_based_confidence(self, entity: Dict[str, Any], file_info: FileInfo) -> float:
        """Calculate confidence based on file naming patterns"""
        entity_name = entity.get('name', '').lower()
        file_name = file_info.file_name.lower()
        
        confidence = 0.0
        
        # Check for common patterns
        patterns = [
            f"{entity_name}_data",
            f"{entity_name}_export",
            f"{entity_name}_dump",
            f"data_{entity_name}",
            f"export_{entity_name}",
            f"{entity_name}_table",
            f"table_{entity_name}"
        ]
        
        for pattern in patterns:
            if pattern in file_name:
                confidence = max(confidence, 0.7)
        
        # Check for date patterns that might indicate data exports
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'\d{8}',              # YYYYMMDD
            r'\d{6}'               # YYMMDD
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, file_name):
                confidence = max(confidence, 0.4)
        
        return confidence
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison"""
        if not name:
            return ""
        
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
    
    async def validate_entity_file_mappings(self, mappings: Dict[str, EntityFileMatch]) -> Dict[str, Any]:
        """
        Validate entity-file mappings and provide recommendations
        
        Args:
            mappings: Dictionary of entity mappings
            
        Returns:
            Dictionary with validation results and recommendations
        """
        logger.info("Validating entity-file mappings")
        
        validation_results = {
            "total_entities": len(mappings),
            "mapped_entities": 0,
            "unmapped_entities": [],
            "low_confidence_mappings": [],
            "multiple_file_mappings": [],
            "recommendations": []
        }
        
        for entity_id, mapping in mappings.items():
            if mapping.matched_files:
                validation_results["mapped_entities"] += 1
                
                # Check for low confidence mappings
                avg_confidence = mapping.get_average_confidence()
                if avg_confidence < 0.5:
                    validation_results["low_confidence_mappings"].append({
                        "entity_id": entity_id,
                        "entity_name": mapping.entity_name,
                        "confidence": avg_confidence,
                        "file_count": len(mapping.matched_files)
                    })
                
                # Check for multiple file mappings
                if len(mapping.matched_files) > 1:
                    validation_results["multiple_file_mappings"].append({
                        "entity_id": entity_id,
                        "entity_name": mapping.entity_name,
                        "file_count": len(mapping.matched_files),
                        "files": [f.file_name for f in mapping.matched_files]
                    })
            else:
                validation_results["unmapped_entities"].append({
                    "entity_id": entity_id,
                    "entity_name": mapping.entity_name
                })
        
        # Generate recommendations
        if validation_results["unmapped_entities"]:
            validation_results["recommendations"].append(
                f"Consider reviewing {len(validation_results['unmapped_entities'])} unmapped entities"
            )
        
        if validation_results["low_confidence_mappings"]:
            validation_results["recommendations"].append(
                f"Review {len(validation_results['low_confidence_mappings'])} low-confidence mappings"
            )
        
        if validation_results["multiple_file_mappings"]:
            validation_results["recommendations"].append(
                f"Resolve {len(validation_results['multiple_file_mappings'])} entities with multiple file matches"
            )
        
        logger.info(f"Mapping validation completed: {validation_results['mapped_entities']}/{validation_results['total_entities']} entities mapped")
        
        return validation_results
    
    async def suggest_entity_file_mappings(self, unmapped_entities: List[Dict[str, Any]], unmatched_files: List[FileInfo]) -> List[Dict[str, Any]]:
        """
        Suggest possible mappings for unmapped entities
        
        Args:
            unmapped_entities: List of entities without file mappings
            unmatched_files: List of files not matched to any entity
            
        Returns:
            List of mapping suggestions
        """
        logger.info(f"Generating mapping suggestions for {len(unmapped_entities)} entities and {len(unmatched_files)} files")
        
        suggestions = []
        
        for entity in unmapped_entities:
            entity_name = entity.get('name', '')
            entity_id = entity.get('id', entity_name)
            
            # Find potential matches among unmatched files
            potential_matches = []
            
            for file_info in unmatched_files:
                confidence = self.calculate_match_confidence(entity_name, file_info.file_name)
                if confidence > 0.2:  # Lower threshold for suggestions
                    potential_matches.append({
                        "file_info": file_info,
                        "confidence": confidence
                    })
            
            # Sort by confidence
            potential_matches.sort(key=lambda x: x["confidence"], reverse=True)
            
            if potential_matches:
                suggestions.append({
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                    "suggested_files": potential_matches[:3],  # Top 3 suggestions
                    "suggestion_reason": "Name similarity analysis"
                })
        
        logger.info(f"Generated {len(suggestions)} mapping suggestions")
        return suggestions
    
    def get_mapping_statistics(self, mappings: Dict[str, EntityFileMatch]) -> Dict[str, Any]:
        """
        Get statistics about entity-file mappings
        
        Args:
            mappings: Dictionary of entity mappings
            
        Returns:
            Dictionary with mapping statistics
        """
        try:
            total_entities = len(mappings)
            mapped_entities = sum(1 for m in mappings.values() if m.matched_files)
            total_files = sum(len(m.matched_files) for m in mappings.values())
            
            confidence_scores = []
            for mapping in mappings.values():
                if mapping.matched_files:
                    confidence_scores.extend(mapping.confidence_scores.values())
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            return {
                "total_entities": total_entities,
                "mapped_entities": mapped_entities,
                "unmapped_entities": total_entities - mapped_entities,
                "mapping_rate": (mapped_entities / total_entities) * 100 if total_entities > 0 else 0,
                "total_matched_files": total_files,
                "average_confidence": round(avg_confidence, 3),
                "confidence_distribution": {
                    "high_confidence": len([c for c in confidence_scores if c >= 0.8]),
                    "medium_confidence": len([c for c in confidence_scores if 0.5 <= c < 0.8]),
                    "low_confidence": len([c for c in confidence_scores if c < 0.5])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate mapping statistics: {str(e)}")
            return {}

