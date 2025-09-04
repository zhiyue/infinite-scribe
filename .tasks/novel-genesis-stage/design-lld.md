# 低层设计 (Low-Level Design) — 小说创世阶段

文档版本: 1.0  
生成日期: 2025-09-05  
对应 HLD: [design-hld.md](design-hld.md)

## 概述

本 LLD 基于已批准的 [HLD](design-hld.md)，细化"小说创世阶段（Stage
0–5）"的实现细节。

**文档关系说明**：

- **HLD ([design-hld.md](design-hld.md))** - 架构决策、组件交互、数据流设计
- **LLD (本文档)** - 具体实现、代码规范、数据库模式、API细节

本文档包含从 HLD 中提取的所有实现层细节，覆盖 API/会话服务、事件与 Outbox、Orchestrator、专门化 Agents、EventBridge（Kafka→Redis
SSE）、数据模型（PostgreSQL/Neo4j/Milvus）、异常与重试、测试与容量、部署与回滚等。P1 聚焦“至少一次 + 事务性 Outbox +
Kafka”链路与基础安全；P2 预留 Prefect 编排与 RBAC。

## 组件详细设计

### 组件1：API + Conversation Service（FastAPI）

职责：

- 路由聚合、JWT 鉴权、SSE 推送；写通缓存（Redis）+ 持久化（PostgreSQL）
- 同一事务内写入 `conversation_rounds`、`domain_events`、`event_outbox`

#### 接口签名

```typescript
// API Client（前端）接口草案
export interface GenesisApi {
  createSession(body: {
    title?: string
    seed?: string
    methodology?: string
    user_context?: Record<string, any>
  }): Promise<{
    session_id: string
    novel_id: string
    status: string
    stage: string
  }>

  getSession(sessionId: string): Promise<ConversationSession>
  listRounds(
    sessionId: string,
    params?: { after?: string; limit?: number },
  ): Promise<ConversationRound[]>

  postMessage(
    sessionId: string,
    body: UserMessage,
  ): Promise<{ accepted: true; correlation_id: string }>
  postCommand(
    sessionId: string,
    commandType: string,
    body?: Record<string, any>,
    idempotencyKey?: string,
  ): Promise<{ accepted: true; command_id: string }>
}
```

```python
# Python 服务端签名（简化），位于 FastAPI 路由层
from typing import Any
from uuid import UUID

class ConversationAPI:
    async def create_session(self, body: dict) -> dict: ...
    async def get_session(self, session_id: UUID) -> dict: ...
    async def list_rounds(self, session_id: UUID, after: str | None, limit: int = 50) -> list[dict]: ...

    async def post_message(self, session_id: UUID, body: dict) -> dict:
        """
        事务内：INSERT conversation_rounds + domain_events + event_outbox
        :raises: ValueError(校验失败), ConflictError(幂等冲突), DatabaseError
        """
        ...

    async def post_command(self, session_id: UUID, command_type: str, body: dict, idem_key: str | None) -> dict:
        """
        事务内：UPSERT command_inbox + domain_events + event_outbox
        :raises: ConflictError(命令唯一约束), DatabaseError
        """
        ...
```

#### 状态机设计（会话推进/命令处理）

```mermaid
stateDiagram-v2
    [*] --> 未开始
    未开始 --> STAGE0_进行中: create_session
    STAGE0_进行中 --> STAGE0_待审核: Outliner 生成高概念
    STAGE0_待审核 --> STAGE0_已锁定: ConfirmConception
    STAGE0_已锁定 --> STAGE1_进行中: RequestTheme
    STAGE1_进行中 --> STAGE1_待审核: Theme Proposed
    STAGE1_待审核 --> STAGE1_已锁定: ConfirmTheme
    STAGE1_已锁定 --> STAGE2_进行中: BuildWorldview
    STAGE2_进行中 --> STAGE2_待审核: World Completed
    STAGE2_待审核 --> STAGE2_已锁定: ConfirmWorld
    STAGE2_已锁定 --> STAGE3_进行中: DesignCharacters
    STAGE3_进行中 --> STAGE3_待审核: Characters Completed
    STAGE3_待审核 --> STAGE3_已锁定: ConfirmCharacters
    STAGE3_已锁定 --> STAGE4_进行中: BuildPlot
    STAGE4_进行中 --> STAGE4_待审核: Plot Completed
    STAGE4_待审核 --> STAGE4_已锁定: ConfirmPlot
    STAGE4_已锁定 --> STAGE5_进行中: GenerateDetails
    STAGE5_进行中 --> STAGE5_待审核: Details Completed
    STAGE5_待审核 --> STAGE5_已锁定: ConfirmDetails
    STAGE5_已锁定 --> 完成
```

#### 内部数据结构

```typescript
export interface ConversationSession {
  id: string
  scope_type: 'GENESIS'
  scope_id: string // novel_id
  status: 'ACTIVE' | 'COMPLETED' | 'ABANDONED' | 'PAUSED'
  stage?: string
  state?: Record<string, any>
  version: number
  created_at: string
  updated_at: string
}

export interface ConversationRound {
  session_id: string
  round_path: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  input?: any
  output?: any
  correlation_id?: string
  created_at: string
}

export interface UserMessage {
  content: string
  attachments?: Array<{ type: string; url: string }>
  metadata?: Record<string, any>
}
```

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    PAUSED = "PAUSED"

@dataclass
class ConversationSessionModel:
    id: str
    scope_type: str
    scope_id: str
    status: SessionStatus
    stage: Optional[str]
    state: dict[str, Any] | None
    version: int
    created_at: datetime
    updated_at: datetime

@dataclass
class ConversationRoundModel:
    session_id: str
    round_path: str
    role: str
    input: Any | None
    output: Any | None
    correlation_id: str | None
    created_at: datetime
```

---

### 组件2：Orchestrator（业务协调者）

职责：消费 `genesis.session.events`；将 `Genesis.Session.*.Requested`
映射到对应能力 `*.tasks`；将能力完成事件回流为
`Genesis.Session.*.Proposed/Completed`。

#### 接口签名

```typescript
export interface OrchestratorMapper {
  mapDomainToCapability(event: DomainEvent): CapabilityTask | null
  mapCapabilityToDomain(event: CapabilityEvent): DomainEvent | null
}
```

```python
class OrchestratorService:
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def map_domain_to_capability(self, evt: dict) -> dict | None: ...
    def map_capability_to_domain(self, evt: dict) -> dict | None: ...
```

#### 状态机（消费循环）

```mermaid
stateDiagram-v2
    [*] --> 拉取
    拉取 --> 解析: 收到消息
    解析 --> 映射: 领域→能力
    映射 --> 生产: 输出到 *.tasks
    生产 --> 提交: 成功
    生产 --> 重试: 失败
    重试 --> 提交: 超过阈值→DLT
    提交 --> 拉取
```

#### 内部数据结构

```typescript
export interface DomainEventEnvelope {
  event_id: string
  event_type: string // Genesis.Session.*
  aggregate_type: string
  aggregate_id: string
  correlation_id?: string
  payload: any
  metadata?: Record<string, any>
}

export interface CapabilityTask {
  topic: string
  key?: string
  payload: any
  headers?: Record<string, any>
}
```

---

### 组件3：EventBridge（Kafka→Redis SSE）

职责：消费 `genesis.session.events`，筛选可见 Facts，发布到 Redis
Streams（持久化）+ PubSub（实时）。

#### 接口签名

```typescript
export interface SSEClient {
  connect(sseToken: string): EventSource
  onEvent(handler: (evt: SSEMessage) => void): void
}

export interface SSEMessage {
  event: string
  id: string
  data: any
  version: '1.0'
  scope: 'USER'
}
```

```python
class RedisSSEService:
    async def init_pubsub_client(self) -> None: ...
    async def publish_event(self, user_id: str, event: SSEMessage) -> str: ...
    async def subscribe_user_events(self, user_id: str):  # -> AsyncIterator[SSEMessage]
        ...
```

#### 状态机（连接与推送）

```mermaid
stateDiagram-v2
    [*] --> 连接
    连接 --> 订阅: PubSub subscribe
    订阅 --> 推送: 收到指针→读Streams→构建SSE
    推送 --> 订阅: 持续监听
    订阅 --> 重试: 连接失败
    重试 --> 订阅: 指数退避≤3
    重试 --> 熔断: 失败率>50%
    熔断 --> 半开: 30s 探活
    半开 --> 订阅: 恢复
```

---

### 组件4：Agents（Outliner/Worldbuilder/Character/Plot/Detail ...）

职责：消费各自 `*.tasks`，处理后产出到 `*.events`；错误分类→重试/ DLT；可携带
`_topic/_key` 覆盖默认路由。

#### 接口签名

```typescript
export interface AgentMessage {
  type: string
  payload: any
  _topic?: string
  _key?: string
}
```

```python
class BaseAgent:
    async def process_message(self, message: dict) -> dict: ...
    def classify_error(self, error: Exception, message: dict) -> str:  # 'retriable' | 'non_retriable'
        ...
```

#### 内部数据结构

```python
class DLTEnvelope(TypedDict):
    id: str
    ts: str
    correlation_id: str | None
    retries: int
    payload: dict
    original_topic: str
    original_partition: int
    original_offset: int
```

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

## 前端组件设计

#### 组件表格

| 组件名称       | 职责                                   | Props/状态摘要                                      |
| -------------- | -------------------------------------- | --------------------------------------------------- |
| GenesisFlow    | 创世阶段总控与阶段面板切换             | sessionId, stage, onCommand, onAccept, onRegenerate |
| SessionSidebar | 会话历史/轮次/版本概览                 | sessionId, rounds, onSelectRound                    |
| EventStream    | 订阅 SSE 并分发到 UI                   | sseToken, onEvent, lastEventId                      |
| StagePanel     | 各阶段详情（主题/世界/人物/情节/细节） | stage, data, onEdit, onConfirm                      |

#### API 端点设计

| 方法 | 路由                                        | 目的               | 认证 | 状态码                                 |
| ---- | ------------------------------------------- | ------------------ | ---- | -------------------------------------- |
| POST | /api/v1/genesis/sessions                    | 创建创世会话       | 需要 | 201, 400, 401, 500                     |
| GET  | /api/v1/genesis/sessions/{id}               | 查询会话           | 需要 | 200, 401, 404, 500                     |
| GET  | /api/v1/genesis/sessions/{id}/rounds        | 列出会话轮次       | 需要 | 200, 401, 404, 500                     |
| POST | /api/v1/genesis/sessions/{id}/messages      | 提交用户消息       | 需要 | 202, 400, 401, 409, 422, 500           |
| POST | /api/v1/genesis/sessions/{id}/commands/{ct} | 提交幂等命令       | 需要 | 202, 400, 401, 409, 422, 500           |
| GET  | /api/v1/events/stream?sse_token=...         | SSE 事件流（下行） | 需要 | 200, 401, 403, 500（网络断连重连策略） |

## 数据模型设计

#### 领域实体

1. ConversationSession：对话会话（scope=GENESIS，scope_id=novel_id）
2. ConversationRound：对话轮次（分层 round_path）
3. DomainEvent：领域事件（事件溯源）
4. EventOutbox：事务性发件箱（可靠投递）
5. CommandInbox：命令收件箱（幂等 + 重试）
6. Novel/WorldRule/Character/...：图模型（Neo4j）

#### 实体关系

```mermaid
erDiagram
    ConversationSession ||--|{ ConversationRound : has
    ConversationSession ||--o{ DomainEvent : aggregates
    ConversationSession }o--|| Novel : binds
    DomainEvent ||--o{ EventOutbox : enqueues
    ConversationSession ||--o{ CommandInbox : commands
```

#### 数据模型定义

```typescript
export interface DomainEvent {
  event_id: string
  event_type: string
  aggregate_type: string
  aggregate_id: string
  payload: any
  metadata?: Record<string, any>
  created_at: string
}
```

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class EventOutboxRow:
    id: str
    topic: str
    key: str | None
    partition_key: str | None
    payload: dict
    headers: dict | None
    status: str
    retry_count: int
    max_retries: int
    created_at: datetime
```

### 组件2：[数据访问层]

#### 数据库模式设计（PostgreSQL 完整实现）

```sql
-- 枚举类型定义
CREATE TYPE command_status AS ENUM ('RECEIVED','PROCESSING','COMPLETED','FAILED');
CREATE TYPE outbox_status   AS ENUM ('PENDING','SENDING','SENT','FAILED');

-- 会话表（conversation_sessions）
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY,
    scope_type TEXT NOT NULL,                 -- GENESIS/CHAPTER/REVIEW/...
    scope_id TEXT NOT NULL,                   -- 绑定业务实体ID（创世阶段=novel_id）
    status TEXT NOT NULL DEFAULT 'ACTIVE',    -- ACTIVE/COMPLETED/ABANDONED/PAUSED
    stage TEXT,                               -- 当前业务阶段（可选）
    state JSONB,                              -- 会话聚合/摘要
    version INTEGER NOT NULL DEFAULT 0,       -- 乐观锁版本（OCC）
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conv_sessions_scope ON conversation_sessions (scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_conv_sessions_updated_at ON conversation_sessions (updated_at DESC);

-- 轮次表（conversation_rounds）
CREATE TABLE conversation_rounds (
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    round_path TEXT NOT NULL,                 -- '1','2','2.1','2.1.1'
    role TEXT NOT NULL,                       -- user/assistant/system/tool
    input JSONB,
    output JSONB,
    tool_calls JSONB,
    model TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    latency_ms INTEGER,
    cost NUMERIC,
    correlation_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_id, round_path)
);
CREATE INDEX IF NOT EXISTS idx_conv_rounds_session_created ON conversation_rounds (session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conv_rounds_correlation ON conversation_rounds (correlation_id);

-- 命令收件箱（CommandInbox，CQRS命令侧）
CREATE TABLE command_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,                         -- 会话标识
    command_type TEXT NOT NULL,                       -- 命令类型（如 ConfirmStoryConception, GenerateWorldview）
    idempotency_key TEXT UNIQUE NOT NULL,             -- 幂等键，确保同一命令不会被重复处理
    payload JSONB,                                     -- 命令载荷，包含命令执行所需的所有数据
    status command_status NOT NULL DEFAULT 'RECEIVED', -- 命令状态（RECEIVED/PROCESSING/COMPLETED/FAILED）
    error_message TEXT,                               -- 错误信息（当状态为FAILED时必填）
    retry_count INTEGER NOT NULL DEFAULT 0,           -- 重试次数，用于失败重试机制
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 核心索引：支持幂等性和高效查询
CREATE UNIQUE INDEX idx_command_inbox_unique_pending_command
    ON command_inbox(session_id, command_type)
    WHERE status IN ('RECEIVED', 'PROCESSING');
CREATE INDEX idx_command_inbox_session_id ON command_inbox(session_id);
CREATE INDEX idx_command_inbox_status ON command_inbox(status);
CREATE INDEX idx_command_inbox_command_type ON command_inbox(command_type);
CREATE INDEX idx_command_inbox_created_at ON command_inbox(created_at);
CREATE INDEX idx_command_inbox_session_status ON command_inbox(session_id, status);
CREATE INDEX idx_command_inbox_status_created ON command_inbox(status, created_at);

-- 领域事件表（Event Sourcing事件存储）
CREATE TABLE domain_events (
    sequence_id BIGSERIAL PRIMARY KEY,                -- 自增主键，确保严格顺序
    event_id UUID NOT NULL DEFAULT gen_random_uuid(), -- 事件唯一标识
    correlation_id UUID,                              -- 关联ID（跟踪整个流程）
    causation_id UUID,                                -- 因果ID（触发此事件的前一个事件）
    event_type TEXT NOT NULL,                         -- 事件类型（点式命名）
    event_version INTEGER NOT NULL DEFAULT 1,         -- 事件版本
    aggregate_type TEXT NOT NULL,                     -- 聚合类型
    aggregate_id TEXT NOT NULL,                       -- 聚合根ID
    payload JSONB NOT NULL,                           -- 事件数据
    metadata JSONB,                                   -- 元数据
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_domain_events_event_id ON domain_events(event_id);
CREATE INDEX idx_domain_events_aggregate ON domain_events(aggregate_type, aggregate_id);
CREATE INDEX idx_domain_events_correlation ON domain_events(correlation_id);
CREATE INDEX idx_domain_events_event_type ON domain_events(event_type);
CREATE INDEX idx_domain_events_created_at ON domain_events(created_at);

-- 事件发件箱（Outbox，事务性可靠投递）
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,                         -- 主题（Kafka / 逻辑主题）
    key TEXT,                                   -- key（顺序/分区控制）
    partition_key TEXT,                         -- 分区键（可选）
    payload JSONB NOT NULL,                     -- 事件载荷
    headers JSONB,                              -- 元信息（event_type使用点式命名、version、trace等）
    status outbox_status NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 5,
    last_error TEXT,
    scheduled_at TIMESTAMPTZ,                   -- 延迟发送（可选）
    sent_at TIMESTAMPTZ,                        -- 成功发送时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_event_outbox_status ON event_outbox(status);
CREATE INDEX idx_event_outbox_topic ON event_outbox(topic);
CREATE INDEX idx_event_outbox_created_at ON event_outbox(created_at);
CREATE INDEX idx_event_outbox_pending_scheduled ON event_outbox(status, scheduled_at);
CREATE INDEX idx_event_outbox_retry_count ON event_outbox(retry_count);
CREATE INDEX idx_event_outbox_topic_status ON event_outbox(topic, status);
CREATE INDEX idx_event_outbox_status_created ON event_outbox(status, created_at);
CREATE INDEX idx_event_outbox_key ON event_outbox(key);
CREATE INDEX idx_event_outbox_partition_key ON event_outbox(partition_key);
```

#### Neo4j 图模型数据库实现

```cypher
-- Neo4j 5.x 标准语法
-- 注意：所有节点的主键统一为 novel_id（Novel节点）或 id（其他节点）

-- 小说节点
MERGE (n:Novel {
    novel_id: 'uuid',        -- 统一使用 novel_id 作为主键
    app_id: 'infinite-scribe',
    title: 'string',
    created_at: datetime()
})

-- 角色节点（8维度）
MERGE (c:Character {
    id: 'uuid',
    novel_id: 'uuid',        -- 关联到小说
    name: 'string',
    appearance: 'text',      -- 外貌
    personality: 'text',     -- 性格
    background: 'text',      -- 背景
    motivation: 'text',      -- 动机
    goals: 'text',          -- 目标
    obstacles: 'text',      -- 障碍
    arc: 'text',            -- 转折
    wounds: 'text'          -- 心结
})

-- 角色状态节点（支持连续性校验）
MERGE (cs:CharacterState {
    id: 'uuid',
    character_id: 'uuid',
    chapter: 0,             -- 章节号
    age: 0,                 -- 年龄
    status: 'string',
    attributes: '{}'        -- JSON 字符串
})

-- 世界规则节点
MERGE (w:WorldRule {
    id: 'uuid',
    novel_id: 'uuid',
    dimension: 'string',    -- 地理/历史/文化/规则/社会
    rule: 'text',
    priority: 0,            -- 优先级（冲突时使用）
    scope: '{}',            -- 适用范围（地域/时间）
    examples: '{}',
    constraints: '{}',
    created_at: datetime()  -- 创建时间（冲突判定）
})

-- 事件节点（支持时间线校验）
MERGE (e:Event {
    id: 'uuid',
    novel_id: 'uuid',
    description: 'text',
    timestamp: datetime(),
    type: 'string'          -- normal/time_skip/battle等
})

-- 位置节点（支持空间校验）
MERGE (l:Location {
    id: 'uuid',
    novel_id: 'uuid',
    name: 'string',
    x: 0.0,                 -- 坐标X
    y: 0.0,                 -- 坐标Y
    timestamp: datetime()   -- 时间戳
})

-- 交通工具节点
MERGE (t:Transportation {
    id: 'uuid',
    type: 'string',         -- walk/horse/car/teleport等
    speed: 0.0              -- km/h
})

-- 关系定义（支持一致性校验）
MATCH (c1:Character {id: 'uuid1'}), (c2:Character {id: 'uuid2'})
MERGE (c1)-[:RELATES_TO {
    strength: 8,            -- 关系强度1-10
    type: 'friend',         -- friend/enemy/knows_of等
    symmetric: true         -- 是否对称关系
}]->(c2)

-- 角色与小说关系
MATCH (c:Character {id: 'uuid'}), (n:Novel {novel_id: 'uuid'})
MERGE (c)-[:BELONGS_TO]->(n)

-- 角色与状态关系
MATCH (c:Character {id: 'uuid'}), (cs:CharacterState {character_id: 'uuid'})
MERGE (c)-[:HAS_STATE]->(cs)

-- 角色位置关系
MATCH (c:Character {id: 'uuid'}), (l:Location {id: 'uuid'})
MERGE (c)-[:LOCATED_AT {timestamp: datetime()}]->(l)

-- 角色使用工具关系
MATCH (c:Character {id: 'uuid'}), (t:Transportation {id: 'uuid'})
MERGE (c)-[:USES]->(t)

-- 世界规则管理关系
MATCH (w:WorldRule {id: 'uuid'}), (n:Novel {novel_id: 'uuid'})
MERGE (w)-[:GOVERNS]->(n)

-- 规则冲突关系
MATCH (w1:WorldRule {id: 'uuid1'}), (w2:WorldRule {id: 'uuid2'})
MERGE (w1)-[:CONFLICTS_WITH {
    severity: 'major'       -- critical/major/minor
}]->(w2)

-- 事件因果关系
MATCH (e1:Event {id: 'uuid1'}), (e2:Event {id: 'uuid2'})
MERGE (e1)-[:CAUSES]->(e2)

-- 事件涉及角色
MATCH (e:Event {id: 'uuid'}), (c:Character {id: 'uuid'})
MERGE (e)-[:INVOLVES]->(c)

-- 事件发生地点
MATCH (e:Event {id: 'uuid'}), (l:Location {id: 'uuid'})
MERGE (e)-[:OCCURS_AT]->(l)

-- ==================== Neo4j 5.x 约束定义 ====================
-- 唯一性约束（使用 Neo4j 5.x 语法）
CREATE CONSTRAINT unique_novel_novel_id IF NOT EXISTS
FOR (n:Novel) REQUIRE n.novel_id IS UNIQUE;

CREATE CONSTRAINT unique_character_id IF NOT EXISTS
FOR (c:Character) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT unique_world_rule_id IF NOT EXISTS
FOR (w:WorldRule) REQUIRE w.id IS UNIQUE;

CREATE CONSTRAINT unique_event_id IF NOT EXISTS
FOR (e:Event) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT unique_location_id IF NOT EXISTS
FOR (l:Location) REQUIRE l.id IS UNIQUE;

-- Node Key 约束（Neo4j 5.x 支持）
CREATE CONSTRAINT character_state_key IF NOT EXISTS
FOR (cs:CharacterState) REQUIRE (cs.character_id, cs.chapter) IS NODE KEY;

-- ==================== Neo4j 5.x 索引定义 ====================
-- 性能优化索引（使用 Neo4j 5.x 语法）
CREATE INDEX novel_app_id_index IF NOT EXISTS
FOR (n:Novel) ON (n.app_id);

CREATE INDEX character_novel_index IF NOT EXISTS
FOR (c:Character) ON (c.novel_id);

CREATE INDEX worldrule_novel_index IF NOT EXISTS
FOR (w:WorldRule) ON (w.novel_id);

CREATE INDEX event_novel_index IF NOT EXISTS
FOR (e:Event) ON (e.novel_id);

CREATE INDEX event_timestamp_index IF NOT EXISTS
FOR (e:Event) ON (e.timestamp);

CREATE INDEX location_novel_index IF NOT EXISTS
FOR (l:Location) ON (l.novel_id);

CREATE INDEX location_coords_index IF NOT EXISTS
FOR (l:Location) ON (l.x, l.y);

CREATE INDEX character_state_chapter_index IF NOT EXISTS
FOR (cs:CharacterState) ON (cs.chapter);
```

#### Milvus 向量数据库实现

##### 集合Schema定义

```python
collection_schema = {
    "name": "novel_embeddings_v1",  # 版本化命名
    "fields": [
        {"name": "id", "type": DataType.INT64, "is_primary": True},
        {"name": "novel_id", "type": DataType.VARCHAR, "max_length": 36},
        {"name": "content_type", "type": DataType.VARCHAR, "max_length": 50},
        {"name": "content", "type": DataType.VARCHAR, "max_length": 8192},
        {"name": "embedding", "type": DataType.FLOAT_VECTOR, "dim": 768},
        {"name": "created_at", "type": DataType.INT64},  # 时间戳
        {"name": "version", "type": DataType.INT32},      # 内容版本
        {"name": "metadata", "type": DataType.JSON}       # 扩展元数据
    ],
    "index": {
        "type": "HNSW",
        "metric": "COSINE",
        "params": {"M": 32, "efConstruction": 200}
    },
    "partition": {
        "key": "novel_id",  # 按小说分区
        "ttl": 90 * 24 * 3600  # 90天TTL
    }
}
```

##### VectorService封装层实现

```python
from typing import List, Dict, Optional
import numpy as np
from dataclasses import dataclass
from pymilvus import Collection, utility

@dataclass
class VectorConfig:
    """向量配置"""
    model_name: str = "qwen3-embedding-0.6b"
    dimension: int = 768
    metric_type: str = "COSINE"
    index_type: str = "HNSW"
    collection_version: int = 1

class VectorService:
    """向量服务封装层"""

    def __init__(self, config: VectorConfig):
        self.config = config
        self.collection_name = f"novel_embeddings_v{config.collection_version}"
        self._init_collection()

    async def create_collection(self, force: bool = False):
        """创建集合"""
        if utility.has_collection(self.collection_name) and not force:
            return

        # 创建集合schema
        schema = self._build_schema()
        collection = Collection(
            name=self.collection_name,
            schema=schema,
            using='default'
        )

        # 创建索引
        await self._create_index(collection)

        # 设置TTL
        await self._set_ttl(collection)

        return collection

    async def upsert_embeddings(
        self,
        novel_id: str,
        contents: List[str],
        embeddings: List[np.ndarray],
        content_types: List[str],
        versions: Optional[List[int]] = None
    ):
        """批量插入/更新向量"""
        collection = Collection(self.collection_name)

        # 准备数据
        entities = []
        for i, (content, embedding, content_type) in enumerate(
            zip(contents, embeddings, content_types)
        ):
            entity = {
                "novel_id": novel_id,
                "content": content[:8192],  # 截断超长文本
                "content_type": content_type,
                "embedding": embedding.tolist(),
                "created_at": int(time.time()),
                "version": versions[i] if versions else 1,
                "metadata": {}
            }
            entities.append(entity)

        # 批量插入
        collection.insert(entities)
        collection.flush()

        return len(entities)

    async def search_similar(
        self,
        novel_id: str,
        query_embedding: np.ndarray,
        content_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.6
    ) -> List[Dict]:
        """相似度搜索"""
        collection = Collection(self.collection_name)
        collection.load()

        # 构建搜索参数
        search_params = {
            "metric_type": self.config.metric_type,
            "params": {"ef": 200}
        }

        # 构建过滤表达式
        expr = f'novel_id == "{novel_id}"'
        if content_type:
            expr += f' and content_type == "{content_type}"'

        # 执行搜索
        results = collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["content", "content_type", "version", "metadata"]
        )

        # 过滤低分结果
        filtered_results = []
        for hit in results[0]:
            if hit.score >= min_score:
                filtered_results.append({
                    "id": hit.id,
                    "content": hit.entity.get("content"),
                    "content_type": hit.entity.get("content_type"),
                    "version": hit.entity.get("version"),
                    "score": hit.score,
                    "metadata": hit.entity.get("metadata")
                })

        return filtered_results

    async def migrate_to_new_model(
        self,
        new_config: VectorConfig,
        batch_size: int = 1000
    ):
        """模型变更迁移"""
        old_collection = Collection(self.collection_name)
        new_service = VectorService(new_config)

        # 创建新集合
        await new_service.create_collection()

        # 批量迁移数据
        offset = 0
        while True:
            # 读取旧数据
            old_data = old_collection.query(
                expr="",
                offset=offset,
                limit=batch_size,
                output_fields=["novel_id", "content", "content_type", "version"]
            )

            if not old_data:
                break

            # 使用新模型重新生成embedding
            contents = [item["content"] for item in old_data]
            new_embeddings = await self._generate_embeddings(
                contents,
                new_config.model_name
            )

            # 插入新集合
            await new_service.upsert_embeddings(
                novel_id=old_data[0]["novel_id"],
                contents=contents,
                embeddings=new_embeddings,
                content_types=[item["content_type"] for item in old_data],
                versions=[item["version"] for item in old_data]
            )

            offset += batch_size

        # 切换别名
        utility.do_bulk_insert(
            collection_name=new_service.collection_name,
            alias="novel_embeddings_active"
        )

        return new_service

    async def setup_cold_hot_partitions(self):
        """冷热数据分层"""
        collection = Collection(self.collection_name)

        # 创建热数据分区（最近30天）
        hot_partition = collection.create_partition("hot_data")

        # 创建温数据分区（30-60天）
        warm_partition = collection.create_partition("warm_data")

        # 创建冷数据分区（60天以上）
        cold_partition = collection.create_partition("cold_data")

        # 设置不同的索引参数
        hot_index = {
            "index_type": "IVF_FLAT",  # 热数据用精确索引
            "metric_type": "COSINE",
            "params": {"nlist": 128}
        }

        cold_index = {
            "index_type": "HNSW",  # 冷数据用近似索引
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 100}
        }

        return {
            "hot": hot_partition,
            "warm": warm_partition,
            "cold": cold_partition
        }

    async def cleanup_expired_data(self, days: int = 90):
        """清理过期数据"""
        collection = Collection(self.collection_name)

        # 计算过期时间戳
        expire_time = int(time.time()) - (days * 24 * 3600)

        # 删除过期数据
        expr = f"created_at < {expire_time}"
        collection.delete(expr)
        collection.flush()

        # 压缩集合
        collection.compact()
```

#### 模型变更策略

```yaml
model_migration_strategy:
  trigger:
    - dimension_change # 维度变化（如768→1024）
    - metric_change # 度量变化（如COSINE→L2）
    - model_upgrade # 模型升级（如qwen3→qwen4）

  process:
    1_preparation:
      - create_new_collection # 创建新版本集合
      - setup_dual_write # 设置双写模式

    2_migration:
      - batch_reindex # 批量重建索引
      - validate_quality # 验证搜索质量
      - gradual_traffic # 逐步切换流量

    3_cleanup:
      - switch_alias # 切换活跃别名
      - archive_old # 归档旧集合
      - delete_after_30d # 30天后删除

cold_hot_strategy:
  hot_tier:
    retention: 30_days
    index_type: IVF_FLAT
    cache: enabled

  warm_tier:
    retention: 60_days
    index_type: IVF_SQ8
    cache: disabled

  cold_tier:
    retention: 90_days
    index_type: HNSW
    compression: enabled
```

### 组件3：[业务逻辑层实现]

#### 质量评分计算实现

质量评分采用**多维度加权模型**，整合以下维度：

| 维度           | 权重范围 | 数据源            | 评分标准                   |
| -------------- | -------- | ----------------- | -------------------------- |
| **LLM 评分**   | 0.4-0.6  | GPT-4/Claude 评估 | 内容质量、创意度、连贯性   |
| **规则校验**   | 0.1-0.2  | 硬编码规则引擎    | 格式正确性、必填项完整性   |
| **相似度检测** | 0.1-0.2  | Milvus 向量检索   | 避免重复、保持新颖性       |
| **一致性校验** | 0.2-0.3  | Neo4j 图数据分析  | 角色关系、世界规则、时间线 |

##### 阶段特定权重调整

```yaml
Stage_0_创意种子:
  创意性: +10% # 提高创意权重
  一致性: -10% # 降低一致性要求

Stage_1_立意主题:
  语义相似度: +15% # 强调与种子的关联
  规则校验: -15% # 放宽格式要求

Stage_2_世界观:
  一致性: +20% # 强调内部一致性
  创意性: -20% # 降低创意要求

Stage_3_人物:
  完整性: +15% # 8维度完整性
  一致性: +10% # 与世界观一致

Stage_4_情节:
  结构性: +20% # 情节逻辑
  相似度: -20% # 允许创新

Stage_5_细节:
  规则校验: +30% # 格式规范性
  创意性: -30% # 批量生成规范化
```

##### 评分计算实现

```python
def calculate_quality_score(stage: str, content: dict, novel_id: str) -> float:
    """计算质量评分"""
    # 获取一致性校验器
    validator = ConsistencyValidator()
    consistency_result = await validator.validate_all(novel_id)

    base_scores = {
        'llm_score': llm_evaluate(content),           # 0-10
        'rule_check': validate_rules(content),        # 0或1
        'similarity': calculate_similarity(content),   # 0-1
        'consistency': consistency_result.score       # 0-10（来自Neo4j校验）
    }

    # 归一化到0-10
    normalized = {
        'llm_score': base_scores['llm_score'],
        'rule_check': base_scores['rule_check'] * 10,
        'similarity': base_scores['similarity'] * 10,
        'consistency': base_scores['consistency']     # 已经是0-10
    }

    # 应用权重
    weights = get_stage_weights(stage)
    final_score = sum(
        normalized[key] * weights[key]
        for key in normalized
    )

    return final_score

def get_stage_weights(stage: str) -> dict:
    """获取阶段特定权重"""
    base_weights = {
        'llm_score': 0.30,
        'rule_check': 0.20,
        'similarity': 0.25,
        'consistency': 0.25
    }

    adjustments = {
        'Stage_0': {'llm_score': +0.10, 'consistency': -0.10},
        'Stage_1': {'similarity': +0.15, 'rule_check': -0.15},
        'Stage_2': {'consistency': +0.20, 'llm_score': -0.20},
        'Stage_3': {'rule_check': +0.15, 'consistency': +0.10, 'similarity': -0.25},
        'Stage_4': {'rule_check': +0.20, 'similarity': -0.20},
        'Stage_5': {'rule_check': +0.30, 'llm_score': -0.30}
    }

    if stage in adjustments:
        for key, adjustment in adjustments[stage].items():
            base_weights[key] += adjustment

    return base_weights
```

##### 评分阈值与处理策略

| 分数区间 | 处理策略                 | 事件类型                  |
| -------- | ------------------------ | ------------------------- |
| ≥ 8.0    | 直接通过，推送用户确认   | `*.Proposed`              |
| 6.0-7.9  | 带建议通过，标记可优化点 | `*.Proposed` + 建议       |
| 4.0-5.9  | 需要修正，生成改进建议   | `*.RevisionRequested`     |
| < 4.0    | 重新生成，调整prompt     | `*.RegenerationRequested` |

##### 重试与DLT策略

```python
class QualityRetryPolicy:
    """质量重试策略"""

    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 30]  # 秒

    def should_retry(self, score: float, attempt: int) -> bool:
        """判断是否重试"""
        if attempt >= self.MAX_RETRIES:
            return False

        # 分数过低直接DLT
        if score < 2.0:
            return False

        # 逐次提高阈值
        threshold = 4.0 + (attempt * 1.0)
        return score < threshold

    def get_retry_strategy(self, attempt: int) -> dict:
        """获取重试策略"""
        strategies = {
            1: {
                'temperature': 0.9,      # 提高创造性
                'prompt_adjust': 'creative'
            },
            2: {
                'temperature': 0.7,      # 平衡模式
                'prompt_adjust': 'detailed',
                'examples': True         # 添加示例
            },
            3: {
                'temperature': 0.5,      # 保守模式
                'prompt_adjust': 'structured',
                'model': 'gpt-4'        # 切换模型
            }
        }
        return strategies.get(attempt, strategies[3])
```

##### 采纳率监控

```yaml
metrics:
  # 实时指标
  acceptance_rate:
    formula: confirmed_events / proposed_events
    window: 1_hour
    alert_threshold: < 0.6

  # 阶段指标
  stage_acceptance:
    stage_0: 0.75 # 创意阶段容忍度高
    stage_1: 0.70 # 主题阶段标准
    stage_2: 0.65 # 世界观复杂度高
    stage_3: 0.70 # 人物设计标准
    stage_4: 0.60 # 情节框架挑战大
    stage_5: 0.80 # 细节生成规范化

  # 改进触发
  improvement_triggers:
    - acceptance_rate < 0.5 for 30_minutes
    - stage_failures > 5 in 1_hour
    - user_rejections > 3 consecutive
```

#### 一致性校验规则集（Neo4j实现）

##### 校验查询定义

```cypher
-- 1. 角色关系闭包校验
-- 检测关系不一致：A→B→C 但 A与C无关系定义
MATCH (a:Character)-[:RELATES_TO]->(b:Character)-[:RELATES_TO]->(c:Character)
WHERE a.novel_id = $novel_id
  AND NOT EXISTS((a)-[:RELATES_TO]-(c))
  AND a <> c
RETURN a.name as character1, b.name as mediator, c.name as character2,
       "Missing transitive relationship" as violation

-- 2. 世界规则冲突检测
-- 检测矛盾的世界规则
MATCH (r1:WorldRule)-[:CONFLICTS_WITH]-(r2:WorldRule)
WHERE r1.novel_id = $novel_id
  AND EXISTS((r1)-[:GOVERNS]->(:Novel)<-[:GOVERNS]-(r2))
RETURN r1.rule as rule1, r2.rule as rule2,
       "Conflicting rules both govern the same novel" as violation

-- 3. 时间线一致性校验
-- 检测时间悖论：因在果之后
MATCH (e1:Event)-[:CAUSES]->(e2:Event)
WHERE e1.novel_id = $novel_id
  AND e1.timestamp > e2.timestamp
RETURN e1.description as cause_event, e1.timestamp as cause_time,
       e2.description as effect_event, e2.timestamp as effect_time,
       "Cause happens after effect" as violation

-- 4. 人物属性一致性校验
-- 检测不合理的属性突变
MATCH (c:Character)-[:HAS_STATE]->(s1:CharacterState),
      (c)-[:HAS_STATE]->(s2:CharacterState)
WHERE c.novel_id = $novel_id
  AND s2.chapter = s1.chapter + 1
  AND abs(s2.age - s1.age) > 10  -- 年龄突变超过10岁
  AND NOT EXISTS((e:Event {type: 'time_skip'}))
RETURN c.name as character, s1.chapter as chapter1, s1.age as age1,
       s2.chapter as chapter2, s2.age as age2,
       "Unreasonable age change" as violation

-- 5. 地理空间一致性校验
-- 检测不可能的移动速度
MATCH (c:Character)-[:LOCATED_AT]->(l1:Location),
      (c)-[:LOCATED_AT]->(l2:Location)
WHERE c.novel_id = $novel_id
  AND l2.timestamp - l1.timestamp < 3600  -- 1小时内
  AND distance(point({x: l1.x, y: l1.y}),
               point({x: l2.x, y: l2.y})) > 500  -- 超过500公里
  AND NOT EXISTS((c)-[:USES]->(:Transportation {type: 'teleport'}))
RETURN c.name as character, l1.name as from_location, l2.name as to_location,
       duration((l2.timestamp - l1.timestamp)) as travel_time,
       distance(point({x: l1.x, y: l1.y}), point({x: l2.x, y: l2.y})) as distance,
       "Impossible travel speed" as violation
```

##### 校验器Python实现

```python
class ConsistencyValidator:
    """一致性校验器"""

    VALIDATION_RULES = {
        'relationship_closure': {
            'query': RELATIONSHIP_CLOSURE_QUERY,
            'severity': 'warning',
            'auto_fix': True
        },
        'world_rule_conflict': {
            'query': WORLD_RULE_CONFLICT_QUERY,
            'severity': 'error',
            'auto_fix': False
        },
        'timeline_consistency': {
            'query': TIMELINE_CONSISTENCY_QUERY,
            'severity': 'error',
            'auto_fix': True
        },
        'character_continuity': {
            'query': CHARACTER_CONTINUITY_QUERY,
            'severity': 'warning',
            'auto_fix': True
        },
        'spatial_consistency': {
            'query': SPATIAL_CONSISTENCY_QUERY,
            'severity': 'warning',
            'auto_fix': True
        }
    }

    async def validate_all(self, novel_id: str) -> ValidationResult:
        """执行所有校验规则"""
        violations = []

        for rule_name, rule_config in self.VALIDATION_RULES.items():
            result = await self.neo4j.run(
                rule_config['query'],
                {'novel_id': novel_id}
            )

            if result:
                violations.append({
                    'rule': rule_name,
                    'severity': rule_config['severity'],
                    'violations': result,
                    'auto_fix_available': rule_config['auto_fix']
                })

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            score=self.calculate_consistency_score(violations)
        )

    def calculate_consistency_score(self, violations: List) -> float:
        """计算一致性分数（0-10）"""
        if not violations:
            return 10.0

        penalties = {
            'error': 3.0,
            'warning': 1.0,
            'info': 0.3
        }

        total_penalty = sum(
            penalties[v['severity']] * len(v['violations'])
            for v in violations
        )

        return max(0, 10.0 - total_penalty)
```

#### 批量任务调度实现

采用**分阶段实现**的批量处理架构：

| 实现阶段           | 调度方式               | 能力特性                                | 适用场景             |
| ------------------ | ---------------------- | --------------------------------------- | -------------------- |
| **P1: 简单调度**   | 基于 Outbox 的事件驱动 | 任务分发、状态跟踪、基础重试            | MVP阶段、单用户场景  |
| **P2: 工作流编排** | Prefect 流程引擎       | 暂停/恢复、条件分支、并行处理、失败补偿 | 多用户、复杂业务逻辑 |

##### 任务生命周期管理

**任务分类**：

- **细节生成任务**：地名、人名、道具等批量创建
- **内容校验任务**：一致性检查、质量评估
- **优化任务**：向量索引更新、缓存刷新

**状态流转**：

```
待调度 → 执行中 → 完成/失败 → 清理
   ↓        ↓        ↓        ↓
  入队 → 分发给Agent → 结果回收 → 资源回收
```

**容错机制**：

- **重试策略**：指数退避，最多3次
- **超时处理**：任务超时自动取消并重新调度
- **死信队列**：多次失败任务进入DLT处理

##### P1实现：基于Outbox的简单调度

```python
class BatchDetailGenerator:
    """P1: 批量细节生成（无Prefect）"""

    async def generate_details(self, novel_id: str, categories: List[str], style: str):
        """通过Agent直接处理批量任务"""
        # 发布到Outbox
        await self.publish_to_outbox({
            "event_type": "Genesis.Session.Details.Requested",
            "novel_id": novel_id,
            "categories": categories,
            "style": style
        })

        # Detail Generator Agent会消费任务并处理
        # 完成后发布 Genesis.Session.Details.Generated 事件

class TaskScheduler:
    """任务调度器"""

    async def schedule_batch_tasks(self, tasks: List[dict]) -> str:
        """调度批量任务"""
        batch_id = str(uuid.uuid4())

        # 为每个任务创建Outbox条目
        for task in tasks:
            await self.publish_to_outbox({
                "event_type": f"{task['agent_type']}.Task.Requested",
                "batch_id": batch_id,
                "task_id": task['id'],
                "payload": task['payload']
            })

        return batch_id

    async def track_batch_progress(self, batch_id: str) -> dict:
        """跟踪批量任务进度"""
        # 查询任务状态
        tasks = await self.get_batch_tasks(batch_id)

        completed = sum(1 for t in tasks if t['status'] == 'completed')
        failed = sum(1 for t in tasks if t['status'] == 'failed')

        return {
            "batch_id": batch_id,
            "total": len(tasks),
            "completed": completed,
            "failed": failed,
            "progress": completed / len(tasks) if tasks else 0
        }
```

##### P2扩展：Prefect工作流编排

```python
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1)
)
async def generate_batch_details(
    category: str,
    count: int,
    style: str
) -> List[str]:
    """批量生成细节任务"""
    # 实际的细节生成逻辑
    pass

@flow(name="genesis-detail-generation")
async def detail_generation_flow(
    novel_id: str,
    categories: List[str],
    style: str
):
    """P2: 复杂工作流编排
    - 支持暂停/恢复
    - 支持条件分支
    - 支持并行处理
    - 支持失败补偿
    """

    # 并行生成各类细节
    futures = []
    for category in categories:
        future = await generate_batch_details.submit(
            category=category,
            count=get_count_for_category(category),
            style=style
        )
        futures.append(future)

    # 等待所有任务完成
    results = await gather(*futures)

    # 发布完成事件
    await publish_to_outbox({
        "event_type": "Genesis.Session.Details.Completed",
        "novel_id": novel_id,
        "results": results
    })

class WorkflowOrchestrator:
    """P2工作流编排器"""

    async def start_complex_workflow(self, workflow_type: str, params: dict):
        """启动复杂工作流"""
        if workflow_type == "detail_generation":
            return await detail_generation_flow(
                novel_id=params["novel_id"],
                categories=params["categories"],
                style=params["style"]
            )
        # 其他工作流类型...

    async def pause_workflow(self, flow_run_id: str):
        """暂停工作流"""
        # Prefect API调用暂停
        pass

    async def resume_workflow(self, flow_run_id: str):
        """恢复工作流"""
        # Prefect API调用恢复
        pass
```

##### 限流实现

```python
class RateLimiter:
    """限流器实现"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def sliding_window_check(self, key: str, window_size: int, limit: int) -> bool:
        """滑动窗口限流（P1实现）"""
        now = int(time.time())
        window_start = now - window_size

        pipe = self.redis.pipeline()
        # 删除窗口外的记录
        pipe.zremrangebyscore(key, 0, window_start)
        # 添加当前请求
        pipe.zadd(key, {str(now): now})
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        # 设置过期时间
        pipe.expire(key, window_size)

        results = await pipe.execute()
        current_count = results[2]

        return current_count <= limit

    async def token_bucket_check(self, key: str, capacity: int, refill_rate: float) -> bool:
        """令牌桶限流（P2实现，使用Redis Lua脚本）"""
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now

        -- 计算需要补充的令牌数
        local time_passed = now - last_refill
        local tokens_to_add = time_passed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)

        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return 0
        end
        """

        result = await self.redis.eval(
            lua_script, 1, key, capacity, refill_rate, int(time.time())
        )

        return bool(result)
```

from prefect.tasks import task_input_hash from datetime import timedelta

@task( retries=3, retry_delay_seconds=60, cache_key_fn=task_input_hash,
cache_expiration=timedelta(hours=1) ) async def generate_batch_details(
category: str, count: int, style: str ) -> List[str]: """批量生成细节任务"""
pass

@flow(name="genesis-detail-generation") async def detail_generation_flow(
novel_id: str, categories: List[str], style: str ):
"""P2: 复杂工作流编排 - 支持暂停/恢复 - 支持条件分支 - 支持并行处理 - 支持失败补偿 """

    # 并行生成各类细节
    futures = []
    for category in categories:
        future = await generate_batch_details.submit(
            category=category,
            count=get_count_for_category(category),
            style=style
        )
        futures.append(future)

    # 等待所有任务完成
    results = await gather(*futures)

    # 发布完成事件
    await publish_to_outbox({
        "event_type": "Genesis.Session.Details.Completed",
        "novel_id": novel_id,
        "results": results
    })

````

## 版本控制实现

### 版本化范围定义

#### 已版本化内容（已实现）

```yaml
chapter_versions:
  storage: PostgreSQL + MinIO
  tracking:
    - content: MinIO URL引用
    - metadata: 创建时间、作者、版本号
    - status: draft/published/archived
  operations:
    - create_version  # 创建新版本
    - restore_version # 恢复历史版本
    - compare_versions # 版本对比
````

#### 创世内容版本化（新增）

```python
class GenesisVersioning:
    """创世内容版本控制"""

    # 世界规则版本化
    async def version_world_rules(self, novel_id: str, rule_id: str):
        """世界规则版本化（Neo4j属性版本）"""
        query = """
        MATCH (r:WorldRule {id: $rule_id, novel_id: $novel_id})
        CREATE (v:WorldRuleVersion {
            id: apoc.create.uuid(),
            rule_id: $rule_id,
            version: r.version + 1,
            content: r.rule,
            dimension: r.dimension,
            priority: r.priority,
            scope: r.scope,
            created_at: datetime(),
            is_active: false
        })
        CREATE (r)-[:HAS_VERSION]->(v)
        SET r.version = r.version + 1
        RETURN v
        """
        return await self.neo4j.execute(query, {
            "novel_id": novel_id,
            "rule_id": rule_id
        })

    # 角色卡版本化
    async def version_character_card(self, novel_id: str, character_id: str):
        """角色卡版本化（Neo4j关系建模）"""
        query = """
        MATCH (c:Character {id: $character_id, novel_id: $novel_id})

        // 创建角色版本节点
        CREATE (cv:CharacterVersion {
            id: apoc.create.uuid(),
            character_id: $character_id,
            version: c.version + 1,
            created_at: datetime(),

            // 8维度数据快照
            name: c.name,
            appearance: c.appearance,
            personality: c.personality,
            background: c.background,
            motivation: c.motivation,
            goals: c.goals,
            obstacles: c.obstacles,
            arc: c.arc,
            wounds: c.wounds
        })

        // 建立版本关系
        CREATE (c)-[:HAS_VERSION {
            version_number: c.version + 1,
            is_active: false
        }]->(cv)

        // 更新当前版本号
        SET c.version = c.version + 1

        // 标记活跃版本
        WITH c, cv
        MATCH (c)-[r:HAS_VERSION]->(old_cv:CharacterVersion)
        WHERE r.is_active = true
        SET r.is_active = false

        WITH c, cv
        MATCH (c)-[r:HAS_VERSION]->(cv)
        SET r.is_active = true

        RETURN cv
        """
        return await self.neo4j.execute(query, {
            "novel_id": novel_id,
            "character_id": character_id
        })

    # 情节节点版本化
    async def version_plot_node(self, novel_id: str, node_id: str):
        """情节节点版本化"""
        # 序列化为JSON
        plot_node = await self.get_plot_node(node_id)

        # 存储到MinIO
        version_key = f"novels/{novel_id}/plot_nodes/{node_id}/v{plot_node.version}.json"
        await self.minio.put_object(
            bucket="genesis-versions",
            key=version_key,
            data=json.dumps(plot_node.to_dict()),
            metadata={
                "novel_id": novel_id,
                "node_id": node_id,
                "version": str(plot_node.version),
                "created_at": datetime.now().isoformat()
            }
        )

        # 更新Neo4j引用
        query = """
        MATCH (p:PlotNode {id: $node_id, novel_id: $novel_id})
        SET p.version = p.version + 1,
            p.minio_url = $minio_url,
            p.updated_at = datetime()
        RETURN p
        """
        return await self.neo4j.execute(query, {
            "novel_id": novel_id,
            "node_id": node_id,
            "minio_url": version_key
        })
```

#### 版本边界与合并

```python
class VersionBoundaries:
    """版本控制边界定义"""

    # Neo4j版本化（图内管理）
    NEO4J_VERSIONED = [
        "WorldRule",       # 世界规则：属性版本
        "Character",       # 角色卡：关系版本
        "CharacterState",  # 角色状态：时间序列版本
        "Event"           # 事件：不可变记录
    ]

    # MinIO版本化（对象存储）
    MINIO_VERSIONED = [
        "ChapterContent",  # 章节内容：完整快照
        "PlotNode",       # 情节节点：JSON序列化
        "DialogueTree",   # 对话树：结构化数据
        "DetailBatch"     # 批量细节：压缩归档
    ]

    # 混合版本化（Neo4j元数据+MinIO内容）
    HYBRID_VERSIONED = [
        "Novel",          # 小说：Neo4j索引+MinIO快照
        "Outline",        # 大纲：Neo4j结构+MinIO详情
        "WorldSettings"   # 世界设定：Neo4j规则+MinIO文档
    ]

class VersionMergeStrategy:
    """版本合并策略"""

    async def merge_world_rules(
        self,
        base_version: str,
        current_version: str,
        incoming_version: str
    ):
        """三路合并世界规则"""
        # 获取三个版本
        base = await self.get_rule_version(base_version)
        current = await self.get_rule_version(current_version)
        incoming = await self.get_rule_version(incoming_version)

        # 冲突检测
        conflicts = []

        # 规则文本冲突
        if current.rule != base.rule and incoming.rule != base.rule:
            if current.rule != incoming.rule:
                conflicts.append({
                    "type": "rule_conflict",
                    "current": current.rule,
                    "incoming": incoming.rule
                })

        # 优先级冲突
        if current.priority != incoming.priority:
            conflicts.append({
                "type": "priority_conflict",
                "current": current.priority,
                "incoming": incoming.priority
            })

        # 范围冲突
        if not self._is_scope_compatible(current.scope, incoming.scope):
            conflicts.append({
                "type": "scope_conflict",
                "current": current.scope,
                "incoming": incoming.scope
            })

        if conflicts:
            return {
                "status": "conflict",
                "conflicts": conflicts,
                "resolution_required": True
            }

        # 自动合并
        merged = WorldRuleVersion(
            rule=incoming.rule if incoming.rule != base.rule else current.rule,
            priority=max(current.priority, incoming.priority),
            scope=self._merge_scopes(current.scope, incoming.scope)
        )

        return {
            "status": "merged",
            "result": merged,
            "auto_merged": True
        }
```

#### 版本化边界总结

| 内容类型 | 存储位置   | 版本化策略 | 快照频率    |
| -------- | ---------- | ---------- | ----------- |
| 章节内容 | MinIO      | 完整快照   | 每次保存    |
| 世界规则 | Neo4j      | 属性版本   | 规则变更时  |
| 角色卡   | Neo4j      | 关系版本   | 8维度变更时 |
| 角色状态 | Neo4j      | 时间序列   | 章节边界    |
| 情节节点 | MinIO      | JSON序列化 | 节点修改时  |
| 对话历史 | PostgreSQL | 增量记录   | 实时        |
| 向量嵌入 | Milvus     | 版本字段   | 内容更新时  |

#### 版本保留策略

```yaml
retention_policy:
  chapters:
    draft: 30_days # 草稿保留30天
    published: forever # 发布版永久保留

  world_rules:
    active: forever # 活跃版本永久
    historical: 90_days # 历史版本90天

  characters:
    current: forever # 当前版本永久
    snapshots: 10 # 保留最近10个快照

  plot_nodes:
    working: 60_days # 工作版本60天
    milestone: forever # 里程碑版本永久
```

## SSE 详细实现规范

### 连接管理配置

- **并发限制**：每用户最多 2 条连接（超限返回 429，`Retry-After` 按配置）
- **心跳与超时**：`ping` 间隔 15s，发送超时 30s；自动检测客户端断连并清理
- **重连语义**：支持 `Last-Event-ID` 续传近期事件（Redis 历史 + 实时聚合队列）
- **健康检查**：`/api/v1/events/health` 返回 Redis 状态与连接统计；异常时 503
- **响应头**：`Cache-Control: no-cache`、`Connection: keep-alive`
- **鉴权**：`POST /api/v1/auth/sse-token` 获取短时效
  `sse_token`（**默认 TTL=60秒**），`GET /api/v1/events/stream?sse_token=...`
  建立连接
- **SLO 口径**：重连场景不计入"首 Token"延迟；新会话从事件生成时刻开始计时

### Redis Stream 配置

```yaml
历史事件保留:
  stream_maxlen: 1000 # XADD maxlen ≈ 1000（默认值）
  stream_ttl: 3600 # 1小时后自动清理
  user_history_limit: 100 # 每用户保留最近100条

回放策略:
  初次连接:
    max_events: 20 # 仅回放最近20条
    time_window: 300 # 或最近5分钟内的事件

  重连场景:
    from_last_event_id: true # 从Last-Event-ID开始全量补发
    batch_size: 50 # 每批发送50条
    max_backfill: 500 # 最多补发500条
    timeout_ms: 5000 # 补发超时时间
```

### Token 管理实现

```yaml
token_config:
  default_ttl: 60           # 默认60秒有效期
  max_ttl: 300             # 最长5分钟（用于长连接）
  refresh_window: 15       # 过期前15秒可续签

签发流程:
  1. POST /api/v1/auth/sse-token
     - 验证JWT主令牌有效性
     - 生成短时效SSE令牌
     - 返回: {token, expires_in: 60}

  2. GET /api/v1/events/stream?sse_token=xxx
     - 验证SSE令牌
     - 建立SSE连接
     - 开始推送事件流
```

### 客户端续签实现

```javascript
class SSETokenManager {
  constructor() {
    this.token = null
    this.expiresAt = null
    this.refreshTimer = null
  }

  async connect() {
    // 1. 获取初始token
    const tokenData = await fetch('/api/v1/auth/sse-token', {
      method: 'POST',
      headers: { Authorization: `Bearer ${mainJWT}` },
    }).then((r) => r.json())

    this.token = tokenData.token
    this.expiresAt = Date.now() + tokenData.expires_in * 1000

    // 2. 建立SSE连接
    this.eventSource = new EventSource(
      `/api/v1/events/stream?sse_token=${this.token}`,
    )

    // 3. 设置自动续签（提前15秒）
    this.scheduleRefresh()
  }

  scheduleRefresh() {
    const refreshTime = this.expiresAt - Date.now() - 15000 // 提前15秒
    this.refreshTimer = setTimeout(() => this.refresh(), refreshTime)
  }

  async refresh() {
    try {
      // 4. 获取新token
      const newTokenData = await fetch('/api/v1/auth/sse-token', {
        method: 'POST',
        headers: { Authorization: `Bearer ${mainJWT}` },
      }).then((r) => r.json())

      // 5. 无缝切换连接
      const oldEventSource = this.eventSource
      this.token = newTokenData.token
      this.expiresAt = Date.now() + newTokenData.expires_in * 1000

      // 6. 创建新连接（带Last-Event-ID）
      this.eventSource = new EventSource(
        `/api/v1/events/stream?sse_token=${this.token}`,
        { headers: { 'Last-Event-ID': this.lastEventId } },
      )

      // 7. 关闭旧连接
      setTimeout(() => oldEventSource.close(), 1000)

      // 8. 递归设置下次续签
      this.scheduleRefresh()
    } catch (error) {
      console.error('Token refresh failed:', error)
      // 触发重连逻辑
      this.reconnect()
    }
  }
}
```

### 服务端验证实现

```python
async def validate_sse_token(token: str) -> dict:
    """验证SSE令牌"""
    # 1. 从Redis获取token信息
    token_data = await redis.get(f"sse_token:{token}")
    if not token_data:
        raise HTTPException(401, "Invalid or expired SSE token")

    # 2. 检查过期时间
    if datetime.now() > token_data["expires_at"]:
        await redis.delete(f"sse_token:{token}")
        raise HTTPException(401, "SSE token expired")

    # 3. 可选：检查主JWT是否仍有效
    if not await is_main_jwt_valid(token_data["user_id"]):
        raise HTTPException(401, "Main session expired")

    return token_data
```

### SSE 事件格式规范

```json
{
  "id": "event-123", // Last-Event-ID
  "event": "Genesis.Session.Theme.Proposed", // 事件类型（点式命名）
  "data": {
    "event_id": "uuid", // 事件唯一ID
    "event_type": "Genesis.Session.Theme.Proposed",
    "session_id": "uuid", // 会话ID
    "novel_id": "uuid", // 小说ID
    "correlation_id": "uuid", // 关联ID（跟踪整个流程）
    "trace_id": "uuid", // 追踪ID（分布式追踪）
    "timestamp": "ISO-8601", // 事件时间戳
    "payload": {
      // 业务数据（最小集）
      "stage": "Stage_1",
      "content": {
        // 仅必要的展示数据
        "theme": "...",
        "summary": "..."
      }
    }
  }
}
```

### 可推送事件白名单

仅以下领域事件会推送到SSE（都来自 `genesis.session.events`）：

- `Genesis.Session.Started` - 会话开始
- `Genesis.Session.*.Proposed` - AI提议（需用户审核）
- `Genesis.Session.*.Confirmed` - 用户确认
- `Genesis.Session.*.Updated` - 内容更新
- `Genesis.Session.StageCompleted` - 阶段完成
- `Genesis.Session.Finished` - 创世完成
- `Genesis.Session.Failed` - 处理失败

**注意**：能力事件（`*.tasks/events`）不推送到SSE，仅用于内部协调。

#### 迁移策略

- 使用 Alembic 版本化迁移脚本；顺序：新建表→数据迁移→切换读写→删除旧表
- 回滚脚本配套：每个升级脚本必须包含 downgrade 分支
- 热点索引基于查询模式建立（会话按更新时间、事件按 event_type/correlation）

#### 缓存策略

```typescript
export interface CacheStrategy {
  generateKey(params: any): string
  getTTL(key: string): number
  invalidate(pattern: string): Promise<void>
  warmup(keys: string[]): Promise<void>
}

export class SessionCache implements CacheStrategy {
  private readonly DEFAULT_TTL = 60 * 60 // 1h
  generateKey(params: any) {
    return `dialogue:session:${params.sessionId}`
  }
  getTTL(_key: string) {
    return this.DEFAULT_TTL
  }
  async invalidate(pattern: string) {
    /* redis scan+del */
  }
  async warmup(keys: string[]) {
    /* batch mget */
  }
}
```

## 异常处理与重试机制

### 异常分类

| 异常类型       | 错误码  | 处理策略                | 重试策略       |
| -------------- | ------- | ----------------------- | -------------- |
| 参数校验失败   | 400     | 返回详细错误            | 不重试         |
| 未认证/未授权  | 401/403 | 返回错误，提示登录/权限 | 不重试         |
| 幂等冲突       | 409     | 返回冲突信息            | 1 次（短退避） |
| 语义校验失败   | 422     | 返回错误，标注字段      | 不重试         |
| 限流/超时      | 429/504 | 等待后重试              | 指数退避 ≤3    |
| 服务器错误     | 500     | 降级/记录/告警          | 指数退避 ≤3    |
| Agent 不可重试 | -       | 写入 DLT                | 不重试         |

### 重试实现（前端/服务示例）

```typescript
function retryable<T>(fn: () => Promise<T>, max = 3, base = 500) {
  return (async () => {
    let attempt = 0
    while (true) {
      try {
        return await fn()
      } catch (e) {
        if (attempt++ >= max) throw e
        await new Promise((r) =>
          setTimeout(r, Math.min(30_000, base * 2 ** attempt)),
        )
      }
    }
  })()
}
```

## 回滚步骤详细设计

```yaml
rollback:
  steps:
    - name: 停止流量
      command: kubectl scale deploy/api --replicas=0
    - name: 回滚数据库
      command: alembic downgrade -1
    - name: 回滚应用镜像
      command: kubectl rollout undo deploy/api
    - name: 恢复流量并验证
      command: |
        kubectl scale deploy/api --replicas=2
        ./scripts/smoke-test.sh
      success_criteria:
        - http_2xx_rate > 0.99
        - p95_latency_ms < 3000
```

## 容量参数配置

```yaml
capacity:
  resources:
    requests: { cpu: '500m', memory: '512Mi' }
    limits: { cpu: '2000m', memory: '2Gi' }
  concurrency:
    max_connections: 1000
    max_requests_per_second: 500
    max_concurrent_requests: 100
  queues:
    outbox_sender: { max_size: 20000, batch: 100, max_delay: 60s }
  pools:
    database: { min_size: 10, max_size: 100, max_idle_time: 300s }
    redis: { min_size: 5, max_size: 50 }
  rate_limits:
    - key: 'user_id'
      limit: 60
      window: 60s
```

### 自动伸缩参数

```yaml
autoscaling:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
    - type: Resource
      resource:
        { name: memory, target: { type: Utilization, averageUtilization: 80 } }
```

## 测试策略

### 测试目标

- 降低质量风险；保障对话与事件链路端到端稳定；满足 NFR 延迟目标

### 风险矩阵（摘要）

| 区域       | 风险 | 必须            | 可选 |
| ---------- | ---- | --------------- | ---- |
| 会话一致性 | 高   | 单元、集成、E2E | -    |
| 事件可靠性 | 高   | 契约、集成      | 弹性 |
| 图一致性   | 中   | 集成、属性      | -    |
| 向量检索   | 中   | 集成            | 性能 |

### 按层最小化

- 单元：Outbox 序列化、命令幂等、映射函数、错误分类
- 契约：API OpenAPI 契约、事件 Envelope 契约
- 集成：Kafka/Redis/Neo4j/Milvus 依赖的最小可用路径
- E2E（≤3）：创世主流程；断线重连 SSE；低分重试到 DLT

### CI 门控与退出标准

- PR：单元+契约 必须通过；暂存：集成+E2E 必须通过；Sev1/Sev2=0

## 测试点设计

### 单元测试（示例）

```typescript
describe('orchestrator.mapDomainToCapability', () => {
  it('将 Theme.Requested 映射到 Outliner 任务', () => {
    // Arrange / Act / Assert
  })
})
```

### 集成测试（示例）

```python
def test_end_to_end_flow(client, kafka, redis):
    # 1. 创建会话 → 2. 提交消息 → 3. 消费任务 → 4. 回流领域事件 → 5. SSE 下行
    ...
```

## 部署细节

### CI/CD Pipeline（建议）

```yaml
stages: [build, test, deploy]
build:
  stage: build
  script:
    - pnpm install
    - pnpm backend lint && pnpm frontend lint
    - docker build -t $IMAGE:$CI_COMMIT_SHA apps/backend
test:
  stage: test
  script:
    - pnpm backend test
    - pnpm frontend test
deploy:
  stage: deploy
  script:
    - kubectl set image deploy/api api=$IMAGE:$CI_COMMIT_SHA
    - kubectl rollout status deploy/api
    - ./scripts/smoke-test.sh
```

## 依赖管理

### 外部依赖

| 依赖       | 版本 | 用途           | 降级方案     |
| ---------- | ---- | -------------- | ------------ |
| PostgreSQL | 14+  | 会话/事件表    | 只读降级     |
| Redis      | 7+   | 缓存与 SSE     | 降级为无 SSE |
| Kafka      | 3.x+ | 事件总线       | 暂存 Outbox  |
| Neo4j      | 5.x+ | 知识图谱与校验 | 关闭校验     |
| Milvus     | 2.4+ | 嵌入检索       | 关闭向量检索 |

### 版本兼容性（运行环境）

```json
{
  "python": ">=3.11",
  "node": ">=20",
  "pnpm": ">=9"
}
```

## 与HLD的关系

- 统一遵循 HLD 的架构与事件命名；表结构与 Topic 映射完全对齐
- NFR：首 token < 3s、能力生成 < 5s；指标与容量配置已在本 LLD 细化

## 交付物

- 完整接口签名（API/Orchestrator/Agents/SSE）
- 状态机与 ER 图
- 数据结构定义与 DDL 摘要
- 异常矩阵与重试实现
- 回滚步骤与容量配置
- 测试策略与关键测试点
- 部署与依赖矩阵
