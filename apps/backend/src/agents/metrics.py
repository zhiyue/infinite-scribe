"""Optional Prometheus metrics for agents (no-op if library unavailable)."""

from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram

    PROCESSING_LATENCY = Histogram(
        "agent_processing_latency_seconds",
        "Time spent processing messages",
        labelnames=("agent",),
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
    )
    ERRORS = Counter("agent_errors_total", "Total errors", labelnames=("agent", "type"))
    DLT = Counter("agent_dlt_total", "Messages sent to DLT", labelnames=("agent",))
    LAG = Gauge("agent_kafka_lag", "Kafka consumer lag (approx)", labelnames=("agent",))

    def record_latency(agent: str, seconds: float) -> None:
        PROCESSING_LATENCY.labels(agent=agent).observe(seconds)

    def inc_error(agent: str, err_type: str) -> None:
        ERRORS.labels(agent=agent, type=err_type).inc()

    def inc_dlt(agent: str) -> None:
        DLT.labels(agent=agent).inc()

    def set_lag(agent: str, value: float) -> None:
        LAG.labels(agent=agent).set(value)

except (ImportError, AttributeError, RuntimeError):  # pragma: no cover - metrics optional
    # Prometheus client unavailable or setup failed
    def record_latency(agent: str, seconds: float) -> None:
        pass

    def inc_error(agent: str, err_type: str) -> None:
        pass

    def inc_dlt(agent: str) -> None:
        pass

    def set_lag(agent: str, value: float) -> None:
        pass
