"""
Unit tests for CircuitBreaker component.

Tests the circuit breaker pattern implementation for EventBridge Redis failures.
"""

import asyncio
import time
from unittest.mock import Mock

import pytest
from src.services.eventbridge.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """Test CircuitBreaker component for handling Redis failures."""

    def setup_method(self):
        """Setup test fixtures."""
        # Use short windows for testing - make sure half_open_interval <= window_seconds
        self.circuit_breaker = CircuitBreaker(
            window_seconds=5,  # 5 second window for testing
            failure_threshold=0.5,  # 50% failure rate
            half_open_interval_seconds=2,  # 2 seconds between half-open attempts
        )

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker starts in closed state and tracks success."""
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 0
        assert self.circuit_breaker.success_count == 0

        # Record success - should stay closed
        self.circuit_breaker.record_success()
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.success_count == 1

    def test_circuit_breaker_opens_on_failure_threshold(self):
        """Test circuit breaker opens when failure threshold is exceeded."""
        # Record failures that exceed threshold
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()  # 3 failures, 0 successes = 100% failure rate

        assert self.circuit_breaker.state == CircuitState.OPEN
        assert self.circuit_breaker.failure_count == 3

    def test_circuit_breaker_mixed_success_failure(self):
        """Test circuit breaker with mixed success/failure under threshold."""
        # 1 failure, 2 successes = 33% failure rate (under 50% threshold)
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_success()
        self.circuit_breaker.record_success()

        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.failure_count == 1
        assert self.circuit_breaker.success_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker transitions to half-open after interval."""
        # Open the circuit
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()
        assert self.circuit_breaker.state == CircuitState.OPEN

        # Wait for half-open interval (2 seconds in test config)
        await asyncio.sleep(2.1)

        # Should now be eligible for half-open
        assert self.circuit_breaker.can_attempt() is True

        # Try to use it - should transition to half-open
        self.circuit_breaker.record_attempt()
        assert self.circuit_breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_success_closes(self):
        """Test half-open circuit closes on successful operation."""
        # Open the circuit first
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()
        assert self.circuit_breaker.state == CircuitState.OPEN

        # Wait for half-open interval
        await asyncio.sleep(2.1)
        self.circuit_breaker.record_attempt()
        assert self.circuit_breaker.state == CircuitState.HALF_OPEN

        # Success in half-open should close the circuit
        self.circuit_breaker.record_success()
        assert self.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_failure_reopens(self):
        """Test half-open circuit reopens on failed operation."""
        # Create a circuit breaker with shorter interval for this test
        short_cb = CircuitBreaker(
            window_seconds=1,
            failure_threshold=0.5,
            half_open_interval_seconds=1,  # 1 second interval
        )

        # Open the circuit first - record enough failures to exceed threshold
        short_cb.record_failure()
        short_cb.record_failure()
        assert short_cb.state == CircuitState.OPEN

        # Wait for half-open interval
        await asyncio.sleep(1.1)  # Wait a bit more than interval
        short_cb.record_attempt()
        assert short_cb.state == CircuitState.HALF_OPEN

        # Failure in half-open should reopen the circuit
        short_cb.record_failure()
        assert short_cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_consumer_pause_resume(self):
        """Test consumer pause/resume integration."""
        mock_consumer = Mock()
        mock_consumer.pause = Mock()
        mock_consumer.resume = Mock()
        mock_partitions = [Mock(), Mock()]

        # Register consumer
        self.circuit_breaker.register_consumer(mock_consumer, mock_partitions)

        # Open the circuit - should pause consumer
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()
        assert self.circuit_breaker.state == CircuitState.OPEN
        mock_consumer.pause.assert_called_once_with(mock_partitions)

        # Transition to half-open - should resume consumer
        await asyncio.sleep(2.1)
        self.circuit_breaker.record_attempt()
        assert self.circuit_breaker.state == CircuitState.HALF_OPEN
        mock_consumer.resume.assert_called_once_with(mock_partitions)

    def test_circuit_breaker_can_attempt_when_closed(self):
        """Test can_attempt returns True when circuit is closed."""
        assert self.circuit_breaker.state == CircuitState.CLOSED
        assert self.circuit_breaker.can_attempt() is True

    def test_circuit_breaker_cannot_attempt_when_open(self):
        """Test can_attempt returns False when circuit is open."""
        # Open the circuit
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()
        assert self.circuit_breaker.state == CircuitState.OPEN
        assert self.circuit_breaker.can_attempt() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_window_reset(self):
        """Test failure/success counts reset after time window."""
        # Create a circuit breaker with shorter window for this test
        short_window_cb = CircuitBreaker(
            window_seconds=1,  # 1 second window for quick test
            failure_threshold=0.5,
            half_open_interval_seconds=2,
        )

        # Record some failures
        short_window_cb.record_failure()
        assert short_window_cb.failure_count == 1

        # Wait for window to expire with extra margin
        await asyncio.sleep(1.2)  # Window is 1 second, use 1.2 for safety

        # Force cleanup of old operations first
        short_window_cb._clean_old_operations()

        # Verify old failure is cleaned up
        assert short_window_cb.failure_count == 0

        # New operation should only have success
        short_window_cb.record_success()
        assert short_window_cb.success_count == 1
        assert short_window_cb.failure_count == 0
        # Only success operation should remain in window
        assert short_window_cb._calculate_failure_rate() == 0.0

    def test_circuit_breaker_get_state(self):
        """Test get_state returns current circuit state."""
        assert self.circuit_breaker.get_state() == CircuitState.CLOSED

        # Open the circuit
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()
        assert self.circuit_breaker.get_state() == CircuitState.OPEN

    def test_circuit_breaker_get_failure_rate(self):
        """Test get_failure_rate returns current failure rate."""
        # Initially no operations
        assert self.circuit_breaker.get_failure_rate() == 0.0

        # 1 failure, 1 success = 50% failure rate
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_success()
        assert self.circuit_breaker.get_failure_rate() == 0.5

        # 1 failure, 2 successes = 33% failure rate
        self.circuit_breaker.record_success()
        assert abs(self.circuit_breaker.get_failure_rate() - 0.333) < 0.001

    def test_circuit_breaker_configurable_thresholds(self):
        """Test circuit breaker with different configuration values."""
        # Create circuit breaker with 75% threshold
        cb = CircuitBreaker(
            window_seconds=1,
            failure_threshold=0.75,
            half_open_interval_seconds=1,
        )

        # 2 failures, 1 success = 67% failure rate (under 75% threshold)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

        # Add another failure: 3 failures, 1 success = 75% failure rate (at threshold)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_no_consumer_registered(self):
        """Test circuit breaker works without consumer registered."""
        # Should not raise exception when no consumer is registered
        self.circuit_breaker.record_failure()
        self.circuit_breaker.record_failure()
        assert self.circuit_breaker.state == CircuitState.OPEN

        # State transitions should still work
        self.circuit_breaker.record_success()  # Won't close from open, but shouldn't error

    def test_circuit_breaker_memory_leak_fix(self):
        """Test that operations deque doesn't grow beyond max size."""
        # Create circuit breaker with 1-second window
        cb = CircuitBreaker(window_seconds=1)

        # The max size should be window_seconds * 100 = 100
        expected_max_size = 100

        # Add more operations than the max size
        for i in range(200):
            cb.record_success()
            # Small delay to ensure timestamps are different
            time.sleep(0.01)

        # Check that operations size doesn't exceed expected max
        assert (
            len(cb.operations) <= expected_max_size
        ), f"Operations deque grew to {len(cb.operations)}, expected max {expected_max_size}"

        # Wait for window to pass
        time.sleep(1.1)

        # Trigger cleanup
        cb._clean_old_operations()

        # All operations should be cleaned up
        assert len(cb.operations) == 0, f"Operations not cleaned up, size: {len(cb.operations)}"

    def test_circuit_breaker_deque_efficiency(self):
        """Test that deque operations are efficient."""
        cb = CircuitBreaker(window_seconds=10)

        # Add many operations
        start_time = time.time()
        for i in range(1000):
            cb.record_success()
        add_time = time.time() - start_time

        # Should be very fast
        assert add_time < 0.1, f"Adding 1000 operations took {add_time:.3f}s, expected < 0.1s"

        # Clean up should also be fast
        start_time = time.time()
        cb._clean_old_operations()
        cleanup_time = time.time() - start_time

        assert cleanup_time < 0.01, f"Cleanup took {cleanup_time:.3f}s, expected < 0.01s"

    def test_circuit_breaker_deque_clear_method(self):
        """Test that clear() method works properly with deque."""
        cb = CircuitBreaker(window_seconds=10)

        # Add some operations
        cb.record_success()
        cb.record_failure()
        cb.record_success()

        assert len(cb.operations) == 3

        # Clear should empty the deque
        cb.operations.clear()
        assert len(cb.operations) == 0
        assert cb.get_failure_rate() == 0.0
