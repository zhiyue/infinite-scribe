# 任务 5 测试场景 - 适配器层

**关联任务**：5  
**关联需求**：FR-001, FR-002, FR-004, NFR-002  
**生成时间**：2025-01-09T22:10:00+08:00

## BaseAdapter 接口测试

### 1. 适配器基类抽象方法验证

- 场景描述：验证 BaseAdapter 定义了必要的抽象方法
- 测试数据：`BaseAdapter("test", {})`
- 预期结果：`TypeError: Can't instantiate abstract class`

### 2. 适配器基类初始化状态

- 场景描述：验证适配器初始化后的默认状态
- 测试数据：
  ```python
  class TestAdapter(BaseAdapter):
      async def start(self): return True
      async def stop(self, timeout=30): return True  
      async def health_check(self): return {}
  adapter = TestAdapter("test", {"key": "value"})
  ```
- 预期结果：`adapter.name == "test" and adapter.status == ComponentStatus.INIT`

### 3. 适配器配置获取

- 场景描述：验证适配器能正确获取配置信息
- 测试数据：`TestAdapter("api", {"host": "127.0.0.1", "port": 8000})`
- 预期结果：`adapter.config["host"] == "127.0.0.1" and adapter.config["port"] == 8000`

## ApiAdapter 单进程模式测试

### 4. 单进程模式启动成功

- 场景描述：验证单进程模式能成功启动 uvicorn 服务器
- 测试数据：
  ```python
  config = {
      "mode": "single",
      "host": "127.0.0.1", 
      "port": 8000,
      "app": "src.api.main:app"
  }
  adapter = ApiAdapter(config)
  ```
- 预期结果：`await adapter.start() == True and adapter.status == ComponentStatus.RUNNING`

### 5. 单进程模式停止成功

- 场景描述：验证单进程模式能优雅停止服务器
- 测试数据：已启动的单进程 ApiAdapter 实例
- 预期结果：`await adapter.stop() == True and adapter.status == ComponentStatus.STOPPED`

### 6. 单进程模式健康检查

- 场景描述：验证单进程模式健康检查返回正确状态
- 测试数据：运行中的单进程 ApiAdapter 实例
- 预期结果：`health_result["status"] == "healthy" and health_result["mode"] == "single"`

### 7. 单进程模式启动失败处理

- 场景描述：验证单进程模式启动失败时的错误处理
- 测试数据：
  ```python
  config = {
      "mode": "single",
      "app": "invalid.module:app"  # 无效模块
  }
  ```
- 预期结果：`await adapter.start() == False and adapter.status == ComponentStatus.ERROR`

## ApiAdapter 多进程模式测试

### 8. 多进程模式启动成功

- 场景描述：验证多进程模式能成功启动子进程
- 测试数据：
  ```python
  config = {
      "mode": "multi",
      "host": "127.0.0.1",
      "port": 8001
  }
  adapter = ApiAdapter(config)
  ```
- 预期结果：`await adapter.start() == True and adapter._process is not None`

### 9. 多进程模式优雅停止

- 场景描述：验证多进程模式优雅停止（SIGTERM）
- 测试数据：运行中的多进程 ApiAdapter，`timeout=10`
- 预期结果：`await adapter.stop(10) == True and process.terminate.called == True`

### 10. 多进程模式超时强制终止

- 场景描述：验证超时后强制终止进程（SIGKILL）
- 测试数据：mock process.wait() 抛出 `asyncio.TimeoutError`
- 预期结果：`process.kill.called == True`

### 11. 多进程模式进程组管理

- 场景描述：验证多进程模式创建新进程组
- 测试数据：多进程 ApiAdapter 启动参数
- 预期结果：`create_subprocess_exec.called_with(preexec_fn=os.setsid)`

### 12. 多进程模式端口配置

- 场景描述：验证多进程模式使用正确的端口配置
- 测试数据：`config = {"mode": "multi", "port": 8080}`
- 预期结果：`subprocess_args 包含 "--port", "8080"`

## AgentsAdapter 测试

### 13. AgentsAdapter 初始化

- 场景描述：验证 AgentsAdapter 正确初始化并设置 agent 列表
- 测试数据：`config = {"agents": ["worldsmith", "writer"]}`
- 预期结果：`adapter.agent_names == ["worldsmith", "writer"]`

### 14. AgentsAdapter 启动所有 Agents

- 场景描述：验证 AgentsAdapter 能启动指定的 agents
- 测试数据：配置包含 `["worldsmith", "writer"]` 的 AgentsAdapter
- 预期结果：`launcher.load_agents.called_with(["worldsmith", "writer"]) and launcher.start_all.called`

### 15. AgentsAdapter 启动默认 Agents

- 场景描述：验证未指定 agents 时启动所有可用 agents
- 测试数据：`config = {}` (无 agents 配置)
- 预期结果：`launcher.load_agents.called_with(None)`

### 16. AgentsAdapter 停止所有 Agents

- 场景描述：验证 AgentsAdapter 能正确停止所有 agents
- 测试数据：运行中的 AgentsAdapter 实例
- 预期结果：`await adapter.stop() == True and launcher.stop_all.called`

### 17. AgentsAdapter 健康检查

- 场景描述：验证 AgentsAdapter 健康检查返回 agents 状态
- 测试数据：运行中的 AgentsAdapter，包含 2 个 agents
- 预期结果：`health_result["total_agents"] == 2 and "agents" in health_result`

### 18. AgentsAdapter 启动失败处理

- 场景描述：验证 AgentsAdapter 启动失败时的错误处理
- 测试数据：mock `launcher.start_all()` 抛出异常
- 预期结果：`await adapter.start() == False and adapter.status == ComponentStatus.ERROR`

## 状态管理测试

### 19. 适配器状态转换

- 场景描述：验证适配器在启动过程中的状态转换
- 测试数据：ApiAdapter 从初始化到启动完成
- 预期结果：`状态序列: INIT → STARTING → RUNNING`

### 20. 适配器状态查询

- 场景描述：验证 get_status() 方法返回当前状态
- 测试数据：不同状态的适配器实例
- 预期结果：`adapter.get_status() == adapter.status`

### 21. 错误状态处理

- 场景描述：验证出现错误时状态正确设置为 ERROR
- 测试数据：模拟启动失败的适配器
- 预期结果：`adapter.status == ComponentStatus.ERROR`

## 配置验证测试

### 22. ApiAdapter 配置默认值

- 场景描述：验证 ApiAdapter 配置的默认值设置
- 测试数据：`config = {"mode": "single"}`
- 预期结果：`adapter.host == "127.0.0.1" and adapter.port == 8000`

### 23. 无效模式处理

- 场景描述：验证无效运行模式的处理
- 测试数据：`config = {"mode": "invalid"}`
- 预期结果：默认使用 multi 模式或抛出配置错误

### 24. 必要配置缺失

- 场景描述：验证缺少必要配置时的错误处理
- 测试数据：`config = {}` (空配置)
- 预期结果：使用合理的默认值或抛出配置错误

## 集成测试

### 25. ApiAdapter 与 AgentsAdapter 协同

- 场景描述：验证两个适配器可以同时运行而不冲突
- 测试数据：同时启动的 ApiAdapter 和 AgentsAdapter
- 预期结果：`api_adapter.status == RUNNING and agents_adapter.status == RUNNING`

### 26. 资源清理验证

- 场景描述：验证适配器停止后正确清理资源
- 测试数据：启动后停止的适配器
- 预期结果：进程句柄被关闭，无资源泄漏

### 27. 并发启动停止

- 场景描述：验证多个适配器的并发启动和停止
- 测试数据：使用 `asyncio.gather()` 并发操作多个适配器
- 预期结果：所有操作成功完成，无竞态条件

## 性能测试

### 28. 启动时间测试

- 场景描述：验证适配器启动时间符合性能要求
- 测试数据：记录 `start()` 方法执行时间
- 预期结果：`启动时间 < 5秒`

### 29. 内存使用测试

- 场景描述：验证适配器运行时的内存使用合理
- 测试数据：监控适配器运行期间的内存占用
- 预期结果：内存使用稳定，无明显泄漏

### 30. 停止响应时间

- 场景描述：验证优雅停止的响应时间
- 测试数据：测量从发送停止信号到完全停止的时间
- 预期结果：`停止时间 < 30秒（默认超时）`