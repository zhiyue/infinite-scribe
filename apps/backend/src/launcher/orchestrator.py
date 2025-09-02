"""Service orchestration logic for unified backend launcher"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from graphlib import CycleError, TopologicalSorter
from typing import Any

import structlog

from .adapters import AgentsAdapter, ApiAdapter, BaseAdapter
from .config import LauncherConfigModel
from .errors import OrchestrationError
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
        self._state_lock = asyncio.Lock()  # Protect state changes
        self._running_authorized: set[str] = set()
        self._dependency_graph_cache: dict[str, set[str]] | None = None

    def get_service_state(self, service_name: str) -> ServiceStatus:
        """Get the current state of a service"""
        return self.service_states.get(service_name, ServiceStatus.STOPPED)

    def get_all_service_states(self) -> dict[str, dict[str, Any]]:
        """Get detailed state information for all services"""
        result = {}
        for service_name in self.service_states:
            adapter = self.services.get(service_name)

            # Get basic state
            state = self.service_states[service_name]

            # Get additional info from adapter if available
            service_info = {"state": state, "uptime": 0, "started_at": None, "pid": None, "port": None}

            if adapter:
                # Get info from adapter's status method if available
                try:
                    # Use getattr with default to avoid type checker issues
                    get_status_info = getattr(adapter, "get_status_info", None)
                    if get_status_info:
                        status_info = get_status_info()
                        service_info.update(status_info)
                    else:
                        port = getattr(adapter, "port", None)
                        if port is not None:
                            service_info["port"] = port
                except Exception:
                    # If adapter info retrieval fails, use defaults
                    pass

            result[service_name] = service_info

        return result

    async def set_service_state(self, service_name: str, state: ServiceStatus) -> None:
        """Set service state with validation and locking"""
        async with self._state_lock:
            current_state = self.service_states.get(service_name, ServiceStatus.STOPPED)
            # Idempotent: allow setting to the same state
            if state == current_state:
                logger.info(
                    "Service state unchanged",
                    service=service_name,
                    state=state.value,
                )
                return
            if (
                current_state == ServiceStatus.STARTING
                and state == ServiceStatus.RUNNING
                and service_name not in self._running_authorized
            ):
                # Only orchestrator-internal flow can promote STARTING -> RUNNING
                raise OrchestrationError(
                    f"Invalid state transition for {service_name}: {current_state.value} -> {state.value}"
                )
            if not self.is_valid_state_transition(current_state, state):
                raise OrchestrationError(
                    f"Invalid state transition for {service_name}: {current_state.value} -> {state.value}"
                )
            self.service_states[service_name] = state
            logger.info(
                "Service state changed",
                service=service_name,
                from_state=current_state.value,
                to_state=state.value,
            )

    def is_valid_state_transition(self, from_state: ServiceStatus, to_state: ServiceStatus) -> bool:
        """Check if a state transition is valid according to the state machine"""
        valid_transitions = {
            ServiceStatus.STOPPED: {ServiceStatus.STARTING},
            ServiceStatus.STARTING: {ServiceStatus.RUNNING, ServiceStatus.FAILED},
            ServiceStatus.RUNNING: {ServiceStatus.STOPPING, ServiceStatus.DEGRADED, ServiceStatus.FAILED},
            ServiceStatus.DEGRADED: {ServiceStatus.STOPPING, ServiceStatus.RUNNING, ServiceStatus.FAILED},
            ServiceStatus.STOPPING: {ServiceStatus.STOPPED, ServiceStatus.FAILED},
            ServiceStatus.FAILED: {ServiceStatus.STARTING, ServiceStatus.STOPPING},
        }
        return to_state in valid_transitions.get(from_state, set())

    def build_dependency_graph(self) -> dict[str, set[str]]:
        """Build or return cached dependency graph"""
        if self._dependency_graph_cache is None:
            self._dependency_graph_cache = self._build_dependency_graph_internal()
        return self._dependency_graph_cache

    def _build_dependency_graph_internal(self) -> dict[str, set[str]]:
        """Internal method to build the dependency graph from config or defaults"""
        # Prefer configured dependencies if provided
        graph: dict[str, set[str]] = {}
        if getattr(self.config, "dependencies", None):
            for svc, deps in (self.config.dependencies or {}).items():
                graph[svc] = set(deps)
        # Ensure all configured components are present in graph
        for comp in self.config.components:
            graph.setdefault(comp.value, set())
        # Fallback default if graph is empty
        if not graph:
            graph = {
                "agents": {"api"},  # agents depend on api
                "api": set(),  # api has no dependencies
            }
        return graph

    def get_startup_order(self, target_services: list[str]) -> list[list[str]]:
        """Get service startup order using topological sort"""
        if not target_services:
            return []

        deps = self.build_dependency_graph()

        # Build graph for only target services
        graph: dict[str, set[str]] = {}
        for service in target_services:
            if service in deps:
                # Only include dependencies that are also in target_services
                graph[service] = deps[service] & set(target_services)
            else:
                graph[service] = set()

        try:
            sorter = TopologicalSorter(graph)
            levels: list[list[str]] = []
            sorter.prepare()

            while True:
                ready = list(sorter.get_ready())
                if not ready:
                    break
                # Only include services that are in target_services
                level = [s for s in ready if s in target_services]
                if level:
                    levels.append(level)
                for r in ready:
                    sorter.done(r)

            return levels

        except CycleError as e:
            raise OrchestrationError(f"Circular dependency detected: {e}") from e

    async def orchestrate_startup(self, target_services: list[str] | None = None) -> bool:
        """Start services in dependency order with concurrent startup for same level"""
        services = target_services or [c.value for c in self.config.components]
        # Validate dependencies are present or already running
        deps = self.build_dependency_graph()
        requested = set(services)
        running = {name for name, state in self.service_states.items() if state == ServiceStatus.RUNNING}
        for svc in list(requested):
            missing = (deps.get(svc, set()) - requested) - running
            if missing:
                logger.error("Missing dependencies for service", service=svc, missing=list(missing))
                return False

        startup_levels = self.get_startup_order(services)
        started_services: list[str] = []

        try:
            for level in startup_levels:
                # Start all services in this level concurrently
                timeout = getattr(self.config, "startup_timeout", 30)
                tasks = [
                    asyncio.create_task(asyncio.wait_for(self._start_service(service_name), timeout=timeout))
                    for service_name in level
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for service_name, result in zip(level, results, strict=False):
                    if isinstance(result, Exception):
                        logger.error("Service failed to start", service=service_name, error=str(result))
                        # Mark service as failed on exception (e.g., timeout)
                        await self.set_service_state(service_name, ServiceStatus.FAILED)
                        # _start_service should have set FAILED on error
                        raise OrchestrationError(f"Failed to start service: {service_name}")
                    if result is True:
                        started_services.append(service_name)
                    else:
                        logger.error("Service failed to start", service=service_name)
                        raise OrchestrationError(f"Failed to start service: {service_name}")

            logger.info("All services started successfully", services=started_services)
            return True

        except Exception as e:
            logger.error("Startup failed, initiating rollback", error=str(e))
            await self._rollback_startup(started_services)
            return False

    async def _start_service(self, service_name: str) -> bool:
        """Start a single service"""
        try:
            # Get or create adapter first to validate service
            adapter = self.services.get(service_name)
            if adapter is None:
                adapter = self._create_adapter_by_name(service_name)
                if adapter is None:
                    logger.error("Unknown service", service=service_name)
                    # Keep state as STOPPED for unknown services
                    return False
                self.services[service_name] = adapter

            await self.set_service_state(service_name, ServiceStatus.STARTING)

            # Start the service
            success = await adapter.start()
            if success:
                # Authorize RUNNING promotion for internal flow
                self._running_authorized.add(service_name)
                try:
                    await self.set_service_state(service_name, ServiceStatus.RUNNING)
                finally:
                    self._running_authorized.discard(service_name)
                logger.info("Service started", service=service_name)
            else:
                await self.set_service_state(service_name, ServiceStatus.FAILED)
                logger.error("Service failed to start", service=service_name)

            return success

        except Exception as e:
            logger.error("Error starting service", service=service_name, error=str(e))
            await self.set_service_state(service_name, ServiceStatus.FAILED)
            raise

    async def _rollback_startup(self, started_services: list[str]) -> None:
        """Rollback by stopping services that were started"""
        logger.info("Rolling back started services", services=started_services)
        for service_name in reversed(started_services):
            try:
                await self.set_service_state(service_name, ServiceStatus.STOPPING)
                adapter = self.services.get(service_name)
                if adapter:
                    grace = getattr(self.config, "stop_grace", 10)
                    await asyncio.wait_for(adapter.stop(timeout=grace), timeout=grace)
                await self.set_service_state(service_name, ServiceStatus.STOPPED)
                logger.info("Service rolled back", service=service_name)
            except TimeoutError:
                logger.error("Rollback timeout", service=service_name)
                await self.set_service_state(service_name, ServiceStatus.FAILED)
            except Exception as e:
                logger.error("Rollback failed", service=service_name, error=str(e))
                await self.set_service_state(service_name, ServiceStatus.FAILED)

    async def orchestrate_shutdown(self, target_services: list[str] | None = None) -> bool:
        """Stop services in reverse dependency order with concurrent shutdown for same level"""
        services = target_services or list(self.services.keys())
        if not services:
            return True

        # Get startup order and reverse it for shutdown
        startup_levels = self.get_startup_order(services)
        success_count = 0
        total_count = len(services)

        # Shutdown in reverse order (last started, first stopped)
        for level in reversed(startup_levels):
            grace = getattr(self.config, "stop_grace", 10)
            tasks = [
                asyncio.create_task(asyncio.wait_for(self._stop_service(service_name), timeout=grace))
                for service_name in level
                if service_name in self.services
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for service_name, result in zip(level, results, strict=False):
                if isinstance(result, Exception):
                    logger.error("Shutdown error", service=service_name, error=str(result))
                elif result is True:
                    success_count += 1
                else:
                    logger.error("Service failed to stop", service=service_name)

        return success_count == total_count

    async def _stop_service(self, service_name: str) -> bool:
        """Stop a single service"""
        try:
            current = self.get_service_state(service_name)
            adapter = self.services.get(service_name)

            if adapter:
                # If service is already stopped, call adapter.stop() without state changes
                if current == ServiceStatus.STOPPED:
                    logger.info("Service already stopped", service=service_name)
                    grace = getattr(self.config, "stop_grace", 10)
                    try:
                        success = await adapter.stop(timeout=grace)
                    except TypeError:
                        success = await adapter.stop()
                    return success

                await self.set_service_state(service_name, ServiceStatus.STOPPING)
                grace = getattr(self.config, "stop_grace", 10)
                try:
                    success = await adapter.stop(timeout=grace)
                except TypeError:
                    success = await adapter.stop()
                if success:
                    await self.set_service_state(service_name, ServiceStatus.STOPPED)
                    logger.info("Service stopped", service=service_name)
                else:
                    await self.set_service_state(service_name, ServiceStatus.FAILED)
                    logger.error("Service failed to stop gracefully", service=service_name)
                return success

            return False

        except Exception as e:
            logger.error("Error stopping service", service=service_name, error=str(e))
            await self.set_service_state(service_name, ServiceStatus.FAILED)
            return False

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
            cfg = {
                "agents": self.config.agents.names,
                "disable_signal_handlers": self.config.agents.disable_signal_handlers,
            }
            return AgentsAdapter(cfg)
        return None

    async def update_service_health(self, service_name: str) -> None:
        """Update service health status based on health check"""
        adapter = self.services.get(service_name)
        if not adapter:
            return

        try:
            # Perform health check
            health = await adapter.health_check()

            # Determine if service is healthy
            is_healthy = False
            if isinstance(health, dict):
                status = health.get("status")
                is_healthy = status in {"healthy", "running"}
            else:
                is_healthy = bool(health)

            # Update state based on health
            current_state = self.get_service_state(service_name)
            if current_state == ServiceStatus.RUNNING and not is_healthy:
                await self.set_service_state(service_name, ServiceStatus.DEGRADED)
                logger.warning("Service degraded", service=service_name)
            elif current_state == ServiceStatus.DEGRADED and is_healthy:
                await self.set_service_state(service_name, ServiceStatus.RUNNING)
                logger.info("Service recovered", service=service_name)

        except Exception as e:
            logger.error("Health check failed", service=service_name, error=str(e))
            await self.set_service_state(service_name, ServiceStatus.FAILED)

    def collect_error_context(self, service_name: str) -> dict[str, Any]:
        """Collect diagnostic information for error reporting"""
        current_state = self.get_service_state(service_name)
        deps = self.build_dependency_graph()

        return {
            "service_name": service_name,
            "current_state": current_state.value,
            "dependencies": list(deps.get(service_name, set())),
            "error_timestamp": datetime.now(UTC).isoformat(),
            "config": {
                "mode": getattr(self.config.default_mode, "value", str(self.config.default_mode)),
                "components": [c.value for c in self.config.components],
            },
        }
