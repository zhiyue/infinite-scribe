from __future__ import annotations

from src.agents.orchestrator.agent import OrchestratorAgent
from src.agents.registry import register_agent

register_agent("orchestrator", OrchestratorAgent)

__all__ = ["OrchestratorAgent"]
