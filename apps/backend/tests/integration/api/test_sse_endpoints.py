"""Integration tests for SSE (Server-Sent Events) endpoints.

Tests realistic authentication flows and cross-service integration.
Unit tests handle basic endpoint existence and parameter validation.
"""

from unittest.mock import patch

import pytest


@pytest.fixture
async def mock_user():
    """Mock authenticated user fixture."""
    from src.models.user import User

    user = User()
    # id 在模型中是 int（Mapped[int]），测试中使用整数以满足类型检查
    user.id = 123
    user.email = "test@example.com"
    return user


class TestSSEAuthenticationFlow:
    """Test complete SSE authentication flow."""

    @pytest.mark.asyncio
    async def test_stream_missing_token_parameter(self, postgres_async_client):
        """Stream endpoint should require sse_token parameter."""
        response = await postgres_async_client.get("/api/v1/events/stream")
        assert response.status_code == 422

        error_detail = response.json()["detail"]
        assert any("sse_token" in str(error) for error in error_detail)

    @pytest.mark.asyncio
    async def test_stream_with_invalid_token_format(self, postgres_async_client):
        """Stream endpoint should reject malformed tokens."""
        response = await postgres_async_client.get("/api/v1/events/stream?sse_token=invalid_token")
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_token_creation_without_jwt(self, postgres_async_client):
        """Token creation should require JWT authentication."""
        response = await postgres_async_client.post("/api/v1/auth/sse-token")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_creation_with_invalid_jwt(self, postgres_async_client):
        """Token creation should validate JWT tokens."""
        response = await postgres_async_client.post(
            "/api/v1/auth/sse-token", headers={"Authorization": "Bearer invalid_jwt"}
        )
        assert response.status_code == 401


class TestSSEHealthIntegration:
    """Test health endpoint integration with services."""

    @pytest.mark.asyncio
    async def test_health_endpoint_structure(self, postgres_async_client):
        """Health endpoint should return proper service status structure."""
        response = await postgres_async_client.get("/api/v1/events/health")

        # Should return 503 when Redis is unavailable (normal in test environment)
        assert response.status_code == 503

        data = response.json()

        # Verify required fields
        assert "status" in data
        assert "service" in data
        assert "redis_status" in data
        assert "version" in data

        # Verify values
        assert data["service"] == "sse"
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert data["redis_status"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth_required(self, postgres_async_client):
        """Health endpoint should not require authentication."""
        # Should work without any headers
        response = await postgres_async_client.get("/api/v1/events/health")

        # Should return service status (503 due to Redis unavailable in tests)
        assert response.status_code == 503
        assert response.headers["content-type"].startswith("application/json")


class TestSSEServiceIntegration:
    """Test SSE service integration scenarios."""

    @pytest.mark.asyncio
    @patch("src.services.sse_connection_manager.SSEConnectionManager.add_connection")
    @patch("src.api.routes.v1.events.verify_sse_token")
    async def test_stream_connection_with_valid_token(
        self, mock_verify_token, mock_add_connection, postgres_async_client
    ):
        """Test successful SSE connection with valid token."""
        # Mock successful token verification
        mock_verify_token.return_value = "123"

        # Mock connection manager response
        from fastapi.responses import StreamingResponse

        mock_add_connection.return_value = StreamingResponse(iter([b"data: test\n\n"]), media_type="text/event-stream")

        response = await postgres_async_client.get("/api/v1/events/stream?sse_token=valid_sse_token")

        # Should accept the connection
        assert response.status_code == 200
        mock_verify_token.assert_called_once_with("valid_sse_token")
        mock_add_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_creation_with_valid_jwt(self, postgres_async_client, mock_user):
        """Test successful SSE token creation with valid JWT."""
        # 使用依赖覆盖替代函数 patch，确保 FastAPI 路由依赖被替换
        from src.api.main import app
        from src.api.routes.v1.auth_sse_token import get_current_user as dep_get_current_user

        app.dependency_overrides[dep_get_current_user] = lambda: mock_user
        try:
            response = await postgres_async_client.post(
                "/api/v1/auth/sse-token", headers={"Authorization": "Bearer valid_jwt_token"}
            )
        finally:
            app.dependency_overrides.pop(dep_get_current_user, None)

        # Should create token successfully
        assert response.status_code == 200

        data = response.json()
        assert "sse_token" in data
        assert "expires_at" in data
        assert "token_type" in data
        assert data["token_type"] == "sse"

    @pytest.mark.asyncio
    async def test_stream_with_last_event_id_header(self, postgres_async_client):
        """Test that Last-Event-ID header is accepted but token validation still applies."""
        headers = {"Last-Event-ID": "event-123"}
        response = await postgres_async_client.get("/api/v1/events/stream?sse_token=invalid_token", headers=headers)

        # Should still fail due to invalid token, but accept the header
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]


class TestSSEErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_stream_handles_empty_token(self, postgres_async_client):
        """Stream endpoint should handle empty token parameter."""
        response = await postgres_async_client.get("/api/v1/events/stream?sse_token=")
        assert response.status_code == 401
        assert "Token is required" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("src.common.services.redis_sse_service.RedisSSEService.init_pubsub_client")
    async def test_health_handles_redis_connection_errors(self, mock_init_pubsub, postgres_async_client):
        """Health endpoint should handle Redis connection errors gracefully."""
        # Mock Redis connection failure
        mock_init_pubsub.side_effect = Exception("Redis connection failed")

        response = await postgres_async_client.get("/api/v1/events/health")

        # Should return 503 with error information
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data
