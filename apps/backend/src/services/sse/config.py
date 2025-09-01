"""SSE Connection Configuration."""

from dataclasses import dataclass


@dataclass
class SSEConfig:
    """Configuration constants for SSE connection management."""

    # Connection limits
    MAX_CONNECTIONS_PER_USER: int = 2
    CONNECTION_EXPIRY_SECONDS: int = 300
    RETRY_AFTER_SECONDS: int = 30

    # Event streaming
    PING_INTERVAL_SECONDS: int = 15
    SEND_TIMEOUT_SECONDS: int = 30

    # History handling
    MAX_HISTORY_BATCH_SIZE: int = 100
    DEFAULT_HISTORY_LIMIT: int = 50

    # Cleanup
    STALE_CONNECTION_THRESHOLD_SECONDS: int = 300


# Global configuration instance
sse_config = SSEConfig()
