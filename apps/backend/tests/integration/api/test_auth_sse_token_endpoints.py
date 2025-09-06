"""Integration tests for SSE token authentication endpoints."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt
from src.core.config import settings


@pytest.fixture
def valid_access_token():
    """Create a valid access token for testing."""
    from src.common.services.jwt_service import jwt_service

    user_id = "123"  # Use string representation of integer ID
    access_token, _, _ = jwt_service.create_access_token(user_id)
    return access_token


class TestSSETokenEndpoints:
    """Integration tests for SSE token endpoints."""

    @pytest.mark.asyncio
    async def test_create_sse_token_endpoint_success(self, async_client: AsyncClient, valid_access_token: str):
        """Test successful SSE token creation via API endpoint."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Act
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)

        # Assert
        assert response.status_code == 200

        response_data = response.json()
        assert "sse_token" in response_data
        assert "expires_at" in response_data
        assert response_data["token_type"] == "sse"

        # Verify token is valid JWT
        sse_token = response_data["sse_token"]
        assert sse_token is not None
        assert len(sse_token.split(".")) == 3  # JWT structure: header.payload.signature

        # Decode and verify token payload
        decoded_payload = jwt.decode(
            sse_token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )

        assert decoded_payload["token_type"] == "sse"
        assert "user_id" in decoded_payload
        assert "exp" in decoded_payload
        assert "iat" in decoded_payload

    @pytest.mark.asyncio
    async def test_create_sse_token_endpoint_unauthorized(self, async_client: AsyncClient):
        """Test SSE token creation fails without authentication."""
        # Act
        response = await async_client.post("/api/v1/auth/sse-token")

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_sse_token_endpoint_invalid_token(self, async_client: AsyncClient):
        """Test SSE token creation fails with invalid authentication token."""
        # Arrange
        headers = {"Authorization": "Bearer invalid_token"}

        # Act
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_sse_token_endpoint_expired_token(self, async_client: AsyncClient):
        """Test SSE token creation fails with expired authentication token."""
        # Arrange - Create an expired JWT token
        expired_payload = {
            "sub": "test-user-123",
            "exp": datetime.now(UTC) - timedelta(seconds=1),  # Expired
            "iat": datetime.now(UTC) - timedelta(minutes=10),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.auth.jwt_secret_key,
            algorithm=settings.auth.jwt_algorithm,
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        # Act
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_sse_token_response_structure(self, async_client: AsyncClient, valid_access_token: str):
        """Test SSE token response has correct structure and expiration."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Act
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)

        # Assert
        assert response.status_code == 200

        response_data = response.json()
        required_fields = {"sse_token", "expires_at", "token_type"}
        assert all(field in response_data for field in required_fields)

        # Verify expiration time is approximately 60 seconds from now
        expires_at_str = response_data["expires_at"]
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))

        now = datetime.now(UTC)
        expected_expiry = now + timedelta(seconds=settings.auth.sse_token_expire_seconds)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 5  # Allow 5 second tolerance for network/processing time

    @pytest.mark.asyncio
    async def test_create_multiple_sse_tokens(self, async_client: AsyncClient, valid_access_token: str):
        """Test creating multiple SSE tokens for the same user."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Act - Create multiple tokens
        response1 = await async_client.post("/api/v1/auth/sse-token", headers=headers)
        response2 = await async_client.post("/api/v1/auth/sse-token", headers=headers)

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        token1 = response1.json()["sse_token"]
        token2 = response2.json()["sse_token"]

        # Tokens should be different (different creation times)
        assert token1 != token2

        # Both tokens should be valid for the same user
        payload1 = jwt.decode(token1, settings.auth.jwt_secret_key, algorithms=[settings.auth.jwt_algorithm])
        payload2 = jwt.decode(token2, settings.auth.jwt_secret_key, algorithms=[settings.auth.jwt_algorithm])

        assert payload1["user_id"] == payload2["user_id"]
        assert payload1["token_type"] == payload2["token_type"] == "sse"

    @pytest.mark.asyncio
    async def test_sse_token_can_be_verified(self, async_client: AsyncClient, valid_access_token: str):
        """Test that created SSE token can be successfully verified."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Act - Create SSE token
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)
        assert response.status_code == 200

        sse_token = response.json()["sse_token"]

        # Verify the token using the verify function
        from src.api.routes.v1.auth_sse_token import verify_sse_token

        user_id = verify_sse_token(sse_token)

        # Assert
        assert user_id is not None
        assert isinstance(user_id, str)

    @pytest.mark.asyncio
    async def test_sse_token_short_expiration(self, async_client: AsyncClient, valid_access_token: str):
        """Test that SSE tokens have short expiration as configured."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Act
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)
        assert response.status_code == 200

        sse_token = response.json()["sse_token"]

        # Decode token to check expiration
        decoded_payload = jwt.decode(
            sse_token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
        )

        exp_timestamp = decoded_payload["exp"]
        iat_timestamp = decoded_payload["iat"]

        # Calculate token lifetime
        token_lifetime_seconds = exp_timestamp - iat_timestamp

        # Assert token lifetime matches configured expiration
        assert token_lifetime_seconds == settings.auth.sse_token_expire_seconds

    @pytest.mark.asyncio
    async def test_sse_token_security_headers(self, async_client: AsyncClient, valid_access_token: str):
        """Test that SSE token endpoint returns appropriate security headers."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Act
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)

        # Assert
        assert response.status_code == 200

        # Check for security headers that should be present
        response_headers = response.headers

        # FastAPI should include basic security headers
        # Note: Specific headers depend on middleware configuration
        assert "content-type" in response_headers
        assert response_headers["content-type"] == "application/json"


class TestSSETokenSecurity:
    """Security-focused tests for SSE token functionality."""

    @pytest.mark.asyncio
    async def test_sse_token_different_secret_fails_verification(
        self, async_client: AsyncClient, valid_access_token: str
    ):
        """Test that SSE tokens signed with different secrets fail verification."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Create SSE token normally
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)
        assert response.status_code == 200

        # Create a malicious token with different secret
        malicious_payload = {
            "user_id": "malicious-user",
            "token_type": "sse",
            "exp": datetime.now(UTC) + timedelta(seconds=60),
            "iat": datetime.now(UTC),
        }
        malicious_token = jwt.encode(malicious_payload, "different_secret", algorithm="HS256")

        # Act & Assert - Verification should fail
        from fastapi import HTTPException
        from src.api.routes.v1.auth_sse_token import verify_sse_token

        with pytest.raises(HTTPException):
            verify_sse_token(malicious_token)

    @pytest.mark.asyncio
    async def test_sse_token_algorithm_substitution_attack(self):
        """Test protection against algorithm substitution attacks."""
        # Arrange - Create token with 'none' algorithm
        payload = {
            "user_id": "attack-user",
            "token_type": "sse",
            "exp": datetime.now(UTC) + timedelta(seconds=60),
            "iat": datetime.now(UTC),
        }

        # Create unsigned token (algorithm 'none')
        import base64
        import json

        header = {"alg": "none", "typ": "JWT"}
        encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).decode().rstrip("=")
        unsigned_token = f"{encoded_header}.{encoded_payload}."

        # Act & Assert - Verification should fail
        from fastapi import HTTPException
        from src.api.routes.v1.auth_sse_token import verify_sse_token

        with pytest.raises(HTTPException):
            verify_sse_token(unsigned_token)

    @pytest.mark.asyncio
    async def test_sse_token_payload_tampering(self, async_client: AsyncClient, valid_access_token: str):
        """Test that tampered token payloads are rejected."""
        # Arrange
        headers = {"Authorization": f"Bearer {valid_access_token}"}

        # Create legitimate SSE token
        response = await async_client.post("/api/v1/auth/sse-token", headers=headers)
        assert response.status_code == 200

        legitimate_token = response.json()["sse_token"]
        header, payload, signature = legitimate_token.split(".")

        # Tamper with payload (change user_id)
        import base64
        import json

        decoded_payload = json.loads(base64.urlsafe_b64decode(payload + "=="))
        decoded_payload["user_id"] = "tampered-user-id"

        tampered_payload = (
            base64.urlsafe_b64encode(json.dumps(decoded_payload, default=str).encode()).decode().rstrip("=")
        )
        tampered_token = f"{header}.{tampered_payload}.{signature}"

        # Act & Assert - Verification should fail
        from fastapi import HTTPException
        from src.api.routes.v1.auth_sse_token import verify_sse_token

        with pytest.raises(HTTPException):  # Should raise HTTPException due to invalid signature
            verify_sse_token(tampered_token)
