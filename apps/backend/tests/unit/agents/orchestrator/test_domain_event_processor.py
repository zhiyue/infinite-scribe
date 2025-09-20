"""Unit tests for DomainEventProcessor and its components.

Tests the domain event processing logic with proper isolation and mocking.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.orchestrator.domain_event_processor import (
    CommandMapper,
    CorrelationIdExtractor,
    DomainEventProcessor,
    EventValidator,
    PayloadEnricher,
)


class TestCorrelationIdExtractor:
    """Tests for correlation ID extraction logic."""

    def test_extract_from_context_meta(self):
        """Test extracting correlation_id from context.meta."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {}
        context = {"meta": {"correlation_id": correlation_id}}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id

    def test_extract_from_context_headers_dict(self):
        """Test extracting correlation_id from context.headers as dict."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {}
        context = {"headers": {"correlation_id": correlation_id}}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id

    def test_extract_from_context_headers_dict_with_dash(self):
        """Test extracting correlation_id from context.headers with dash."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {}
        context = {"headers": {"correlation-id": correlation_id}}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id

    def test_extract_from_context_headers_list(self):
        """Test extracting correlation_id from context.headers as list of tuples."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {}
        context = {"headers": [("correlation_id", correlation_id.encode()), ("other", "value")]}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id

    def test_extract_from_context_headers_list_with_dash(self):
        """Test extracting correlation_id from headers list with dash."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {}
        context = {"headers": [("correlation-id", correlation_id), ("other", "value")]}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id

    def test_extract_from_event_metadata(self):
        """Test extracting correlation_id from event metadata."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {"metadata": {"correlation_id": correlation_id}}
        context = {}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id

    def test_extract_from_event_direct(self):
        """Test extracting correlation_id directly from event."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {"correlation_id": correlation_id}
        context = {}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id

    def test_extract_priority_order(self):
        """Test that context.meta takes priority over other sources."""
        # Arrange
        preferred_id = str(uuid4())
        other_id = str(uuid4())
        evt = {"correlation_id": other_id, "metadata": {"correlation_id": other_id}}
        context = {"meta": {"correlation_id": preferred_id}, "headers": {"correlation_id": other_id}}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == preferred_id

    def test_extract_with_exception(self):
        """Test handling of exceptions during extraction."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {"correlation_id": correlation_id}
        context = {"meta": "invalid"}  # This will cause an exception

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result == correlation_id  # Should fall back to event-level correlation_id

    def test_extract_none_when_not_found(self):
        """Test returning None when correlation_id is not found."""
        # Arrange
        evt = {}
        context = {}

        # Act
        result = CorrelationIdExtractor.extract_correlation_id(evt, context)

        # Assert
        assert result is None


class TestEventValidator:
    """Tests for event validation logic."""

    def test_is_command_received_event_true(self):
        """Test identifying valid command received events."""
        # Test cases
        test_cases = [
            "Genesis.Command.Received",
            "Character.Command.Received",
            "Plot.Command.Received",
        ]

        for event_type in test_cases:
            result = EventValidator.is_command_received_event(event_type)
            assert result is True, f"Failed for event_type: {event_type}"

    def test_is_command_received_event_false(self):
        """Test rejecting non-command events."""
        # Test cases
        test_cases = [
            "Genesis.Character.Requested",
            "Character.Generated",
            "Plot.Requested",
            "Command.Received.Invalid",
            "",
        ]

        for event_type in test_cases:
            result = EventValidator.is_command_received_event(event_type)
            assert result is False, f"Failed for event_type: {event_type}"

    def test_extract_command_type_success(self):
        """Test extracting command_type from event."""
        # Arrange
        evt = {"command_type": "Character.Request"}

        # Act
        result = EventValidator.extract_command_type(evt)

        # Assert
        assert result == "Character.Request"

    def test_extract_command_type_missing(self):
        """Test handling missing command_type."""
        # Arrange
        evt = {}

        # Act
        result = EventValidator.extract_command_type(evt)

        # Assert
        assert result is None

    def test_extract_scope_info_with_prefix(self):
        """Test extracting scope info from event with prefix."""
        # Arrange
        event_type = "Character.Command.Received"

        # Act
        scope_prefix, scope_type = EventValidator.extract_scope_info(event_type)

        # Assert
        assert scope_prefix == "Character"
        assert scope_type == "CHARACTER"

    def test_extract_scope_info_without_prefix(self):
        """Test extracting scope info from event without meaningful prefix."""
        # Arrange
        event_type = "Command.Received"

        # Act
        scope_prefix, scope_type = EventValidator.extract_scope_info(event_type)

        # Assert
        assert scope_prefix == "Command"
        assert scope_type == "COMMAND"

    def test_extract_scope_info_no_dots(self):
        """Test extracting scope info from event with no dots (fallback to Genesis)."""
        # Arrange
        event_type = "Received"

        # Act
        scope_prefix, scope_type = EventValidator.extract_scope_info(event_type)

        # Assert
        assert scope_prefix == "Genesis"
        assert scope_type == "GENESIS"


class TestCommandMapper:
    """Tests for command mapping logic."""

    def test_map_command_delegates_to_registry(self):
        """Test that command mapping delegates to the command registry."""
        # Arrange
        cmd_type = "Character.Request"
        scope_type = "GENESIS"
        scope_prefix = "Genesis"
        aggregate_id = "session-123"
        payload = {"character_type": "hero"}

        with patch("src.agents.orchestrator.domain_event_processor.command_registry") as mock_registry:
            mock_mapping = MagicMock()
            mock_registry.process_command.return_value = mock_mapping

            # Act
            result = CommandMapper.map_command(cmd_type, scope_type, scope_prefix, aggregate_id, payload)

            # Assert
            assert result == mock_mapping
            mock_registry.process_command.assert_called_once_with(
                cmd_type=cmd_type,
                scope_type=scope_type,
                scope_prefix=scope_prefix,
                aggregate_id=aggregate_id,
                payload=payload,
            )


class TestPayloadEnricher:
    """Tests for payload enrichment logic."""

    def test_enrich_domain_payload_basic(self):
        """Test basic payload enrichment."""
        # Arrange
        evt = {}
        aggregate_id = "session-123"
        payload = {"character_type": "hero"}

        # Act
        result = PayloadEnricher.enrich_domain_payload(evt, aggregate_id, payload)

        # Assert
        expected = {
            "session_id": aggregate_id,
            "input": payload,
        }
        assert result == expected

    def test_enrich_domain_payload_with_user_id(self):
        """Test payload enrichment with user_id."""
        # Arrange
        evt = {"user_id": "user-456"}
        aggregate_id = "session-123"
        payload = {"character_type": "hero"}

        # Act
        result = PayloadEnricher.enrich_domain_payload(evt, aggregate_id, payload)

        # Assert
        expected = {
            "session_id": aggregate_id,
            "input": payload,
            "user_id": "user-456",
        }
        assert result == expected

    def test_enrich_domain_payload_with_timestamp(self):
        """Test payload enrichment with timestamp."""
        # Arrange
        timestamp = "2023-01-01T12:00:00Z"
        evt = {"created_at": timestamp}
        aggregate_id = "session-123"
        payload = {"character_type": "hero"}

        # Act
        result = PayloadEnricher.enrich_domain_payload(evt, aggregate_id, payload)

        # Assert
        expected = {
            "session_id": aggregate_id,
            "input": payload,
            "timestamp": timestamp,
        }
        assert result == expected

    def test_enrich_domain_payload_with_all_fields(self):
        """Test payload enrichment with all optional fields."""
        # Arrange
        timestamp = "2023-01-01T12:00:00Z"
        evt = {"user_id": "user-456", "created_at": timestamp}
        aggregate_id = "session-123"
        payload = {"character_type": "hero"}

        # Act
        result = PayloadEnricher.enrich_domain_payload(evt, aggregate_id, payload)

        # Assert
        expected = {
            "session_id": aggregate_id,
            "input": payload,
            "user_id": "user-456",
            "timestamp": timestamp,
        }
        assert result == expected


class TestDomainEventProcessor:
    """Tests for the main domain event processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.processor = DomainEventProcessor(self.mock_logger)

    @pytest.mark.asyncio
    async def test_handle_domain_event_success(self):
        """Test successful domain event processing."""
        # Arrange
        correlation_id = str(uuid4())
        evt = {
            "event_type": "Genesis.Command.Received",
            "aggregate_id": "session-123",
            "payload": {"character_type": "hero"},
            "metadata": {"source": "user"},
            "command_type": "Character.Request",
            "user_id": "user-456",
            "event_id": str(uuid4()),
        }
        context = {"meta": {"correlation_id": correlation_id}}

        # Mock the command mapping result
        mock_mapping = MagicMock()
        mock_mapping.requested_action = "Character.Requested"
        mock_mapping.capability_message = {
            "type": "Character.Design.GenerationRequested",
            "input": {"character_type": "hero"},
        }

        with patch("src.agents.orchestrator.domain_event_processor.command_registry") as mock_registry:
            mock_registry.process_command.return_value = mock_mapping

            # Act
            result = await self.processor.handle_domain_event(evt, context)

            # Assert
            assert result is not None
            assert result["correlation_id"] == correlation_id
            assert result["scope_type"] == "GENESIS"
            assert result["aggregate_id"] == "session-123"
            assert result["mapping"] == mock_mapping
            assert result["causation_id"] == evt["event_id"]

            # Verify enriched payload
            enriched_payload = result["enriched_payload"]
            assert enriched_payload["session_id"] == "session-123"
            assert enriched_payload["input"] == {"character_type": "hero"}
            assert enriched_payload["user_id"] == "user-456"

    @pytest.mark.asyncio
    async def test_handle_domain_event_not_command_received(self):
        """Test handling of non-command events."""
        # Arrange
        evt = {
            "event_type": "Genesis.Character.Requested",
            "aggregate_id": "session-123",
            "payload": {"character_type": "hero"},
        }
        context = {}

        # Act
        result = await self.processor.handle_domain_event(evt, context)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_domain_event_missing_command_type(self):
        """Test handling of events missing command_type."""
        # Arrange
        evt = {
            "event_type": "Genesis.Command.Received",
            "aggregate_id": "session-123",
            "payload": {"character_type": "hero"},
            # Missing command_type
        }
        context = {}

        # Act
        result = await self.processor.handle_domain_event(evt, context)

        # Assert
        assert result is None
        self.mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_domain_event_no_mapping(self):
        """Test handling when command mapping fails."""
        # Arrange
        evt = {
            "event_type": "Genesis.Command.Received",
            "aggregate_id": "session-123",
            "payload": {"character_type": "hero"},
            "command_type": "Unknown.Request",
        }
        context = {}

        with patch("src.agents.orchestrator.domain_event_processor.command_registry") as mock_registry:
            mock_registry.process_command.return_value = None

            # Act
            result = await self.processor.handle_domain_event(evt, context)

            # Assert
            assert result is None
            self.mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_domain_event_extracts_scope_correctly(self):
        """Test correct extraction of scope information."""
        # Arrange
        evt = {
            "event_type": "Character.Command.Received",
            "aggregate_id": "session-123",
            "payload": {"character_type": "hero"},
            "command_type": "Character.Request",
        }
        context = {}

        mock_mapping = MagicMock()
        mock_mapping.requested_action = "Character.Requested"
        mock_mapping.capability_message = {"type": "Character.Design.GenerationRequested"}

        with patch("src.agents.orchestrator.domain_event_processor.command_registry") as mock_registry:
            mock_registry.process_command.return_value = mock_mapping

            # Act
            result = await self.processor.handle_domain_event(evt, context)

            # Assert
            assert result["scope_type"] == "CHARACTER"
            mock_registry.process_command.assert_called_once()
            call_args = mock_registry.process_command.call_args[1]
            assert call_args["scope_type"] == "CHARACTER"
            assert call_args["scope_prefix"] == "Character"