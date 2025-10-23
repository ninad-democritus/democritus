"""
Classification merger
Merges and deduplicates classifications from multiple sources
"""
from typing import List, Dict
import logging
from ..models import Classification
from ..taxonomy.definitions import get_mutually_exclusive_tags

logger = logging.getLogger(__name__)


class ClassificationMerger:
    """Merges classifications from multiple classifiers"""
    
    def __init__(self, config):
        self.config = config
        self.mutual_exclusions = get_mutually_exclusive_tags()
    
    def merge_classifications(self, 
                            classifications_by_source: Dict[str, List[Classification]]) -> List[Classification]:
        """
        Merge classifications from multiple sources
        
        Args:
            classifications_by_source: Dict mapping source name to list of classifications
            
        Returns:
            Merged and deduplicated list of classifications
        """
        # Collect all classifications
        all_classifications = []
        for source, classifications in classifications_by_source.items():
            all_classifications.extend(classifications)
        
        # Deduplicate by tag (keep highest confidence)
        tag_to_classification = {}
        for classification in all_classifications:
            tag = classification.tag
            if tag not in tag_to_classification:
                tag_to_classification[tag] = classification
            else:
                # Keep the one with higher confidence
                existing = tag_to_classification[tag]
                if classification.confidence > existing.confidence:
                    tag_to_classification[tag] = classification
                    logger.debug(f"Replaced {tag} classification with higher confidence: "
                               f"{classification.confidence:.2f} > {existing.confidence:.2f}")
        
        # Enforce mutual exclusivity
        final_classifications = self._enforce_mutual_exclusivity(
            list(tag_to_classification.values())
        )
        
        return final_classifications
    
    def _enforce_mutual_exclusivity(self, classifications: List[Classification]) -> List[Classification]:
        """
        Enforce mutually exclusive constraints
        
        If two mutually exclusive tags are present, keep the one with higher confidence
        """
        # Build tag to classification mapping
        tag_map = {c.tag: c for c in classifications}
        
        # Check for mutual exclusion conflicts
        to_remove = set()
        for classification in classifications:
            if classification.tag in to_remove:
                continue
            
            # Check if this tag has exclusions
            exclusive_tags = self.mutual_exclusions.get(classification.tag, [])
            for exclusive_tag in exclusive_tags:
                if exclusive_tag in tag_map:
                    # Conflict found - keep higher confidence
                    other = tag_map[exclusive_tag]
                    if classification.confidence >= other.confidence:
                        to_remove.add(exclusive_tag)
                        logger.info(f"Removed {exclusive_tag} (confidence={other.confidence:.2f}) "
                                   f"in favor of {classification.tag} (confidence={classification.confidence:.2f}) "
                                   f"due to mutual exclusivity")
                    else:
                        to_remove.add(classification.tag)
                        logger.info(f"Removed {classification.tag} (confidence={classification.confidence:.2f}) "
                                   f"in favor of {exclusive_tag} (confidence={other.confidence:.2f}) "
                                   f"due to mutual exclusivity")
                        break
        
        # Filter out removed classifications
        return [c for c in classifications if c.tag not in to_remove]

