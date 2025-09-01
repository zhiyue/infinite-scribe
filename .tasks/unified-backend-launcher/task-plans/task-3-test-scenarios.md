# 任务 3 测试场景

生成时间：2025-09-01T23:30:00Z  
任务描述：启动器配置模型 - 定义LauncherConfigModel并集成现有配置系统  
关联需求：FR-006, NFR-004  

## 枚举类型测试场景

1. 启动模式枚举值验证

- 场景描述：验证LaunchMode枚举包含所有支持的启动模式
- 测试数据：`LaunchMode.SINGLE, LaunchMode.MULTI, LaunchMode.AUTO`
- 预期结果：`{"SINGLE": "single", "MULTI": "multi", "AUTO": "auto"}`

2. 组件类型枚举值验证

- 场景描述：验证ComponentType枚举包含所有支持的组件类型
- 测试数据：`ComponentType.API, ComponentType.AGENTS`
- 预期结果：`{"API": "api", "AGENTS": "agents"}`

3. 枚举字符串值类型检查

- 场景描述：确保枚举值为字符串类型，便于序列化
- 测试数据：`LaunchMode.SINGLE.value, ComponentType.API.value`
- 预期结果：`isinstance(value, str) == True`

## API配置模型测试场景

4. API配置默认值验证

- 场景描述：验证LauncherApiConfig使用正确的默认值
- 测试数据：`LauncherApiConfig()`
- 预期结果：`{"host": "0.0.0.0", "port": 8000, "reload": False}`

5. API配置自定义值设置

- 场景描述：验证API配置可以接受自定义参数值
- 测试数据：`LauncherApiConfig(host="127.0.0.1", port=9000, reload=True)`
- 预期结果：`{"host": "127.0.0.1", "port": 9000, "reload": True}`

6. API端口范围边界验证

- 场景描述：验证API端口必须在有效范围内
- 测试数据：`LauncherApiConfig(port=1023)` 和 `LauncherApiConfig(port=65536)`
- 预期结果：抛出`ValidationError`

7. API配置字段类型验证

- 场景描述：验证API配置字段类型严格检查
- 测试数据：`LauncherApiConfig(host=123, port="invalid", reload="yes")`
- 预期结果：抛出`ValidationError`

## Agents配置模型测试场景

8. Agents配置默认值验证

- 场景描述：验证LauncherAgentsConfig默认不启动任何Agent
- 测试数据：`LauncherAgentsConfig()`
- 预期结果：`{"names": None}`

9. Agents配置有效名称列表

- 场景描述：验证Agents配置接受有效的Agent名称列表
- 测试数据：`LauncherAgentsConfig(names=["worldsmith", "plotmaster"])`
- 预期结果：`{"names": ["worldsmith", "plotmaster"]}`

10. Agents名称格式验证

- 场景描述：验证Agent名称必须符合命名规范
- 测试数据：`LauncherAgentsConfig(names=["invalid@name", "name-with-special#chars"])`
- 预期结果：抛出`ValidationError`

11. Agents空列表拒绝验证

- 场景描述：验证不允许空的Agent名称列表
- 测试数据：`LauncherAgentsConfig(names=[])`
- 预期结果：抛出`ValidationError`

12. Agents名称长度限制验证

- 场景描述：验证Agent名称不能超过最大长度限制
- 测试数据：`LauncherAgentsConfig(names=["a" * 51])`
- 预期结果：抛出`ValidationError`

## 主配置模型测试场景

13. 启动器配置默认值验证

- 场景描述：验证LauncherConfigModel使用正确的默认配置
- 测试数据：`LauncherConfigModel()`
- 预期结果：`{"default_mode": "single", "components": ["api", "agents"], "health_interval": 1.0}`

14. 启动器配置自定义值设置

- 场景描述：验证启动器配置支持自定义各种参数
- 测试数据：`LauncherConfigModel(default_mode="multi", components=["api"], health_interval=2.5)`
- 预期结果：`{"default_mode": "multi", "components": ["api"], "health_interval": 2.5}`

15. 健康检查间隔范围验证

- 场景描述：验证健康检查间隔必须在合理范围内
- 测试数据：`LauncherConfigModel(health_interval=0.05)` 和 `LauncherConfigModel(health_interval=61.0)`
- 预期结果：抛出`ValidationError`

16. 组件列表空值拒绝验证

- 场景描述：验证不允许空的组件列表
- 测试数据：`LauncherConfigModel(components=[])`
- 预期结果：抛出`ValidationError`

17. 组件列表重复拒绝验证

- 场景描述：验证不允许重复的组件类型
- 测试数据：`LauncherConfigModel(components=["api", "api", "agents"])`
- 预期结果：抛出`ValidationError`

18. 嵌套配置模型访问验证

- 场景描述：验证可以正确访问嵌套的API和Agents配置
- 测试数据：`LauncherConfigModel().api.host` 和 `LauncherConfigModel().agents.names`
- 预期结果：`"0.0.0.0"` 和 `None`

## 配置系统集成测试场景

19. Settings包含启动器配置验证

- 场景描述：验证Settings类正确包含启动器配置字段
- 测试数据：`Settings()`
- 预期结果：`hasattr(settings, 'launcher') == True`

20. TOML配置文件加载验证

- 场景描述：验证能够从TOML配置文件正确加载启动器配置
- 测试数据：
```toml
[launcher]
default_mode = "multi"
health_interval = 2.0
[launcher.api]
host = "127.0.0.1"
port = 9000
```
- 预期结果：`{"default_mode": "multi", "health_interval": 2.0, "api": {"host": "127.0.0.1", "port": 9000}}`

21. 环境变量覆盖验证

- 场景描述：验证环境变量可以正确覆盖TOML配置
- 测试数据：`os.environ['LAUNCHER__DEFAULT_MODE'] = 'auto'` 和 `os.environ['LAUNCHER__API__PORT'] = '9001'`
- 预期结果：`{"default_mode": "auto", "api": {"port": 9001}}`

22. 嵌套环境变量命名验证

- 场景描述：验证嵌套配置的环境变量命名规则正确
- 测试数据：`LAUNCHER__AGENTS__NAMES` 和 `LAUNCHER__API__RELOAD`
- 预期结果：正确映射到`launcher.agents.names`和`launcher.api.reload`字段

23. 配置加载优先级验证

- 场景描述：验证配置加载优先级：环境变量 > TOML配置 > 默认值
- 测试数据：TOML设置`port=8000`，环境变量设置`LAUNCHER__API__PORT=9000`
- 预期结果：最终配置`port=9000`

## 边界情况和错误处理测试场景

24. 无效启动模式字符串验证

- 场景描述：验证配置中的无效启动模式被正确拒绝
- 测试数据：`{"launcher": {"default_mode": "invalid_mode"}}`
- 预期结果：抛出`ValidationError`包含有效选项列表

25. 类型转换错误处理验证

- 场景描述：验证配置类型转换错误的处理
- 测试数据：`{"launcher": {"health_interval": "not_a_number"}}`
- 预期结果：抛出`ValidationError`包含类型要求说明

26. 部分配置缺失处理验证

- 场景描述：验证部分配置缺失时使用默认值
- 测试数据：`{"launcher": {"default_mode": "multi"}}`（缺少api和agents配置）
- 预期结果：缺失的配置使用默认值

27. 配置模型实例化性能验证

- 场景描述：验证配置模型实例化时间在可接受范围内
- 测试数据：重复创建`LauncherConfigModel()`实例1000次
- 预期结果：总耗时 `< 100ms`

28. 配置序列化和反序列化验证

- 场景描述：验证配置模型可以正确序列化为JSON并反序列化
- 测试数据：`LauncherConfigModel().model_dump()` 和 `LauncherConfigModel.model_validate(data)`
- 预期结果：序列化后反序列化得到相同配置

## 集成验收测试场景

29. 完整配置流程端到端验证

- 场景描述：验证完整的配置加载、验证、访问流程
- 测试数据：完整的TOML配置文件 + 环境变量覆盖
- 预期结果：Settings实例包含正确合并后的启动器配置

30. 现有配置系统兼容性验证

- 场景描述：验证添加启动器配置不影响现有配置功能
- 测试数据：包含数据库、认证等现有配置的Settings实例
- 预期结果：现有配置字段和功能正常工作