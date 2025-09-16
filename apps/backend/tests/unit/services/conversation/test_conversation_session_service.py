"""Unit tests for conversation session service."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.conversation.conversation_session_service import ConversationSessionService
from src.models.conversation import ConversationSession
from src.schemas.novel.dialogue import ScopeType, SessionStatus


class TestConversationSessionService:
    """Test conversation session service functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_cache(self):
        """Create mock conversation cache."""
        cache = AsyncMock()
        cache.cache_session = AsyncMock()
        cache.get_session = AsyncMock()
        cache.clear_session = AsyncMock()
        cache.list_sessions = AsyncMock()
        return cache

    @pytest.fixture
    def mock_access_control(self):
        """Create mock access control."""
        access_control = AsyncMock()
        access_control.get_novel_for_scope = AsyncMock()
        access_control.verify_cached_session_access = AsyncMock()
        access_control.verify_session_access = AsyncMock()
        return access_control

    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer."""
        return Mock()

    @pytest.fixture
    def mock_repository(self):
        """Create mock conversation session repository."""
        repository = AsyncMock()
        repository.find_active_by_scope = AsyncMock()
        repository.create = AsyncMock()
        repository.find_by_id = AsyncMock()
        repository.update = AsyncMock()
        repository.delete = AsyncMock()
        repository.list_by_user = AsyncMock()
        return repository

    @pytest.fixture
    def session_service(self, mock_cache, mock_access_control, mock_serializer, mock_repository):
        """Create ConversationSessionService instance."""
        return ConversationSessionService(mock_cache, mock_access_control, mock_serializer, mock_repository)

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, session_service, mock_db, mock_access_control, mock_cache, mock_serializer, mock_repository
    ):
        """Test successful session creation."""
        # Arrange
        user_id = 123
        scope_type = ScopeType.GENESIS
        scope_id = str(uuid4())
        stage = "worldbuilding"
        initial_state = {"key": "value"}

        # Mock successful access check
        mock_access_control.get_novel_for_scope.return_value = {"success": True}

        # Mock no existing session
        mock_repository.find_active_by_scope.return_value = None

        # Mock successful session creation
        created_session = Mock(spec=ConversationSession)
        created_session.id = uuid4()
        mock_repository.create.return_value = created_session

        # Mock serialization
        serialized_session = {"id": str(created_session.id), "scope_type": "genesis"}
        mock_serializer.serialize_session.return_value = serialized_session

        # Act
        result = await session_service.create_session(mock_db, user_id, scope_type, scope_id, stage, initial_state)

        # Assert
        assert result["success"] is True
        assert result["session"] == serialized_session
        mock_access_control.get_novel_for_scope.assert_awaited_once_with(
            mock_db, user_id, ScopeType.GENESIS.value, scope_id
        )
        mock_repository.find_active_by_scope.assert_awaited_once_with(scope_type.value, str(scope_id))
        mock_repository.create.assert_awaited_once_with(
            scope_type=scope_type.value,
            scope_id=str(scope_id),
            status=SessionStatus.ACTIVE.value,
            stage=stage,
            state=initial_state,
            version=1,
        )
        mock_cache.cache_session.assert_awaited_once_with(str(created_session.id), serialized_session)

    @pytest.mark.asyncio
    async def test_create_session_unsupported_scope(self, session_service, mock_db):
        """Test session creation with unsupported scope type."""
        # Arrange
        user_id = 123
        scope_type = "unsupported_scope"  # Not ScopeType.GENESIS
        scope_id = str(uuid4())

        # Act
        result = await session_service.create_session(mock_db, user_id, scope_type, scope_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Only GENESIS scope is supported"
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_session_access_denied(self, session_service, mock_db, mock_access_control):
        """Test session creation when access is denied."""
        # Arrange
        user_id = 123
        scope_type = ScopeType.GENESIS
        scope_id = str(uuid4())

        # Mock access denied
        mock_access_control.get_novel_for_scope.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await session_service.create_session(mock_db, user_id, scope_type, scope_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_session_existing_active_session(self, session_service, mock_db, mock_access_control, mock_repository):
        """Test session creation when active session already exists."""
        # Arrange
        user_id = 123
        scope_type = ScopeType.GENESIS
        scope_id = str(uuid4())

        # Mock successful access check
        mock_access_control.get_novel_for_scope.return_value = {"success": True}

        # Mock existing active session
        existing_session = Mock(spec=ConversationSession)
        mock_repository.find_active_by_scope.return_value = existing_session

        # Act
        result = await session_service.create_session(mock_db, user_id, scope_type, scope_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "An active session already exists for this novel"
        assert result["code"] == 409
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_session_database_exception(self, session_service, mock_db, mock_access_control):
        """Test session creation when database raises exception."""
        # Arrange
        user_id = 123
        scope_type = ScopeType.GENESIS
        scope_id = str(uuid4())

        # Mock successful access check
        mock_access_control.get_novel_for_scope.return_value = {"success": True}

        # Mock no existing session
        mock_db.scalar.return_value = None

        # Mock database exception during commit
        mock_db.commit.side_effect = Exception("Database error")

        # Act
        result = await session_service.create_session(mock_db, user_id, scope_type, scope_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Failed to create session"
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_from_cache(self, session_service, mock_db, mock_cache, mock_access_control):
        """Test getting session from cache with successful access verification."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock cached session
        cached_session = {"id": str(session_id), "scope_type": "genesis", "scope_id": str(uuid4())}
        mock_cache.get_session.return_value = cached_session

        # Mock successful access verification
        mock_access_control.verify_cached_session_access.return_value = {"success": True}

        # Act
        result = await session_service.get_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is True
        assert result["session"] == cached_session
        assert result.get("cached") is True
        mock_db.scalar.assert_not_called()  # Should not query DB

    @pytest.mark.asyncio
    async def test_get_session_cache_access_denied(self, session_service, mock_db, mock_cache, mock_access_control):
        """Test getting session from cache when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock cached session
        cached_session = {"id": str(session_id), "scope_type": "genesis", "scope_id": str(uuid4())}
        mock_cache.get_session.return_value = cached_session

        # Mock access denied
        mock_access_control.verify_cached_session_access.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await session_service.get_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403

    @pytest.mark.asyncio
    async def test_get_session_from_database(
        self, session_service, mock_db, mock_cache, mock_access_control, mock_serializer, mock_repository
    ):
        """Test getting session from database when not in cache."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock cache miss
        mock_cache.get_session.return_value = None

        # Mock database session
        db_session = Mock(spec=ConversationSession)
        db_session.id = session_id
        db_session.scope_type = "genesis"
        db_session.scope_id = "novel-123"
        db_session.status = "active"
        mock_repository.find_by_id.return_value = db_session

        # Mock successful access verification
        mock_access_control.verify_cached_session_access.return_value = {"success": True}

        # Mock serialization
        serialized_session = {"id": str(session_id), "scope_type": "genesis"}
        mock_serializer.serialize_session.return_value = serialized_session

        # Act
        result = await session_service.get_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is True
        assert result["session"] == serialized_session
        mock_repository.find_by_id.assert_called_once_with(session_id)
        mock_cache.cache_session.assert_called_once_with(str(session_id), serialized_session)

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_service, mock_db, mock_cache, mock_repository):
        """Test getting session that doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock cache miss and database miss
        mock_cache.get_session.return_value = None
        mock_repository.find_by_id.return_value = None

        # Act
        result = await session_service.get_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_update_session_success(
        self, session_service, mock_db, mock_access_control, mock_cache, mock_serializer, mock_repository
    ):
        """Test successful session update."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        new_status = SessionStatus.COMPLETED
        new_stage = "finished"
        new_state = {"finished": True}
        expected_version = 1

        # Mock existing session
        existing_session = Mock(spec=ConversationSession)
        existing_session.id = session_id
        existing_session.scope_type = "genesis"
        existing_session.scope_id = "novel-123"
        existing_session.status = "active"
        mock_repository.find_by_id.return_value = existing_session

        # Mock successful access verification
        mock_access_control.verify_cached_session_access.return_value = {"success": True}

        # Mock successful update
        updated_session = Mock(spec=ConversationSession)
        updated_session.id = session_id
        mock_repository.update.return_value = updated_session

        # Mock serialization
        serialized_session = {"id": str(session_id), "status": "completed"}
        mock_serializer.serialize_session.return_value = serialized_session

        # Act
        result = await session_service.update_session(
            mock_db,
            user_id,
            session_id,
            status=new_status,
            stage=new_stage,
            state=new_state,
            expected_version=expected_version,
        )

        # Assert
        assert result["success"] is True
        assert result["session"] == serialized_session
        mock_repository.find_by_id.assert_called_once_with(session_id)
        mock_repository.update.assert_called_once_with(
            session_id=session_id,
            status=new_status.value,
            stage=new_stage,
            state=new_state,
            expected_version=expected_version,
        )
        mock_cache.cache_session.assert_called_once_with(str(session_id), serialized_session)

    @pytest.mark.asyncio
    async def test_update_session_not_found(self, session_service, mock_db, mock_repository):
        """Test updating session that doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session not found
        mock_repository.find_by_id.return_value = None

        # Act
        result = await session_service.update_session(mock_db, user_id, session_id, status=SessionStatus.COMPLETED)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404

    @pytest.mark.asyncio
    async def test_update_session_access_denied(self, session_service, mock_db, mock_access_control, mock_repository):
        """Test updating session when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock existing session
        existing_session = Mock(spec=ConversationSession)
        existing_session.scope_type = "genesis"
        existing_session.scope_id = "novel-123"
        existing_session.status = "active"
        mock_repository.find_by_id.return_value = existing_session

        # Mock access denied
        mock_access_control.verify_cached_session_access.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await session_service.update_session(mock_db, user_id, session_id, status=SessionStatus.COMPLETED)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403

    @pytest.mark.asyncio
    async def test_update_session_no_changes(self, session_service, mock_db, mock_access_control):
        """Test updating session with no actual changes."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock existing session
        existing_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = existing_session

        # Mock successful access verification
        mock_access_control.verify_session_access.return_value = {"success": True, "session": existing_session}

        # Act - no parameters to update
        result = await session_service.update_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is True
        assert result["session"] == existing_session
        mock_db.execute.assert_not_called()  # No update executed

    @pytest.mark.asyncio
    async def test_update_session_version_conflict(self, session_service, mock_db, mock_access_control):
        """Test updating session with version conflict."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock existing session
        existing_session = Mock(spec=ConversationSession)
        mock_db.scalar.return_value = existing_session

        # Mock successful access verification
        mock_access_control.verify_session_access.return_value = {"success": True, "session": existing_session}

        # Mock update returning None (version conflict)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await session_service.update_session(
            mock_db, user_id, session_id, status=SessionStatus.COMPLETED, expected_version=999
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Version mismatch or conflict"
        assert result["code"] == 412
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_session_success(self, session_service, mock_db, mock_access_control, mock_cache, mock_repository):
        """Test successful session deletion."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock existing session
        existing_session = Mock(spec=ConversationSession)
        existing_session.id = session_id
        existing_session.scope_type = "genesis"
        existing_session.scope_id = "novel-123"
        existing_session.status = "active"
        mock_repository.find_by_id.return_value = existing_session

        # Mock successful access verification
        mock_access_control.verify_cached_session_access.return_value = {"success": True}

        # Mock successful deletion
        mock_repository.delete.return_value = True

        # Act
        result = await session_service.delete_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is True
        mock_repository.delete.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, session_service, mock_db):
        """Test deleting session that doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session not found
        mock_db.scalar.return_value = None

        # Act
        result = await session_service.delete_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Session not found"
        assert result["code"] == 404
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_session_access_denied(self, session_service, mock_db, mock_access_control, mock_repository):
        """Test deleting session when access is denied."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock existing session
        existing_session = Mock(spec=ConversationSession)
        existing_session.scope_type = "genesis"
        existing_session.scope_id = "novel-123"
        existing_session.status = "active"
        mock_repository.find_by_id.return_value = existing_session

        # Mock access denied
        mock_access_control.verify_cached_session_access.return_value = {
            "success": False,
            "error": "Access denied",
            "code": 403,
        }

        # Act
        result = await session_service.delete_session(mock_db, user_id, session_id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Access denied"
        assert result["code"] == 403
        mock_repository.delete.assert_not_called()
