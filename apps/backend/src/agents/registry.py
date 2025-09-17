"""Agent registry for explicit mapping of agent id to classes.

Prefer using registry over pure reflection for reliability.
"""

from __future__ import annotations

from src.agents.agent_config import canonicalize_agent_id
from src.agents.base import BaseAgent

_REGISTRY: dict[str, type[BaseAgent]] = {}


def register_agent(agent_id: str, cls: type[BaseAgent]) -> None:
    """Register an agent class with validation.

    Args:
        agent_id: The agent identifier (will be canonicalized)
        cls: The agent class to register (must inherit from BaseAgent)

    Raises:
        ValueError: If cls doesn't inherit from BaseAgent
    """
    if not (isinstance(cls, type) and issubclass(cls, BaseAgent)):
        raise ValueError(f"Class {cls} must inherit from BaseAgent")
    cid = canonicalize_agent_id(agent_id)
    _REGISTRY[cid] = cls


def get_registered_agent(agent_id: str) -> type[BaseAgent] | None:
    return _REGISTRY.get(canonicalize_agent_id(agent_id))


def list_registered_agents() -> list[str]:
    return sorted(_REGISTRY.keys())
