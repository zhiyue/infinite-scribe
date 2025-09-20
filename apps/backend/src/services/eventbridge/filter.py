"""
EventFilter for validating and filtering domain events.

This module implements event filtering and validation logic for the EventBridge
service, ensuring only valid Genesis.Session.* events are processed.
"""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.logging import get_logger

logger = get_logger(__name__)


class EventFilter:
    """
    Event filter and validator for EventBridge.

    Validates domain events against:
    - Event type naming convention (Genesis.Session.*)
    - White-list patterns for allowed events
    - Required field validation
    - Data type validation
    """

    # White-listed event patterns (regex patterns)
    ALLOWED_EVENT_PATTERNS = [
        r"^Genesis\.Session\.Started$",
        r"^Genesis\.Session\.Command\.Received$",
        r"^Genesis\.Session\..*\.Requested$",
        r"^Genesis\.Session\..*\.Generated$",
        r"^Genesis\.Session\..*\.Evaluated$",
        r"^Genesis\.Session\..*\.Proposed$",
        r"^Genesis\.Session\..*\.Confirmed$",
        r"^Genesis\.Session\..*\.Updated$",
        r"^Genesis\.Session\..*\.Revised$",
        r"^Genesis\.Session\..*\.Created$",
        r"^Genesis\.Session\.StageCompleted$",
        r"^Genesis\.Session\.Finished$",
        r"^Genesis\.Session\.Failed$",
        r"^Genesis\.Session\.BranchCreated$",
    ]

    # Required envelope fields
    REQUIRED_ENVELOPE_FIELDS = [
        "event_id",
        "event_type",
        "aggregate_id",
        "correlation_id",
        "payload",
    ]

    # Required payload fields
    REQUIRED_PAYLOAD_FIELDS = [
        "user_id",
        "session_id",
        "timestamp",
    ]

    # Optional payload fields that are validated if present
    OPTIONAL_PAYLOAD_FIELDS = [
        "novel_id",
    ]

    def __init__(self):
        """Initialize EventFilter with compiled regex patterns."""
        self.compiled_patterns = [re.compile(pattern) for pattern in self.ALLOWED_EVENT_PATTERNS]

    def validate(self, envelope: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate domain event envelope.

        Args:
            envelope: Event envelope from Kafka

        Returns:
            Tuple of (is_valid, reason). reason is None if valid.
        """
        try:
            # Check required envelope fields
            validation_result = self._validate_envelope_fields(envelope)
            if validation_result is not None:
                return False, validation_result

            # Validate event type naming convention
            event_type = envelope["event_type"]
            if not self._validate_event_type(event_type):
                return False, f"event_type must start with 'Genesis.Session', got: {event_type}"

            # Check white-list patterns
            if not self._validate_event_pattern(event_type):
                return False, f"event_type '{event_type}' not in allowed patterns"

            # Validate payload
            payload = envelope["payload"]
            validation_result = self._validate_payload(payload)
            if validation_result is not None:
                return False, validation_result

            # Validate UUID fields
            validation_result = self._validate_uuid_fields(envelope)
            if validation_result is not None:
                return False, validation_result

            return True, None

        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return False, f"Validation error: {e!s}"

    def _validate_envelope_fields(self, envelope: dict[str, Any]) -> str | None:
        """Validate required envelope fields are present."""
        for field in self.REQUIRED_ENVELOPE_FIELDS:
            if field not in envelope:
                return f"Missing required field: {field}"

        # Validate payload is a dictionary
        if not isinstance(envelope["payload"], dict):
            return "payload must be a dictionary"

        return None

    def _validate_event_type(self, event_type: str) -> bool:
        """Validate event type follows Genesis.Session.* convention."""
        return event_type.startswith("Genesis.Session.")

    def _validate_event_pattern(self, event_type: str) -> bool:
        """Check if event type matches any allowed pattern."""
        return any(pattern.match(event_type) for pattern in self.compiled_patterns)

    def _validate_payload(self, payload: dict[str, Any]) -> str | None:
        """Validate required payload fields are present and valid."""
        # Check required payload fields
        for field in self.REQUIRED_PAYLOAD_FIELDS:
            if field not in payload:
                return f"Missing required payload field: {field}"

        # Validate timestamp format
        try:
            datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return "timestamp must be a valid ISO format"

        # Validate optional UUID fields if present
        for field in self.OPTIONAL_PAYLOAD_FIELDS:
            if field in payload:
                try:
                    UUID(payload[field])
                except (ValueError, TypeError):
                    return f"{field} must be a valid UUID"

        return None

    def _validate_uuid_fields(self, envelope: dict[str, Any]) -> str | None:
        """Validate UUID format for UUID fields."""
        uuid_fields = ["event_id", "aggregate_id", "correlation_id"]
        payload = envelope["payload"]
        payload_uuid_fields = ["user_id", "session_id"]

        # Validate envelope UUID fields
        for field in uuid_fields:
            if field in envelope:
                try:
                    UUID(envelope[field])
                except (ValueError, TypeError):
                    return f"{field} must be a valid UUID"

        # Validate payload UUID fields
        for field in payload_uuid_fields:
            if field in payload:
                try:
                    UUID(payload[field])
                except (ValueError, TypeError):
                    return f"{field} must be a valid UUID"

        return None
