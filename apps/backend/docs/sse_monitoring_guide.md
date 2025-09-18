# SSE Monitoring Guide

## Overview

This guide explains the comprehensive monitoring features added to the SSE (Server-Sent Events) service for production observability, alerting, and performance optimization.

## Features Added

### 1. Performance Monitoring

#### Cleanup Duration Tracking
- Measures time taken for each cleanup operation
- Tracks cleanup efficiency (success rate)
- Records batch processing metrics

#### Connection Age Analysis
- **Stale**: Connections past activity threshold
- **Active**: Connections with recent activity
- **Long-lived**: Connections active for >1 hour
- **Very Old**: Connections older than 6 hours

#### Error Rate Monitoring
- Tracks cleanup operation failures
- Calculates error rate percentages
- Monitors consecutive error counts

### 2. Health Indicators

#### Alert Conditions (High Severity)
- **Connection Mismatch**: Large gap between active and Redis connections
- **High Cleanup Error Rate**: >10% cleanup failures
- **Cleanup Not Running**: Periodic cleanup disabled when it should be running

#### Warning Conditions (Medium Severity)
- **High Connection Count**: >1000 active connections
- **Elevated Error Rate**: 5-10% cleanup failures
- **Stale Connection Accumulation**: >50 stale connections
- **Very Old Connections**: >10 connections older than 6 hours

#### Health Status Levels
- **Healthy**: No issues detected
- **Degraded**: Warnings present, service functional
- **Unhealthy**: Critical alerts present

### 3. Configuration Validation

#### Automatic Validation on Startup
- Cleanup interval optimization checks
- Batch size validation
- Threshold relationship validation
- Ping interval compatibility checks

#### Warning Conditions
- Cleanup interval too short (<10s) or too long (>300s)
- Batch size too small (<1) or too large (>100)
- Stale threshold less than 2x cleanup interval
- Stale threshold less than 3x ping interval

## Usage Examples

### Basic Monitoring

```python
from src.services.sse.provider import SSEProvider

# Get SSE manager
provider = SSEProvider()
manager = await provider.get_connection_manager()

# Get comprehensive monitoring data
monitoring_data = await manager.get_detailed_monitoring_stats()

# Check health status
health = monitoring_data['health_indicators']
is_healthy = health['overall_health'] == 'healthy'
```

### Dashboard Integration

```python
# Get metrics for external monitoring systems
async def get_prometheus_metrics():
    manager = await provider.get_connection_manager()
    stats = await manager.get_detailed_monitoring_stats()

    return {
        'sse_active_connections': stats['connection_stats']['active_connections'],
        'sse_cleanup_error_rate': stats['cleanup_stats']['error_rate'],
        'sse_health_alerts': len(stats['health_indicators']['alerts']),
    }
```

### Health Check Endpoint

```python
async def health_check():
    """Simple health check for load balancers."""
    try:
        manager = await provider.get_connection_manager()
        stats = await manager.get_detailed_monitoring_stats()

        # Service is healthy if no critical alerts
        return stats['health_indicators']['overall_health'] in ['healthy', 'degraded']
    except Exception:
        return False
```

## Monitoring Data Structure

### Complete Monitoring Response

```json
{
  "timestamp": "2025-01-20T10:30:00Z",
  "service_name": "sse_connection_manager",
  "connection_stats": {
    "active_connections": 150,
    "redis_connection_counters": 148,
    "cleanup_task_running": true
  },
  "cleanup_stats": {
    "total_cleanups": 45,
    "total_connections_cleaned": 89,
    "cleanup_errors": 1,
    "failed_connections": 3,
    "error_rate": 2.2,
    "connection_failure_rate": 3.3,
    "last_cleanup_duration_ms": 12.5,
    "connections_per_cleanup": 1.98,
    "stale": 2,
    "active": 148,
    "long_lived": 45,
    "very_old": 3
  },
  "health_indicators": {
    "overall_health": "healthy",
    "alerts": [],
    "warnings": [
      {
        "type": "very_old_connections",
        "message": "Connections older than 6 hours detected: 3",
        "severity": "medium",
        "value": 3
      }
    ]
  },
  "performance_metrics": {
    "avg_cleanup_duration_ms": 12.5,
    "cleanup_efficiency_rate": 96.7,
    "cleanup_error_rate": 2.2,
    "connections_cleaned_per_operation": 1.98
  },
  "configuration": {
    "cleanup_interval_seconds": 60,
    "cleanup_batch_size": 10,
    "stale_threshold_seconds": 300,
    "periodic_cleanup_enabled": true
  }
}
```

## Alerting Recommendations

### Critical Alerts
- Health status becomes "unhealthy"
- Cleanup error rate >10%
- Connection mismatch >10 connections
- Periodic cleanup stops running

### Warning Alerts
- Health status becomes "degraded"
- Cleanup error rate >5%
- Stale connections >50
- Very old connections >10

### Performance Alerts
- Cleanup duration >100ms consistently
- Connection count >1000
- Error rate trending upward

## Integration with Monitoring Systems

### Prometheus Integration

```python
# Export metrics in Prometheus format
def export_prometheus_metrics(stats):
    metrics = []

    # Gauge metrics
    metrics.append(f'sse_active_connections {stats["connection_stats"]["active_connections"]}')
    metrics.append(f'sse_cleanup_error_rate {stats["cleanup_stats"]["error_rate"]}')

    # Counter metrics
    metrics.append(f'sse_total_connections_cleaned {stats["cleanup_stats"]["total_connections_cleaned"]}')

    return '\n'.join(metrics)
```

### Grafana Dashboard Queries

```promql
# Active connections over time
sse_active_connections

# Cleanup error rate
rate(sse_cleanup_errors_total[5m]) / rate(sse_cleanup_total[5m]) * 100

# Connection age distribution
sse_stale_connections
sse_long_lived_connections
sse_very_old_connections

# Health status alert
sse_health_status > 1
```

### CloudWatch Integration

```python
import boto3

def send_to_cloudwatch(stats):
    cloudwatch = boto3.client('cloudwatch')

    cloudwatch.put_metric_data(
        Namespace='SSE/ConnectionManager',
        MetricData=[
            {
                'MetricName': 'ActiveConnections',
                'Value': stats['connection_stats']['active_connections'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'CleanupErrorRate',
                'Value': stats['cleanup_stats']['error_rate'],
                'Unit': 'Percent'
            }
        ]
    )
```

## Log Analysis

### Enhanced Log Messages

The monitoring system produces structured log messages for analysis:

```
# Successful cleanup
SSE cleanup completed: cleaned=5, failed=0, total_before=150, total_after=145,
duration_ms=12.50, efficiency=100.0%, batch_size=10, threshold_seconds=300,
stale_connections=5, active_connections=145, long_lived_connections=45

# Periodic cleanup cycle
Periodic cleanup cycle: cleaned=3 connections, cycle_duration_ms=8.30,
total_cleanups=45, total_cleaned=89, error_rate=2.2%

# Configuration validation
SSE configuration validated successfully: cleanup_interval=60s, batch_size=10,
stale_threshold=300s, ping_interval=15s
```

### Log Filtering for Monitoring

```bash
# Find cleanup errors
grep "Error during periodic SSE cleanup" /var/log/app.log

# Monitor cleanup performance
grep "SSE cleanup completed" /var/log/app.log | tail -20

# Check configuration warnings
grep "SSE configuration validation warnings" /var/log/app.log
```

## Performance Tuning

### Configuration Optimization

Based on monitoring data, adjust these settings:

```python
# For high-traffic scenarios
sse_config.CLEANUP_INTERVAL_SECONDS = 30  # More frequent cleanup
sse_config.CLEANUP_BATCH_SIZE = 20        # Larger batches
sse_config.STALE_CONNECTION_THRESHOLD_SECONDS = 180  # Shorter threshold

# For low-traffic scenarios
sse_config.CLEANUP_INTERVAL_SECONDS = 120  # Less frequent cleanup
sse_config.CLEANUP_BATCH_SIZE = 5          # Smaller batches
sse_config.STALE_CONNECTION_THRESHOLD_SECONDS = 600  # Longer threshold
```

### Monitoring-Based Tuning

1. **High Error Rate**: Increase cleanup interval or batch size
2. **Long Cleanup Duration**: Reduce batch size
3. **Stale Connection Accumulation**: Reduce threshold or increase frequency
4. **Too Many Alerts**: Adjust alert thresholds based on baseline metrics

## Troubleshooting

### Common Issues

1. **High Connection Mismatch**
   - Check Redis connectivity
   - Verify counter synchronization
   - Review connection lifecycle

2. **Cleanup Errors**
   - Check network connectivity
   - Review error logs for patterns
   - Verify Redis operations

3. **Performance Degradation**
   - Monitor cleanup duration trends
   - Check system resource usage
   - Review batch size settings

### Debug Commands

```python
# Get detailed cleanup statistics
stats = await manager.state_manager.get_cleanup_statistics()
print(f"Error rate: {stats['error_rate']}%")

# Force cleanup for testing
cleaned = await manager.cleanup_stale_connections(batch_size=5)
print(f"Cleaned {cleaned} connections")

# Check configuration validation
# (Validation runs automatically on startup)
```

## Best Practices

1. **Regular Monitoring**: Check health indicators every 5-15 minutes
2. **Baseline Establishment**: Monitor for 1-2 weeks to establish normal patterns
3. **Alert Tuning**: Adjust thresholds based on observed baselines
4. **Log Retention**: Keep cleanup logs for at least 30 days
5. **Performance Testing**: Test configuration changes in staging first
6. **Capacity Planning**: Monitor trends for connection growth patterns

## See Also

- [SSE Architecture Documentation](./sse_architecture.md)
- [Configuration Reference](./sse_configuration.md)
- [Troubleshooting Guide](./sse_troubleshooting.md)
- [Example Monitoring Script](../src/services/sse/monitoring_example.py)
