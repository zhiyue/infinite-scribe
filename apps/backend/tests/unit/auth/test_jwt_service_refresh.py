"""Unit tests for JWT refresh token functionality."""

from datetime import datetime, timedelta
from unittest.mock import patch

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
        assert expires_at > datetime.utcnow()

        # Verify token can be decoded
        payload = jwt_service.verify_token(token, "refresh")
        assert payload["sub"] == user_id
        assert payload["token_type"] == "refresh"

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_refresh_access_token_success(self):
        """Test successful access token refresh."""
        # Arrange
        user_id = "123"
        refresh_token, _ = jwt_service.create_refresh_token(user_id)

        # Act
        result = jwt_service.refresh_access_token(refresh_token)

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

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_refresh_access_token_invalid_refresh_token(self):
        """Test refresh with invalid refresh token."""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act
        result = jwt_service.refresh_access_token(invalid_token)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "invalid" in result["error"].lower()

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_refresh_access_token_expired_refresh_token(self):
        """Test refresh with expired refresh token."""
        # Arrange
        user_id = "123"

        # Create expired refresh token by mocking time
        with patch("src.common.services.jwt_service.datetime") as mock_datetime:
            # Set time to past for token creation
            past_time = datetime.utcnow() - timedelta(days=31)
            mock_datetime.utcnow.return_value = past_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            refresh_token, _ = jwt_service.create_refresh_token(user_id)

        # Act (with current time)
        result = jwt_service.refresh_access_token(refresh_token)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "expired" in result["error"].lower()

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_refresh_access_token_wrong_token_type(self):
        """Test refresh with access token instead of refresh token."""
        # Arrange
        user_id = "123"
        access_token, _, _ = jwt_service.create_access_token(user_id)

        # Act
        result = jwt_service.refresh_access_token(access_token)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "token type" in result["error"].lower()

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_refresh_token_rotation(self):
        """Test that refresh generates new refresh token."""
        # Arrange
        user_id = "123"
        original_refresh_token, _ = jwt_service.create_refresh_token(user_id)

        # Act
        result = jwt_service.refresh_access_token(original_refresh_token)

        # Assert
        assert result["success"] is True
        new_refresh_token = result["refresh_token"]

        # New refresh token should be different
        assert new_refresh_token != original_refresh_token

        # Both tokens should be valid (for now)
        payload1 = jwt_service.verify_token(original_refresh_token, "refresh")
        payload2 = jwt_service.verify_token(new_refresh_token, "refresh")
        assert payload1["sub"] == payload2["sub"]

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_refresh_token_blacklist_old_access_token(self):
        """Test that refresh blacklists the old access token if provided."""
        # Arrange
        user_id = "123"
        old_access_token, old_jti, old_expires = jwt_service.create_access_token(user_id)
        refresh_token, _ = jwt_service.create_refresh_token(user_id)

        # Act
        result = jwt_service.refresh_access_token(refresh_token, old_access_token)

        # Assert
        assert result["success"] is True

        # Old access token should be blacklisted
        assert jwt_service.is_token_blacklisted(old_jti) is True

    @patch("src.common.services.jwt_service.jwt_service._redis_client", mock_redis)
    def test_refresh_token_performance(self):
        """Test refresh token performance."""
        # Arrange
        user_id = "123"
        refresh_token, _ = jwt_service.create_refresh_token(user_id)

        # Act & Assert
        import time

        start_time = time.time()

        for _ in range(10):
            result = jwt_service.refresh_access_token(refresh_token)
            assert result["success"] is True
            # Use the new refresh token for next iteration
            refresh_token = result["refresh_token"]

        end_time = time.time()

        # Should complete 10 refreshes in under 1 second
        assert (end_time - start_time) < 1.0
