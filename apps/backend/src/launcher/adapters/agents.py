"""Agents service adapter for managing AI agents"""

import asyncio
from time import monotonic
from typing import Any

import structlog

from src.agents.launcher import AgentLauncher

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
        # When True, agent signal handlers are disabled (managed by external orchestrator)
        self._disable_signal_handlers = config.get("disable_signal_handlers", False)
        # Background task for launcher.start_all()
        self._task: asyncio.Task | None = None
        # Optional readiness wait (seconds). 0 or None means no wait.
        # Prefer explicit ready_timeout; fall back to startup_timeout if provided.
        rt = config.get("ready_timeout")
        if rt is None:
            rt = config.get("startup_timeout", 0)
        try:
            self._ready_timeout: float = float(rt) if rt is not None else 0.0
        except Exception:
            self._ready_timeout = 0.0

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
        Start loaded agents in background (non-blocking).

        Returns:
            bool: True if startup initiated successfully, False on early failure
        """
        # If already running, don't double-start
        if self.status == ServiceStatus.RUNNING:
            logger.info("Agents adapter is already running; skip start")
            return False

        try:
            self.status = ServiceStatus.STARTING

            # Create AgentLauncher instance
            self._launcher = AgentLauncher()

            # Setup signal handlers (disable if managed by external orchestrator)
            enable_signal_handlers = not self._disable_signal_handlers
            self._launcher.setup_signal_handlers(enable=enable_signal_handlers)

            if self._disable_signal_handlers:
                logger.info("Agent signal handlers disabled - managed by external orchestrator")

            # Use agent names from config if not loaded explicitly
            agents_to_load = self._loaded_agents if self._loaded_agents else self._agent_names

            # Load agents into launcher
            self._launcher.load_agents(agents_to_load)

            # Sync loaded agent names for consistent health reporting
            if not self._loaded_agents and self._launcher.agents:
                self._loaded_agents = list(self._launcher.agents.keys())

            # Start all agents in background
            self._task = asyncio.create_task(self._launcher.start_all())

            # Yield once to let the background task actually call start_all (important for tests and fast-fail)
            await asyncio.sleep(0)

            # If task already failed synchronously (e.g., injected failure), surface it now
            if self._task.done():
                exc = self._task.exception()
                if exc is not None:
                    logger.error("Agents startup failed immediately", error=str(exc))
                    self.status = ServiceStatus.FAILED
                    return False

            # Optional minimal readiness wait (non-fatal on timeout)
            if self._ready_timeout and self._ready_timeout > 0:
                ready = await self._wait_until_ready(self._ready_timeout)
                if not ready:
                    logger.warning(
                        "Agents not fully ready within timeout",
                        timeout=self._ready_timeout,
                        loaded_agents=self._loaded_agents,
                    )

            self.status = ServiceStatus.RUNNING
            logger.info("Agents startup initiated (background)")
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

            # Ensure background task completes
            if self._task is not None:
                try:
                    await asyncio.wait_for(self._task, timeout=timeout)
                except TimeoutError:
                    logger.warning("Agents background task did not finish within grace period")
                finally:
                    self._task = None

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
        agent_status: dict[str, Any] = {}
        # Fallback to launcher's agents if _loaded_agents not populated
        names = self._loaded_agents or list(self._launcher.agents.keys())
        for agent_name in names:
            if self._launcher.running:
                agent_status[agent_name] = "running"
            else:
                agent_status[agent_name] = "stopped"

        # Optional: include per-agent details when available
        details: dict[str, Any] = {}
        for name, agent in self._launcher.agents.items():
            try:
                details[name] = agent.get_status()
            except Exception:
                # Fallback if agent doesn't implement get_status()
                details[name] = {"running": getattr(agent, "is_running", False)}

        return {
            "status": "healthy" if self._launcher.running else "stopped",
            "agents": agent_status,
            "total_agents": len(self._launcher.agents) if self._launcher.agents else 0,
            "details": details,
        }

    def get_loaded_agents(self) -> list[str]:
        """Get list of loaded agents"""
        return self._loaded_agents.copy()

    async def _wait_until_ready(self, timeout: float, interval: float = 0.1) -> bool:
        """Best-effort readiness check within timeout.

        Criteria per agent:
        - agent.is_running is True; and
        - if agent.consume_topics -> consumer is not None
        - if agent.produce_topics -> producer is not None
        Returns True when all loaded agents satisfy the criteria.
        """
        if self._launcher is None:
            return False

        deadline = monotonic() + max(0.0, timeout)
        while monotonic() < deadline:
            # Early failure: background task crashed
            if self._task is not None and self._task.done():
                return False

            if self._all_agents_ready():
                return True

            await asyncio.sleep(interval)

        return self._all_agents_ready()

    def _all_agents_ready(self) -> bool:
        """Check readiness of all loaded agents based on Kafka client initialization."""
        if self._launcher is None:
            return False

        names = self._loaded_agents or list(self._launcher.agents.keys())
        for name in names:
            agent = self._launcher.agents.get(name)
            if agent is None:
                return False
            # Must be running
            if not getattr(agent, "is_running", False):
                return False
            # If configured to consume, consumer must be initialized
            consume_topics = getattr(agent, "consume_topics", []) or []
            if consume_topics and getattr(agent, "consumer", None) is None:
                return False
            # If configured to produce, producer must be initialized
            produce_topics = getattr(agent, "produce_topics", []) or []
            if produce_topics and getattr(agent, "producer", None) is None:
                return False
        return True
