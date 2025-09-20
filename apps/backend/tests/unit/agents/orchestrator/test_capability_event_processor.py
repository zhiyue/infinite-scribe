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
from src.agents.orchestrator.types import (
    ConsistencyCheckData,
    GenerationData,
    MessageContext,
    QualityReviewData,
    ScopeInfo,
)


class TestEventDataExtractor:
    """Tests for event data extraction logic."""

    def test_extract_event_data_with_data_field(self):
        message = {
            "data": {"session_id": "session-123", "result": "success"},
            "other_field": "ignored",
        }

        result = EventDataExtractor.extract_event_data(message)

        assert isinstance(result, GenerationData)
        assert result.model_dump(exclude_none=True) == {
            "session_id": "session-123",
            "result": "success",
        }

    def test_extract_event_data_without_data_field(self):
        message = {"session_id": "session-123", "result": "success"}

        result = EventDataExtractor.extract_event_data(message)

        assert isinstance(result, GenerationData)
        assert result.model_dump(exclude_none=True) == message

    def test_extract_session_and_scope_with_session_id(self):
        data = GenerationData(session_id="session-123", other="data")
        context = MessageContext(topic="genesis.character.events")

        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        assert session_id == "session-123"
        assert isinstance(scope_info, ScopeInfo)
        assert scope_info.topic == "genesis.character.events"
        assert scope_info.scope_prefix == "GENESIS"
        assert scope_info.scope_type == "GENESIS"

    def test_extract_session_and_scope_with_aggregate_id(self):
        data = GenerationData(aggregate_id="session-456", other="data")
        context = MessageContext(topic="character.world.events")

        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        assert session_id == "session-456"
        assert scope_info.scope_prefix == "CHARACTER"
        assert scope_info.scope_type == "CHARACTER"

    def test_extract_session_and_scope_no_session(self):
        data = GenerationData()
        context = MessageContext(topic="plot.outline.events")

        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        assert session_id == ""
        assert scope_info.scope_prefix == "PLOT"
        assert scope_info.scope_type == "PLOT"

    def test_extract_session_and_scope_no_topic(self):
        data = GenerationData(session_id="session-123")
        context = MessageContext()

        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        assert session_id == "session-123"
        assert scope_info.topic == ""
        assert scope_info.scope_prefix == "GENESIS"
        assert scope_info.scope_type == "GENESIS"

    def test_extract_session_and_scope_single_word_topic(self):
        data = GenerationData(session_id="session-123")
        context = MessageContext(topic="events")

        session_id, scope_info = EventDataExtractor.extract_session_and_scope(data, context)

        assert session_id == "session-123"
        assert scope_info.scope_prefix == "GENESIS"
        assert scope_info.scope_type == "GENESIS"

    def test_extract_correlation_id_from_context_meta(self):
        correlation_id = str(uuid4())
        context = MessageContext(meta={"correlation_id": correlation_id})
        data = GenerationData(correlation_id="other-id")

        result = EventDataExtractor.extract_correlation_id(context, data)

        assert result == correlation_id

    def test_extract_correlation_id_from_data_fallback(self):
        correlation_id = str(uuid4())
        context = MessageContext(meta={})
        data = GenerationData(correlation_id=correlation_id)

        result = EventDataExtractor.extract_correlation_id(context, data)

        assert result == correlation_id

    def test_extract_correlation_id_none(self):
        context = MessageContext(meta={})
        data = GenerationData()

        result = EventDataExtractor.extract_correlation_id(context, data)

        assert result is None

    def test_extract_causation_id_from_context_meta(self):
        causation_id = str(uuid4())
        context = MessageContext(meta={"event_id": causation_id})
        data = GenerationData(event_id="other-id")

        result = EventDataExtractor.extract_causation_id(context, data)

        assert result == causation_id

    def test_extract_causation_id_from_data_fallback(self):
        causation_id = str(uuid4())
        context = MessageContext(meta={})
        data = GenerationData(event_id=causation_id)

        result = EventDataExtractor.extract_causation_id(context, data)

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
        data = GenerationData(session_id=session_id, character_id="char-456", name="Hero")
        correlation_id = str(uuid4())
        scope_info = ScopeInfo(topic="genesis.character.events", scope_prefix="GENESIS", scope_type="GENESIS")
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
                msg_type, session_id, data, correlation_id, "GENESIS", "GENESIS", causation_id
            )

    def test_find_matching_handler_second_handler_matches(self):
        """Test when second handler matches."""
        # Arrange
        msg_type = "Character.Quality.ReviewCompleted"
        session_id = "session-123"
        data = QualityReviewData(
            session_id=session_id,
            quality_score=85,
            feedback="Good character",
        )
        correlation_id = str(uuid4())
        scope_info = ScopeInfo(topic="genesis.character.events", scope_prefix="GENESIS", scope_type="GENESIS")
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
                msg_type, session_id, data, correlation_id, "GENESIS", "GENESIS", causation_id
            )

    def test_find_matching_handler_no_match(self):
        """Test when no handler matches."""
        # Arrange
        msg_type = "Unknown.Event.Type"
        session_id = "session-123"
        data = GenerationData(session_id=session_id)
        correlation_id = str(uuid4())
        scope_info = ScopeInfo(topic="genesis.character.events", scope_prefix="GENESIS", scope_type="GENESIS")
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
                data_type="GenerationData",
                handlers_tried=1,
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
        assert result.action == mock_action
        assert result.msg_type == msg_type
        assert result.session_id == "session-123"
        assert result.correlation_id == context["meta"]["correlation_id"]

        # Verify handler matcher was called correctly
        self.processor.handler_matcher.find_matching_handler.assert_called_once()
        call_args = self.processor.handler_matcher.find_matching_handler.call_args[0]
        assert call_args[0] == msg_type
        assert call_args[1] == "session-123"
        event_data = call_args[2]
        assert isinstance(event_data, GenerationData)
        assert event_data.model_dump(exclude_none=True) == {
            "session_id": "session-123",
            "character_id": "char-456",
            "name": "Hero",
        }
        assert call_args[3] == context["meta"]["correlation_id"]
        scope_info = call_args[4]
        assert isinstance(scope_info, ScopeInfo)
        assert scope_info.scope_type == "GENESIS"
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
        assert isinstance(extracted_data, GenerationData)
        assert extracted_data.model_dump(exclude_none=True) == {
            "session_id": "session-123",
            "result": "success",
        }

        # Verify scope extraction
        scope_info = call_args[4]
        assert isinstance(scope_info, ScopeInfo)
        assert scope_info.scope_type == "CHARACTER"
        assert scope_info.scope_prefix == "CHARACTER"

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
        assert isinstance(extracted_data, GenerationData)
        assert extracted_data.model_dump(exclude_none=True) == message
