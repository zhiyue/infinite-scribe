"""Unit tests for launcher admin endpoints."""

import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from src.api.routes.admin.launcher import get_health_monitor, get_orchestrator, require_admin_access, router
from src.core.config import Settings
from src.launcher.health import HealthCheckResult, HealthMonitor, HealthStatus
from src.launcher.orchestrator import Orchestrator
from src.launcher.types import ServiceStatus


# Module-level fixtures for shared use across all test classes
@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator fixture."""
    orchestrator = Mock(spec=Orchestrator)
    return orchestrator


@pytest.fixture
def mock_health_monitor():
    """Mock health monitor fixture."""
    health_monitor = Mock(spec=HealthMonitor)
    return health_monitor


@pytest.fixture
def mock_settings():
    """Mock settings fixture."""
    settings = Mock(spec=Settings)
    settings.environment = "development"
    settings.launcher = Mock()
    settings.launcher.admin_enabled = True
    return settings


@pytest.fixture
def test_client(mock_orchestrator, mock_health_monitor, mock_settings):
    """Create test client with mocked dependencies."""
    app = FastAPI()

    # Override dependencies using FastAPI's recommended approach
    app.dependency_overrides[require_admin_access] = lambda: True
    
    # Set mock instances directly in app.state (new approach)
    app.state.orchestrator = mock_orchestrator
    app.state.health_monitor = mock_health_monitor

    app.include_router(router)
    return TestClient(app)


class TestAdminEndpoints:
    """Test admin launcher endpoints."""

    def test_get_launcher_status_success(self, test_client, mock_orchestrator):
        """Test getting launcher status successfully - Scenario 1"""
        # Arrange - Mock orchestrator returns 2 services (1 running, 1 starting)
        mock_orchestrator.get_all_service_states.return_value = {
            "api-gateway": {
                "state": ServiceStatus.RUNNING,
                "started_at": "2025-09-02T15:30:00Z",
                "uptime": 1800,
                "pid": 12345,
                "port": 8000,
            },
            "agents": {"state": ServiceStatus.STARTING, "started_at": None, "uptime": 0, "pid": None, "port": None},
        }

        # Act
        response = test_client.get("/admin/launcher/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["launcher_status"] == "partial"
        assert data["total_services"] == 2
        assert data["running_services"] == 1
        assert len(data["services"]) == 2

        # Verify service details
        api_service = next(s for s in data["services"] if s["name"] == "api-gateway")
        assert api_service["status"] == "running"
        assert api_service["uptime_seconds"] == 1800
        assert api_service["pid"] == 12345

    def test_get_launcher_status_all_running(self, test_client, mock_orchestrator):
        """Test launcher status when all services are running - Scenario 2"""
        # Arrange - Mock orchestrator returns all services as RUNNING
        mock_orchestrator.get_all_service_states.return_value = {
            "api-gateway": {
                "state": ServiceStatus.RUNNING,
                "started_at": "2025-09-02T15:30:00Z",
                "uptime": 1800,
                "pid": 12345,
                "port": 8000,
            },
            "agents": {
                "state": ServiceStatus.RUNNING,
                "started_at": "2025-09-02T15:35:00Z",
                "uptime": 900,
                "pid": 12346,
                "port": 8001,
            },
        }

        # Act
        response = test_client.get("/admin/launcher/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["launcher_status"] == "running"
        assert data["running_services"] == data["total_services"]
        assert data["total_services"] == 2

    def test_get_launcher_status_empty_services(self, test_client, mock_orchestrator):
        """Test launcher status with no services - Scenario 4"""
        # Arrange - Mock orchestrator returns empty services
        mock_orchestrator.get_all_service_states.return_value = {}

        # Act
        response = test_client.get("/admin/launcher/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["launcher_status"] == "stopped"
        assert data["total_services"] == 0
        assert data["running_services"] == 0
        assert data["services"] == []

    def test_get_launcher_health_success(self, test_client, mock_health_monitor):
        """Test getting health summary successfully - Scenario 6"""
        # Arrange - Mock health monitor returns 3 services (2 healthy, 1 degraded)
        mock_health_monitor.get_cluster_health.return_value = {
            "api-gateway": HealthCheckResult(
                service_name="api-gateway", status=HealthStatus.HEALTHY, response_time_ms=25.0, timestamp=time.time()
            ),
            "agent:worldsmith": HealthCheckResult(
                service_name="agent:worldsmith",
                status=HealthStatus.DEGRADED,
                response_time_ms=150.0,
                timestamp=time.time(),
            ),
            "agents": HealthCheckResult(
                service_name="agents", status=HealthStatus.HEALTHY, response_time_ms=50.0, timestamp=time.time()
            ),
        }
        mock_health_monitor.get_cluster_status.return_value = HealthStatus.DEGRADED

        # Act
        response = test_client.get("/admin/launcher/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["cluster_status"] == "degraded"
        assert data["total_count"] == 3
        assert data["healthy_count"] == 2
        assert len(data["services"]) == 3

    def test_get_launcher_health_all_healthy(self, test_client, mock_health_monitor):
        """Test health summary when all services are healthy - Scenario 8"""
        # Arrange - All services HEALTHY
        mock_health_monitor.get_cluster_health.return_value = {
            "api-gateway": HealthCheckResult(
                service_name="api-gateway", status=HealthStatus.HEALTHY, response_time_ms=25.0, timestamp=time.time()
            ),
            "agents": HealthCheckResult(
                service_name="agents", status=HealthStatus.HEALTHY, response_time_ms=30.0, timestamp=time.time()
            ),
        }
        mock_health_monitor.get_cluster_status.return_value = HealthStatus.HEALTHY

        # Act
        response = test_client.get("/admin/launcher/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["cluster_status"] == "healthy"
        assert data["healthy_count"] == data["total_count"]

    def test_get_launcher_health_no_data(self, test_client, mock_health_monitor):
        """Test health summary with no health data - Scenario 9"""
        # Arrange - Mock health monitor returns empty health cache
        mock_health_monitor.get_cluster_health.return_value = {}
        mock_health_monitor.get_cluster_status.return_value = HealthStatus.UNKNOWN

        # Act
        response = test_client.get("/admin/launcher/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["cluster_status"] == "unknown"
        assert data["total_count"] == 0
        assert data["services"] == []

    def test_orchestrator_not_ready(self, test_client, mock_orchestrator):
        """Test status endpoint when orchestrator is not ready - Scenario 17"""
        # Arrange - Mock orchestrator throws exception
        mock_orchestrator.get_all_service_states.side_effect = Exception("Orchestrator not ready")

        # Act
        response = test_client.get("/admin/launcher/status")

        # Assert
        assert response.status_code == 503
        assert "service unavailable" in response.json()["detail"].lower()

    def test_health_monitor_exception(self, test_client, mock_health_monitor):
        """Test health endpoint when health monitor throws exception - Scenario 18"""
        # Arrange - Mock health monitor throws exception
        mock_health_monitor.get_cluster_health.side_effect = Exception("Health monitor error")

        # Act
        response = test_client.get("/admin/launcher/health")

        # Assert
        assert response.status_code == 503
        assert "service unavailable" in response.json()["detail"].lower()

    def test_response_time_validation(self, test_client, mock_orchestrator):
        """Test response time meets NFR-003 requirements - Scenario 21"""
        # Arrange
        mock_orchestrator.get_all_service_states.return_value = {
            "api-gateway": {
                "state": ServiceStatus.RUNNING,
                "started_at": "2025-09-02T15:30:00Z",
                "uptime": 1800,
                "pid": 12345,
                "port": 8000,
            }
        }

        # Act
        start_time = time.time()
        response = test_client.get("/admin/launcher/status")
        response_time = time.time() - start_time

        # Assert
        assert response.status_code == 200
        # NFR-003: Response time should be < 200ms
        assert response_time < 0.2  # 200ms in seconds

    def test_concurrent_access(self, test_client, mock_orchestrator, mock_health_monitor):
        """Test concurrent access to admin endpoints - Scenario 22"""
        # Arrange
        mock_orchestrator.get_all_service_states.return_value = {"api": {"state": ServiceStatus.RUNNING, "uptime": 100}}
        mock_health_monitor.get_cluster_health.return_value = {
            "api": HealthCheckResult("api", HealthStatus.HEALTHY, 25.0, time.time())
        }

        # Act - Make concurrent requests
        import threading

        results = []

        def make_request():
            response = test_client.get("/admin/launcher/status")
            results.append(response.status_code)

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Assert - All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10


class TestAdminSecurity:
    """Test admin endpoint security controls."""

    def test_development_environment_enables_endpoints(self):
        """Test development environment enables admin endpoints - Scenario 10"""
        # Arrange
        settings = Mock()
        settings.environment = "development"
        settings.launcher = Mock()
        settings.launcher.admin_enabled = True

        # Act & Assert
        result = require_admin_access(settings)
        assert result is True

    def test_production_environment_disables_by_default(self):
        """Test production environment disables admin endpoints by default - Scenario 11"""
        # Arrange
        settings = Mock()
        settings.environment = "production"
        settings.launcher = Mock()
        settings.launcher.admin_enabled = False

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            require_admin_access(settings)

        assert exc_info.value.status_code == 404
        assert "not available" in exc_info.value.detail

    def test_production_environment_explicit_enable(self):
        """Test production environment can explicitly enable - Scenario 12"""
        # Arrange
        settings = Mock()
        settings.environment = "production"
        settings.launcher = Mock()
        settings.launcher.admin_enabled = True

        # Act & Assert
        result = require_admin_access(settings)
        assert result is True


class TestAPISpecCompliance:
    """Test API specification compliance."""

    def test_openapi_documentation_generation(self, test_client):
        """Test admin endpoints appear in OpenAPI docs - Scenario 14"""
        # Act
        response = test_client.get("/openapi.json")

        # Assert
        assert response.status_code == 200
        openapi_spec = response.json()

        # Check that admin endpoints are documented
        paths = openapi_spec["paths"]
        assert "/admin/launcher/status" in paths
        assert "/admin/launcher/health" in paths

        # Check correct tags
        status_endpoint = paths["/admin/launcher/status"]["get"]
        assert "launcher-admin" in status_endpoint["tags"]

    def test_response_model_validation(self, test_client, mock_orchestrator):
        """Test responses conform to Pydantic models - Scenario 15"""
        # Arrange
        mock_orchestrator.get_all_service_states.return_value = {
            "api": {
                "state": ServiceStatus.RUNNING,
                "started_at": "2025-09-02T15:30:00Z",
                "uptime": 1800,
                "pid": 12345,
                "port": 8000,
            }
        }

        # Act
        response = test_client.get("/admin/launcher/status")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Validate response structure matches LauncherStatusResponse model
        required_fields = ["launcher_status", "services", "total_services", "running_services", "timestamp"]
        for field in required_fields:
            assert field in data

        # Validate service item structure
        service = data["services"][0]
        service_required_fields = ["name", "status", "uptime_seconds"]
        for field in service_required_fields:
            assert field in service

    def test_timestamp_format_consistency(self, test_client, mock_orchestrator, mock_health_monitor):
        """Test all timestamp fields use consistent ISO format - Scenario 16"""
        # Arrange
        mock_orchestrator.get_all_service_states.return_value = {
            "api": {"state": ServiceStatus.RUNNING, "started_at": "2025-09-02T15:30:00Z", "uptime": 1800}
        }
        mock_health_monitor.get_cluster_health.return_value = {
            "api": HealthCheckResult("api", HealthStatus.HEALTHY, 25.0, time.time())
        }
        mock_health_monitor.get_cluster_status.return_value = HealthStatus.HEALTHY

        # Act
        status_response = test_client.get("/admin/launcher/status")
        health_response = test_client.get("/admin/launcher/health")

        # Assert
        assert status_response.status_code == 200
        assert health_response.status_code == 200

        # Check timestamp format (should be ISO 8601)
        status_data = status_response.json()
        health_data = health_response.json()

        # Validate timestamps can be parsed as ISO format
        datetime.fromisoformat(status_data["timestamp"].replace("Z", "+00:00"))
        datetime.fromisoformat(health_data["timestamp"].replace("Z", "+00:00"))

        # Check service timestamps
        if status_data["services"]:
            service = status_data["services"][0]
            if service.get("started_at"):
                datetime.fromisoformat(service["started_at"].replace("Z", "+00:00"))


class TestIntegrationScenarios:
    """Test integration scenarios with real launcher components."""

    @pytest.mark.integration
    def test_end_to_end_integration(self):
        """Test complete integration with actual launcher components - Scenario 24"""
        # This would be implemented in integration tests with real instances
        # For now, we'll mark it as expected to fail until GREEN phase
        pytest.skip("Integration test - requires real launcher instances")
