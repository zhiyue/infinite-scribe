"""Unit tests for SSE token authentication endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status
from jose import jwt
from src.api.routes.v1.auth_sse_token import SSETokenResponse, create_sse_token, verify_sse_token
from src.models.user import User


class TestCreateSSEToken:
    """Test cases for SSE token creation endpoint."""

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_sse_token.settings")
    async def test_create_sse_token_success(self, mock_settings):
        """Test successful SSE token creation."""
        # Arrange
        mock_settings.auth.sse_token_expire_seconds = 60
        mock_settings.auth.jwt_secret_key = "test_secret_key_32_chars_minimum"
        mock_settings.auth.jwt_algorithm = "HS256"

        mock_user = Mock(spec=User)
        mock_user.id = 123

        # Act
        response = await create_sse_token(mock_user)

        # Assert
        assert isinstance(response, SSETokenResponse)
        assert response.sse_token is not None
        assert response.token_type == "sse"
        assert isinstance(response.expires_at, datetime)

        # Verify token expiration time (should be ~60 seconds from now)
        now = datetime.now(UTC)
        expected_expiry = now + timedelta(seconds=60)
        time_diff = abs((response.expires_at - expected_expiry).total_seconds())
        assert time_diff < 2  # Allow 2 second tolerance for test execution time

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_sse_token.settings")
    async def test_create_sse_token_with_valid_payload(self, mock_settings):
        """Test SSE token contains correct payload structure."""
        # Arrange
        mock_settings.auth.sse_token_expire_seconds = 60
        mock_settings.auth.jwt_secret_key = "test_secret_key_32_chars_minimum"
        mock_settings.auth.jwt_algorithm = "HS256"

        mock_user = Mock(spec=User)
        mock_user.id = 456

        # Act
        response = await create_sse_token(mock_user)

        # Decode the token to verify its contents
        decoded_payload = jwt.decode(
            response.sse_token,
            mock_settings.auth.jwt_secret_key,
            algorithms=[mock_settings.auth.jwt_algorithm],
        )

        # Assert
        assert decoded_payload["user_id"] == 456
        assert decoded_payload["token_type"] == "sse"
        assert "exp" in decoded_payload
        assert "iat" in decoded_payload



class TestVerifySSEToken:
    """Test cases for SSE token verification function."""

    @patch("src.api.routes.v1.auth_sse_token.settings")
    def test_verify_sse_token_success(self, mock_settings):
        """Test successful SSE token verification."""
        # Arrange
        mock_settings.auth.jwt_secret_key = "test_secret_key_32_chars_minimum"
        mock_settings.auth.jwt_algorithm = "HS256"

        # Create a valid SSE token
        payload = {
            "user_id": 123,
            "token_type": "sse",
            "exp": datetime.now(UTC) + timedelta(seconds=60),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, mock_settings.auth.jwt_secret_key, algorithm=mock_settings.auth.jwt_algorithm)

        # Act
        user_id = verify_sse_token(token)

        # Assert
        assert user_id == "123"

    @patch("src.api.routes.v1.auth_sse_token.settings")
    def test_verify_sse_token_invalid_token_type(self, mock_settings):
        """Test SSE token verification rejects non-SSE tokens."""
        # Arrange
        mock_settings.auth.jwt_secret_key = "test_secret_key_32_chars_minimum"
        mock_settings.auth.jwt_algorithm = "HS256"

        # Create a token with wrong type
        payload = {
            "user_id": 123,
            "token_type": "access",  # Wrong type
            "exp": datetime.now(UTC) + timedelta(seconds=60),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, mock_settings.auth.jwt_secret_key, algorithm=mock_settings.auth.jwt_algorithm)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_sse_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid token type"

    @patch("src.api.routes.v1.auth_sse_token.settings")
    def test_verify_sse_token_missing_user_id(self, mock_settings):
        """Test SSE token verification rejects tokens without user_id."""
        # Arrange
        mock_settings.auth.jwt_secret_key = "test_secret_key_32_chars_minimum"
        mock_settings.auth.jwt_algorithm = "HS256"

        # Create a token without user_id
        payload = {
            "token_type": "sse",
            "exp": datetime.now(UTC) + timedelta(seconds=60),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, mock_settings.auth.jwt_secret_key, algorithm=mock_settings.auth.jwt_algorithm)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_sse_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid token payload"

    @patch("src.api.routes.v1.auth_sse_token.settings")
    def test_verify_sse_token_expired(self, mock_settings):
        """Test SSE token verification handles expired tokens."""
        # Arrange
        mock_settings.auth.jwt_secret_key = "test_secret_key_32_chars_minimum"
        mock_settings.auth.jwt_algorithm = "HS256"

        # Create an expired token
        payload = {
            "user_id": 123,
            "token_type": "sse",
            "exp": datetime.now(UTC) - timedelta(seconds=1),  # Expired
            "iat": datetime.now(UTC) - timedelta(seconds=61),
        }
        token = jwt.encode(payload, mock_settings.auth.jwt_secret_key, algorithm=mock_settings.auth.jwt_algorithm)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_sse_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "SSE token has expired"

    @patch("src.api.routes.v1.auth_sse_token.settings")
    @patch("src.api.routes.v1.auth_sse_token.logger")
    def test_verify_sse_token_invalid_signature(self, mock_logger, mock_settings):
        """Test SSE token verification handles invalid signature."""
        # Arrange
        mock_settings.auth.jwt_secret_key = "test_secret_key_32_chars_minimum"
        mock_settings.auth.jwt_algorithm = "HS256"

        # Create a token with wrong secret
        payload = {
            "user_id": 123,
            "token_type": "sse",
            "exp": datetime.now(UTC) + timedelta(seconds=60),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(payload, "wrong_secret", algorithm=mock_settings.auth.jwt_algorithm)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_sse_token(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid token"

        # Verify warning is logged
        mock_logger.warning.assert_called_once()
        log_args = mock_logger.warning.call_args[0]
        assert "Invalid SSE token" in log_args[0]

    def test_verify_sse_token_malformed_token(self):
        """Test SSE token verification handles malformed tokens."""
        # Arrange
        malformed_token = "not.a.valid.jwt.token"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            verify_sse_token(malformed_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid token"

    def test_verify_sse_token_empty_token(self):
        """Test SSE token verification handles empty/None tokens."""
        # Act & Assert - Test empty string
        with pytest.raises(HTTPException) as exc_info:
            verify_sse_token("")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Token is required"

        # Act & Assert - Test whitespace only
        with pytest.raises(HTTPException) as exc_info:
            verify_sse_token("   ")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Token is required"


class TestSSETokenModels:
    """Test cases for SSE token Pydantic models."""

    def test_sse_token_response_model(self):
        """Test SSETokenResponse model validation."""
        # Arrange
        expires_at = datetime.now(UTC) + timedelta(seconds=60)

        # Act
        response = SSETokenResponse(sse_token="test.token.here", expires_at=expires_at)

        # Assert
        assert response.sse_token == "test.token.here"
        assert response.expires_at == expires_at
        assert response.token_type == "sse"
