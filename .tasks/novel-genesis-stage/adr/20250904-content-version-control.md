---
id: ADR-004-content-version-control
title: 内容版本控制实现方案（修订版草案）
status: Accepted
date: 2025-09-04
decision_makers: [platform-arch, backend-lead]
related_requirements: [FR-007, FR-009, NFR-002, NFR-004]
related_stories: [STORY-007, STORY-009]
supersedes: []
superseded_by: null
tags: [architecture, versioning, data-management, storage]
revision: 2
updated_at: 2025-09-04
---

# 内容版本控制实现方案（修订版草案）

## Status

Accepted

## Context

### Business Context

根据 PRD 的版本管理与分支需求：

- 相关用户故事：
  - STORY-007: 内容审核与调整（需要版本对比）
  - STORY-009: 对话历史回溯（需要完整历史）
- 业务价值：支持创意探索、内容回滚、分支创作，提高创作灵活性
- 业务约束：保留至少 30 天历史；支持分支与合并操作

### Technical Context

基于现有架构：

- 数据面：PostgreSQL（结构化）、MinIO（大文本）、Redis（缓存）、Kafka（事件）
- 约定：事件驱动架构，所有变更产生领域事件
- 集成：知识库、对话管理、内容生成模块

### Requirements Driving This Decision

- FR-007: 版本管理，保留所有版本便于对比
- FR-009: 分支管理，支持从历史节点创建新分支
- NFR-002: 数据持久性 ≥ 99.999%
- NFR-004: 审计追踪，记录所有变更

### Constraints

- 技术：处理 100MB+ 文本（百万字级），合并/冲突可视化
- 业务：并排对比、分支合并
- 成本：控制存储增长与带宽开销

## Decision Drivers

- 存储效率：多版本小说存储成本可控
- 查询性能：快速获取任意版本（含冷链重建）
- 分支管理：Git-like 操作（创建/合并/回滚）
- 合并能力：章节粒度三路合并 + 冲突结构化标注
- 审计：追加只写、不可篡改、可追溯

## Considered Options

### Option 1: Event Sourcing（事件溯源）

- 优点：完整审计、时间旅行、天然契合事件驱动
- 缺点：重建成本高、实现复杂；MVP 交付风险高

### Option 2: 快照 + 增量（推荐）

- 优点：存储与性能平衡；实现适中；兼容现有存储；易做分支
- 缺点：需设计快照策略、链长控制与合并逻辑

### Option 3: Copy-on-Write（写时复制）

- 优点：访问简单、实现直接
- 缺点：存储成本高，重复数据多

### Option 4: 使用 Git 作为后端

- 优点：功能成熟、合并能力强
- 缺点：与 DB/MinIO 集成差；不适合大对象与高并发

## Decision

采用 Option 2：快照 + 增量方案（增强版）

理由：

1. 平衡存储成本与访问性能；支持逐步优化
2. 实现复杂度适中，符合 MVP 时限
3. 与 PostgreSQL/MinIO/Redis/Kafka 兼容良好
4. 原生支持分支/合并/回滚，便于产品演进

## Consequences

### Positive

- 增量存储 + 定期快照，显著降低成本
- 快速访问（最近快照 + 有限链重建）
- 支持 DAG 版本图，合并/回滚更灵活
- 审计可追溯，追加只写

### Negative

- 合并/冲突与链管理策略需精心设计
- 存储/缓存/一致性增加实现复杂度

### Risks 与缓解

- 快照过多导致存储增长 → 时间分桶保留 + 去重 + 冷归档
- 增量链过长影响读性能 → 链长阈值 + 读后物化新快照
- 合并冲突复杂 → 章节粒度三路合并 + 结构化冲突
- 并发写踩踏 → CAS 更新 HEAD + 幂等等幂

## Implementation Plan

### 模块与边界

- 代码位置：
  - 核心：`apps/backend/src/core/versioning/`
  - 存储适配：`apps/backend/src/infrastructure/storage/`
- 组件：
  - `VersionManager`：版本接口（创建/读取/回滚/分支/合并）
  - `SnapshotStore`：快照持久化（MinIO）
  - `DeltaStore`：增量存储（PostgreSQL）
  - `MergeEngine`：三路合并与冲突生成
  - `Optimizer`：快照策略、链折叠、归档

### 数据模型（修订）

```python
from sqlalchemy import (
    Column, String, JSON, DateTime, ForeignKey, Enum, Boolean,
    Integer, BigInteger, LargeBinary, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

class ContentVersion(Base):
    __tablename__ = 'content_versions'

    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey('projects.id'), nullable=False)
    branch_name = Column(String, nullable=False, default='main')
    sequence = Column(BigInteger, nullable=False)  # 分支内单调递增

    version_type = Column(Enum('snapshot', 'delta', 'merge', name='version_type'), nullable=False)
    storage_path = Column(String, nullable=True)  # 快照对象键（仅 snapshot/merge 可能有）
    content_hash = Column(String, nullable=True)  # 快照内容哈希（sha256）
    content_size = Column(BigInteger, nullable=True)  # 未压缩字节数
    compression = Column(String, nullable=True)  # 'zstd' 等

    message = Column(String, default='')
    metadata = Column(JSON, default={})
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(UUID, ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint('project_id', 'branch_name', 'sequence', name='uq_branch_seq'),
        Index('idx_versions_project', 'project_id'),
        Index('idx_versions_branch', 'branch_name'),
        Index('idx_versions_type', 'version_type'),
    )

class ContentVersionParent(Base):
    __tablename__ = 'content_version_parents'

    version_id = Column(UUID, ForeignKey('content_versions.id'), primary_key=True)
    parent_id = Column(UUID, ForeignKey('content_versions.id'), primary_key=True)
    relation = Column(Enum('linear', 'merge', name='parent_relation'), default='linear')
    created_at = Column(DateTime, default=datetime.utcnow)

class ContentDelta(Base):
    __tablename__ = 'content_deltas'

    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey('projects.id'), nullable=False)
    version_id = Column(UUID, ForeignKey('content_versions.id'), nullable=False)

    target_kind = Column(Enum('chapter', 'metadata', name='delta_target_kind'), nullable=False)
    delta_path = Column(String, nullable=False)  # JSON Pointer: /chapters/{id}
    patch_type = Column(Enum('dmp', 'json_patch', 'replace', name='patch_type'), nullable=False)
    patch = Column(LargeBinary, nullable=False)  # 压缩字节（zstd）
    stats = Column(JSON, default={})  # 大小、耗时、文本比例等
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_deltas_version', 'version_id'),
        Index('idx_deltas_project', 'project_id'),
    )

class BranchInfo(Base):
    __tablename__ = 'branches'

    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey('projects.id'), nullable=False)
    name = Column(String, nullable=False)
    head_version_id = Column(UUID, ForeignKey('content_versions.id'), nullable=False)
    base_version_id = Column(UUID, ForeignKey('content_versions.id'), nullable=False)
    status = Column(Enum('active', 'merged', 'abandoned', name='branch_status'), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    merged_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='uq_branch_project_name'),
        Index('idx_branch_project', 'project_id'),
    )
```

要点：

- 移除 `version_number`，改为分支内 `sequence`；版本父子关系改为单独表
  `content_version_parents`，支持多父（合并）。
- `ContentDelta` 采用标准补丁语义：文本用 DMP patch 文本；元数据用 JSON
  Patch（RFC6902）；路径统一 JSON Pointer（RFC6901）。
- 快照记录 `content_hash/size/compression`，便于去重、校验与审计。

### 接口契约（示例）

- 创建版本（增量/快照）：
  - 输入：`project_id`, `branch`, `content`（章节映射与元数据），`message`,
    `create_snapshot?`, `expected_head_version_id?`
  - 语义：若指定
    `expected_head_version_id`，在 HEAD 未变化时才成功（CAS）；否则 409。
- 创建分支：`from_version_id` 复制为分支基线；`head = base = from_version_id`。
- 合并：`source_branch -> target_branch`，找 LCA，执行章节级三路合并；合并提交记录两个父版本。
- 读取版本内容：优先缓存命中；否则从最近快照 + 有限链（≤N）迭代重建；超过阈值触发异步物化快照。

### 核心流程与策略

1. 快照触发（任一满足）：

- 链长阈值：自最近快照起增量数量 ≥ N（默认 10）
- 增量体积阈值：累计 patch 原始大小 ≥ S（默认 5MB）
- 时间阈值：距离最近快照 ≥ T（默认 24h）

2. 增量计算：

- 章节新增/删除/修改均产出 delta；重命名由前端/业务层显式事件表示。
- 文本差异：优先 DMP；当差异比例 >
  P（默认 70%）或 DMP 超时（例如 100ms）时降级为 `replace` 整段替换。
- 元数据差异：生成 JSON Patch；不可表示的复杂变更降级为 `replace`。

3. 读取与链折叠：

- 迭代重建（非递归）：最近快照 → 依次应用后续增量（按 sequence）。
- 若应用增量数 > N/或耗时 >
  L（如 1s），后台任务物化新快照并更新分支 HEAD 的“最近快照指针”。

4. 合并与冲突：

- 以章节为单元进行三路合并（base/source/target）。
- 单方变更直接采用；双方变更时尝试 DMP 文本合并；失败则产出结构化冲突：

```json
{
  "type": "conflict",
  "path": "/chapters/{chapter_id}",
  "base": "...",
  "source": "...",
  "target": "..."
}
```

- 合并提交 `version_type = 'merge'`，`content_version_parents` 记录两个父版本。

5. 并发与幂等：

- 分支 HEAD 更新采用 CAS：
  - SQL 形如
    `UPDATE branches SET head_version_id=? WHERE project_id=? AND name=? AND head_version_id=?`；未命中返回 0 行 →
    409。
- 事件幂等：版本创建/合并事件携带 `event_id`；幂等表去重。

### 存储与压缩

- MinIO 对象命名：`snapshots/{project_id}/{hash[:2]}/{hash}.json.zst`（内容寻址 + 分层目录）。
- 压缩：统一 zstd；记录 `compression` 与未压缩 `content_size`。
- 完整性：计算 `sha256`，读写校验；异常报警。
- 去重：同 `hash` 不重复写入；引用计数或周期性 GC 清理悬挂对象。
- 合规：启用对象版本化与对象锁（WORM/保留策略）以满足审计与持久性要求。

### 缓存策略

- 缓存键：`version:content:{version_id}`。
- 反向索引集合：`version:by_project:{project_id}`（Set）收集所有版本缓存键，以便项目级失效：
  - 失效：读取集合成员并批量 `UNLINK`；或使用 `SCAN` 分页删除。
- 读取热度：对热点版本命中后延长 TTL；冷版本不缓存或短 TTL。

### 事件与主题（Kafka）

- 主题：
  - `content.version.created`
  - `content.branch.created`
  - `content.merge.completed`
- Key：`project_id`（保证项目内有序）
- Envelope：`id`, `ts`, `project_id`, `version_id`, `branch`, `correlation_id`,
  `retries`

### API（草案）

- `POST /projects/{id}/branches`
  - body: `name`, `from_version_id`
- `GET /projects/{id}/branches`
- `POST /projects/{id}/versions`
  - body: `branch`, `content`, `message`, `create_snapshot?`,
    `expected_head_version_id?`
- `GET /versions/{id}`
- `GET /diff?from=...&to=...`
- `POST /merge`（`source_branch`, `target_branch`）
- `POST /revert`（从任意 version 创建回滚提交）

### 参考实现片段（接口为主，省略细节）

```python
class VersionManager:
    async def create_version(self, *, project_id: str, branch: str, content: dict,
                             message: str = '', create_snapshot: bool = False,
                             expected_head_version_id: str | None = None) -> ContentVersion: ...

    async def get_version_content(self, version_id: str, use_cache: bool = True) -> dict: ...

    async def create_branch(self, *, project_id: str, name: str, from_version_id: str) -> BranchInfo: ...

    async def merge(self, *, project_id: str, source_branch: str, target_branch: str) -> ContentVersion: ...

class DeltaBuilder:
    def diff_chapter(self, old: str, new: str) -> tuple[str, bytes, dict]:
        """返回 (patch_type, compressed_patch, stats)；DMP 超时或差异过大时返回 replace。"""

    def diff_metadata(self, old: dict, new: dict) -> tuple[str, bytes, dict]:
        """返回 JSON Patch 或 replace。"""
```

## Storage Optimization（修订）

保留策略：

- 最近 7 天：保留所有快照
- 7–30 天：每日首个快照
- ≥30 天：每周首个快照

实现与约束：

- 不将快照“转换为增量”（避免历史形态改变）。
- 可执行“链重写”：对老链物化新快照，并将后继版本父指向新快照（保留旧版本记录只读，新增重写版本）。
- 冷归档：≥30 天版本移动到冷存储 bucket/ILM 策略；记录
  `is_archived/archived_at`。

## Rollback Plan

- 触发：性能或复杂度风险超预期
- 步骤：
  1. 暂停增量创建；强制快照模式
  2. 使用内容哈希快照 + 压缩去重，保证存储可控
  3. 后台逐步补齐增量管线与合并功能

## Validation

### Alignment 与审查重点

- 架构一致：领域事件、DAG 版本图、追加只写
- 审查：并发 CAS、合并正确性、链长控制、对象命名与校验、缓存失效、幂等等幂

### Metrics（分类型目标）

- 创建：
- 增量提交（≤100KB patch）P95 < 800ms
- 快照提交（≈5MB 内容）P95 < 3s（多段上传）
- 读取：
  - 缓存命中 P95 < 300ms
  - 冷读（链长 ≤ 10）P95 < 2.5s；超阈值触发物化
- 存储：月增长率 < 10%；快照压缩比 > 5:1（文本数据）

### Test Strategy（细化）

- 单元：`apply(patch(diff(a,b)), a) == b`（property-based）；DMP 超时降级
- 集成：版本创建/读取/回滚/分支/合并全链路
- 性能：50k/200k/1M 字符数据集的 diff/merge/读取评测
- 压力：并发创建/合并 + CAS 冲突压测（指数退避）
- 端到端：分支图可视化、冲突交互与解决

## Security & Compliance

- 权限：项目级 ACL；`created_by` 追踪
- 数据加密：MinIO SSE；DB 连接加密
- 审计不可变：版本表禁止 UPDATE/DELETE（仅软删标记）；对象存储启用版本化与对象锁；快照使用内容寻址 + 哈希校验

## Open Questions

- 章节 ID 稳定性与命名约定（是否允许重命名/层级段落）
- 冲突数据结构前后端共享模型与 UI 呈现细节
- JSON Patch/Pointer 的库选择与跨语言一致性
- 冷归档介质与 RTO/RPO 目标；跨区域容灾策略

## References

- diff-match-patch
- Event Sourcing Pattern（Martin Fowler）
- Git Internals（Plumbing and Porcelain）

## Changelog

- 2025-09-04: 初始草案创建
- 2025-09-04: 修订版草案（R2）— 增加多父版本、标准补丁语义、CAS 并发、快照去重与压缩、链长控制、指标与测试细化
