"""Unit tests for conversation service facade."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.conversation.conversation_service import ConversationService
from src.schemas.novel.dialogue import DialogueRole, ScopeType, SessionStatus


class TestConversationService:
    """Test conversation service facade functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_session_service(self):
        """Create mock session service."""
        return AsyncMock()

    @pytest.fixture
    def mock_round_service(self):
        """Create mock round service."""
        return AsyncMock()

    @pytest.fixture
    def mock_command_service(self):
        """Create mock command service."""
        return AsyncMock()

    @pytest.fixture
    def conversation_service(self, mock_session_service, mock_round_service, mock_command_service):
        """Create ConversationService facade instance."""
        return ConversationService(
            cache=None,
            session_service=mock_session_service, 
            round_service=mock_round_service, 
            command_service=mock_command_service
        )

    # Session Tests

    @pytest.mark.asyncio
    async def test_create_session_delegates_to_session_service(
        self, conversation_service, mock_db, mock_session_service
    ):
        """Test that create_session delegates to session service."""
        # Arrange
        user_id = 123
        scope_type = ScopeType.GENESIS
        scope_id = str(uuid4())
        stage = "worldbuilding"
        initial_state = {"key": "value"}

        expected_result = {"success": True, "session": {"id": str(uuid4())}}
        mock_session_service.create_session.return_value = expected_result

        # Act
        result = await conversation_service.create_session(mock_db, user_id, scope_type, scope_id, stage, initial_state)

        # Assert
        assert result == expected_result
        mock_session_service.create_session.assert_called_once_with(
            mock_db, user_id, scope_type, scope_id, stage, initial_state
        )

    @pytest.mark.asyncio
    async def test_get_session_delegates_to_session_service(self, conversation_service, mock_db, mock_session_service):
        """Test that get_session delegates to session service."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        expected_result = {"success": True, "session": {"id": str(session_id)}}
        mock_session_service.get_session.return_value = expected_result

        # Act
        result = await conversation_service.get_session(mock_db, user_id, session_id)

        # Assert
        assert result == expected_result
        mock_session_service.get_session.assert_called_once_with(mock_db, user_id, session_id)

    @pytest.mark.asyncio
    async def test_update_session_delegates_to_session_service(
        self, conversation_service, mock_db, mock_session_service
    ):
        """Test that update_session delegates to session service."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        status = SessionStatus.COMPLETED
        stage = "finished"
        state = {"completed": True}
        expected_version = 2

        expected_result = {"success": True, "session": {"id": str(session_id), "version": 3}}
        mock_session_service.update_session.return_value = expected_result

        # Act
        result = await conversation_service.update_session(
            mock_db, user_id, session_id, status=status, stage=stage, state=state, expected_version=expected_version
        )

        # Assert
        assert result == expected_result
        mock_session_service.update_session.assert_called_once_with(
            mock_db, user_id, session_id, status=status, stage=stage, state=state, expected_version=expected_version
        )

    @pytest.mark.asyncio
    async def test_delete_session_delegates_to_session_service(
        self, conversation_service, mock_db, mock_session_service
    ):
        """Test that delete_session delegates to session service."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        expected_result = {"success": True}
        mock_session_service.delete_session.return_value = expected_result

        # Act
        result = await conversation_service.delete_session(mock_db, user_id, session_id)

        # Assert
        assert result == expected_result
        mock_session_service.delete_session.assert_called_once_with(mock_db, user_id, session_id)

    # Round Tests

    @pytest.mark.asyncio
    async def test_list_rounds_delegates_to_round_service(self, conversation_service, mock_db, mock_round_service):
        """Test that list_rounds delegates to round service."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        after = "round-5"
        limit = 20
        order = "desc"
        role = DialogueRole.USER

        expected_result = {"success": True, "rounds": [{"round_path": "6"}]}
        mock_round_service.list_rounds.return_value = expected_result

        # Act
        result = await conversation_service.list_rounds(
            mock_db, user_id, session_id, after=after, limit=limit, order=order, role=role
        )

        # Assert
        assert result == expected_result
        mock_round_service.list_rounds.assert_called_once_with(
            mock_db, user_id, session_id, after=after, limit=limit, order=order, role=role
        )

    @pytest.mark.asyncio
    async def test_create_round_delegates_to_round_service(self, conversation_service, mock_db, mock_round_service):
        """Test that create_round delegates to round service."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        role = DialogueRole.USER
        input_data = {"prompt": "Hello"}
        model = "gpt-4"
        correlation_id = str(uuid4())

        expected_result = {"success": True, "round": {"round_path": "1"}}
        mock_round_service.create_round.return_value = expected_result

        # Act
        result = await conversation_service.create_round(
            mock_db, user_id, session_id, role=role, input_data=input_data, model=model, correlation_id=correlation_id
        )

        # Assert
        assert result == expected_result
        mock_round_service.create_round.assert_called_once_with(
            mock_db, user_id, session_id, role=role, input_data=input_data, model=model, correlation_id=correlation_id
        )

    @pytest.mark.asyncio
    async def test_get_round_delegates_to_round_service(self, conversation_service, mock_db, mock_round_service):
        """Test that get_round delegates to round service."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "3"

        expected_result = {"success": True, "round": {"round_path": "3"}}
        mock_round_service.get_round.return_value = expected_result

        # Act
        result = await conversation_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result == expected_result
        mock_round_service.get_round.assert_called_once_with(mock_db, user_id, session_id, round_path)

    # Command Tests

    @pytest.mark.asyncio
    async def test_enqueue_command_delegates_to_command_service(
        self, conversation_service, mock_db, mock_command_service
    ):
        """Test that enqueue_command delegates to command service."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        command_type = "generate_content"
        payload = {"prompt": "Write something"}
        idempotency_key = str(uuid4())

        expected_result = {"success": True, "command": {"id": str(uuid4())}}
        mock_command_service.enqueue_command.return_value = expected_result

        # Act
        result = await conversation_service.enqueue_command(
            mock_db, user_id, session_id, command_type=command_type, payload=payload, idempotency_key=idempotency_key
        )

        # Assert
        assert result == expected_result
        mock_command_service.enqueue_command.assert_called_once_with(
            mock_db, user_id, session_id, command_type=command_type, payload=payload, idempotency_key=idempotency_key
        )

    # Integration Tests

    @pytest.mark.asyncio
    async def test_full_conversation_flow(
        self, conversation_service, mock_db, mock_session_service, mock_round_service, mock_command_service
    ):
        """Test a full conversation flow using the facade."""
        user_id = 123
        session_id = uuid4()

        # Step 1: Create session
        mock_session_service.create_session.return_value = {
            "success": True,
            "session": {"id": str(session_id), "status": "active"},
        }

        session_result = await conversation_service.create_session(mock_db, user_id, ScopeType.GENESIS, str(uuid4()))
        assert session_result["success"] is True

        # Step 2: Create round
        mock_round_service.create_round.return_value = {"success": True, "round": {"round_path": "1", "role": "user"}}

        round_result = await conversation_service.create_round(
            mock_db, user_id, session_id, role=DialogueRole.USER, input_data={"prompt": "Hello"}
        )
        assert round_result["success"] is True

        # Step 3: Enqueue command
        mock_command_service.enqueue_command.return_value = {
            "success": True,
            "command": {"id": str(uuid4()), "status": "received"},
        }

        command_result = await conversation_service.enqueue_command(
            mock_db,
            user_id,
            session_id,
            command_type="generate_response",
            payload={"context": "conversation"},
            idempotency_key=None,
        )
        assert command_result["success"] is True

        # Step 4: List rounds
        mock_round_service.list_rounds.return_value = {"success": True, "rounds": [{"round_path": "1"}]}

        list_result = await conversation_service.list_rounds(mock_db, user_id, session_id)
        assert list_result["success"] is True
        assert len(list_result["rounds"]) == 1

        # Verify all service methods were called
        mock_session_service.create_session.assert_called_once()
        mock_round_service.create_round.assert_called_once()
        mock_command_service.enqueue_command.assert_called_once()
        mock_round_service.list_rounds.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_propagation_from_session_service(self, conversation_service, mock_db, mock_session_service):
        """Test that errors from session service are properly propagated."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        error_result = {"success": False, "error": "Session not found", "code": 404}
        mock_session_service.get_session.return_value = error_result

        # Act
        result = await conversation_service.get_session(mock_db, user_id, session_id)

        # Assert
        assert result == error_result
        assert result["success"] is False
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_error_propagation_from_round_service(self, conversation_service, mock_db, mock_round_service):
        """Test that errors from round service are properly propagated."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        error_result = {"success": False, "error": "Access denied", "code": 403}
        mock_round_service.list_rounds.return_value = error_result

        # Act
        result = await conversation_service.list_rounds(mock_db, user_id, session_id)

        # Assert
        assert result == error_result
        assert result["success"] is False
        assert result["code"] == 403

    @pytest.mark.asyncio
    async def test_error_propagation_from_command_service(self, conversation_service, mock_db, mock_command_service):
        """Test that errors from command service are properly propagated."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        error_result = {"success": False, "error": "Failed to enqueue command"}
        mock_command_service.enqueue_command.return_value = error_result

        # Act
        result = await conversation_service.enqueue_command(
            mock_db, user_id, session_id, command_type="test", payload={}, idempotency_key=None
        )

        # Assert
        assert result == error_result
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_service_independence(
        self, conversation_service, mock_db, mock_session_service, mock_round_service, mock_command_service
    ):
        """Test that services operate independently."""
        user_id = 123
        session_id = uuid4()

        # Configure different return values for different services
        mock_session_service.get_session.return_value = {"success": True, "session": {}}
        mock_round_service.get_round.return_value = {"success": False, "error": "Round not found"}
        mock_command_service.enqueue_command.return_value = {"success": True, "command": {}}

        # Call different service methods
        session_result = await conversation_service.get_session(mock_db, user_id, session_id)
        round_result = await conversation_service.get_round(mock_db, user_id, session_id, "1")
        command_result = await conversation_service.enqueue_command(
            mock_db, user_id, session_id, command_type="test", payload={}, idempotency_key=None
        )

        # Verify independent results
        assert session_result["success"] is True
        assert round_result["success"] is False
        assert command_result["success"] is True

        # Verify each service was called only for its own operations
        mock_session_service.get_session.assert_called_once()
        mock_round_service.get_round.assert_called_once()
        mock_command_service.enqueue_command.assert_called_once()

    def test_facade_initialization(self):
        """Test that ConversationService can be initialized with dependencies."""
        # Arrange
        mock_cache = Mock()
        mock_session_service = Mock()
        mock_round_service = Mock()
        mock_command_service = Mock()

        # Act
        service = ConversationService(
            cache=mock_cache,
            session_service=mock_session_service, 
            round_service=mock_round_service, 
            command_service=mock_command_service
        )

        # Assert
        assert service.cache == mock_cache
        assert service.session_service == mock_session_service
        assert service.round_service == mock_round_service
        assert service.command_service == mock_command_service

    @pytest.mark.asyncio
    async def test_default_parameter_handling(
        self, conversation_service, mock_db, mock_session_service, mock_round_service
    ):
        """Test handling of default parameters in delegated methods."""
        user_id = 123
        session_id = uuid4()

        # Test session creation with defaults
        mock_session_service.create_session.return_value = {"success": True}
        await conversation_service.create_session(mock_db, user_id, ScopeType.GENESIS, str(uuid4()))

        # Verify defaults were passed correctly
        call_args = mock_session_service.create_session.call_args
        assert call_args.args[4] is None
        assert call_args.args[5] is None

        # Test round listing with defaults
        mock_round_service.list_rounds.return_value = {"success": True, "rounds": []}
        await conversation_service.list_rounds(mock_db, user_id, session_id)

        # Verify defaults were passed correctly
        call_args = mock_round_service.list_rounds.call_args
        assert call_args[1]["after"] is None
        assert call_args[1]["limit"] == 50
        assert call_args[1]["order"] == "asc"
        assert call_args[1]["role"] is None
