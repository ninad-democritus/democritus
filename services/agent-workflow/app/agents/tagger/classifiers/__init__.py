"""
Classification assignment components
"""
from .base import BaseClassifier
from .semantic_type_classifier import SemanticTypeClassifier
from .name_pattern_classifier import NamePatternClassifier
from .statistical_classifier import StatisticalClassifier
from .context_classifier import ContextClassifier
from .merger import ClassificationMerger

__all__ = [
    'BaseClassifier',
    'SemanticTypeClassifier',
    'NamePatternClassifier',
    'StatisticalClassifier',
    'ContextClassifier',
    'ClassificationMerger'
]

