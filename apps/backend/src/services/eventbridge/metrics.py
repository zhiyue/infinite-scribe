"""
EventBridge 服务的指标收集器

本模块实现了 EventBridge 服务的集中化指标收集和报告，
提供可观测性和健康监控功能，并支持可选的 Prometheus 集成。

功能概述:
========

指标收集器跟踪和报告处理指标，包括：
- 事件计数（消费、发布、丢弃、过滤）
- Redis 发布延迟
- 熔断器状态
- 健康状态计算
- 可选的 Prometheus 指标导出

Prometheus 集成:
==============

如果启用，收集器会创建以下 Prometheus 指标：
- eventbridge_events_consumed_total: 消费的事件总数
- eventbridge_events_published_total: 发布的事件总数
- eventbridge_events_dropped_total: 丢弃的事件总数
- eventbridge_events_filtered_total: 过滤的事件总数
- eventbridge_redis_publish_latency_seconds: Redis 发布延迟
- eventbridge_circuit_breaker_state: 熔断器状态
- eventbridge_redis_failure_rate: Redis 故障率

健康状态计算:
============

健康状态基于以下因素：
- 熔断器状态（开启则不健康）
- 故障率（超过 80% 则不健康）
- 发布成功率

周期性日志:
==========

每处理一定数量的事件（默认：100）后，记录周期性指标：
- 事件计数统计
- 当前熔断器状态
- 故障率百分比
- 相关事件和会话 ID

使用示例:
========

```python
# 创建指标收集器
metrics = EventBridgeMetricsCollector(
    circuit_breaker=cb,
    prometheus_enabled=True,
    metrics_log_interval=100
)

# 记录指标
metrics.record_event_consumed()
metrics.record_event_published()
metrics.record_event_dropped("redis_error")

# 获取健康状态
health = metrics.get_health_status()
```

性能考虑:
========

- 指标记录开销最小化
- Prometheus 指标按需创建
- 周期性日志避免日志风暴
- 内存使用优化（仅保存计数器）
"""

from threading import Thread
from typing import Any

from src.core.logging import get_logger
from src.services.eventbridge.circuit_breaker import CircuitBreaker, CircuitState
from src.services.eventbridge.constants import (
    CircuitStateValues,
    EventProcessingDefaults,
    HealthThresholds,
    PrometheusDefaults,
)

logger = get_logger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class EventBridgeMetricsCollector:
    """
    Centralized metrics collector for EventBridge operations.

    Tracks and reports processing metrics including:
    - Event counts (consumed, published, dropped, filtered)
    - Redis publish latency
    - Circuit breaker status
    - Health status calculations
    - Optional Prometheus metrics export
    """

    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        prometheus_enabled: bool = False,
        metrics_log_interval: int = EventProcessingDefaults.METRICS_LOG_INTERVAL.value,
    ):
        """
        Initialize metrics collector.

        Args:
            circuit_breaker: Circuit breaker for failure rate monitoring
            prometheus_enabled: Enable Prometheus metrics collection
            metrics_log_interval: Log metrics every N processed events
        """
        self.circuit_breaker = circuit_breaker
        self.prometheus_enabled = prometheus_enabled and PROMETHEUS_AVAILABLE
        self.metrics_log_interval = metrics_log_interval

        # Processing counters
        self.events_consumed = 0
        self.events_published = 0
        self.events_dropped = 0
        self.events_filtered = 0

        # Initialize Prometheus metrics if available
        if self.prometheus_enabled:
            self._setup_prometheus_metrics()

    def _setup_prometheus_metrics(self) -> None:
        """Setup Prometheus metrics collectors."""
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, skipping metrics setup")
            return

        # Event counters
        self.prom_events_consumed = Counter(
            "eventbridge_events_consumed_total",
            "Total number of events consumed from Kafka",
            ["topic", "partition"],
        )

        self.prom_events_published = Counter(
            "eventbridge_events_published_total",
            "Total number of events published to SSE",
            ["user_id", "event_type"],
        )

        self.prom_events_dropped = Counter(
            "eventbridge_events_dropped_total",
            "Total number of events dropped due to errors or circuit breaker",
            ["reason"],
        )

        self.prom_events_filtered = Counter(
            "eventbridge_events_filtered_total",
            "Total number of events filtered out",
            ["event_type"],
        )

        # Redis publish latency histogram
        self.prom_redis_publish_latency = Histogram(
            "eventbridge_redis_publish_latency_seconds",
            "Time spent publishing events to Redis",
            buckets=PrometheusDefaults.HISTOGRAM_BUCKETS.value,
        )

        # Circuit breaker state gauge
        self.prom_circuit_state = Gauge(
            "eventbridge_circuit_breaker_state",
            "Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
        )

        # Failure rate gauge
        self.prom_failure_rate = Gauge("eventbridge_redis_failure_rate", "Current Redis failure rate")

    def record_event_consumed(self, topic: str | None = None, partition: int | None = None) -> None:
        """
        Record an event was consumed from Kafka.

        Args:
            topic: Kafka topic (for Prometheus labels)
            partition: Kafka partition (for Prometheus labels)
        """
        self.events_consumed += 1

        if self.prometheus_enabled and hasattr(self, "prom_events_consumed"):
            self.prom_events_consumed.labels(
                topic=topic or "unknown",
                partition=str(partition) if partition is not None else "unknown",
            ).inc()

    def record_event_published(self, user_id: str | None = None, event_type: str | None = None) -> None:
        """
        Record an event was successfully published to SSE.

        Args:
            user_id: User ID (for Prometheus labels)
            event_type: Event type (for Prometheus labels)
        """
        self.events_published += 1

        if self.prometheus_enabled and hasattr(self, "prom_events_published"):
            self.prom_events_published.labels(user_id=user_id or "unknown", event_type=event_type or "unknown").inc()

    def record_event_dropped(self, reason: str = "unknown") -> None:
        """
        Record an event was dropped due to circuit breaker or errors.

        Args:
            reason: Reason for dropping (circuit_breaker, redis_error, etc.)
        """
        self.events_dropped += 1

        if self.prometheus_enabled and hasattr(self, "prom_events_dropped"):
            self.prom_events_dropped.labels(reason=reason).inc()

    def record_event_filtered(self, event_type: str | None = None) -> None:
        """
        Record an event was filtered out during validation.

        Args:
            event_type: Event type that was filtered
        """
        self.events_filtered += 1

        if self.prometheus_enabled and hasattr(self, "prom_events_filtered"):
            self.prom_events_filtered.labels(event_type=event_type or "unknown").inc()

    def record_redis_publish_latency(self, latency_seconds: float) -> None:
        """
        Record Redis publish latency.

        Args:
            latency_seconds: Time taken to publish to Redis in seconds
        """
        if self.prometheus_enabled and hasattr(self, "prom_redis_publish_latency"):
            self.prom_redis_publish_latency.observe(latency_seconds)

    def update_circuit_state_metric(self) -> None:
        """Update circuit breaker state and failure rate metrics."""
        if self.prometheus_enabled:
            if hasattr(self, "prom_circuit_state"):
                circuit_state = self.circuit_breaker.get_state()
                state_value = {
                    CircuitState.CLOSED: CircuitStateValues.CLOSED.value,
                    CircuitState.OPEN: CircuitStateValues.OPEN.value,
                    CircuitState.HALF_OPEN: CircuitStateValues.HALF_OPEN.value,
                }.get(circuit_state, 0)
                self.prom_circuit_state.set(state_value)

            if hasattr(self, "prom_failure_rate"):
                failure_rate = self.circuit_breaker.get_failure_rate()
                self.prom_failure_rate.set(failure_rate)

    def maybe_log_periodic_metrics(self, envelope: dict[str, Any], message: Any) -> None:
        """
        Log metrics periodically for observability.

        Args:
            envelope: Event envelope for context
            message: Kafka message for context
        """
        if self.events_consumed % self.metrics_log_interval == 0:
            circuit_state = self.circuit_breaker.get_state()
            failure_rate = self.circuit_breaker.get_failure_rate()

            # Update Prometheus metrics
            self.update_circuit_state_metric()

            logger.info(
                "EventBridge periodic metrics",
                events_consumed=self.events_consumed,
                events_published=self.events_published,
                events_dropped=self.events_dropped,
                events_filtered=self.events_filtered,
                circuit_state=circuit_state.value,
                failure_rate=f"{failure_rate:.2%}",
                event_id=envelope.get("event_id"),
                session_id=envelope.get("session_id"),
                correlation_id=envelope.get("correlation_id"),
            )

    def log_final_metrics(self) -> None:
        """Log final processing metrics on shutdown."""
        circuit_state = self.circuit_breaker.get_state()
        failure_rate = self.circuit_breaker.get_failure_rate()

        # Update Prometheus metrics one final time
        self.update_circuit_state_metric()

        logger.info(
            "Final EventBridge metrics",
            events_consumed=self.events_consumed,
            events_published=self.events_published,
            events_dropped=self.events_dropped,
            events_filtered=self.events_filtered,
            circuit_state=circuit_state.value,
            failure_rate=f"{failure_rate:.2%}",
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
        is_healthy = circuit_state != CircuitState.OPEN and failure_rate < HealthThresholds.FAILURE_RATE_UNHEALTHY.value

        # Calculate publish success rate
        eligible_events = max(self.events_consumed - self.events_filtered, 1)
        publish_success_rate = (
            self.events_published / eligible_events if self.events_consumed > self.events_filtered else 1.0
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
            "prometheus_enabled": self.prometheus_enabled,
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
            "prometheus_enabled": self.prometheus_enabled,
        }


class PrometheusMetricsServer:
    """
    Manages Prometheus metrics HTTP server.
    """

    def __init__(self, host: str = PrometheusDefaults.HOST.value, port: int = PrometheusDefaults.PORT.value):
        """
        Initialize Prometheus metrics server.

        Args:
            host: Host to bind the metrics server
            port: Port to bind the metrics server
        """
        self.host = host
        self.port = port
        self._server_thread: Thread | None = None

    def start(self) -> bool:
        """
        Start the Prometheus metrics HTTP server.

        Returns:
            True if server started successfully, False otherwise
        """
        if not PROMETHEUS_AVAILABLE:
            logger.warning("Prometheus client not available, cannot start metrics server")
            return False

        try:
            # Start the HTTP server in a separate thread
            self._server_thread = Thread(target=start_http_server, args=(self.port, self.host), daemon=True)
            self._server_thread.start()

            logger.info(
                "Prometheus metrics server started",
                host=self.host,
                port=self.port,
                metrics_url=f"http://{self.host}:{self.port}/metrics",
            )
            return True

        except Exception as e:
            logger.error("Failed to start Prometheus metrics server", error=str(e))
            return False

    def is_running(self) -> bool:
        """Check if the metrics server is running."""
        return self._server_thread is not None and self._server_thread.is_alive()
