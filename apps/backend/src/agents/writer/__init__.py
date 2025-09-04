"""Writer Agent !W"""

from ..registry import register_agent
from .agent import WriterAgent

# Explicitly register agent class for discovery reliability
register_agent("writer", WriterAgent)

__all__ = ["WriterAgent"]
