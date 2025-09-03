"""Launcher admin endpoint response models."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ServiceStatusItem(BaseModel):
    """Single service status item."""

    name: str = Field(description="Service name")
    status: str = Field(description="Service status: running/starting/stopped/error/degraded")
    uptime_seconds: int = Field(description="Runtime duration in seconds")
    started_at: str | None = Field(default=None, description="Start time in ISO format")
    pid: int | None = Field(default=None, description="Process ID")
    port: int | None = Field(default=None, description="Service port")


class LauncherStatusResponse(BaseModel):
    """Launcher status response."""

    launcher_status: str = Field(description="Overall launcher status")
    services: list[ServiceStatusItem] = Field(description="List of service statuses")
    total_services: int = Field(description="Total number of services")
    running_services: int = Field(description="Number of running services")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"), description="Query timestamp"
    )


class HealthSummaryItem(BaseModel):
    """Health summary item."""

    service_name: str
    status: str  # healthy/unhealthy/degraded/unknown
    response_time_ms: float
    last_check: str
    error: str | None = None


class HealthSummaryResponse(BaseModel):
    """Health summary response."""

    cluster_status: str = Field(description="Overall cluster health status")
    services: list[HealthSummaryItem] = Field(description="Per-service health statuses")
    healthy_count: int = Field(description="Number of healthy services")
    total_count: int = Field(description="Total number of services")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z"), description="Query timestamp"
    )
