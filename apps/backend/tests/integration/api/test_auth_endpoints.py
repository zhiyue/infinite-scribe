"""Integration tests for authentication endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.database import get_db
from src.models.user import User
from src.models.email_verification import EmailVerification
from tests.unit.test_mocks import mock_redis, mock_email_service


@pytest.fixture
def client_with_mocks(test_session):
    """Create test client with mocked dependencies."""
    def override_get_db():
        return test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with patch('src.common.services.jwt_service.jwt_service._redis_client', mock_redis):
        with patch('src.common.services.email_service.EmailService') as mock_email_cls:
            mock_email_cls.return_value = mock_email_service
            with TestClient(app) as test_client:
                yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()
    mock_redis.clear()
    mock_email_service.clear()


class TestAuthRegister:
    """Test cases for user registration endpoint."""
    
    def test_register_success(self, client_with_mocks):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # Act
        response = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "user" in data
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"
        assert "password" not in data["user"]  # Password should not be returned
        assert "message" in data
        assert "verify" in data["message"].lower() and "email" in data["message"].lower()
    
    def test_register_weak_password(self, client_with_mocks):
        """Test registration with weak password."""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak"
        }
        
        # Act
        response = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 422  # Validation error from pydantic
        data = response.json()
        assert "detail" in data
    
    def test_register_duplicate_email(self, client_with_mocks):
        """Test registration with duplicate email."""
        # Arrange
        user_data = {
            "username": "testuser1",
            "email": "duplicate@example.com",
            "password": "SecurePassword123!"
        }
        
        # Act - Register first user
        response1 = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Act - Try to register with same email
        user_data["username"] = "testuser2"
        response2 = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        
        # Assert
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()
    
    def test_register_duplicate_username(self, client_with_mocks):
        """Test registration with duplicate username."""
        # Arrange
        user_data = {
            "username": "duplicateuser",
            "email": "test1@example.com",
            "password": "SecurePassword123!"
        }
        
        # Act - Register first user
        response1 = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201
        
        # Act - Try to register with same username
        user_data["email"] = "test2@example.com"
        response2 = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        
        # Assert
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()
    
    def test_register_invalid_email(self, client_with_mocks):
        """Test registration with invalid email format."""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "SecurePassword123!"
        }
        
        # Act
        response = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_register_missing_required_fields(self, client_with_mocks):
        """Test registration with missing required fields."""
        # Arrange
        user_data = {
            "username": "testuser"
            # Missing email and password
        }
        
        # Act
        response = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        
        # Assert
        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Test cases for user login endpoint."""
    
    def test_login_success(self, client_with_mocks):
        """Test successful user login."""
        # Arrange - First register a user
        user_data = {
            "username": "logintest",
            "email": "login@example.com",
            "password": "SecurePassword123!"
        }
        register_response = client_with_mocks.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201
        
        # TODO: This test will need to be updated when we implement
        # proper email verification flow
        
        # Act
        login_data = {
            "email": "login@example.com",
            "password": "SecurePassword123!"
        }
        response = client_with_mocks.post("/api/v1/auth/login", json=login_data)
        
        # Assert - For now we expect 403 since email is not verified
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "verify" in data["detail"].lower()
    
    def test_login_invalid_credentials(self, client_with_mocks):
        """Test login with invalid credentials."""
        # Arrange
        login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        
        # Act
        response = client_with_mocks.post("/api/v1/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "credentials" in data["detail"].lower()
    
    def test_login_unverified_email(self, client_with_mocks):
        """Test login with unverified email."""
        # This test will be implemented when we have proper email verification
        pass


class TestAuthLogout:
    """Test cases for user logout endpoint."""
    
    def test_logout_success(self, client_with_mocks):
        """Test successful user logout."""
        # Arrange - Login first to get token
        # This will be implemented after login endpoint is working
        pass
    
    def test_logout_invalid_token(self, client_with_mocks):
        """Test logout with invalid token."""
        # Arrange
        headers = {"Authorization": "Bearer invalid_token"}
        
        # Act
        response = client_with_mocks.post("/api/v1/auth/logout", headers=headers)
        
        # Assert
        assert response.status_code == 401


class TestAuthRefresh:
    """Test cases for token refresh endpoint."""
    
    def test_refresh_success(self, client_with_mocks):
        """Test successful token refresh."""
        # Arrange - Create a refresh token using JWT service directly
        from src.common.services.jwt_service import jwt_service
        user_id = "123"
        refresh_token, _ = jwt_service.create_refresh_token(user_id)
        
        # Act
        data = {"refresh_token": refresh_token}
        response = client_with_mocks.post("/api/v1/auth/refresh", json=data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Verify tokens are different from original
        assert data["refresh_token"] != refresh_token
    
    def test_refresh_invalid_token(self, client_with_mocks):
        """Test refresh with invalid token."""
        # Arrange
        data = {"refresh_token": "invalid_token"}
        
        # Act
        response = client_with_mocks.post("/api/v1/auth/refresh", json=data)
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower()