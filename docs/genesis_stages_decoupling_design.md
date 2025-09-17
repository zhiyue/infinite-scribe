**标题**
创世阶段与对话会话解耦设计（Genesis Stages Decoupling）

**作者/日期**
- 作者：内部架构组
- 日期：2025-09-17

**状态**
- 提案（Proposal）

**背景与问题**
- 现有系统用通用对话聚合 `conversation_sessions/rounds` 承载用户与 Agent 的交互，并在 `conversation_sessions.stage/state` 中混合了创世（Genesis）业务状态。
- 当一个 Genesis 阶段需要多个独立会话（并行/历史/复盘），或跨阶段管理与统计时，耦合在 `conversation_sessions` 难以清晰表达、复用与审计。
- 诉求：
  - 将 Genesis 的“流程/阶段/阶段配置与产出”从对话聚合中解耦；
  - 支持“每个阶段可以拥有独立的 session，且可能有多个 session”；
  - 复用现有命令（CommandInbox）、任务（AsyncTask）、事件（DomainEvent/EventOutbox）体系与对话存储，不破坏既有 API。

**目标**
- 解耦：对话会话（Conversation）保持领域无关；Genesis 业务独立建模。
- 多会话：同一阶段允许 1..N 个对话会话绑定，且可指定主会话（primary）。
- 审计与迭代：阶段记录可保留历史（多条记录或迭代计数），支持配置/结果/指标持久化。
- 低侵入：不修改 `conversation_sessions/rounds` 结构，通过关联表连接。
- 可观测：沿用 `correlation_id=command.id` 贯穿命令→任务→事件→回合，阶段/流程 ID 加入事件元数据，便于前端聚合。

**非目标（Non-Goals）**
- 引入重量级 BPM/工作流引擎；
- 立即替换现有对话/命令/任务 API；
- 为每个阶段单独建一张专有数据表（先用通用阶段表表达）。

**高层架构**
- 对话层（Conversation）：`conversation_sessions`、`conversation_rounds` 承载所有消息与可视化回合树。
- Genesis 层（新）：
  - `genesis_flows`：创世流程实例（对某部小说的总进度）。
  - `genesis_stage_records`：阶段业务记录（配置、结果、指标、状态、迭代）。
  - `genesis_stage_sessions`：阶段↔对话会话的关联（多对多，含主会话标记与类别）。
  - （可选）`genesis_stage_task_links`：阶段↔任务关联，指向 `async_tasks.id`（或现存 `genesis_tasks`）。
- 事件层：`domain_events` + `event_outbox` 不变，事件 `payload/metadata` 增加 `flow_id/stage_id`（可选）。

**数据模型（PostgreSQL）**
- 表：`genesis_flows`
  - 字段：
    - `id UUID PK`
    - `novel_id UUID NOT NULL`（FK→`novels.id`）
    - `status VARCHAR NOT NULL`（GenesisStatus：IN_PROGRESS/COMPLETED/ABANDONED/PAUSED）
    - `current_stage VARCHAR NULL`（GenesisStage：INITIAL_PROMPT/WORLDVIEW/CHARACTERS/PLOT_OUTLINE/FINISHED）
    - `version INT NOT NULL DEFAULT 1`
    - `state JSONB NULL`（全局聚合与跨阶段元数据，可选）
    - `created_at/updated_at TIMESTAMPTZ`
  - 约束/索引：`UNIQUE(novel_id)`；`INDEX(novel_id,status)`；`INDEX(current_stage)`

- 表：`genesis_stage_records`
  - 字段：
    - `id UUID PK`
    - `flow_id UUID NOT NULL`（FK→`genesis_flows.id`）
    - `stage VARCHAR NOT NULL`（GenesisStage）
    - `status VARCHAR NOT NULL`（RUNNING/COMPLETED/FAILED/PAUSED 等）
    - `config JSONB NULL`（阶段参数与用户选择）
    - `result JSONB NULL`（阶段产出索引/摘要：如世界观条目/角色ID列表等）
    - `iteration_count INT NOT NULL DEFAULT 0`
    - `metrics JSONB NULL`（tokens/cost/latency 等聚合）
    - `started_at/completed_at TIMESTAMPTZ NULL`
    - `created_at/updated_at TIMESTAMPTZ`
  - 索引：`INDEX(flow_id, stage, created_at DESC)`；是否 `UNIQUE(flow_id, stage)` 取决于是否要保留历史（建议不唯一以保留审计）。

- 表：`genesis_stage_sessions`
  - 作用：阶段↔对话会话 关联表（多对多），支持一个阶段多个会话、主会话标记。
  - 字段：
    - `id UUID PK`
    - `stage_id UUID NOT NULL`（FK→`genesis_stage_records.id`）
    - `session_id UUID NOT NULL`（FK→`conversation_sessions.id`）
    - `status VARCHAR NOT NULL DEFAULT 'ACTIVE'`（ACTIVE/ARCHIVED/CLOSED）
    - `is_primary BOOLEAN NOT NULL DEFAULT FALSE`
    - `session_kind VARCHAR NULL`（user_interaction/review/agent_autonomous 等）
    - `created_at/updated_at TIMESTAMPTZ`
  - 约束/索引：
    - `UNIQUE(stage_id, session_id)`
    - 部分唯一：`UNIQUE(stage_id) WHERE is_primary = true`（可选）
    - `INDEX(stage_id)`，`INDEX(session_id)`

- 表（可选）：`genesis_stage_task_links`
  - 字段：`stage_id UUID NOT NULL`（FK→`genesis_stage_records.id`），`task_id UUID NOT NULL`（FK→`async_tasks.id`）
  - 约束/索引：`PRIMARY KEY(stage_id, task_id)`；`INDEX(task_id)`

**与对话会话的关联规则**
- 仅在 `genesis_stage_sessions` 建立 FK 关联；`conversation_sessions` 不新增 Genesis 字段。
- 绑定校验：
  - `conversation_sessions.scope_type` 必须为 `GENESIS`；
  - `conversation_sessions.scope_id` 必须等于 `genesis_flows.novel_id`（防止跨小说绑定）。
- Round 查询（按阶段）：
  - `SELECT r.* FROM genesis_stage_sessions gss JOIN conversation_rounds r ON r.session_id=gss.session_id WHERE gss.stage_id=$1 ORDER BY r.created_at;`

**核心用例与时序**
- 创建创世流程
  1) 用户新建 Genesis 会话或进入创作 → 若无 `genesis_flows(novel_id)` 则创建（`status=IN_PROGRESS`，`current_stage=INITIAL_PROMPT`）。
- 进入某阶段并创建会话（可多个）
  1) 插入 `genesis_stage_records(flow_id, stage, status=RUNNING, config=...)`；
  2) 通过通用 API 创建 `conversation_session(scope_type=GENESIS, scope_id=novel_id)`；
  3) 插入 `genesis_stage_sessions(stage_id, session_id, is_primary=?, session_kind=...)`；
  4) 对话消息/命令/回合照旧落库，SSE 事件携带 `correlation_id`，UI 从阶段关联反查。
- 并行会话
  - 同一 `stage_id` 可绑定多个 `session_id`；`is_primary=true` 的会话作为默认展示源。
- 完成阶段
  - 更新 `genesis_stage_records.status=COMPLETED`、写回 `result/metrics`；
  - `genesis_flows.current_stage` 推进或 `status=COMPLETED`；
  - 将 `genesis_stage_sessions` 置为 `ARCHIVED`（历史复盘仍可读）。

**API 设计（基于命令模式的简化）**

### 实际实现状态
当前 Genesis API 实现已大幅精简，实际包含 **6 个核心接口**，分布在：
- **flows.py**: 4个接口（流程管理）
- **stage_sessions.py**: 2个接口（会话关联）
- **queries.py**: 1个查询函数（fetch_stage_conversation_rounds）

#### 已实现的核心接口（6个）
- **`POST /api/v1/genesis/flows/{novel_id}`** - 幂等创建或返回当前 flow
- **`GET /api/v1/genesis/flows/{novel_id}`** - 查看流程进度与状态
- **`POST /api/v1/genesis/flows/{novel_id}/switch-stage`** - 切换流程阶段（支持前进/后退/跳转）
- **`POST /api/v1/genesis/flows/{novel_id}/complete`** - 完成流程
- **`POST /api/v1/genesis/stages/{stage_id}/sessions`** - 创建并绑定会话（或绑定现有 session_id）
- **`GET /api/v1/genesis/stages/{stage_id}/sessions`** - 列出阶段的所有会话

#### 查询工具函数
- **`fetch_stage_conversation_rounds(db, stage_id, limit, offset)`** - 按阶段查询对话轮次
  - 实现设计文档中的 SQL 查询：`SELECT r.* FROM genesis_stage_sessions gss JOIN conversation_rounds r ON r.session_id=gss.session_id WHERE gss.stage_id=$1 ORDER BY r.created_at`

### 实现特点
1. **已高度精简**：实际实现比设计文档建议的 5 个核心接口还多 1 个，但功能更完整
2. **支持阶段切换**：`switch-stage` 接口支持灵活的阶段导航（前进/后退/跳转）
3. **流程完成**：独立的 `complete` 接口用于标记流程完成
4. **会话绑定**：支持创建新会话或绑定现有会话到阶段
5. **查询分离**：对话轮次查询通过专用函数处理，遵循关注点分离

#### 复用接口（对话操作）
- **历史消息查询**: `GET /api/v1/conversations/sessions/{session_id}/rounds`（分页、排序、角色过滤）
- **发送命令**: `POST /api/v1/conversations/sessions/{session_id}/commands`（创建和消息发送）
- **单个轮次查询**: `GET /api/v1/conversations/sessions/{session_id}/rounds/{round_id}`
- **会话内容导出**: `POST /api/v1/conversations/sessions/{session_id}/content/export`

**事件与可观测性**
- 继续使用 `DomainEvent` 与 `EventOutbox`；
- 在事件 `payload/metadata` 中增加 `flow_id/stage_id`（可选）；
- 仍以 `correlation_id=command.id` 贯穿任务链路；
- 前端订阅 SSE 后可按 `stage_id` 聚合对话/任务进度。

**迁移计划（Alembic 草案）**
1) 创建三张表：`genesis_flows`、`genesis_stage_records`、`genesis_stage_sessions`；
2) 为上述表建立索引与部分唯一约束；
3) 不修改既有 `conversation_*`、`async_tasks`；
4) 兼容期内允许从 `conversation_sessions.state/stage` 只读回填到新表（可选脚本）。

示例 DDL 片段（简化）
```sql
CREATE TABLE genesis_flows (
  id uuid PRIMARY KEY,
  novel_id uuid NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
  status varchar NOT NULL,
  current_stage varchar NULL,
  version int NOT NULL DEFAULT 1,
  state jsonb NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_genesis_flows_novel ON genesis_flows(novel_id);

CREATE TABLE genesis_stage_records (
  id uuid PRIMARY KEY,
  flow_id uuid NOT NULL REFERENCES genesis_flows(id) ON DELETE CASCADE,
  stage varchar NOT NULL,
  status varchar NOT NULL,
  config jsonb NULL,
  result jsonb NULL,
  iteration_count int NOT NULL DEFAULT 0,
  metrics jsonb NULL,
  started_at timestamptz NULL,
  completed_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_stage_records_flow_stage ON genesis_stage_records(flow_id, stage, created_at DESC);

CREATE TABLE genesis_stage_sessions (
  id uuid PRIMARY KEY,
  stage_id uuid NOT NULL REFERENCES genesis_stage_records(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
  status varchar NOT NULL DEFAULT 'ACTIVE',
  is_primary boolean NOT NULL DEFAULT false,
  session_kind varchar NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(stage_id, session_id)
);
CREATE INDEX ix_stage_sessions_stage ON genesis_stage_sessions(stage_id);
CREATE INDEX ix_stage_sessions_session ON genesis_stage_sessions(session_id);
-- 可选：仅允许一个主会话
-- CREATE UNIQUE INDEX ux_stage_primary ON genesis_stage_sessions(stage_id) WHERE is_primary = true;
```

**服务层设计（骨架）**
- `GenesisFlowService`
  - `ensure_flow(novel_id) -> flow`
  - `get_flow(novel_id) -> flow`
  - `advance(flow_id, next_stage)` / `complete(flow_id)`
- `GenesisStageService`
  - `create_stage(flow_id, stage, config) -> stage_id`
  - `add_stage_session(stage_id, session_id, is_primary, kind)`
  - `create_and_bind_session(stage_id, novel_id, is_primary, kind) -> session_id`
  - `list_stage_sessions(stage_id) -> [session]`
  - `complete_stage(stage_id, result, metrics)`
- 对话层不改动；绑定时做 `scope_type/scope_id` 校验。

**权限与安全**
- 绑定校验：`conversation_sessions.scope_type=GENESIS` 且 `scope_id == flow.novel_id`。
- API 访问需复用现有鉴权（用户必须是 `novel.owner`）。

**性能与扩展性**
- 核心查询走 `(stage_id)` 与 `(session_id)` 索引；
- 阶段→回合查询通过一次 JOIN 到 `conversation_rounds`，可分页；
- 大量历史阶段可通过归档策略清理或基于 `created_at` 滚动查询。

**测试计划**
- 单元：
  - 绑定校验（错误 `scope_type/scope_id` 拒绝）。
  - 一个阶段允许多个会话；`is_primary` 局部唯一约束。
  - 阶段完成后，查询回合仍可从历史会话读出。
- 集成：
  - 从创建阶段→创建绑定会话→发消息→按阶段查询回合的端到端。
  - 与 SSE：事件携带 `stage_id`，前端按阶段聚合。

**发布与回滚**
- 发布：先建表与索引；再灰度接入绑定逻辑；最后提供查询 API。
- 回滚：解绑逻辑关闭；新表保留不影响对话功能；必要时清空新表。

**与现有实现的对比**
- 保留 `conversation_sessions` 纯粹性（对话容器）；
- Genesis 业务状态、配置与产出移至专用表，查询边界清晰；
- 支持“每个阶段多个 session”的一等能力。

**conversation_sessions 表字段清理计划**

解耦后，`conversation_sessions` 表将专注于对话容器的职责，需要清理Genesis业务相关字段：

### 建议删除的字段

#### 立即删除
- **`stage`** (位置: `apps/backend/src/models/conversation.py:41`)
  - 原本承载当前业务阶段；解耦后应由 `genesis_flows.current_stage` 与 `genesis_stage_records` 管理。

- **`state`** (位置: `apps/backend/src/models/conversation.py:42`)
  - 原本承载阶段配置/聚合状态；解耦后应落在 `genesis_flows.state`（全局）与 `genesis_stage_records.config/result/metrics`（分阶段）。

#### 可选删除
- **`version`** (位置: `apps/backend/src/models/conversation.py:43`)
  - 仅用于会话层乐观并发控制（更新 stage/state/status 时自增）。如果后续不在会话层更新业务字段（只创建/归档），可改用 `updated_at` 作为 ETag 并去掉 `version`。
  - 替代方案：ETag = `updated_at.isoformat()` 或数据库 `xmin`（Postgres）作为并发戳。

### 必须保留的字段

- **`scope_type`、`scope_id`** (位置: `apps/backend/src/models/conversation.py:38, 39`)
  - 作用：会话归属与权限校验（GENESIS 下 `scope_id=novel_id`）；列表查询按 scope 过滤。

- **`status`** (位置: `apps/backend/src/models/conversation.py:40`)
  - 作用：标记会话生命周期（ACTIVE/PAUSED/COMPLETED…），配合列表过滤及归档。

- **`round_sequence`** (位置: `apps/backend/src/models/conversation.py:44`)
  - 作用：顶层 round 自增编号（生成 1/2/3…）。强依赖于创建轮次逻辑。
  - 使用处：`apps/backend/src/common/services/conversation/conversation_round_creation_service.py:222`

- **`created_at`、`updated_at`** (位置: `apps/backend/src/models/conversation.py:45-48`)
  - 作用：排序、审计、ETag 替代（若去掉 version）。

### 连带影响调整

#### API 模型与返回
- **`SessionResponse`** (位置: `apps/backend/src/schemas/novel/dialogue/read.py:103`)
  - 当前包含 `stage/state/version`，删除后需去掉或置为可选默认空。
- **会话创建/更新接口** (位置: `apps/backend/src/api/routes/v1/conversations/conversations_sessions.py`)
  - 去掉对 `stage/state` 的读写；ETag 改用 `updated_at`。

#### 阶段相关旧接口
- **`GET/PUT /sessions/{id}/stage`** (位置: `apps/backend/src/api/routes/v1/conversations/conversations_stages.py`)
  - 基于会话 `stage/version`，解耦后应改为 Genesis 新接口或移除。

#### 仓储与服务层
- **`ConversationSessionRepository.create/update`** (位置: `apps/backend/src/common/repositories/conversation/session_repository.py`)
  - 去掉 `stage/state/version` 参数与 OCC 分支；或仅保留 `status` 更新。
- **`ConversationSessionService.update_session`**
  - 不再处理 `stage/state/version`；若保留 `version`，请明确仅对 `status` 做 OCC。

### 进一步精简（可选）

如果后续不再按 `status` 过滤/变更（完全由 `genesis_stage_sessions.status` 管理生命周期），也可考虑移除会话层 `status`，仅通过是否仍被阶段引用来判断会话是否活跃。但建议保留 `status` 以便通用场景（非 Genesis）复用。

### 推荐方案

- **最小改动版**：删 `stage/state`，保留 `version`（继续用 `version` 做 ETag 与 OCC），其余不动。
- **彻底简化版**：删 `stage/state/version`，ETag 改用 `updated_at`；会话只承载对话容器最小字段，所有业务状态放入 `genesis_flows/genesis_stage_records/genesis_stage_sessions`。

**后续可选增强**
- 增加 `genesis_stage_task_links` 与 `depends_on` 建模任务依赖；
- 为阶段记录增加变更审计表；
- 提供阶段视图的聚合 API（进度、成本、失败率）。

**Definition of Done**
- [x] **Alembic 迁移创建三张表（含索引/约束）** - 已完成数据模型实现
- [x] **服务层实现** - 已实现 GenesisFlowService 和 GenesisStageSessionService
- [x] **绑定校验与错误处理** - 完整的 scope 与 novel 归属校验
- [x] **核心 API 实现（6个实际接口）**
  - [x] `POST /api/v1/genesis/flows/{novel_id}` - 创建/获取流程
  - [x] `GET /api/v1/genesis/flows/{novel_id}` - 查看流程进度
  - [x] `POST /api/v1/genesis/flows/{novel_id}/switch-stage` - 阶段切换（替代单独创建阶段）
  - [x] `POST /api/v1/genesis/flows/{novel_id}/complete` - 完成流程
  - [x] `POST /api/v1/genesis/stages/{stage_id}/sessions` - 绑定会话
  - [x] `GET /api/v1/genesis/stages/{stage_id}/sessions` - 列出阶段会话
- [x] **命令集成** - 创建和消息发送通过 ConversationCommand 处理
- [x] **查询集成** - fetch_stage_conversation_rounds 实现按阶段查询对话轮次
- [x] **API 高度精简** - 实现了比预期更精简的 6 个核心接口

### 实现说明
实际实现采用了更优雅的设计：
- **阶段管理**: 通过 flow 的 `switch-stage` 接口统一管理，而非独立的阶段创建接口
- **流程完成**: 独立的 `complete` 接口确保流程状态管理的明确性
- **查询优化**: 专用的查询函数处理复杂的跨表查询需求
- **权限一致**: 所有接口都有完整的权限验证和错误处理

---

## API 实现状态总结

### 当前状况
- **实际实现**: 6个 Genesis API 接口
- **原设计预期**: 22个接口 → 5个核心接口
- **实际状态**: 已实现高度精简的架构

### 实现亮点
1. **命令模式集成**: 创建、更新操作通过统一的服务层处理
2. **查询职责分离**: 对话轮次查询通过专用函数 `fetch_stage_conversation_rounds` 处理
3. **流程状态管理**: 支持阶段切换和流程完成的完整生命周期
4. **会话绑定灵活**: 支持创建新会话或绑定现有会话到阶段

### 架构优势
1. **高度精简**: 6个接口覆盖完整功能需求
2. **接口一致**: 所有接口遵循相同的错误处理和响应格式
3. **权限控制**: 完整的小说所有权验证和阶段访问控制
4. **事务安全**: 所有写操作都有完整的事务管理和回滚处理

### 与设计文档对比
- **✅ 流程管理**: 实现了 flows 的创建、查询、阶段切换、完成功能
- **✅ 会话绑定**: 实现了阶段与会话的关联管理
- **✅ 查询分离**: 对话轮次查询通过独立函数处理
- **✅ 命令集成**: 消息发送通过现有 ConversationCommand 处理
- **✅ 权限验证**: 完整的所有权校验机制

