"""
Rule-based relationship detection
"""
from .fk_matcher import ForeignKeyMatcher
from .common_column_matcher import CommonColumnMatcher
from .name_similarity import NameSimilarityCalculator

__all__ = [
    'ForeignKeyMatcher',
    'CommonColumnMatcher',
    'NameSimilarityCalculator'
]

