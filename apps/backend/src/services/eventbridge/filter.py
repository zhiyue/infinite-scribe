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
        r"^Genesis\.Session\.Command\.(Started|Completed|Failed|Progress)$",
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

    # Required data fields (business payload)
    REQUIRED_DATA_FIELDS = [
        "user_id",
        "session_id",
        "timestamp",
    ]

    # Optional data fields that are validated if present
    OPTIONAL_DATA_FIELDS = [
        "novel_id",
    ]

    def __init__(self):
        """Initialize EventFilter with compiled regex patterns."""
        self.compiled_patterns = [re.compile(pattern) for pattern in self.ALLOWED_EVENT_PATTERNS]

    def validate(self, envelope: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate domain event envelope.

        Only supports new nested structure:
        {system: {event_id, event_type, ...}, data: {...}, schema_version}

        Args:
            envelope: Event envelope from Kafka

        Returns:
            Tuple of (is_valid, reason). reason is None if valid.
        """
        try:
            # Check required top-level fields for new structure
            required_top_fields = ["system", "data", "schema_version"]
            for field in required_top_fields:
                if field not in envelope:
                    return False, f"Missing required field: {field}"

            system = envelope["system"]
            data = envelope["data"]

            # Validate system metadata
            validation_result = self._validate_system_metadata(system)
            if validation_result is not None:
                return False, validation_result

            # Validate event type naming convention
            event_type = system["event_type"]
            if not self._validate_event_type(event_type):
                return False, f"event_type must start with 'Genesis.Session', got: {event_type}"

            # Check white-list patterns
            if not self._validate_event_pattern(event_type):
                return False, f"event_type '{event_type}' not in allowed patterns"

            # Validate business data (equivalent to old payload)
            validation_result = self._validate_payload(data)
            if validation_result is not None:
                return False, validation_result

            # Validate UUID fields in system metadata
            validation_result = self._validate_uuid_fields_in_system(system)
            if validation_result is not None:
                return False, validation_result

            return True, None

        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return False, f"Validation error: {e!s}"


    def _validate_system_metadata(self, system: dict[str, Any]) -> str | None:
        """Validate required system metadata fields are present."""
        required_system_fields = ["event_id", "event_type", "aggregate_id"]
        for field in required_system_fields:
            if field not in system:
                return f"Missing required system field: {field}"
        return None

    def _validate_uuid_fields_in_system(self, system: dict[str, Any]) -> str | None:
        """Validate UUID format for UUID fields in system metadata."""
        uuid_fields = ["event_id", "aggregate_id", "correlation_id"]

        for field in uuid_fields:
            if field in system and system[field] is not None:
                try:
                    UUID(system[field])
                except (ValueError, TypeError):
                    return f"system.{field} must be a valid UUID"

        return None


    def _validate_event_type(self, event_type: str) -> bool:
        """Validate event type follows Genesis.Session.* convention."""
        return event_type.startswith("Genesis.Session.")

    def _validate_event_pattern(self, event_type: str) -> bool:
        """Check if event type matches any allowed pattern."""
        return any(pattern.match(event_type) for pattern in self.compiled_patterns)

    def _validate_payload(self, data: dict[str, Any]) -> str | None:
        """Validate required data fields are present and valid."""
        # Check required data fields
        for field in self.REQUIRED_DATA_FIELDS:
            if field not in data:
                return f"Missing required data field: {field}"

        # Validate timestamp format
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return "timestamp must be a valid ISO format"

        # Validate optional UUID fields if present
        for field in self.OPTIONAL_DATA_FIELDS:
            if field in data:
                try:
                    UUID(data[field])
                except (ValueError, TypeError):
                    return f"{field} must be a valid UUID"

        return None

