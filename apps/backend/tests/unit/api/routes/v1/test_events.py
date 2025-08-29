"""Unit tests for SSE events endpoints."""

from fastapi.testclient import TestClient
from src.api.main import app


class TestSSEEndpointsExistence:
    """Test that SSE endpoints exist and return correct status codes."""

    def test_sse_stream_endpoint_exists(self):
        """Test that GET /api/v1/events/stream endpoint exists and requires token."""
        client = TestClient(app)

        # Endpoint exists but requires sse_token parameter (422 Unprocessable Entity)
        response = client.get("/api/v1/events/stream")
        assert response.status_code == 422, "SSE stream endpoint should require sse_token parameter"

    def test_sse_token_endpoint_exists(self):
        """Test that POST /api/v1/auth/sse-token endpoint exists and requires auth."""
        client = TestClient(app)

        # Endpoint exists but requires JWT authentication (401 Unauthorized)
        response = client.post("/api/v1/auth/sse-token")
        assert response.status_code == 401, "SSE token endpoint should require JWT authentication"

    def test_sse_health_endpoint_exists(self):
        """Test that GET /api/v1/events/health endpoint exists."""
        client = TestClient(app)

        # Health endpoint exists but Redis is not available in tests (503 Service Unavailable)
        response = client.get("/api/v1/events/health")
        assert response.status_code == 503, "SSE health endpoint should return 503 when Redis unavailable"


class TestSSEStreamEndpointBehavior:
    """Test expected behavior of SSE stream endpoint."""

    def test_sse_stream_with_invalid_token(self):
        """Test that SSE stream validates token correctly."""
        client = TestClient(app)

        # Invalid token should return 401
        response = client.get("/api/v1/events/stream?sse_token=invalid_token")
        assert response.status_code == 401

    def test_sse_stream_requires_token(self):
        """Test that SSE stream requires sse_token parameter."""
        client = TestClient(app)

        # Missing token parameter should return 422
        response = client.get("/api/v1/events/stream")
        assert response.status_code == 422


class TestSSETokenEndpointBehavior:
    """Test expected behavior of SSE token endpoint."""

    def test_sse_token_requires_jwt(self):
        """Test that SSE token creation requires JWT authentication."""
        client = TestClient(app)

        # Without JWT authentication, should return 401
        response = client.post("/api/v1/auth/sse-token")
        assert response.status_code == 401

    def test_sse_token_with_invalid_jwt(self):
        """Test that SSE token endpoint validates JWT."""
        client = TestClient(app)

        # With invalid JWT token, should return 401
        response = client.post("/api/v1/auth/sse-token", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 401


class TestSSEHealthEndpointBehavior:
    """Test expected behavior of SSE health endpoint."""

    def test_health_endpoint_no_auth_required(self):
        """Test that health endpoint doesn't require authentication."""
        client = TestClient(app)

        # Health endpoint accessible without auth, but Redis unavailable returns 503
        response = client.get("/api/v1/events/health")
        assert response.status_code == 503

    def test_health_endpoint_returns_json_format(self):
        """Test that health endpoint returns proper JSON format."""
        client = TestClient(app)

        # Health endpoint returns JSON with status info
        response = client.get("/api/v1/events/health")
        assert response.status_code == 503

        # Should be valid JSON
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "sse"
