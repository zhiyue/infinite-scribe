"""Unit tests for JWT refresh token functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.services.jwt_service import jwt_service
from tests.unit.test_mocks import mock_redis


class TestJWTRefreshToken:
    """Test cases for JWT refresh token functionality."""

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_create_refresh_token_basic(self):
        """Test basic refresh token creation."""
        # Arrange
        user_id = "123"

        # Act
        token, expires_at = jwt_service.create_refresh_token(user_id)

        # Assert
        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

        # Verify token can be decoded
        payload = jwt_service.verify_token(token, "refresh")
        assert payload["sub"] == user_id
        assert payload["token_type"] == "refresh"

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    @patch("src.common.services.session_service.session_service")
    async def test_refresh_access_token_success(self, mock_session_service):
        """Test successful access token refresh."""
        # Arrange
        user_id = "123"
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        
        # Mock database session
        mock_db = AsyncMock()
        
        # Mock session with user
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        
        mock_session = Mock()
        mock_session.is_valid = True
        mock_session.user_id = int(user_id)
        mock_session.refresh_token = refresh_token
        mock_session.id = 1
        mock_session.user = mock_user
        
        # Mock session service methods
        mock_session_service.get_session_by_refresh_token = AsyncMock(return_value=mock_session)
        mock_session_service.update_session_tokens = AsyncMock()
        mock_session_service._cache_session = AsyncMock()

        # Act
        result = await jwt_service.refresh_access_token(mock_db, refresh_token)

        # Assert
        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result
        assert "expires_at" in result

        # Verify new access token is valid
        new_access_token = result["access_token"]
        payload = jwt_service.verify_token(new_access_token, "access")
        assert payload["sub"] == user_id
        assert payload["token_type"] == "access"

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    async def test_refresh_access_token_invalid_refresh_token(self):
        """Test refresh with invalid refresh token."""
        # Arrange
        invalid_token = "invalid.token.here"
        mock_db = AsyncMock()

        # Act
        result = await jwt_service.refresh_access_token(mock_db, invalid_token)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    async def test_refresh_access_token_expired_refresh_token(self):
        """Test refresh with expired refresh token."""
        # Arrange
        user_id = "123"
        mock_db = AsyncMock()

        # Create expired refresh token by temporarily changing token expiration
        original_days = jwt_service.refresh_token_expire_days
        jwt_service.refresh_token_expire_days = -1  # Set to negative to create expired token
        
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        
        # Restore original expiration
        jwt_service.refresh_token_expire_days = original_days

        # Act (with current time)
        result = await jwt_service.refresh_access_token(mock_db, refresh_token)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "expired" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    async def test_refresh_access_token_wrong_token_type(self):
        """Test refresh with access token instead of refresh token."""
        # Arrange
        user_id = "123"
        access_token, _, _ = jwt_service.create_access_token(user_id)
        mock_db = AsyncMock()

        # Act
        result = await jwt_service.refresh_access_token(mock_db, access_token)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "token type" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    @patch("src.common.services.session_service.session_service")
    async def test_refresh_token_rotation(self, mock_session_service):
        """Test that refresh generates new refresh token."""
        # Arrange
        user_id = "123"
        original_refresh_token, _ = jwt_service.create_refresh_token(user_id)
        mock_db = AsyncMock()
        
        # Mock session with user
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        
        mock_session = Mock()
        mock_session.is_valid = True
        mock_session.user_id = int(user_id)
        mock_session.refresh_token = original_refresh_token
        mock_session.id = 1
        mock_session.user = mock_user
        
        # Mock session service methods
        mock_session_service.get_session_by_refresh_token = AsyncMock(return_value=mock_session)
        mock_session_service.update_session_tokens = AsyncMock()
        mock_session_service._cache_session = AsyncMock()

        # Act
        result = await jwt_service.refresh_access_token(mock_db, original_refresh_token)

        # Assert
        assert result["success"] is True
        new_refresh_token = result["refresh_token"]

        # New refresh token should be different
        assert new_refresh_token != original_refresh_token

        # Both tokens should be valid (for now)
        payload1 = jwt_service.verify_token(original_refresh_token, "refresh")
        payload2 = jwt_service.verify_token(new_refresh_token, "refresh")
        assert payload1["sub"] == payload2["sub"]

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    @patch("src.common.services.session_service.session_service")
    async def test_refresh_token_blacklist_old_access_token(self, mock_session_service):
        """Test that refresh blacklists the old access token if provided."""
        # Arrange
        user_id = "123"
        old_access_token, old_jti, old_expires = jwt_service.create_access_token(user_id)
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        mock_db = AsyncMock()
        
        # Mock session with user
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        
        mock_session = Mock()
        mock_session.is_valid = True
        mock_session.user_id = int(user_id)
        mock_session.refresh_token = refresh_token
        mock_session.id = 1
        mock_session.user = mock_user
        
        # Mock session service methods
        mock_session_service.get_session_by_refresh_token = AsyncMock(return_value=mock_session)
        mock_session_service.update_session_tokens = AsyncMock()
        mock_session_service._cache_session = AsyncMock()

        # Act
        result = await jwt_service.refresh_access_token(mock_db, refresh_token, old_access_token)

        # Assert
        assert result["success"] is True

        # Old access token should be blacklisted
        assert jwt_service.is_token_blacklisted(old_jti) is True

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    @patch("src.common.services.session_service.session_service")
    async def test_refresh_token_performance(self, mock_session_service):
        """Test refresh token performance."""
        # Arrange
        user_id = "123"
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        mock_db = AsyncMock()
        
        # Mock session with user
        mock_user = Mock()
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"
        
        mock_session = Mock()
        mock_session.is_valid = True
        mock_session.user_id = int(user_id)
        mock_session.refresh_token = refresh_token
        mock_session.id = 1
        mock_session.user = mock_user
        
        # Mock session service methods to return updated tokens
        def update_refresh_token(*args):
            nonlocal refresh_token
            # Simulate token rotation - return the new token from the result
            return None
            
        mock_session_service.get_session_by_refresh_token = AsyncMock(return_value=mock_session)
        mock_session_service.update_session_tokens = AsyncMock(side_effect=update_refresh_token)
        mock_session_service._cache_session = AsyncMock()

        # Act & Assert
        import time

        start_time = time.time()

        for _ in range(10):
            result = await jwt_service.refresh_access_token(mock_db, refresh_token)
            assert result["success"] is True
            # Use the new refresh token for next iteration
            refresh_token = result["refresh_token"]
            # Update mock to return session with new token
            mock_session.refresh_token = refresh_token

        end_time = time.time()

        # Should complete 10 refreshes in under 1 second
        assert (end_time - start_time) < 1.0
