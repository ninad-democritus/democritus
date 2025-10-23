"""
Narrative generation - LLM-powered and template-based description generators
"""
from .generator import NarrativeGenerator
from .templates import PromptTemplates
from .confidence_mapper import ConfidenceMapper

__all__ = ['NarrativeGenerator', 'PromptTemplates', 'ConfidenceMapper']

