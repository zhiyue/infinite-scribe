"""Tests for launcher config integration with Settings"""

import pytest
from pydantic import ValidationError
from src.core.config import Settings
from src.launcher.config import LauncherConfigModel
from src.launcher.types import ComponentType, LaunchMode


class TestConfigSystemIntegration:
    """Test configuration system integration"""

    def test_settings_includes_launcher_config(self):
        """Test Settings includes launcher configuration"""
        settings = Settings()
        assert hasattr(settings, "launcher")
        assert isinstance(settings.launcher, LauncherConfigModel)

    def test_launcher_config_defaults_in_settings(self):
        """Test launcher config defaults are correct when accessed via Settings"""
        settings = Settings()
        assert settings.launcher.default_mode == LaunchMode.SINGLE
        assert settings.launcher.components == [ComponentType.API, ComponentType.AGENTS]
        assert settings.launcher.health_interval == 1.0
        assert settings.launcher.api.host == "0.0.0.0"
        assert settings.launcher.api.port == 8000
        assert settings.launcher.agents.names is None

    def test_environment_variable_override(self, monkeypatch):
        """Test environment variable override for launcher config"""
        # Set environment variables following the nested delimiter pattern
        monkeypatch.setenv("LAUNCHER__DEFAULT_MODE", "auto")
        monkeypatch.setenv("LAUNCHER__HEALTH_INTERVAL", "5.0")
        monkeypatch.setenv("LAUNCHER__API__PORT", "9001")

        settings = Settings()

        assert settings.launcher.default_mode == LaunchMode.AUTO
        assert settings.launcher.health_interval == 5.0
        assert settings.launcher.api.port == 9001

    def test_environment_variable_list_parsing(self, monkeypatch):
        """Test list type environment variable (JSON) parsing"""
        monkeypatch.setenv("LAUNCHER__COMPONENTS", '["api"]')
        monkeypatch.setenv("LAUNCHER__AGENTS__NAMES", '["worldsmith","plotmaster"]')

        settings = Settings()

        assert settings.launcher.components == [ComponentType.API]
        assert settings.launcher.agents.names == ["worldsmith", "plotmaster"]

    def test_toml_config_loading(self, tmp_path, monkeypatch):
        """Test TOML configuration loading"""
        # Create a temporary TOML file
        toml_content = """
[launcher]
default_mode = "multi"
health_interval = 2.0

[launcher.api]
host = "127.0.0.1"
port = 9000
reload = true

[launcher.agents]
names = ["worldsmith", "plotmaster"]
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(toml_content)

        # Change working directory to temp directory so TOML loader finds the file
        monkeypatch.chdir(tmp_path)

        settings = Settings()

        assert settings.launcher.default_mode == LaunchMode.MULTI
        assert settings.launcher.health_interval == 2.0
        assert settings.launcher.api.host == "127.0.0.1"
        assert settings.launcher.api.port == 9000
        assert settings.launcher.api.reload is True
        assert settings.launcher.agents.names == ["worldsmith", "plotmaster"]

    def test_configuration_priority(self, tmp_path, monkeypatch):
        """Test configuration priority: env variables > TOML > defaults"""
        # Create TOML file with one value
        toml_content = """
[launcher.api]
port = 8000
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(toml_content)
        monkeypatch.chdir(tmp_path)

        # Set environment variable to override TOML
        monkeypatch.setenv("LAUNCHER__API__PORT", "9001")

        settings = Settings()
        assert settings.launcher.api.port == 9001  # Environment variable wins

    def test_existing_config_compatibility(self):
        """Test that adding launcher config doesn't break existing functionality"""
        settings = Settings()

        # Test that existing config sections still work
        assert hasattr(settings, "auth")
        assert hasattr(settings, "database")
        assert settings.service_name == "infinite-scribe-backend"
        assert settings.api_port == 8000

    def test_environment_variable_components_duplicate_validation(self, monkeypatch):
        """Duplicate components provided via ENV should be rejected by validation."""
        monkeypatch.setenv("LAUNCHER__COMPONENTS", '["api","api"]')

        with pytest.raises(ValidationError) as exc_info:
            Settings()
        # Error message should indicate duplicate components
        assert any("Duplicate" in (e.get("msg") or "") for e in exc_info.value.errors())

    def test_environment_variable_agents_empty_list_rejected(self, monkeypatch):
        """Empty agents list from ENV should be rejected (None is allowed, empty list is not)."""
        monkeypatch.setenv("LAUNCHER__AGENTS__NAMES", "[]")

        with pytest.raises(ValidationError) as exc_info:
            Settings()
        # Error message should indicate empty list is not allowed
        assert any(
            "cannot be empty" in str(e) or "cannot be empty" in (e.get("msg") or "") for e in exc_info.value.errors()
        )
