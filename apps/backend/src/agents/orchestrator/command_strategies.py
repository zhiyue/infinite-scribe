"""Command Processing Strategies

Uses Strategy pattern with data-driven configuration for better maintainability.
Strategies are now configured through centralized mapping in events/config.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NamedTuple

from src.common.events.config import (
    get_strategy_config,
    get_strategy_keys,
    is_state_change_event,
)
from src.common.events.mapping import (
    build_topic_name,
    extract_strategy_key_from_event_type,
    get_command_aliases_for_action,
)


class CommandMapping(NamedTuple):
    """Represents a command mapping result."""

    requested_action: str
    capability_message: dict[str, Any] | None


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
        return build_topic_name(base_topic, scope_type, scope_prefix)


class GenericRequestStrategy(CommandStrategy):
    """Generic data-driven strategy for request processing."""

    def __init__(self, strategy_key: str) -> None:
        """Initialize with strategy configuration key.

        Args:
            strategy_key: Key from STRATEGY_CONFIG (e.g., "character", "theme")
        """
        self.strategy_key = strategy_key
        self.config = get_strategy_config(strategy_key)
        if not self.config:
            raise ValueError(f"Unknown strategy key: {strategy_key}")

    def get_aliases(self) -> set[str]:
        """Get command aliases for this strategy's requested action."""
        requested_action = self.config["requested_action"]
        return get_command_aliases_for_action(requested_action)

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        """Process command using configuration data."""
        return CommandMapping(
            requested_action=self.config["requested_action"],
            capability_message={
                "type": self.config["capability_type"],
                "session_id": aggregate_id,
                "input": payload,
                "_topic": self._build_topic(self.config["base_topic"], scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class CommandStrategyRegistry:
    """Registry for command strategies with auto-discovery."""

    def __init__(self) -> None:
        self._strategies: dict[str, CommandStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register all default strategies using configuration data."""
        # Create generic strategies for all configured strategy keys
        for strategy_key in get_strategy_keys():
            try:
                strategy = GenericRequestStrategy(strategy_key)
                self.register(strategy)
            except ValueError as e:
                # Log the error but continue with other strategies
                # This prevents total registry failure due to one bad configuration
                import logging

                logging.warning(f"Failed to register strategy '{strategy_key}': {e}")

    def register(self, strategy: CommandStrategy) -> None:
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
            # Check if this is a state-only change that doesn't need capability tasks
            if is_state_change_event(event_type):
                return CommandMapping(requested_action=event_type, capability_message=None)

            # For events that need capability tasks, find appropriate strategy
            strategy = self._strategies.get(cmd_type)
            if not strategy:
                # Try to create strategy based on event type prefix
                strategy_key = extract_strategy_key_from_event_type(event_type)
                if strategy_key and strategy_key in get_strategy_keys():
                    try:
                        strategy = GenericRequestStrategy(strategy_key)
                    except ValueError:
                        # Strategy creation failed, return state-only mapping
                        return CommandMapping(requested_action=event_type, capability_message=None)

            if strategy:
                result = strategy.process(scope_type, scope_prefix, aggregate_id, payload)
                if result and result.capability_message:
                    # Use event_type from configuration for consistency
                    return CommandMapping(requested_action=event_type, capability_message=result.capability_message)
                else:
                    # Strategy exists but couldn't process, return state-only mapping
                    return CommandMapping(requested_action=event_type, capability_message=None)

        # Pure strategy fallback (existing behavior for unmapped commands)
        strategy = self._strategies.get(cmd_type)
        if strategy:
            return strategy.process(scope_type, scope_prefix, aggregate_id, payload)

        return None


# Global registry instance
command_registry = CommandStrategyRegistry()
