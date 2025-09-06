"""Unit tests for command strategies.

Demonstrates the excellent testability of the Strategy pattern.
Each strategy can be tested independently with clear test cases.
"""

import pytest
from src.agents.orchestrator.command_strategies import (
    CharacterRequestStrategy,
    CommandStrategyRegistry,
    StageLockStrategy,
    StageValidationStrategy,
    ThemeRequestStrategy,
)


class TestCharacterRequestStrategy:
    """Tests for character request strategy."""

    def setup_method(self):
        self.strategy = CharacterRequestStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {"Character.Request", "CHARACTER_REQUEST", "Character.Requested"}
        assert self.strategy.get_aliases() == expected_aliases

    def test_process_genesis_scope(self):
        """Test character request processing in Genesis scope."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-123",
            payload={"payload": {"character_type": "hero"}},
        )

        assert mapping.requested_action == "Character.Requested"
        assert mapping.capability_message["type"] == "Character.Design.GenerationRequested"
        assert mapping.capability_message["session_id"] == "test-123"
        assert mapping.capability_message["input"] == {"character_type": "hero"}
        assert mapping.capability_message["_topic"] == "genesis.character.tasks"
        assert mapping.capability_message["_key"] == "test-123"

    def test_process_custom_scope(self):
        """Test character request processing in custom scope."""
        mapping = self.strategy.process(
            scope_type="NOVEL",
            scope_prefix="Novel",
            aggregate_id="test-456",
            payload={"payload": {"character_name": "Alice"}},
        )

        assert mapping.capability_message["_topic"] == "novel.character.tasks"


class TestThemeRequestStrategy:
    """Tests for theme request strategy."""

    def setup_method(self):
        self.strategy = ThemeRequestStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {"Theme.Request", "THEME_REQUEST", "Theme.Requested"}
        assert self.strategy.get_aliases() == expected_aliases

    def test_process_creates_correct_mapping(self):
        """Test theme request processing."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="theme-789",
            payload={"payload": {"theme_type": "dark fantasy"}},
        )

        assert mapping.requested_action == "Theme.Requested"
        assert mapping.capability_message["type"] == "Outliner.Theme.GenerationRequested"
        assert mapping.capability_message["_topic"] == "genesis.outline.tasks"


class TestStageValidationStrategy:
    """Tests for stage validation strategy."""

    def setup_method(self):
        self.strategy = StageValidationStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {"Stage.Validate", "STAGE_VALIDATE", "ValidateStage"}
        assert self.strategy.get_aliases() == expected_aliases

    def test_process_creates_validation_mapping(self):
        """Test stage validation processing."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="stage-101",
            payload={"payload": {"stage_data": "test"}},
        )

        assert mapping.requested_action == "Stage.ValidationRequested"
        assert mapping.capability_message["type"] == "Review.Consistency.CheckRequested"
        assert mapping.capability_message["_topic"] == "genesis.review.tasks"


class TestStageLockStrategy:
    """Tests for stage lock strategy."""

    def setup_method(self):
        self.strategy = StageLockStrategy()

    def test_process_creates_lock_mapping(self):
        """Test stage lock processing."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="stage-202",
            payload={"payload": {}},
        )

        assert mapping.requested_action == "Stage.LockRequested"
        assert mapping.capability_message["type"] == "Review.Consistency.CheckRequested"


class TestCommandStrategyRegistry:
    """Tests for command strategy registry."""

    def setup_method(self):
        self.registry = CommandStrategyRegistry()

    def test_processes_character_request(self):
        """Test registry processes character requests correctly."""
        mapping = self.registry.process_command(
            cmd_type="Character.Request",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="char-123",
            payload={"payload": {"test": "data"}},
        )

        assert mapping is not None
        assert mapping.requested_action == "Character.Requested"

    def test_processes_theme_request(self):
        """Test registry processes theme requests correctly."""
        mapping = self.registry.process_command(
            cmd_type="THEME_REQUEST",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="theme-456",
            payload={"payload": {}},
        )

        assert mapping is not None
        assert mapping.requested_action == "Theme.Requested"

    def test_processes_stage_validation(self):
        """Test registry processes stage validation correctly."""
        mapping = self.registry.process_command(
            cmd_type="ValidateStage",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="stage-789",
            payload={"payload": {}},
        )

        assert mapping is not None
        assert mapping.requested_action == "Stage.ValidationRequested"

    def test_unknown_command_returns_none(self):
        """Test unknown command types return None."""
        mapping = self.registry.process_command(
            cmd_type="Unknown.Command",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-000",
            payload={},
        )

        assert mapping is None

    def test_empty_payload_handled_gracefully(self):
        """Test empty payloads are handled gracefully."""
        mapping = self.registry.process_command(
            cmd_type="Character.Request",
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-empty",
            payload={},  # Empty payload
        )

        assert mapping is not None
        assert mapping.capability_message["input"] == {}

    @pytest.mark.parametrize(
        "cmd_type,expected_action",
        [
            ("Character.Request", "Character.Requested"),
            ("CHARACTER_REQUEST", "Character.Requested"),
            ("Character.Requested", "Character.Requested"),
            ("Theme.Request", "Theme.Requested"),
            ("THEME_REQUEST", "Theme.Requested"),
            ("Stage.Validate", "Stage.ValidationRequested"),
            ("Stage.Lock", "Stage.LockRequested"),
        ],
    )
    def test_command_alias_mapping(self, cmd_type, expected_action):
        """Test all command aliases map to correct actions."""
        mapping = self.registry.process_command(
            cmd_type=cmd_type,
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-param",
            payload={"payload": {}},
        )

        assert mapping is not None
        assert mapping.requested_action == expected_action
