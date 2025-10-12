# Agent 消息流与数据存储架构

## 概述

本文档描述 InfiniteScribe 系统中 Agent 间通信的完整数据流，包括消息封装标准、存储层次和上下文构建机制。

### 核心设计原则

1. **Envelope 模式**：所有 Agent 输出使用统一的 Envelope 结构封装
2. **Outbox 模式**：通过 EventOutbox 表实现可靠消息传递
3. **分层职责**：PostgreSQL（暂存）→ Kafka（传输）→ BaseAgent（解析）→ Orchestrator（编排）
4. **运行时上下文**：context 不存储，由 Kafka metadata 和 Envelope 运行时合成

---

## 1. Envelope 标准格式

### 1.1 定义

所有 Agent 能力完成事件必须使用 Envelope 格式封装，确保消息的一致性和可追踪性。

**代码位置**：`apps/backend/src/agents/message.py:15-44`

```python
class Envelope(BaseModel):
    """Agent 间通信的标准消息封装"""
    id: str                          # UUID 消息标识符
    ts: datetime                     # UTC 时间戳
    type: str                        # 业务事件类型（如 "Inquiry.Response.Generated"）
    version: str = "v1"              # 信封版本
    agent: str | None                # 生产者 agent 名称
    correlation_id: str | None       # 分布式追踪关联 ID
    retries: int | None              # 重试次数
    status: str | None               # 状态："ok" 或 "error"
    data: dict[str, Any]             # 业务负载数据
```

### 1.2 封装过程

**函数**：`encode_message(agent, result, correlation_id, retries)`

```python
# Agent 发送消息
result = {
    "type": "Inquiry.Response.Generated",  # 必需字段
    "query": "什么是小说主题？",
    "response": {...},
    "session_id": "sess-123"
}

# encode_message 自动封装
envelope = {
    "id": "msg-uuid",                      # ← 自动生成
    "ts": "2025-10-12T09:24:32Z",          # ← 自动生成
    "type": "Inquiry.Response.Generated",  # ← 从 result.type 提升
    "version": "v1",
    "agent": "inquiry",
    "correlation_id": "corr-456",
    "retries": 0,
    "status": "ok",
    "data": {                              # ← result 去掉 type 后的内容
        "query": "什么是小说主题？",
        "response": {...},
        "session_id": "sess-123"
    }
}
```

> ℹ️ **统一出口**：无论 Agent 直接调用 `OutboxEgress.enqueue_envelope()`，还是简单 `return {...}` 交给 `BaseAgent`，最终都会在 `encode_message()`（`apps/backend/src/agents/message.py:33`）里生成相同的 Envelope。`MessageProcessor._send_result()`（`apps/backend/src/agents/message_processor.py:266`）也会调用该函数后经 `BaseOutboxManager.enqueue_message()` 写入 Outbox，确保结构一致。

### 1.3 能力事件的业务负载约定（GenerationData）

`Envelope.data` 会被 Orchestrator 解析为 `GenerationData`（`apps/backend/src/agents/orchestrator/types.py:222`）。模型只显式声明了 `content` 字段，但允许附加键值。为避免后续编排失败，建议：

```python
{
    "type": "Inquiry.Response.Generated",
    "content": {
        "text": "答案内容",              # 主要文本
        "title": "查询类型",           # 可选标题
        "metadata": {                 # 扩展元数据
            "query_type": "progress",
            "confidence": 0.95
        }
    },
    "session_id": "sess-123",         # 业务字段
    "query": "原始问题"               # 其他业务字段
}
```

**注意事项**：
- ❌ **不要**在 `data` 中重复 `id/ts/correlation_id` 等系统字段，这些由 Envelope 或 `context.meta` 承担
- ✅ **必须**确保 `session_id` 能在业务数据或 `context.meta.aggregate_id` 中取到（`apps/backend/src/agents/orchestrator/capability_event_processor.py:60`）
- ✅ **应该**把主内容放到 `content`（`ContentData`，`types.py:199`），其余业务字段可以直接附加在根层

### 1.4 领域事件结构（system/data/schema_version）

领域事件通过 `DomainEventProcessor` 处理时，需要遵循分层结构（`apps/backend/src/agents/orchestrator/domain_event_processor.py:200`）：

```jsonc
{
  "system": {
    "event_type": "Genesis.Session.Command.Received",
    "aggregate_id": "sess-123",
    "event_id": "evt-uuid",
    "metadata": {"source": "api", "user_id": "u-1"},
    "correlation_id": "corr-456"
  },
  "data": {
    "command_type": "Character.Request",
    "payload": {
      "character_id": "char-42",
      "intent": "create"
    }
  },
  "schema_version": "v1"
}
```

`CorrelationIdExtractor` 会按 `context.meta` → headers → `system.correlation_id` → `system.metadata.correlation_id` 的顺序回退（同文件 `:24-69`），请确保至少一个层级提供关联 ID。

---

## 2. 数据流全景

### 2.1 完整流程图

```
┌──────────────────────────────────────────────────────────────────┐
│ 阶段 1: Agent 完成任务                                           │
├──────────────────────────────────────────────────────────────────┤
│ InquiryAgent.process_message()                                   │
│   ↓                                                              │
│ # 两种出站路径（二选一，最终都走 encode_message）                │
│ await egress.enqueue_envelope(...)  # 显式调用 OutboxEgress       │
│         或                                                           │
│ return {"type": "...", ...}        # 交给 MessageProcessor        │
│   ↓                                                              │
│ encode_message() → Envelope JSON                                 │
│   ↓                                                              │
│ INSERT INTO event_outbox (                                       │
│     topic, key, payload, headers, status                         │
│ )                                                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 阶段 2: OutboxRelay 中继到 Kafka                                 │
├──────────────────────────────────────────────────────────────────┤
│ OutboxRelayService._process_row()                                │
│   ↓                                                              │
│ payload = row.payload  # Envelope JSON from DB                   │
│   ↓                                                              │
│ await producer.send_and_wait(                                    │
│     topic="genesis.inquiry.events",                              │
│     value=json.dumps(payload).encode("utf-8"),                   │
│     key=b"sess-123",                                             │
│     headers=[("type", b"..."), ("correlation_id", b"...")]       │
│ )                                                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 阶段 3: Kafka 持久化存储                                         │
├──────────────────────────────────────────────────────────────────┤
│ /var/lib/kafka/data/genesis.inquiry.events-0/                   │
│ ├── 00000000000012345.log                                        │
│ │   ├── Offset: 12345      ← Kafka 自动分配                      │
│ │   ├── Timestamp: ...     ← Producer 提供                       │
│ │   ├── Key: b"sess-123"   ← 从 EventOutbox.key                 │
│ │   ├── Value: b'{...}'    ← Envelope JSON                       │
│ │   └── Headers: [...]     ← 从 EventOutbox.headers             │
│ ├── *.index                                                      │
│ └── *.timeindex                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 阶段 4: BaseAgent 消费并构建 context                             │
├──────────────────────────────────────────────────────────────────┤
│ async for msg in consumer:  # msg = ConsumerRecord              │
│   ↓                                                              │
│ MessageProcessor.decode_message_with_context(msg)                │
│   ↓                                                              │
│ payload, meta = decode_message(msg.value)  # 解析 Envelope       │
│   ↓                                                              │
│ context = {                        # ✅ 运行时构建               │
│     "topic": msg.topic,            # ← 从 Kafka                 │
│     "partition": msg.partition,    # ← 从 Kafka                 │
│     "offset": msg.offset,          # ← 从 Kafka                 │
│     "timestamp": msg.timestamp,    # ← 从 Kafka                 │
│     "key": msg.key,                # ← 从 Kafka                 │
│     "headers": msg.headers,        # ← 从 Kafka                 │
│     "meta": meta                   # ← 从 Envelope 提取          │
│ }                                                                │
│   ↓                                                              │
│ await orchestrator.process_message(payload, context)             │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ 阶段 5: Orchestrator 处理                                        │
├──────────────────────────────────────────────────────────────────┤
│ message = payload  # Envelope.data                               │
│ context = {                                                      │
│     "topic": "genesis.inquiry.events",                           │
│     "meta": {                                                    │
│         "id": "msg-uuid",                                        │
│         "type": "Inquiry.Response.Generated",                    │
│         "correlation_id": "corr-456",                            │
│         ...                                                      │
│     }                                                            │
│ }                                                                │
│   ↓                                                              │
│ CapabilityEventProcessor.handle_capability_event()               │
│   ↓                                                              │
│ 1. 转换为 GenerationData                                         │
│ 2. 匹配事件处理器                                                │
│ 3. 创建领域事件 + 任务                                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. 存储层次详解

### 3.1 PostgreSQL 层（EventOutbox 表）

**作用**：可靠消息暂存，实现 Outbox 模式

```sql
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY,
    topic VARCHAR NOT NULL,              -- "genesis.inquiry.events"
    key VARCHAR,                         -- "sess-123" (用于 Kafka 分区)
    partition_key VARCHAR,               -- 同上
    payload JSONB NOT NULL,              -- ✅ 能力事件:Envelope / 领域事件:OutboxPayloadEnvelope
    headers JSONB,                       -- Kafka headers（部分冗余）
    status VARCHAR NOT NULL,             -- "PENDING" / "SENT" / "FAILED"
    created_at TIMESTAMP,
    sent_at TIMESTAMP,
    -- 其他字段...
);
```

**payload 字段示例**：

```json
{
  "id": "msg-uuid-123",
  "ts": "2025-10-12T09:24:32.923135Z",
  "type": "Inquiry.Response.Generated",
  "version": "v1",
  "agent": "inquiry",
  "correlation_id": "corr-456",
  "retries": 0,
  "status": "ok",
  "data": {
    "query": "什么是小说主题？",
    "response": {
      "type": "general",
      "text": "主题是小说的核心思想...",
      "data": {}
    },
    "session_id": "sess-123"
  }
}
```

> 💡 **领域事件**：当由 Orchestrator 写入时，`payload` 会是 `OutboxPayloadEnvelope`（`system` + `data` + `schema_version`）。其 SQL 行结构与上例相同，只是 `payload` 字段的 JSON 形态不同。

**特点**：
- ✅ 支持 SQL 查询和事务
- ✅ 可以回滚和重试
- ❌ 不适合高吞吐量实时流式处理

---

### 3.2 Kafka 层（Broker 磁盘）

**作用**：分布式提交日志，实现消息总线和事件溯源

#### 物理存储位置

```bash
/var/lib/kafka/data/
├── genesis.inquiry.events-0/     # Topic + Partition 目录
│   ├── 00000000000012345.log     # 二进制日志段（消息存储）
│   ├── 00000000000012345.index   # Offset 索引（快速定位）
│   └── 00000000000012345.timeindex # 时间戳索引
├── genesis.inquiry.events-1/
└── __consumer_offsets-0/         # 内部 topic（消费者偏移量）
```

#### 消息记录格式（简化）

```
┌─────────────────────────────────────────────────────┐
│ Record (存储在 .log 文件中)                         │
├─────────────────────────────────────────────────────┤
│ offset:    12345                ← Kafka 自动分配    │
│ timestamp: 1736676272923        ← Producer 或 Broker│
│ key:       b"sess-123"          ← EventOutbox.key   │
│ value:     b'{"id":"msg-uuid"...}' ← Envelope JSON  │
│ headers:   [                    ← EventOutbox.headers│
│   ("type", b"Inquiry.Response.Generated"),         │
│   ("correlation_id", b"corr-456"),                  │
│   ("agent", b"inquiry")                             │
│ ]                                                   │
└─────────────────────────────────────────────────────┘
```

**特点**：
- ✅ 高吞吐量、低延迟
- ✅ 支持消息重放（offset 可回溯）
- ✅ 分区并行消费
- ❌ 不支持复杂查询（只能顺序读取）
- ❌ 不可变（append-only）

---

### 3.3 运行时层（BaseAgent 内存）

**作用**：解析 Kafka 消息，构建统一的 context 结构

**代码位置**：`apps/backend/src/agents/message_processor.py:36-72`

```python
def decode_message_with_context(self, msg: ConsumerRecord):
    """从 Kafka 消息构建 context（运行时）"""

    # 1. 解码 value（Envelope）
    payload, meta = decode_message(msg.value)

    # 2. 构建 context
    context = {
        # ✅ 从 Kafka ConsumerRecord 提取
        "topic": msg.topic,              # "genesis.inquiry.events"
        "partition": msg.partition,      # 0
        "offset": msg.offset,            # 12345
        "timestamp": msg.timestamp,      # 1736676272923
        "key": msg.key,                  # b"sess-123"
        "headers": msg.headers,          # [("type", b"..."), ...]

        # ✅ 从 Envelope 提取
        "meta": {
            "id": envelope.id,
            "type": envelope.type,
            "correlation_id": envelope.correlation_id,
            "agent": envelope.agent,
            "version": envelope.version,
            "status": envelope.status,
            "retries": envelope.retries,
        }
    }

    return payload, context, correlation_id, message_id
```

**特点**：
- ⚠️ **不持久化**：context 仅存在于内存中
- ✅ **灵活构建**：不同消费者可以按需定制 context 结构
- ✅ **避免冗余**：元数据已在 Kafka 和 Envelope 中，无需额外存储

---

## 4. Context 的来源分析

### 4.1 关键问题：Context 存储在哪里？

**答案**：**nowhere！Context 不存储。**

Context 是运行时从以下来源合成的：

| Context 字段 | 数据来源 | 存储位置 |
|-------------|---------|---------|
| `topic` | Kafka | Broker 日志文件的**目录名** |
| `partition` | Kafka | Broker 日志文件的**目录名** |
| `offset` | Kafka | Broker 日志文件的 **Record 字段** |
| `timestamp` | Kafka | Broker 日志文件的 **Record 字段** |
| `key` | Kafka | Broker 日志文件的 **Record 字段** |
| `headers` | Kafka | Broker 日志文件的 **Record 字段** |
| `meta.id` | Envelope | Envelope.id（存储在 Kafka value 中） |
| `meta.type` | Envelope | Envelope.type |
| `meta.correlation_id` | Envelope | Envelope.correlation_id |
| `meta.agent` | Envelope | Envelope.agent |
| `meta.version` | Envelope | Envelope.version |
| `meta.status` | Envelope | Envelope.status |
| `meta.retries` | Envelope | Envelope.retries |

### 4.2 数据流对比

```
PostgreSQL (EventOutbox)
├── topic: "genesis.inquiry.events"  ← 字符串字段
├── key: "sess-123"                  ← 字符串字段
└── payload: {Envelope JSON}         ← JSONB 字段
         ↓
OutboxRelay 发送
         ↓
Kafka (Broker Disk)
├── 目录名: genesis.inquiry.events-0/  ← topic + partition
└── .log 文件:
    ├── offset: 12345                  ← Kafka 分配
    ├── timestamp: 1736676272923       ← Kafka 记录
    ├── key: b"sess-123"               ← 来自 EventOutbox
    ├── value: b'{Envelope JSON}'      ← 来自 EventOutbox.payload
    └── headers: [...]                 ← 来自 EventOutbox.headers
         ↓
BaseAgent 消费
         ↓
运行时构建 context = {
    "topic": msg.topic,         ← 从 Kafka
    "partition": msg.partition, ← 从 Kafka
    "offset": msg.offset,       ← 从 Kafka
    "timestamp": msg.timestamp, ← 从 Kafka
    "key": msg.key,             ← 从 Kafka
    "headers": msg.headers,     ← 从 Kafka
    "meta": {                   ← 从 Envelope 解析
        "id": envelope.id,
        "type": envelope.type,
        ...
    }
}
```

---

## 5. Orchestrator 类型系统详解

### 5.1 核心数据模型

Orchestrator 使用 Pydantic 模型强制验证所有接收的能力事件，确保类型安全和数据一致性。

**代码位置**：`apps/backend/src/agents/orchestrator/types.py`

#### CapabilityEventMessage

**定义**（types.py:382-408）：
```python
class CapabilityEventMessage(BaseModel):
    """能力事件的标准消息结构"""
    type: str | None = None                      # 事件类型
    data: CapabilityEventData | None = None      # 业务数据封装
    session_id: str | None = None                # 兼容字段（不推荐）
    correlation_id: str | None = None            # 兼容字段（不推荐）

    model_config = ConfigDict(extra="allow")     # 允许额外字段

    def to_typed_data(self) -> GenerationData:
        """转换为 GenerationData 类型"""
        if not self.data or not self.data.processed_data:
            return GenerationData()
        return GenerationData(**self.data.processed_data)
```

#### CapabilityEventData

**定义**（types.py:373-379）：
```python
class CapabilityEventData(BaseModel):
    """业务数据封装层"""
    raw_data: Any | None = None                  # 原始数据（未使用）
    processed_data: dict[str, Any] | None = None # 业务负载（主要使用）

    model_config = ConfigDict(extra="allow")
```

**关键点**：
- ✅ Orchestrator 只读取 `processed_data`
- ⚠️ `raw_data` 字段存在但未被使用，设计目的不明确

#### GenerationData

**定义**（types.py:210-215）：
```python
class GenerationData(BaseModel):
    """通用的生成数据模型"""
    content: ContentData | None = None           # 唯一显式字段

    model_config = ConfigDict(extra="allow")     # 允许扩展字段
```

#### ContentData

**定义**（types.py:199-207）：
```python
class ContentData(BaseModel):
    """内容数据结构"""
    text: str | None = None                      # 文本内容
    title: str | None = None                     # 标题
    description: str | None = None               # 描述
    metadata: dict[str, Any] | None = None       # 元数据

    model_config = ConfigDict(extra="allow")
```

---

### 5.2 数据转换流程

**处理流程**（capability_event_processor.py:186-202）：

```python
async def handle_capability_event(self, msg_type, message, context):
    # 1. 构建 CapabilityEventMessage（Pydantic 验证）
    event_msg = CapabilityEventMessage(
        type=context["meta"]["type"],            # 从 context.meta 提取
        data=CapabilityEventData(
            processed_data=message               # 整个 message 作为 processed_data
        ),
        session_id=message.get("session_id"),
        correlation_id=context["meta"]["correlation_id"],
    )

    # 2. 转换为 GenerationData
    gen_data = event_msg.to_typed_data()
    # gen_data 包含：
    # - content: ContentData（如果 processed_data 中有 content 字段）
    # - 其他字段：processed_data 中的任意键值（extra="allow"）

    # 3. 提取 session_id 和 scope
    session_id, scope_info = self.data_extractor.extract_session_and_scope(
        gen_data, context_model
    )

    # 4. 匹配处理器
    action = handler_matcher.find_matching_handler(
        msg_type=msg_type,
        session_id=session_id,
        data=gen_data,
        ...
    )
```

---

### 5.3 完整的消息结构示例

#### InquiryAgent 发送消息

**Agent 代码**：
```python
await self.egress.enqueue_envelope(
    agent="inquiry",
    topic="genesis.inquiry.events",
    key=session_id,
    result={
        "type": "Inquiry.Response.Generated",
        "query": "什么是小说主题？",
        "response": {...},
        "session_id": session_id,
    },
    correlation_id=correlation_id,
)
```

**EventOutbox.payload**（存储的 Envelope）：
```json
{
  "id": "msg-uuid-123",
  "ts": "2025-10-12T09:24:32.923135Z",
  "type": "Inquiry.Response.Generated",
  "version": "v1",
  "agent": "inquiry",
  "correlation_id": "corr-456",
  "retries": 0,
  "status": "ok",
  "data": {
    "query": "什么是小说主题？",
    "response": {...},
    "session_id": "sess-123"
  }
}
```

**Kafka 消息**（OutboxRelay 发送）：
```
topic: "genesis.inquiry.events"
key: b"sess-123"
value: {上述 Envelope JSON}
headers: [
  ("type", b"Inquiry.Response.Generated"),
  ("correlation_id", b"corr-456"),
  ("agent", b"inquiry")
]
```

**Orchestrator 接收**：
```python
# message = Envelope.data（BaseAgent 解析后）
{
  "query": "什么是小说主题？",
  "response": {...},
  "session_id": "sess-123"
}

# context（运行时构建）
{
  "topic": "genesis.inquiry.events",
  "meta": {
    "id": "msg-uuid-123",
    "type": "Inquiry.Response.Generated",
    "correlation_id": "corr-456",
    "agent": "inquiry",
    "version": "v1",
    "status": "ok"
  }
}

# Orchestrator 内部转换
event_msg = CapabilityEventMessage(
  type="Inquiry.Response.Generated",
  data=CapabilityEventData(
    processed_data={
      "query": "什么是小说主题？",
      "response": {...},
      "session_id": "sess-123"
    }
  )
)

gen_data = event_msg.to_typed_data()
# gen_data = GenerationData(
#   query="什么是小说主题？",
#   response={...},
#   session_id="sess-123"
# )
# 注意：由于 extra="allow"，所有字段都被保留
```

#### 领域事件写入 Outbox（对比参考）

当 Orchestrator 或 Conversation 服务写入领域事件时，会使用 `OutboxPayloadBuilder` 构建三层结构：

```jsonc
{
  "system": {
    "event_id": "evt-uuid",
    "event_type": "Genesis.Session.Theme.Proposed",
    "aggregate_type": "GenesisSession",
    "aggregate_id": "sess-123",
    "metadata": {"user_id": "u-1", "source": "orchestrator"},
    "correlation_id": "corr-456",
    "causation_id": "cmd-uuid"
  },
  "data": {
    "payload": {
      "session_id": "sess-123",
      "theme": {"title": "希望"}
    }
  },
  "schema_version": "v1"
}
```

> 领域事件消费者需按照 `system` / `data` 分层解析；该结构在 `docs/orchestrator-event-structures.md` 中有完整说明。

### 5.4 领域事件的 `system` / `data` 层

当编排器消费领域事件（通常来自 `EventBridge` 或其它协调组件）时，会使用 `DomainEventProcessor`。事件需要包含：

- `system`: 核心元数据（`event_type`、`aggregate_id`、`event_id`、`metadata`、`correlation_id` 等）。
- `data`: 业务有效负载。若包含 `payload` 子字段，则使用它；否则会自动从 `data` 中剥离 `command_type` 等系统键。
- `schema_version`: 可选，用于迭代。

示例（`apps/backend/src/agents/orchestrator/domain_event_processor.py:200`）：

```jsonc
{
  "system": {
    "event_type": "Genesis.Session.Command.Received",
    "aggregate_id": "sess-123",
    "event_id": "evt-uuid",
    "metadata": {"source": "api", "user_id": "u-1"},
    "correlation_id": "corr-456"
  },
  "data": {
    "command_type": "Character.Request",
    "payload": {"character_id": "char-42", "intent": "create"}
  },
  "schema_version": "v1"
}
```

`CorrelationIdExtractor` 会依次尝试 `context.meta`、Kafka headers、`system.correlation_id`、`system.metadata.correlation_id`（同文件 `:24-69`），确保事件在缺省场景仍能追踪。

---

## 6. 当前设计的问题分析

### 6.1 核心问题：强制统一使用 GenerationData

**问题描述**：

当前 Orchestrator 强制将所有能力事件转换为 `GenerationData` 类型，而 `GenerationData` 的设计假设是内容生成（content: ContentData），这导致非生成类能力需要强行适配这个结构。

**具体案例**：

#### ❌ 不自然的 InquiryAgent 适配

```python
# 当前方式：强制使用 content 结构
{
  "type": "Inquiry.Response.Generated",
  "content": {                    # 不自然的嵌套
    "text": "答案内容",           # 把答案塞进 text
    "title": "问题类型",         # 滥用 title
    "metadata": {
      "query": "原始问题",        # 核心字段被降级为 metadata
      "query_type": "progress",
      "confidence": 0.95
    }
  }
}

# 更自然的结构应该是：
{
  "type": "Inquiry.Response.Generated",
  "query": "进度如何？",
  "query_type": "progress",
  "answer": {
    "text": "当前进度30%",
    "confidence": 0.95,
    "sources": [...]
  }
}
```

#### ❌ CharacterExpert 的适配问题

```python
# 当前方式：不合理的序列化
{
  "type": "Character.Design.Generated",
  "content": {
    "text": JSON.stringify(character_data),  # 把对象序列化为文本？
    "title": character_name,
    "metadata": {...}  # 所有有价值的数据都在这里
  }
}

# 更自然的结构：
{
  "type": "Character.Design.Generated",
  "character": {
    "id": "char-123",
    "name": "李明",
    "personality": {...},
    "background": {...},
    "relationships": [...]
  }
}
```

---

### 6.2 过度嵌套问题

**当前结构**：
```
message
  └─ data
      └─ processed_data
          └─ content
              └─ text / metadata
```

**问题**：
- 4 层嵌套访问业务数据
- 增加序列化/反序列化开销
- 降低代码可读性

**示例**：
```python
# 当前访问方式
text = message.data.processed_data.content.text

# 理想访问方式
text = message.data.answer.text
```

---

### 6.3 raw_data vs processed_data 的混淆

**当前定义**：
```python
class CapabilityEventData(BaseModel):
    raw_data: Any | None = None
    processed_data: dict[str, Any] | None = None
```

**问题**：
- 什么时候使用 `raw_data`？什么时候使用 `processed_data`？
- 为什么不直接使用一个字段？
- 如果两者都存在，以哪个为准？
- 实际情况：Orchestrator 只读取 `processed_data`，那 `raw_data` 的存在意义是什么？

---

## 7. 改进建议

### 7.1 方案 A：多态事件数据模型（推荐）

**核心思想**：为不同类型的能力定义专用的数据类型，而不是强制所有能力使用同一个 `GenerationData`。

**实现方案**：

```python
# apps/backend/src/agents/orchestrator/types.py

from typing import Union
from pydantic import BaseModel, Field

# 基础事件数据
class BaseEventData(BaseModel):
    session_id: str
    correlation_id: str | None = None
    model_config = ConfigDict(extra="forbid")  # 禁止额外字段

# 文本生成类能力
class GenerationEventData(BaseEventData):
    """文本生成类能力的响应（Outliner, Writer 等）"""
    content: ContentData
    word_count: int | None = None

# 查询类能力
class InquiryEventData(BaseEventData):
    """查询类能力的响应"""
    query: str
    query_type: str
    answer: AnswerData
    confidence: float | None = None

class AnswerData(BaseModel):
    text: str
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

# 角色生成类能力
class CharacterEventData(BaseEventData):
    """角色生成类能力的响应"""
    character: CharacterProfile
    generation_method: str | None = None

class CharacterProfile(BaseModel):
    id: str
    name: str
    personality: dict[str, Any]
    background: dict[str, Any]
    relationships: list[dict[str, Any]]

# 联合类型
EventData = Union[
    GenerationEventData,
    InquiryEventData,
    CharacterEventData,
]

# 更新 CapabilityEventMessage
class CapabilityEventMessage(BaseModel):
    type: str
    data: EventData  # 使用联合类型
    session_id: str | None = None
    correlation_id: str | None = None
```

**处理器改造**：

```python
# apps/backend/src/agents/orchestrator/capability_event_processor.py

async def handle_capability_event(self, msg_type, message, context):
    event_type = context["meta"]["type"]

    # 根据 event_type 选择正确的数据类型
    if event_type.startswith("Inquiry"):
        data = InquiryEventData(**message)
        return await self.handle_inquiry_event(data, context)

    elif event_type.startswith("Character"):
        data = CharacterEventData(**message)
        return await self.handle_character_event(data, context)

    elif event_type in ["Outliner.Theme.Generated", "Writer.Chapter.Generated"]:
        data = GenerationEventData(**message)
        return await self.handle_generation_event(data, context)

    else:
        raise ValueError(f"Unknown event type: {event_type}")
```

**优点**：
- ✅ 类型安全：Pydantic 强制验证，每种能力有专用结构
- ✅ 清晰：字段名称直观反映业务含义
- ✅ 灵活：各能力可独立演进
- ✅ 可维护：添加新能力类型时，只需新增数据类

---

### 7.2 方案 B：扁平化数据结构

**核心思想**：保留通用结构，但降低嵌套层次，去掉 `processed_data` 和强制的 `content` 层。

**实现方案**：

```python
class CapabilityEventMessage(BaseModel):
    type: str
    session_id: str
    correlation_id: str | None = None

    # 业务负载直接放在顶层（去掉 data 层）
    payload: dict[str, Any]  # 允许不同结构

    model_config = ConfigDict(extra="allow")

# InquiryAgent 使用
{
  "type": "Inquiry.Response.Generated",
  "session_id": "sess-123",
  "correlation_id": "corr-456",
  "payload": {
    "query": "进度如何？",
    "answer": {...},
    "query_type": "progress"
  }
}

# CharacterExpert 使用
{
  "type": "Character.Design.Generated",
  "session_id": "sess-123",
  "payload": {
    "character": {...},
    "generation_method": "llm"
  }
}
```

**优点**：
- ✅ 减少嵌套：只有 2 层而不是 4 层
- ✅ 保持灵活性：payload 允许各能力定义自己的结构
- ✅ 向后兼容：可以通过 extra="allow" 支持旧格式

**缺点**：
- ⚠️ 类型安全较弱：payload 是 dict，需要运行时验证

---

### 7.3 方案 C：混合方案（平衡）

**核心思想**：保留 `data` 字段作为业务数据容器，但去掉 `processed_data` 和强制的 `content` 结构。

**实现方案**：

```python
class CapabilityEventMessage(BaseModel):
    type: str
    data: dict[str, Any]  # 直接的业务数据字典

    # 可选的系统字段（向后兼容）
    session_id: str | None = None
    correlation_id: str | None = None

    model_config = ConfigDict(extra="allow")

# InquiryAgent 使用
{
  "type": "Inquiry.Response.Generated",
  "data": {
    "query": "进度如何？",
    "answer": {...},
    "query_type": "progress"
  }
}

# CharacterExpert 使用
{
  "type": "Character.Design.Generated",
  "data": {
    "character": {...},
    "generation_method": "llm"
  }
}

# 处理器统一处理
class CapabilityEventProcessor:
    async def handle_capability_event(self, message, context):
        event_type = message["type"]
        data = message["data"]  # 直接获取，不需要 processed_data

        # 根据 event_type 路由到不同处理器
        handler = self.get_handler(event_type)
        return await handler(data, context)
```

**优点**：
- ✅ 减少嵌套：只有 2 层
- ✅ 灵活性：各能力定义自己的 data 结构
- ✅ 简单：处理器逻辑清晰

---

### 7.4 推荐选择

**首选**：**方案 A（多态事件数据模型）**

**理由**：
1. 类型安全最强：Pydantic 编译时+运行时双重保证
2. 可维护性最好：明确的类型定义，易于理解和扩展
3. 符合领域模型：每种能力有自己的数据模型，而不是强行统一

**次选**：**方案 C（混合方案）**

**理由**：
1. 改动成本低：保留现有的 data 字段，只需去掉 processed_data 和 content 强制
2. 向后兼容性好
3. 足够灵活

---

## 8. 实践指南

### 8.1 Agent 发送消息（推荐）

**目标**：通过 Outbox 模式 + Envelope 封装可靠发送能力事件。

```python
from src.services.outbox.egress import OutboxEgress


class InquiryAgent(BaseAgent):
    def __init__(self, ...):
        super().__init__(name="inquiry", consume_topics=..., produce_topics=...)
        self.egress = OutboxEgress()

    async def process_message(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> None:
        session_id = message.get("session_id")
        query = self._extract_query(message)
        response = await self._handle_query(query, session_id=session_id, context=context)

        correlation_id = (context or {}).get("meta", {}).get("correlation_id")

        await self.egress.enqueue_envelope(
            agent=self.name,
            topic="genesis.inquiry.events",
            key=session_id,
            result={
                "type": "Inquiry.Response.Generated",    # 必填字段
                "session_id": session_id,                  # GenerationData 关键字段
                "content": {                              # 推荐结构
                    "text": response.get("text"),
                    "metadata": {
                        "query_type": response.get("type"),
                        "confidence": response.get("confidence"),
                    },
                },
                "query": query,
                "answer": response,                       # 额外业务字段
            },
            correlation_id=correlation_id,
        )

        return None  # 交由 OutboxRelay 发布
```

### 8.2 Agent 发送消息（兼容路径）

在极少数场景（例如已有旧实现）可以直接 `return dict`，框架会在 `MessageProcessor._send_result()` 执行以下步骤：

1. 自动从字典中提取 `_topic`/`_key`，或使用 Agent 默认的 `produce_topics`
2. 调用 `encode_message(self.agent_name, result, correlation_id, retries)`
3. 经 `BaseOutboxManager.enqueue_message()` 写入 `event_outbox`

```python
class LegacyAgent(BaseAgent):
    async def process_message(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = self._do_work(message)
        return {
            "_topic": "genesis.legacy.events",     # 可选，未提供则 fallback
            "_key": payload.get("session_id"),
            "type": "Legacy.Work.Completed",       # 必填
            "session_id": payload.get("session_id"),
            "content": payload.get("content"),
        }
```

> ⚠️ **注意**：若选择兼容路径，仍需确保返回的数据字段满足 `GenerationData` 约定。建议逐步迁移为 OutboxEgress 写法，以集中管理出站逻辑和指标。

### 8.3 能力事件结构检查清单

| 项目 | 必填 | 说明 | 参考 |
|------|------|------|------|
| `type` | ✅ | 能力事件类型，例如 `Character.Design.Generated` | `Envelope` (`message.py:33`)
| `session_id` | ✅ | 允许放在 `data` 或 `context.meta.aggregate_id` | `capability_event_processor.py:60`
| `content.text` | ✅ | 生成内容正文 | `GenerationData` / `ContentData`
| `content.metadata` | ⚙️ | 可扩展上下文（prompt、attempt 等） | 业务自定义
| 额外业务字段 | ⚙️ | 如 `outline_id`、`character_id` | 会透传至质量审查/领域事件
| 系统字段（`correlation_id` 等） | ❌ | 放在 `context.meta` / Envelope 顶层 | `encode_message`

### 8.4 领域事件结构检查清单

| 项目 | 必填 | 说明 | 参考 |
|------|------|------|------|
| `system.event_type` | ✅ | 领域事件类型，例如 `Genesis.Session.Command.Received` | `domain_event_processor.py:200`
| `system.aggregate_id` | ✅ | 会话/聚合标识 | 同上 |
| `system.correlation_id` | ⚙️ | 如缺失，确保 `context` 或 headers 里提供 | `domain_event_processor.py:24`
| `data.command_type` | ✅ | 命令类型，用于路由 | `domain_event_processor.py:226`
| `data.payload` | ⚙️ | 业务负载，缺失时会继承 `data` 的其他字段 | `domain_event_processor.py:236`
| `schema_version` | ⚙️ | 版本控制，可选 | 同上 |

### 8.5 调试与排错技巧

- **检查 Outbox**：查询 `event_outbox`，确认 `payload` 是否符合期望结构（能力事件=Envelope，领域事件=OutboxPayloadEnvelope）。
- **校验结构**：能力事件可用 `Envelope.model_validate(payload)`；领域事件则使用 `OutboxPayloadEnvelope.model_validate(payload)`（位于 `src/common/outbox/payload.py`）。
- **追踪 correlation_id**：确保请求上下游一致，便于串联日志。
- **观察日志**：`CapabilityEventProcessor`、`DomainEventProcessor` 均在关键节点打点（搜索 `orchestrator_*` 日志）。
- **启用测试工具**：利用 `apps/backend/tests/unit/agents/orchestrator` 下的单测了解结构期望。
