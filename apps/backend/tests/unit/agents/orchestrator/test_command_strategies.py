"""Unit tests for command strategies.

Demonstrates the excellent testability of the Strategy pattern.
Each strategy can be tested independently with clear test cases.
"""

import pytest
from src.agents.orchestrator.command_strategies import (
    CharacterRequestStrategy,
    CommandStrategyRegistry,
    DetailsRequestStrategy,
    PlotRequestStrategy,
    SeedRequestStrategy,
    StageLockStrategy,
    StageValidationStrategy,
    ThemeRequestStrategy,
    WorldRequestStrategy,
)


class TestCharacterRequestStrategy:
    """Tests for character request strategy."""

    def setup_method(self):
        self.strategy = CharacterRequestStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {
            "Character.Request",
            "CHARACTER_REQUEST",
            "Character.Requested",
            "Command.Genesis.Session.Character.Request"
        }
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
        expected_aliases = {
            "Theme.Request",
            "THEME_REQUEST",
            "Theme.Requested",
            "Command.Genesis.Session.Theme.Request"
        }
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


class TestSeedRequestStrategy:
    """Tests for seed request strategy."""

    def setup_method(self):
        self.strategy = SeedRequestStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {
            "Seed.Request",
            "SEED_REQUEST",
            "Seed.Requested",
            "Command.Genesis.Session.Seed.Request"
        }
        assert self.strategy.get_aliases() == expected_aliases

    def test_process_genesis_scope(self):
        """Test seed request processing in Genesis scope."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-seed-123",
            payload={"payload": {"initial_input": "Write a fantasy novel"}},
        )

        assert mapping.requested_action == "Seed.Requested"
        assert mapping.capability_message["type"] == "Outliner.Concept.GenerationRequested"
        assert mapping.capability_message["session_id"] == "test-seed-123"
        assert mapping.capability_message["input"] == {"initial_input": "Write a fantasy novel"}
        assert mapping.capability_message["_topic"] == "genesis.outline.tasks"
        assert mapping.capability_message["_key"] == "test-seed-123"


class TestWorldRequestStrategy:
    """Tests for world request strategy."""

    def setup_method(self):
        self.strategy = WorldRequestStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {
            "World.Request",
            "WORLD_REQUEST",
            "World.Requested",
            "Command.Genesis.Session.World.Request"
        }
        assert self.strategy.get_aliases() == expected_aliases

    def test_process_genesis_scope(self):
        """Test world request processing in Genesis scope."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-world-456",
            payload={"payload": {"world_type": "medieval fantasy"}},
        )

        assert mapping.requested_action == "World.Requested"
        assert mapping.capability_message["type"] == "Worldbuilder.World.GenerationRequested"
        assert mapping.capability_message["session_id"] == "test-world-456"
        assert mapping.capability_message["input"] == {"world_type": "medieval fantasy"}
        assert mapping.capability_message["_topic"] == "genesis.world.tasks"
        assert mapping.capability_message["_key"] == "test-world-456"


class TestPlotRequestStrategy:
    """Tests for plot request strategy."""

    def setup_method(self):
        self.strategy = PlotRequestStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {
            "Plot.Request",
            "PLOT_REQUEST",
            "Plot.Requested",
            "Command.Genesis.Session.Plot.Request"
        }
        assert self.strategy.get_aliases() == expected_aliases

    def test_process_genesis_scope(self):
        """Test plot request processing in Genesis scope."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-plot-789",
            payload={"payload": {"plot_structure": "three-act"}},
        )

        assert mapping.requested_action == "Plot.Requested"
        assert mapping.capability_message["type"] == "Plot.Structure.GenerationRequested"
        assert mapping.capability_message["session_id"] == "test-plot-789"
        assert mapping.capability_message["input"] == {"plot_structure": "three-act"}
        assert mapping.capability_message["_topic"] == "genesis.plot.tasks"
        assert mapping.capability_message["_key"] == "test-plot-789"


class TestDetailsRequestStrategy:
    """Tests for details request strategy."""

    def setup_method(self):
        self.strategy = DetailsRequestStrategy()

    def test_aliases_are_correct(self):
        """Test that the strategy handles correct aliases."""
        expected_aliases = {
            "Details.Request",
            "DETAILS_REQUEST",
            "Details.Requested",
            "Command.Genesis.Session.Details.Request"
        }
        assert self.strategy.get_aliases() == expected_aliases

    def test_process_genesis_scope(self):
        """Test details request processing in Genesis scope."""
        mapping = self.strategy.process(
            scope_type="GENESIS",
            scope_prefix="Genesis",
            aggregate_id="test-details-101",
            payload={"payload": {"detail_level": "comprehensive"}},
        )

        assert mapping.requested_action == "Details.Requested"
        assert mapping.capability_message["type"] == "Writer.Content.GenerationRequested"
        assert mapping.capability_message["session_id"] == "test-details-101"
        assert mapping.capability_message["input"] == {"detail_level": "comprehensive"}
        assert mapping.capability_message["_topic"] == "genesis.writer.tasks"
        assert mapping.capability_message["_key"] == "test-details-101"


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
