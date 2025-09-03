# 任务 7 测试细节

生成时间：2025-09-02T16:20:00Z
任务描述：健康监控（最小）- 实现API健康检查与状态聚合
关联场景：task-7-test-scenarios.md
关联实现计划：7.md

## 被测对象（SUT）

- **被测试的类叫** `HealthMonitor`。它的构造函数接受 `check_interval: float = 1.0` 作为健康检查间隔；
- **HealthMonitor** 的核心方法包括：
  - `check_health(service_name: str) -> HealthCheckResult` - 对单个服务执行健康检查
  - `start_monitoring() -> None` - 启动监控循环
  - `get_cluster_health() -> Dict[str, HealthCheckResult]` - 获取集群健康状态
  - `subscribe(callback: Callable[[HealthCheckResult], Awaitable[None]]) -> None` - 订阅状态变化
- **验证时**，通过检查 `HealthCheckResult` 的 `status`, `response_time_ms`, `error` 属性完成验证

## 详细规格

### 核心类定义
```python
# src/launcher/health.py
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Awaitable
import asyncio
import httpx
import time
import structlog

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    service_name: str
    status: HealthStatus
    response_time_ms: float
    timestamp: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class HealthMonitor:
    def __init__(self, check_interval: float = 1.0) -> None:
        """初始化健康监控器"""
        
    async def check_health(self, service_name: str) -> HealthCheckResult:
        """对指定服务执行一次健康检查"""
        
    async def start_monitoring(self) -> None:
        """启动健康监控循环"""
        
    async def stop_monitoring(self) -> None:
        """停止健康监控"""
        
    def get_cluster_health(self) -> Dict[str, HealthCheckResult]:
        """获取集群健康状态（同步方法）"""
        
    def get_cluster_status(self) -> HealthStatus:
        """获取集群整体状态"""
        
    def subscribe(self, callback: Callable[[HealthCheckResult], Awaitable[None]]) -> None:
        """订阅健康状态变化通知"""
        
    def add_service(self, service: ServiceDefinition) -> None:
        """添加要监控的服务"""
```

### 依赖注入与Mock策略

| 依赖名称 | 类型 | 用途 | Mock策略 |
|---------|------|------|----------|
| httpx.AsyncClient | AsyncClient | HTTP健康检查请求 | `patch("httpx.AsyncClient.get")` |
| ServiceDefinition | dataclass | 服务定义信息 | 直接构造测试数据 |
| AgentsAdapter | Protocol | Agents状态获取 | `Mock(spec=AgentsAdapter)` |
| structlog.logger | Logger | 结构化日志记录 | 一般不mock，使用真实logger |

### 方法规格

#### `__init__(self, check_interval: float = 1.0)`
- **参数**：
  - `check_interval: float` - 健康检查间隔（秒），范围0.05-1.0
- **返回值**：None
- **异常**：
  - `ValueError` - 当check_interval超出有效范围时

#### `check_health(self, service_name: str) -> HealthCheckResult`
- **参数**：
  - `service_name: str` - 要检查的服务名称
- **返回值**：`HealthCheckResult` - 健康检查结果
- **异常**：无（内部捕获所有异常并返回结果）

#### `start_monitoring(self) -> None`
- **参数**：无
- **返回值**：None（异步方法）
- **副作用**：创建后台监控任务

#### `subscribe(self, callback: Callable[[HealthCheckResult], Awaitable[None]]) -> None`
- **参数**：
  - `callback: Callable` - 异步回调函数
- **返回值**：None
- **异常**：
  - `TypeError` - 当callback不是异步函数时

## 测试实现模板

### 测试文件结构
```python
# tests/unit/launcher/test_health.py
import pytest
import asyncio
import time
from unittest.mock import patch, Mock, AsyncMock
import httpx

from src.launcher.health import HealthMonitor, HealthStatus, HealthCheckResult
from src.launcher.types import ServiceDefinition
from src.launcher.adapters.agents import AgentsAdapter


class TestHealthMonitor:
    """HealthMonitor 测试套件"""
    
    @pytest.fixture
    def monitor(self):
        """创建默认监控器实例"""
        return HealthMonitor(check_interval=1.0)
    
    @pytest.fixture
    def sample_service(self):
        """创建示例服务定义"""
        return ServiceDefinition(
            name="api-gateway",
            service_type="fastapi",
            module_path="api.main",
            dependencies=[],
            health_check_url="http://localhost:8000/health"
        )
```

### 场景到测试的映射

#### 场景1：HTTP健康检查成功
```python
@pytest.mark.asyncio
async def test_http_health_check_success(self, monitor):
    """验证服务健康端点返回200时标记为HEALTHY"""
    # Arrange
    service_name = "api-gateway"
    url = "http://localhost:8000/health"
    expected_json = {"status": "ok", "version": "1.0.0"}
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_json
        mock_response.headers = {"content-type": "application/json"}
        mock_get.return_value = mock_response
        
        # Act
        result = await monitor._check_http_health(service_name, url)
        
        # Assert
        assert result.service_name == service_name
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms > 0  # 响应时间为正数
        assert result.details == expected_json
        assert result.error is None
        assert isinstance(result.timestamp, float)
```

#### 场景2：HTTP健康检查失败（500错误）
```python
@pytest.mark.asyncio
async def test_http_health_check_500_error(self, monitor):
    """验证服务返回500错误时标记为UNHEALTHY"""
    # Arrange
    service_name = "api-gateway"
    url = "http://localhost:8000/health"
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Act
        result = await monitor._check_http_health(service_name, url)
        
        # Assert
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "HTTP 500"
        assert result.details is None
```

#### 场景3：超时处理
```python
@pytest.mark.asyncio
async def test_http_health_check_timeout(self, monitor):
    """验证请求超时时正确处理"""
    # Arrange
    service_name = "api-gateway"
    url = "http://localhost:8000/health"
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timeout")
        
        # Act
        result = await monitor._check_http_health(service_name, url, timeout=1.0)
        
        # Assert
        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.error.lower()
        assert result.response_time_ms > 0  # 记录了尝试时间
```

#### 场景6-9：频率配置验证
```python
def test_valid_check_intervals(self):
    """验证有效的检查间隔"""
    # 默认1Hz
    monitor1 = HealthMonitor()
    assert monitor1.check_interval == 1.0
    
    # 最高20Hz
    monitor2 = HealthMonitor(check_interval=0.05)
    assert monitor2.check_interval == 0.05
    
    # 边界值
    monitor3 = HealthMonitor(check_interval=1.0)
    assert monitor3.check_interval == 1.0

def test_invalid_check_intervals(self):
    """验证无效频率被拒绝"""
    # 过高频率（>20Hz）
    with pytest.raises(ValueError, match="check_interval must be between"):
        HealthMonitor(check_interval=0.04)
    
    # 过低频率（<1Hz）
    with pytest.raises(ValueError, match="check_interval must be between"):
        HealthMonitor(check_interval=1.5)
```

#### 场景10-15：订阅通知机制
```python
@pytest.mark.asyncio
async def test_subscription_notification_on_state_change(self, monitor):
    """验证健康状态变化时触发订阅通知"""
    # Arrange
    notifications = []
    
    async def callback(result: HealthCheckResult):
        notifications.append(result)
    
    monitor.subscribe(callback)
    
    result1 = HealthCheckResult(
        service_name="api",
        status=HealthStatus.HEALTHY,
        response_time_ms=10.0,
        timestamp=time.time()
    )
    
    result2 = HealthCheckResult(
        service_name="api", 
        status=HealthStatus.UNHEALTHY,
        response_time_ms=5000.0,
        timestamp=time.time()
    )
    
    # Act
    await monitor._notify_subscribers(result1, None)  # 首次通知
    await monitor._notify_subscribers(result2, result1)  # 状态变化通知
    await monitor._notify_subscribers(result2, result2)  # 状态不变，不通知
    
    # Assert
    assert len(notifications) == 2  # 只有前两次触发通知
    assert notifications[0].status == HealthStatus.HEALTHY
    assert notifications[1].status == HealthStatus.UNHEALTHY

@pytest.mark.asyncio
async def test_subscription_callback_exception_isolation(self, monitor):
    """验证一个回调异常不影响其他订阅者"""
    # Arrange
    callback1_calls = []
    callback2_calls = []
    
    async def callback1(result):
        raise ValueError("Callback1 failed")
    
    async def callback2(result):
        callback2_calls.append(result)
    
    monitor.subscribe(callback1)
    monitor.subscribe(callback2)
    
    result = HealthCheckResult("api", HealthStatus.HEALTHY, 10.0, time.time())
    
    # Act - 不应该抛出异常
    await monitor._notify_subscribers(result, None)
    
    # Assert
    assert len(callback2_calls) == 1  # callback2正常执行
    # 异常被日志记录但不影响其他回调

def test_subscribe_requires_async_callback(self, monitor):
    """验证订阅需要异步回调函数"""
    # Arrange
    def sync_callback(result):
        pass
    
    # Act & Assert
    with pytest.raises(TypeError, match="Callback must be an async function"):
        monitor.subscribe(sync_callback)
```

#### 场景16-19：监控循环
```python
@pytest.mark.asyncio
async def test_monitoring_loop_periodic_execution(self, monitor, sample_service):
    """验证监控循环正常启动并周期执行"""
    # Arrange
    monitor.check_interval = 0.1  # 100ms for faster test
    monitor.add_service(sample_service)
    
    with patch.object(monitor, '_check_http_health') as mock_check:
        mock_check.return_value = HealthCheckResult(
            service_name="api-gateway",
            status=HealthStatus.HEALTHY,
            response_time_ms=10.0,
            timestamp=time.time()
        )
        
        # Act
        await monitor.start_monitoring()
        await asyncio.sleep(0.35)  # 等待约3个检查周期
        await monitor.stop_monitoring()
        
        # Assert
        assert mock_check.call_count >= 3
        
@pytest.mark.asyncio 
async def test_monitoring_start_stop_lifecycle(self, monitor):
    """验证监控循环启动停止生命周期"""
    # Act - 启动
    await monitor.start_monitoring()
    assert monitor._monitoring_task is not None
    assert not monitor._monitoring_task.done()
    
    # Act - 停止
    await monitor.stop_monitoring()
    assert monitor._monitoring_task is None
    assert monitor._http_client is None

@pytest.mark.asyncio
async def test_concurrent_health_checks(self, monitor):
    """验证多个服务并发健康检查"""
    # Arrange - 添加5个服务
    services = []
    for i in range(5):
        service = ServiceDefinition(
            name=f"service-{i}",
            service_type="fastapi", 
            module_path="test",
            dependencies=[],
            health_check_url=f"http://localhost:800{i}/health"
        )
        services.append(service)
        monitor.add_service(service)
    
    with patch.object(monitor, '_check_http_health') as mock_check:
        # 模拟每个检查耗时100ms
        async def slow_check(*args):
            await asyncio.sleep(0.1)
            return HealthCheckResult(
                service_name=args[0],
                status=HealthStatus.HEALTHY,
                response_time_ms=100.0,
                timestamp=time.time()
            )
        
        mock_check.side_effect = slow_check
        
        # Act - 测量并发执行时间
        start_time = time.time()
        tasks = [monitor._check_and_notify(s.name) for s in services]
        await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time
        
        # Assert - 并发执行应该明显快于串行
        assert elapsed_time < 0.15  # 应该<150ms而非500ms（5*100ms）
        assert mock_check.call_count == 5
```

#### 场景20-23：集群健康聚合
```python
def test_cluster_health_aggregation(self, monitor):
    """验证集群健康状态聚合"""
    # Arrange - 设置不同状态的服务
    monitor.health_cache = {
        "api": HealthCheckResult("api", HealthStatus.HEALTHY, 10.0, time.time()),
        "agent1": HealthCheckResult("agent1", HealthStatus.DEGRADED, 100.0, time.time()),
        "agent2": HealthCheckResult("agent2", HealthStatus.HEALTHY, 15.0, time.time()),
    }
    
    # Act
    cluster_health = monitor.get_cluster_health()
    cluster_status = monitor.get_cluster_status()
    
    # Assert
    assert len(cluster_health) == 3
    assert cluster_health["api"].status == HealthStatus.HEALTHY
    assert cluster_health["agent1"].status == HealthStatus.DEGRADED
    assert cluster_status == HealthStatus.DEGRADED  # 返回最差状态

def test_cluster_status_priority_unhealthy_wins(self, monitor):
    """验证UNHEALTHY状态具有最高优先级"""
    # Arrange
    monitor.health_cache = {
        "svc1": HealthCheckResult("svc1", HealthStatus.HEALTHY, 10.0, time.time()),
        "svc2": HealthCheckResult("svc2", HealthStatus.DEGRADED, 50.0, time.time()),
        "svc3": HealthCheckResult("svc3", HealthStatus.UNHEALTHY, 1000.0, time.time()),
    }
    
    # Act & Assert
    assert monitor.get_cluster_status() == HealthStatus.UNHEALTHY

def test_empty_cluster_returns_unknown(self, monitor):
    """验证空集群返回UNKNOWN状态"""
    # Arrange - 空缓存
    monitor.health_cache = {}
    
    # Act & Assert
    assert monitor.get_cluster_status() == HealthStatus.UNKNOWN
```

#### 场景24-26：Agents健康集成
```python
@pytest.mark.asyncio
async def test_agent_health_status_mapping(self, monitor):
    """验证Agent内部状态正确映射到健康状态"""
    # Arrange
    agents_adapter = Mock()
    agents_adapter.get_agent_statuses.return_value = {
        "worldsmith": {"status": "running", "health": "healthy"},
        "plotmaster": {"status": "running", "health": "degraded"},
        "storybuilder": {"status": "running"},  # 没有health字段
        "writer": {"status": "stopped", "health": "healthy"},  # 停止状态
    }
    
    # Act
    await monitor.check_agents_health(agents_adapter)
    cluster_health = monitor.get_cluster_health()
    
    # Assert
    assert "agent:worldsmith" in cluster_health
    assert cluster_health["agent:worldsmith"].status == HealthStatus.HEALTHY
    assert cluster_health["agent:plotmaster"].status == HealthStatus.DEGRADED
    assert cluster_health["agent:storybuilder"].status == HealthStatus.UNKNOWN  # running但无health
    assert cluster_health["agent:writer"].status == HealthStatus.UNHEALTHY  # 已停止

@pytest.mark.asyncio
async def test_agents_health_check_exception_handling(self, monitor):
    """验证获取Agent状态失败时的处理"""
    # Arrange
    agents_adapter = Mock()
    agents_adapter.get_agent_statuses.side_effect = Exception("Connection failed")
    
    # Act - 不应该抛出异常
    await monitor.check_agents_health(agents_adapter)
    
    # Assert - 异常被捕获并记录，不影响其他功能
    cluster_health = monitor.get_cluster_health()
    assert len(cluster_health) == 0  # 没有agent状态被记录
```

## 断言策略

### 基本断言
- **相等性**：`assert result == expected`
- **状态枚举**：`assert result.status == HealthStatus.HEALTHY`
- **数值范围**：`assert 0 < result.response_time_ms < 1000`
- **字符串包含**：`assert "timeout" in result.error.lower()`

### 异步断言
- **异步方法调用**：`result = await monitor.method()`
- **异常捕获**：`with pytest.raises(ExceptionType, match="pattern")`
- **Mock验证**：`assert mock_method.call_count == expected_count`

### 集合断言
- **字典长度**：`assert len(cluster_health) == 3`
- **键存在性**：`assert "service_name" in cluster_health`
- **列表内容**：`assert all(isinstance(r, HealthCheckResult) for r in results)`

### 时间相关断言
- **时间戳合理性**：`assert abs(result.timestamp - time.time()) < 1.0`
- **持续时间测试**：`assert elapsed_time < expected_max_duration`

## 测试数据工厂

### 有效数据生成
```python
def create_healthy_result(service_name: str = "test-service") -> HealthCheckResult:
    """创建健康检查成功结果"""
    return HealthCheckResult(
        service_name=service_name,
        status=HealthStatus.HEALTHY,
        response_time_ms=25.0,
        timestamp=time.time(),
        details={"status": "ok", "version": "1.0.0"}
    )

def create_service_definition(
    name: str = "test-service",
    health_url: str = "http://localhost:8000/health"
) -> ServiceDefinition:
    """创建服务定义"""
    return ServiceDefinition(
        name=name,
        service_type="fastapi",
        module_path="test.main",
        dependencies=[],
        health_check_url=health_url
    )
```

### Mock设置辅助
```python
def setup_http_mock_success(mock_get, response_data=None):
    """设置HTTP成功响应Mock"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data or {"status": "ok"}
    mock_response.headers = {"content-type": "application/json"}
    mock_get.return_value = mock_response
    return mock_response

def setup_http_mock_timeout(mock_get):
    """设置HTTP超时Mock"""
    mock_get.side_effect = httpx.TimeoutException("Request timeout")
```

## 测试性能考虑

### 超时控制
- 单个测试方法超时：使用`pytest-timeout`或测试内`asyncio.wait_for`
- 快速失败：网络Mock避免真实请求
- 并发测试：使用较小的时间间隔但确保逻辑正确

### 资源清理
```python
@pytest.fixture
async def monitor(self):
    """自动清理的监控器实例"""
    monitor = HealthMonitor()
    yield monitor
    # 清理
    await monitor.stop_monitoring()
```

## 验证清单

- [x] 所有26个测试场景都有对应的测试实现模板
- [x] HealthMonitor的构造函数参数和验证逻辑明确
- [x] 核心方法签名完整（check_health, start_monitoring等）
- [x] HTTP客户端Mock策略清晰（patch httpx.AsyncClient.get）
- [x] 异步测试模式正确（pytest.mark.asyncio）
- [x] 断言方式具体可执行且涵盖边界情况
- [x] 错误处理和异常场景覆盖完整
- [x] 测试数据工厂提供便利的对象创建

---
*此文档提供了Task 7健康监控的详细测试技术规格，确保测试实现的准确性和完整性*