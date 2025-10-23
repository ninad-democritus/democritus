"""
Modular ProfilerAgent - Main package exports
"""
from .agent import ProfilerAgent
from .models import FileProfile, ColumnProfile
from .config import ProfilerConfig

__all__ = [
    'ProfilerAgent',
    'FileProfile',
    'ColumnProfile',
    'ProfilerConfig'
]

