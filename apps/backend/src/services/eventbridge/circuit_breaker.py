"""
Circuit breaker implementation for EventBridge Redis failures.

This module implements the circuit breaker pattern to handle Redis failures
gracefully by pausing/resuming Kafka consumption based on failure rates.
"""

from src.core.logging import get_logger
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class OperationRecord:
    """Record of an operation with timestamp."""

    timestamp: float
    success: bool


class CircuitBreaker:
    """
    Circuit breaker for Redis failures with Kafka consumer integration.

    Features:
    - Configurable failure rate thresholds
    - Time-based sliding window for failure rate calculation
    - Automatic consumer pause/resume based on circuit state
    - Half-open state for recovery testing
    """

    def __init__(
        self,
        window_seconds: int = 10,
        failure_threshold: float = 0.5,
        half_open_interval_seconds: int = 30,
    ):
        """
        Initialize circuit breaker.

        Args:
            window_seconds: Time window for failure rate calculation
            failure_threshold: Failure rate threshold to open circuit (0.0-1.0)
            half_open_interval_seconds: Interval between half-open attempts
        """
        self.window_seconds = window_seconds
        self.failure_threshold = failure_threshold
        self.half_open_interval_seconds = half_open_interval_seconds

        # State management
        self.state = CircuitState.CLOSED
        self.last_failure_time: float | None = None
        self.last_half_open_time: float | None = None

        # Operation tracking within sliding window
        self.operations: list[OperationRecord] = []

        # Consumer management for pause/resume
        self.consumer = None
        self.partitions = None

    def register_consumer(self, consumer: Any, partitions: list[Any]) -> None:
        """
        Register Kafka consumer for pause/resume operations.

        Args:
            consumer: Kafka consumer instance
            partitions: List of partitions to pause/resume
        """
        self.consumer = consumer
        self.partitions = partitions
        logger.info("Consumer registered with circuit breaker")

    def update_partitions(self, new_partitions: list[Any]) -> None:
        """
        Update partition assignment after Kafka rebalance.
        
        This method handles partition updates when Kafka rebalances the consumer group,
        ensuring that circuit breaker pause/resume operations work with the new assignment.
        
        Args:
            new_partitions: New list of partitions assigned after rebalance
        """
        old_count = len(self.partitions) if self.partitions else 0
        self.partitions = new_partitions
        new_count = len(new_partitions)
        
        logger.info(
            "Circuit breaker partitions updated after rebalance",
            old_partitions_count=old_count,
            new_partitions_count=new_count,
            service="eventbridge"
        )

    def record_success(self) -> None:
        """Record a successful operation."""
        current_time = time.time()
        self._add_operation(current_time, success=True)

        if self.state == CircuitState.HALF_OPEN:
            # Success in half-open state closes the circuit
            self._close_circuit()
        # Always update circuit state to check current failure rate
        self._update_circuit_state()

    def record_failure(self) -> None:
        """Record a failed operation."""
        current_time = time.time()
        self.last_failure_time = current_time
        self._add_operation(current_time, success=False)

        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open state reopens the circuit
            self._open_circuit()
        else:
            # Always check if circuit state should change
            self._update_circuit_state()

    def record_attempt(self) -> None:
        """Record an attempt to use the circuit (for half-open transition)."""
        if self.state == CircuitState.OPEN and self._can_try_half_open():
            self._half_open_circuit()

    def can_attempt(self) -> bool:
        """
        Check if operations can be attempted.

        Returns:
            True if circuit allows operations, False if circuit is open
        """
        if self.state == CircuitState.CLOSED or self.state == CircuitState.HALF_OPEN:
            return True
        elif self.state == CircuitState.OPEN:
            # Don't automatically transition, let caller decide
            return self._can_try_half_open()
        return False

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_failure_rate(self) -> float:
        """Get current failure rate in the time window."""
        return self._calculate_failure_rate()

    @property
    def failure_count(self) -> int:
        """Get current failure count in time window."""
        self._clean_old_operations()
        return sum(1 for op in self.operations if not op.success)

    @property
    def success_count(self) -> int:
        """Get current success count in time window."""
        self._clean_old_operations()
        return sum(1 for op in self.operations if op.success)

    def _add_operation(self, timestamp: float, success: bool) -> None:
        """Add operation record and clean old entries."""
        self.operations.append(OperationRecord(timestamp, success))
        self._clean_old_operations()

    def _clean_old_operations(self) -> None:
        """Remove operations outside the time window."""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        self.operations = [op for op in self.operations if op.timestamp > cutoff_time]

    def _calculate_failure_rate(self) -> float:
        """Calculate current failure rate in the time window."""
        self._clean_old_operations()

        if not self.operations:
            return 0.0

        failures = sum(1 for op in self.operations if not op.success)
        total = len(self.operations)
        return failures / total if total > 0 else 0.0

    def _update_circuit_state(self) -> None:
        """Update circuit state based on current failure rate."""
        failure_rate = self._calculate_failure_rate()
        total_ops = len(self.operations)

        if self.state == CircuitState.CLOSED:
            # Open circuit if failure rate exceeds threshold and we have enough samples
            if failure_rate >= self.failure_threshold and total_ops >= 2:
                self._open_circuit()
        elif self.state == CircuitState.OPEN and total_ops >= 2 and failure_rate < self.failure_threshold:
            # Allow circuit to close if failure rate drops below threshold
            # This is more lenient than traditional circuit breakers
            self._close_circuit(clear_history=False)

    def _open_circuit(self) -> None:
        """Transition to open state and pause consumer."""
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        logger.warning(
            f"Circuit breaker opened - failure rate: {self.get_failure_rate():.2%}, "
            f"threshold: {self.failure_threshold:.2%}"
        )
        self._pause_consumer()

    def _close_circuit(self, clear_history: bool = True) -> None:
        """Transition to closed state and resume consumer."""
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
        self.last_half_open_time = None
        if clear_history:
            # Clear operations to start fresh (for recovery from HALF_OPEN)
            self.operations = []
        logger.info("Circuit breaker closed - service recovered")
        self._resume_consumer()

    def _half_open_circuit(self) -> None:
        """Transition to half-open state and resume consumer for testing."""
        self.state = CircuitState.HALF_OPEN
        self.last_half_open_time = time.time()
        logger.info("Circuit breaker half-open - testing service recovery")
        self._resume_consumer()

    def _can_try_half_open(self) -> bool:
        """Check if enough time has passed to try half-open state."""
        if not self.last_failure_time:
            return False

        current_time = time.time()
        return (current_time - self.last_failure_time) >= self.half_open_interval_seconds

    def _pause_consumer(self) -> None:
        """Pause Kafka consumer if registered."""
        if self.consumer and self.partitions:
            try:
                self.consumer.pause(self.partitions)
                logger.info(f"Paused consumer on {len(self.partitions)} partitions")
            except Exception as e:
                logger.error(f"Failed to pause consumer: {e}")
        else:
            logger.debug("No consumer registered for pause operation")

    def _resume_consumer(self) -> None:
        """Resume Kafka consumer if registered."""
        if self.consumer and self.partitions:
            try:
                self.consumer.resume(self.partitions)
                logger.info(f"Resumed consumer on {len(self.partitions)} partitions")
            except Exception as e:
                logger.error(f"Failed to resume consumer: {e}")
        else:
            logger.debug("No consumer registered for resume operation")
