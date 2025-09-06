from __future__ import annotations

from ..registry import register_agent
from .agent import OrchestratorAgent

register_agent("orchestrator", OrchestratorAgent)

__all__ = ["OrchestratorAgent"]

