"""Content Analyzer Agent package.

Registers the ContentAnalyzerAgent in the global registry for reliable loading.
"""

from ..registry import register_agent
from .agent import ContentAnalyzerAgent

register_agent("content_analyzer", ContentAnalyzerAgent)

__all__ = ["ContentAnalyzerAgent"]

