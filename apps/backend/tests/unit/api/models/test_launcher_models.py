"""Unit tests for launcher API models."""

from src.api.models.launcher import HealthSummaryItem, HealthSummaryResponse, LauncherStatusResponse, ServiceStatusItem


class TestServiceStatusItem:
    """Test ServiceStatusItem model."""

    def test_service_status_item_creation(self):
        """Test service status item model creation"""
        # Arrange
        service_name = "api-gateway"
        status = "running"
        uptime_seconds = 3600

        # Act
        item = ServiceStatusItem(
            name=service_name, status=status, uptime_seconds=uptime_seconds, started_at="2025-09-02T15:30:00Z"
        )

        # Assert
        assert item.name == service_name
        assert item.status == status
        assert item.uptime_seconds == 3600
        assert item.started_at == "2025-09-02T15:30:00Z"

    def test_service_status_item_with_optional_fields(self):
        """Test service status item with optional fields"""
        # Arrange & Act
        item = ServiceStatusItem(
            name="api-gateway",
            status="running",
            uptime_seconds=1800,
            started_at="2025-09-02T15:30:00Z",
            pid=12345,
            port=8000,
        )

        # Assert
        assert item.pid == 12345
        assert item.port == 8000


class TestLauncherStatusResponse:
    """Test LauncherStatusResponse model."""

    def test_launcher_status_response_creation(self):
        """Test launcher status response model creation"""
        # Arrange
        services = [
            ServiceStatusItem(name="api", status="running", uptime_seconds=1800),
            ServiceStatusItem(name="agents", status="starting", uptime_seconds=0),
        ]

        # Act
        response = LauncherStatusResponse(
            launcher_status="partial", services=services, total_services=2, running_services=1
        )

        # Assert
        assert response.launcher_status == "partial"
        assert len(response.services) == 2
        assert response.total_services == 2
        assert response.running_services == 1

    def test_launcher_status_response_serialization(self):
        """Test launcher status response JSON serialization"""
        # Arrange
        services = [
            ServiceStatusItem(name="api", status="running", uptime_seconds=1800),
            ServiceStatusItem(name="agents", status="starting", uptime_seconds=0),
        ]

        # Act
        response = LauncherStatusResponse(
            launcher_status="running", services=services, total_services=2, running_services=1
        )

        # Assert
        json_data = response.model_dump()
        assert json_data["launcher_status"] == "running"
        assert len(json_data["services"]) == 2
        assert json_data["total_services"] == 2
        assert json_data["running_services"] == 1
        assert "timestamp" in json_data

    def test_launcher_status_response_empty_services(self):
        """Test launcher status response with empty services list"""
        # Act
        response = LauncherStatusResponse(launcher_status="stopped", services=[], total_services=0, running_services=0)

        # Assert
        assert response.launcher_status == "stopped"
        assert len(response.services) == 0
        assert response.total_services == 0
        assert response.running_services == 0


class TestHealthSummaryItem:
    """Test HealthSummaryItem model."""

    def test_health_summary_item_creation(self):
        """Test health summary item creation"""
        # Act
        item = HealthSummaryItem(
            service_name="api-gateway", status="healthy", response_time_ms=25.0, last_check="2025-09-02T16:39:45Z"
        )

        # Assert
        assert item.service_name == "api-gateway"
        assert item.status == "healthy"
        assert item.response_time_ms == 25.0
        assert item.last_check == "2025-09-02T16:39:45Z"
        assert item.error is None

    def test_health_summary_item_with_error(self):
        """Test health summary item with error"""
        # Act
        item = HealthSummaryItem(
            service_name="agent-worker",
            status="unhealthy",
            response_time_ms=0.0,
            last_check="2025-09-02T16:39:30Z",
            error="Connection timeout",
        )

        # Assert
        assert item.error == "Connection timeout"
        assert item.status == "unhealthy"


class TestHealthSummaryResponse:
    """Test HealthSummaryResponse model."""

    def test_health_summary_response_creation(self):
        """Test health summary response creation"""
        # Arrange
        services = [
            HealthSummaryItem(
                service_name="api-gateway", status="healthy", response_time_ms=25.0, last_check="2025-09-02T16:39:45Z"
            ),
            HealthSummaryItem(
                service_name="agent-worker",
                status="degraded",
                response_time_ms=150.0,
                last_check="2025-09-02T16:39:30Z",
                error="High response time",
            ),
        ]

        # Act
        response = HealthSummaryResponse(cluster_status="degraded", services=services, healthy_count=1, total_count=2)

        # Assert
        assert response.cluster_status == "degraded"
        assert len(response.services) == 2
        assert response.healthy_count == 1
        assert response.total_count == 2

    def test_health_summary_response_serialization(self):
        """Test health summary response JSON serialization"""
        # Arrange
        services = [
            HealthSummaryItem(
                service_name="api-gateway", status="healthy", response_time_ms=25.0, last_check="2025-09-02T16:39:45Z"
            )
        ]

        # Act
        response = HealthSummaryResponse(cluster_status="healthy", services=services, healthy_count=1, total_count=1)

        # Assert
        json_data = response.model_dump()
        assert json_data["cluster_status"] == "healthy"
        assert len(json_data["services"]) == 1
        assert json_data["healthy_count"] == 1
        assert json_data["total_count"] == 1
        assert "timestamp" in json_data
