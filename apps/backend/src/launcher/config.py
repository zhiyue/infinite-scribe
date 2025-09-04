"""Launcher configuration models"""

import re
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from .types import ComponentType, LaunchMode


class LauncherApiConfig(BaseModel):
    """Launcher API configuration"""

    host: str = Field(default="0.0.0.0", description="API server bind address")
    port: int = Field(default=8000, ge=1024, le=65535, description="API server port")
    reload: bool = Field(default=False, description="Development mode hot reload")


class LauncherAgentsConfig(BaseModel):
    """Launcher Agents configuration"""

    # Class-level constants
    MAX_NAME_LENGTH: ClassVar[int] = 50
    NAME_PATTERN: ClassVar[re.Pattern] = re.compile(r"^[a-zA-Z0-9_-]+$")

    names: list[str] | None = Field(default=None, description="List of agent names to start")
    disable_signal_handlers: bool = Field(
        default=False, description="Disable agent signal handlers when managed by external orchestrator"
    )
    ready_timeout: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional readiness wait time (seconds) for agents background startup; 0 or None disables waiting",
    )

    @field_validator("names")
    @classmethod
    def validate_agent_names(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v

        if not v:  # Empty list
            raise ValueError("Agent names list cannot be empty")

        for name in v:
            if not cls.NAME_PATTERN.match(name):
                raise ValueError(f"Invalid agent name: {name}")
            if len(name) > cls.MAX_NAME_LENGTH:
                raise ValueError(f"Agent name too long: {name}")
        return v


class LauncherConfigModel(BaseModel):
    """Main launcher configuration model"""

    default_mode: LaunchMode = Field(default=LaunchMode.SINGLE, description="Default launch mode")
    components: list[ComponentType] = Field(
        default_factory=lambda: [ComponentType.API, ComponentType.AGENTS], description="List of components to start"
    )
    health_interval: float = Field(default=1.0, ge=0.1, le=60.0, description="Health check interval in seconds")
    startup_timeout: int = Field(default=30, ge=1, le=600, description="Per-service startup timeout in seconds")
    stop_grace: int = Field(default=10, ge=0, le=120, description="Graceful shutdown timeout in seconds")
    timeout: int = Field(default=30, ge=5, le=300, description="Operation timeout in seconds")
    admin_enabled: bool = Field(default=False, description="Enable admin endpoints in production environment")
    api: LauncherApiConfig = Field(default_factory=LauncherApiConfig, description="API configuration")
    agents: LauncherAgentsConfig = Field(default_factory=LauncherAgentsConfig, description="Agents configuration")
    dependencies: dict[str, list[str]] | None = Field(
        default=None, description="Optional dependency graph mapping: service -> list of dependencies"
    )

    @field_validator("components")
    @classmethod
    def validate_components(cls, v: list[ComponentType]) -> list[ComponentType]:
        if not v:  # Empty list
            raise ValueError("Components list cannot be empty")

        if len(set(v)) != len(v):  # Check for duplicates
            raise ValueError("Duplicate components are not allowed")

        return v
