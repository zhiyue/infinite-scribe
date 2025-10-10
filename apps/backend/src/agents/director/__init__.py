"""Director Agent !W"""

from src.agents.director.agent import DirectorAgent
from src.agents.registry import register_agent

# Explicitly register agent class for discovery reliability
register_agent("director", DirectorAgent)

__all__ = ["DirectorAgent"]
