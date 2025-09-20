# 编排代理 (Orchestrator Agent)

负责协调领域事件和能力任务的核心编排服务，实现命令到领域事件的投影和能力任务的分发。

## 🏗️ 架构概览

### 核心职责

- **事件处理**：消费领域总线和能力事件
- **命令映射**：将触发类领域事件投影为领域事实
- **任务分发**：向对应的能力主题发送能力任务
- **结果投影**：将能力结果投影为领域事实

### 架构图

```mermaid
graph TB
    subgraph "输入事件"
        A[领域事件 Command.Received]
        B[能力事件 Capability Envelope]
    end
    
    subgraph "OrchestratorAgent"
        C[process_message]
        D[_handle_domain_event]
        E[_handle_capability_event]
        F[CommandStrategyRegistry]
        G[CapabilityEventHandlers]
    end
    
    subgraph "输出动作"
        H[持久化领域事件]
        I[创建异步任务]
        J[发送能力消息]
        K[完成异步任务]
    end
    
    A --> D
    B --> E
    D --> F
    E --> G
    F --> H
    F --> I
    G --> J
    G --> K
```

## 📁 目录结构

```
orchestrator/
├── __init__.py           # 代理注册和导出
├── agent.py              # 主编排代理类
├── command_strategies.py # 命令处理策略
├── event_handlers.py     # 能力事件处理器
└── message_factory.py    # 消息工厂
```

## 🎯 核心组件

### OrchestratorAgent

主编排代理类，继承自 `BaseAgent`，负责处理两种类型的事件：

```mermaid
sequenceDiagram
    participant K as Kafka
    participant O as OrchestratorAgent
    participant DB as Database
    participant C as Capability Services
    
    K->>O: 领域事件 (Command.Received)
    O->>O: _handle_domain_event
    O->>DB: 持久化领域事实 (*Requested)
    O->>DB: 创建异步任务
    O->>K: 发送能力任务
    
    K->>O: 能力事件结果
    O->>O: _handle_capability_event
    O->>G: CapabilityEventHandlers
    G->>DB: 更新异步任务状态
    G->>DB: 持久化领域事实
    G->>K: 发送后续能力消息
```

### CommandStrategyRegistry

命令策略注册表，使用策略模式实现不同命令类型的处理逻辑：

```mermaid
classDiagram
    class CommandStrategyRegistry {
        +process_command()
        +register()
        -_strategies
    }
    
    class CommandStrategy {
        <<abstract>>
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    class CharacterRequestStrategy {
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    class ThemeRequestStrategy {
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    class StageValidationStrategy {
        +get_aliases() set[str]
        +process() CommandMapping
    }
    
    CommandStrategyRegistry --> CommandStrategy
    CharacterRequestStrategy --|> CommandStrategy
    ThemeRequestStrategy --|> CommandStrategy
    StageValidationStrategy --|> CommandStrategy
```

### CapabilityEventHandlers

能力事件处理器集合，处理不同类型的能力完成事件：

```mermaid
graph TD
    A[能力事件] --> B{事件类型判断}
    
    B -->|Character.Generated| C[handle_generation_completed]
    B -->|Theme.Generated| C
    B -->|Review.Quality.Evaluated| D[handle_quality_review_result]
    B -->|Review.Consistency.Checked| E[handle_consistency_check_result]
    
    C --> F[生成领域事件 Character.Proposed]
    C --> G[完成异步任务]
    C --> H[触发质量检查]
    
    D --> I{质量分数判断}
    I -->|通过| J[确认内容]
    I -->|未通过且仍有尝试| K[重新生成]
    I -->|达到最大尝试| L[标记失败]
    
    E --> M{一致性检查}
    M -->|通过| N[确认阶段]
    M -->|失败| O[标记阶段失败]
```

## 🔧 命令处理流程

### 1. 命令到事件的映射

```mermaid
flowchart TD
    A[接收命令] --> B[解析命令类型]
    B --> C[查找策略处理]
    C --> D[生成领域事实]
    D --> E[创建能力任务]
    E --> F[发送到能力总线]
```

### 2. 幂等性保护

- **领域事件**：通过 `correlation_id + event_type` 确保唯一性
- **异步任务**：检查已有 `RUNNING/PENDING` 状态的任务

### 3. 任务状态管理

```mermaid
stateDiagram-v2
    [*] --> RUNNING: 创建任务
    RUNNING --> COMPLETED: 处理完成
    RUNNING --> FAILED: 处理失败
    COMPLETED --> [*]
    FAILED --> [*]
```

## 🚀 使用示例

### 注册命令策略

```python
# 注册自定义命令策略
class CustomCommandStrategy(CommandStrategy):
    def get_aliases(self) -> set[str]:
        return {"Custom.Command"}
    
    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        return CommandMapping(
            requested_action="Custom.Requested",
            capability_message={
                "type": "Custom.Process.Requested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
            }
        )

# 注册到全局注册表
command_registry.register(CustomCommandStrategy())
```

### 处理能力事件

```python
# 扩展事件处理器
class CustomEventHandler:
    @staticmethod
    def handle_custom_event(msg_type: str, session_id: str, data: dict[str, Any]) -> EventAction | None:
        if msg_type == "Custom.Process.Completed":
            return EventAction(
                domain_event={
                    "scope_type": "GENESIS",
                    "session_id": session_id,
                    "event_action": "Custom.Completed",
                    "payload": data,
                },
                task_completion={
                    "correlation_id": data.get("correlation_id"),
                    "expect_task_prefix": "Custom.Process",
                    "result_data": data,
                }
            )
        return None
```

## 📊 监控和调试

### 关键日志点

- `orchestrator_ignored_message`: 忽略未知格式的消息
- `async_task_create_failed`: 异步任务创建失败
- `async_task_already_exists`: 检测到重复的异步任务

### 性能考虑

- 使用数据库连接池管理会话
- 批量处理领域事件持久化
- 异步任务状态更新采用乐观锁

## 🔗 相关模块

- **事件映射**: `src.common.events.mapping` - 统一事件映射配置
- **领域模型**: `src.models.event` - 领域事件模型
- **工作流模型**: `src.models.workflow` - 异步任务模型
- **基础代理**: `src.agents.base` - 代理基类

## 📝 注意事项

1. **幂等性**：所有关键操作都需要考虑幂等性保护
2. **错误处理**：能力任务创建失败时只记录警告，不中断主流程
3. **事件溯源**：领域事件通过 EventOutbox 模式确保可靠投递
4. **任务追踪**：每个能力任务都创建对应的 AsyncTask 记录用于追踪