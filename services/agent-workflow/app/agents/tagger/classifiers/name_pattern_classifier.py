"""
Name pattern-based classifier
Matches canonical names and synonyms against classification keywords
"""
from typing import List, Dict, Any
import re
import logging
from .base import BaseClassifier
from ..models import Classification
from ..taxonomy import CLASSIFICATION_KEYWORDS, CLASSIFICATION_PATTERNS

logger = logging.getLogger(__name__)


class NamePatternClassifier(BaseClassifier):
    """Classifies columns based on name patterns"""
    
    def __init__(self, config):
        super().__init__(config)
        # Compile regex patterns
        self.compiled_patterns = {}
        for tag, patterns in CLASSIFICATION_PATTERNS.items():
            self.compiled_patterns[tag] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def classify_column(self, column: Dict[str, Any], entity: Dict[str, Any]) -> List[Classification]:
        """
        Classify column based on name patterns
        
        Args:
            column: Column metadata including canonical_name and synonyms
            entity: Parent entity for context
            
        Returns:
            List of Classification objects
        """
        canonical_name = column.get('canonical_name', '').lower()
        synonyms = [s.lower() for s in column.get('synonyms', [])]
        alignment_confidence = column.get('alignment_confidence', 1.0)
        
        # Collect all names to check
        all_names = [canonical_name] + synonyms
        
        classifications = []
        
        # Check keyword-based classifications
        for tag, keywords in CLASSIFICATION_KEYWORDS.items():
            match_score = self._calculate_keyword_match(all_names, keywords)
            
            if match_score > 0.0:
                # Base confidence from match score
                base_confidence = 0.70 + (match_score * 0.20)  # 0.70-0.90 range
                
                # Adjust based on alignment confidence
                # If alignment is uncertain, reduce confidence
                if alignment_confidence < self.config.alignment_confidence_threshold:
                    penalty = (self.config.alignment_confidence_threshold - alignment_confidence) * 0.25
                    base_confidence *= (1.0 - penalty)
                    logger.debug(f"Reduced {tag} confidence due to low alignment: {alignment_confidence:.2f}")
                
                final_confidence = max(0.5, min(0.92, base_confidence))
                
                # Only add if above threshold
                if final_confidence >= self.config.min_classification_confidence:
                    classifications.append(Classification(
                        tag=tag,
                        confidence=final_confidence,
                        source='name_pattern',
                        upstream_factors={
                            'canonical_name': column.get('canonical_name'),
                            'match_score': match_score,
                            'alignment_confidence': alignment_confidence
                        }
                    ))
                    
                    logger.info(f"Pattern matched {column.get('name')} to {tag} "
                               f"(confidence={final_confidence:.2f}, match={match_score:.2f})")
        
        # Check regex pattern-based classifications
        pattern_classifications = self._check_regex_patterns(all_names, alignment_confidence)
        classifications.extend(pattern_classifications)
        
        return classifications
    
    def _calculate_keyword_match(self, names: List[str], keywords: List[str]) -> float:
        """
        Calculate match score between names and keywords
        
        Returns:
            Score between 0.0 and 1.0
        """
        if not names or not keywords:
            return 0.0
        
        max_score = 0.0
        
        for name in names:
            for keyword in keywords:
                keyword_lower = keyword.lower().replace('-', '_').replace(' ', '_')
                name_clean = name.replace('-', '_').replace(' ', '_')
                
                # Exact match
                if keyword_lower == name_clean:
                    return 1.0
                
                # Contains match
                if keyword_lower in name_clean:
                    score = 0.9
                    max_score = max(max_score, score)
                
                # Starts/ends with match
                if name_clean.startswith(keyword_lower) or name_clean.endswith(keyword_lower):
                    score = 0.85
                    max_score = max(max_score, score)
                
                # Partial word match (fuzzy)
                if self._fuzzy_match(name_clean, keyword_lower):
                    score = 0.7
                    max_score = max(max_score, score)
        
        return max_score
    
    def _fuzzy_match(self, text: str, keyword: str) -> bool:
        """Simple fuzzy matching"""
        # Check if keyword appears as part of underscore-separated words
        words = text.split('_')
        for word in words:
            if keyword in word or word in keyword:
                return True
        return False
    
    def _check_regex_patterns(self, names: List[str], alignment_confidence: float) -> List[Classification]:
        """Check regex pattern matches"""
        classifications = []
        
        for tag, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for name in names:
                    if pattern.match(name):
                        # Pattern matches have slightly lower base confidence
                        base_confidence = 0.75
                        
                        # Adjust for alignment confidence
                        if alignment_confidence < self.config.alignment_confidence_threshold:
                            penalty = (self.config.alignment_confidence_threshold - alignment_confidence) * 0.2
                            base_confidence *= (1.0 - penalty)
                        
                        final_confidence = max(0.5, min(0.85, base_confidence))
                        
                        if final_confidence >= self.config.min_classification_confidence:
                            classifications.append(Classification(
                                tag=tag,
                                confidence=final_confidence,
                                source='regex_pattern',
                                upstream_factors={
                                    'pattern': pattern.pattern,
                                    'matched_name': name,
                                    'alignment_confidence': alignment_confidence
                                }
                            ))
                            
                            logger.info(f"Regex pattern matched '{name}' to {tag} "
                                       f"(confidence={final_confidence:.2f})")
                        break  # Only match once per tag
        
        return classifications

