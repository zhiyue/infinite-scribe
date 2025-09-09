"""Unit tests for conversation round service."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.conversation.conversation_round_service import ConversationRoundService
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import DialogueRole


class TestConversationRoundService:
    """Test conversation round service functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_cache(self):
        """Create mock conversation cache."""
        return AsyncMock()

    @pytest.fixture
    def mock_access_control(self):
        """Create mock access control."""
        return AsyncMock()

    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer."""
        return Mock()

    @pytest.fixture
    def mock_event_handler(self):
        """Create mock event handler."""
        return AsyncMock()

    @pytest.fixture
    def round_service(self, mock_cache):
        """Create ConversationRoundService instance."""
        return ConversationRoundService(cache=mock_cache)

    @pytest.mark.asyncio
    async def test_list_rounds_success(self, round_service, mock_db, mock_access_control):
        """Test successful round listing."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session existence and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock rounds query result
        mock_round1 = Mock(spec=ConversationRound)
        mock_round2 = Mock(spec=ConversationRound)
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_round1, mock_round2]
        mock_db.execute.return_value = mock_result

        # Act
        result = await round_service.list_rounds(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is True
        assert result["rounds"] == [mock_round1, mock_round2]
        mock_access_control.verify_session_access.assert_called_once_with(mock_db, user_id, mock_session)

    @pytest.mark.asyncio
    async def test_list_rounds_session_not_found(self, round_service, mock_db):
        """Test listing rounds when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session not found
        mock_db.scalar.return_value = None

        # Act
        result = await round_service.list_rounds(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_list_rounds_access_denied(self, round_service, mock_db, mock_access_control):
        """Test listing rounds when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session exists but access denied
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await round_service.list_rounds(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403

    @pytest.mark.asyncio
    async def test_list_rounds_with_filters(self, round_service, mock_db, mock_access_control):
        """Test listing rounds with role filter and pagination."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        after = "round-5"
        limit = 10
        order = "desc"
        role = DialogueRole.USER

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock filtered query result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # Act
        result = await round_service.list_rounds(
            mock_db, user_id, session_id, after=after, limit=limit, order=order, role=role
        )

        # Assert
        assert result["success"] is True
        assert result["rounds"] == []

    @pytest.mark.asyncio
    async def test_create_round_success_new(
        self, round_service, mock_db, mock_access_control, mock_event_handler, mock_cache, mock_serializer
    ):
        """Test successful creation of new round."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        role = DialogueRole.USER
        input_data = {"prompt": "Hello"}
        model = "gpt-4"
        correlation_id = str(uuid4())

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = "genesis"
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock no existing idempotent round
        mock_db.scalar.side_effect = [mock_session, None]  # Session exists, no existing round

        # Mock count query for round path calculation
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 5  # 5 existing rounds
        mock_db.execute.return_value = mock_count_result

        # Mock successful round creation
        created_round = Mock(spec=ConversationRound)
        created_round.id = uuid4()
        created_round.round_path = "6"

        # Mock successful event handling
        mock_event_handler.create_round_events.return_value = created_round

        # Mock serialization
        serialized_round = {"session_id": str(session_id), "round_path": "6"}
        mock_serializer.serialize_round.return_value = serialized_round

        # Act
        result = await round_service.create_round(
            mock_db, user_id, session_id, role=role, input_data=input_data, model=model, correlation_id=correlation_id
        )

        # Assert
        assert result["success"] is True
        assert result["round"] == created_round
        mock_event_handler.create_round_events.assert_called_once()
        mock_cache.cache_round.assert_called_once_with(str(session_id), "6", serialized_round)

    @pytest.mark.asyncio
    async def test_create_round_idempotent_replay(
        self, round_service, mock_db, mock_access_control, mock_event_handler, mock_cache, mock_serializer
    ):
        """Test idempotent round creation with existing correlation_id."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        role = DialogueRole.USER
        input_data = {"prompt": "Hello"}
        model = "gpt-4"
        correlation_id = str(uuid4())

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = "genesis"
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock existing idempotent round
        existing_round = Mock(spec=ConversationRound)
        existing_round.id = uuid4()
        existing_round.round_path = "3"
        existing_round.correlation_id = correlation_id
        mock_db.scalar.side_effect = [mock_session, existing_round]  # Session + existing round

        # Mock event handling for idempotent case
        mock_event_handler.ensure_round_events.return_value = existing_round

        # Mock serialization
        serialized_round = {"session_id": str(session_id), "round_path": "3"}
        mock_serializer.serialize_round.return_value = serialized_round

        # Act
        result = await round_service.create_round(
            mock_db, user_id, session_id, role=role, input_data=input_data, model=model, correlation_id=correlation_id
        )

        # Assert
        assert result["success"] is True
        assert result["round"] == existing_round
        mock_event_handler.ensure_round_events.assert_called_once()
        mock_cache.cache_round.assert_called_once_with(str(session_id), "3", serialized_round)

    @pytest.mark.asyncio
    async def test_create_round_session_not_found(self, round_service, mock_db):
        """Test creating round when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session not found
        mock_db.scalar.return_value = None

        # Act
        result = await round_service.create_round(mock_db, user_id, session_id, role=DialogueRole.USER, input_data={})

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_create_round_access_denied(self, round_service, mock_db, mock_access_control):
        """Test creating round when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session exists but access denied
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await round_service.create_round(mock_db, user_id, session_id, role=DialogueRole.USER, input_data={})

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403

    @pytest.mark.asyncio
    async def test_create_round_exception(self, round_service, mock_db, mock_access_control):
        """Test creating round when database raises exception."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock database exception
        mock_db.scalar.side_effect = [mock_session, Exception("Database error")]

        # Act
        result = await round_service.create_round(mock_db, user_id, session_id, role=DialogueRole.USER, input_data={})

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to create round"

    @pytest.mark.asyncio
    async def test_get_round_from_cache(self, round_service, mock_db, mock_cache, mock_access_control):
        """Test getting round from cache."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "5"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock cached round
        cached_round = {"session_id": str(session_id), "round_path": round_path}
        mock_cache.get_round.return_value = cached_round

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is True
        assert result["round"] == cached_round
        assert result.get("cached") is True
        # Should not query database for round
        assert mock_db.scalar.call_count == 1  # Only session query

    @pytest.mark.asyncio
    async def test_get_round_from_database(
        self, round_service, mock_db, mock_cache, mock_access_control, mock_serializer
    ):
        """Test getting round from database when not in cache."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "7"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock cache miss
        mock_cache.get_round.return_value = None

        # Mock database round
        db_round = Mock(spec=ConversationRound)
        db_round.id = uuid4()
        db_round.round_path = round_path
        mock_db.scalar.side_effect = [mock_session, db_round]

        # Mock serialization
        serialized_round = {"session_id": str(session_id), "round_path": round_path}
        mock_serializer.serialize_round.return_value = serialized_round

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is True
        assert result["round"] == db_round
        mock_cache.cache_round.assert_called_once_with(str(session_id), round_path, serialized_round)

    @pytest.mark.asyncio
    async def test_get_round_not_found(self, round_service, mock_db, mock_cache, mock_access_control):
        """Test getting round that doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "999"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock cache miss and database miss
        mock_cache.get_round.return_value = None
        mock_db.scalar.side_effect = [mock_session, None]  # Session exists, round doesn't

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Round not found"
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_get_round_session_not_found(self, round_service, mock_db):
        """Test getting round when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "1"

        # Mock session not found
        mock_db.scalar.return_value = None

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_get_round_access_denied(self, round_service, mock_db, mock_access_control):
        """Test getting round when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "1"

        # Mock session exists but access denied
        mock_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = mock_session
        mock_access_control.verify_session_access.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403

    @pytest.mark.asyncio
    async def test_get_round_database_exception(self, round_service, mock_db, mock_access_control):
        """Test getting round when database raises exception."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "1"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock database exception
        mock_db.scalar.side_effect = [mock_session, Exception("Database error")]

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to get round"

    def test_compute_next_round_path(self, round_service):
        """Test computing next round path from count."""
        # Test with zero existing rounds
        assert round_service._compute_next_round_path(0) == "1"

        # Test with existing rounds
        assert round_service._compute_next_round_path(5) == "6"
        assert round_service._compute_next_round_path(999) == "1000"

    def test_parse_correlation_uuid_valid(self, round_service):
        """Test parsing valid correlation ID to UUID."""
        # Arrange
        correlation_id = str(uuid4())

        # Act
        result = round_service._parse_correlation_uuid(correlation_id)

        # Assert
        assert result is not None
        assert str(result) == correlation_id

    def test_parse_correlation_uuid_invalid(self, round_service):
        """Test parsing invalid correlation ID."""
        # Test with invalid UUID string
        assert round_service._parse_correlation_uuid("invalid-uuid") is None

        # Test with None
        assert round_service._parse_correlation_uuid(None) is None

        # Test with empty string
        assert round_service._parse_correlation_uuid("") is None
