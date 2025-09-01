"""
SSE (Server-Sent Events) service module.

Provides centralized SSE functionality including connection management,
Redis-based event streaming, and configuration.
"""

from .config import SSEConfig, sse_config
from .connection_manager import SSEConnectionManager
from .connection_state import SSEConnectionState, SSEConnectionStateManager
from .event_streamer import SSEEventStreamer
from .redis_client import RedisSSEService
from .redis_counter import RedisCounterService

__all__ = [
    # Configuration
    "SSEConfig",
    "sse_config",
    # Core services
    "SSEConnectionManager",
    "RedisSSEService",
    "SSEEventStreamer",
    # State management
    "SSEConnectionState",
    "SSEConnectionStateManager",
    # Utilities
    "RedisCounterService",
]
