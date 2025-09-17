"""Content Analyzer Agent package.

Registers the ContentAnalyzerAgent in the global registry for reliable loading.
"""

from src.agents.content_analyzer.agent import ContentAnalyzerAgent
from src.agents.registry import register_agent

register_agent("content_analyzer", ContentAnalyzerAgent)

__all__ = ["ContentAnalyzerAgent"]
