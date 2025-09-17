"""Knowledge Updater Agent package.

Registers the KnowledgeUpdateAgent for reliable discovery.
"""

from ..registry import register_agent
from .agent import KnowledgeUpdateAgent

register_agent("knowledge_updater", KnowledgeUpdateAgent)

__all__ = ["KnowledgeUpdateAgent"]

