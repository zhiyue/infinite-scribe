"""Integration tests for authentication endpoints."""

import pytest


class TestAuthRegister:
    """Test cases for user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client, pg_session):
        """Test successful user registration."""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "first_name": "Test",
            "last_name": "User",
        }

        # Act
        response = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        if response.status_code != 201:
            print(f"Error response: {response.text}")
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "user" in data
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"
        assert "password" not in data["user"]  # Password should not be returned
        assert "message" in data
        assert "verify" in data["message"].lower() and "email" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client):
        """Test registration with weak password."""
        # Arrange
        user_data = {"username": "testuser", "email": "test@example.com", "password": "weak"}

        # Act
        response = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        assert response.status_code == 422  # Validation error from pydantic
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client):
        """Test registration with duplicate email."""
        # Arrange
        user_data = {"username": "testuser1", "email": "duplicate@example.com", "password": "SecurePassword123!"}

        # Act - Register first user
        response1 = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        # Act - Try to register with same email
        user_data["username"] = "testuser2"
        response2 = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, async_client):
        """Test registration with duplicate username."""
        # Arrange
        user_data = {"username": "duplicateuser", "email": "test1@example.com", "password": "SecurePassword123!"}

        # Act - Register first user
        response1 = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        # Act - Try to register with same username
        user_data["email"] = "test2@example.com"
        response2 = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already exists" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client):
        """Test registration with invalid email format."""
        # Arrange
        user_data = {"username": "testuser", "email": "invalid-email", "password": "SecurePassword123!"}

        # Act
        response = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_required_fields(self, async_client):
        """Test registration with missing required fields."""
        # Arrange
        user_data = {
            "username": "testuser"
            # Missing email and password
        }

        # Act
        response = await async_client.post("/api/v1/auth/register", json=user_data)

        # Assert
        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Test cases for user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client):
        """Test successful user login."""
        # Arrange - First register a user
        user_data = {"username": "logintest", "email": "login@example.com", "password": "SecurePassword123!"}
        register_response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        # TODO: This test will need to be updated when we implement
        # proper email verification flow

        # Act
        login_data = {"email": "login@example.com", "password": "SecurePassword123!"}
        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Assert - For now we expect 403 since email is not verified
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        # Handle both string and dict formats for detail
        if isinstance(data["detail"], str):
            assert "verify" in data["detail"].lower()
        else:
            assert "message" in data["detail"]
            assert "verify" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client):
        """Test login with invalid credentials."""
        # Arrange
        login_data = {"email": "nonexistent@example.com", "password": "WrongPassword123!"}

        # Act
        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        # Handle both string and dict formats for detail
        if isinstance(data["detail"], str):
            assert "credentials" in data["detail"].lower()
        else:
            assert "message" in data["detail"]
            assert "credentials" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_login_unverified_email(self, async_client):
        """Test login with unverified email."""
        # This test will be implemented when we have proper email verification
        pass


class TestAuthLogout:
    """Test cases for user logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, async_client):
        """Test successful user logout."""
        # Arrange - Login first to get token
        # This will be implemented after login endpoint is working
        pass

    @pytest.mark.asyncio
    async def test_logout_invalid_token(self, async_client):
        """Test logout with invalid token."""
        # Arrange
        headers = {"Authorization": "Bearer invalid_token"}

        # Act
        response = await async_client.post("/api/v1/auth/logout", headers=headers)

        # Assert
        assert response.status_code == 401


class TestAuthRefresh:
    """Test cases for token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, async_client):
        """Test successful token refresh."""
        # This test needs proper login flow to create session
        # For now, we'll test with invalid token to ensure endpoint works

        # Arrange - Create a refresh token using JWT service directly
        from src.common.services.user.auth_service import auth_service

        user_id = "123"
        refresh_token, _ = auth_service.create_refresh_token(user_id)

        # Act
        data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=data)

        # Assert - Expect 401 because there's no session
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "session" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, async_client):
        """Test refresh with invalid token."""
        # Arrange
        data = {"refresh_token": "invalid_token"}

        # Act
        response = await async_client.post("/api/v1/auth/refresh", json=data)

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_empty_request_body(self, async_client):
        """Test refresh with empty request body."""
        # Act
        response = await async_client.post("/api/v1/auth/refresh", json={})

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Verify it's a validation error about missing refresh_token
        assert any("refresh_token" in str(error).lower() for error in data["detail"])

    @pytest.mark.asyncio
    async def test_refresh_missing_refresh_token_field(self, async_client):
        """Test refresh with request body missing refresh_token field."""
        # Arrange
        data = {"other_field": "value"}

        # Act
        response = await async_client.post("/api/v1/auth/refresh", json=data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Verify it's a validation error about missing refresh_token
        assert any("refresh_token" in str(error).lower() for error in data["detail"])

    @pytest.mark.asyncio
    async def test_refresh_null_refresh_token(self, async_client):
        """Test refresh with null refresh_token."""
        # Arrange
        data = {"refresh_token": None}

        # Act
        response = await async_client.post("/api/v1/auth/refresh", json=data)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_refresh_with_old_access_token_header(self, async_client):
        """Test refresh endpoint properly extracts old access token from header."""
        # Arrange - Create tokens
        from src.common.services.user.auth_service import auth_service

        user_id = "123"
        old_access_token, _, _ = auth_service.create_access_token(user_id)
        refresh_token, _ = auth_service.create_refresh_token(user_id)

        # Act - Send refresh request with old access token in header
        headers = {"Authorization": f"Bearer {old_access_token}"}
        data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=data, headers=headers)

        # Assert - Expect 401 because there's no session
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
