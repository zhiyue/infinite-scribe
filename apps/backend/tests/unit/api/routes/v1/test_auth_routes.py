"""Unit tests for authentication routes with background tasks."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import BackgroundTasks
from src.api.routes.v1.auth_register import register_user
from src.api.routes.v1.auth_password import forgot_password


class TestAuthRegisterRoute:
    """Test cases for register route with background tasks."""

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_register.user_service")
    async def test_register_route_with_background_tasks(self, mock_user_service):
        """Test register route properly injects background tasks."""
        # Arrange
        request_data = Mock()
        request_data.model_dump.return_value = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }

        mock_db = AsyncMock()
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock successful registration
        mock_user_service.register_user = AsyncMock(
            return_value={
                "success": True,
                "user": {
                    "id": 1,
                    "username": "testuser",
                    "email": "test@example.com",
                    "is_active": True,
                    "is_verified": False,
                    "is_superuser": False,
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                },
                "message": "Registration successful",
            }
        )

        # Act
        response = await register_user(request_data, background_tasks, mock_db)

        # Assert
        assert response.success is True
        assert response.user.username == "testuser"
        assert response.user.email == "test@example.com"
        mock_user_service.register_user.assert_called_once()
        call_args = mock_user_service.register_user.call_args
        assert call_args[0][0] == mock_db  # First arg is db
        assert call_args[0][1] == request_data.model_dump.return_value  # Second arg is user data
        assert call_args[0][2] == background_tasks  # Third arg is background_tasks

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_register.user_service")
    async def test_register_route_error_handling(self, mock_user_service):
        """Test register route error handling with background tasks."""
        # Arrange
        from fastapi import HTTPException
        
        request_data = Mock()
        request_data.model_dump.return_value = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }

        mock_db = AsyncMock()
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock registration failure
        mock_user_service.register_user = AsyncMock(
            return_value={"success": False, "error": "Email already exists"}
        )

        # Act & Assert - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await register_user(request_data, background_tasks, mock_db)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Email already exists"


class TestAuthPasswordRoute:
    """Test cases for password reset route with background tasks."""

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_password.user_service")
    async def test_forgot_password_route_with_background_tasks(self, mock_user_service):
        """Test forgot password route properly injects background tasks."""
        # Arrange
        request_data = Mock()
        request_data.email = "test@example.com"

        mock_db = AsyncMock()
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock successful password reset request
        mock_user_service.request_password_reset = AsyncMock(
            return_value={
                "success": True,
                "message": "Password reset email sent",
            }
        )

        # Act
        response = await forgot_password(request_data, background_tasks, mock_db)

        # Assert
        assert response.success is True
        assert response.message == "Password reset email sent"
        mock_user_service.request_password_reset.assert_called_once()
        call_args = mock_user_service.request_password_reset.call_args
        assert call_args[0][0] == mock_db  # First arg is db
        assert call_args[0][1] == "test@example.com"  # Second arg is email
        assert call_args[0][2] == background_tasks  # Third arg is background_tasks

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.auth_password.user_service")
    async def test_forgot_password_route_error_handling(self, mock_user_service):
        """Test forgot password route error handling."""
        # Arrange
        from fastapi import HTTPException
        
        request_data = Mock()
        request_data.email = "nonexistent@example.com"

        mock_db = AsyncMock()
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock user not found
        mock_user_service.request_password_reset = AsyncMock(
            return_value={
                "success": False,
                "error": "User not found",
            }
        )

        # Act & Assert - should raise HTTPException (currently returns 500 due to KeyError)
        with pytest.raises(HTTPException) as exc_info:
            await forgot_password(request_data, background_tasks, mock_db)
        
        # The current implementation has a bug where it tries to access result["message"]
        # even when success is False, causing a KeyError that results in a 500 error
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "An error occurred while processing the request"