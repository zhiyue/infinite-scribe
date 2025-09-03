"""Tests for main launcher configuration model"""

import pytest
from pydantic import ValidationError
from src.launcher.config import LauncherAgentsConfig, LauncherApiConfig, LauncherConfigModel
from src.launcher.types import ComponentType, LaunchMode


class TestLauncherConfigModel:
    """Test main configuration model"""

    def test_default_values(self):
        """Test launcher config default values"""
        config = LauncherConfigModel()
        assert config.default_mode == LaunchMode.SINGLE
        assert config.components == [ComponentType.API, ComponentType.AGENTS]
        assert config.health_interval == 1.0
        assert isinstance(config.api, LauncherApiConfig)
        assert isinstance(config.agents, LauncherAgentsConfig)

    def test_custom_values(self):
        """Test launcher config custom values"""
        config = LauncherConfigModel(default_mode=LaunchMode.MULTI, components=[ComponentType.API], health_interval=2.5)
        assert config.default_mode == LaunchMode.MULTI
        assert config.components == [ComponentType.API]
        assert config.health_interval == 2.5

    def test_health_interval_range_validation(self):
        """Test health interval range validation"""
        # Test minimum value
        with pytest.raises(ValidationError):
            LauncherConfigModel(health_interval=0.05)

        # Test maximum value
        with pytest.raises(ValidationError):
            LauncherConfigModel(health_interval=61.0)

        # Test valid value
        config = LauncherConfigModel(health_interval=30.0)
        assert config.health_interval == 30.0

    def test_components_validation(self):
        """Test components list validation"""
        # Test empty list
        with pytest.raises(ValidationError) as exc_info:
            LauncherConfigModel(components=[])
        # Check field location in error
        assert any(e.get("loc") == ("components",) for e in exc_info.value.errors())

        # Test duplicate components
        with pytest.raises(ValidationError) as exc_info:
            LauncherConfigModel(components=[ComponentType.API, ComponentType.API])
        assert any("Duplicate" in e.get("msg", "") for e in exc_info.value.errors())

        # Test invalid component (using string instead of enum)
        with pytest.raises(ValidationError):
            LauncherConfigModel(components=["invalid_component"])

    def test_nested_model_access(self):
        """Test nested model access"""
        config = LauncherConfigModel()

        # Test API config access
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 8000
        assert not config.api.reload

        # Test Agents config access
        assert config.agents.names is None

    def test_nested_model_customization(self):
        """Test nested model customization"""
        api_config = LauncherApiConfig(host="127.0.0.1", port=9000)
        agents_config = LauncherAgentsConfig(names=["worldsmith"])

        config = LauncherConfigModel(api=api_config, agents=agents_config)

        assert config.api.host == "127.0.0.1"
        assert config.api.port == 9000
        assert config.agents.names == ["worldsmith"]

    def test_model_serialization(self):
        """Test model serialization"""
        config = LauncherConfigModel(default_mode=LaunchMode.MULTI, health_interval=2.0)

        data = config.model_dump(mode="json")

        assert data["default_mode"] == "multi"
        assert data["health_interval"] == 2.0
        assert "api" in data
        assert "agents" in data

    def test_model_deserialization(self):
        """Test model deserialization"""
        data = {
            "default_mode": "multi",
            "components": ["api", "agents"],
            "health_interval": 2.0,
            "api": {"host": "127.0.0.1", "port": 9000, "reload": True},
            "agents": {"names": ["worldsmith", "plotmaster"]},
        }

        config = LauncherConfigModel.model_validate(data)

        assert config.default_mode == LaunchMode.MULTI
        assert config.health_interval == 2.0
        assert config.api.host == "127.0.0.1"
        assert config.api.port == 9000
        assert config.agents.names == ["worldsmith", "plotmaster"]
