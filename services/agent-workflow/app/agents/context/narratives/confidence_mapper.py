"""
Confidence to natural language mapper
"""
from typing import Dict, Tuple


class ConfidenceMapper:
    """Maps confidence scores to natural language qualifiers"""
    
    CONFIDENCE_LANGUAGE = {
        'high': {
            'qualifiers': ['confirmed', 'established', 'verified', 'definite'],
            'phrases': ['has been confirmed', 'is established', 'clearly indicates']
        },
        'medium': {
            'qualifiers': ['likely', 'probable', 'strongly indicated', 'appears to be'],
            'phrases': ['is highly likely', 'strongly suggests', 'appears to indicate']
        },
        'low': {
            'qualifiers': ['possible', 'tentative', 'preliminary', 'potential'],
            'phrases': ['may indicate', 'suggests possibility', 'tentatively identified as']
        }
    }
    
    def __init__(self, thresholds: Dict[str, Tuple[float, float]] = None):
        """
        Initialize confidence mapper
        
        Args:
            thresholds: Dict mapping level names to (min, max) confidence ranges
        """
        self.thresholds = thresholds or {
            'high': (0.85, 1.0),
            'medium': (0.70, 0.85),
            'low': (0.0, 0.70)
        }
    
    def get_level(self, confidence: float) -> str:
        """
        Get confidence level name
        
        Args:
            confidence: Confidence score (0.0 - 1.0)
            
        Returns:
            Level name ('high', 'medium', 'low')
        """
        for level, (min_conf, max_conf) in self.thresholds.items():
            if min_conf <= confidence <= max_conf:
                return level
        return 'low'
    
    def get_qualifier(self, confidence: float, index: int = 0) -> str:
        """
        Get a confidence qualifier word
        
        Args:
            confidence: Confidence score
            index: Index of qualifier to use (for variety)
            
        Returns:
            Qualifier word
        """
        level = self.get_level(confidence)
        qualifiers = self.CONFIDENCE_LANGUAGE[level]['qualifiers']
        return qualifiers[index % len(qualifiers)]
    
    def get_phrase(self, confidence: float, index: int = 0) -> str:
        """
        Get a confidence phrase
        
        Args:
            confidence: Confidence score
            index: Index of phrase to use (for variety)
            
        Returns:
            Confidence phrase
        """
        level = self.get_level(confidence)
        phrases = self.CONFIDENCE_LANGUAGE[level]['phrases']
        return phrases[index % len(phrases)]
    
    def should_mention_confidence(self, confidence: float) -> bool:
        """
        Determine if confidence should be explicitly mentioned
        
        Args:
            confidence: Confidence score
            
        Returns:
            True if confidence is low/medium and should be mentioned
        """
        return confidence < 0.85

