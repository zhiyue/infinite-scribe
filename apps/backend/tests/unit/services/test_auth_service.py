"""Unit tests for authentication service functionality."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from src.api.routes.v1.auth_login import login_user
from src.api.schemas import UserLoginRequest
from src.common.settings import settings
from src.utils import utc_now


class TestAccountLockout:
    """Test account lockout functionality."""

    @pytest.mark.asyncio
    async def test_account_lockout_increments_attempts(self):
        """Test that failed login attempts increment correctly."""
        # Mock setup
        mock_request = Mock()
        mock_request.client = Mock(host="127.0.0.1")
        mock_request.headers = {"user-agent": "Test Agent"}

        mock_db = AsyncMock()
        login_request = UserLoginRequest(email="test@example.com", password="wrong_password")

        # Mock user_service.login to return failure with remaining attempts
        with patch("src.api.routes.v1.auth_login.user_service") as mock_user_service:
            mock_user_service.login = AsyncMock(
                return_value={
                    "success": False,
                    "error": "Invalid credentials. 4 attempts remaining.",
                    "remaining_attempts": 4,
                }
            )

            # Act - Call login_user and expect HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await login_user(login_request, mock_request, mock_db)

            # Assert - Verify login_user was called through user_service.login
            mock_user_service.login.assert_called_once_with(
                mock_db, "test@example.com", "wrong_password", "127.0.0.1", "Test Agent"
            )

            # Assert - Verify the exception details
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "remaining_attempts" in exc_info.value.detail
            assert exc_info.value.detail["remaining_attempts"] == 4

    @pytest.mark.asyncio
    async def test_account_lockout_after_max_attempts(self):
        """Test that account is locked after maximum failed attempts."""
        # Mock setup
        mock_request = Mock()
        mock_request.client = Mock(host="127.0.0.1")
        mock_request.headers = {"user-agent": "Test Agent"}

        mock_db = AsyncMock()
        login_request = UserLoginRequest(email="test@example.com", password="wrong_password")

        # Calculate expected unlock time
        expected_unlock_time = utc_now() + timedelta(minutes=settings.auth.account_lockout_duration_minutes)

        # Mock user_service.login to return account locked
        with patch("src.api.routes.v1.auth_login.user_service") as mock_user_service:
            mock_user_service.login = AsyncMock(
                return_value={
                    "success": False,
                    "error": "Account is locked due to too many failed login attempts.",
                    "locked_until": expected_unlock_time.isoformat(),
                }
            )

            # Act - Call login_user and expect HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await login_user(login_request, mock_request, mock_db)

            # Assert - Verify login_user was called
            mock_user_service.login.assert_called_once_with(
                mock_db, "test@example.com", "wrong_password", "127.0.0.1", "Test Agent"
            )

            # Assert - Verify the exception details
            assert exc_info.value.status_code == status.HTTP_423_LOCKED
            assert "locked_until" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_successful_login_resets_attempts(self):
        """Test that successful login resets failed attempts counter."""
        # Mock setup
        mock_request = Mock()
        mock_request.client = Mock(host="127.0.0.1")
        mock_request.headers = {"user-agent": "Test Agent"}

        mock_db = AsyncMock()
        login_request = UserLoginRequest(email="test@example.com", password="correct_password")

        # Mock successful login
        with patch("src.api.routes.v1.auth_login.user_service") as mock_user_service:
            mock_user_service.login = AsyncMock(
                return_value={
                    "success": True,
                    "user": {
                        "id": "user123",
                        "email": "test@example.com",
                        "username": "testuser",
                        "is_active": True,
                        "is_email_verified": True,
                        "role": "user",
                        "created_at": utc_now().isoformat(),
                        "updated_at": utc_now().isoformat(),
                    },
                    "access_token": "access_token_here",
                    "refresh_token": "refresh_token_here",
                }
            )

            # Act - Call login_user
            result = await login_user(login_request, mock_request, mock_db)

            # Assert - Verify login_user was called
            mock_user_service.login.assert_called_once_with(
                mock_db, "test@example.com", "correct_password", "127.0.0.1", "Test Agent"
            )

            # Assert - Verify successful response
            assert result.success is True
            assert result.access_token == "access_token_here"
            assert result.refresh_token == "refresh_token_here"
            assert result.user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_login_with_unverified_email(self):
        """Test login attempt with unverified email."""
        # Mock setup
        mock_request = Mock()
        mock_request.client = Mock(host="127.0.0.1")
        mock_request.headers = {"user-agent": "Test Agent"}

        mock_db = AsyncMock()
        login_request = UserLoginRequest(email="test@example.com", password="password")

        # Mock user_service.login to return unverified email error
        with patch("src.api.routes.v1.auth_login.user_service") as mock_user_service:
            mock_user_service.login = AsyncMock(
                return_value={"success": False, "error": "Please verify your email before logging in."}
            )

            # Act - Call login_user and expect HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await login_user(login_request, mock_request, mock_db)

            # Assert - Verify login_user was called
            mock_user_service.login.assert_called_once_with(
                mock_db, "test@example.com", "password", "127.0.0.1", "Test Agent"
            )

            # Assert - Verify the exception details
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "verify" in exc_info.value.detail["message"].lower()
