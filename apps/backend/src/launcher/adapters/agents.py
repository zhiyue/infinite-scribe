"""Agents service adapter for managing AI agents"""

from typing import Any, TypedDict

from ..types import ServiceStatus


class AgentsStatus(TypedDict):
    adapter: str
    agents: dict[str, str]


class AgentsAdapter:
    """Adapter for managing AI agents"""

    def __init__(self):
        """Initialize the agents adapter"""
        self._launcher = None  # Will reuse apps/backend/src/agents/launcher.AgentLauncher
        self._agents: dict[str, Any] = {}
        self._status: ServiceStatus = ServiceStatus.STOPPED
        self._loaded_agents: list[str] = []

    def load(self, agent_names: list[str] | None = None) -> None:
        """
        Load specified agents

        Args:
            agent_names: List of agent names to load. If None, loads all available agents.
        """
        # TODO: Implement agent loading logic
        # Will integrate with existing AgentLauncher
        if agent_names:
            self._loaded_agents = agent_names
        else:
            # Default agents
            self._loaded_agents = ["worldsmith", "plotmaster", "director", "writer"]

    async def start(self) -> bool:
        """
        Start loaded agents

        Returns:
            bool: True if all agents started successfully
        """
        self._status = ServiceStatus.STARTING

        # TODO: Implement agent startup logic
        # Will use existing AgentLauncher.start() method

        self._status = ServiceStatus.RUNNING
        return True

    async def stop(self, grace: int = 10) -> bool:
        """
        Stop all agents

        Args:
            grace: Grace period in seconds for graceful shutdown

        Returns:
            bool: True if all agents stopped successfully
        """
        self._status = ServiceStatus.STOPPING

        # TODO: Implement agent shutdown logic
        # Will use existing AgentLauncher.stop() method

        self._status = ServiceStatus.STOPPED
        return True

    def status(self) -> AgentsStatus:
        """
        Get status of all agents

        Returns:
            Dict mapping agent names to their status
        """
        agents: dict[str, str] = {}
        status_dict: AgentsStatus = {"adapter": self._status.value, "agents": agents}

        for agent_name in self._loaded_agents:
            # TODO: Get actual agent status
            agents[agent_name] = "running"

        return status_dict

    def get_loaded_agents(self) -> list[str]:
        """Get list of loaded agents"""
        return self._loaded_agents.copy()
