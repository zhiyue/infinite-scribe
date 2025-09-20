"""Command Processing Strategies

Uses Strategy pattern for better separation of concerns and testability.
Each command type has its own strategy class with specific logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NamedTuple


class CommandMapping(NamedTuple):
    """Represents a command mapping result."""

    requested_action: str
    capability_message: dict[str, Any]


class CommandStrategy(ABC):
    """Abstract base class for command processing strategies."""

    @abstractmethod
    def get_aliases(self) -> set[str]:
        """Return set of command type aliases this strategy handles."""
        pass

    @abstractmethod
    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        """Process the command and return mapping."""
        pass

    def _build_topic(self, base_topic: str, scope_type: str, scope_prefix: str) -> str:
        """Helper to build topic name based on scope."""
        return (
            f"genesis.{base_topic}.tasks" if scope_type == "GENESIS" else f"{scope_prefix.lower()}.{base_topic}.tasks"
        )


class CharacterRequestStrategy(CommandStrategy):
    """Strategy for character generation requests."""

    def get_aliases(self) -> set[str]:
        return {
            "Character.Request",
            "CHARACTER_REQUEST",
            "Character.Requested",
            "Command.Genesis.Session.Character.Request"
        }

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Character.Requested",
            capability_message={
                "type": "Character.Design.GenerationRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("character", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class ThemeRequestStrategy(CommandStrategy):
    """Strategy for theme generation requests."""

    def get_aliases(self) -> set[str]:
        return {
            "Theme.Request",
            "THEME_REQUEST",
            "Theme.Requested",
            "Command.Genesis.Session.Theme.Request"
        }

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Theme.Requested",
            capability_message={
                "type": "Outliner.Theme.GenerationRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("outline", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class SeedRequestStrategy(CommandStrategy):
    """Strategy for initial seed/concept generation requests."""

    def get_aliases(self) -> set[str]:
        return {
            "Seed.Request",
            "SEED_REQUEST",
            "Seed.Requested",
            "Command.Genesis.Session.Seed.Request"
        }

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Seed.Requested",
            capability_message={
                "type": "Outliner.Concept.GenerationRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("outline", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class WorldRequestStrategy(CommandStrategy):
    """Strategy for world/worldview generation requests."""

    def get_aliases(self) -> set[str]:
        return {
            "World.Request",
            "WORLD_REQUEST",
            "World.Requested",
            "Command.Genesis.Session.World.Request"
        }

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="World.Requested",
            capability_message={
                "type": "Worldbuilder.World.GenerationRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("world", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class PlotRequestStrategy(CommandStrategy):
    """Strategy for plot generation requests."""

    def get_aliases(self) -> set[str]:
        return {
            "Plot.Request",
            "PLOT_REQUEST",
            "Plot.Requested",
            "Command.Genesis.Session.Plot.Request"
        }

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Plot.Requested",
            capability_message={
                "type": "Plot.Structure.GenerationRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("plot", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class DetailsRequestStrategy(CommandStrategy):
    """Strategy for details generation requests."""

    def get_aliases(self) -> set[str]:
        return {
            "Details.Request",
            "DETAILS_REQUEST",
            "Details.Requested",
            "Command.Genesis.Session.Details.Request"
        }

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Details.Requested",
            capability_message={
                "type": "Writer.Content.GenerationRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("writer", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class StageValidationStrategy(CommandStrategy):
    """Strategy for stage validation requests."""

    def get_aliases(self) -> set[str]:
        return {"Stage.Validate", "STAGE_VALIDATE", "ValidateStage"}

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Stage.ValidationRequested",
            capability_message={
                "type": "Review.Consistency.CheckRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("review", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class StageLockStrategy(CommandStrategy):
    """Strategy for stage lock requests."""

    def get_aliases(self) -> set[str]:
        return {"Stage.Lock", "STAGE_LOCK", "LockStage"}

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Stage.LockRequested",
            capability_message={
                "type": "Review.Consistency.CheckRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic("review", scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class CommandStrategyRegistry:
    """Registry for command strategies with auto-discovery."""

    def __init__(self):
        self._strategies: dict[str, CommandStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register all default strategies."""
        strategies = [
            CharacterRequestStrategy(),
            ThemeRequestStrategy(),
            SeedRequestStrategy(),
            WorldRequestStrategy(),
            PlotRequestStrategy(),
            DetailsRequestStrategy(),
            StageValidationStrategy(),
            StageLockStrategy(),
        ]

        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy: CommandStrategy):
        """Register a strategy for its aliases."""
        for alias in strategy.get_aliases():
            self._strategies[alias] = strategy

    def process_command(
        self, cmd_type: str, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]
    ) -> CommandMapping | None:
        """Process a command using unified mapping configuration with strategy fallback."""
        from src.common.events.mapping import get_event_by_command

        # Try configuration mapping first
        event_type = get_event_by_command(cmd_type)
        if event_type:
            # Configuration hit: set requested_action from config, then choose appropriate strategy
            strategy = self._strategies.get(cmd_type)
            if not strategy:
                # Fallback: choose strategy by event_type prefix (e.g., "Character.Requested" -> CharacterRequestStrategy)
                prefix = event_type.split(".", 1)[0].lower()
                strategy = {
                    "character": CharacterRequestStrategy(),
                    "theme": ThemeRequestStrategy(),
                    "seed": SeedRequestStrategy(),
                    "world": WorldRequestStrategy(),
                    "plot": PlotRequestStrategy(),
                    "details": DetailsRequestStrategy(),
                }.get(prefix)
            if strategy:
                result = strategy.process(scope_type, scope_prefix, aggregate_id, payload)
                if result:
                    return CommandMapping(requested_action=event_type, capability_message=result.capability_message)

        # Pure strategy fallback (existing behavior)
        strategy = self._strategies.get(cmd_type)
        if not strategy:
            return None

        return strategy.process(scope_type, scope_prefix, aggregate_id, payload)


# Global registry instance
command_registry = CommandStrategyRegistry()
