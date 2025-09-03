"""Tests for launcher configuration models"""

import pytest
from pydantic import ValidationError
from src.launcher.config import LauncherAgentsConfig, LauncherApiConfig


class TestLauncherApiConfig:
    """Test API configuration model"""

    def test_default_values(self):
        """Test API config default values"""
        config = LauncherApiConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.reload is False

    def test_custom_values(self):
        """Test API config custom values"""
        config = LauncherApiConfig(host="127.0.0.1", port=9000, reload=True)
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.reload is True

    def test_port_range_validation(self):
        """Test port range validation"""
        # Test below minimum valid port
        with pytest.raises(ValidationError):
            LauncherApiConfig(port=1023)

        # Test above maximum valid port
        with pytest.raises(ValidationError):
            LauncherApiConfig(port=65536)

        # Test valid port range
        config = LauncherApiConfig(port=8080)
        assert config.port == 8080

    def test_field_type_validation(self):
        """Test field type validation"""
        with pytest.raises(ValidationError):
            LauncherApiConfig(host=123)

        with pytest.raises(ValidationError):
            LauncherApiConfig(port="invalid")

        with pytest.raises(ValidationError):
            LauncherApiConfig(reload="maybe")


class TestLauncherAgentsConfig:
    """Test Agents configuration model"""

    def test_default_values(self):
        """Test Agents config default values"""
        config = LauncherAgentsConfig()
        assert config.names is None

    def test_valid_names_list(self):
        """Test valid agent names list"""
        names = ["worldsmith", "plotmaster"]
        config = LauncherAgentsConfig(names=names)
        assert config.names == names
        assert len(config.names) == 2

    def test_empty_list_rejection(self):
        """Test empty list rejection"""
        with pytest.raises(ValidationError) as exc_info:
            LauncherAgentsConfig(names=[])
        assert "cannot be empty" in str(exc_info.value)

    def test_invalid_name_format_rejection(self):
        """Test invalid name format rejection"""
        # Test special characters
        with pytest.raises(ValidationError) as exc_info:
            LauncherAgentsConfig(names=["invalid@name"])
        assert "Invalid agent name" in str(exc_info.value)

        # Test multiple invalid characters
        with pytest.raises(ValidationError):
            LauncherAgentsConfig(names=["name-with-special#chars"])

    def test_name_length_limit(self):
        """Test name length limit"""
        long_name = "a" * 51
        with pytest.raises(ValidationError) as exc_info:
            LauncherAgentsConfig(names=[long_name])
        assert "too long" in str(exc_info.value)

        # Test boundary value - valid name
        valid_name = "a" * 50
        config = LauncherAgentsConfig(names=[valid_name])
        assert config.names == [valid_name]

    def test_valid_name_patterns(self):
        """Test valid name patterns"""
        valid_names = [
            "simple_name",
            "name-with-hyphens",
            "name123",
            "Name_With_Caps",
            "a",  # Minimum length
            "a" * 50,  # Maximum length
        ]
        config = LauncherAgentsConfig(names=valid_names)
        assert config.names == valid_names
