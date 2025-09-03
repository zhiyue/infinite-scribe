"""Base adapter class for service management"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

import structlog

from ..types import ServiceStatus

logger = structlog.get_logger(__name__)


class BaseAdapter(ABC):
    """Abstract base class for service adapters"""

    def __init__(self, name: str, config: dict[str, Any]):
        """
        Initialize the adapter

        Args:
            name: Name of the service/adapter
            config: Configuration dictionary
        """
        self.name = name
        self.config = config
        self.status = ServiceStatus.STOPPED
        self.process: asyncio.subprocess.Process | None = None

        logger.debug("Initialized adapter", name=name, config_keys=list(config.keys()))

    @abstractmethod
    async def start(self) -> bool:
        """
        Start the service

        Returns:
            bool: True if started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def stop(self, timeout: int = 30) -> bool:
        """
        Stop the service

        Args:
            timeout: Graceful shutdown timeout in seconds

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on the service

        Returns:
            dict: Health check result with status and additional info
        """
        pass

    def get_status(self) -> ServiceStatus:
        """
        Get current service status

        Returns:
            ServiceStatus: Current status
        """
        return self.status
