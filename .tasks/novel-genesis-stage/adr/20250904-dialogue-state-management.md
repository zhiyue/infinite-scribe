---
id: ADR-001-dialogue-state-management
title: 对话状态管理方案选择
status: Proposed
date: 2025-09-04
decision_makers: [platform-arch, backend-lead]
related_requirements: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-009, NFR-001, NFR-002]
related_stories: [STORY-001, STORY-002, STORY-003, STORY-004, STORY-005]
supersedes: []
superseded_by: null
tags: [architecture, performance, scalability, state-management]
---

# 对话状态管理方案选择

## Status
Proposed

## Context

### Business Context
基于PRD中的对话式创作引擎需求，系统需要管理复杂的多轮对话状态：
- 相关用户故事：STORY-001 至 STORY-005（创世阶段的所有交互流程）
- 业务价值：对话状态管理是实现"AI主导生成、人类审核微调"核心理念的基础设施
- 业务约束：需要支持3-15轮的对话深化，每个阶段都需要保存完整历史

### Technical Context
基于现有架构分析：
- 当前架构：事件驱动的微服务架构，使用FastAPI作为API网关，Kafka作为事件总线
- 现有技术栈：PostgreSQL（关系型数据）、Redis（缓存）、Neo4j（图数据）、Milvus（向量存储）
- 现有约定：所有服务间通信通过Kafka事件总线，避免直接点对点调用
- 集成点：需要与API Gateway、各Agent服务、Prefect工作流引擎集成

### Requirements Driving This Decision
- FR-001: 创意种子生成需要维护最多10轮对话状态
- FR-002: 立意主题对话系统需要支持3-15轮对话
- FR-003: 世界观构建需要维护5个维度×3-5轮的复杂对话树
- FR-009: 需要完整记录每轮对话的输入输出、时间戳、tokens等元数据
- NFR-001: 首token响应P95<3秒，需要快速访问会话上下文
- NFR-002: 系统需要99.5%可用性，状态管理不能成为单点故障

### Constraints
- 技术约束：上下文窗口32K tokens，超过10轮需要自动摘要
- 业务约束：对话历史需保留至少30天，支持回溯和分支
- 成本约束：需要平衡存储成本和访问性能

## Decision Drivers
- **性能要求**：毫秒级的状态读写，支持高并发访问
- **可靠性要求**：状态不能丢失，需要持久化和备份
- **扩展性要求**：支持水平扩展，应对并发对话会话≥100个
- **复杂度控制**：方案需要在一周MVP周期内实现

## Considered Options

### Option 1: Redis Session + PostgreSQL 持久化（推荐）
- **描述**：使用Redis作为主要的会话存储，提供快速读写；PostgreSQL作为持久化层，定期同步关键状态
- **与现有架构的一致性**：高 - 充分利用现有Redis和PostgreSQL基础设施
- **实现复杂度**：低
- **优点**：
  - 毫秒级访问延迟（Redis内存存储）
  - 与现有技术栈完美匹配
  - 团队已有Redis和PostgreSQL使用经验
  - 支持TTL自动过期管理
  - PostgreSQL提供ACID保证的持久化
- **缺点**：
  - 需要实现双写逻辑
  - Redis故障时需要从PostgreSQL恢复
- **风险**：数据同步延迟可能导致短暂不一致

### Option 2: 纯PostgreSQL with JSONB
- **描述**：使用PostgreSQL的JSONB字段存储对话状态，利用索引优化查询
- **与现有架构的一致性**：中 - 使用现有PostgreSQL，但未充分利用Redis
- **实现复杂度**：低
- **优点**：
  - 单一数据源，无同步问题
  - ACID事务保证
  - JSONB支持灵活的schema演进
- **缺点**：
  - 访问延迟较高（磁盘I/O）
  - 高并发下可能成为瓶颈
  - 缺少自动过期机制
- **风险**：性能可能无法满足P95<3秒的要求

### Option 3: 内存缓存 + Event Sourcing
- **描述**：应用内存存储活跃会话，通过事件溯源重建状态
- **与现有架构的一致性**：中 - 符合事件驱动理念，但引入新的复杂度
- **实现复杂度**：高
- **优点**：
  - 极低延迟（内存访问）
  - 完整的审计追踪
  - 可以重放历史获得任意时间点状态
- **缺点**：
  - 实现复杂度高
  - 需要处理事件去重、顺序保证等问题
  - MVP时间紧迫，风险较高
- **风险**：一周内难以实现稳定的事件溯源系统

## Decision
建议采用 **Option 1: Redis Session + PostgreSQL 持久化**

理由：
1. 最佳平衡性能和可靠性需求
2. 充分利用现有基础设施，降低集成风险
3. 实现复杂度适中，符合MVP时间要求
4. 团队熟悉技术栈，减少学习成本

一致性与并发控制的核心选型（更新）：
- 一致性模型：采用写通（write-through）+ 缓存旁路（cache-aside）。先写 PostgreSQL（事务提交成功），再回填 Redis；读优先 Redis，miss 则回源 PG 并回填。放弃“先写 Redis、异步写 PG”的默认路径，以降低数据丢失/不一致风险。
- 并发控制：使用乐观并发控制（OCC），在 `conversation_sessions` 使用 `version` 字段；更新语句按 `WHERE id=? AND version=?`，成功后 `version=version+1`。
- 幂等与顺序：Kafka 分区键统一为 `session_id` 保序；数据库对“轮次”使用唯一键（`session_id, round_path`）与 `ON CONFLICT` 保证幂等；业务贯穿 `correlation_id`。

## Consequences

### Positive
- 毫秒级的会话访问速度，轻松满足NFR-001性能要求
- 双层存储提供高可用性，Redis故障时可从PostgreSQL恢复
- 支持灵活的过期策略和内存管理
- 可以独立扩展缓存层和持久层

### Negative
- 需要维护两个数据存储的一致性
- 增加了系统复杂度（双写、同步逻辑）
- Redis内存成本相对较高

### Risks
- **风险1：数据不一致**
  - 缓解：实现最终一致性模型，关键操作直接读PostgreSQL
- **风险2：Redis内存溢出**
  - 缓解：设置合理的TTL，实施LRU淘汰策略，监控内存使用

## Implementation Plan

### Integration with Existing Architecture
- **代码位置**：`apps/backend/src/core/session/` - 创建专门的会话管理模块
- **模块边界**：
  - SessionManager: 统一的会话管理接口
  - RedisSessionStore: Redis存储实现
  - PostgresSessionRepository: PostgreSQL持久化层
- **依赖管理**：使用现有的redis和asyncpg客户端库

### Consistency & Concurrency（更新）
- **一致性**：写通（PG→Redis），读缓存旁路；保证持久化优先，缓存为附属。
- **OCC**：`conversation_sessions.version` 字段实现乐观锁；冲突返回重试/合并策略。
- **幂等**：
  - 会话级：`id` 为主键，`updated_at` 与 `version` 控制更新。
  - 轮次级：`(session_id, round_path)` 唯一；`correlation_id` 追踪重试与去重。
- **顺序**：Kafka Producer 设置 `key=session_id`，确保同会话内顺序可靠。

### Kafka & Idempotency（更新）
- 事件 envelope：`{ id, ts, correlation_id, session_id, round_path, payload, retries }`。
- Producer：`acks=all`，`enable_idempotence=true`，`linger_ms=5`（沿用全局默认）。
- Consumer/写库：对 `conversation_rounds` 使用 `INSERT ... ON CONFLICT DO NOTHING/UPDATE`。

### Migration Strategy（更新）
- 阶段0：确认 `genesis_sessions` 未被业务使用，准备用通用表替换并删除。
- 阶段1：新增 `conversation_sessions` 与 `conversation_rounds`（含索引）。
- 阶段2：更新代码与文档中 `session_id` 的语义为“关联 conversation_sessions.id”。
- 阶段3：实现 SessionManager 与缓存写通策略，并完成集成/性能/故障测试。
- 阶段4：下线并删除 `genesis_sessions`（如需过渡，可临时保留同名视图）。

### Implementation Details（采用通用对话表）
```python
# Redis存储策略
- Key格式: `dialogue:session:{session_id}`
- TTL: 24小时（可配置，滑动过期，读写续期）
- 序列化: JSON（使用Pydantic的json()方法）
- 失效广播: Pub/Sub `session_invalidate:{session_id}` 用于多实例同步失效

# PostgreSQL schema（新增通用会话 + 轮次表；删除未使用的 genesis_sessions）
-- 1) 会话表
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY,
    scope_type TEXT NOT NULL,                 -- GENESIS/CHAPTER/REVIEW/...（后续可迁 ENUM）
    scope_id TEXT NOT NULL,                   -- 绑定的业务实体ID
    status TEXT NOT NULL DEFAULT 'ACTIVE',    -- ACTIVE/COMPLETED/ABANDONED/PAUSED
    stage TEXT,                               -- 业务阶段（可选）
    state JSONB,                              -- 会话聚合/摘要
    version INTEGER NOT NULL DEFAULT 0,       -- OCC 版本
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_scope ON conversation_sessions (scope_type, scope_id);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_updated_at ON conversation_sessions (updated_at DESC);

-- 2) 轮次表
CREATE TABLE conversation_rounds (
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    round_path TEXT NOT NULL,                 -- 如 '1', '2', '2.1', '2.1.1'
    role TEXT NOT NULL,                       -- user/assistant/system/tool 等
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_conversation_rounds_session_created ON conversation_rounds (session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_rounds_correlation ON conversation_rounds (correlation_id);

# 同步策略
- 写入（写通）：先写PostgreSQL（事务&幂等），提交成功后回填/失效Redis；回填失败不回滚事务，记录指标并退化为首次读回源。
- 读取：优先Redis；miss/过期则回源PostgreSQL并回填，设置滑动TTL。
- 并发更新：`UPDATE conversation_sessions SET state=?, version=version+1, updated_at=NOW() WHERE id=? AND version=?`；受影响行数=0则触发重试/合并。
- 轮次追加：`INSERT ... ON CONFLICT DO NOTHING/UPDATE` 保证重复投递幂等。
- 缓存失效：写通后发布 `session_invalidate:{session_id}`，多实例清理本地缓存。

# 摘要策略（新增）
- 触发：当累计轮次>N 或累计 `context_tokens` 超阈值时触发滚动摘要；保留“最近N轮 + 累积摘要 + locked_content”。
- 元数据：摘要记录 `summary_version` 与 `source_rounds`；使用原子替换（写临时字段→校验→切换）。
- 长期语义记忆（可选）：对“确认/锁定”的事实入 Milvus 以 RAG 检索；避免对噪声内容入库。
```

### Failure & Recovery（新增）
- Redis：生产采用 Sentinel/Cluster；开启 AOF（everysec）+ 定期 RDB；Redis 不可用时直接回源 PG，并临时禁用回填。
- Postgres：短暂失败时写请求可进入 outbox（可选）并重放；读路径告警并退化策略生效。
- 一致性窗口：监控“缓存回填失败率”“回源比例”，若异常升高自动降级为“只读缓存”。

### Cache Invalidation & Broadcast（新增）
- 写通后通过 Redis Pub/Sub 向 `session_invalidate:{session_id}` 频道广播；各实例订阅并删除/刷新本地缓存键。

### Capacity & Sizing（新增）
- 假设：并发会话≥100、每会话10–15轮、平均每轮消息体 2–8KB。
- Redis：设置 `maxmemory-policy=allkeys-lru`，监控 `evicted_keys`；热键空间使用前缀 `dialogue:session:*`。
- 保留期：≥30天由 PG 负责，Redis 仅做 24h 热缓存（滑动）。
```

### Code Organization（代码组织，更新）
- 模块归属：`apps/backend/src/core/session/`（SessionManager 接口 + Redis adapter + Postgres repository），与 ORM 解耦，通过服务层使用 `postgres_service` 与 `redis_service`。
- 模型与迁移：新增 ORM `ConversationSession`/`ConversationRound` 对应 `conversation_sessions/rounds`；删除未使用的 `genesis_sessions`；Alembic 迁移置于 `apps/backend/alembic/versions/`。
- Schemas：在 `apps/backend/src/schemas/session/` 增加轻量 DTO（仅 API 层使用），Agent 仅依赖 `session_id/correlation_id`。
- 事件与消息：与 `event_outbox` 对齐，发布带 `correlation_id` 的消息；分区键统一为 `session_id`。
- 测试布局：`tests/unit/core/session/`（缓存策略、OCC、摘要触发）与 `tests/integration/session/`（PG+Redis 端到端）。

### Schema Changes Summary（与 database-schema.md 对齐，更新）
- 删除未使用的 `genesis_sessions`。
- 新增 `conversation_sessions` 与 `conversation_rounds` 作为统一的对话存储。
- 索引：`conversation_sessions(scope_type, scope_id)`、`conversation_sessions(updated_at)`；`conversation_rounds(session_id, created_at)`、`conversation_rounds(correlation_id)`。
- 外键策略：`conversation_rounds.session_id -> conversation_sessions.id`（CASCADE 删除）。

### Rollback Plan
- **触发条件**：性能不达标或数据一致性问题严重
- **回滚步骤**：
  1. 停止新会话创建
  2. 导出Redis中的活跃会话到PostgreSQL
  3. 切换到纯PostgreSQL模式（Option 2）
  4. 验证系统正常运行
- **数据恢复**：PostgreSQL中保留完整历史，可随时恢复

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：符合现有的微服务+事件驱动模式
- **代码审查重点**：
  - 双写逻辑的原子性
  - 错误处理和降级策略
  - 内存泄漏和资源管理

### Metrics
- **性能指标**：
  - 会话读取延迟：当前N/A → P95 < 10ms
  - 会话写入延迟：当前N/A → P95 < 50ms
  - Cache命中率：目标 > 95%
- **质量指标**：
  - 代码覆盖率：> 80%
  - 数据一致性检查通过率：> 99.9%

### Observability & Alerts（新增）
- 指标：
  - 写回失败率/回填失败率、回源比例、OCC 冲突率、幂等冲突率、缓存一致性窗口（PG 与 Redis 偏差时间）、Redis 内存与逐出次数、Kafka 重试/DLT 率。
- 追踪：OpenTelemetry 贯穿 API→Agent→SessionManager→Redis/PG，传递 `correlation_id`。
- 告警阈值：命中率 < 90%、写入错误率 > 0.5%、回源比例 > 20%、回填失败率 > 1%、逐出速率异常上升。

### Test Strategy
- **单元测试**：SessionManager各方法的独立测试
- **集成测试**：Redis + PostgreSQL完整流程测试
- **性能测试**：使用Locust模拟100并发会话
- **故障测试**：模拟Redis宕机，验证降级和恢复流程
 - **一致性/并发**：OCC 冲突重试、幂等重复入库（同一 `correlation_id`）、顺序性（Kafka key=session_id）。
 - **超时与CI**：按仓库指南配置 `pytest-timeout` 与外层 `timeout` 包裹长测用例。

## References
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [PostgreSQL JSONB Performance](https://www.postgresql.org/docs/current/datatype-json.html)
- 现有项目架构文档：`docs/architecture/high-level-architecture.md`
- 数据库设计总览：`docs/architecture/database-schema.md`

## Changelog
- 2025-09-04: 初始草稿创建
- 2025-09-04: 采纳通用对话表（conversation_sessions/rounds），计划删除 genesis_sessions
