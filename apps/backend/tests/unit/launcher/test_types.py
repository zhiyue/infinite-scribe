"""Tests for launcher types module"""

from src.launcher.types import ComponentType, LaunchMode


class TestLaunchModeEnum:
    """Test launch mode enumeration"""

    def test_enum_values(self):
        """Test enum values are correct"""
        assert LaunchMode.SINGLE.value == "single"
        assert LaunchMode.MULTI.value == "multi"
        assert LaunchMode.AUTO.value == "auto"

    def test_enum_values_are_strings(self):
        """Test enum values are string types"""
        assert isinstance(LaunchMode.SINGLE.value, str)
        assert isinstance(LaunchMode.MULTI.value, str)
        assert isinstance(LaunchMode.AUTO.value, str)


class TestComponentTypeEnum:
    """Test component type enumeration"""

    def test_component_type_enum_values(self):
        """Test component type enum values"""
        assert ComponentType.API.value == "api"
        assert ComponentType.AGENTS.value == "agents"
        assert ComponentType.RELAY.value == "relay"

    def test_component_type_values_are_strings(self):
        """Test component type enum values are strings"""
        assert isinstance(ComponentType.API.value, str)
        assert isinstance(ComponentType.AGENTS.value, str)
        assert isinstance(ComponentType.RELAY.value, str)

    def test_component_type_enum_completeness(self):
        """Test that all expected component types are present"""
        values = [component.value for component in ComponentType]
        assert "api" in values
        assert "agents" in values
        assert "relay" in values
        assert "eventbridge" in values
        assert len(values) == 4  # Four components supported  # Exactly three components supported
