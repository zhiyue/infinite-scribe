# 测试场景 - Task 7: 健康监控（最小）

生成时间：2025-09-02T16:10:00Z  
关联任务：7  
关联需求：FR-003 (实时状态监控), NFR-003 (可用性需求)  
测试场景数量：26

## 核心功能测试场景

### HTTP 健康检查

1. HTTP 健康检查成功

- 场景描述：验证服务健康端点返回 200 时标记为 HEALTHY
- 测试数据：`mock_response(status=200, json={"status": "ok"})`
- 预期结果：`HealthStatus.HEALTHY`，`response_time_ms` 为正（允许近似断言），`details` 可解析为 JSON

2. HTTP 健康检查失败（500 错误）

- 场景描述：验证服务返回 500 错误时标记为 UNHEALTHY
- 测试数据：`mock_response(status=500, text="Internal Server Error")`
- 预期结果：`HealthStatus.UNHEALTHY, error="HTTP 500"`

3. HTTP 健康检查超时

- 场景描述：验证请求超时时正确处理
- 测试数据：`httpx.TimeoutException("Request timeout"), timeout=5.0`
- 预期结果：`HealthStatus.UNHEALTHY, error="Request timeout"`

4. 网络连接被拒绝

- 场景描述：验证服务未启动时的连接错误处理
- 测试数据：`httpx.ConnectError("Connection refused")`
- 预期结果：`HealthStatus.UNHEALTHY, error="Connection refused"`

5. 非 JSON 响应处理

- 场景描述：验证健康端点返回纯文本时的处理
- 测试数据：`mock_response(status=200, text="OK", content_type="text/plain")`
- 预期结果：`HealthStatus.HEALTHY, details=None`

### 检查频率配置

6. 默认频率（1Hz）

- 场景描述：验证默认 1 秒间隔的健康检查
- 测试数据：`HealthMonitor(check_interval=1.0)`
- 预期结果：`monitor.check_interval == 1.0`

7. 最高频率（20Hz）

- 场景描述：验证支持 20Hz 的高频检查
- 测试数据：`HealthMonitor(check_interval=0.05)`
- 预期结果：`monitor.check_interval == 0.05`

8. 无效频率拒绝（过高）

- 场景描述：验证拒绝超过 20Hz 的频率
- 测试数据：`HealthMonitor(check_interval=0.04)`
- 预期结果：`ValueError("check_interval must be between 0.05 (20Hz) and 1.0 (1Hz)")`

9. 无效频率拒绝（过低）

- 场景描述：验证拒绝低于 1Hz 的频率
- 测试数据：`HealthMonitor(check_interval=1.5)`
- 预期结果：`ValueError("check_interval must be between 0.05 (20Hz) and 1.0 (1Hz)")`

### 订阅通知机制

10. 首次检查通知

- 场景描述：验证首次产生健康结果（无历史结果）时也会通知订阅者
- 测试数据：`old_result=None, new_result=HEALTHY`
- 预期结果：`callback 被调用 1 次，参数为首次状态`

11. 状态变化通知

- 场景描述：验证健康状态变化时触发订阅通知
- 测试数据：`状态从 HEALTHY 变为 UNHEALTHY`
- 预期结果：`callback 被调用 1 次，参数为新状态`

12. 状态不变不通知

- 场景描述：验证状态未变化时不触发通知
- 测试数据：`连续两次 HEALTHY 状态`
- 预期结果：`callback 不被调用`

13. 多订阅者通知

- 场景描述：验证多个订阅者都收到通知
- 测试数据：`3 个订阅回调，状态变化 1 次`
- 预期结果：`所有 3 个 callback 被调用`

14. 订阅回调异常隔离

- 场景描述：验证一个回调异常不影响其他订阅者
- 测试数据：`callback1 抛出异常，callback2 正常`
- 预期结果：`callback2 仍被调用，错误被结构化日志记录`

15. 取消订阅

- 场景描述：验证取消订阅后不再收到通知
- 测试数据：`subscribe 后 unsubscribe，然后状态变化`
- 预期结果：`callback 不被调用`

### 监控循环

16. 监控循环启动

- 场景描述：验证监控循环正常启动并周期执行
- 测试数据：`start_monitoring(), interval=0.1, wait=0.35`
- 预期结果：`健康检查执行≥3次`

17. 监控循环停止

- 场景描述：验证监控循环正常停止
- 测试数据：`start_monitoring()后stop_monitoring()`
- 预期结果：`监控任务被取消，HTTP客户端关闭`

18. 重复启动监控

- 场景描述：验证避免重复启动监控任务
- 测试数据：`连续调用start_monitoring()两次`
- 预期结果：`只有一个监控任务运行`

19. 并发健康检查

- 场景描述：验证多个服务并发健康检查
- 测试数据：`5个服务，各响应时间100ms`
- 预期结果：`总执行时间<150ms（并发执行）`

### 集群健康聚合

20. 集群健康状态获取

- 场景描述：验证同步获取所有服务的健康状态（缓存拷贝）
- 测试数据：`api=HEALTHY, agent1=DEGRADED, agent2=HEALTHY`
- 预期结果：`get_cluster_health()返回3个服务状态`

21. 集群最差状态聚合

- 场景描述：验证集群状态返回最差的服务状态
- 测试数据：`HEALTHY, DEGRADED, UNHEALTHY混合`
- 预期结果：`get_cluster_status()返回UNHEALTHY`

22. 全健康集群状态

- 场景描述：验证所有服务健康时的集群状态
- 测试数据：`所有服务状态为HEALTHY`
- 预期结果：`get_cluster_status()返回HEALTHY`

23. 空集群状态

- 场景描述：验证无服务时的集群状态
- 测试数据：`health_cache为空`
- 预期结果：`get_cluster_status()返回UNKNOWN`

### Agents 健康集成

24. Agent 健康状态映射

- 场景描述：验证Agent内部状态正确映射到健康状态
- 测试数据：`agent_status={"status": "running", "health": "healthy"}`
- 预期结果：`HealthStatus.HEALTHY`

25. Agent 降级状态

- 场景描述：验证Agent降级状态的正确映射
- 测试数据：`agent_status={"status": "running", "health": "degraded"}`
- 预期结果：`HealthStatus.DEGRADED`

26. Agent 异常处理

- 场景描述：验证获取Agent状态失败时的处理
- 测试数据：`agents_adapter.get_agent_statuses()抛出异常`
- 预期结果：`错误被记录，不影响其他健康检查`

## 性能验证场景

### P1 - 响应时间验证

- 单服务健康检查响应时间 < 200ms（NFR-003）
- 10个服务并发检查总时间 < 500ms
- 健康状态查询响应时间 < 10ms（缓存读取）

### P2 - 资源使用验证

- 1Hz监控循环CPU占用 < 1%
- 20Hz监控循环CPU占用 < 5%
- 内存使用稳定，无泄漏（运行1小时）

## 边界条件

- 服务动态添加/移除时的监控状态
- HTTP客户端连接池管理
- 极端网络延迟下的超时处理
- 大量订阅者（>100）的通知性能

## 测试优先级

- **P0（必须）**：场景 1-5、10-11、16、20-21
- **P1（重要）**：场景 6-9、12-15、17-19、22-23
- **P2（可选）**：场景 24-26、性能验证场景

## API 行为约定（便于测试）

- `HealthMonitor.check_health(service_name) -> HealthCheckResult`：对单个服务执行一次检查并回写缓存。
- `HealthMonitor.get_cluster_health() -> dict[str, HealthCheckResult]`：同步读取缓存副本。
- `HealthMonitor.get_cluster_status() -> HealthStatus`：返回最差状态。
- 订阅回调：仅在首次检查或状态变化时触发，需为异步函数。

## 执行建议与超时

- 单元测试目录：`apps/backend/tests/unit/launcher/`。
- 使用 `pytest-asyncio` 运行异步用例；推荐 `timeout 10 uv run pytest tests/unit -v` 包裹。
- 对网络调用进行 `httpx.AsyncClient.get` 打桩，避免真实请求。

---
*此测试场景文档用于指导Task 7健康监控的TDD实施*
