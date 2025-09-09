"""Unit tests for JWT refresh token functionality."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from src.common.services.user.auth_service import auth_service


class TestJWTRefreshToken:
    """Test cases for JWT refresh token functionality."""

    @patch("src.common.services.user.auth_service.auth_service._redis_client")
    def test_create_refresh_token_basic(self, mock_redis_client):
        """Test basic refresh token creation."""
        # Arrange
        user_id = "123"
        mock_redis_client.setex.return_value = True
        mock_redis_client.get.return_value = None

        # Act
        token, expires_at = auth_service.create_refresh_token(user_id)

        # Assert
        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

    @patch("src.common.services.user.auth_service.auth_service._redis_client")
    def test_create_refresh_token_user_id_validation(self, mock_redis_client):
        """Test refresh token creation with invalid user ID."""
        # Arrange
        mock_redis_client.setex.return_value = True

        # Act & Assert
        with pytest.raises(ValueError):
            auth_service.create_refresh_token("")

        with pytest.raises(ValueError):
            auth_service.create_refresh_token(None)

    @patch("src.common.services.user.auth_service.auth_service._redis_client")
    def test_verify_refresh_token_valid(self, mock_redis_client):
        """Test verifying a valid refresh token."""
        # Arrange
        user_id = "123"
        mock_redis_client.setex.return_value = True
        mock_redis_client.get.return_value = user_id  # Token exists in Redis

        token, _ = auth_service.create_refresh_token(user_id)

        # Act
        result = auth_service.verify_refresh_token(token)

        # Assert
        assert result == user_id
        mock_redis_client.get.assert_called()

    @patch("src.common.services.user.auth_service.auth_service._redis_client")
    def test_verify_refresh_token_invalid(self, mock_redis_client):
        """Test verifying an invalid refresh token."""
        # Arrange
        mock_redis_client.get.return_value = None  # Token doesn't exist
        invalid_token = "invalid.token.here"

        # Act
        result = auth_service.verify_refresh_token(invalid_token)

        # Assert
        assert result is None

    @patch("src.common.services.user.auth_service.auth_service._redis_client")
    def test_revoke_refresh_token(self, mock_redis_client):
        """Test revoking a refresh token."""
        # Arrange
        token = "sample.refresh.token"
        mock_redis_client.delete.return_value = 1

        # Act
        result = auth_service.revoke_refresh_token(token)

        # Assert
        assert result is True
        mock_redis_client.delete.assert_called()

    @patch("src.common.services.user.auth_service.auth_service._redis_client")
    def test_revoke_refresh_token_not_found(self, mock_redis_client):
        """Test revoking a non-existent refresh token."""
        # Arrange
        token = "nonexistent.token"
        mock_redis_client.delete.return_value = 0

        # Act
        result = auth_service.revoke_refresh_token(token)

        # Assert
        assert result is False
