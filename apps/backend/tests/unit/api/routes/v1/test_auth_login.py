"""Unit tests for authentication login/logout endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.routes.v1.auth_login import login_user, logout_user, refresh_access_token
from src.api.schemas import RefreshTokenRequest, UserLoginRequest
from src.models.user import User


class TestAuthLogin:
    """Test cases for authentication login endpoints."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request object."""
        mock_req = Mock()
        mock_req.client.host = "192.168.1.1"
        mock_req.headers = {"user-agent": "Mozilla/5.0"}
        mock_req.state = Mock()
        return mock_req

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def mock_user(self):
        """Create mock user object."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.is_active = True
        user.is_verified = True
        user.to_dict.return_value = {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True,
            "is_verified": True,
            "is_superuser": False,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        return user

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_login_user_success(self, mock_user_service, mock_request, mock_db, mock_user):
        """Test successful user login."""
        # Arrange
        login_request = UserLoginRequest(email="test@example.com", password="password123")

        mock_user_service.login = AsyncMock(
            return_value={
                "success": True,
                "access_token": "access_token_123",
                "refresh_token": "refresh_token_123",
                "user": mock_user.to_dict(),
            }
        )

        # Act
        result = await login_user(login_request, mock_request, mock_db)

        # Assert
        assert result.success is True
        assert result.access_token == "access_token_123"
        assert result.refresh_token == "refresh_token_123"
        assert result.user.email == "test@example.com"

        mock_user_service.login.assert_called_once_with(
            mock_db, "test@example.com", "password123", "192.168.1.1", "Mozilla/5.0"
        )

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_login_user_invalid_credentials(self, mock_user_service, mock_request, mock_db):
        """Test login with invalid credentials."""
        # Arrange
        login_request = UserLoginRequest(email="test@example.com", password="wrong_password")

        mock_user_service.login = AsyncMock(return_value={"success": False, "error": "Invalid credentials"})

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_request, mock_request, mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail["message"] == "Invalid credentials"

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_login_user_account_locked(self, mock_user_service, mock_request, mock_db):
        """Test login with locked account."""
        # Arrange
        login_request = UserLoginRequest(email="test@example.com", password="password123")

        mock_user_service.login = AsyncMock(
            return_value={
                "success": False,
                "error": "Account is locked until 2024-01-01",
                "locked_until": "2024-01-01T00:00:00",
            }
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_request, mock_request, mock_db)

        assert exc_info.value.status_code == status.HTTP_423_LOCKED
        assert "locked" in exc_info.value.detail["message"].lower()
        assert exc_info.value.detail["locked_until"] == "2024-01-01T00:00:00"

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_login_user_email_not_verified(self, mock_user_service, mock_request, mock_db):
        """Test login with unverified email."""
        # Arrange
        login_request = UserLoginRequest(email="test@example.com", password="password123")

        mock_user_service.login = AsyncMock(
            return_value={"success": False, "error": "Please verify your email before logging in"}
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_request, mock_request, mock_db)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "verify" in exc_info.value.detail["message"].lower()

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_login_user_with_remaining_attempts(self, mock_user_service, mock_request, mock_db):
        """Test login failure with remaining attempts info."""
        # Arrange
        login_request = UserLoginRequest(email="test@example.com", password="wrong_password")

        mock_user_service.login = AsyncMock(
            return_value={
                "success": False,
                "error": "Invalid credentials. 2 attempt(s) remaining.",
                "remaining_attempts": 2,
            }
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_request, mock_request, mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail["remaining_attempts"] == 2

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_login_user_exception(self, mock_user_service, mock_request, mock_db):
        """Test login with unexpected exception."""
        # Arrange
        login_request = UserLoginRequest(email="test@example.com", password="password123")

        mock_user_service.login = AsyncMock(side_effect=Exception("Database error"))

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await login_user(login_request, mock_request, mock_db)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "An error occurred during login"

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_logout_user_success(self, mock_user_service, mock_request, mock_db, mock_user):
        """Test successful user logout."""
        # Arrange
        mock_request.state.jti = "jti_123"
        mock_user_service.logout = AsyncMock(return_value={"success": True})

        # Act
        result = await logout_user(mock_request, mock_db, mock_user)

        # Assert
        assert result.success is True
        assert result.message == "Logged out successfully"
        mock_user_service.logout.assert_called_once_with(mock_db, "jti_123")

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_logout_user_no_jti(self, mock_user_service, mock_request, mock_db, mock_user):
        """Test logout when no JTI in request."""
        # Arrange
        mock_request.state.jti = None

        # Act
        result = await logout_user(mock_request, mock_db, mock_user)

        # Assert
        assert result.success is True
        assert result.message == "Logged out successfully"
        mock_user_service.logout.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_logout_user_failure(self, mock_user_service, mock_request, mock_db, mock_user):
        """Test logout when service returns failure."""
        # Arrange
        mock_request.state.jti = "jti_123"
        mock_user_service.logout = AsyncMock(return_value={"success": False, "error": "Logout failed"})

        # Act
        result = await logout_user(mock_request, mock_db, mock_user)

        # Assert
        # Still returns success for security
        assert result.success is True
        assert result.message == "Logged out successfully"

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_login.user_service")
    async def test_logout_user_exception(self, mock_user_service, mock_request, mock_db, mock_user):
        """Test logout with exception."""
        # Arrange
        mock_request.state.jti = "jti_123"
        mock_user_service.logout = AsyncMock(side_effect=Exception("Database error"))

        # Act
        result = await logout_user(mock_request, mock_db, mock_user)

        # Assert
        # Still returns success for security
        assert result.success is True
        assert result.message == "Logged out successfully"

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service")
    async def test_refresh_token_success(self, mock_jwt_service, mock_request, mock_db):
        """Test successful token refresh."""
        # Arrange
        refresh_request = RefreshTokenRequest(refresh_token="refresh_token_123")
        mock_request.headers = {"Authorization": "Bearer old_access_token"}

        mock_jwt_service.extract_token_from_header.return_value = "old_access_token"
        mock_jwt_service.refresh_access_token = AsyncMock(
            return_value={
                "success": True,
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            }
        )

        # Act
        result = await refresh_access_token(refresh_request, mock_request, mock_db)

        # Assert
        assert result.success is True
        assert result.access_token == "new_access_token"
        assert result.refresh_token == "new_refresh_token"

        mock_jwt_service.extract_token_from_header.assert_called_once_with("Bearer old_access_token")
        mock_jwt_service.refresh_access_token.assert_called_once_with(mock_db, "refresh_token_123", "old_access_token")

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service")
    async def test_refresh_token_no_auth_header(self, mock_jwt_service, mock_request, mock_db):
        """Test token refresh without authorization header."""
        # Arrange
        refresh_request = RefreshTokenRequest(refresh_token="refresh_token_123")
        mock_request.headers = {}

        mock_jwt_service.refresh_access_token = AsyncMock(
            return_value={
                "success": True,
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            }
        )

        # Act
        result = await refresh_access_token(refresh_request, mock_request, mock_db)

        # Assert
        assert result.success is True
        mock_jwt_service.extract_token_from_header.assert_not_called()
        mock_jwt_service.refresh_access_token.assert_called_once_with(mock_db, "refresh_token_123", None)

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service")
    async def test_refresh_token_failure(self, mock_jwt_service, mock_request, mock_db):
        """Test token refresh failure."""
        # Arrange
        refresh_request = RefreshTokenRequest(refresh_token="invalid_token")
        mock_request.headers = {}

        mock_jwt_service.refresh_access_token = AsyncMock(
            return_value={"success": False, "error": "Invalid refresh token"}
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(refresh_request, mock_request, mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid refresh token"

    @pytest.mark.asyncio
    @patch("src.common.services.jwt_service.jwt_service")
    async def test_refresh_token_exception(self, mock_jwt_service, mock_request, mock_db):
        """Test token refresh with exception."""
        # Arrange
        refresh_request = RefreshTokenRequest(refresh_token="refresh_token_123")
        mock_request.headers = {}

        mock_jwt_service.refresh_access_token = AsyncMock(side_effect=Exception("Service error"))

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await refresh_access_token(refresh_request, mock_request, mock_db)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "An error occurred during token refresh"
