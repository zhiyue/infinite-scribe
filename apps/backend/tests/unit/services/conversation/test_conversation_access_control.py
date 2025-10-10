"""Unit tests for conversation access control."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.models.conversation import ConversationSession
from src.models.novel import Novel
from src.schemas.novel.dialogue import ScopeType


class TestConversationAccessControl:
    """Test conversation access control functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_verify_scope_access_with_valid_novel_id(self, mock_db):
        """Test scope access check with valid novel ID and ownership."""
        # Arrange
        user_id = 123
        novel_id = uuid4()
        scope_type = ScopeType.GENESIS.value

        # Mock successful novel query - returns novel_id to indicate existence
        mock_db.scalar.return_value = novel_id

        # Act
        result = await ConversationAccessControl.verify_scope_access(mock_db, user_id, scope_type, str(novel_id))

        # Assert
        assert result == {"success": True}
        mock_db.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_scope_access_with_invalid_novel_id_format(self, mock_db):
        """Test scope access check with invalid UUID format."""
        # Arrange
        user_id = 123
        scope_type = ScopeType.GENESIS.value
        invalid_novel_id = "not-a-uuid"

        # Act
        result = await ConversationAccessControl.verify_scope_access(mock_db, user_id, scope_type, invalid_novel_id)

        # Assert
        assert result == {"success": False, "error": "Invalid novel id", "code": 422}
        mock_db.scalar.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_scope_access_with_nonexistent_novel(self, mock_db):
        """Test scope access check when novel doesn't exist."""
        # Arrange
        user_id = 123
        novel_id = uuid4()
        scope_type = ScopeType.GENESIS.value

        # Mock novel not found
        mock_db.scalar.return_value = None

        # Act
        result = await ConversationAccessControl.verify_scope_access(mock_db, user_id, scope_type, str(novel_id))

        # Assert
        assert result == {"success": False, "error": "Access denied", "code": 403}
        mock_db.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_scope_access_with_different_user(self, mock_db):
        """Test scope access check when novel belongs to different user."""
        # Arrange
        user_id = 123
        novel_id = uuid4()
        scope_type = ScopeType.GENESIS.value

        # Mock novel owned by different user (query returns None due to user_id filter)
        mock_db.scalar.return_value = None

        # Act
        result = await ConversationAccessControl.verify_scope_access(mock_db, user_id, scope_type, str(novel_id))

        # Assert
        assert result == {"success": False, "error": "Access denied", "code": 403}

    @pytest.mark.asyncio
    async def test_verify_scope_access_with_database_exception(self, mock_db):
        """Test scope access check when database raises exception."""
        # Arrange
        user_id = 123
        novel_id = uuid4()
        scope_type = ScopeType.GENESIS.value

        # Mock database exception
        mock_db.scalar.side_effect = Exception("Database connection failed")

        # Act
        result = await ConversationAccessControl.verify_scope_access(mock_db, user_id, scope_type, str(novel_id))

        # Assert
        assert result == {"success": False, "error": "Failed to verify scope access"}

    @pytest.mark.asyncio
    async def test_verify_session_access_with_genesis_scope(self, mock_db):
        """Test session access verification with GENESIS scope."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        novel_id = uuid4()

        mock_session = Mock(spec=ConversationSession)
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(novel_id)

        # Mock session query and novel access check
        mock_db.scalar.side_effect = [mock_session, novel_id]  # Session exists, novel access granted

        # Act
        result = await ConversationAccessControl.verify_session_access(mock_db, user_id, session_id)

        # Assert
        assert result == {"success": True, "session": mock_session}

    @pytest.mark.asyncio
    async def test_verify_session_access_with_session_not_found(self, mock_db):
        """Test session access verification when session doesn't exist."""
        # Arrange
        user_id = 123
        session_id = uuid4()

        # Mock session not found
        mock_db.scalar.return_value = None

        # Act
        result = await ConversationAccessControl.verify_session_access(mock_db, user_id, session_id)

        # Assert
        assert result == {"success": False, "error": "Session not found", "code": 404}

    @pytest.mark.asyncio
    async def test_verify_session_access_with_no_novel_access(self, mock_db):
        """Test session access verification when user has no access to novel."""
        # Arrange
        user_id = 123
        session_id = uuid4()
        novel_id = uuid4()

        mock_session = Mock(spec=ConversationSession)
        mock_session.scope_type = ScopeType.GENESIS.value
        mock_session.scope_id = str(novel_id)

        # Mock session found but no novel access
        mock_db.scalar.side_effect = [mock_session, None]  # Session exists, novel access denied

        # Act
        result = await ConversationAccessControl.verify_session_access(mock_db, user_id, session_id)

        # Assert
        assert result == {"success": False, "error": "Access denied", "code": 403}

    @pytest.mark.asyncio
    async def test_verify_cached_session_access_with_valid_genesis(self, mock_db):
        """Test cached session access verification with valid GENESIS session."""
        # Arrange
        user_id = 123
        novel_id = uuid4()

        cached_session = {"scope_type": ScopeType.GENESIS.value, "scope_id": str(novel_id), "status": "active"}

        # Mock successful novel query
        mock_db.scalar.return_value = novel_id  # Novel exists for this user

        # Act
        result = await ConversationAccessControl.verify_cached_session_access(mock_db, user_id, cached_session)

        # Assert
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_verify_cached_session_access_with_invalid_scope_id(self, mock_db):
        """Test cached session access verification with invalid scope ID."""
        # Arrange
        user_id = 123

        cached_session = {"scope_type": ScopeType.GENESIS.value, "scope_id": "invalid-uuid", "status": "active"}

        # Act
        result = await ConversationAccessControl.verify_cached_session_access(mock_db, user_id, cached_session)

        # Assert
        assert result == {"success": False, "error": "Invalid novel id", "code": 422}
        mock_db.scalar.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_cached_session_access_with_no_novel_access(self, mock_db):
        """Test cached session access verification when user has no novel access."""
        # Arrange
        user_id = 123
        novel_id = uuid4()

        cached_session = {"scope_type": ScopeType.GENESIS.value, "scope_id": str(novel_id), "status": "active"}

        # Mock novel not found for this user
        mock_db.scalar.return_value = None

        # Act
        result = await ConversationAccessControl.verify_cached_session_access(mock_db, user_id, cached_session)

        # Assert
        assert result == {"success": False, "error": "Access denied", "code": 403}

    @pytest.mark.asyncio
    async def test_verify_cached_session_access_with_missing_data(self, mock_db):
        """Test cached session access verification with missing session data."""
        # Arrange
        user_id = 123

        cached_session = {
            "status": "active"  # Missing scope_type and scope_id
        }

        # Act
        result = await ConversationAccessControl.verify_cached_session_access(mock_db, user_id, cached_session)

        # Assert
        assert result == {"success": False, "error": "Invalid cached session data"}
        mock_db.scalar.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_novel_for_scope_with_valid_genesis(self, mock_db):
        """Test getting novel for valid GENESIS scope."""
        # Arrange
        user_id = 123
        novel_id = uuid4()
        scope_type = ScopeType.GENESIS.value

        mock_novel = Mock(spec=Novel)
        mock_novel.id = novel_id
        mock_novel.user_id = user_id
        mock_db.scalar.return_value = mock_novel

        # Act
        result = await ConversationAccessControl.get_novel_for_scope(mock_db, user_id, scope_type, str(novel_id))

        # Assert
        assert result == {"success": True, "novel": mock_novel}
        mock_db.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_for_scope_with_invalid_scope_type(self, mock_db):
        """Test getting novel for invalid scope type."""
        # Arrange
        user_id = 123
        novel_id = uuid4()
        scope_type = "invalid_scope"

        # Act
        result = await ConversationAccessControl.get_novel_for_scope(mock_db, user_id, scope_type, str(novel_id))

        # Assert
        assert result == {"success": False, "error": "Only GENESIS scope is supported"}
        mock_db.scalar.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_novel_for_scope_with_invalid_uuid(self, mock_db):
        """Test getting novel with invalid UUID format."""
        # Arrange
        user_id = 123
        scope_type = ScopeType.GENESIS.value
        invalid_novel_id = "not-a-uuid"

        # Act
        result = await ConversationAccessControl.get_novel_for_scope(mock_db, user_id, scope_type, invalid_novel_id)

        # Assert
        assert result == {"success": False, "error": "Invalid novel id", "code": 422}
        mock_db.scalar.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_novel_for_scope_novel_not_found(self, mock_db):
        """Test getting novel when novel doesn't exist or access denied."""
        # Arrange
        user_id = 123
        novel_id = uuid4()
        scope_type = ScopeType.GENESIS.value

        # Mock novel not found
        mock_db.scalar.return_value = None

        # Act
        result = await ConversationAccessControl.get_novel_for_scope(mock_db, user_id, scope_type, str(novel_id))

        # Assert
        assert result == {"success": False, "error": "Novel not found or access denied", "code": 403}

    @pytest.mark.asyncio
    async def test_verify_scope_access_with_unsupported_scope(self, mock_db):
        """Test scope access check with unsupported scope type."""
        # Arrange
        user_id = 123
        scope_id = "some-id"
        scope_type = "unsupported_scope"

        # Act
        result = await ConversationAccessControl.verify_scope_access(mock_db, user_id, scope_type, scope_id)

        # Assert
        assert result == {"success": False, "error": "Only GENESIS scope is supported"}
        mock_db.scalar.assert_not_called()
