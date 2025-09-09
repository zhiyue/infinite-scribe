"""Unit tests for conversation event handler."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.conversation.conversation_event_handler import ConversationEventHandler
from src.models.conversation import ConversationRound, ConversationSession
from src.models.event import DomainEvent
from src.models.workflow import CommandInbox, EventOutbox
from src.schemas.novel.dialogue import DialogueRole


class TestConversationEventHandler:
    """Test conversation event handler functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def event_handler(self):
        """Create ConversationEventHandler instance."""
        return ConversationEventHandler()

    @pytest.mark.asyncio
    async def test_create_round_events_new_round(self, event_handler, mock_db):
        """Test creating events for a new round."""
        # Arrange
        session_id = uuid4()
        correlation_id = str(uuid4())
        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"

        # Mock database operations for new round creation
        mock_round = Mock(spec=ConversationRound)
        mock_round.id = uuid4()
        mock_round.round_path = "5"
        mock_round.role = DialogueRole.USER.value
        mock_round.correlation_id = correlation_id

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 4  # 4 existing rounds
        mock_db.execute.return_value = mock_count_result

        # Mock flush operation
        mock_db.flush = AsyncMock()

        # Mock domain event creation
        mock_domain_event = Mock(spec=DomainEvent)
        mock_domain_event.event_id = uuid4()

        with (
            patch("src.common.services.conversation.conversation_event_handler.DomainEvent") as mock_domain_event_class,
            patch("src.common.services.conversation.conversation_event_handler.EventOutbox") as mock_outbox_class,
            patch("src.common.services.conversation.conversation_event_handler.ConversationRound") as mock_round_class,
        ):
            # Setup mocks
            mock_round_class.return_value = mock_round
            mock_domain_event_class.return_value = mock_domain_event
            mock_outbox_class.return_value = Mock(spec=EventOutbox)

            # Act
            result = await event_handler.create_round_events(
                mock_db, session, DialogueRole.USER, {"prompt": "Hello"}, "gpt-4", correlation_id
            )

            # Assert
            assert result == mock_round
            mock_db.add.assert_called()  # Should add round, domain event, and outbox
            mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_round_events_existing_round(self, event_handler, mock_db):
        """Test ensuring events exist for an existing round."""
        # Arrange
        session_id = uuid4()
        correlation_uuid = uuid4()

        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"

        existing_round = Mock(spec=ConversationRound)
        existing_round.id = uuid4()
        existing_round.round_path = "3"
        existing_round.role = DialogueRole.USER.value
        existing_round.model = "gpt-4"

        # Mock existing domain event
        existing_domain_event = Mock(spec=DomainEvent)
        existing_domain_event.event_id = uuid4()
        mock_db.scalar.return_value = existing_domain_event

        # Mock existing outbox entry
        mock_db.scalar.side_effect = [existing_domain_event, Mock(spec=EventOutbox)]

        # Act
        result = await event_handler.ensure_round_events(mock_db, session, existing_round, correlation_uuid)

        # Assert
        assert result == existing_round
        # Should check for existing events but not create new ones

    @pytest.mark.asyncio
    async def test_ensure_round_events_missing_domain_event(self, event_handler, mock_db):
        """Test ensuring events when domain event is missing."""
        # Arrange
        session_id = uuid4()
        correlation_uuid = uuid4()

        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"

        existing_round = Mock(spec=ConversationRound)
        existing_round.round_path = "2"
        existing_round.role = DialogueRole.ASSISTANT.value
        existing_round.model = "claude-3"

        # Mock missing domain event, existing outbox
        mock_db.scalar.side_effect = [None, Mock(spec=EventOutbox)]

        with patch(
            "src.common.services.conversation.conversation_event_handler.DomainEvent"
        ) as mock_domain_event_class:
            mock_domain_event = Mock(spec=DomainEvent)
            mock_domain_event.event_id = uuid4()
            mock_domain_event_class.return_value = mock_domain_event

            # Act
            result = await event_handler.ensure_round_events(mock_db, session, existing_round, correlation_uuid)

            # Assert
            assert result == existing_round
            mock_db.add.assert_called_with(mock_domain_event)
            mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_round_events_missing_outbox(self, event_handler, mock_db):
        """Test ensuring events when outbox entry is missing."""
        # Arrange
        session_id = uuid4()
        correlation_uuid = uuid4()

        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"

        existing_round = Mock(spec=ConversationRound)
        existing_round.round_path = "4"

        # Mock existing domain event, missing outbox
        existing_domain_event = Mock(spec=DomainEvent)
        existing_domain_event.event_id = uuid4()
        existing_domain_event.event_type = "genesis.Round.Created"
        existing_domain_event.aggregate_type = "ConversationSession"
        existing_domain_event.aggregate_id = str(session_id)
        existing_domain_event.payload = {"test": "data"}
        existing_domain_event.event_metadata = {"source": "api"}
        mock_db.scalar.side_effect = [existing_domain_event, None]

        with patch("src.common.services.conversation.conversation_event_handler.EventOutbox") as mock_outbox_class:
            mock_outbox = Mock(spec=EventOutbox)
            mock_outbox_class.return_value = mock_outbox

            # Act
            result = await event_handler.ensure_round_events(mock_db, session, existing_round, correlation_uuid)

            # Assert
            assert result == existing_round
            mock_db.add.assert_called_with(mock_outbox)

    @pytest.mark.asyncio
    async def test_create_command_events_new_command(self, event_handler, mock_db):
        """Test creating events for a new command."""
        # Arrange
        session_id = uuid4()
        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"

        command_type = "generate_content"
        payload = {"prompt": "Write something"}
        idempotency_key = str(uuid4())

        # Mock new command creation
        with (
            patch("src.common.services.conversation.conversation_event_handler.CommandInbox") as mock_command_class,
            patch("src.common.services.conversation.conversation_event_handler.DomainEvent") as mock_domain_event_class,
            patch("src.common.services.conversation.conversation_event_handler.EventOutbox") as mock_outbox_class,
        ):
            mock_command = Mock(spec=CommandInbox)
            mock_command.id = uuid4()
            mock_command_class.return_value = mock_command

            mock_domain_event = Mock(spec=DomainEvent)
            mock_domain_event.event_id = uuid4()
            mock_domain_event_class.return_value = mock_domain_event

            mock_outbox_class.return_value = Mock(spec=EventOutbox)

            # Act
            result = await event_handler.create_command_events(mock_db, session, command_type, payload, idempotency_key)

            # Assert
            assert result == mock_command
            mock_db.add.assert_called()  # Should add command, domain event, and outbox
            mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_ensure_command_events_existing_command(self, event_handler, mock_db):
        """Test ensuring events exist for an existing command."""
        # Arrange
        session_id = uuid4()
        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"

        existing_command = Mock(spec=CommandInbox)
        existing_command.id = uuid4()
        existing_command.command_type = "analyze_text"
        existing_command.payload = {"text": "Sample"}

        # Mock existing domain event and outbox
        existing_domain_event = Mock(spec=DomainEvent)
        existing_domain_event.event_id = uuid4()
        existing_outbox = Mock(spec=EventOutbox)
        mock_db.scalar.side_effect = [existing_domain_event, existing_outbox]

        # Act
        result = await event_handler.ensure_command_events(mock_db, session, existing_command)

        # Assert
        assert result == existing_command
        # Should check for existing events but not create new ones

    @pytest.mark.asyncio
    async def test_ensure_command_events_missing_events(self, event_handler, mock_db):
        """Test ensuring events when both domain event and outbox are missing."""
        # Arrange
        session_id = uuid4()
        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"

        existing_command = Mock(spec=CommandInbox)
        existing_command.id = uuid4()
        existing_command.command_type = "test_command"
        existing_command.payload = {}

        # Mock missing events
        mock_db.scalar.side_effect = [None, None]

        with (
            patch("src.common.services.conversation.conversation_event_handler.DomainEvent") as mock_domain_event_class,
            patch("src.common.services.conversation.conversation_event_handler.EventOutbox") as mock_outbox_class,
        ):
            mock_domain_event = Mock(spec=DomainEvent)
            mock_domain_event.event_id = uuid4()
            mock_domain_event_class.return_value = mock_domain_event

            mock_outbox_class.return_value = Mock(spec=EventOutbox)

            # Act
            result = await event_handler.ensure_command_events(mock_db, session, existing_command)

            # Assert
            assert result == existing_command
            assert mock_db.add.call_count >= 2  # Should add both domain event and outbox

    def test_compute_next_round_path(self, event_handler):
        """Test computing next round path from count."""
        # Test with different counts
        assert event_handler._compute_next_round_path(0) == "1"
        assert event_handler._compute_next_round_path(1) == "2"
        assert event_handler._compute_next_round_path(10) == "11"
        assert event_handler._compute_next_round_path(999) == "1000"

    @pytest.mark.asyncio
    async def test_create_round_events_with_none_correlation_id(self, event_handler, mock_db):
        """Test creating round events when correlation_id is None."""
        # Arrange
        session = Mock(spec=ConversationSession)
        session.id = uuid4()
        session.scope_type = "genesis"

        # Mock count query
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_count_result

        with (
            patch("src.common.services.conversation.conversation_event_handler.ConversationRound") as mock_round_class,
            patch("src.common.services.conversation.conversation_event_handler.DomainEvent") as mock_domain_event_class,
            patch("src.common.services.conversation.conversation_event_handler.EventOutbox") as mock_outbox_class,
        ):
            mock_round = Mock(spec=ConversationRound)
            mock_round.id = uuid4()
            mock_round_class.return_value = mock_round

            mock_domain_event = Mock(spec=DomainEvent)
            mock_domain_event.event_id = uuid4()
            mock_domain_event_class.return_value = mock_domain_event

            mock_outbox_class.return_value = Mock(spec=EventOutbox)

            # Act
            result = await event_handler.create_round_events(
                mock_db,
                session,
                DialogueRole.USER,
                {},
                None,
                None,  # None correlation_id
            )

            # Assert
            assert result == mock_round
            # Should handle None correlation_id gracefully

    @pytest.mark.asyncio
    async def test_create_command_events_with_none_payload(self, event_handler, mock_db):
        """Test creating command events with None payload."""
        # Arrange
        session = Mock(spec=ConversationSession)
        session.id = uuid4()
        session.scope_type = "genesis"

        with (
            patch("src.common.services.conversation.conversation_event_handler.CommandInbox") as mock_command_class,
            patch("src.common.services.conversation.conversation_event_handler.DomainEvent") as mock_domain_event_class,
            patch("src.common.services.conversation.conversation_event_handler.EventOutbox") as mock_outbox_class,
        ):
            mock_command = Mock(spec=CommandInbox)
            mock_command.id = uuid4()
            mock_command_class.return_value = mock_command

            mock_domain_event = Mock(spec=DomainEvent)
            mock_domain_event.event_id = uuid4()
            mock_domain_event_class.return_value = mock_domain_event

            mock_outbox_class.return_value = Mock(spec=EventOutbox)

            # Act
            result = await event_handler.create_command_events(
                mock_db,
                session,
                "test_command",
                None,
                "test-key",  # None payload
            )

            # Assert
            assert result == mock_command
            # Should handle None payload gracefully

    @pytest.mark.asyncio
    async def test_database_error_handling(self, event_handler, mock_db):
        """Test error handling when database operations fail."""
        # Arrange
        session = Mock(spec=ConversationSession)
        session.id = uuid4()
        session.scope_type = "genesis"

        # Mock database error
        mock_db.execute.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(Exception, match="Database connection failed"):
            await event_handler.create_round_events(mock_db, session, DialogueRole.USER, {}, "gpt-4", str(uuid4()))
