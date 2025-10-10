"""Agent-specific metrics management."""

from datetime import UTC, datetime
from typing import Any


class AgentMetrics:
    """Manages agent-specific metrics and status tracking."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name

        # Core metrics
        self.metrics: dict[str, int | float] = {
            "consumed": 0,
            "processed": 0,
            "failed": 0,
            "retries": 0,
            "dlt": 0,
            "processing_latency_ms_sum": 0.0,
        }

        # Status tracking
        self.last_message_at: datetime | None = None
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None
        self.lag: int | None = None

    def increment_consumed(self) -> None:
        """Increment consumed message counter."""
        self.metrics["consumed"] = int(self.metrics.get("consumed", 0)) + 1

    def increment_processed(self) -> None:
        """Increment processed message counter."""
        self.metrics["processed"] = int(self.metrics.get("processed", 0)) + 1
        self.last_message_at = datetime.now(UTC)

    def increment_failed(self) -> None:
        """Increment failed message counter."""
        self.metrics["failed"] = int(self.metrics.get("failed", 0)) + 1

    def increment_retries(self) -> None:
        """Increment retry counter."""
        self.metrics["retries"] = int(self.metrics.get("retries", 0)) + 1

    def increment_dlt(self) -> None:
        """Increment DLT counter."""
        self.metrics["dlt"] = int(self.metrics.get("dlt", 0)) + 1

    def record_processing_latency(self, latency_ms: float) -> None:
        """Record processing latency in milliseconds."""
        self.metrics["processing_latency_ms_sum"] = (
            float(self.metrics.get("processing_latency_ms_sum", 0.0)) + latency_ms
        )

    def record_error(self, error: str) -> None:
        """Record error information."""
        self.last_error = error
        self.last_error_at = datetime.now(UTC)

    def clear_error(self) -> None:
        """Clear error state."""
        self.last_error = None
        self.last_error_at = None

    def get_metrics_dict(self) -> dict[str, int | float]:
        """Get current metrics as dictionary."""
        return self.metrics.copy()

    def get_status_dict(self) -> dict[str, Any]:
        """Get current status information."""
        return {
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "lag": self.lag,
        }

    def __getitem__(self, key: str) -> int | float:
        """Backward compatibility: allow dict-style access to metrics."""
        return self.metrics[key]

    def __setitem__(self, key: str, value: int | float) -> None:
        """Backward compatibility: allow dict-style assignment to metrics."""
        self.metrics[key] = value

    def get(self, key: str, default=None):
        """Backward compatibility: dict-style get method."""
        return self.metrics.get(key, default)
