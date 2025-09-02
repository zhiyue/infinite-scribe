# 任务 6 测试场景

生成时间：2025-09-02T00:00:00Z  
更新时间：2025-09-02T14:00:00Z  
任务描述：轻量编排器 - 基于显式状态机与拓扑分层：按依赖启动/逆序停止，失败回滚  
关联需求：FR-001, FR-002, FR-004, NFR-002  
测试场景总数：32个（P0: 18个, P1: 10个, P2: 4个）  

## 组件状态管理测试场景

1. 服务状态枚举值验证

- 场景描述：验证 ServiceStatus 枚举包含所有必需的状态值（与现有类型一致）
- 测试数据：`ServiceStatus.STOPPED, ServiceStatus.STARTING, ServiceStatus.RUNNING, ServiceStatus.DEGRADED, ServiceStatus.STOPPING, ServiceStatus.FAILED`
- 预期结果：`{"STOPPED": "stopped", "STARTING": "starting", "RUNNING": "running", "DEGRADED": "degraded", "STOPPING": "stopping", "FAILED": "failed"}`

2. 初始状态设置测试

- 场景描述：验证未启动的服务默认查询状态为 STOPPED（按 getter 的默认值）
- 测试数据：`orchestrator.get_service_state("api")`
- 预期结果：`orchestrator.get_service_state("api") == ServiceStatus.STOPPED`

3. 状态转换有效性验证

- 场景描述：验证状态转换遵循允许的状态机规则
- 测试数据：`orchestrator.is_valid_state_transition(ServiceStatus.STARTING, ServiceStatus.RUNNING)`
- 预期结果：返回 True

4. 非法状态转换拒绝

- 场景描述：验证非法的状态转换被拒绝
- 测试数据：`orchestrator.is_valid_state_transition(ServiceStatus.STOPPED, ServiceStatus.RUNNING)`
- 预期结果：返回 False（如需强制转换应抛 OrchestrationError）

## 服务依赖管理测试场景

5. 简单依赖链排序

- 场景描述：验证基本的依赖链能正确分层排序
- 测试数据：`deps = {"agents": {"api"}}`
- 预期结果：`[["api"], ["agents"]]`

6. 复杂依赖图拓扑排序（可选，模拟依赖图）

- 场景描述：验证复杂依赖关系的拓扑排序（通过打桩 `build_dependency_graph`）
- 测试数据：`{"api": {"db", "cache"}, "agents": {"api"}, "db": set(), "cache": set()}`
- 预期结果：`[["db", "cache"], ["api"], ["agents"]]`

7. 循环依赖检测

- 场景描述：验证循环依赖能被检测并报错
- 测试数据：`{"a": {"b"}, "b": {"c"}, "c": {"a"}}`
- 预期结果：抛出 `OrchestrationError`

8. 自依赖检测

- 场景描述：验证服务自依赖被检测并报错
- 测试数据：`{"api": {"api"}}`
- 预期结果：抛出 `OrchestrationError`

## 启动编排测试场景

9. 按依赖顺序启动成功

- 场景描述：验证服务按正确的依赖顺序启动
- 测试数据：`await orchestrator.orchestrate_startup(["api", "agents"])`，并打桩 `build_dependency_graph -> {"agents": {"api"}}`
- 预期结果：`orchestrator.get_service_state("api") == ServiceStatus.RUNNING` 且之后 `agents` 也为 RUNNING

10. 依赖启动失败时回滚

- 场景描述：验证后续级别服务启动失败时触发回滚机制
- 测试数据：打桩 `api.start()->True`，`agents.start()->raise Exception`
- 预期结果：返回 False，已启动的 `api` 被回滚到 `STOPPED`

11. 部分服务启动场景（依赖缺失处理）

- 场景描述：验证只启动指定服务子集时的依赖处理
- 测试数据：`await orchestrator.orchestrate_startup(["agents"])` 而 `api` 未启动
- 预期结果：P1阶段返回 False 并记录错误日志；P2阶段可选抛出 `DependencyNotReadyError`

12. 并发启动同层级服务（性能验证）

- 场景描述：验证无依赖关系的同层级服务可并发启动，且性能优于串行
- 测试数据：
  ```python
  deps = {"a": set(), "b": set(), "api": {"a", "b"}}
  # 模拟每个服务启动需要 100ms
  async def slow_start():
      await asyncio.sleep(0.1)
      return True
  ```
- 预期结果：
  ```python
  start_time = time.time()
  result = await orchestrator.orchestrate_startup(["a", "b", "api"])
  elapsed = time.time() - start_time
  assert elapsed < 0.25  # 并发应在 200ms 内完成（而非串行的 300ms）
  ```

## 停止编排测试场景

13. 逆序停止服务

- 场景描述：验证服务按依赖关系的逆序停止
- 测试数据：`await orchestrator.orchestrate_shutdown(["api", "agents"])`（假设 agents 依赖 api）
- 预期结果：先停止 `agents`，再停止 `api`

14. 优雅停止超时处理

- 场景描述：验证服务停止超时后的强制终止（由适配器/ProcessManager 处理）
- 测试数据：将 `config.stop_grace` 设为 1，停止过程超过 1 秒触发强制终止
- 预期结果：服务状态最终为 `ServiceStatus.STOPPED`，并包含超时与强制终止的警告日志

15. 停止过程中的错误处理

- 场景描述：验证停止过程中某服务失败不影响其他服务停止
- 测试数据：`api.stop()` 抛异常，`agents.stop()` 正常
- 预期结果：`agents` 仍然正常停止为 `ServiceStatus.STOPPED`，总返回值为 False

16. 部分服务停止（当启用健康降级时）

- 场景描述：验证只停止指定服务时依赖关系的处理
- 测试数据：停止 `api` 而 `agents` 仍依赖于 `api`
- 预期结果：`agents` 通过健康检查降级为 `ServiceStatus.DEGRADED`

## 错误处理与故障转移测试场景

17. 服务启动超时处理（适配器层）

- 场景描述：验证服务启动超时时的状态管理
- 测试数据：模拟 `adapter.start()` 超时/失败
- 预期结果：状态置为 `ServiceStatus.FAILED` 并触发回滚

18. 运行时服务故障检测（健康检查）

- 场景描述：验证运行时服务故障被正确检测和标记
- 测试数据：健康检查返回 `{"status": "unhealthy"}`
- 预期结果：`update_service_health("api")` 后状态为 `ServiceStatus.DEGRADED`

19. 故障服务的依赖影响（可选，需依赖关系与健康订阅）

- 场景描述：验证依赖服务故障时对其他服务状态的影响
- 测试数据：`api` 依赖 `db`，`db` 健康检查失败
- 预期结果：`api` 降级为 `ServiceStatus.DEGRADED`

20. 故障恢复重启（可选）

- 场景描述：验证故障服务可重启恢复
- 测试数据：对 `FAILED/DEGRADED` 服务执行重启（`stop()->start()`）
- 预期结果：服务状态转为 `RUNNING`

## 健康监控集成测试场景

21. 健康状态聚合（HealthMonitor）

- 场景描述：验证多服务健康状态的聚合计算（使用 HealthMonitor）
- 测试数据：api(RUNNING), db(RUNNING), cache(DEGRADED)
- 预期结果：`health_monitor.get_cluster_health()["cluster"] == "degraded"`

22. 健康检查失败触发降级

- 场景描述：验证健康检查失败时服务状态降级
- 测试数据：api 服务健康检查失败
- 预期结果：`update_service_health("api")` 后 `get_service_state("api") == ServiceStatus.DEGRADED`

23. 空服务列表处理

- 场景描述：验证空服务列表时的编排器行为
- 测试数据：`await orchestrator.orchestrate_startup([])`
- 预期结果：返回 True 且不抛出异常

24. 未知服务名称处理

- 场景描述：验证包含未知服务名时的错误处理
- 测试数据：`await orchestrator.orchestrate_startup(["unknown"])`
- 预期结果：返回 False（内部记录错误日志）；`get_service_state("unknown")` 返回 `ServiceStatus.STOPPED`

## 并发安全测试场景

25. 并发状态修改安全性（P1 - 核心功能）

- 场景描述：验证多个协程同时修改服务状态时的线程安全
- 测试数据：
  ```python
  tasks = [
      orchestrator.set_service_state("api", ServiceStatus.STARTING),
      orchestrator.set_service_state("api", ServiceStatus.RUNNING),
      orchestrator.set_service_state("api", ServiceStatus.STOPPING)
  ]
  ```
- 预期结果：使用 `asyncio.Lock` 保护，只有合法状态转换成功，非法转换抛出 `OrchestrationError`

26. 启动停止并发调用（P1 - 核心功能）

- 场景描述：验证同时调用启动和停止方法时的互斥处理
- 测试数据：
  ```python
  await asyncio.gather(
      orchestrator.orchestrate_startup(),
      orchestrator.orchestrate_shutdown(),
      return_exceptions=True
  )
  ```
- 预期结果：操作串行执行，不会出现状态混乱，最终状态一致

27. 大规模服务编排性能（P2 - 可选）

- 场景描述：验证大量服务时编排器的性能表现
- 测试数据：100 个服务的复杂依赖图（打桩）
- 预期结果：拓扑排序在 10ms 内完成（O(V+E) 复杂度）

28. 内存状态持久性

- 场景描述：验证服务状态在内存中的正确维护
- 测试数据：服务状态变更后立即查询
- 预期结果：状态查询结果与最后一次设置一致

29. 启动超时处理（P1 - 新增）

- 场景描述：验证单个服务启动超时的处理机制
- 测试数据：
  ```python
  async def slow_start():
      await asyncio.sleep(2)  # 模拟慢启动
      return True
  mock_api.start = slow_start
  orchestrator.config.startup_timeout = 1  # 1秒超时
  ```
- 预期结果：
  - 启动操作在1秒后超时
  - 服务状态变为 `ServiceStatus.FAILED`
  - 触发回滚机制
  - 返回 False

30. 分层并发停止测试（P1 - 新增）

- 场景描述：验证同层服务并发停止的性能优势
- 测试数据：
  ```python
  deps = {"db": set(), "cache": set(), "api": {"db", "cache"}}
  # db 和 cache 各需 100ms 停止
  ```
- 预期结果：
  ```python
  start_time = time.time()
  result = await orchestrator.orchestrate_shutdown(["api", "db", "cache"])
  elapsed = time.time() - start_time
  assert elapsed < 0.25  # 并发停止应在 200ms 内完成
  ```

31. 状态转换锁保护测试（P1 - 新增）

- 场景描述：验证状态转换的原子性和线程安全
- 测试数据：
  ```python
  async def rapid_state_changes():
      for _ in range(100):
          await orchestrator.set_service_state(
              "api", 
              random.choice([ServiceStatus.STARTING, ServiceStatus.RUNNING])
          )
  # 并发执行多个 rapid_state_changes
  ```
- 预期结果：
  - 所有状态转换要么成功要么抛出异常
  - 不会出现状态不一致
  - 最终状态符合状态机规则

32. 依赖图缓存测试（P2 - 新增）

- 场景描述：验证依赖图构建的缓存机制避免重复计算
- 测试数据：
  ```python
  with patch.object(orchestrator, 'build_dependency_graph', wraps=orchestrator.build_dependency_graph) as mock_build:
      orchestrator.get_startup_order(["api", "agents"])
      orchestrator.get_startup_order(["api", "agents"])
      orchestrator.get_startup_order(["api"])
  ```
- 预期结果：
  - `build_dependency_graph` 只被调用一次（使用缓存）
  - 多次调用 `get_startup_order` 返回一致的结果
