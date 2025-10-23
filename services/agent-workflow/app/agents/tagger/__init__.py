"""
TaggerAgent - Governance-focused classification tagging
"""
from .agent import TaggerAgent
from .models import Classification, ClassificationResult
from .config import TaggerConfig

__all__ = ['TaggerAgent', 'Classification', 'ClassificationResult', 'TaggerConfig']

