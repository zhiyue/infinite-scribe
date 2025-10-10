#!/usr/bin/env python3
"""
SSE Monitoring Example

This script demonstrates how to use the new SSE monitoring features
for production monitoring and alerting.
"""

import asyncio
import json
from datetime import datetime

from src.services.sse.provider import SSEProvider


async def get_sse_monitoring_report():
    """
    Example of how to get comprehensive SSE monitoring data
    for dashboard integration and alerting.
    """
    # Get SSE service (assumes it's already initialized)
    provider = SSEProvider()
    manager = await provider.get_connection_manager()

    if not manager:
        print("SSE service not initialized")
        return

    # Get detailed monitoring statistics
    monitoring_data = await manager.get_detailed_monitoring_stats()

    # Pretty print the monitoring data
    print("=== SSE Service Monitoring Report ===")
    print(f"Timestamp: {monitoring_data['timestamp']}")
    print(f"Service: {monitoring_data['service_name']}")
    print()

    # Connection Statistics
    conn_stats = monitoring_data["connection_stats"]
    print("📊 Connection Statistics:")
    print(f"  Active Connections: {conn_stats['active_connections']}")
    print(f"  Redis Counters: {conn_stats['redis_connection_counters']}")
    print(f"  Cleanup Running: {'✅' if conn_stats['cleanup_task_running'] else '❌'}")
    print()

    # Cleanup Statistics
    cleanup_stats = monitoring_data["cleanup_stats"]
    print("🧹 Cleanup Statistics:")
    print(f"  Total Cleanups: {cleanup_stats['total_cleanups']}")
    print(f"  Connections Cleaned: {cleanup_stats['total_connections_cleaned']}")
    print(f"  Error Rate: {cleanup_stats['error_rate']:.1f}%")
    print(f"  Failed Connections: {cleanup_stats.get('failed_connections', 0)}")
    print(f"  Connection Failure Rate: {cleanup_stats.get('connection_failure_rate', 0.0):.1f}%")
    print(f"  Last Duration: {cleanup_stats['last_cleanup_duration_ms']:.2f}ms")
    print(f"  Connections per Cleanup: {cleanup_stats['connections_per_cleanup']:.1f}")
    print()

    # Connection Age Analysis
    print("📈 Connection Age Analysis:")
    print(f"  Stale: {cleanup_stats.get('stale', 0)}")
    print(f"  Active: {cleanup_stats.get('active', 0)}")
    print(f"  Long-lived: {cleanup_stats.get('long_lived', 0)}")
    print(f"  Very Old (6h+): {cleanup_stats.get('very_old', 0)}")
    print()

    # Health Indicators
    health = monitoring_data["health_indicators"]
    print(f"🏥 Health Status: {health['overall_health'].upper()}")

    # Alerts
    if health["alerts"]:
        print("🚨 ALERTS:")
        for alert in health["alerts"]:
            print(f"  ❗ {alert['type']}: {alert['message']} (severity: {alert['severity']})")

    # Warnings
    if health["warnings"]:
        print("⚠️  WARNINGS:")
        for warning in health["warnings"]:
            print(f"  ⚠️  {warning['type']}: {warning['message']} (severity: {warning['severity']})")

    if not health["alerts"] and not health["warnings"]:
        print("✅ No alerts or warnings")

    print()

    # Performance Metrics
    perf = monitoring_data["performance_metrics"]
    print("⚡ Performance Metrics:")
    print(f"  Avg Cleanup Duration: {perf['avg_cleanup_duration_ms']:.2f}ms")
    print(f"  Cleanup Efficiency: {perf['cleanup_efficiency_rate']:.1f}%")
    print(f"  Cleanup Error Rate: {perf.get('cleanup_error_rate', 0.0):.1f}%")
    print(f"  Connections/Operation: {perf['connections_cleaned_per_operation']:.1f}")
    print()

    # Configuration
    config = monitoring_data["configuration"]
    print("⚙️  Configuration:")
    print(f"  Cleanup Interval: {config['cleanup_interval_seconds']}s")
    print(f"  Batch Size: {config['cleanup_batch_size']}")
    print(f"  Stale Threshold: {config['stale_threshold_seconds']}s")
    print(f"  Periodic Cleanup: {'Enabled' if config['periodic_cleanup_enabled'] else 'Disabled'}")

    return monitoring_data


async def check_sse_health():
    """
    Example health check function for monitoring systems.
    Returns True if service is healthy, False otherwise.
    """
    try:
        provider = SSEProvider()
        manager = await provider.get_connection_manager()

        if not manager:
            return False

        monitoring_data = await manager.get_detailed_monitoring_stats()
        health = monitoring_data["health_indicators"]

        # Service is healthy if no critical alerts
        return health["overall_health"] in ["healthy", "degraded"]

    except Exception as e:
        print(f"Health check failed: {e}")
        return False


async def generate_alerting_metrics():
    """
    Example function to generate metrics for external monitoring systems
    like Prometheus, Grafana, or CloudWatch.
    """
    provider = SSEProvider()
    manager = await provider.get_connection_manager()

    if not manager:
        return {}

    monitoring_data = await manager.get_detailed_monitoring_stats()

    # Extract key metrics for alerting systems
    metrics = {
        # Connection metrics
        "sse_active_connections": monitoring_data["connection_stats"]["active_connections"],
        "sse_redis_connections": monitoring_data["connection_stats"]["redis_connection_counters"],
        "sse_cleanup_running": 1 if monitoring_data["connection_stats"]["cleanup_task_running"] else 0,
        # Cleanup metrics
        "sse_cleanup_error_rate": monitoring_data["cleanup_stats"]["error_rate"],
        "sse_cleanup_duration_ms": monitoring_data["cleanup_stats"]["last_cleanup_duration_ms"],
        "sse_connections_cleaned_total": monitoring_data["cleanup_stats"]["total_connections_cleaned"],
        # Age metrics
        "sse_stale_connections": monitoring_data["cleanup_stats"].get("stale", 0),
        "sse_long_lived_connections": monitoring_data["cleanup_stats"].get("long_lived", 0),
        "sse_very_old_connections": monitoring_data["cleanup_stats"].get("very_old", 0),
        # Health metrics
        "sse_health_alerts": len(monitoring_data["health_indicators"]["alerts"]),
        "sse_health_warnings": len(monitoring_data["health_indicators"]["warnings"]),
        "sse_health_status": {"healthy": 1, "degraded": 2, "unhealthy": 3}.get(
            monitoring_data["health_indicators"]["overall_health"], 0
        ),
    }

    return metrics


def format_metrics_for_prometheus(metrics: dict) -> str:
    """
    Format metrics in Prometheus exposition format.
    """
    lines = []
    timestamp = int(datetime.now().timestamp() * 1000)

    for metric_name, value in metrics.items():
        lines.append(f"{metric_name} {value} {timestamp}")

    return "\n".join(lines)


async def main():
    """Main monitoring example."""
    print("SSE Monitoring Demo")
    print("=" * 50)

    # Example 1: Get full monitoring report
    await get_sse_monitoring_report()

    print("\n" + "=" * 50)

    # Example 2: Health check
    is_healthy = await check_sse_health()
    print(f"Health Check Result: {'✅ HEALTHY' if is_healthy else '❌ UNHEALTHY'}")

    print("\n" + "=" * 50)

    # Example 3: Generate metrics for external systems
    metrics = await generate_alerting_metrics()
    print("Metrics for External Systems:")
    print(json.dumps(metrics, indent=2))

    print("\n" + "=" * 50)

    # Example 4: Prometheus format
    prometheus_metrics = format_metrics_for_prometheus(metrics)
    print("Prometheus Format:")
    print(prometheus_metrics)


if __name__ == "__main__":
    asyncio.run(main())
