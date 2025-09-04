"""Director Agent !W"""

from ..registry import register_agent
from .agent import DirectorAgent

# Explicitly register agent class for discovery reliability
register_agent("director", DirectorAgent)

__all__ = ["DirectorAgent"]
