# 测试场景 - Task 8: 管理端点（开发默认启用）

生成时间：2025-09-02T16:40:00Z  
关联任务：8  
关联需求：FR-003 (实时状态监控), NFR-003 (可用性需求)  
测试场景数量：24

## 核心功能测试场景

### 启动器状态端点

1. 获取启动器状态成功

- 场景描述：验证 GET /admin/launcher/status 返回正确的服务状态信息
- 测试数据：`Mock orchestrator 返回 2 个服务（1个运行，1个启动中）`
- 预期结果：`200 OK，launcher_status="partial"，total_services=2，running_services=1`

2. 全部服务运行状态

- 场景描述：验证所有服务运行时的启动器总体状态
- 测试数据：`Mock orchestrator 返回所有服务状态为 RUNNING`
- 预期结果：`launcher_status="running"，running_services=total_services`

3. 服务详细信息完整

- 场景描述：验证返回的服务包含完整的详细信息
- 测试数据：`Mock 服务包含 name, status, uptime_seconds, started_at, pid, port`
- 预期结果：`响应包含所有字段，数据类型正确`

4. 空服务列表处理

- 场景描述：验证无服务时的状态响应
- 测试数据：`Mock orchestrator 返回空的服务列表`
- 预期结果：`launcher_status="stopped"，total_services=0，services=[]`

5. 服务状态枚举映射

- 场景描述：验证内部状态正确映射为 API 响应格式
- 测试数据：`ServiceState.STARTING -> "starting", ServiceState.ERROR -> "error"`
- 预期结果：`状态字符串符合 API 规范（小写，易读）`

### 健康摘要端点

6. 获取健康摘要成功

- 场景描述：验证 GET /admin/launcher/health 返回集群健康信息
- 测试数据：`Mock health monitor 返回 3 个服务（2健康，1降级）`
- 预期结果：`200 OK，cluster_status="degraded"，healthy_count=2，total_count=3`

7. 健康服务详细信息

- 场景描述：验证健康摘要包含服务级别详细信息
- 测试数据：`Mock 健康结果包含 response_time_ms, last_check, error`
- 预期结果：`每个服务项包含完整健康信息，时间格式为 ISO 字符串`

8. 全健康集群状态

- 场景描述：验证所有服务健康时的集群状态
- 测试数据：`所有服务 HealthStatus.HEALTHY`
- 预期结果：`cluster_status="healthy"，healthy_count=total_count`

9. 无健康数据处理

- 场景描述：验证健康监控无数据时的响应
- 测试数据：`Mock health monitor 返回空的健康缓存`
- 预期结果：`cluster_status="unknown"，total_count=0，services=[]`

### 环境安全控制

10. 开发环境启用端点

- 场景描述：验证开发环境下管理端点正常访问
- 测试数据：`settings.environment="development"`
- 预期结果：`端点正常响应，不返回 404 或 403`

11. 生产环境默认禁用

- 场景描述：验证生产环境下管理端点默认禁用
- 测试数据：`settings.environment="production", admin_enabled=False`
- 预期结果：`返回 404 Not Found`

12. 生产环境显式启用

- 场景描述：验证生产环境可通过配置显式启用
- 测试数据：`settings.environment="production", admin_enabled=True`
- 预期结果：`端点正常响应（需要鉴权或本地绑定）`

13. 权限控制函数验证

- 场景描述：验证 require_admin_access 依赖正确工作
- 测试数据：`各种环境和配置组合`
- 预期结果：`根据配置正确允许/拒绝访问`

### API 规范合规

14. OpenAPI 文档生成

- 场景描述：验证管理端点在 OpenAPI 文档中正确显示
- 测试数据：`访问 /docs 和 /openapi.json`
- 预期结果：`文档包含管理端点，标签为 "launcher-admin"`

15. 响应模型验证

- 场景描述：验证响应符合 Pydantic 模型定义
- 测试数据：`实际 API 响应数据`
- 预期结果：`通过 Pydantic 模型验证，字段类型正确`

16. 时间戳格式一致性

- 场景描述：验证所有时间字段使用一致的 ISO 格式
- 测试数据：`包含时间戳的响应字段`
- 预期结果：`所有时间字段为 ISO 8601 格式字符串`

### 错误处理

17. 编排器未就绪处理

- 场景描述：验证编排器未初始化时的错误处理
- 测试数据：`get_orchestrator() 抛出异常或返回 None`
- 预期结果：`返回 503 Service Unavailable，含错误信息`

18. 健康监控异常处理

- 场景描述：验证健康监控服务异常时的容错处理
- 测试数据：`get_health_monitor() 抛出异常`
- 预期结果：`返回部分数据或 503，记录错误日志`

19. 依赖注入失败处理

- 场景描述：验证依赖注入失败时的错误响应
- 测试数据：`FastAPI 依赖解析失败`
- 预期结果：`返回 500 Internal Server Error`

20. 响应序列化错误

- 场景描述：验证响应数据序列化失败时的处理
- 测试数据：`包含不可序列化对象的响应数据`
- 预期结果：`返回 500，记录序列化错误`

### 性能验证

21. 响应时间验证（NFR-003）

- 场景描述：验证管理端点响应时间符合性能要求
- 测试数据：`正常负载下的端点调用`
- 预期结果：`响应时间 < 200ms（NFR-003 要求）`

22. 并发访问处理

- 场景描述：验证多个并发请求的处理能力
- 测试数据：`10 个并发请求同时访问管理端点`
- 预期结果：`所有请求成功响应，无阻塞或死锁`

23. 大量服务数据处理

- 场景描述：验证大量服务时的响应性能
- 测试数据：`Mock 50+ 服务的状态和健康数据`
- 预期结果：`响应时间仍在可接受范围，数据完整`

### 集成验证

24. 端到端集成测试

- 场景描述：验证管理端点与实际启动器组件的完整集成
- 测试数据：`启动实际 launcher 实例，真实 orchestrator 和 health monitor`
- 预期结果：`端点返回真实的服务状态和健康数据`

## 边界条件与特殊场景

### 数据边界处理
- 服务名称包含特殊字符
- 极长的服务名称或路径
- PID 和端口号边界值（0, 65535）
- 时间戳精度和时区处理

### 网络相关
- 请求头验证（Content-Type, Accept）
- HTTP 方法限制（仅支持 GET）
- 查询参数处理（如支持过滤）

### 配置相关
- 配置文件不存在或损坏
- 环境变量优先级
- 配置热重载影响

## 测试优先级

- **P0（必须）**：场景 1-2, 6-7, 10-11, 17-18
- **P1（重要）**：场景 3-5, 8-9, 12-16, 19-20
- **P2（可选）**：场景 21-24，边界条件场景

## API 合约定义

### 请求格式
```http
GET /admin/launcher/status HTTP/1.1
Accept: application/json

GET /admin/launcher/health HTTP/1.1  
Accept: application/json
```

### 响应格式示例
```json
// /admin/launcher/status 响应
{
  "launcher_status": "running|partial|starting|stopped",
  "services": [
    {
      "name": "api-gateway",
      "status": "running",
      "uptime_seconds": 1800,
      "started_at": "2025-09-02T15:30:00Z",
      "pid": 12345,
      "port": 8000
    }
  ],
  "total_services": 2,
  "running_services": 1,
  "timestamp": "2025-09-02T16:40:00Z"
}

// /admin/launcher/health 响应
{
  "cluster_status": "healthy|degraded|unhealthy|unknown",
  "services": [
    {
      "service_name": "api-gateway",
      "status": "healthy",
      "response_time_ms": 25.0,
      "last_check": "2025-09-02T16:39:45Z",
      "error": null
    }
  ],
  "healthy_count": 2,
  "total_count": 3,
  "timestamp": "2025-09-02T16:40:00Z"
}
```

## 测试实施建议

### Mock 策略
- 对 `get_orchestrator()` 和 `get_health_monitor()` 进行依赖注入 Mock
- 使用 `FastAPI TestClient` 进行端到端 API 测试
- 通过配置 Mock 控制不同的环境和错误场景

### 测试数据管理
- 创建测试数据工厂函数生成标准的服务状态和健康数据
- 使用参数化测试覆盖不同的状态组合
- 实现测试夹具自动清理资源

### 断言策略
- JSON 响应结构验证：使用 JSONSchema 或 Pydantic 模型验证
- 时间相关断言：允许合理的时间误差（±1 秒）
- 性能断言：使用时间测量和统计分析

---
*此测试场景文档用于指导 Task 8 管理端点的 TDD 实施*