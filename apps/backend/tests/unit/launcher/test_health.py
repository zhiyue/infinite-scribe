"""Unit tests for health monitoring functionality"""

import time
from unittest.mock import Mock, patch

import httpx
import pytest
from src.launcher.health import HealthCheckResult, HealthMonitor, HealthStatus
from src.launcher.types import ServiceDefinition


class TestHealthMonitor:
    """HealthMonitor test suite"""

    @pytest.fixture
    def monitor(self):
        """Create default monitor instance"""
        return HealthMonitor(check_interval=1.0)

    @pytest.fixture
    def sample_service(self):
        """Create sample service definition"""
        return ServiceDefinition(
            name="api-gateway",
            service_type="fastapi",
            module_path="api.main",
            dependencies=[],
            health_check_url="http://localhost:8000/health",
        )

    @pytest.mark.asyncio
    async def test_health_check_result_creation(self):
        """Test HealthCheckResult creation"""
        service_name = "api-gateway"
        status = HealthStatus.HEALTHY
        response_time = 25.5
        timestamp = time.time()

        result = HealthCheckResult(
            service_name=service_name,
            status=status,
            response_time_ms=response_time,
            timestamp=timestamp,
            details={"version": "1.0.0", "uptime": 3600},
        )

        assert result.service_name == service_name
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 25.5
        assert result.details is not None
        assert result.details["version"] == "1.0.0"
        assert result.error is None

    def test_valid_check_intervals(self):
        """Test valid check intervals"""
        # Default 1Hz
        monitor1 = HealthMonitor()
        assert monitor1.check_interval == 1.0

        # Maximum 20Hz
        monitor2 = HealthMonitor(check_interval=0.05)
        assert monitor2.check_interval == 0.05

        # Boundary value
        monitor3 = HealthMonitor(check_interval=1.0)
        assert monitor3.check_interval == 1.0

    def test_invalid_check_intervals(self):
        """Test invalid check intervals are rejected"""
        # Too high frequency (>20Hz)
        with pytest.raises(ValueError, match="check_interval must be between"):
            HealthMonitor(check_interval=0.04)

        # Too low frequency (<1Hz)
        with pytest.raises(ValueError, match="check_interval must be between"):
            HealthMonitor(check_interval=1.5)

    @pytest.mark.asyncio
    async def test_http_health_check_success(self):
        """Test HTTP health check success (200 OK)"""
        monitor = HealthMonitor(check_interval=1.0)
        service_name = "api-gateway"
        url = "http://localhost:8000/health"
        expected_json = {"status": "ok", "version": "1.0.0"}

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected_json
            mock_response.headers = {"content-type": "application/json"}
            mock_get.return_value = mock_response

            result = await monitor._check_http_health(service_name, url)

            assert result.service_name == service_name
            assert result.status == HealthStatus.HEALTHY
            assert result.response_time_ms > 0  # Response time is positive
            assert result.details == expected_json
            assert result.error is None
            assert isinstance(result.timestamp, float)

    @pytest.mark.asyncio
    async def test_http_health_check_500_error(self):
        """Test HTTP health check failure (500 error)"""
        monitor = HealthMonitor(check_interval=1.0)
        service_name = "api-gateway"
        url = "http://localhost:8000/health"

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            result = await monitor._check_http_health(service_name, url)

            assert result.status == HealthStatus.UNHEALTHY
            assert result.error == "HTTP 500"
            assert result.details is None

    @pytest.mark.asyncio
    async def test_http_health_check_timeout(self):
        """Test HTTP health check timeout"""
        monitor = HealthMonitor(check_interval=1.0)
        service_name = "api-gateway"
        url = "http://localhost:8000/health"

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            result = await monitor._check_http_health(service_name, url, timeout=1.0)

            assert result.status == HealthStatus.UNHEALTHY
            assert result.error is not None
            assert "timeout" in result.error.lower()
            assert result.response_time_ms > 0  # Records attempt time

    @pytest.mark.asyncio
    async def test_subscription_notification_on_state_change(self):
        """Test subscription notification on health state changes"""
        monitor = HealthMonitor()
        notifications = []

        async def callback(result: HealthCheckResult):
            notifications.append(result)

        monitor.subscribe(callback)

        result1 = HealthCheckResult(
            service_name="api", status=HealthStatus.HEALTHY, response_time_ms=10.0, timestamp=time.time()
        )

        result2 = HealthCheckResult(
            service_name="api", status=HealthStatus.UNHEALTHY, response_time_ms=5000.0, timestamp=time.time()
        )

        # First notification (no previous result)
        await monitor._notify_subscribers(result1, None)
        # State change notification
        await monitor._notify_subscribers(result2, result1)
        # No change, should not notify
        await monitor._notify_subscribers(result2, result2)

        assert len(notifications) == 2  # Only first two trigger notifications
        assert notifications[0].status == HealthStatus.HEALTHY
        assert notifications[1].status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_subscription_callback_exception_isolation(self):
        """Test callback exception doesn't affect other subscribers"""
        monitor = HealthMonitor()
        callback2_calls = []

        async def callback1(result):
            raise ValueError("Callback1 failed")

        async def callback2(result):
            callback2_calls.append(result)

        monitor.subscribe(callback1)
        monitor.subscribe(callback2)

        result = HealthCheckResult("api", HealthStatus.HEALTHY, 10.0, time.time())

        # Should not raise exception
        await monitor._notify_subscribers(result, None)

        assert len(callback2_calls) == 1  # callback2 executed normally

    def test_subscribe_requires_async_callback(self):
        """Test subscribe requires async callback function"""
        monitor = HealthMonitor()

        def sync_callback(result: HealthCheckResult):
            pass

        with pytest.raises(TypeError, match="Callback must be an async function"):
            monitor.subscribe(sync_callback)

    def test_cluster_health_aggregation(self):
        """Test cluster health status aggregation"""
        monitor = HealthMonitor()

        monitor.health_cache = {
            "api": HealthCheckResult("api", HealthStatus.HEALTHY, 10.0, time.time()),
            "agent1": HealthCheckResult("agent1", HealthStatus.DEGRADED, 100.0, time.time()),
            "agent2": HealthCheckResult("agent2", HealthStatus.HEALTHY, 15.0, time.time()),
        }

        cluster_health = monitor.get_cluster_health()
        cluster_status = monitor.get_cluster_status()

        assert len(cluster_health) == 3
        assert cluster_health["api"].status == HealthStatus.HEALTHY
        assert cluster_health["agent1"].status == HealthStatus.DEGRADED
        assert cluster_status == HealthStatus.DEGRADED  # Returns worst status

    def test_empty_cluster_returns_unknown(self):
        """Test empty cluster returns UNKNOWN status"""
        monitor = HealthMonitor()
        monitor.health_cache = {}

        assert monitor.get_cluster_status() == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self):
        """Test monitoring start/stop lifecycle"""
        monitor = HealthMonitor(check_interval=0.1)

        # Start monitoring
        await monitor.start_monitoring()
        assert monitor._monitoring_task is not None
        assert not monitor._monitoring_task.done()

        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor._monitoring_task is None
        assert monitor._http_client is None
