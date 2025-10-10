"""
EventBridge Redis 故障的熔断器实现

本模块实现了熔断器模式，通过根据故障率暂停/恢复 Kafka 消费，
来优雅地处理 Redis 故障。

熔断器模式:
==========

熔断器在 Redis 不可用时防止级联故障：

1. 关闭状态：正常操作，所有请求通过
2. 开启状态：快速失败，不向 Redis 发送请求
3. 半开状态：使用有限请求测试恢复

状态转换:
========

关闭 → 开启：当故障率超过阈值（默认：50%）
开启 → 半开：冷却期后（默认：30秒）
半开 → 关闭：请求成功时
半开 → 开启：请求失败时

与 Kafka 消费者集成:
==================

熔断器与 Kafka 消费者集成以：
- 熔断器开启时暂停消费（防止消息积压）
- 熔断器关闭时恢复消费
- 正确处理分区再平衡
- 维护消费者组偏移量

故障率计算:
==========

使用滑动时间窗口（默认：10秒）计算故障率：
- 只考虑窗口内的近期操作
- 状态转换需要最小操作数（默认：2）
- 自动清理旧操作记录

配置:
====

所有参数都可配置，具有合理的默认值：
- window_seconds：故障率计算的时间窗口
- failure_threshold：开启熔断器的故障率（0.0-1.0）
- half_open_interval_seconds：测试恢复前的冷却时间

使用示例:
========

```python
# 创建熔断器
cb = CircuitBreaker(
    window_seconds=10,
    failure_threshold=0.5,
    half_open_interval_seconds=30
)

# 注册 Kafka 消费者
cb.register_consumer(consumer, partitions)

# 在事件处理中使用
if cb.can_attempt():
    try:
        await redis_operation()
        cb.record_success()
    except Exception:
        cb.record_failure()
```

监控:
====

熔断器提供：
- 当前状态（关闭/开启/半开）
- 故障率百分比
- 成功/失败计数
- 状态转换日志
"""

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.core.logging import get_logger
from src.services.eventbridge.constants import CircuitBreakerDefaults

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
        window_seconds: int = CircuitBreakerDefaults.WINDOW_SECONDS.value,
        failure_threshold: float = CircuitBreakerDefaults.FAILURE_THRESHOLD.value,
        half_open_interval_seconds: int = CircuitBreakerDefaults.HALF_OPEN_INTERVAL_SECONDS.value,
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
        # Use deque with maxlen to prevent memory leaks
        max_operations = self.window_seconds * 100  # Assume max 100 ops/sec
        self.operations: deque[OperationRecord] = deque(maxlen=max_operations)

        # Consumer management for pause/resume
        self.consumer = None
        self.partitions: list[Any] | None = None

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
            service="eventbridge",
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

        # Use deque's efficient popleft() for removing old operations
        while self.operations and self.operations[0].timestamp <= cutoff_time:
            self.operations.popleft()

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
            if (
                failure_rate >= self.failure_threshold
                and total_ops >= CircuitBreakerDefaults.MIN_OPERATIONS_FOR_STATE_CHANGE.value
            ):
                self._open_circuit()
        elif (
            self.state == CircuitState.OPEN
            and total_ops >= CircuitBreakerDefaults.MIN_OPERATIONS_FOR_STATE_CHANGE.value
            and failure_rate < self.failure_threshold
        ):
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
            self.operations.clear()
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
