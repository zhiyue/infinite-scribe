"""
Standardized error handling for conversation services.

Provides consistent error response formats and logging patterns.
"""

from __future__ import annotations

import logging
from typing import Any


class ConversationErrorHandler:
    """Standardized error handling for conversation services."""

    @staticmethod
    def success_response(data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a standardized success response."""
        response = {"success": True}
        if data:
            response.update(data)
        return response

    @staticmethod
    def error_response(
        message: str,
        code: int = 500,
        logger_instance: logging.Logger | None = None,
        context: str | None = None,
        correlation_id: str | None = None,
        error_type: str | None = None,
        session_id: str | None = None,
        user_id: int | None = None,
        exception: Exception | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Create a standardized error response with enhanced logging and tracing.

        Args:
            message: Human-readable error message
            code: HTTP status code (default: 500)
            logger_instance: Logger instance for error logging
            context: Context string for logging (e.g., "Create round error")
            correlation_id: Request correlation ID for tracing
            error_type: Error classification (business/system/validation)
            session_id: Session ID for context
            user_id: User ID for context
            exception: Exception instance for detailed logging
            **kwargs: Additional data to include in response

        Returns:
            Standardized error response dict
        """
        response = {
            "success": False,
            "error": message,
            "code": code,
        }
        
        # Add correlation_id and error_type to response if provided
        if correlation_id:
            response["correlation_id"] = correlation_id
        if error_type:
            response["error_type"] = error_type

        if kwargs:
            response.update(kwargs)

        # Enhanced logging with context
        if logger_instance and context:
            log_extra = {}
            if correlation_id:
                log_extra["correlation_id"] = correlation_id
            if session_id:
                log_extra["session_id"] = session_id
            if user_id:
                log_extra["user_id"] = user_id
            if error_type:
                log_extra["error_type"] = error_type

            if exception:
                # Use logger.exception to preserve stack trace
                logger_instance.exception(f"{context}: {message}", extra=log_extra)
            else:
                # Determine log level based on HTTP status code
                if 400 <= code < 500:
                    logger_instance.warning(f"{context}: {message}", extra=log_extra)
                else:
                    logger_instance.error(f"{context}: {message}", extra=log_extra)

        return response

    @staticmethod
    def not_found_error(
        resource: str = "Resource", logger_instance: logging.Logger | None = None, context: str | None = None
    ) -> dict[str, Any]:
        """Create a standardized 404 not found error."""
        return ConversationErrorHandler.error_response(
            f"{resource} not found", code=404, logger_instance=logger_instance, context=context
        )

    @staticmethod
    def access_denied_error(
        logger_instance: logging.Logger | None = None, context: str | None = None
    ) -> dict[str, Any]:
        """Create a standardized 403 access denied error."""
        return ConversationErrorHandler.error_response(
            "Access denied", code=403, logger_instance=logger_instance, context=context
        )

    @staticmethod
    def validation_error(
        message: str = "Invalid input data", logger_instance: logging.Logger | None = None, context: str | None = None
    ) -> dict[str, Any]:
        """Create a standardized 422 validation error."""
        return ConversationErrorHandler.error_response(
            message, code=422, logger_instance=logger_instance, context=context
        )

    @staticmethod
    def conflict_error(
        message: str = "Resource conflict", logger_instance: logging.Logger | None = None, context: str | None = None
    ) -> dict[str, Any]:
        """Create a standardized 409 conflict error."""
        return ConversationErrorHandler.error_response(
            message, code=409, logger_instance=logger_instance, context=context
        )

    @staticmethod
    def precondition_failed_error(
        message: str = "Precondition failed", logger_instance: logging.Logger | None = None, context: str | None = None
    ) -> dict[str, Any]:
        """Create a standardized 412 precondition failed error."""
        return ConversationErrorHandler.error_response(
            message, code=412, logger_instance=logger_instance, context=context
        )

    @staticmethod
    def internal_error(
        message: str = "Internal server error",
        logger_instance: logging.Logger | None = None,
        context: str | None = None,
        exception: Exception | None = None,
        correlation_id: str | None = None,
        session_id: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a standardized 500 internal server error with enhanced context.

        Args:
            message: Error message
            logger_instance: Logger for error logging
            context: Context for logging
            exception: Exception instance for detailed logging
            correlation_id: Request correlation ID
            session_id: Session ID for context
            user_id: User ID for context
        """
        return ConversationErrorHandler.error_response(
            message,
            code=500,
            logger_instance=logger_instance,
            context=context,
            exception=exception,
            correlation_id=correlation_id,
            error_type="system",
            session_id=session_id,
            user_id=user_id,
        )
