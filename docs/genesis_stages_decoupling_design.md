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

**API 设计（增量）**
- 新增（只读/写）
  - `POST /api/v1/genesis/flows/{novel_id}`（幂等创建或返回当前 flow）
  - `POST /api/v1/genesis/flows/{novel_id}/stages/{stage}`（创建阶段记录：可带 config/迭代策略）
  - `POST /api/v1/genesis/stages/{stage_id}/sessions`（创建并绑定会话，或绑定现有 `session_id`）
  - `GET /api/v1/genesis/stages/{stage_id}/sessions`（列出阶段的所有会话）
  - `GET /api/v1/genesis/flows/{novel_id}`（查看流程进度与阶段摘要）
- 复用
  - 对话消息：`/api/v1/conversations/sessions/{session_id}/rounds/messages|commands`（保持不变）

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

**后续可选增强**
- 增加 `genesis_stage_task_links` 与 `depends_on` 建模任务依赖；
- 为阶段记录增加变更审计表；
- 提供阶段视图的聚合 API（进度、成本、失败率）。

**Definition of Done**
- [ ] Alembic 迁移创建三张表（含索引/约束）
- [ ] 服务层最小实现（ensure_flow/create_stage/add_stage_session/list_stage_sessions）
- [ ] 绑定校验与错误处理（scope 与 novel 归属）
- [ ] 只读查询 API（按阶段列出会话，按小说获取流程）
- [ ] 基本集成测试（创建→绑定→发送消息→按阶段查询）

