"""Knowledge Updater Agent package.

Registers the KnowledgeUpdateAgent for reliable discovery.
"""

from src.agents.knowledge_updater.agent import KnowledgeUpdateAgent
from src.agents.registry import register_agent

register_agent("knowledge_updater", KnowledgeUpdateAgent)

__all__ = ["KnowledgeUpdateAgent"]
