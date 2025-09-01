"""Service orchestration logic for unified backend launcher"""

from __future__ import annotations

from typing import Any

import structlog

from .adapters import AgentsAdapter, ApiAdapter, BaseAdapter
from .config import LauncherConfigModel
from .types import ComponentType, ServiceStatus

logger = structlog.get_logger(__name__)


class Orchestrator:
    """Service orchestrator for managing backend components"""

    def __init__(self, config: LauncherConfigModel | None = None):
        """Initialize the orchestrator"""
        self.config = config or LauncherConfigModel()
        self.services: dict[str, BaseAdapter] = {}
        self.dependency_graph: dict[str, set[str]] = {}
        self.service_states: dict[str, ServiceStatus] = {}

    async def orchestrate_startup(self, target_services: list[str] | None = None) -> bool:
        """Start services in dependency order (simple sequence for now)"""
        names = target_services or [c.value for c in self.config.components]
        try:
            for name in names:
                adapter = self.services.get(name) or self._create_adapter_by_name(name)
                if adapter is None:
                    raise ValueError(f"Unknown service: {name}")
                self.services[name] = adapter

                ok = await adapter.start()
                self.service_states[name] = adapter.get_status()
                if not ok:
                    logger.error("Service failed to start", service=name)
                    return False

            return True
        except Exception as e:
            logger.error("Startup orchestration error", error=str(e))
            return False

    async def orchestrate_shutdown(self, target_services: list[str] | None = None) -> bool:
        """Stop services in reverse order (simple sequence for now)"""
        names = target_services or list(self.services.keys())
        ok_all = True
        for name in reversed(names):
            adapter = self.services.get(name)
            if not adapter:
                continue
            try:
                ok = await adapter.stop(timeout=self.config.stop_grace)
                self.service_states[name] = adapter.get_status()
                ok_all = ok_all and ok
            except Exception as e:
                logger.error("Shutdown orchestration error", service=name, error=str(e))
                ok_all = False
        return ok_all

    def _create_adapter_by_name(self, name: str) -> BaseAdapter | None:
        """Factory: create adapter instance by service name using config injection"""
        if name == ComponentType.API.value:
            cfg: dict[str, Any] = {
                "host": self.config.api.host,
                "port": self.config.api.port,
                "reload": self.config.api.reload,
                "mode": self.config.default_mode,
            }
            return ApiAdapter(cfg)
        if name == ComponentType.AGENTS.value:
            cfg = {"agents": self.config.agents.names}
            return AgentsAdapter(cfg)
        return None

    def get_startup_order(self, target_services: list[str]) -> list[list[str]]:
        """Placeholder for topological sort of dependencies"""
        # TODO: Implement dependency-aware ordering when graph is available
        return [target_services]

    def _build_dependency_graph(self) -> dict[str, set[str]]:
        """Build the service dependency graph (not implemented yet)"""
        # TODO: Build dependency graph from service definitions
        return {}
