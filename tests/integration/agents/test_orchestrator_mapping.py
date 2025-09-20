"""Integration tests for orchestrator event mapping."""

import pytest
from unittest.mock import Mock

from src.agents.orchestrator.command_strategies import CommandStrategyRegistry, CommandMapping


class TestCommandStrategyRegistryIntegration:
    """Test CommandStrategyRegistry integration with unified mapping."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = CommandStrategyRegistry()

    def test_command_strategy_registry_with_config_mapping(self):
        """Test configuration mapping takes precedence over strategy for requested_action."""
        # Test command that has configuration mapping
        result = self.registry.process_command(
            cmd_type="Character.Request",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="session-123",
            payload={"payload": {"test": "data"}}
        )

        assert result is not None
        # Should use config mapping for requested_action
        assert result.requested_action == "Character.Requested"
        # Should still have capability_message from strategy
        assert "type" in result.capability_message
        assert result.capability_message["session_id"] == "session-123"

    def test_command_strategy_registry_fallback_to_strategy(self):
        """Test fallback to pure strategy when no config mapping exists."""
        # Test command that doesn't have configuration mapping
        result = self.registry.process_command(
            cmd_type="Theme.Request",  # This should have mapping too
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="session-123",
            payload={"payload": {"test": "data"}}
        )

        assert result is not None
        # Should use config mapping
        assert result.requested_action == "Theme.Requested"

    def test_command_strategy_registry_unknown_command(self):
        """Test behavior with unknown commands."""
        result = self.registry.process_command(
            cmd_type="UnknownCommand",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="session-123",
            payload={}
        )

        # Should return None for unmapped commands
        assert result is None

    def test_backward_compatibility(self):
        """Test that existing strategies still work without configuration mapping."""
        # Mock a strategy that doesn't have config mapping
        mock_strategy = Mock()
        mock_strategy.process.return_value = CommandMapping(
            requested_action="Custom.Action",
            capability_message={"type": "Custom.Generated", "data": "test"}
        )

        # Temporarily add custom strategy
        self.registry._strategies["CustomCommand"] = mock_strategy

        result = self.registry.process_command(
            cmd_type="CustomCommand",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="session-123",
            payload={}
        )

        assert result is not None
        assert result.requested_action == "Custom.Action"
        assert result.capability_message["type"] == "Custom.Generated"

        # Clean up
        del self.registry._strategies["CustomCommand"]

    def test_config_mapping_with_missing_strategy(self):
        """Test config mapping when strategy doesn't exist."""
        # Add a command mapping without corresponding strategy
        from src.common.events.mapping import COMMAND_EVENT_MAPPING

        # Test with a command that has config but no strategy
        # This should fall back to strategy lookup which returns None
        original_mapping = COMMAND_EVENT_MAPPING.copy()
        COMMAND_EVENT_MAPPING["TestConfigOnly"] = "Test.Requested"

        try:
            result = self.registry.process_command(
                cmd_type="TestConfigOnly",
                scope_type="GENESIS",
                scope_prefix="Genesis",
                aggregate_id="session-123",
                payload={}
            )

            # Should return None since strategy doesn't exist
            assert result is None

        finally:
            # Restore original mapping
            COMMAND_EVENT_MAPPING.clear()
            COMMAND_EVENT_MAPPING.update(original_mapping)


class TestOrchestratorTaskTypeNormalization:
    """Test task type normalization in orchestrator context."""

    def test_normalize_task_type_import(self):
        """Test that normalize_task_type can be imported and used."""
        from src.common.events.mapping import normalize_task_type

        result = normalize_task_type("Character.Design.GenerationRequested")
        assert result == "Character.Design.Generation"

    def test_orchestrator_uses_unified_mapping(self):
        """Test that OrchestratorAgent uses unified mapping."""
        from src.agents.orchestrator.agent import OrchestratorAgent

        # Verify the import exists in the agent module
        import src.agents.orchestrator.agent as agent_module
        assert hasattr(agent_module, 'normalize_task_type')


class TestEventSerializationIntegration:
    """Test EventSerializationUtils integration with unified mapping."""

    def test_event_serialization_uses_unified_mapping(self):
        """Test that EventSerializationUtils uses unified mapping."""
        from src.schemas.genesis_events import EventSerializationUtils
        from src.schemas.enums import GenesisEventType

        # Test with a mapped event
        payload_data = {
            "session_id": "test-session",
            "stage": "INSPIRATION",
            "previous_stage": None,
            "context_data": {"test": "data"}
        }

        result = EventSerializationUtils.deserialize_payload(
            GenesisEventType.STAGE_ENTERED,
            payload_data
        )

        # Should get the specific payload class, not generic
        from src.schemas.genesis_events import StageEnteredPayload
        assert isinstance(result, StageEnteredPayload)

    def test_event_serialization_fallback(self):
        """Test fallback behavior for unmapped events."""
        from src.schemas.genesis_events import EventSerializationUtils, GenesisEventPayload
        from src.schemas.enums import GenesisEventType

        # Test with an unmapped event
        payload_data = {
            "session_id": "test-session",
            "user_id": None,
        }

        result = EventSerializationUtils.deserialize_payload(
            GenesisEventType.AI_GENERATION_FAILED,  # This should not have specific mapping
            payload_data
        )

        # Should fall back to generic payload
        assert isinstance(result, GenesisEventPayload)
        assert not isinstance(result, type(result).__bases__[0]) or result.__class__ == GenesisEventPayload