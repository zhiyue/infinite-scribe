"""Health monitoring and checking for launched services"""

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import structlog


class HealthStatus(Enum):
    """Health status enumeration"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

    @classmethod
    def worst_of(cls, statuses: list["HealthStatus"]) -> "HealthStatus":
        """Return the worst status from a list (for cluster aggregation)"""
        if not statuses:
            return cls.UNKNOWN

        # Priority order: UNHEALTHY > DEGRADED > UNKNOWN > HEALTHY
        priority_order = [cls.UNHEALTHY, cls.DEGRADED, cls.UNKNOWN, cls.HEALTHY]
        for status in priority_order:
            if status in statuses:
                return status
        return cls.HEALTHY


@dataclass
class HealthCheckResult:
    """Health check result"""

    service_name: str
    status: HealthStatus
    response_time_ms: float
    timestamp: float
    details: dict[str, Any] | None = None
    error: str | None = None


class HealthMonitor:
    """Monitor health of launched services"""

    def __init__(self, check_interval: float = 1.0):
        """Initialize the health monitor
        :param check_interval: Health check interval (seconds), 0.1-60.0s range
        """
        if not 0.1 <= check_interval <= 60.0:
            raise ValueError("check_interval must be between 0.1 and 60.0 seconds")

        self.check_interval = check_interval
        self.services: dict[str, Any] = {}  # ServiceDefinition objects
        self.health_cache: dict[str, HealthCheckResult] = {}
        self.subscribers: list[Callable[[HealthCheckResult], Awaitable[None]]] = []
        self._monitoring_task: asyncio.Task | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._log = structlog.get_logger(__name__)
        self._elapsed_ms = 0.0

    @asynccontextmanager
    async def _timed_operation(self):
        """Context manager to track operation timing"""
        start_time = time.time()
        try:
            yield
        finally:
            self._elapsed_ms = (time.time() - start_time) * 1000

    def _has_valid_health_url(self, service_name: str) -> bool:
        """Check if service has a valid health check URL"""
        service = self.services.get(service_name)
        return service is not None and getattr(service, "health_check_url", None) is not None

    def _determine_status_from_response(
        self, response: httpx.Response
    ) -> tuple[HealthStatus, dict[str, Any] | None, str | None]:
        """Determine health status from HTTP response"""
        if response.status_code != 200:
            return HealthStatus.UNHEALTHY, None, f"HTTP {response.status_code}"

        # Success case
        details = None
        if response.headers.get("content-type", "").startswith("application/json"):
            details = response.json()

        return HealthStatus.HEALTHY, details, None

    async def _check_http_health(
        self,
        service_name: str,
        url: str,
        timeout: float = 5.0,
    ) -> HealthCheckResult:
        """Execute HTTP health check"""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=timeout)

        status = HealthStatus.UNHEALTHY
        details = None
        error = None

        try:
            async with self._timed_operation():
                response = await self._http_client.get(url, timeout=timeout)
                status, details, error = self._determine_status_from_response(response)
        except httpx.TimeoutException:
            error = "Request timeout"
        except Exception as e:
            error = str(e)

        return HealthCheckResult(
            service_name=service_name,
            status=status,
            response_time_ms=self._elapsed_ms,
            timestamp=time.time(),
            details=details,
            error=error,
        )

    def add_service(self, service) -> None:
        """Add a service to monitor"""
        self.services[service.name] = service

    def remove_service(self, service_name: str) -> None:
        """Remove a service from monitoring"""
        self.services.pop(service_name, None)
        self.health_cache.pop(service_name, None)

    async def check_health(self, service_name: str) -> HealthCheckResult:
        """
        Check health of a specific service

        Args:
            service_name: Name of the service to check

        Returns:
            HealthCheckResult: Health check result
        """
        if not self._has_valid_health_url(service_name):
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0.0,
                timestamp=time.time(),
                error="Service not registered or no health_check_url",
            )

        service = self.services[service_name]
        result = await self._check_http_health(service_name, service.health_check_url)
        self.health_cache[service_name] = result
        return result

    async def start_monitoring(self) -> None:
        """Start continuous health monitoring"""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                tasks = []
                for service_name in self.services:
                    if self._has_valid_health_url(service_name):
                        tasks.append(self._check_and_notify(service_name))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error("monitoring_loop_error", error=str(e))
                await asyncio.sleep(self.check_interval)

    async def _check_and_notify(self, service_name: str) -> None:
        """Check service health and notify subscribers"""
        if not self._has_valid_health_url(service_name):
            return

        service = self.services[service_name]
        result = await self._check_http_health(service_name, service.health_check_url)
        old_result = self.health_cache.get(service_name)
        self.health_cache[service_name] = result
        await self._notify_subscribers(result, old_result)

    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitoring_task
            self._monitoring_task = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def get_cluster_health(self) -> dict[str, HealthCheckResult]:
        """
        Get health status of all services

        Returns:
            Dict containing health status of all services
        """
        return self.health_cache.copy()

    def get_cluster_status(self) -> HealthStatus:
        """Get overall cluster status (worst status)"""
        statuses = [result.status for result in self.health_cache.values()]
        return HealthStatus.worst_of(statuses)

    def subscribe(self, callback: Callable[[HealthCheckResult], Awaitable[None]]) -> None:
        """
        Subscribe to health status changes

        Args:
            callback: Async function to call when health status changes
        """
        if not asyncio.iscoroutinefunction(callback):
            raise TypeError("Callback must be an async function")
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[HealthCheckResult], Awaitable[None]]) -> None:
        """Unsubscribe from health status changes"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    async def _notify_subscribers(
        self,
        result: HealthCheckResult,
        old_result: HealthCheckResult | None,
    ) -> None:
        """Notify subscribers (only on status changes)"""
        if old_result is None or old_result.status != result.status:
            for callback in self.subscribers:
                try:
                    await callback(result)
                except Exception as e:
                    self._log.error(
                        "health_callback_error",
                        callback=getattr(callback, "__name__", str(callback)),
                        error=str(e),
                    )
