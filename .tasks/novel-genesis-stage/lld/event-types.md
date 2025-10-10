# 事件类型定义

## 命名格式

```
<Domain>.<AggregateRoot>.<OptionalSubAggregate>.<ActionInPastTense>
```

**设计原则**：
- 使用过去式（Started, Requested, Proposed, Confirmed）
- 遵循点式命名约定
- 表示已发生的业务事实

## 创世阶段事件类型

### Stage 0 - 创意种子
```yaml
Genesis.Session.Started                    # 创世会话开始（此时即创建 Novel 记录，status=GENESIS）
Genesis.Session.SeedRequested              # 请求生成创意种子
Genesis.Session.ConceptProposed            # AI提出高概念方案
Genesis.Session.ConceptConfirmed           # 用户确认高概念
Genesis.Session.StageCompleted             # 阶段完成
```

### Stage 1 - 立意主题
```yaml
Genesis.Session.Theme.Requested            # 请求生成主题
Genesis.Session.Theme.Proposed             # AI提出主题方案
Genesis.Session.Theme.Revised              # 主题被修订
Genesis.Session.Theme.Confirmed            # 主题确认
```

### Stage 2 - 世界观
```yaml
Genesis.Session.World.Requested            # 请求构建世界观
Genesis.Session.World.Proposed             # AI提出世界观设定
Genesis.Session.World.Updated              # 世界观更新
Genesis.Session.World.Confirmed            # 世界观确认
```

### Stage 3 - 人物
```yaml
Genesis.Session.Character.Requested        # 请求设计人物
Genesis.Session.Character.Proposed         # AI提出人物设定
Genesis.Session.Character.Updated          # 人物更新
Genesis.Session.Character.Confirmed        # 人物确认
Genesis.Session.CharacterNetwork.Created   # 关系网络生成
```

### Stage 4 - 情节
```yaml
Genesis.Session.Plot.Requested             # 请求构建情节
Genesis.Session.Plot.Proposed              # AI提出情节框架
Genesis.Session.Plot.Updated               # 情节更新
Genesis.Session.Plot.Confirmed             # 情节确认
```

### Stage 5 - 细节
```yaml
Genesis.Session.Details.Requested          # 请求批量生成
Genesis.Session.Details.Generated          # 细节生成完成
Genesis.Session.Details.Confirmed          # 细节确认
```

## 通用事件

```yaml
Genesis.Session.Finished                   # 创世完成
Genesis.Session.Failed                     # 创世失败
Genesis.Session.BranchCreated              # 版本分支创建
```

## 命令到事件映射

```python
# 完整的命令→事件映射表
COMMAND_EVENT_MAPPING = {
    # Stage 0 - 创意种子
    "Command.Genesis.Session.Start": "Genesis.Session.Started",
    "Command.Genesis.Session.Seed.Request": "Genesis.Session.SeedRequested",
    "Command.Genesis.Session.Concept.Confirm": "Genesis.Session.ConceptConfirmed",
    "Command.Genesis.Session.Stage.Complete": "Genesis.Session.StageCompleted",

    # Stage 1 - 立意主题
    "Command.Genesis.Session.Theme.Request": "Genesis.Session.Theme.Requested",
    "Command.Genesis.Session.Theme.Revise": "Genesis.Session.Theme.Revised",
    "Command.Genesis.Session.Theme.Confirm": "Genesis.Session.Theme.Confirmed",

    # Stage 2 - 世界观
    "Command.Genesis.Session.World.Request": "Genesis.Session.World.Requested",
    "Command.Genesis.Session.World.Update": "Genesis.Session.World.Updated",
    "Command.Genesis.Session.World.Confirm": "Genesis.Session.World.Confirmed",

    # Stage 3 - 人物
    "Command.Genesis.Session.Character.Request": "Genesis.Session.Character.Requested",
    "Command.Genesis.Session.Character.Update": "Genesis.Session.Character.Updated",
    "Command.Genesis.Session.Character.Confirm": "Genesis.Session.Character.Confirmed",
    "Command.Genesis.Session.CharacterNetwork.Create": "Genesis.Session.CharacterNetwork.Created",

    # Stage 4 - 情节
    "Command.Genesis.Session.Plot.Request": "Genesis.Session.Plot.Requested",
    "Command.Genesis.Session.Plot.Update": "Genesis.Session.Plot.Updated",
    "Command.Genesis.Session.Plot.Confirm": "Genesis.Session.Plot.Confirmed",

    # Stage 5 - 细节
    "Command.Genesis.Session.Details.Request": "Genesis.Session.Details.Requested",
    "Command.Genesis.Session.Details.Confirm": "Genesis.Session.Details.Confirmed",

    # 通用映射
    "Command.Genesis.Session.Finish": "Genesis.Session.Finished",
    "Command.Genesis.Session.Fail": "Genesis.Session.Failed",
    "Command.Genesis.Session.Branch.Create": "Genesis.Session.BranchCreated"
}

def get_result_event_type(command_type: str) -> str:
    """根据命令类型获取对应的结果事件类型"""
    return COMMAND_EVENT_MAPPING.get(command_type)
```

## Python 枚举定义

```python
from enum import Enum

class GenesisEventType(Enum):
    """创世事件类型枚举，value使用点式命名"""

    # Stage 0 - 创意种子
    SESSION_STARTED = "Genesis.Session.Started"
    SEED_REQUESTED = "Genesis.Session.SeedRequested"
    CONCEPT_PROPOSED = "Genesis.Session.ConceptProposed"
    CONCEPT_CONFIRMED = "Genesis.Session.ConceptConfirmed"
    STAGE_COMPLETED = "Genesis.Session.StageCompleted"

    # Stage 1 - 立意主题
    THEME_REQUESTED = "Genesis.Session.Theme.Requested"
    THEME_PROPOSED = "Genesis.Session.Theme.Proposed"
    THEME_REVISED = "Genesis.Session.Theme.Revised"
    THEME_CONFIRMED = "Genesis.Session.Theme.Confirmed"

    # Stage 2 - 世界观
    WORLD_REQUESTED = "Genesis.Session.World.Requested"
    WORLD_PROPOSED = "Genesis.Session.World.Proposed"
    WORLD_UPDATED = "Genesis.Session.World.Updated"
    WORLD_CONFIRMED = "Genesis.Session.World.Confirmed"

    # Stage 3 - 人物
    CHARACTER_REQUESTED = "Genesis.Session.Character.Requested"
    CHARACTER_PROPOSED = "Genesis.Session.Character.Proposed"
    CHARACTER_UPDATED = "Genesis.Session.Character.Updated"
    CHARACTER_CONFIRMED = "Genesis.Session.Character.Confirmed"
    CHARACTER_NETWORK_CREATED = "Genesis.Session.CharacterNetwork.Created"

    # Stage 4 - 情节
    PLOT_REQUESTED = "Genesis.Session.Plot.Requested"
    PLOT_PROPOSED = "Genesis.Session.Plot.Proposed"
    PLOT_UPDATED = "Genesis.Session.Plot.Updated"
    PLOT_CONFIRMED = "Genesis.Session.Plot.Confirmed"

    # Stage 5 - 细节
    DETAILS_REQUESTED = "Genesis.Session.Details.Requested"
    DETAILS_GENERATED = "Genesis.Session.Details.Generated"
    DETAILS_CONFIRMED = "Genesis.Session.Details.Confirmed"

    # 通用事件
    SESSION_FINISHED = "Genesis.Session.Finished"
    SESSION_FAILED = "Genesis.Session.Failed"
    BRANCH_CREATED = "Genesis.Session.BranchCreated"

    @classmethod
    def from_string(cls, value: str):
        """从字符串获取枚举值"""
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"Unknown GenesisEventType value: {value}")
```

## 事件结构规范

### 基础事件字段
```python
{
    "event_id": "UUID",               # 事件唯一标识
    "event_type": "点式命名字符串",      # GenesisEventType.value
    "aggregate_id": "UUID",           # session_id
    "aggregate_type": "字符串",        # "GenesisSession"
    "aggregate_version": "int",       # 聚合版本号
    "payload": "JSONB",              # 事件具体内容
    "correlation_id": "UUID",         # 流程关联ID
    "causation_id": "UUID",           # 触发此事件的命令/事件ID
    "user_id": "UUID",               # 用户ID
    "occurred_at": "timestamp",       # 发生时间
    "metadata": "JSONB"              # 扩展元数据
}
```

### Payload 结构示例

#### 会话开始事件
```python
# Genesis.Session.Started
{
    "session_id": "UUID",
    "novel_id": "UUID",               # 创建的小说ID
    "stage": "Stage_0",
    "user_id": "UUID",
    "content": {
        "initial_input": "string",
        "preferences": "object"
    },
    "timestamp": "ISO-8601"
}
```

#### 概念提出事件
```python
# Genesis.Session.ConceptProposed
{
    "session_id": "UUID",
    "novel_id": "UUID",
    "stage": "Stage_0",
    "user_id": "UUID",
    "content": {
        "concept_id": "UUID",
        "title": "string",
        "premise": "string",
        "genre": "string",
        "target_audience": "string",
        "themes": ["array"],
        "tone": "string",
        "estimated_length": "string",
        "unique_elements": ["array"]
    },
    "quality_score": "float",         # 0-10
    "generation_metadata": {
        "model_version": "string",
        "generation_time_ms": "int",
        "confidence_score": "float",
        "iteration_count": "int"
    },
    "timestamp": "ISO-8601"
}
```

#### 主题提出事件
```python
# Genesis.Session.Theme.Proposed
{
    "session_id": "UUID",
    "novel_id": "UUID",
    "stage": "Stage_1",
    "user_id": "UUID",
    "content": {
        "theme_id": "UUID",
        "core_theme": "string",
        "sub_themes": ["array"],
        "philosophical_questions": ["array"],
        "emotional_core": "string",
        "target_impact": "string",
        "narrative_techniques": ["array"]
    },
    "quality_score": "float",
    "generation_metadata": "object",
    "timestamp": "ISO-8601"
}
```

## Topic 架构

### 领域总线（对外暴露）
```yaml
genesis.session.events:
  description: "承载 Genesis.Session.* 等领域事实"
  consumers: ["UI", "SSE", "审计系统"]
  partition_key: "session_id"
```

### 能力总线（内部）
```yaml
# 各能力的命名空间事件（参考 events.md）
genesis.outline.events:     # Outliner.*.* 事件
genesis.writer.events:      # Writer.*.* 事件
genesis.review.events:      # Review.*.* 事件
genesis.world.events:       # Worldbuilder.*.* 事件
genesis.character.events:   # Character.*.* 事件
genesis.plot.events:        # Plot.*.* 事件
```

## 使用说明

1. **事件发布**：所有 `Genesis.Session.*` 事件发布到 `genesis.session.events` topic
2. **事件消费**：UI/SSE 只监听领域总线，不直接消费能力总线
3. **映射查找**：使用 `get_result_event_type()` 获取命令对应的事件类型
4. **版本控制**：`aggregate_version` 确保事件顺序，支持乐观锁