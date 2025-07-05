"""Unit tests for authentication middleware."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request
from jose import JWTError

from src.middleware.auth import get_current_user, require_auth, require_admin


class TestAuthMiddleware:
    """Test cases for authentication middleware."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.headers = {}
        return request
    
    @pytest.fixture
    def mock_jwt_service(self):
        """Mock JWT service."""
        with patch('src.middleware.auth.jwt_service') as mock:
            mock.extract_token_from_header.return_value = "valid_token"
            mock.verify_token.return_value = {
                "sub": "123",
                "email": "test@example.com",
                "username": "testuser",
                "jti": "jti123"
            }
            yield mock
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch('src.middleware.auth.get_db') as mock:
            session = AsyncMock()
            mock.return_value.__aenter__.return_value = session
            mock.return_value.__aexit__.return_value = None
            yield session
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock()
        user.id = 123
        user.email = "test@example.com"
        user.username = "testuser"
        user.is_active = True
        user.is_verified = True
        user.is_superuser = False
        user.to_dict.return_value = {
            "id": 123,
            "email": "test@example.com",
            "username": "testuser"
        }
        return user
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_request, mock_jwt_service, mock_db_session, mock_user):
        """Test getting current user with valid token."""
        # Arrange
        mock_request.headers = {"Authorization": "Bearer valid_token"}
        mock_db_session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=mock_user))
        )
        
        # Act
        result = await get_current_user(mock_request, mock_db_session)
        
        # Assert
        assert result == mock_user
        mock_jwt_service.extract_token_from_header.assert_called_once()
        mock_jwt_service.verify_token.assert_called_once_with("valid_token", "access")
    
    @pytest.mark.asyncio
    async def test_get_current_user_no_authorization_header(self, mock_request):
        """Test get current user without authorization header."""
        # Arrange
        mock_request.headers = {}
        
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)
        
        # Assert
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_format(self, mock_request, mock_jwt_service):
        """Test get current user with invalid token format."""
        # Arrange
        mock_request.headers = {"Authorization": "InvalidFormat"}
        mock_jwt_service.extract_token_from_header.return_value = None
        
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)
        
        # Assert
        assert exc_info.value.status_code == 401
        assert "Invalid authentication" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, mock_request, mock_jwt_service):
        """Test get current user with expired token."""
        # Arrange
        mock_request.headers = {"Authorization": "Bearer expired_token"}
        mock_jwt_service.verify_token.side_effect = JWTError("Token expired")
        
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)
        
        # Assert
        assert exc_info.value.status_code == 401
        assert "Token expired" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, mock_request, mock_jwt_service, mock_db_session):
        """Test get current user when user not found in database."""
        # Arrange
        mock_request.headers = {"Authorization": "Bearer valid_token"}
        mock_db_session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None))
        )
        
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_db_session)
        
        # Assert
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, mock_request, mock_jwt_service, mock_db_session, mock_user):
        """Test get current user with inactive user."""
        # Arrange
        mock_request.headers = {"Authorization": "Bearer valid_token"}
        mock_user.is_active = False
        mock_db_session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=mock_user))
        )
        
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_db_session)
        
        # Assert
        assert exc_info.value.status_code == 403
        assert "User is inactive" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_auth_success(self, mock_user):
        """Test require_auth with authenticated user."""
        # Act
        result = await require_auth(mock_user)
        
        # Assert
        assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_auth_unverified_user(self, mock_user):
        """Test require_auth with unverified user."""
        # Arrange
        mock_user.is_verified = False
        
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(mock_user)
        
        # Assert
        assert exc_info.value.status_code == 403
        assert "Email not verified" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_require_admin_success(self, mock_user):
        """Test require_admin with admin user."""
        # Arrange
        mock_user.is_superuser = True
        
        # Act
        result = await require_admin(mock_user)
        
        # Assert
        assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_admin_non_admin_user(self, mock_user):
        """Test require_admin with non-admin user."""
        # Arrange
        mock_user.is_superuser = False
        
        # Act
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_user)
        
        # Assert
        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)