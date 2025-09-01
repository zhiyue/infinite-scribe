"""Type definitions for launcher module"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LaunchMode(Enum):
    """Launch mode enumeration"""

    SINGLE = "single"  # Single-process mode
    MULTI = "multi"  # Multi-process mode
    AUTO = "auto"  # Auto-detect mode


class ComponentType(Enum):
    """Component type enumeration"""

    API = "api"        # API Gateway
    AGENTS = "agents"  # AI Agents


class LauncherStatus(Enum):
    """Launcher status enumeration"""

    INIT = "init"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceStatus(Enum):
    """Service status enumeration"""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    FAILED = "failed"


# LaunchConfig dataclass removed - use LauncherConfigModel from config.py instead


@dataclass
class ServiceDefinition:
    """Service definition"""

    name: str
    service_type: str  # 'fastapi', 'agent', 'consumer'
    module_path: str
    dependencies: list[str]
    port: int | None = None
    health_check_url: str | None = None
    env_vars: dict[str, str] | None = None
    startup_timeout: int = 30


@dataclass
class LauncherState:
    """Launcher internal state"""

    status: LauncherStatus
    mode: LaunchMode
    services: dict[str, Any]  # Service instances
    config: Any  # LauncherConfigModel - using Any to avoid circular imports
    start_time: float | None = None
    error_info: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "status": self.status.value,
            "mode": self.mode.value,
            "start_time": self.start_time,
            "service_count": len(self.services),
            "error_info": self.error_info,
        }
