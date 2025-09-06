"""
Unit tests for EventFilter component.

Tests the event filtering and validation logic for EventBridge.
"""

from datetime import datetime
from uuid import uuid4

from src.services.eventbridge.filter import EventFilter


class TestEventFilter:
    """Test EventFilter component for white-listing and validation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.event_filter = EventFilter()

    def test_event_filter_validates_genesis_events(self):
        """Test that valid Genesis.Session.* events pass validation."""
        valid_envelope = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "metadata": {"trace_id": str(uuid4())},
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "novel_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }

        is_valid, reason = self.event_filter.validate(valid_envelope)
        assert is_valid is True
        assert reason is None

    def test_event_filter_rejects_non_genesis_events(self):
        """Test that non-Genesis events are rejected."""
        invalid_envelope = {
            "event_id": str(uuid4()),
            "event_type": "Chapter.Session.Started",  # Not Genesis
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "metadata": {"trace_id": str(uuid4())},
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }

        is_valid, reason = self.event_filter.validate(invalid_envelope)
        assert is_valid is False
        assert "event_type must start with 'Genesis.Session'" in reason

    def test_event_filter_validates_required_fields(self):
        """Test that missing required fields are caught."""
        # Missing event_id
        incomplete_envelope = {
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }

        is_valid, reason = self.event_filter.validate(incomplete_envelope)
        assert is_valid is False
        assert "Missing required field: event_id" in reason

    def test_event_filter_validates_payload_required_fields(self):
        """Test that missing required payload fields are caught."""
        # Missing user_id in payload
        envelope_missing_user = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }

        is_valid, reason = self.event_filter.validate(envelope_missing_user)
        assert is_valid is False
        assert "Missing required payload field: user_id" in reason

    def test_event_filter_white_list_patterns(self):
        """Test white-list pattern matching for Genesis events."""
        test_cases = [
            ("Genesis.Session.Started", True),
            ("Genesis.Session.Theme.Proposed", True),
            ("Genesis.Session.Character.Confirmed", True),
            ("Genesis.Session.Plot.Updated", True),
            ("Genesis.Session.StageCompleted", True),
            ("Genesis.Session.Finished", True),
            ("Genesis.Session.Failed", True),
            ("Genesis.Session.InvalidAction", False),  # Not in whitelist
            ("Genesis.Other.Started", False),  # Not Session
        ]

        for event_type, should_pass in test_cases:
            envelope = {
                "event_id": str(uuid4()),
                "event_type": event_type,
                "aggregate_id": str(uuid4()),
                "correlation_id": str(uuid4()),
                "payload": {
                    "user_id": str(uuid4()),
                    "session_id": str(uuid4()),
                    "timestamp": datetime.now().isoformat(),
                },
            }

            is_valid, reason = self.event_filter.validate(envelope)
            if should_pass:
                assert is_valid is True, f"Event type {event_type} should pass validation"
                assert reason is None
            else:
                assert is_valid is False, f"Event type {event_type} should fail validation"
                assert reason is not None

    def test_event_filter_handles_malformed_payload(self):
        """Test handling of malformed or missing payload."""
        # Missing payload entirely
        envelope_no_payload = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
        }

        is_valid, reason = self.event_filter.validate(envelope_no_payload)
        assert is_valid is False
        assert "Missing required field: payload" in reason

        # Payload is not a dict
        envelope_invalid_payload = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": "invalid",
        }

        is_valid, reason = self.event_filter.validate(envelope_invalid_payload)
        assert is_valid is False
        assert "payload must be a dictionary" in reason

    def test_event_filter_validates_uuid_format(self):
        """Test that UUID fields are validated for proper format."""
        envelope_invalid_uuid = {
            "event_id": "not-a-uuid",
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }

        is_valid, reason = self.event_filter.validate(envelope_invalid_uuid)
        assert is_valid is False
        assert "event_id must be a valid UUID" in reason

    def test_event_filter_allows_optional_novel_id(self):
        """Test that novel_id in payload is optional but validated if present."""
        # With valid novel_id
        envelope_with_novel = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "novel_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }

        is_valid, reason = self.event_filter.validate(envelope_with_novel)
        assert is_valid is True
        assert reason is None

        # Without novel_id (should still pass)
        envelope_without_novel = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
            },
        }

        is_valid, reason = self.event_filter.validate(envelope_without_novel)
        assert is_valid is True
        assert reason is None

    def test_event_filter_validates_timestamp_format(self):
        """Test that timestamp field is validated for ISO format."""
        envelope_invalid_timestamp = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": "not-a-timestamp",
            },
        }

        is_valid, reason = self.event_filter.validate(envelope_invalid_timestamp)
        assert is_valid is False
        assert "timestamp must be a valid ISO format" in reason
