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

### Migration Strategy
- **阶段1**：实现基础SessionManager接口和Redis存储（Day 1-2）
- **阶段2**：添加PostgreSQL持久化层和同步机制（Day 2-3）
- **阶段3**：集成测试和性能优化（Day 3-4）
- **向后兼容**：新系统启动，暂无历史数据迁移需求

### Implementation Details
```python
# 会话数据模型
class DialogueSession(BaseModel):
    session_id: str
    stage: Stage  # 0-5
    round_number: int
    context_tokens: int
    dialogue_history: List[DialogueRound]
    locked_content: Dict[str, Any]
    metadata: SessionMetadata
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

# Redis存储策略
- Key格式: `dialogue:session:{session_id}`
- TTL: 24小时（可配置）
- 序列化: JSON（使用Pydantic的json()方法）

# PostgreSQL schema
CREATE TABLE dialogue_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    project_id UUID NOT NULL,
    stage INTEGER NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

# 同步策略
- 写入时：先写Redis，异步写PostgreSQL
- 读取时：优先Redis，miss时从PostgreSQL加载
- 定期任务：每5分钟同步活跃会话到PostgreSQL
```

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

### Test Strategy
- **单元测试**：SessionManager各方法的独立测试
- **集成测试**：Redis + PostgreSQL完整流程测试
- **性能测试**：使用Locust模拟100并发会话
- **故障测试**：模拟Redis宕机，验证降级和恢复流程

## References
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [PostgreSQL JSONB Performance](https://www.postgresql.org/docs/current/datatype-json.html)
- 现有项目架构文档：`docs/architecture/high-level-architecture.md`

## Changelog
- 2025-09-04: 初始草稿创建