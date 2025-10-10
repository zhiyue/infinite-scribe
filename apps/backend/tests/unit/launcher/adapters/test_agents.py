"""Unit tests for AgentsAdapter"""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from launcher.adapters.agents import AgentsAdapter
from launcher.types import ServiceStatus


@pytest.fixture
def mock_agent_launcher():
    """Create mock AgentLauncher for testing"""
    launcher = Mock()
    launcher.agents = {"worldsmith": Mock(), "writer": Mock()}
    launcher.running = False
    launcher.load_agents = Mock()
    launcher.start_all = AsyncMock()
    launcher.stop_all = AsyncMock()
    launcher.setup_signal_handlers = Mock()
    return launcher


@pytest.fixture
def agents_adapter():
    """Create AgentsAdapter for testing"""
    return AgentsAdapter({"agents": ["worldsmith", "writer"]})


def test_agents_adapter_initialization():
    """Test AgentsAdapter initialization"""
    config = {"agents": ["worldsmith", "writer", "director"]}
    adapter = AgentsAdapter(config)

    assert adapter.name == "agents"
    assert adapter.config == config
    assert adapter.status == ServiceStatus.STOPPED
    assert adapter._launcher is None


def test_agents_adapter_initialization_no_config():
    """Test AgentsAdapter initialization with empty config"""
    adapter = AgentsAdapter({})
    assert adapter._agent_names is None


def test_agents_adapter_load_specific_agents(agents_adapter):
    """Test loading specific agents"""
    agents_adapter.load(["worldsmith", "director"])
    assert agents_adapter._loaded_agents == ["worldsmith", "director"]


def test_agents_adapter_load_all_agents(agents_adapter):
    """Test loading all available agents"""
    agents_adapter.load(None)
    # Should load default agents
    expected_agents = ["orchestrator", "worldsmith", "plotmaster", "director", "writer"]
    assert agents_adapter._loaded_agents == expected_agents


@pytest.mark.asyncio
async def test_agents_adapter_start_success(agents_adapter, mock_agent_launcher):
    """Test successful agent startup"""
    with patch("launcher.adapters.agents.AgentLauncher", return_value=mock_agent_launcher):
        # Load agents first
        agents_adapter.load(["worldsmith", "writer"])

        # Start agents
        result = await agents_adapter.start()

        assert result is True
        assert agents_adapter.status == ServiceStatus.RUNNING
        mock_agent_launcher.setup_signal_handlers.assert_called_once()
        mock_agent_launcher.load_agents.assert_called_once_with(["worldsmith", "writer"])
        mock_agent_launcher.start_all.assert_called_once()


@pytest.mark.asyncio
async def test_agents_adapter_start_with_none_agents(agents_adapter, mock_agent_launcher):
    """Test starting with None agents (should load all)"""
    with patch("launcher.adapters.agents.AgentLauncher", return_value=mock_agent_launcher):
        # Don't call load - should use agent_names from config
        result = await agents_adapter.start()

        assert result is True
        mock_agent_launcher.load_agents.assert_called_once_with(["worldsmith", "writer"])


@pytest.mark.asyncio
async def test_agents_adapter_start_failure(agents_adapter, mock_agent_launcher):
    """Test agent startup failure"""
    mock_agent_launcher.start_all.side_effect = Exception("Startup failed")

    with patch("launcher.adapters.agents.AgentLauncher", return_value=mock_agent_launcher):
        agents_adapter.load(["worldsmith"])

        result = await agents_adapter.start()

        assert result is False
        assert agents_adapter.status == ServiceStatus.FAILED


@pytest.mark.asyncio
async def test_agents_adapter_stop_success(agents_adapter, mock_agent_launcher):
    """Test successful agent stop"""
    agents_adapter._launcher = mock_agent_launcher
    agents_adapter.status = ServiceStatus.RUNNING

    result = await agents_adapter.stop(timeout=15)

    assert result is True
    assert agents_adapter.status == ServiceStatus.STOPPED
    mock_agent_launcher.stop_all.assert_called_once()


@pytest.mark.asyncio
async def test_agents_adapter_stop_no_launcher(agents_adapter):
    """Test stop when no launcher is initialized"""
    result = await agents_adapter.stop()

    assert result is True
    assert agents_adapter.status == ServiceStatus.STOPPED


@pytest.mark.asyncio
async def test_agents_adapter_stop_failure(agents_adapter, mock_agent_launcher):
    """Test agent stop failure"""
    mock_agent_launcher.stop_all.side_effect = Exception("Stop failed")
    agents_adapter._launcher = mock_agent_launcher
    agents_adapter.status = ServiceStatus.RUNNING

    result = await agents_adapter.stop()

    assert result is False
    assert agents_adapter.status == ServiceStatus.FAILED


@pytest.mark.asyncio
async def test_agents_adapter_health_check_running(agents_adapter, mock_agent_launcher):
    """Test health check when agents are running"""
    mock_agent_launcher.running = True
    mock_agent_launcher.agents = {"worldsmith": Mock(), "writer": Mock()}
    agents_adapter._launcher = mock_agent_launcher
    agents_adapter._loaded_agents = ["worldsmith", "writer"]

    health = await agents_adapter.health_check()

    assert health["status"] == "healthy"
    assert health["total_agents"] == 2
    assert "worldsmith" in health["agents"]
    assert "writer" in health["agents"]


@pytest.mark.asyncio
async def test_agents_adapter_health_check_not_started(agents_adapter):
    """Test health check when launcher not initialized"""
    health = await agents_adapter.health_check()

    assert health["status"] == "not_started"


@pytest.mark.asyncio
async def test_agents_adapter_health_check_stopped(agents_adapter, mock_agent_launcher):
    """Test health check when agents are stopped"""
    mock_agent_launcher.running = False
    agents_adapter._launcher = mock_agent_launcher
    agents_adapter._loaded_agents = ["worldsmith"]

    health = await agents_adapter.health_check()

    assert health["status"] == "stopped"
    assert health["agents"]["worldsmith"] == "stopped"


@pytest.mark.asyncio
async def test_agents_adapter_health_check_states_and_errors(agents_adapter):
    """health_check returns states/errors with per-agent summaries"""

    class DummyAgent:
        def __init__(self, state: str, err: str | None = None):
            self._state = state
            self._err = err

        def get_status(self) -> dict[str, Any]:  # type: ignore[name-defined]
            s: dict[str, Any] = {"running": self._state in {"RUNNING", "DEGRADED", "STARTING"}, "state": self._state}
            if self._err:
                s["last_error"] = self._err
                s["last_error_at"] = "2024-01-01T00:00:00Z"
            return s

    launcher = Mock()
    launcher.running = True
    launcher.agents = {
        "writer": DummyAgent("RUNNING"),
        "director": DummyAgent("DEGRADED", "recent failure"),
    }

    agents_adapter._launcher = launcher
    agents_adapter._loaded_agents = ["writer", "director"]

    health = await agents_adapter.health_check()

    assert "states" in health and isinstance(health["states"], dict)
    assert health["states"]["writer"] == "RUNNING"
    assert health["states"]["director"] == "DEGRADED"
    assert "errors" in health and isinstance(health["errors"], dict)
    assert "director" in health["errors"] and health["errors"]["director"]["error"] == "recent failure"
    assert "writer" not in health["errors"]


def test_agents_adapter_get_loaded_agents(agents_adapter):
    """Test getting loaded agents list"""
    agents_adapter._loaded_agents = ["worldsmith", "director"]

    loaded = agents_adapter.get_loaded_agents()

    assert loaded == ["worldsmith", "director"]
    # Verify it returns a copy
    loaded.append("new_agent")
    assert agents_adapter._loaded_agents == ["worldsmith", "director"]


def test_agents_adapter_status_property(agents_adapter):
    """Test status property"""
    assert agents_adapter.get_status() == ServiceStatus.STOPPED

    agents_adapter.status = ServiceStatus.RUNNING
    assert agents_adapter.get_status() == ServiceStatus.RUNNING
