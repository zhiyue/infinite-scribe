"""Unit tests for CapabilityEventProcessor and its components.

Tests the capability event processing logic with proper isolation and mocking.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.agents.orchestrator.capability_event_processor import (
    CapabilityEventProcessor,
    EventDataExtractor,
    EventHandlerMatcher,
)
from src.agents.orchestrator.event_handlers import EventAction


class TestEventDataExtractor:
    """Tests for event data extraction logic."""

    def test_extract_event_data_with_data_field(self):
        """Test extracting data when message has 'data' field."""
        # Arrange
        message = {
            "data": {"session_id": "session-123", "result": "success"},
            "other_field": "ignored",
        }

        # Act
        result = EventDataExtractor.extract_event_data(message)

        # Assert
        assert result == {"session_id": "session-123", "result": "success"}

    def test_extract_event_data_without_data_field(self):
        """Test extracting data when message has no 'data' field."""
        # Arrange
        message = {"session_id": "session-123", "result": "success"}

        # Act
        result = EventDataExtractor.extract_event_data(message)

        # Assert
        assert result == message

    def test_extract_session_and_scope_with_session_id(self):
        """Test extracting session and scope with session_id."""
        # Arrange
        data = {"session_id": "session-123", "other": "data"}
        context = {"topic": "genesis.character.events"}

        # Act
        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        # Assert
        assert session_id == "session-123"
        assert scope_info["topic"] == "genesis.character.events"
        assert scope_info["scope_prefix"] == "GENESIS"
        assert scope_info["scope_type"] == "GENESIS"

    def test_extract_session_and_scope_with_aggregate_id(self):
        """Test extracting session and scope with aggregate_id fallback."""
        # Arrange
        data = {"aggregate_id": "session-456", "other": "data"}
        context = {"topic": "character.world.events"}

        # Act
        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        # Assert
        assert session_id == "session-456"
        assert scope_info["scope_prefix"] == "CHARACTER"
        assert scope_info["scope_type"] == "CHARACTER"

    def test_extract_session_and_scope_no_session(self):
        """Test extracting session and scope with no session info."""
        # Arrange
        data = {"other": "data"}
        context = {"topic": "plot.outline.events"}

        # Act
        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        # Assert
        assert session_id == ""
        assert scope_info["scope_prefix"] == "PLOT"
        assert scope_info["scope_type"] == "PLOT"

    def test_extract_session_and_scope_no_topic(self):
        """Test extracting session and scope with no topic."""
        # Arrange
        data = {"session_id": "session-123"}
        context = {}

        # Act
        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        # Assert
        assert session_id == "session-123"
        assert scope_info["topic"] == ""
        assert scope_info["scope_prefix"] == "GENESIS"
        assert scope_info["scope_type"] == "GENESIS"

    def test_extract_session_and_scope_single_word_topic(self):
        """Test extracting session and scope with single word topic."""
        # Arrange
        data = {"session_id": "session-123"}
        context = {"topic": "events"}

        # Act
        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        # Assert
        assert scope_info["scope_prefix"] == "GENESIS"
        assert scope_info["scope_type"] == "GENESIS"

    def test_extract_correlation_id_from_context_meta(self):
        """Test extracting correlation_id from context meta."""
        # Arrange
        correlation_id = str(uuid4())
        context = {"meta": {"correlation_id": correlation_id}}
        data = {"correlation_id": "other-id"}

        # Act
        result = EventDataExtractor.extract_correlation_id(context, data)

        # Assert
        assert result == correlation_id

    def test_extract_correlation_id_from_data_fallback(self):
        """Test extracting correlation_id from data as fallback."""
        # Arrange
        correlation_id = str(uuid4())
        context = {"meta": {}}
        data = {"correlation_id": correlation_id}

        # Act
        result = EventDataExtractor.extract_correlation_id(context, data)

        # Assert
        assert result == correlation_id

    def test_extract_correlation_id_none(self):
        """Test when no correlation_id is found."""
        # Arrange
        context = {"meta": {}}
        data = {}

        # Act
        result = EventDataExtractor.extract_correlation_id(context, data)

        # Assert
        assert result is None

    def test_extract_causation_id_from_context_meta(self):
        """Test extracting causation_id from context meta."""
        # Arrange
        causation_id = str(uuid4())
        context = {"meta": {"event_id": causation_id}}
        data = {"event_id": "other-id"}

        # Act
        result = EventDataExtractor.extract_causation_id(context, data)

        # Assert
        assert result == causation_id

    def test_extract_causation_id_from_data_fallback(self):
        """Test extracting causation_id from data as fallback."""
        # Arrange
        causation_id = str(uuid4())
        context = {"meta": {}}
        data = {"event_id": causation_id}

        # Act
        result = EventDataExtractor.extract_causation_id(context, data)

        # Assert
        assert result == causation_id


class TestEventHandlerMatcher:
    """Tests for event handler matching logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.matcher = EventHandlerMatcher(self.mock_logger)

    def test_find_matching_handler_success(self):
        """Test finding a matching handler successfully."""
        # Arrange
        msg_type = "Character.Design.GenerationCompleted"
        session_id = "session-123"
        data = {"character_id": "char-456", "name": "Hero"}
        correlation_id = str(uuid4())
        scope_info = {"scope_type": "GENESIS", "scope_prefix": "Genesis"}
        causation_id = str(uuid4())

        mock_action = EventAction(
            domain_event={"scope_type": "GENESIS", "event_action": "Character.Generated"},
            task_completion={"correlation_id": correlation_id, "expect_task_prefix": "Character.Design"},
        )

        with patch(
            "src.agents.orchestrator.capability_event_processor.CapabilityEventHandlers"
        ) as mock_handlers:
            # Mock first handler to return the action
            mock_handlers.handle_generation_completed.return_value = mock_action
            mock_handlers.handle_quality_review_result.return_value = None
            mock_handlers.handle_consistency_check_result.return_value = None

            # Act
            result = self.matcher.find_matching_handler(
                msg_type, session_id, data, correlation_id, scope_info, causation_id
            )

            # Assert
            assert result == mock_action
            mock_handlers.handle_generation_completed.assert_called_once_with(
                msg_type, session_id, data, correlation_id, "GENESIS", "Genesis", causation_id
            )

    def test_find_matching_handler_second_handler_matches(self):
        """Test when second handler matches."""
        # Arrange
        msg_type = "Character.Quality.ReviewCompleted"
        session_id = "session-123"
        data = {"quality_score": 85, "feedback": "Good character"}
        correlation_id = str(uuid4())
        scope_info = {"scope_type": "GENESIS", "scope_prefix": "Genesis"}
        causation_id = str(uuid4())

        mock_action = EventAction(
            domain_event={"scope_type": "GENESIS", "event_action": "Character.QualityReviewed"}
        )

        with patch(
            "src.agents.orchestrator.capability_event_processor.CapabilityEventHandlers"
        ) as mock_handlers:
            # Mock second handler to return the action
            mock_handlers.handle_generation_completed.return_value = None
            mock_handlers.handle_quality_review_result.return_value = mock_action
            mock_handlers.handle_consistency_check_result.return_value = None

            # Act
            result = self.matcher.find_matching_handler(
                msg_type, session_id, data, correlation_id, scope_info, causation_id
            )

            # Assert
            assert result == mock_action
            mock_handlers.handle_quality_review_result.assert_called_once_with(
                msg_type, session_id, data, correlation_id, "GENESIS", "Genesis", causation_id
            )

    def test_find_matching_handler_no_match(self):
        """Test when no handler matches."""
        # Arrange
        msg_type = "Unknown.Event.Type"
        session_id = "session-123"
        data = {"unknown": "data"}
        correlation_id = str(uuid4())
        scope_info = {"scope_type": "GENESIS", "scope_prefix": "Genesis"}
        causation_id = str(uuid4())

        with patch(
            "src.agents.orchestrator.capability_event_processor.CapabilityEventHandlers"
        ) as mock_handlers:
            # Mock all handlers to return None
            mock_handlers.handle_generation_completed.return_value = None
            mock_handlers.handle_quality_review_result.return_value = None
            mock_handlers.handle_consistency_check_result.return_value = None

            # Act
            result = self.matcher.find_matching_handler(
                msg_type, session_id, data, correlation_id, scope_info, causation_id
            )

            # Assert
            assert result is None
            self.mock_logger.debug.assert_called_with(
                "orchestrator_no_handler_matched",
                msg_type=msg_type,
                session_id=session_id,
                handlers_tried=3,
            )


class TestCapabilityEventProcessor:
    """Tests for the main capability event processor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.processor = CapabilityEventProcessor(self.mock_logger)

    @pytest.mark.asyncio
    async def test_handle_capability_event_success(self):
        """Test successful capability event processing."""
        # Arrange
        msg_type = "Character.Design.GenerationCompleted"
        message = {
            "data": {"session_id": "session-123", "character_id": "char-456", "name": "Hero"},
            "other_field": "ignored",
        }
        context = {
            "topic": "genesis.character.events",
            "meta": {"correlation_id": str(uuid4()), "event_id": str(uuid4())},
        }

        mock_action = EventAction(
            domain_event={"scope_type": "GENESIS", "event_action": "Character.Generated"},
            task_completion={"correlation_id": context["meta"]["correlation_id"], "expect_task_prefix": "Character.Design"},
        )

        # Mock the handler matcher to return an action
        self.processor.handler_matcher.find_matching_handler = MagicMock(return_value=mock_action)

        # Act
        result = await self.processor.handle_capability_event(msg_type, message, context)

        # Assert
        assert result is not None
        assert result["action"] == mock_action
        assert result["msg_type"] == msg_type
        assert result["session_id"] == "session-123"
        assert result["correlation_id"] == context["meta"]["correlation_id"]

        # Verify handler matcher was called correctly
        self.processor.handler_matcher.find_matching_handler.assert_called_once()
        call_args = self.processor.handler_matcher.find_matching_handler.call_args[0]
        assert call_args[0] == msg_type
        assert call_args[1] == "session-123"
        assert call_args[2] == {"session_id": "session-123", "character_id": "char-456", "name": "Hero"}
        assert call_args[3] == context["meta"]["correlation_id"]
        assert call_args[4]["scope_type"] == "GENESIS"
        assert call_args[5] == context["meta"]["event_id"]

    @pytest.mark.asyncio
    async def test_handle_capability_event_no_handler_match(self):
        """Test when no handler matches the event."""
        # Arrange
        msg_type = "Unknown.Event.Type"
        message = {"data": {"session_id": "session-123", "unknown": "data"}}
        context = {"topic": "genesis.unknown.events"}

        # Mock the handler matcher to return None
        self.processor.handler_matcher.find_matching_handler = MagicMock(return_value=None)

        # Act
        result = await self.processor.handle_capability_event(msg_type, message, context)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_capability_event_extracts_data_correctly(self):
        """Test that event data is extracted correctly."""
        # Arrange
        msg_type = "Character.Design.GenerationCompleted"
        message = {
            "data": {"session_id": "session-123", "result": "success"},
            "metadata": "ignored",
        }
        context = {
            "topic": "character.design.events",
            "meta": {"correlation_id": str(uuid4())},
        }

        mock_action = EventAction(domain_event={"scope_type": "CHARACTER"})

        # Mock the handler matcher
        self.processor.handler_matcher.find_matching_handler = MagicMock(return_value=mock_action)

        # Act
        result = await self.processor.handle_capability_event(msg_type, message, context)

        # Assert
        assert result is not None

        # Verify correct data extraction
        call_args = self.processor.handler_matcher.find_matching_handler.call_args[0]
        extracted_data = call_args[2]
        assert extracted_data == {"session_id": "session-123", "result": "success"}

        # Verify scope extraction
        scope_info = call_args[4]
        assert scope_info["scope_type"] == "CHARACTER"
        assert scope_info["scope_prefix"] == "CHARACTER"

    @pytest.mark.asyncio
    async def test_handle_capability_event_message_without_data_field(self):
        """Test handling message without separate data field."""
        # Arrange
        msg_type = "Character.Design.GenerationCompleted"
        message = {"session_id": "session-123", "result": "success"}
        context = {"topic": "genesis.character.events"}

        mock_action = EventAction(domain_event={"scope_type": "GENESIS"})

        # Mock the handler matcher
        self.processor.handler_matcher.find_matching_handler = MagicMock(return_value=mock_action)

        # Act
        result = await self.processor.handle_capability_event(msg_type, message, context)

        # Assert
        assert result is not None

        # Verify the entire message was used as data
        call_args = self.processor.handler_matcher.find_matching_handler.call_args[0]
        extracted_data = call_args[2]
        assert extracted_data == message