"""Message Factory for Common Message Patterns

Provides utilities to create common message structures used in the orchestrator,
reducing code duplication and centralizing message format logic.
"""

from __future__ import annotations

from typing import Any


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
        return {
            "type": "Review.Quality.EvaluationRequested",
            "session_id": session_id,
            "target_type": target_type,
            "input": {"content": content},
            "_topic": f"{scope_prefix.lower()}.review.tasks",
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
        if target_type == "character":
            return {
                "type": "Character.Design.GenerationRequested",
                "session_id": session_id,
                "input": {"prompt_adjust": "structured", "attempt": attempts + 1},
                "_topic": f"{scope_prefix.lower()}.character.tasks",
                "_key": session_id,
            }

        elif target_type == "theme":
            return {
                "type": "Outliner.Theme.GenerationRequested",
                "session_id": session_id,
                "input": {"prompt_adjust": "detailed", "attempt": attempts + 1},
                "_topic": f"{scope_prefix.lower()}.outline.tasks",
                "_key": session_id,
            }

        return None

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
