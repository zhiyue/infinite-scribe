# 命令类型定义

## 命名格式

```
Command.<Domain>.<AggregateRoot>.<OptionalSubAggregate>.<ActionInImperative>
```

**设计原则**：
- 使用祈使语态（Request, Confirm, Update, Create）
- 遵循点式命名约定
- 与事件类型形成明确映射关系

## 创世阶段命令类型

### Stage 0 - 创意种子
```yaml
Command.Genesis.Session.Start                    # 开始创世会话
Command.Genesis.Session.Seed.Request             # 请求生成创意种子
Command.Genesis.Session.Concept.Confirm          # 确认高概念
Command.Genesis.Session.Stage.Complete           # 完成阶段
```

### Stage 1 - 立意主题
```yaml
Command.Genesis.Session.Theme.Request            # 请求生成主题
Command.Genesis.Session.Theme.Revise             # 修订主题
Command.Genesis.Session.Theme.Confirm            # 确认主题
```

### Stage 2 - 世界观
```yaml
Command.Genesis.Session.World.Request            # 请求构建世界观
Command.Genesis.Session.World.Update             # 更新世界观
Command.Genesis.Session.World.Confirm            # 确认世界观
```

### Stage 3 - 人物
```yaml
Command.Genesis.Session.Character.Request        # 请求设计人物
Command.Genesis.Session.Character.Update         # 更新人物
Command.Genesis.Session.Character.Confirm        # 确认人物
Command.Genesis.Session.CharacterNetwork.Create  # 创建关系网络
```

### Stage 4 - 情节
```yaml
Command.Genesis.Session.Plot.Request             # 请求构建情节
Command.Genesis.Session.Plot.Update              # 更新情节
Command.Genesis.Session.Plot.Confirm             # 确认情节
```

### Stage 5 - 细节
```yaml
Command.Genesis.Session.Details.Request          # 请求批量生成
Command.Genesis.Session.Details.Confirm          # 确认细节
```

## 通用命令

```yaml
Command.Genesis.Session.Finish                   # 完成创世
Command.Genesis.Session.Fail                     # 标记失败
Command.Genesis.Session.Branch.Create            # 创建版本分支
```

## Python 枚举定义

```python
from enum import Enum

class CommandType(Enum):
    """命令类型枚举，value使用点式命名"""

    # Stage 0 - 创意种子
    SESSION_START = "Command.Genesis.Session.Start"
    SEED_REQUEST = "Command.Genesis.Session.Seed.Request"
    CONCEPT_CONFIRM = "Command.Genesis.Session.Concept.Confirm"
    STAGE_COMPLETE = "Command.Genesis.Session.Stage.Complete"

    # Stage 1 - 立意主题
    THEME_REQUEST = "Command.Genesis.Session.Theme.Request"
    THEME_REVISE = "Command.Genesis.Session.Theme.Revise"
    THEME_CONFIRM = "Command.Genesis.Session.Theme.Confirm"

    # Stage 2 - 世界观
    WORLD_REQUEST = "Command.Genesis.Session.World.Request"
    WORLD_UPDATE = "Command.Genesis.Session.World.Update"
    WORLD_CONFIRM = "Command.Genesis.Session.World.Confirm"

    # Stage 3 - 人物
    CHARACTER_REQUEST = "Command.Genesis.Session.Character.Request"
    CHARACTER_UPDATE = "Command.Genesis.Session.Character.Update"
    CHARACTER_CONFIRM = "Command.Genesis.Session.Character.Confirm"
    CHARACTER_NETWORK_CREATE = "Command.Genesis.Session.CharacterNetwork.Create"

    # Stage 4 - 情节
    PLOT_REQUEST = "Command.Genesis.Session.Plot.Request"
    PLOT_UPDATE = "Command.Genesis.Session.Plot.Update"
    PLOT_CONFIRM = "Command.Genesis.Session.Plot.Confirm"

    # Stage 5 - 细节
    DETAILS_REQUEST = "Command.Genesis.Session.Details.Request"
    DETAILS_CONFIRM = "Command.Genesis.Session.Details.Confirm"

    # 通用命令
    SESSION_FINISH = "Command.Genesis.Session.Finish"
    SESSION_FAIL = "Command.Genesis.Session.Fail"
    BRANCH_CREATE = "Command.Genesis.Session.Branch.Create"

    @classmethod
    def from_string(cls, value: str):
        """从字符串获取枚举值"""
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"Unknown CommandType value: {value}")
```

## 命令结构规范

### 基础命令字段
```python
{
    "command_id": "UUID",           # 命令唯一标识
    "command_type": "点式命名字符串",  # CommandType.value
    "aggregate_id": "UUID",         # session_id 或 novel_id
    "aggregate_type": "字符串",      # "GenesisSession"
    "payload": "JSONB",            # 命令具体内容
    "correlation_id": "UUID",       # 流程关联ID
    "causation_id": "UUID",         # 触发此命令的事件ID
    "user_id": "UUID",             # 用户ID
    "metadata": "JSONB"            # 扩展元数据
}
```

### Payload 结构示例

#### 开始会话命令
```python
# Command.Genesis.Session.Start
{
    "user_id": "UUID",
    "initial_input": "string",      # 用户初始输入
    "preferences": {                # 用户偏好
        "genre": "string",
        "length": "string",
        "style": "string"
    }
}
```

#### 请求生成种子命令
```python
# Command.Genesis.Session.Seed.Request
{
    "session_id": "UUID",
    "user_id": "UUID",
    "user_input": "string",         # 用户输入
    "preferences": "object",        # 用户偏好
    "context": {                    # 上下文信息
        "previous_attempts": "int",
        "iteration_number": "int"
    }
}
```

#### 确认概念命令
```python
# Command.Genesis.Session.Concept.Confirm
{
    "session_id": "UUID",
    "novel_id": "UUID",
    "concept_id": "UUID",
    "user_feedback": "string",      # 用户反馈（可选）
    "modifications": "object"       # 用户修改（可选）
}
```

## 使用说明

1. **新增命令类型**：在枚举中添加新值，遵循命名格式
2. **命令处理**：使用 `CommandType.from_string()` 进行反序列化
3. **映射查找**：参考 [event-types.md](event-types.md) 中的映射表
4. **数据验证**：确保 payload 结构符合对应命令的规范