"""Admin launcher management endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from src.api.models.launcher import HealthSummaryItem, HealthSummaryResponse, LauncherStatusResponse, ServiceStatusItem
from src.core.config import Settings, get_settings
from src.launcher.health import HealthMonitor, HealthStatus
from src.launcher.orchestrator import Orchestrator
from src.launcher.types import ServiceStatus


def require_admin_access(settings: Settings = Depends(get_settings)) -> bool:
    """Require admin access based on environment settings."""
    if settings.environment == "production":
        # Check if admin endpoints are explicitly enabled in production
        if not getattr(settings, "launcher", None) or not getattr(settings.launcher, "admin_enabled", False):
            raise HTTPException(status_code=404, detail="Admin endpoints not available")
    return True


router = APIRouter(prefix="/admin/launcher", tags=["launcher-admin"], dependencies=[Depends(require_admin_access)])


# Global singletons for launcher components
_orchestrator_instance: Orchestrator | None = None
_health_monitor_instance: HealthMonitor | None = None


def get_orchestrator() -> Orchestrator:
    """Get orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        # For minimal implementation, create a basic orchestrator
        # In real implementation, this would get the actual running instance
        from src.launcher.config import LauncherConfigModel

        _orchestrator_instance = Orchestrator(LauncherConfigModel())
    return _orchestrator_instance


def get_health_monitor() -> HealthMonitor:
    """Get health monitor instance."""
    global _health_monitor_instance
    if _health_monitor_instance is None:
        # For minimal implementation, create a basic health monitor
        _health_monitor_instance = HealthMonitor(check_interval=1.0)
    return _health_monitor_instance


@router.get("/status", response_model=LauncherStatusResponse)
async def get_launcher_status() -> LauncherStatusResponse:
    """Get launcher and service status."""
    try:
        orchestrator = get_orchestrator()
        # Get all service states from orchestrator
        service_states = orchestrator.get_all_service_states()

        # Convert to response format
        services = []
        running_count = 0

        for service_name, state_info in service_states.items():
            status_str = _map_service_state(state_info["state"])
            if status_str == "running":
                running_count += 1

            service_item = ServiceStatusItem(
                name=service_name,
                status=status_str,
                uptime_seconds=state_info.get("uptime", 0),
                started_at=state_info.get("started_at"),
                pid=state_info.get("pid"),
                port=state_info.get("port"),
            )
            services.append(service_item)

        # Determine overall launcher status
        total_services = len(services)
        if total_services == 0:
            launcher_status = "stopped"
        elif running_count == total_services:
            launcher_status = "running"
        elif running_count > 0:
            launcher_status = "partial"
        elif any(s.status == "starting" for s in services):
            launcher_status = "starting"
        else:
            launcher_status = "stopped"

        return LauncherStatusResponse(
            launcher_status=launcher_status,
            services=services,
            total_services=total_services,
            running_services=running_count,
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/health", response_model=HealthSummaryResponse)
async def get_launcher_health() -> HealthSummaryResponse:
    """Get cluster health summary."""
    try:
        health_monitor = get_health_monitor()
        # Get cluster health status
        cluster_health = health_monitor.get_cluster_health()
        cluster_status = health_monitor.get_cluster_status()

        # Convert to response format
        services = []
        healthy_count = 0

        for service_name, health_result in cluster_health.items():
            if health_result.status == HealthStatus.HEALTHY:
                healthy_count += 1

            health_item = HealthSummaryItem(
                service_name=service_name,
                status=health_result.status.value,
                response_time_ms=health_result.response_time_ms,
                last_check=datetime.fromtimestamp(health_result.timestamp, UTC).isoformat().replace("+00:00", "Z"),
                error=health_result.error,
            )
            services.append(health_item)

        return HealthSummaryResponse(
            cluster_status=cluster_status.value,
            services=services,
            healthy_count=healthy_count,
            total_count=len(services),
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Service unavailable")


def _map_service_state(state: ServiceStatus) -> str:
    """Map internal service state to API response format."""
    mapping = {
        ServiceStatus.RUNNING: "running",
        ServiceStatus.STARTING: "starting",
        ServiceStatus.STOPPING: "stopping",
        ServiceStatus.STOPPED: "stopped",
        ServiceStatus.FAILED: "error",
        ServiceStatus.DEGRADED: "degraded",
    }
    return mapping.get(state, "unknown")
