"""Unit tests for command status consumer retry logic fixes."""

import pytest
from unittest.mock import Mock

from src.services.command.command_status_consumer import CommandStatusConsumer


class TestCommandStatusConsumerFixes:
    """Test fixes for command status consumer retry logic."""

    @pytest.fixture
    def consumer(self):
        """Create command status consumer instance."""
        mock_session_factory = Mock()
        mock_event_publisher = Mock()
        return CommandStatusConsumer(
            session_factory=mock_session_factory,
            event_publisher=mock_event_publisher,
            batch_size=10,
            max_retries=3,
            retry_delay_seconds=1
        )

    def test_should_retry_with_retryable_errors(self, consumer):
        """Test that retryable errors allow retry."""
        retryable_errors = [
            "Network timeout occurred",
            "Database connection failed",
            "Temporary service unavailable",
            "Processing failed with exception"
        ]

        for error in retryable_errors:
            assert consumer._should_retry(error, retry_count=0) is True
            assert consumer._should_retry(error, retry_count=1) is True
            assert consumer._should_retry(error, retry_count=2) is True

    def test_should_retry_with_non_retryable_errors(self, consumer):
        """Test that non-retryable errors prevent retry."""
        non_retryable_errors = [
            "Invalid event format",
            "Missing command identifier",
            "Missing command_id in event",
            "Unknown event type",
            "Invalid command_id format",
            "Command not found",
            "badly formed hexadecimal UUID string"  # New fix
        ]

        for error in non_retryable_errors:
            assert consumer._should_retry(error, retry_count=0) is False
            assert consumer._should_retry(error, retry_count=1) is False
            assert consumer._should_retry(error, retry_count=2) is False

    def test_should_retry_max_retries_exceeded(self, consumer):
        """Test that max retries prevents retry even for retryable errors."""
        retryable_error = "Network timeout occurred"

        # Should retry within limits
        assert consumer._should_retry(retryable_error, retry_count=0) is True
        assert consumer._should_retry(retryable_error, retry_count=1) is True
        assert consumer._should_retry(retryable_error, retry_count=2) is True

        # Should not retry when max retries reached
        assert consumer._should_retry(retryable_error, retry_count=3) is False
        assert consumer._should_retry(retryable_error, retry_count=4) is False

    def test_should_retry_with_uuid_error_messages(self, consumer):
        """Test specific UUID error handling."""
        uuid_errors = [
            "Processing error: badly formed hexadecimal UUID string",
            "ValueError: badly formed hexadecimal UUID string: 'invalid-uuid'",
            "UUID parsing failed: badly formed hexadecimal UUID string"
        ]

        for error in uuid_errors:
            assert consumer._should_retry(error, retry_count=0) is False
            assert consumer._should_retry(error, retry_count=1) is False

    def test_should_retry_with_command_not_found_variations(self, consumer):
        """Test command not found error variations."""
        command_errors = [
            "Command not found",
            "Command not found: 12345678-1234-1234-1234-123456789abc",
            "Processing failed: Command not found"
        ]

        for error in command_errors:
            assert consumer._should_retry(error, retry_count=0) is False

    def test_should_retry_with_invalid_format_variations(self, consumer):
        """Test invalid format error variations."""
        format_errors = [
            "Invalid event format",
            "Invalid command_id format",
            "Invalid command_id format: not-a-uuid",
            "Missing command_id in event",
            "Missing command identifier"
        ]

        for error in format_errors:
            assert consumer._should_retry(error, retry_count=0) is False

    def test_should_retry_partial_matches(self, consumer):
        """Test that partial matches work correctly."""
        # Errors containing non-retryable substrings should not retry
        partial_errors = [
            "Error occurred: Invalid event format detected",
            "Failed processing: Command not found in database",
            "Exception: badly formed hexadecimal UUID string encountered"
        ]

        for error in partial_errors:
            assert consumer._should_retry(error, retry_count=0) is False

    def test_should_retry_case_sensitivity(self, consumer):
        """Test that error matching is case sensitive."""
        # These should be retryable because case doesn't match
        case_different_errors = [
            "INVALID EVENT FORMAT",
            "Command Not Found",
            "missing command_id in event"
        ]

        for error in case_different_errors:
            assert consumer._should_retry(error, retry_count=0) is True

    def test_should_retry_with_empty_error(self, consumer):
        """Test behavior with empty error message."""
        assert consumer._should_retry("", retry_count=0) is True
        assert consumer._should_retry(None, retry_count=0) is True

    def test_should_retry_with_whitespace_only_error(self, consumer):
        """Test behavior with whitespace-only error message."""
        assert consumer._should_retry("   ", retry_count=0) is True
        assert consumer._should_retry("\t\n", retry_count=0) is True

    def test_non_retryable_errors_list_completeness(self, consumer):
        """Test that all expected non-retryable errors are in the list."""
        # Access the non_retryable_errors list from the method
        # This is a bit of implementation detail testing, but ensures consistency
        expected_errors = [
            "Invalid event format",
            "Missing command identifier",
            "Missing command_id in event",
            "Unknown event type",
            "Invalid command_id format",
            "Command not found",
            "badly formed hexadecimal UUID string"
        ]

        # Test each expected error
        for expected_error in expected_errors:
            assert consumer._should_retry(expected_error, retry_count=0) is False, \
                f"Expected '{expected_error}' to be non-retryable"

    def test_consumer_max_retries_configuration(self, consumer):
        """Test that consumer respects max_retries configuration."""
        assert consumer.max_retries == 3

        retryable_error = "Network error"

        # Test boundary conditions
        assert consumer._should_retry(retryable_error, retry_count=2) is True  # Under limit
        assert consumer._should_retry(retryable_error, retry_count=3) is False  # At limit
        assert consumer._should_retry(retryable_error, retry_count=4) is False  # Over limit