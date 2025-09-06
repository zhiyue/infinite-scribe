"""Unit tests for BaseAdapter abstract class"""

from abc import ABC
from typing import Any

import pytest

from launcher.adapters.base import BaseAdapter
from launcher.types import ServiceStatus


class ConcreteTestAdapter(BaseAdapter):
    """Test implementation of BaseAdapter for testing"""

    def __init__(self, name: str = "test", config: dict[str, Any] | None = None):
        super().__init__(name, config or {})

    async def start(self) -> bool:
        """Test implementation of start method"""
        self.status = ServiceStatus.RUNNING
        return True

    async def stop(self, timeout: int = 30) -> bool:
        """Test implementation of stop method"""
        self.status = ServiceStatus.STOPPED
        return True

    async def health_check(self) -> dict[str, Any]:
        """Test implementation of health_check method"""
        return {"status": "healthy", "name": self.name}


def test_base_adapter_is_abstract():
    """Test that BaseAdapter cannot be instantiated directly"""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseAdapter("test", {})


def test_base_adapter_inheritance():
    """Test BaseAdapter can be inherited from"""
    adapter = ConcreteTestAdapter("test", {"key": "value"})
    assert isinstance(adapter, BaseAdapter)
    assert isinstance(adapter, ABC)


def test_base_adapter_initialization():
    """Test BaseAdapter initialization with name and config"""
    config = {"host": "127.0.0.1", "port": 8000}
    adapter = ConcreteTestAdapter("api", config)

    assert adapter.name == "api"
    assert adapter.config == config
    assert adapter.status == ServiceStatus.STOPPED
    assert adapter.process is None


@pytest.mark.asyncio
async def test_base_adapter_abstract_methods_implemented():
    """Test that concrete implementation provides required methods"""
    adapter = ConcreteTestAdapter()

    # Test start method
    result = await adapter.start()
    assert result is True
    assert adapter.status == ServiceStatus.RUNNING

    # Test health_check method
    health = await adapter.health_check()
    assert health["status"] == "healthy"
    assert health["name"] == adapter.name

    # Test stop method
    result = await adapter.stop()
    assert result is True
    assert adapter.status == ServiceStatus.STOPPED


def test_base_adapter_get_status():
    """Test get_status method returns current status"""
    adapter = ConcreteTestAdapter()
    assert adapter.get_status() == ServiceStatus.STOPPED

    adapter.status = ServiceStatus.RUNNING
    assert adapter.get_status() == ServiceStatus.RUNNING


def test_base_adapter_config_access():
    """Test configuration access"""
    config = {"timeout": 30, "retry_count": 3}
    adapter = ConcreteTestAdapter("service", config)

    assert adapter.config["timeout"] == 30
    assert adapter.config["retry_count"] == 3


def test_base_adapter_empty_config():
    """Test adapter works with empty config"""
    adapter = ConcreteTestAdapter("service", {})
    assert adapter.config == {}
    assert adapter.name == "service"
