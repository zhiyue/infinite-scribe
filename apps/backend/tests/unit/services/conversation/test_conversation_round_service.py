"""Unit tests for conversation round service."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.conversation.conversation_round_service import ConversationRoundService
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import DialogueRole, ScopeType


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
        handler = AsyncMock()
        handler.create_round_support_events = AsyncMock()
        handler.ensure_round_events = AsyncMock()
        return handler

    @pytest.fixture
    def mock_repository(self):
        """Create mock conversation round repository."""
        repository = AsyncMock()
        repository.list_by_session = AsyncMock()
        repository.find_by_session_and_path = AsyncMock()
        repository.find_by_correlation_id = AsyncMock()
        repository.create = AsyncMock()
        return repository

    @pytest.fixture
    def round_service(
        self,
        mock_cache,
        mock_access_control,
        mock_serializer,
        mock_event_handler,
        mock_repository,
    ):
        """Create ConversationRoundService instance."""
        return ConversationRoundService(
            cache=mock_cache,
            access_control=mock_access_control,
            serializer=mock_serializer,
            event_handler=mock_event_handler,
            repository=mock_repository,
        )

    @pytest.mark.asyncio
    async def test_list_rounds_success(self, round_service, mock_db, mock_access_control, mock_repository):
        """Test successful round listing."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session existence and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock rounds query result
        mock_round1 = Mock(spec=ConversationRound)
        mock_round2 = Mock(spec=ConversationRound)
        mock_repository.list_by_session.return_value = [mock_round1, mock_round2]

        # Act
        result = await round_service.list_rounds(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is True
        assert result["rounds"] == [mock_round1, mock_round2]
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)
        mock_repository.list_by_session.assert_awaited_once_with(
            session_id=session_id,
            after=None,
            limit=50,
            order="asc",
            role=None,
        )

    @pytest.mark.asyncio
    async def test_list_rounds_session_not_found(self, round_service, mock_db, mock_access_control):
        """Test listing rounds when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session not found
        mock_access_control.verify_session_access.return_value = {
            "success": False,
            "error": "Session not found",
            "code": 404,
        }

        # Act
        result = await round_service.list_rounds(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)

    @pytest.mark.asyncio
    async def test_list_rounds_access_denied(self, round_service, mock_db, mock_access_control):
        """Test listing rounds when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session exists but access denied
        mock_session = Mock(spec=ConversationSession)
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
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)

    @pytest.mark.asyncio
    async def test_list_rounds_with_filters(
        self, round_service, mock_db, mock_access_control, mock_repository
    ):
        """Test listing rounds with role filter and pagination."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        after = "5"
        limit = 10
        order = "desc"
        role = DialogueRole.USER

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock filtered query result
        mock_repository.find_by_session_and_path.return_value = Mock(spec=ConversationRound)
        mock_repository.list_by_session.return_value = []

        # Act
        result = await round_service.list_rounds(
            mock_db, user_id, session_id, after=after, limit=limit, order=order, role=role
        )

        # Assert
        assert result["success"] is True
        assert result["rounds"] == []
        mock_repository.find_by_session_and_path.assert_awaited_once_with(session_id, after)
        mock_repository.list_by_session.assert_awaited_once_with(
            session_id=session_id,
            after=after,
            limit=limit,
            order=order,
            role=role,
        )

    @pytest.mark.asyncio
    async def test_create_round_success_new(
        self,
        round_service,
        mock_db,
        mock_access_control,
        mock_event_handler,
        mock_cache,
        mock_serializer,
        mock_repository,
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
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(uuid4())
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # No existing idempotent round
        mock_repository.find_by_correlation_id.return_value = None

        # Round sequence increment
        sequence_result = Mock()
        sequence_result.scalar_one.return_value = 6
        mock_db.execute.return_value = sequence_result

        # Mock successful round creation
        created_round = Mock(spec=ConversationRound)
        created_round.id = uuid4()
        created_round.round_path = "6"
        created_round.session_id = session_id
        mock_repository.create.return_value = created_round

        # Mock serialization
        serialized_round = {"session_id": str(session_id), "round_path": "6"}
        mock_serializer.serialize_round.return_value = serialized_round

        # Act
        result = await round_service.create_round(
            mock_db,
            user_id,
            session_id,
            role=role,
            input_data=input_data,
            model=model,
            correlation_id=correlation_id,
        )

        # Assert
        assert result["success"] is True
        assert result["round"] == created_round
        assert result["serialized_round"] == serialized_round
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)
        mock_repository.find_by_correlation_id.assert_awaited_once()
        mock_repository.create.assert_awaited_once()
        mock_event_handler.create_round_support_events.assert_awaited_once()
        mock_serializer.serialize_round.assert_called_once_with(created_round)
        mock_cache.cache_round.assert_awaited_once_with(str(session_id), "6", serialized_round)

    @pytest.mark.asyncio
    async def test_create_round_idempotent_replay(
        self,
        round_service,
        mock_db,
        mock_access_control,
        mock_event_handler,
        mock_cache,
        mock_serializer,
        mock_repository,
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
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(uuid4())
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock existing idempotent round
        existing_round = Mock(spec=ConversationRound)
        existing_round.id = uuid4()
        existing_round.round_path = "3"
        existing_round.correlation_id = correlation_id
        existing_round.session_id = session_id
        mock_repository.find_by_correlation_id.return_value = existing_round

        # Mock event handling for idempotent case
        mock_event_handler.ensure_round_events.return_value = None

        # Mock serialization
        serialized_round = {"session_id": str(session_id), "round_path": "3"}
        mock_serializer.serialize_round.return_value = serialized_round

        # Act
        result = await round_service.create_round(
            mock_db,
            user_id,
            session_id,
            role=role,
            input_data=input_data,
            model=model,
            correlation_id=correlation_id,
        )

        # Assert
        assert result["success"] is True
        assert result["round"] == existing_round
        assert result["serialized_round"] == serialized_round
        mock_repository.find_by_correlation_id.assert_awaited_once()
        mock_repository.create.assert_not_awaited()
        mock_event_handler.ensure_round_events.assert_awaited_once()
        mock_serializer.serialize_round.assert_called_once_with(existing_round)
        mock_cache.cache_round.assert_awaited_once_with(str(session_id), "3", serialized_round)

    @pytest.mark.asyncio
    async def test_create_round_session_not_found(self, round_service, mock_db, mock_access_control):
        """Test creating round when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session not found
        mock_access_control.verify_session_access.return_value = {
            "success": False,
            "error": "Session not found",
            "code": 404,
        }

        # Act
        result = await round_service.create_round(mock_db, user_id, session_id, role=DialogueRole.USER, input_data={})

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)

    @pytest.mark.asyncio
    async def test_create_round_access_denied(self, round_service, mock_db, mock_access_control):
        """Test creating round when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session exists but access denied
        mock_session = Mock(spec=ConversationSession)
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
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)

    @pytest.mark.asyncio
    async def test_create_round_exception(
        self, round_service, mock_db, mock_access_control, mock_repository
    ):
        """Test creating round when database raises exception."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(uuid4())
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock database exception
        sequence_result = Mock()
        sequence_result.scalar_one.return_value = 1
        mock_db.execute.return_value = sequence_result
        mock_repository.find_by_correlation_id.return_value = None
        mock_repository.create.side_effect = Exception("Database error")

        # Act
        result = await round_service.create_round(mock_db, user_id, session_id, role=DialogueRole.USER, input_data={})

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to create round"

    @pytest.mark.asyncio
    async def test_get_round_from_cache(
        self, round_service, mock_db, mock_cache, mock_access_control, mock_repository
    ):
        """Test getting round from cache."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "5"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(uuid4())
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
        assert result["serialized_round"] == cached_round
        mock_cache.get_round.assert_awaited_once_with(str(session_id), round_path)
        mock_repository.find_by_session_and_path.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_round_from_database(
        self,
        round_service,
        mock_db,
        mock_cache,
        mock_access_control,
        mock_serializer,
        mock_repository,
    ):
        """Test getting round from database when not in cache."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "7"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(uuid4())
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock cache miss
        mock_cache.get_round.return_value = None

        # Mock database round
        db_round = Mock(spec=ConversationRound)
        db_round.id = uuid4()
        db_round.round_path = round_path
        db_round.session_id = session_id
        mock_repository.find_by_session_and_path.return_value = db_round

        # Mock serialization
        serialized_round = {"session_id": str(session_id), "round_path": round_path}
        mock_serializer.serialize_round.return_value = serialized_round

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is True
        assert result["round"] == db_round
        assert result["serialized_round"] == serialized_round
        mock_cache.get_round.assert_awaited_once_with(str(session_id), round_path)
        mock_repository.find_by_session_and_path.assert_awaited_once_with(session_id, round_path)
        mock_cache.cache_round.assert_awaited_once_with(str(session_id), round_path, serialized_round)

    @pytest.mark.asyncio
    async def test_get_round_not_found(
        self, round_service, mock_db, mock_cache, mock_access_control, mock_repository
    ):
        """Test getting round that doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "999"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(uuid4())
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock cache miss and database miss
        mock_cache.get_round.return_value = None
        mock_repository.find_by_session_and_path.return_value = None

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Round not found"
        assert result["code"] == 404
        mock_cache.get_round.assert_awaited_once_with(str(session_id), round_path)
        mock_repository.find_by_session_and_path.assert_awaited_once_with(session_id, round_path)

    @pytest.mark.asyncio
    async def test_get_round_session_not_found(self, round_service, mock_db, mock_access_control):
        """Test getting round when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "1"

        # Mock session not found
        mock_access_control.verify_session_access.return_value = {
            "success": False,
            "error": "Session not found",
            "code": 404,
        }

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)

    @pytest.mark.asyncio
    async def test_get_round_access_denied(self, round_service, mock_db, mock_access_control):
        """Test getting round when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "1"

        # Mock session exists but access denied
        mock_session = Mock(spec=ConversationSession)
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
        mock_access_control.verify_session_access.assert_awaited_once_with(mock_db, user_id, session_id)

    @pytest.mark.asyncio
    async def test_get_round_database_exception(
        self, round_service, mock_db, mock_access_control, mock_cache, mock_repository
    ):
        """Test getting round when database raises exception."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        round_path = "1"

        # Mock session and access
        mock_session = Mock(spec=ConversationSession)
        mock_session.id = session_id
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(uuid4())
        mock_access_control.verify_session_access.return_value = {"success": True, "session": mock_session}

        # Mock database exception
        mock_cache.get_round.return_value = None
        mock_repository.find_by_session_and_path.side_effect = Exception("Database error")

        # Act
        result = await round_service.get_round(mock_db, user_id, session_id, round_path)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to get round"
        mock_repository.find_by_session_and_path.assert_awaited_once_with(session_id, round_path)

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
