"""Unit tests for auth password endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException, status
from src.api.routes.v1.auth_password import (
    change_password,
    forgot_password,
    reset_password,
    validate_password_strength,
)
from src.api.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    PasswordStrengthResponse,
    ResetPasswordRequest,
)
from src.models.user import User


class TestAuthPasswordEndpoints:
    """Test cases for auth password endpoints."""

    @pytest.mark.asyncio
    async def test_forgot_password_success(self):
        """Test forgot password endpoint with successful request."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = ForgotPasswordRequest(email="test@example.com")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.request_password_reset = AsyncMock(return_value={"message": "Password reset email sent"})

            result = await forgot_password(request, mock_background_tasks, mock_db)

            assert isinstance(result, MessageResponse)
            assert result.success is True
            assert result.message == "Password reset email sent"
            mock_user_service.request_password_reset.assert_called_once_with(
                mock_db, "test@example.com", mock_background_tasks
            )

    @pytest.mark.asyncio
    async def test_forgot_password_service_exception(self):
        """Test forgot password endpoint when service raises exception."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = ForgotPasswordRequest(email="test@example.com")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.request_password_reset = AsyncMock(side_effect=Exception("Service error"))

            with pytest.raises(HTTPException) as exc_info:
                await forgot_password(request, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert exc_info.value.detail == "An error occurred while processing the request"

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Test reset password endpoint with successful request."""
        mock_db = AsyncMock()
        request = ResetPasswordRequest(token="valid_token", new_password="NewPassword123!")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.reset_password = AsyncMock(
                return_value={"success": True, "message": "Password reset successful"}
            )

            result = await reset_password(request, mock_db)

            assert isinstance(result, MessageResponse)
            assert result.success is True
            assert result.message == "Password has been reset successfully"
            mock_user_service.reset_password.assert_called_once_with(mock_db, "valid_token", "NewPassword123!")

    @pytest.mark.asyncio
    async def test_reset_password_service_failure(self):
        """Test reset password endpoint when service returns failure."""
        mock_db = AsyncMock()
        request = ResetPasswordRequest(token="invalid_token", new_password="NewPassword123!")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.reset_password = AsyncMock(
                return_value={"success": False, "error": "Invalid or expired token"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await reset_password(request, mock_db)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert exc_info.value.detail == "Invalid or expired token"

    @pytest.mark.asyncio
    async def test_reset_password_service_exception(self):
        """Test reset password endpoint when service raises exception."""
        mock_db = AsyncMock()
        request = ResetPasswordRequest(token="valid_token", new_password="NewPassword123!")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.reset_password = AsyncMock(side_effect=Exception("Service error"))

            with pytest.raises(HTTPException) as exc_info:
                await reset_password(request, mock_db)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert exc_info.value.detail == "An error occurred during password reset"

    @pytest.mark.asyncio
    async def test_change_password_weak_password(self):
        """Test change password with weak password."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.password_hash = "current_hash"
        request = ChangePasswordRequest(current_password="currentpass", new_password="weakpass")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.change_password = AsyncMock(
                return_value={"success": False, "error": "Too short; No uppercase"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, mock_background_tasks, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert exc_info.value.detail == "Too short; No uppercase"

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current_password(self):
        """Test change password with incorrect current password."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.password_hash = "current_hash"
        request = ChangePasswordRequest(current_password="wrong_password", new_password="NewPassword123!")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.change_password = AsyncMock(
                return_value={"success": False, "error": "Current password is incorrect"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, mock_background_tasks, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert exc_info.value.detail == "Current password is incorrect"

    @pytest.mark.asyncio
    async def test_change_password_same_as_current(self):
        """Test change password when new password is same as current."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.password_hash = "current_hash"
        request = ChangePasswordRequest(current_password="currentpass", new_password="currentpass")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.change_password = AsyncMock(
                return_value={"success": False, "error": "New password must be different from current password"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, mock_background_tasks, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert exc_info.value.detail == "New password must be different from current password"

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """Test change password with successful change."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.password_hash = "current_hash"
        request = ChangePasswordRequest(current_password="currentpass", new_password="NewPassword123!")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.change_password = AsyncMock(
                return_value={"success": True, "message": "Password changed successfully"}
            )

            result = await change_password(request, mock_background_tasks, mock_db, mock_user)

            assert isinstance(result, MessageResponse)
            assert result.success is True
            assert result.message == "Password has been changed successfully"
            mock_user_service.change_password.assert_called_once_with(
                mock_db, 1, "currentpass", "NewPassword123!", mock_background_tasks
            )

    @pytest.mark.asyncio
    async def test_change_password_service_exception(self):
        """Test change password when service raises exception."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.password_hash = "current_hash"
        request = ChangePasswordRequest(current_password="currentpass", new_password="NewPassword123!")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.change_password = AsyncMock(side_effect=Exception("Service error"))

            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, mock_background_tasks, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert exc_info.value.detail == "An error occurred during password change"

    @pytest.mark.asyncio
    async def test_validate_password_strength_success(self):
        """Test validate password strength endpoint with successful validation."""
        password = "StrongPassword123!"

        with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
            mock_password_service.validate_password_strength.return_value = {
                "is_valid": True,
                "score": 4,
                "errors": [],
                "suggestions": [],
            }

            result = await validate_password_strength(password)

            assert isinstance(result, PasswordStrengthResponse)
            assert result.is_valid is True
            assert result.score == 4
            assert result.errors == []
            assert result.suggestions == []
            mock_password_service.validate_password_strength.assert_called_once_with(password)

    @pytest.mark.asyncio
    async def test_validate_password_strength_weak(self):
        """Test validate password strength endpoint with weak password."""
        password = "weak"

        with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
            mock_password_service.validate_password_strength.return_value = {
                "is_valid": False,
                "score": 1,
                "errors": ["Too short", "No uppercase"],
                "suggestions": ["Add uppercase letters", "Increase length"],
            }

            result = await validate_password_strength(password)

            assert isinstance(result, PasswordStrengthResponse)
            assert result.is_valid is False
            assert result.score == 1
            assert result.errors == ["Too short", "No uppercase"]
            assert result.suggestions == ["Add uppercase letters", "Increase length"]

    @pytest.mark.asyncio
    async def test_validate_password_strength_service_exception(self):
        """Test validate password strength when service raises exception."""
        password = "TestPassword123!"

        with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
            mock_password_service.validate_password_strength.side_effect = Exception("Service error")

            result = await validate_password_strength(password)

            assert isinstance(result, PasswordStrengthResponse)
            assert result.is_valid is False
            assert result.score == 0
            assert result.errors == ["Unable to validate password"]
            assert result.suggestions == ["Please try again"]
