"""Admin launcher management endpoints."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.models.launcher import HealthSummaryItem, HealthSummaryResponse, LauncherStatusResponse, ServiceStatusItem
from src.core.config import Settings, get_settings
from src.launcher.health import HealthMonitor, HealthStatus
from src.launcher.orchestrator import Orchestrator
from src.launcher.types import ServiceStatus

logger = logging.getLogger(__name__)


def require_admin_access(settings: Settings = Depends(get_settings)) -> bool:
    """Require admin access based on environment settings."""
    if settings.environment == "production" and (not getattr(settings, "launcher", None) or not getattr(settings.launcher, "admin_enabled", False)):
        raise HTTPException(status_code=404, detail="Admin endpoints not available")
    return True


router = APIRouter(prefix="/admin/launcher", tags=["launcher-admin"], dependencies=[Depends(require_admin_access)])


def get_orchestrator(request: Request) -> Orchestrator:
    """Get orchestrator instance from application state."""
    orchestrator = getattr(request.app.state, 'orchestrator', None)
    if orchestrator is None:
        logger.error("Orchestrator instance not available - launcher components not initialized")
        raise HTTPException(
            status_code=503,
            detail="Launcher orchestrator service unavailable"
        )
    return orchestrator


def get_health_monitor(request: Request) -> HealthMonitor:
    """Get health monitor instance from application state."""
    health_monitor = getattr(request.app.state, 'health_monitor', None)
    if health_monitor is None:
        logger.error("Health monitor instance not available - launcher components not initialized")
        raise HTTPException(
            status_code=503,
            detail="Launcher health monitor service unavailable"
        )
    return health_monitor


@router.get("/status", response_model=LauncherStatusResponse)
async def get_launcher_status(orchestrator: Orchestrator = Depends(get_orchestrator)) -> LauncherStatusResponse:
    """Get launcher and service status."""
    try:
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
    except Exception as e:
        logger.error(
            "Failed to retrieve launcher status",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "endpoint": "/admin/launcher/status"
            },
            exc_info=True
        )
        raise HTTPException(status_code=503, detail="Service unavailable") from e


@router.get("/health", response_model=HealthSummaryResponse)
async def get_launcher_health(health_monitor: HealthMonitor = Depends(get_health_monitor)) -> HealthSummaryResponse:
    """Get cluster health summary."""
    try:
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
    except Exception as e:
        logger.error(
            "Failed to retrieve cluster health summary",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "endpoint": "/admin/launcher/health"
            },
            exc_info=True
        )
        raise HTTPException(status_code=503, detail="Service unavailable") from e


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
