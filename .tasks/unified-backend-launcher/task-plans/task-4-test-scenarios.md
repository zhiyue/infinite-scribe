# Task 4 测试场景 - CLI（最小集）

生成时间：2025-09-01T23:55:00Z  
关联任务：4  
关联需求：FR-001, FR-002, NFR-003  
测试场景数量：25

## Up 命令测试场景

### 1. 基本up命令解析

- 场景描述：验证up命令的基本参数解析功能
- 测试数据：`is-launcher up`
- 预期结果：`{"command": "up", "mode": "multi", "components": ["api", "agents"], "agents": null, "reload": false}`

### 2. Single模式启动

- 场景描述：验证单进程模式参数解析
- 测试数据：`is-launcher up --mode single`
- 预期结果：`{"command": "up", "mode": "single", "components": ["api", "agents"], "agents": null, "reload": false}`

### 3. Multi模式启动

- 场景描述：验证多进程模式参数解析
- 测试数据：`is-launcher up --mode multi`
- 预期结果：`{"command": "up", "mode": "multi", "components": ["api", "agents"], "agents": null, "reload": false}`

### 4. 组件选择解析

- 场景描述：验证components参数的逗号分隔解析
- 测试数据：`is-launcher up --components api,agents`
- 预期结果：`{"components": ["api", "agents"]}`

### 5. 单组件选择

- 场景描述：验证单个组件选择解析
- 测试数据：`is-launcher up --components api`
- 预期结果：`{"components": ["api"]}`

### 6. Agent列表解析

- 场景描述：验证agents参数的逗号分隔解析
- 测试数据：`is-launcher up --agents writer,editor,analyzer`
- 预期结果：`{"agents": ["writer", "editor", "analyzer"]}`

### 7. 热重载标志

- 场景描述：验证reload标志解析
- 测试数据：`is-launcher up --reload`
- 预期结果：`{"reload": true}`

### 8. 复合参数组合

- 场景描述：验证多个参数同时使用的解析
- 测试数据：`is-launcher up --mode single --components api --agents writer,editor --reload`
- 预期结果：`{"mode": "single", "components": ["api"], "agents": ["writer", "editor"], "reload": true}`

### 9. 无效模式参数

- 场景描述：验证无效mode参数的错误处理
- 测试数据：`is-launcher up --mode invalid`
- 预期结果：`SystemExit with error message containing "invalid choice: 'invalid'"`

### 10. 空组件列表

- 场景描述：验证空组件列表的处理
- 测试数据：`is-launcher up --components ""`
- 预期结果：`{"components": [""]}`

## Down 命令测试场景

### 11. 基本down命令

- 场景描述：验证down命令的基本功能
- 测试数据：`is-launcher down`
- 预期结果：`{"command": "down", "grace": 10}`

### 12. 自定义grace时间

- 场景描述：验证grace参数的整数解析
- 测试数据：`is-launcher down --grace 15`
- 预期结果：`{"command": "down", "grace": 15}`

### 13. 零grace时间

- 场景描述：验证零grace时间的处理
- 测试数据：`is-launcher down --grace 0`
- 预期结果：`{"grace": 0}`

### 14. 负数grace时间

- 场景描述：验证负数grace时间的处理
- 测试数据：`is-launcher down --grace -5`
- 预期结果：`{"grace": -5}`

## Status 命令测试场景

### 15. 基本status命令

- 场景描述：验证status命令的基本功能
- 测试数据：`is-launcher status`
- 预期结果：`{"command": "status", "watch": false}`

### 16. Watch模式状态查询

- 场景描述：验证watch标志的解析
- 测试数据：`is-launcher status --watch`
- 预期结果：`{"command": "status", "watch": true}`

## Logs 命令测试场景

### 17. API组件日志

- 场景描述：验证api组件日志查看
- 测试数据：`is-launcher logs api`
- 预期结果：`{"command": "logs", "component": "api"}`

### 18. Agents组件日志

- 场景描述：验证agents组件日志查看
- 测试数据：`is-launcher logs agents`
- 预期结果：`{"command": "logs", "component": "agents"}`

### 19. 无效组件日志

- 场景描述：验证无效组件名称的错误处理
- 测试数据：`is-launcher logs invalid`
- 预期结果：`SystemExit with error message containing "invalid choice: 'invalid'"`

### 20. 缺失组件参数

- 场景描述：验证logs命令缺少组件参数的错误处理
- 测试数据：`is-launcher logs`
- 预期结果：`SystemExit with error message about required positional argument`

## 性能测试场景

### 21. CLI响应时间测试

- 场景描述：验证CLI初始化响应时间满足NFR要求
- 测试数据：
```python
import time
start = time.time()
cli = LauncherCLI()
cli.setup_parser()
elapsed = (time.time() - start) * 1000
```
- 预期结果：`elapsed < 100  # milliseconds (NFR-001)`

### 22. 参数解析性能测试

- 场景描述：验证复杂参数解析的响应时间
- 测试数据：
```python
start = time.time()
args = parser.parse_args(['up', '--mode', 'single', '--components', 'api,agents', '--agents', 'writer,editor', '--reload'])
elapsed = (time.time() - start) * 1000
```
- 预期结果：`elapsed < 50  # milliseconds (NFR-003)`

## 错误处理测试场景

### 23. 未指定命令

- 场景描述：验证不提供任何命令时的处理
- 测试数据：`is-launcher`
- 预期结果：`help message displayed and exit code 1`

### 24. 无效命令

- 场景描述：验证无效命令的错误处理
- 测试数据：`is-launcher invalid_command`
- 预期结果：`SystemExit with error message about invalid choice`

### 25. 帮助信息显示

- 场景描述：验证help参数的正确显示
- 测试数据：`is-launcher --help`
- 预期结果：`help text contains "InfiniteScribe统一后端启动器" and exit code 0`

## 集成测试场景

### 26. 控制台脚本可用性

- 场景描述：验证is-launcher命令在安装后可用
- 测试数据：
```python
import subprocess
result = subprocess.run(['is-launcher', '--help'], capture_output=True, text=True)
```
- 预期结果：`result.returncode == 0 and "InfiniteScribe统一后端启动器" in result.stdout`

### 27. 命令调度正确性

- 场景描述：验证命令正确调度到对应处理函数
- 测试数据：
```python
with patch.object(cli, '_handle_up_command') as mock_up:
    cli.run(['up', '--mode', 'single'])
```
- 预期结果：`mock_up.assert_called_once()`

### 28. 异常处理覆盖

- 场景描述：验证CLI运行时异常的优雅处理
- 测试数据：
```python
with patch.object(cli, '_handle_up_command', side_effect=Exception("test error")):
    result = cli.run(['up'])
```
- 预期结果：`result == 1 and error message printed to stderr`

## 验收标准映射

### FR-001 相关测试
- 场景1-10：统一服务启动管理的参数解析验证

### FR-002 相关测试  
- 场景4-6, 9-10：选择性服务控制的参数验证

### NFR-003 相关测试
- 场景21-22：CLI响应性能要求验证

### 错误处理标准
- 场景9, 19, 23-25：错误信息完整性和用户友好性验证

## 测试数据说明

- **参数格式**：所有测试数据使用标准命令行格式
- **预期结果**：以字典形式表示解析后的参数结构
- **性能测试**：包含具体的时间测量代码
- **错误测试**：明确期望的异常类型和错误信息内容

## 实施注意事项

1. **TDD流程**：每个场景应先编写测试（RED），再实现功能（GREEN），最后重构（REFACTOR）
2. **性能监控**：场景21-22需要实际性能测量，不能仅依赖断言
3. **错误覆盖**：确保所有错误场景都有对应的测试用例
4. **集成测试**：场景26需要在真实环境中验证控制台脚本安装
5. **Mock使用**：场景27-28需要适当使用mock来隔离测试范围