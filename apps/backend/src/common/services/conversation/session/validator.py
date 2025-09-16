"""
Session validation logic for conversation services.

Handles validation of session creation and update parameters.
"""

from __future__ import annotations

import logging
from typing import Any

from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.schemas.novel.dialogue import ScopeType

logger = logging.getLogger(__name__)


class ConversationSessionValidator:
    """Validator for conversation session operations."""

    @staticmethod
    def validate_and_normalize_scope_type(
        scope_type: ScopeType | str, user_id: int, scope_id: str
    ) -> tuple[dict[str, Any] | None, ScopeType | None, str | None]:
        """
        Validate and normalize scope type from string or enum.

        Args:
            scope_type: Scope type as string or enum
            user_id: User ID for logging context
            scope_id: Scope ID for logging context

        Returns:
            Tuple of (error_response, scope_type_enum, scope_type_str)
            - error_response: Error dict if validation fails, None if successful
            - scope_type_enum: Normalized enum value
            - scope_type_str: String representation
        """
        if isinstance(scope_type, str):
            scope_type_str = scope_type
            try:
                scope_type_enum = ScopeType(scope_type)
            except ValueError:
                logger.warning(
                    "Invalid scope type provided for session creation",
                    extra={
                        "provided_scope_type": scope_type,
                        "valid_scope_types": [e.value for e in ScopeType],
                        "user_id": user_id,
                        "scope_id": scope_id,
                        "operation": "create_session_validation",
                    },
                )
                error_response = ConversationErrorHandler.validation_error(
                    f"Invalid scope type: {scope_type}",
                    logger_instance=logger,
                    context=f"Session validation - invalid scope type: {scope_type}",
                )
                return error_response, None, None
        else:
            scope_type_enum = scope_type
            scope_type_str = scope_type.value

        return None, scope_type_enum, scope_type_str

    @staticmethod
    def validate_supported_scope_type(
        scope_type_enum: ScopeType, scope_type_str: str, user_id: int, scope_id: str
    ) -> dict[str, Any] | None:
        """
        Validate that the scope type is supported for session operations.

        Args:
            scope_type_enum: Scope type enum
            scope_type_str: Scope type string
            user_id: User ID for logging context
            scope_id: Scope ID for logging context

        Returns:
            Error dict if validation fails, None if successful
        """
        if scope_type_enum != ScopeType.GENESIS:
            logger.warning(
                "Unsupported scope type for session creation",
                extra={
                    "scope_type": scope_type_str,
                    "supported_scope_types": [ScopeType.GENESIS.value],
                    "user_id": user_id,
                    "scope_id": scope_id,
                    "operation": "session_validation",
                },
            )
            return ConversationErrorHandler.validation_error(
                "Only GENESIS scope is supported",
                logger_instance=logger,
                context=f"Session validation - unsupported scope: {scope_type_str}",
            )
        return None

    @staticmethod
    def validate_session_update_params(status: Any, stage: Any, state: Any) -> tuple[bool, dict[str, Any] | None]:
        """
        Validate session update parameters and determine if update is needed.

        Args:
            status: New status value
            stage: New stage value
            state: New state value

        Returns:
            Tuple of (needs_update, error_response)
            - needs_update: True if there are valid parameters to update
            - error_response: Error dict if validation fails, None if successful
        """
        # Check if there are no values to update
        if status is None and stage is None and state is None:
            return False, None

        # Additional parameter validation can be added here
        # For now, we accept any non-None values
        return True, None
