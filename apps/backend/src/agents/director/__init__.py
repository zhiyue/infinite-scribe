"""Director Agent !W"""

from src.agents.registry import register_agent
from src.agents.director.agent import DirectorAgent

# Explicitly register agent class for discovery reliability
register_agent("director", DirectorAgent)

__all__ = ["DirectorAgent"]
