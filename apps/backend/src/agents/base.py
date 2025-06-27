"""Base Agent class for all agent services."""

from abc import ABC, abstractmethod
from typing import Any

from ..core.config import settings


class BaseAgent(ABC):
    """Base class for all agent services."""

    def __init__(self, name: str):
        self.name = name
        self.config = settings

    @abstractmethod
    async def process_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Process incoming message."""
        pass

    @abstractmethod
    async def start(self):
        """Start the agent service."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the agent service."""
        pass
