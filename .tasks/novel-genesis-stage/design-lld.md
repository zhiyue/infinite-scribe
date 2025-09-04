# 低层设计 (Low-Level Design) — 小说创世阶段

文档版本: 1.0  
生成日期: 2025-09-05  
对应 HLD: .tasks/novel-genesis-stage/design-hld.md

## 概述

本 LLD 基于已批准的 HLD，细化“小说创世阶段（Stage 0–5）”的实现细节，覆盖 API/会话服务、事件与 Outbox、Orchestrator、专门化 Agents、EventBridge（Kafka→Redis SSE）、数据模型（PostgreSQL/Neo4j/Milvus）、异常与重试、测试与容量、部署与回滚等。P1 聚焦“至少一次 + 事务性 Outbox + Kafka”链路与基础安全；P2 预留 Prefect 编排与 RBAC。

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
  }): Promise<{ session_id: string; novel_id: string; status: string; stage: string }>

  getSession(sessionId: string): Promise<ConversationSession>
  listRounds(sessionId: string, params?: { after?: string; limit?: number }): Promise<ConversationRound[]>

  postMessage(sessionId: string, body: UserMessage): Promise<{ accepted: true; correlation_id: string }>
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

职责：消费 `genesis.session.events`；将 `Genesis.Session.*.Requested` 映射到对应能力 `*.tasks`；将能力完成事件回流为 `Genesis.Session.*.Proposed/Completed`。

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

职责：消费 `genesis.session.events`，筛选可见 Facts，发布到 Redis Streams（持久化）+ PubSub（实时）。

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

职责：消费各自 `*.tasks`，处理后产出到 `*.events`；错误分类→重试/ DLT；可携带 `_topic/_key` 覆盖默认路由。

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

## 前端组件设计

#### 组件表格

| 组件名称            | 职责                               | Props/状态摘要                                     |
| ------------------- | ---------------------------------- | -------------------------------------------------- |
| GenesisFlow         | 创世阶段总控与阶段面板切换         | sessionId, stage, onCommand, onAccept, onRegenerate |
| SessionSidebar      | 会话历史/轮次/版本概览             | sessionId, rounds, onSelectRound                   |
| EventStream         | 订阅 SSE 并分发到 UI               | sseToken, onEvent, lastEventId                     |
| StagePanel          | 各阶段详情（主题/世界/人物/情节/细节） | stage, data, onEdit, onConfirm                     |

#### API 端点设计

| 方法 | 路由                                        | 目的                 | 认证 | 状态码                               |
| ---- | ------------------------------------------- | -------------------- | ---- | ------------------------------------ |
| POST | /api/v1/genesis/sessions                    | 创建创世会话         | 需要 | 201, 400, 401, 500                   |
| GET  | /api/v1/genesis/sessions/{id}               | 查询会话             | 需要 | 200, 401, 404, 500                   |
| GET  | /api/v1/genesis/sessions/{id}/rounds        | 列出会话轮次         | 需要 | 200, 401, 404, 500                   |
| POST | /api/v1/genesis/sessions/{id}/messages      | 提交用户消息         | 需要 | 202, 400, 401, 409, 422, 500         |
| POST | /api/v1/genesis/sessions/{id}/commands/{ct} | 提交幂等命令         | 需要 | 202, 400, 401, 409, 422, 500         |
| GET  | /api/v1/events/stream?sse_token=...         | SSE 事件流（下行）   | 需要 | 200, 401, 403, 500（网络断连重连策略） |

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

#### 数据库模式设计（PostgreSQL 摘要）

```sql
-- 枚举
CREATE TYPE command_status AS ENUM ('RECEIVED','PROCESSING','COMPLETED','FAILED');
CREATE TYPE outbox_status   AS ENUM ('PENDING','SENDING','SENT','FAILED');

-- 会话/轮次、命令收件箱、领域事件、发件箱（见 HLD DDL 章节，保持一致）
```

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
  generateKey(params: any) { return `dialogue:session:${params.sessionId}` }
  getTTL(_key: string) { return this.DEFAULT_TTL }
  async invalidate(pattern: string) { /* redis scan+del */ }
  async warmup(keys: string[]) { /* batch mget */ }
}
```

## 异常处理与重试机制

### 异常分类

| 异常类型       | 错误码 | 处理策略                 | 重试策略                  |
| -------------- | ------ | ------------------------ | ------------------------- |
| 参数校验失败   | 400    | 返回详细错误             | 不重试                    |
| 未认证/未授权  | 401/403| 返回错误，提示登录/权限  | 不重试                    |
| 幂等冲突       | 409    | 返回冲突信息             | 1 次（短退避）            |
| 语义校验失败   | 422    | 返回错误，标注字段       | 不重试                    |
| 限流/超时      | 429/504| 等待后重试               | 指数退避 ≤3               |
| 服务器错误     | 500    | 降级/记录/告警           | 指数退避 ≤3               |
| Agent 不可重试 | -      | 写入 DLT                 | 不重试                    |

### 重试实现（前端/服务示例）

```typescript
function retryable<T>(fn: () => Promise<T>, max = 3, base = 500) {
  return (async () => {
    let attempt = 0
    while (true) {
      try { return await fn() } catch (e) {
        if (attempt++ >= max) throw e
        await new Promise(r => setTimeout(r, Math.min(30_000, base * 2 ** attempt)))
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
    limits:   { cpu: '2000m', memory: '2Gi' }
  concurrency:
    max_connections: 1000
    max_requests_per_second: 500
    max_concurrent_requests: 100
  queues:
    outbox_sender: { max_size: 20000, batch: 100, max_delay: 60s }
  pools:
    database: { min_size: 10, max_size: 100, max_idle_time: 300s }
    redis:    { min_size: 5, max_size: 50 }
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
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
    - type: Resource
      resource: { name: memory, target: { type: Utilization, averageUtilization: 80 } }
```

## 测试策略

### 测试目标

- 降低质量风险；保障对话与事件链路端到端稳定；满足 NFR 延迟目标

### 风险矩阵（摘要）

| 区域       | 风险 | 必须                 | 可选   |
| ---------- | ---- | -------------------- | ------ |
| 会话一致性 | 高   | 单元、集成、E2E      | -      |
| 事件可靠性 | 高   | 契约、集成           | 弹性   |
| 图一致性   | 中   | 集成、属性           | -      |
| 向量检索   | 中   | 集成                 | 性能   |

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

| 依赖       | 版本   | 用途           | 降级方案    |
| ---------- | ------ | -------------- | ----------- |
| PostgreSQL | 14+    | 会话/事件表    | 只读降级    |
| Redis      | 7+     | 缓存与 SSE     | 降级为无 SSE |
| Kafka      | 3.x+   | 事件总线       | 暂存 Outbox |
| Neo4j      | 5.x+   | 知识图谱与校验 | 关闭校验    |
| Milvus     | 2.4+   | 嵌入检索       | 关闭向量检索 |

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

