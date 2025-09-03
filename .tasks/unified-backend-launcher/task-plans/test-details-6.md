# 任务 6 测试详情

生成时间：2025-09-02T14:00:00Z  
任务描述：轻量编排器 - 基于显式状态机与拓扑分层，按依赖启动/逆序停止，失败回滚  
测试场景总数：28个（与 task-6-test-scenarios 对齐；部分并发停止/启动超时可作为可选增强用例）

## SUT (System Under Test)

### 主要类：Orchestrator

**位置**：`apps/backend/src/launcher/orchestrator.py`

**核心方法**：
1. `__init__(config)` - 初始化编排器
2. `orchestrate_startup(target_services)` - 按依赖启动服务
3. `orchestrate_shutdown(target_services)` - 按逆序停止服务
4. `get_startup_order(target_services)` - 获取服务启动顺序（分层）
5. `set_service_state(service_name, state)` - 设置服务状态（带锁保护，异步）
6. `get_service_state(service_name)` - 获取服务状态
7. `build_dependency_graph()` - 构建服务依赖图
8. `is_valid_state_transition(from_state, to_state)` - 验证状态转换
9. `update_service_health(service_name)` - 更新服务健康状态
10. `collect_error_context(service_name)` - 收集错误诊断信息

## 依赖与 Mock 策略

- `services`: 直接注入 `dict[str, AsyncMock]` 到 `orchestrator.services`，隔离适配器实现；
- `_create_adapter_by_name`: 通过 patch 返回 `AsyncMock` 适配器以覆盖默认工厂；
- `build_dependency_graph()`: 通过 patch 返回指定依赖图以控制拓扑；
- `logger`: 可选择验证关键错误日志（如循环依赖、启动失败回滚）。

说明：未知服务的启动请求返回 False 并记录日志，不强制抛异常；循环依赖检测抛 `OrchestrationError`。

## 测试类结构

### 1. TestOrchestratorStateManagement
```python
class TestOrchestratorStateManagement:
    """测试场景 1-4：状态管理基础测试"""
    
    def test_service_status_enum_values(self)
    def test_initial_state_is_stopped(self)
    def test_valid_state_transitions(self)
    def test_invalid_state_transitions_rejected(self)
```

### 2. TestOrchestratorDependencies  
```python
class TestOrchestratorDependencies:
    """测试场景 5-8：依赖管理测试"""
    
    def test_simple_dependency_chain_sorting(self)
    def test_complex_dependency_graph_sorting(self)
    def test_circular_dependency_detection(self)
    def test_self_dependency_detection(self)
```

### 3. TestOrchestratorStartup
```python
class TestOrchestratorStartup:
    """测试场景 9-12, 29：启动编排测试"""
    
    async def test_startup_follows_dependency_order(self)
    async def test_startup_failure_triggers_rollback(self)
    async def test_partial_services_startup_with_missing_deps(self)
    async def test_concurrent_startup_same_level_performance(self)
    async def test_startup_timeout_handling(self)  # 可选（增强）
```

### 4. TestOrchestratorShutdown
```python
class TestOrchestratorShutdown:
    """测试场景 13-16, 30：停止编排测试"""
    
    async def test_shutdown_reverse_order(self)
    async def test_graceful_shutdown_timeout(self)
    async def test_shutdown_error_handling(self)
    async def test_partial_services_shutdown(self)
    async def test_concurrent_shutdown_same_level(self)  # 可选（增强）
```

## 测试覆盖目标

| 测试类 | 场景数 | 目标覆盖率 | 关键验证点 |
|--------|--------|------------|------------|
| StateManagement | 4 | 100% | 所有状态转换 |
| Dependencies | 4 | 100% | 拓扑排序正确性 |
| Startup | 5 | > 90% | 并发和回滚 |
| Shutdown | 5 | > 90% | 逆序和并发 |

---
*此文档作为Task 6测试实施的详细指南*

## 关键用例模板（示例）

以下示例展示编写测试时的打桩与断言方式，便于快速落地。

1) 状态枚举值验证

```python
def test_service_status_enum_values():
    expected = {
        "STOPPED": "stopped",
        "STARTING": "starting",
        "RUNNING": "running",
        "DEGRADED": "degraded",
        "STOPPING": "stopping",
        "FAILED": "failed",
    }
    for name, value in expected.items():
        assert hasattr(ServiceStatus, name)
        assert ServiceStatus[name].value == value
```

2) 简单依赖分层排序

```python
def test_simple_dependency_chain_sorting(orchestrator, mocker):
    # agents 依赖 api
    mocker.patch.object(orchestrator, "build_dependency_graph", return_value={
        "agents": {"api"},
        "api": set(),
    })
    order = orchestrator.get_startup_order(["api", "agents"])  # 分层
    assert order == [["api"], ["agents"]]
```

3) 按依赖顺序启动（成功）

```python
@pytest.mark.asyncio
async def test_startup_follows_dependency_order(orchestrator, mocker):
    mocker.patch.object(orchestrator, "build_dependency_graph", return_value={
        "agents": {"api"},
        "api": set(),
    })
    started: list[str] = []
    api = AsyncMock(); agents = AsyncMock()
    async def start_api(): started.append("api"); return True
    async def start_agents(): started.append("agents"); return True
    api.start = start_api; agents.start = start_agents
    orchestrator.services = {"api": api, "agents": agents}

    result = await orchestrator.orchestrate_startup(["api", "agents"])
    assert result is True
    assert started == ["api", "agents"]
    assert orchestrator.get_service_state("api") == ServiceStatus.RUNNING
    assert orchestrator.get_service_state("agents") == ServiceStatus.RUNNING
```

4) 启动失败回滚

```python
@pytest.mark.asyncio
async def test_startup_failure_triggers_rollback(orchestrator, mocker):
    mocker.patch.object(orchestrator, "build_dependency_graph", return_value={
        "agents": {"api"},
        "api": set(),
    })
    api = AsyncMock(); agents = AsyncMock()
    api.start = AsyncMock(return_value=True)
    api.stop = AsyncMock(return_value=True)
    agents.start = AsyncMock(side_effect=Exception("boom"))
    orchestrator.services = {"api": api, "agents": agents}

    result = await orchestrator.orchestrate_startup(["api", "agents"])
    assert result is False
    api.stop.assert_called_once()
    assert orchestrator.get_service_state("api") == ServiceStatus.STOPPED
    assert orchestrator.get_service_state("agents") == ServiceStatus.FAILED
```

5) 循环依赖检测

```python
def test_circular_dependency_detection(orchestrator, mocker):
    mocker.patch.object(orchestrator, "build_dependency_graph", return_value={
        "a": {"b"}, "b": {"c"}, "c": {"a"}
    })
    with pytest.raises(OrchestrationError, match="Circular dependency"):
        orchestrator.get_startup_order(["a", "b", "c"])
```

6) 同层并发启动性能（可选）

```python
@pytest.mark.asyncio
async def test_concurrent_startup_same_level_performance(orchestrator, mocker):
    mocker.patch.object(orchestrator, "build_dependency_graph", return_value={
        "s1": set(), "s2": set()
    })
    async def slow():
        await asyncio.sleep(0.1); return True
    s1 = AsyncMock(); s2 = AsyncMock()
    s1.start = slow; s2.start = slow
    orchestrator.services = {"s1": s1, "s2": s2}

    import time
    t0 = time.perf_counter()
    ok = await orchestrator.orchestrate_startup(["s1", "s2"])
    dt = time.perf_counter() - t0
    assert ok is True
    assert dt < 0.15  # 并发而非串行
```

## 断言与校验要点

- 状态断言：`get_service_state(name) == ServiceStatus.*`
- 返回值断言：`result is True/False`
- 顺序断言：分层列表或启动顺序列表比较
- 异常断言：循环依赖使用 `OrchestrationError`
- 日志断言（可选）：校验回滚/超时日志是否输出

## 测试数据工厂（依赖图）

```python
from typing import Dict, Set

def create_linear_dependency_graph(n: int) -> Dict[str, Set[str]]:
    deps: Dict[str, Set[str]] = {}
    for i in range(n):
        name = f"service_{i}"
        prev = f"service_{i-1}" if i > 0 else None
        deps[name] = {prev} if prev else set()
    return deps

def create_circular_dependency_graph() -> Dict[str, Set[str]]:
    return {"a": {"b"}, "b": {"c"}, "c": {"a"}}
```
