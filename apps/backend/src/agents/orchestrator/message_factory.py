"""Message Factory for Common Message Patterns

Provides utilities to create common message structures used in the orchestrator,
reducing code duplication and centralizing message format logic.
"""

from __future__ import annotations

from typing import Any

from src.common.events.config import get_message_type, get_strategy_config


class MessageFactory:
    """Factory for creating common message types."""

    @staticmethod
    def create_quality_review_message(
        session_id: str, target_type: str, content: dict[str, Any], scope_prefix: str
    ) -> dict[str, Any]:
        """Create a quality review evaluation request message.

        Args:
            session_id: Session identifier
            target_type: Type of content being reviewed (character, theme, etc.)
            content: Content data to review
            scope_prefix: Scope prefix for topic routing

        Returns:
            Formatted quality review message
        """
        # Use configuration for review strategy
        review_config = get_strategy_config("stage_validation")
        base_topic = review_config["base_topic"] if review_config else "review"

        # 运行时返回字典，类型提示为 CapabilityTaskMessage
        return {
            "type": get_message_type("quality_review"),
            "session_id": session_id,
            "target_type": target_type,
            "input": {"content": content},
            "_topic": f"{scope_prefix.lower()}.{base_topic}.tasks",
            "_key": session_id,
        }

    @staticmethod
    def create_regeneration_message(
        target_type: str, session_id: str, attempts: int, scope_prefix: str
    ) -> dict[str, Any] | None:
        """Create a regeneration task message for content that needs to be regenerated.

        Args:
            target_type: Type of content to regenerate (character, theme)
            session_id: Session identifier
            attempts: Current attempt number
            scope_prefix: Scope prefix for topic routing

        Returns:
            Formatted regeneration message or None if target_type not supported
        """
        # Get strategy configuration for the target type
        strategy_config = get_strategy_config(target_type)
        if not strategy_config:
            return None

        # Use configuration-driven approach
        return {
            "type": strategy_config["capability_type"],
            "session_id": session_id,
            "input": {
                "prompt_adjust": "structured" if target_type == "character" else "detailed",
                "attempt": attempts + 1
            },
            "_topic": f"{scope_prefix.lower()}.{strategy_config['base_topic']}.tasks",
            "_key": session_id,
        }

    @staticmethod
    def get_confirmation_action(target_type: str) -> str:
        """Get the appropriate confirmation action for a target type.

        Args:
            target_type: Type of content being confirmed

        Returns:
            Formatted confirmation action name
        """
        return f"{target_type.capitalize()}.Confirmed" if target_type in {"character", "theme"} else "Stage.Confirmed"

    @staticmethod
    def get_failure_action(target_type: str) -> str:
        """Get the appropriate failure action for a target type.

        Args:
            target_type: Type of content that failed

        Returns:
            Formatted failure action name
        """
        return f"{target_type.capitalize()}.Failed" if target_type in {"character", "theme"} else "Stage.Failed"

    @staticmethod
    def get_regeneration_action(target_type: str) -> str:
        """Get the appropriate regeneration request action for a target type.

        Args:
            target_type: Type of content needing regeneration

        Returns:
            Formatted regeneration action name
        """
        return (
            f"{target_type.capitalize()}.RegenerationRequested"
            if target_type in {"character", "theme"}
            else "Stage.RegenerationRequested"
        )
