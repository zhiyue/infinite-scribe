"""Agents service adapter for managing AI agents"""

from typing import Any

import structlog

from src.agents.launcher import AgentLauncher, AgentsLoadError

from ..types import ServiceStatus
from .base import BaseAdapter

logger = structlog.get_logger(__name__)


class AgentsAdapter(BaseAdapter):
    """Adapter for managing AI agents"""

    def __init__(self, config: dict[str, Any]):
        """Initialize the agents adapter"""
        super().__init__("agents", config)
        self._agent_names = config.get("agents")
        self._launcher: AgentLauncher | None = None
        self._loaded_agents: list[str] = []

    def load(self, agent_names: list[str] | None = None) -> None:
        """
        Load specified agents

        Args:
            agent_names: List of agent names to load. If None, loads default agents.
        """
        if agent_names:
            self._loaded_agents = agent_names
        else:
            # Default agents
            self._loaded_agents = ["worldsmith", "plotmaster", "director", "writer"]

        logger.info("Loaded agents", agents=self._loaded_agents)

    async def start(self) -> bool:
        """
        Start loaded agents

        Returns:
            bool: True if all agents started successfully
        """
        try:
            self.status = ServiceStatus.STARTING

            # Create AgentLauncher instance
            self._launcher = AgentLauncher()

            # Setup signal handlers
            self._launcher.setup_signal_handlers()

            # Use agent names from config if not loaded explicitly
            agents_to_load = self._loaded_agents if self._loaded_agents else self._agent_names

            # Load agents
            self._launcher.load_agents(agents_to_load)

            # Sync loaded agent names for consistent health reporting
            if not self._loaded_agents and self._launcher.agents:
                self._loaded_agents = list(self._launcher.agents.keys())

            # Start all agents
            await self._launcher.start_all()

            self.status = ServiceStatus.RUNNING
            logger.info("All agents started successfully")
            return True

        except Exception as e:
            logger.error("Failed to start agents", error=str(e))
            self.status = ServiceStatus.FAILED
            return False

    async def stop(self, timeout: int = 30) -> bool:
        """
        Stop all agents

        Args:
            timeout: Grace period in seconds for graceful shutdown

        Returns:
            bool: True if all agents stopped successfully
        """
        try:
            self.status = ServiceStatus.STOPPING

            if self._launcher:
                await self._launcher.stop_all()

            self.status = ServiceStatus.STOPPED
            logger.info("All agents stopped successfully")
            return True

        except Exception as e:
            logger.error("Failed to stop agents", error=str(e))
            self.status = ServiceStatus.FAILED
            return False

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on agents

        Returns:
            dict: Health check result with status and agent info
        """
        if not self._launcher:
            return {"status": "not_started", "agents": {}, "total_agents": 0}

        # Get agent status
        agent_status = {}
        # Fallback to launcher's agents if _loaded_agents not populated
        names = self._loaded_agents or list(self._launcher.agents.keys())
        for agent_name in names:
            if self._launcher.running:
                agent_status[agent_name] = "running"
            else:
                agent_status[agent_name] = "stopped"

        return {
            "status": "healthy" if self._launcher.running else "stopped",
            "agents": agent_status,
            "total_agents": len(self._launcher.agents) if self._launcher.agents else 0,
        }

    def get_loaded_agents(self) -> list[str]:
        """Get list of loaded agents"""
        return self._loaded_agents.copy()
