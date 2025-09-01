"""Launcher configuration models"""

import re

from pydantic import BaseModel, Field, field_validator


class LauncherApiConfig(BaseModel):
    """Launcher API configuration"""

    host: str = Field(default="0.0.0.0", description="API server bind address")
    port: int = Field(default=8000, ge=1024, le=65535, description="API server port")
    reload: bool = Field(default=False, description="Development mode hot reload")


class LauncherAgentsConfig(BaseModel):
    """Launcher Agents configuration"""

    names: list[str] | None = Field(default=None, description="List of agent names to start")

    @field_validator("names")
    @classmethod
    def validate_agent_names(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            if len(v) == 0:
                raise ValueError("Agent names list cannot be empty")

            pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
            for name in v:
                if not pattern.match(name):
                    raise ValueError(f"Invalid agent name: {name}")
                if len(name) > 50:
                    raise ValueError(f"Agent name too long: {name}")
        return v
