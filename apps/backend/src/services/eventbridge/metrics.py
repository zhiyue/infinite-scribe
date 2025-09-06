"""
Metrics collector for EventBridge service.

This module implements centralized metrics collection and reporting for the EventBridge
service, providing observability and health monitoring capabilities.
"""

import logging
from typing import Any

from src.services.eventbridge.circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger(__name__)


class EventBridgeMetricsCollector:
    """
    Centralized metrics collector for EventBridge operations.

    Tracks and reports processing metrics including:
    - Event counts (consumed, published, dropped, filtered)
    - Success rates and failure rates
    - Circuit breaker status
    - Health status calculations
    """

    def __init__(self, circuit_breaker: CircuitBreaker):
        """
        Initialize metrics collector.

        Args:
            circuit_breaker: Circuit breaker for failure rate monitoring
        """
        self.circuit_breaker = circuit_breaker
        
        # Processing counters
        self.events_consumed = 0
        self.events_published = 0
        self.events_dropped = 0
        self.events_filtered = 0

    def record_event_consumed(self) -> None:
        """Record an event was consumed from Kafka."""
        self.events_consumed += 1

    def record_event_published(self) -> None:
        """Record an event was successfully published to SSE."""
        self.events_published += 1

    def record_event_dropped(self) -> None:
        """Record an event was dropped due to circuit breaker or errors."""
        self.events_dropped += 1

    def record_event_filtered(self) -> None:
        """Record an event was filtered out during validation."""
        self.events_filtered += 1

    def maybe_log_periodic_metrics(self, envelope: dict[str, Any], message: Any) -> None:
        """
        Log metrics periodically for observability.

        Args:
            envelope: Event envelope for context
            message: Kafka message for context
        """
        if self.events_consumed % 100 == 0:  # Log every 100 events
            circuit_state = self.circuit_breaker.get_state()
            failure_rate = self.circuit_breaker.get_failure_rate()

            logger.info(
                f"EventBridge metrics: consumed={self.events_consumed}, "
                f"published={self.events_published}, dropped={self.events_dropped}, "
                f"filtered={self.events_filtered}, circuit_state={circuit_state.value}, "
                f"failure_rate={failure_rate:.2%}"
            )

    def log_final_metrics(self) -> None:
        """Log final processing metrics on shutdown."""
        circuit_state = self.circuit_breaker.get_state()
        failure_rate = self.circuit_breaker.get_failure_rate()

        logger.info(
            f"Final EventBridge metrics: "
            f"consumed={self.events_consumed}, "
            f"published={self.events_published}, "
            f"dropped={self.events_dropped}, "
            f"filtered={self.events_filtered}, "
            f"circuit_state={circuit_state.value}, "
            f"failure_rate={failure_rate:.2%}"
        )

    def get_health_status(self) -> dict[str, Any]:
        """
        Calculate current health status based on metrics.

        Returns:
            Health status dictionary with metrics and health indicators
        """
        circuit_state = self.circuit_breaker.get_state()
        failure_rate = self.circuit_breaker.get_failure_rate()

        # Determine overall health
        is_healthy = (
            circuit_state != CircuitState.OPEN and 
            failure_rate < 0.8  # Consider unhealthy if >80% failure rate
        )

        # Calculate publish success rate
        eligible_events = max(self.events_consumed - self.events_filtered, 1)
        publish_success_rate = (
            self.events_published / eligible_events
            if self.events_consumed > self.events_filtered
            else 1.0
        )

        return {
            "healthy": is_healthy,
            "circuit_state": circuit_state.value,
            "failure_rate": failure_rate,
            "events_consumed": self.events_consumed,
            "events_published": self.events_published,
            "events_dropped": self.events_dropped,
            "events_filtered": self.events_filtered,
            "publish_success_rate": publish_success_rate,
        }

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get current metrics summary for monitoring.

        Returns:
            Dictionary with current metric values
        """
        return {
            "events_consumed": self.events_consumed,
            "events_published": self.events_published,
            "events_dropped": self.events_dropped,
            "events_filtered": self.events_filtered,
        }