"""Unit tests for the service orchestrator"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from src.launcher.config import LauncherAgentsConfig, LauncherApiConfig, LauncherConfigModel
from src.launcher.errors import OrchestrationError
from src.launcher.orchestrator import Orchestrator
from src.launcher.types import ComponentType, LaunchMode, ServiceStatus


class TestOrchestratorStateManagement:
    """Test cases for state management functionality"""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance with test configuration"""
        config = LauncherConfigModel(
            default_mode=LaunchMode.SINGLE,
            components=[ComponentType.API, ComponentType.AGENTS],
            health_interval=1.0,
            api=LauncherApiConfig(host="0.0.0.0", port=8000, reload=False),
            agents=LauncherAgentsConfig(names=["worldsmith", "plotmaster"]),
        )
        return Orchestrator(config)

    def test_service_status_enum_values(self):
        """Test that ServiceStatus enum contains all required values"""
        expected = {
            "STOPPED": "stopped",
            "STARTING": "starting",
            "RUNNING": "running",
            "DEGRADED": "degraded",
            "STOPPING": "stopping",
            "FAILED": "failed",
        }
        for name, value in expected.items():
            assert hasattr(ServiceStatus, name)
            assert ServiceStatus[name].value == value

    def test_initial_state_is_stopped(self, orchestrator):
        """Test that services have STOPPED as initial state"""
        # Services should default to STOPPED when queried
        assert orchestrator.get_service_state("api") == ServiceStatus.STOPPED
        assert orchestrator.get_service_state("agents") == ServiceStatus.STOPPED
        assert orchestrator.get_service_state("unknown") == ServiceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_valid_state_transitions(self, orchestrator):
        """Test that valid state transitions are allowed"""
        # Valid transitions according to state machine
        assert orchestrator.is_valid_state_transition(ServiceStatus.STOPPED, ServiceStatus.STARTING)
        assert orchestrator.is_valid_state_transition(ServiceStatus.STARTING, ServiceStatus.RUNNING)
        assert orchestrator.is_valid_state_transition(ServiceStatus.RUNNING, ServiceStatus.STOPPING)
        assert orchestrator.is_valid_state_transition(ServiceStatus.RUNNING, ServiceStatus.DEGRADED)
        assert orchestrator.is_valid_state_transition(ServiceStatus.DEGRADED, ServiceStatus.RUNNING)
        assert orchestrator.is_valid_state_transition(ServiceStatus.STOPPING, ServiceStatus.STOPPED)
        assert orchestrator.is_valid_state_transition(ServiceStatus.STARTING, ServiceStatus.FAILED)
        assert orchestrator.is_valid_state_transition(ServiceStatus.FAILED, ServiceStatus.STARTING)

    @pytest.mark.asyncio
    async def test_invalid_state_transitions_rejected(self, orchestrator):
        """Test that invalid state transitions are rejected"""
        # Invalid transitions should be rejected
        assert not orchestrator.is_valid_state_transition(ServiceStatus.STOPPED, ServiceStatus.RUNNING)
        assert not orchestrator.is_valid_state_transition(ServiceStatus.STOPPED, ServiceStatus.DEGRADED)
        assert not orchestrator.is_valid_state_transition(ServiceStatus.RUNNING, ServiceStatus.STARTING)

        # Setting invalid state transition should raise error
        await orchestrator.set_service_state("api", ServiceStatus.STARTING)
        with pytest.raises(OrchestrationError, match="Invalid state transition"):
            await orchestrator.set_service_state("api", ServiceStatus.STOPPED)


class TestOrchestratorDependencies:
    """Test cases for dependency management"""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance"""
        config = LauncherConfigModel(
            default_mode=LaunchMode.SINGLE,
            components=[ComponentType.API, ComponentType.AGENTS],
        )
        return Orchestrator(config)

    def test_simple_dependency_chain_sorting(self, orchestrator):
        """Test topological sorting with simple dependency chain"""
        # Mock the dependency graph: agents depends on api
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "agents": {"api"},
                "api": set(),
            }

            order = orchestrator.get_startup_order(["api", "agents"])

            # API should start before agents
            assert len(order) == 2
            assert "api" in order[0]
            assert "agents" in order[1]

    def test_complex_dependency_graph_sorting(self, orchestrator):
        """Test topological sorting with complex dependencies"""
        # Mock a more complex dependency graph
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "api": {"db", "cache"},
                "agents": {"api"},
                "db": set(),
                "cache": set(),
            }

            order = orchestrator.get_startup_order(["db", "cache", "api", "agents"])

            # Should have proper layering
            assert len(order) > 0
            # db and cache should be in first layer (no dependencies)
            first_layer = order[0]
            assert "db" in first_layer or "cache" in first_layer

            # api should come after db and cache
            api_layer_idx = next(i for i, layer in enumerate(order) if "api" in layer)
            db_layer_idx = next(i for i, layer in enumerate(order) if "db" in layer)
            cache_layer_idx = next(i for i, layer in enumerate(order) if "cache" in layer)
            assert api_layer_idx > db_layer_idx
            assert api_layer_idx > cache_layer_idx

    def test_circular_dependency_detection(self, orchestrator):
        """Test that circular dependencies are detected and raise error"""
        # Mock a circular dependency
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "a": {"b"},
                "b": {"c"},
                "c": {"a"},
            }

            with pytest.raises(OrchestrationError, match="Circular dependency"):
                orchestrator.get_startup_order(["a", "b", "c"])

    def test_self_dependency_detection(self, orchestrator):
        """Test that self-dependencies are detected"""
        # Mock a self-dependency
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "api": {"api"},  # Self-dependency
            }

            with pytest.raises(OrchestrationError, match="Circular dependency"):
                orchestrator.get_startup_order(["api"])


class TestOrchestratorStartup:
    """Test cases for service startup orchestration"""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance"""
        config = LauncherConfigModel(
            default_mode=LaunchMode.SINGLE,
            components=[ComponentType.API, ComponentType.AGENTS],
            startup_timeout=30,
            stop_grace=10,
        )
        return Orchestrator(config)

    @pytest.mark.asyncio
    async def test_startup_follows_dependency_order(self, orchestrator):
        """Test that services start in correct dependency order"""
        # Track startup order
        started = []

        # Mock adapters
        api_adapter = AsyncMock()
        agents_adapter = AsyncMock()

        async def start_api():
            started.append("api")
            return True

        async def start_agents():
            started.append("agents")
            return True

        api_adapter.start = start_api
        api_adapter.get_status.return_value = ServiceStatus.RUNNING
        agents_adapter.start = start_agents
        agents_adapter.get_status.return_value = ServiceStatus.RUNNING

        orchestrator.services = {"api": api_adapter, "agents": agents_adapter}

        # Mock dependency graph
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "agents": {"api"},
                "api": set(),
            }

            result = await orchestrator.orchestrate_startup(["api", "agents"])

            assert result is True
            assert started == ["api", "agents"]  # Correct order
            assert orchestrator.get_service_state("api") == ServiceStatus.RUNNING
            assert orchestrator.get_service_state("agents") == ServiceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_startup_failure_triggers_rollback(self, orchestrator):
        """Test that startup failure triggers rollback of started services"""
        # Mock adapters
        api_adapter = AsyncMock()
        agents_adapter = AsyncMock()

        api_adapter.start.return_value = True
        api_adapter.stop = AsyncMock(return_value=True)
        api_adapter.get_status.return_value = ServiceStatus.RUNNING

        agents_adapter.start.side_effect = Exception("Startup failed")

        orchestrator.services = {"api": api_adapter, "agents": agents_adapter}

        # Mock dependency graph
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "agents": {"api"},
                "api": set(),
            }

            result = await orchestrator.orchestrate_startup(["api", "agents"])

            assert result is False
            # API should have been stopped (rollback)
            api_adapter.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_services_startup_with_missing_deps(self, orchestrator):
        """Test partial service startup when dependencies are missing"""
        # Try to start only agents without api
        agents_adapter = AsyncMock()
        agents_adapter.start.return_value = True

        orchestrator.services = {"agents": agents_adapter}

        # Mock dependency graph showing agents needs api
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "agents": {"api"},
                "api": set(),
            }

            # This should fail or handle missing dependency gracefully
            result = await orchestrator.orchestrate_startup(["agents"])

            # In P1, we just return False and log error
            assert result is False

    @pytest.mark.asyncio
    async def test_concurrent_startup_same_level_performance(self, orchestrator):
        """Test that services at same dependency level start concurrently"""
        # Mock two services with no dependencies (same level)
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "service1": set(),
                "service2": set(),
            }

            # Create slow-starting services
            async def slow_start():
                await asyncio.sleep(0.1)
                return True

            service1 = AsyncMock()
            service2 = AsyncMock()
            service1.start = slow_start
            service2.start = slow_start
            service1.get_status.return_value = ServiceStatus.RUNNING
            service2.get_status.return_value = ServiceStatus.RUNNING

            orchestrator.services = {"service1": service1, "service2": service2}

            # Measure time
            start_time = time.perf_counter()
            result = await orchestrator.orchestrate_startup(["service1", "service2"])
            elapsed = time.perf_counter() - start_time

            assert result is True
            # Should take ~0.1s (concurrent) not ~0.2s (sequential)
            assert elapsed < 0.15

    @pytest.mark.asyncio
    async def test_startup_timeout_handling(self, orchestrator):
        """Test that startup timeout is properly handled"""

        # Create a service that starts slowly
        async def slow_start():
            await asyncio.sleep(2)  # Longer than timeout
            return True

        api_adapter = AsyncMock()
        api_adapter.start = slow_start

        orchestrator.services = {"api": api_adapter}
        orchestrator.config.startup_timeout = 1  # 1 second timeout

        result = await orchestrator.orchestrate_startup(["api"])

        assert result is False
        assert orchestrator.get_service_state("api") == ServiceStatus.FAILED


class TestOrchestratorShutdown:
    """Test cases for service shutdown orchestration"""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance"""
        config = LauncherConfigModel(
            default_mode=LaunchMode.SINGLE,
            components=[ComponentType.API, ComponentType.AGENTS],
            stop_grace=10,
        )
        return Orchestrator(config)

    @pytest.mark.asyncio
    async def test_shutdown_reverse_order(self, orchestrator):
        """Test that services stop in reverse dependency order"""
        # Track shutdown order
        stopped = []

        # Mock adapters
        api_adapter = AsyncMock()
        agents_adapter = AsyncMock()

        async def stop_api():
            stopped.append("api")
            return True

        async def stop_agents():
            stopped.append("agents")
            return True

        api_adapter.stop = stop_api
        api_adapter.get_status.return_value = ServiceStatus.STOPPED
        agents_adapter.stop = stop_agents
        agents_adapter.get_status.return_value = ServiceStatus.STOPPED

        orchestrator.services = {"api": api_adapter, "agents": agents_adapter}
        orchestrator.service_states = {
            "api": ServiceStatus.RUNNING,
            "agents": ServiceStatus.RUNNING,
        }

        # Mock dependency graph
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "agents": {"api"},
                "api": set(),
            }

            result = await orchestrator.orchestrate_shutdown(["api", "agents"])

            assert result is True
            # Should stop in reverse order: agents first, then api
            assert stopped == ["agents", "api"]

    @pytest.mark.asyncio
    async def test_graceful_shutdown_timeout(self, orchestrator):
        """Test graceful shutdown timeout handling"""

        # Create a service that stops slowly
        async def slow_stop(timeout=10):
            await asyncio.sleep(2)  # Longer than grace period
            return True

        api_adapter = AsyncMock()
        api_adapter.stop = slow_stop

        orchestrator.services = {"api": api_adapter}
        orchestrator.config.stop_grace = 1  # 1 second grace

        result = await orchestrator.orchestrate_shutdown(["api"])

        # Should handle timeout gracefully
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_error_handling(self, orchestrator):
        """Test that shutdown continues even if some services fail"""
        # Mock adapters where one fails
        api_adapter = AsyncMock()
        agents_adapter = AsyncMock()

        api_adapter.stop.side_effect = Exception("Stop failed")
        agents_adapter.stop.return_value = True
        agents_adapter.get_status.return_value = ServiceStatus.STOPPED

        orchestrator.services = {"api": api_adapter, "agents": agents_adapter}

        result = await orchestrator.orchestrate_shutdown(["api", "agents"])

        # Should return False but still stop other services
        assert result is False
        agents_adapter.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_partial_services_shutdown(self, orchestrator):
        """Test shutting down only specific services"""
        # Mock adapters
        api_adapter = AsyncMock()
        agents_adapter = AsyncMock()

        api_adapter.stop.return_value = True
        agents_adapter.stop.return_value = True

        orchestrator.services = {"api": api_adapter, "agents": agents_adapter}

        # Shutdown only api
        result = await orchestrator.orchestrate_shutdown(["api"])

        assert result is True
        api_adapter.stop.assert_called_once()
        agents_adapter.stop.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_shutdown_same_level(self, orchestrator):
        """Test that services at same level can shutdown concurrently"""
        # Mock dependency graph with services at same level
        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "db": set(),
                "cache": set(),
                "api": {"db", "cache"},
            }

            # Create slow-stopping services
            async def slow_stop(timeout=10):
                await asyncio.sleep(0.1)
                return True

            db_adapter = AsyncMock()
            cache_adapter = AsyncMock()
            api_adapter = AsyncMock()

            db_adapter.stop = slow_stop
            cache_adapter.stop = slow_stop
            api_adapter.stop = AsyncMock(return_value=True)

            for adapter in [db_adapter, cache_adapter, api_adapter]:
                adapter.get_status.return_value = ServiceStatus.STOPPED

            orchestrator.services = {
                "db": db_adapter,
                "cache": cache_adapter,
                "api": api_adapter,
            }

            # Measure time
            start_time = time.perf_counter()
            result = await orchestrator.orchestrate_shutdown(["api", "db", "cache"])
            elapsed = time.perf_counter() - start_time

            assert result is True
            # db and cache should stop concurrently (~0.1s not ~0.2s)
            assert elapsed < 0.25


class TestOrchestratorErrorHandling:
    """Test cases for error handling and health monitoring"""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance"""
        config = LauncherConfigModel(
            default_mode=LaunchMode.SINGLE,
            components=[ComponentType.API, ComponentType.AGENTS],
        )
        return Orchestrator(config)

    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, orchestrator):
        """Test that health checks update service state correctly"""
        # Mock adapter with health check
        api_adapter = AsyncMock()
        api_adapter.health_check.return_value = {"status": "unhealthy"}

        orchestrator.services = {"api": api_adapter}
        orchestrator.service_states["api"] = ServiceStatus.RUNNING

        await orchestrator.update_service_health("api")

        assert orchestrator.get_service_state("api") == ServiceStatus.DEGRADED

    def test_error_context_collection(self, orchestrator):
        """Test error context collection for diagnostics"""
        # Set up some state
        orchestrator.service_states["api"] = ServiceStatus.FAILED

        with patch.object(orchestrator, "build_dependency_graph") as mock_build:
            mock_build.return_value = {
                "api": {"db"},
                "db": set(),
            }

            context = orchestrator.collect_error_context("api")

            assert context["service_name"] == "api"
            assert context["current_state"] == "failed"
            assert "dependencies" in context
            assert "error_timestamp" in context
            assert "config" in context

    @pytest.mark.asyncio
    async def test_concurrent_state_mutations(self, orchestrator):
        """Test that concurrent state changes are thread-safe"""

        # Try to change state concurrently
        async def change_state(state):
            await orchestrator.set_service_state("api", state)

        # Set initial state
        await orchestrator.set_service_state("api", ServiceStatus.STOPPED)

        # Try concurrent mutations
        tasks = [
            change_state(ServiceStatus.STARTING),  # Valid from STOPPED
            change_state(ServiceStatus.RUNNING),  # Invalid from STOPPED
            change_state(ServiceStatus.STOPPING),  # Invalid from STOPPED
        ]

        # Gather results, expecting some to fail
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should have failed due to invalid transition
        assert any(isinstance(r, OrchestrationError) for r in results)

    @pytest.mark.asyncio
    async def test_unknown_service_handling(self, orchestrator):
        """Test handling of unknown service names"""
        result = await orchestrator.orchestrate_startup(["unknown_service"])

        # Should handle gracefully and return False
        assert result is False
        assert orchestrator.get_service_state("unknown_service") == ServiceStatus.STOPPED

    def test_empty_service_list_handling(self, orchestrator):
        """Test handling of empty service list"""
        order = orchestrator.get_startup_order([])

        # Should return empty or single empty layer
        assert len(order) == 0 or (len(order) == 1 and len(order[0]) == 0)

    @pytest.mark.asyncio
    async def test_dependency_graph_caching(self, orchestrator):
        """Test that dependency graph is cached to avoid recomputation"""
        mock_graph = {"api": set(), "agents": {"api"}}

        with patch.object(orchestrator, "_build_dependency_graph_internal") as mock_build:
            mock_build.return_value = mock_graph

            # First call
            graph1 = orchestrator.build_dependency_graph()
            # Second call
            graph2 = orchestrator.build_dependency_graph()

            # Should have called internal method only once (cached)
            mock_build.assert_called_once()
            assert graph1 == graph2
