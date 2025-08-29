"""Unit tests for auth register endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException, status
from src.api.routes.v1.auth_register import (
    register_user,
    resend_verification_email,
    verify_email,
)
from src.api.schemas import (
    MessageResponse,
    RegisterResponse,
    ResendVerificationRequest,
    UserRegisterRequest,
)


class TestAuthRegisterEndpoints:
    """Test cases for auth register endpoints."""

    @pytest.mark.asyncio
    async def test_register_user_success(self):
        """Test user registration endpoint with successful registration."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = UserRegisterRequest(
            email="test@example.com",
            password="StrongPassword123!",
            username="testuser",
            first_name="Test",
            last_name="User",
        )

        mock_user = {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.register_user = AsyncMock(
                return_value={
                    "success": True,
                    "user": mock_user,
                    "message": "Registration successful. Please check your email to verify your account.",
                }
            )

            result = await register_user(request, mock_background_tasks, mock_db)

            assert isinstance(result, RegisterResponse)
            assert result.success is True
            assert result.user.email == "test@example.com"
            assert result.user.username == "testuser"
            assert "Registration successful" in result.message

            # Verify service was called with correct data
            mock_user_service.register_user.assert_called_once()
            call_args = mock_user_service.register_user.call_args
            assert call_args[0][0] == mock_db  # First arg is db
            assert call_args[0][1]["email"] == "test@example.com"  # Second arg is user_data
            assert call_args[0][2] == mock_background_tasks  # Third arg is background_tasks

    @pytest.mark.asyncio
    async def test_register_user_service_failure(self):
        """Test user registration when service returns failure."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = UserRegisterRequest(
            email="existing@example.com",
            password="StrongPassword123!",
            username="existinguser",
            first_name="Test",
            last_name="User",
        )

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.register_user = AsyncMock(
                return_value={"success": False, "error": "Email already registered"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await register_user(request, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert exc_info.value.detail == "Email already registered"

    @pytest.mark.asyncio
    async def test_register_user_service_exception(self):
        """Test user registration when service raises exception."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = UserRegisterRequest(
            email="test@example.com",
            password="StrongPassword123!",
            username="testuser",
            first_name="Test",
            last_name="User",
        )

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.register_user = AsyncMock(side_effect=Exception("Database error"))

            with pytest.raises(HTTPException) as exc_info:
                await register_user(request, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert exc_info.value.detail == "An error occurred during registration"

    @pytest.mark.asyncio
    async def test_verify_email_success(self):
        """Test email verification endpoint with successful verification."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        token = "valid_verification_token"

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.verify_email = AsyncMock(
                return_value={"success": True, "message": "Email verified successfully"}
            )

            result = await verify_email(token, mock_background_tasks, mock_db)

            assert isinstance(result, MessageResponse)
            assert result.success is True
            assert result.message == "Email verified successfully"
            mock_user_service.verify_email.assert_called_once_with(mock_db, token, mock_background_tasks)

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self):
        """Test email verification with invalid token."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        token = "invalid_token"

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.verify_email = AsyncMock(
                return_value={"success": False, "error": "Invalid verification token"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await verify_email(token, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Invalid verification token"

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(self):
        """Test email verification with expired token."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        token = "expired_token"

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.verify_email = AsyncMock(
                return_value={"success": False, "error": "Verification token has expired"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await verify_email(token, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_410_GONE
            assert exc_info.value.detail == "Verification token has expired"

    @pytest.mark.asyncio
    async def test_verify_email_generic_error(self):
        """Test email verification with generic error."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        token = "some_token"

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.verify_email = AsyncMock(return_value={"success": False, "error": "Some other error"})

            with pytest.raises(HTTPException) as exc_info:
                await verify_email(token, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert exc_info.value.detail == "Some other error"

    @pytest.mark.asyncio
    async def test_verify_email_service_exception(self):
        """Test email verification when service raises exception."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        token = "valid_token"

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.verify_email = AsyncMock(side_effect=Exception("Service error"))

            with pytest.raises(HTTPException) as exc_info:
                await verify_email(token, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert exc_info.value.detail == "An error occurred during email verification"

    @pytest.mark.asyncio
    async def test_resend_verification_email_success(self):
        """Test resend verification email endpoint."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = ResendVerificationRequest(email="test@example.com")

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.resend_verification_email = AsyncMock()

            result = await resend_verification_email(request, mock_background_tasks, mock_db)

            assert isinstance(result, MessageResponse)
            assert result.success is True
            assert "verification email has been sent" in result.message
            mock_user_service.resend_verification_email.assert_called_once_with(
                mock_db, request.email, mock_background_tasks
            )

    @pytest.mark.asyncio
    async def test_resend_verification_email_exception(self):
        """Test resend verification email when exception occurs."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = ResendVerificationRequest(email="test@example.com")

        with patch("src.api.routes.v1.auth_register.user_service") as mock_user_service:
            mock_user_service.resend_verification_email = AsyncMock(
                side_effect=Exception("Email service error")
            )

            with pytest.raises(HTTPException) as exc_info:
                await resend_verification_email(request, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert exc_info.value.detail == "An error occurred while sending verification email"
