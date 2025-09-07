"""
Constants for EventBridge service.

This module centralizes all magic numbers and configuration constants
used throughout the EventBridge implementation.
"""

from enum import Enum


class CircuitBreakerDefaults(Enum):
    """Default values for circuit breaker configuration."""

    WINDOW_SECONDS = 10
    FAILURE_THRESHOLD = 0.5  # 50% failure rate
    HALF_OPEN_INTERVAL_SECONDS = 30
    MIN_OPERATIONS_FOR_STATE_CHANGE = 2


class HealthThresholds(Enum):
    """Thresholds for health status calculations."""

    FAILURE_RATE_UNHEALTHY = 0.8  # 80% failure rate considered unhealthy


class PrometheusDefaults(Enum):
    """Default values for Prometheus configuration."""

    HOST = "0.0.0.0"
    PORT = 9090
    HISTOGRAM_BUCKETS = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]


class CircuitStateValues(Enum):
    """Numeric values for circuit breaker states."""

    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class EventProcessingDefaults(Enum):
    """Default values for event processing."""

    METRICS_LOG_INTERVAL = 100  # Log metrics every 100 events
