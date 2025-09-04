# 事件设计详细实现

## 事件命名与序列化实现

为落实 HLD 的事件命名契约（点式命名）并确保代码到存储/传输层的一致性，这里给出实现细节与参考代码。

### 枚举与点式命名映射

```python
from enum import Enum

class GenesisEventType(Enum):
    # 枚举名使用大写下划线，value 使用点式命名
    GENESIS_SESSION_STARTED = "Genesis.Session.Started"
    GENESIS_SESSION_THEME_PROPOSED = "Genesis.Session.Theme.Proposed"
    GENESIS_SESSION_THEME_CONFIRMED = "Genesis.Session.Theme.Confirmed"

# 枚举 → 点式字符串
def to_event_type(enum_value: GenesisEventType) -> str:
    return enum_value.value  # "Genesis.Session.Started"

# 点式字符串 → 枚举
def from_event_type(event_type: str) -> GenesisEventType:
    for event in GenesisEventType:
        if event.value == event_type:
            return event
    raise ValueError(f"Unknown event type: {event_type}")
```

### 序列化层（双向映射）

```python
# 序列化层统一映射示例
class EventSerializer:
    """事件序列化器，负责枚举与点式命名的双向映射"""

    @staticmethod
    def serialize_for_storage(event: "DomainEvent") -> dict:
        """序列化到数据库/Kafka时，转换为点式命名"""
        return {
            "event_type": event.event_type.value,  # 枚举的value是点式字符串
            "payload": event.payload,
            # ... 其他字段
        }

    @staticmethod
    def deserialize_from_storage(data: dict) -> "DomainEvent":
        """从数据库/Kafka反序列化时，转换回枚举"""
        event_type = GenesisEventType.from_event_type(data["event_type"])
        return DomainEvent(
            event_type=event_type,  # 内部使用枚举
            payload=data["payload"],
            # ... 其他字段
        )
```

实现要点：

- 外部（Kafka/数据库）一律点式命名；内部可用枚举但其 value 必须是点式字符串。
- 边界（序列化/反序列化）负责统一转换；保留对历史枚举名称的兼容。

## 事件命名契约

**统一标准**：所有事件名称使用点式命名（dot notation），遵循 `docs/architecture/event-naming-conventions.md` 规范。

### 命名格式

```
<Domain>.<AggregateRoot>.<OptionalSubAggregate>.<ActionInPastTense>
```

### 实施要求

1. **Kafka Envelope**：`event_type` 字段必须使用点式命名
   - ✅ 正确：`Genesis.Session.Theme.Proposed`
   - ❌ 错误：`GENESIS_SESSION_THEME_PROPOSED`

2. **数据库存储**：
   - `domain_events` 表的 `event_type` 字段使用点式命名
   - `event_outbox` 表的 headers 中 `event_type` 使用点式命名

3. **代码实现与序列化**：
   - 实现细节已包含在上方"事件命名与序列化实现"章节

## 核心领域事件

创世阶段以 `Genesis.Session` 为聚合根，动作动词严格使用受控词表（Requested/Proposed/Confirmed/Updated/Completed/Finished/Failed/Branched 等）。

### 领域事件列表（Genesis.Session.*）

```yaml
# Stage 0 - 创意种子
Genesis.Session.Started                    # 创世会话开始（此时即创建 Novel 记录，status=GENESIS）
Genesis.Session.SeedRequested              # 请求生成创意种子
Genesis.Session.ConceptProposed            # AI提出高概念方案
Genesis.Session.ConceptConfirmed           # 用户确认高概念
Genesis.Session.StageCompleted             # 阶段完成

# Stage 1 - 立意主题
Genesis.Session.Theme.Requested            # 请求生成主题
Genesis.Session.Theme.Proposed             # AI提出主题方案
Genesis.Session.Theme.Revised              # 主题被修订
Genesis.Session.Theme.Confirmed            # 主题确认

# Stage 2 - 世界观
Genesis.Session.World.Requested            # 请求构建世界观
Genesis.Session.World.Proposed             # AI提出世界观设定
Genesis.Session.World.Updated              # 世界观更新
Genesis.Session.World.Confirmed            # 世界观确认

# Stage 3 - 人物
Genesis.Session.Character.Requested        # 请求设计人物
Genesis.Session.Character.Proposed         # AI提出人物设定
Genesis.Session.Character.Updated          # 人物更新
Genesis.Session.Character.Confirmed        # 人物确认
Genesis.Session.CharacterNetwork.Created   # 关系网络生成

# Stage 4 - 情节
Genesis.Session.Plot.Requested             # 请求构建情节
Genesis.Session.Plot.Proposed              # AI提出情节框架
Genesis.Session.Plot.Updated               # 情节更新
Genesis.Session.Plot.Confirmed             # 情节确认

# Stage 5 - 细节
Genesis.Session.Details.Requested          # 请求批量生成
Genesis.Session.Details.Generated          # 细节生成完成
Genesis.Session.Details.Confirmed          # 细节确认

# 通用事件
Genesis.Session.Finished                   # 创世完成
Genesis.Session.Failed                     # 创世失败
Genesis.Session.BranchCreated              # 版本分支创建
```

### 能力事件命名规范（内部使用）

各能力Agent使用独立命名空间，格式：`<Capability>.<Entity>.<Action>`

```yaml
# Outliner Agent
Outliner.Theme.GenerationRequested
Outliner.Theme.Generated
Outliner.Concept.GenerationRequested
Outliner.Concept.Generated

# Worldbuilder Agent
Worldbuilder.World.GenerationRequested
Worldbuilder.World.Generated
Worldbuilder.Rule.ValidationRequested
Worldbuilder.Rule.Validated

# Character Agent
Character.Design.GenerationRequested
Character.Design.Generated
Character.Relationship.AnalysisRequested
Character.Relationship.Generated

# Plot Agent
Plot.Structure.GenerationRequested
Plot.Structure.Generated
Plot.Node.GenerationRequested
Plot.Node.Generated

# Writer Agent
Writer.Content.GenerationRequested
Writer.Content.Generated
Writer.Content.RevisionRequested
Writer.Content.Revised

# Review Agent
Review.Quality.EvaluationRequested
Review.Quality.Evaluated
Review.Consistency.CheckRequested
Review.Consistency.Checked
```

## 事件负载结构

```python
{
    "event_id": "uuid",
    "event_type": "Genesis.Session.Theme.Proposed",  # 点式命名
    "aggregate_id": "session_id",
    "aggregate_type": "GenesisSession",
    "correlation_id": "flow_id",
    "causation_id": "previous_event_id",
    "payload": {
        "session_id": "uuid",
        "novel_id": "uuid",          # 创世开始即创建并返回 novel_id
        "stage": "Stage_0",
        "user_id": "uuid",
        "content": {},  # 具体内容
        "quality_score": 8.5,
        "timestamp": "ISO-8601"
    },
    "metadata": {
        "version": 1,
        "source": "genesis-agent",
        "trace_id": "uuid"
    }
}
```

## 事件与 Topic 映射（领域总线 + 能力总线）

### 命名一致性保证

- **事件类型**：始终使用点式命名，作为 Envelope/DomainEvent 的 `event_type` 字段
- **传输格式**：统一使用 JSON Envelope（已在 Agents 落地），Avro 作为 P2 选项
- **唯一真相源**：点式命名是事件类型的唯一标准格式
- **命名空间分离**：
  - 领域事件：`Genesis.Session.*` - 表示业务事实，对外可见
  - 能力事件：`Outliner.*`, `Worldbuilder.*`, `Character.*` 等 - 内部处理，不对外暴露

### Topic 架构

领域总线（Facts，对外暴露）：

- `genesis.session.events`（仅承载 Genesis.Session.* 等领域事实；UI/SSE/审计只订阅此总线）

能力总线（Capabilities，内部）：

- Outliner：`genesis.outline.tasks` / `genesis.outline.events`
- Writer：`genesis.writer.tasks` / `genesis.writer.events`
- Review（评论家）：`genesis.review.tasks` / `genesis.review.events`
- Worldbuilder：`genesis.world.tasks` / `genesis.world.events`
- Character：`genesis.character.tasks` / `genesis.character.events`
- Plot：`genesis.plot.tasks` / `genesis.plot.events`
- FactCheck：`genesis.factcheck.tasks` / `genesis.factcheck.events`
- Rewriter：`genesis.rewriter.tasks` / `genesis.rewriter.events`
- Worldsmith：`genesis.worldsmith.tasks` / `genesis.worldsmith.events`

### 路由职责（中央协调者/Orchestrator）

**映射原则**：

- 领域事件（Facts）：始终使用 `Genesis.Session.*` 命名空间，表示业务事实
- 能力事件（Capabilities）：使用各能力的命名空间（`Outliner.*`, `Worldbuilder.*`, `Character.*` 等），表示内部处理

**Orchestrator职责**：

1. **领域→能力映射**：
   - 消费 `genesis.session.events` 中的领域请求（如 `Genesis.Session.Theme.Requested`）
   - 转换为能力任务（如 `Outliner.Theme.GenerationRequested`）
   - 发布到对应能力的 `*.tasks` topic

2. **能力→领域归并**：
   - 消费各 `*.events` 的能力结果（如 `Outliner.Theme.Generated`）
   - 转换为领域事实（如 `Genesis.Session.Theme.Proposed`）
   - 发布回 `genesis.session.events`

3. **关联维护**：
   - 通过 `correlation_id` 关联领域事件与能力事件
   - 确保事件链路完整可追踪

### 示例映射（注意点式命名）

#### 领域事件 → 能力任务（Orchestrator负责映射）

```json
// 输入：领域请求事件
{
  "event_type": "Genesis.Session.Theme.Requested",    // 领域事件
  "topic": "genesis.session.events"
}

// Orchestrator映射输出：能力任务
{
  "event_type": "Outliner.Theme.GenerationRequested",  // 能力任务
  "topic": "genesis.outline.tasks",
  "correlation_id": "xxx"                              // 关联领域请求
}
```

#### 能力结果 → 领域事实（Orchestrator负责归并）

```json
// 输入：能力完成事件
{
  "event_type": "Outliner.Theme.Generated",            // 能力结果
  "topic": "genesis.outline.events"
}

// Orchestrator归并输出：领域事实
{
  "event_type": "Genesis.Session.Theme.Proposed",     // 领域事实
  "topic": "genesis.session.events"
}
```

#### 完整映射表

```yaml
# Stage 0: 创意种子
Genesis.Session.SeedRequested → Outliner.Concept.GenerationRequested
Outliner.Concept.Generated → Genesis.Session.ConceptProposed

# Stage 1: 立意主题
Genesis.Session.Theme.Requested → Outliner.Theme.GenerationRequested
Outliner.Theme.Generated → Genesis.Session.Theme.Proposed

# Stage 2: 世界观构建
Genesis.Session.World.Requested → Worldbuilder.World.GenerationRequested
Worldbuilder.World.Generated → Genesis.Session.World.Proposed
Worldbuilder.Rule.Validated → Genesis.Session.World.Updated

# Stage 3: 人物设计
Genesis.Session.Character.Requested → Character.Design.GenerationRequested
Character.Design.Generated → Genesis.Session.Character.Proposed
Character.Relationship.Generated → Genesis.Session.CharacterNetwork.Created

# Stage 4: 情节框架
Genesis.Session.Plot.Requested → Plot.Structure.GenerationRequested
Plot.Structure.Generated → Genesis.Session.Plot.Proposed
Plot.Node.Generated → Genesis.Session.Plot.Updated

# Stage 5: 细节生成
Genesis.Session.Details.Requested → Writer.Content.GenerationRequested
Writer.Content.Generated → Genesis.Session.Details.Generated

# 质量控制（跨阶段）
Review.Quality.Evaluated → Genesis.Session.*.Updated (根据上下文)
Review.Consistency.Checked → Genesis.Session.*.ValidationCompleted
```

**注意事项**：

1. 所有 `Genesis.Session.*` 事件仅在 `genesis.session.events` topic
2. 所有能力事件分布在各自的 topic（如 `genesis.outline.tasks/events`）
3. Orchestrator维护映射表，确保双向转换的一致性
4. correlation_id贯穿整个事件链，保证可追踪性

注意：DLT 使用统一后缀 `.DLT`（如 `genesis.writer.events.DLT`）。分区键：会话级事件用 `session_id`，章节类能力用 `chapter_id` 保序。