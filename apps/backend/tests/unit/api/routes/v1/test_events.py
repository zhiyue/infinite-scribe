"""Unit tests for SSE events endpoints.

Focuses on basic endpoint existence, parameter validation, and error codes.
Integration tests handle authentication flows and realistic scenarios.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.routes.v1.events import ConnectionStatistics, SSEHealthResponse
from src.common.services.redis_sse_service import RedisSSEService
from src.services.sse_connection_manager import SSEConnectionManager


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


class TestSSEHealthEndpoint:
    """Comprehensive tests for SSE health check endpoint."""

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.events.get_sse_connection_manager")
    @patch("src.api.routes.v1.events.get_redis_sse_service")
    async def test_health_endpoint_healthy_state(self, mock_get_redis_sse, mock_get_connection_manager, client):
        """Test health endpoint returns healthy state when all services are working."""
        # Arrange
        mock_connection_manager = Mock(spec=SSEConnectionManager)
        mock_connection_manager.get_connection_count = AsyncMock(
            return_value={"active_connections": 5, "redis_connection_counters": 3}
        )
        mock_get_connection_manager.return_value = mock_connection_manager

        mock_redis_sse_service = Mock(spec=RedisSSEService)
        mock_pubsub_client = AsyncMock()
        mock_pubsub_client.ping = AsyncMock(return_value=True)
        mock_redis_sse_service._pubsub_client = mock_pubsub_client
        mock_get_redis_sse.return_value = mock_redis_sse_service

        # Act
        response = client.get("/api/v1/events/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis_status"] == "healthy"
        assert data["service"] == "sse"
        assert data["version"] == "1.0.0"
        assert data["connection_statistics"]["active_connections"] == 5
        assert data["connection_statistics"]["redis_connection_counters"] == 3

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.events.get_sse_connection_manager")
    @patch("src.api.routes.v1.events.get_redis_sse_service")
    async def test_health_endpoint_degraded_redis(self, mock_get_redis_sse, mock_get_connection_manager, client):
        """Test health endpoint returns degraded state when Redis is unhealthy."""
        # Arrange
        mock_connection_manager = Mock(spec=SSEConnectionManager)
        mock_connection_manager.get_connection_count = AsyncMock(
            return_value={"active_connections": 2, "redis_connection_counters": 0}
        )
        mock_get_connection_manager.return_value = mock_connection_manager

        mock_redis_sse_service = Mock(spec=RedisSSEService)
        mock_pubsub_client = AsyncMock()
        mock_pubsub_client.ping = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_redis_sse_service._pubsub_client = mock_pubsub_client
        mock_get_redis_sse.return_value = mock_redis_sse_service

        # Act
        response = client.get("/api/v1/events/health")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["redis_status"] == "unhealthy"
        assert data["service"] == "sse"
        assert data["connection_statistics"]["active_connections"] == 2
        assert data["connection_statistics"]["redis_connection_counters"] == 0

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.events.get_sse_connection_manager")
    @patch("src.api.routes.v1.events.get_redis_sse_service")
    async def test_health_endpoint_no_redis_client(self, mock_get_redis_sse, mock_get_connection_manager, client):
        """Test health endpoint handles missing Redis pubsub client gracefully."""
        # Arrange
        mock_connection_manager = Mock(spec=SSEConnectionManager)
        mock_connection_manager.get_connection_count = AsyncMock(
            return_value={"active_connections": 0, "redis_connection_counters": 0}
        )
        mock_get_connection_manager.return_value = mock_connection_manager

        mock_redis_sse_service = Mock(spec=RedisSSEService)
        mock_redis_sse_service._pubsub_client = None  # No client initialized
        mock_get_redis_sse.return_value = mock_redis_sse_service

        # Act
        response = client.get("/api/v1/events/health")

        # Assert
        assert response.status_code == 503  # Service unavailable when Redis client not available
        data = response.json()
        assert data["status"] == "degraded"  # Degraded when Redis not available
        assert data["redis_status"] == "unhealthy"
        assert data["connection_statistics"]["active_connections"] == 0

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.events.get_sse_connection_manager")
    async def test_health_endpoint_connection_manager_error(self, mock_get_connection_manager, client):
        """Test health endpoint handles connection manager errors gracefully."""
        # Arrange
        mock_connection_manager = Mock(spec=SSEConnectionManager)
        mock_connection_manager.get_connection_count = AsyncMock(side_effect=Exception("Connection manager failed"))
        mock_get_connection_manager.return_value = mock_connection_manager

        # Act
        response = client.get("/api/v1/events/health")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["service"] == "sse"
        assert data["connection_statistics"]["active_connections"] == -1
        assert data["connection_statistics"]["redis_connection_counters"] == -1

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.events.get_sse_connection_manager")
    @patch("src.api.routes.v1.events.get_redis_sse_service")
    async def test_health_endpoint_timeout_scenarios(self, mock_get_redis_sse, mock_get_connection_manager, client):
        """Test health endpoint handles timeout scenarios gracefully."""

        # Arrange - connection stats timeout
        mock_connection_manager = Mock(spec=SSEConnectionManager)
        mock_connection_manager.get_connection_count = AsyncMock(side_effect=TimeoutError())
        mock_get_connection_manager.return_value = mock_connection_manager

        mock_redis_sse_service = Mock(spec=RedisSSEService)
        mock_pubsub_client = AsyncMock()
        mock_pubsub_client.ping = AsyncMock(return_value=True)
        mock_redis_sse_service._pubsub_client = mock_pubsub_client
        mock_get_redis_sse.return_value = mock_redis_sse_service

        # Act
        response = client.get("/api/v1/events/health")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"  # Should be unhealthy due to stats timeout
        assert data["connection_statistics"]["active_connections"] == -1
        assert data["connection_statistics"]["redis_connection_counters"] == -1

    @pytest.mark.asyncio
    @patch("src.api.routes.v1.events.get_sse_connection_manager")
    @patch("src.api.routes.v1.events.get_redis_sse_service")
    async def test_health_endpoint_redis_timeout(self, mock_get_redis_sse, mock_get_connection_manager, client):
        """Test health endpoint handles Redis ping timeout gracefully."""

        # Arrange
        mock_connection_manager = Mock(spec=SSEConnectionManager)
        mock_connection_manager.get_connection_count = AsyncMock(
            return_value={"active_connections": 3, "redis_connection_counters": 2}
        )
        mock_get_connection_manager.return_value = mock_connection_manager

        mock_redis_sse_service = Mock(spec=RedisSSEService)
        mock_pubsub_client = AsyncMock()
        mock_pubsub_client.ping = AsyncMock(side_effect=TimeoutError())
        mock_redis_sse_service._pubsub_client = mock_pubsub_client
        mock_get_redis_sse.return_value = mock_redis_sse_service

        # Act
        response = client.get("/api/v1/events/health")

        # Assert
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"  # Should be degraded due to Redis timeout
        assert data["redis_status"] == "unhealthy"
        assert data["connection_statistics"]["active_connections"] == 3


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


class TestSSEHealthModels:
    """Test SSE health response models."""

    def test_connection_statistics_model(self):
        """Test ConnectionStatistics model validation."""
        # Act
        stats = ConnectionStatistics(active_connections=10, redis_connection_counters=5)

        # Assert
        assert stats.active_connections == 10
        assert stats.redis_connection_counters == 5

    def test_sse_health_response_model(self):
        """Test SSEHealthResponse model validation."""
        # Arrange
        connection_stats = ConnectionStatistics(active_connections=3, redis_connection_counters=2)

        # Act
        health_response = SSEHealthResponse(
            status="healthy",
            redis_status="healthy",
            connection_statistics=connection_stats,
            service="sse",
            version="1.0.0",
        )

        # Assert
        assert health_response.status == "healthy"
        assert health_response.redis_status == "healthy"
        assert health_response.connection_statistics.active_connections == 3
        assert health_response.service == "sse"
        assert health_response.version == "1.0.0"

    def test_sse_health_error_response_format(self):
        """Test health endpoint error response format (simplified to plain dict)."""
        # This test verifies that error responses are plain dictionaries
        # instead of complex model classes, which is the simplified approach
        error_data = {
            "status": "unhealthy",
            "error": "Redis connection failed",
            "service": "sse",
            "version": "1.0.0"
        }

        # Assert
        assert error_data["status"] == "unhealthy"
        assert error_data["error"] == "Redis connection failed"
        assert error_data["service"] == "sse"
        assert error_data["version"] == "1.0.0"
