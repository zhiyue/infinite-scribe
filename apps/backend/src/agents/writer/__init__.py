"""Writer Agent !W"""

from src.agents.registry import register_agent
from src.agents.writer.agent import WriterAgent

# Explicitly register agent class for discovery reliability
register_agent("writer", WriterAgent)

__all__ = ["WriterAgent"]
