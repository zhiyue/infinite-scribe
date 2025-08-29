"""Unit tests for SSE events endpoints.

Focuses on basic endpoint existence, parameter validation, and error codes.
Integration tests handle authentication flows and realistic scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestEndpointExistence:
    """Test that all SSE endpoints exist and handle basic validation."""

    def test_stream_endpoint_requires_token_parameter(self, client):
        """SSE stream endpoint should require sse_token parameter."""
        response = client.get("/api/v1/events/stream")
        assert response.status_code == 422

    def test_token_endpoint_requires_authentication(self, client):
        """SSE token endpoint should require JWT authentication."""
        response = client.post("/api/v1/auth/sse-token")
        assert response.status_code == 401

    def test_health_endpoint_accessible(self, client):
        """Health endpoint should be accessible but return 503 without Redis."""
        response = client.get("/api/v1/events/health")
        assert response.status_code == 503


class TestParameterValidation:
    """Test endpoint parameter validation."""

    def test_stream_with_invalid_token(self, client):
        """Stream endpoint should reject invalid tokens."""
        response = client.get("/api/v1/events/stream?sse_token=invalid_token")
        assert response.status_code == 401

    def test_token_with_invalid_jwt(self, client):
        """Token endpoint should reject invalid JWT tokens."""
        response = client.post("/api/v1/auth/sse-token", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 401


class TestResponseFormats:
    """Test that endpoints return expected response formats."""

    def test_health_returns_json_with_status(self, client):
        """Health endpoint should return JSON with service status."""
        response = client.get("/api/v1/events/health")
        assert response.status_code == 503

        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "sse"
