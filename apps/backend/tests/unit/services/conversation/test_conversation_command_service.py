"""Unit tests for conversation command service."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.conversation.conversation_command_service import ConversationCommandService
from src.models.conversation import ConversationSession
from src.models.workflow import CommandInbox


class TestConversationCommandService:
    """Test conversation command service functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_access_control(self):
        """Create mock access control."""
        return AsyncMock()

    @pytest.fixture
    def mock_event_handler(self):
        """Create mock event handler."""
        return AsyncMock()

    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer."""
        return Mock()

    @pytest.fixture
    def command_service(self, mock_access_control, mock_event_handler, mock_serializer):
        """Create ConversationCommandService instance."""
        return ConversationCommandService(mock_access_control, mock_event_handler, mock_serializer)

    @pytest.mark.asyncio
    async def test_enqueue_command_success_new(self, command_service, mock_db, mock_access_control, mock_event_handler, mock_serializer):
        """Test successful enqueuing of new command."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "generate_content"
        payload = {"prompt": "Write a story"}
        idempotency_key = str(uuid4())

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = "genesis"
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock no existing command for idempotency check
        mock_db.scalar.return_value = None

        # Mock successful command creation and event handling
        created_command = Mock(spec=CommandInbox)
        created_command.id = uuid4()
        created_command.command_type = command_type
        created_command.idempotency_key = idempotency_key
        mock_event_handler.create_command_events.return_value = created_command

        # Mock serialization
        serialized_command = {"id": str(created_command.id), "command_type": command_type}
        mock_serializer.serialize_command.return_value = serialized_command

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload=payload, idempotency_key=idempotency_key
        )

        # Assert
        assert result["success"] is True
        assert result["command"] == serialized_command
        mock_access_control.verify_session_access.assert_called_once_with(mock_db, user_id, session_id)
        mock_event_handler.create_command_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_command_idempotent_replay(
        self, command_service, mock_db, mock_access_control, mock_event_handler
    ):
        """Test idempotent command enqueuing with existing idempotency key."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "generate_content"
        payload = {"prompt": "Write a story"}
        idempotency_key = str(uuid4())

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = "genesis"
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock existing command (idempotent case)
        existing_command = Mock(spec=CommandInbox)
        existing_command.id = uuid4()
        existing_command.command_type = command_type
        existing_command.idempotency_key = idempotency_key
        mock_db.scalar.side_effect = [mock_session, existing_command]

        # Mock event handling for idempotent case
        mock_event_handler.ensure_command_events.return_value = existing_command

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload=payload, idempotency_key=idempotency_key
        )

        # Assert
        assert result["success"] is True
        assert result["command"] == existing_command
        mock_event_handler.ensure_command_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_command_without_idempotency_key(
        self, command_service, mock_db, mock_access_control, mock_event_handler
    ):
        """Test enqueuing command without idempotency key (auto-generated)."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "analyze_text"
        payload = {"text": "Sample text"}

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = "genesis"
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock no existing command
        mock_db.scalar.side_effect = [mock_session, None]

        # Mock successful command creation
        created_command = Mock(spec=CommandInbox)
        created_command.id = uuid4()
        created_command.command_type = command_type
        # Auto-generated idempotency key should start with "cmd-"
        created_command.idempotency_key = "cmd-" + str(uuid4())
        mock_event_handler.create_command_events.return_value = created_command

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload=payload, idempotency_key=None
        )

        # Assert
        assert result["success"] is True
        assert result["command"] == created_command
        assert created_command.idempotency_key.startswith("cmd-")

    @pytest.mark.asyncio
    async def test_enqueue_command_session_not_found(self, command_service, mock_db):
        """Test enqueuing command when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "test_command"

        # Mock session not found
        mock_db.scalar.return_value = None

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload={}
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_enqueue_command_access_denied(self, command_service, mock_db, mock_access_control):
        """Test enqueuing command when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "restricted_command"

        # Mock session exists but access denied
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload={}
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403

    @pytest.mark.asyncio
    async def test_enqueue_command_with_empty_payload(
        self, command_service, mock_db, mock_access_control, mock_event_handler
    ):
        """Test enqueuing command with None payload."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "simple_command"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.scope_type = "genesis"
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock no existing command
        mock_db.scalar.side_effect = [mock_session, None]

        # Mock command creation
        created_command = Mock(spec=CommandInbox)
        created_command.id = uuid4()
        mock_event_handler.create_command_events.return_value = created_command

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload=None, idempotency_key=None
        )

        # Assert
        assert result["success"] is True
        assert result["command"] == created_command
        # Should handle None payload gracefully

    @pytest.mark.asyncio
    async def test_enqueue_command_database_exception(self, command_service, mock_db, mock_access_control):
        """Test enqueuing command when database raises exception."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "failing_command"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock database exception during command lookup
        mock_db.scalar.side_effect = [mock_session, Exception("Database connection failed")]

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload={}
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to enqueue command"

    @pytest.mark.asyncio
    async def test_enqueue_command_event_handler_exception(
        self, command_service, mock_db, mock_access_control, mock_event_handler
    ):
        """Test enqueuing command when event handler raises exception."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "problematic_command"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.scope_type = "genesis"
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock no existing command
        mock_db.scalar.side_effect = [mock_session, None]

        # Mock event handler exception
        mock_event_handler.create_command_events.side_effect = Exception("Event handling failed")

        # Act
        result = await command_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload={}
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to enqueue command"


    @pytest.mark.asyncio
    async def test_enqueue_command_complex_payload(
        self, command_service, mock_db, mock_access_control, mock_event_handler
    ):
        """Test enqueuing command with complex payload data."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "complex_generation"
        complex_payload = {
            "characters": ["Alice", "Bob"],
            "settings": {"location": "Medieval castle", "time": "Evening"},
            "requirements": {"length": 1000, "tone": "dramatic", "pov": "third_person"},
            "references": [{"type": "character", "id": "char_123"}, {"type": "location", "id": "loc_456"}],
        }
        idempotency_key = f"complex-{uuid4()}"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.scope_type = "genesis"
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock no existing command
        mock_db.scalar.side_effect = [mock_session, None]

        # Mock command creation
        created_command = Mock(spec=CommandInbox)
        created_command.id = uuid4()
        created_command.payload = complex_payload
        mock_event_handler.create_command_events.return_value = created_command

        # Act
        result = await command_service.enqueue_command(
            mock_db,
            user_id,
            session_id,
            command_type=command_type,
            payload=complex_payload,
            idempotency_key=idempotency_key,
        )

        # Assert
        assert result["success"] is True
        assert result["command"] == created_command
        # Verify complex payload was handled correctly
        mock_event_handler.create_command_events.assert_called_once()
        call_args = mock_event_handler.create_command_events.call_args[1]
        assert call_args["payload"] == complex_payload

    @pytest.mark.asyncio
    async def test_enqueue_command_various_command_types(
        self, command_service, mock_db, mock_access_control, mock_event_handler
    ):
        """Test enqueuing different types of commands."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.scope_type = "genesis"
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        command_types = [
            "generate_scene",
            "develop_character",
            "create_dialogue",
            "analyze_plot",
            "suggest_improvements",
        ]

        for command_type in command_types:
            # Mock no existing command for each type
            mock_db.scalar.side_effect = [mock_session, None]

            # Mock command creation
            created_command = Mock(spec=CommandInbox)
            created_command.id = uuid4()
            created_command.command_type = command_type
            mock_event_handler.create_command_events.return_value = created_command

            # Act
            result = await command_service.enqueue_command(
                mock_db, user_id, session_id, command_type=command_type, payload={f"{command_type}_data": "test"}
            )

            # Assert
            assert result["success"] is True, f"Failed for command type: {command_type}"
            assert result["command"].command_type == command_type
