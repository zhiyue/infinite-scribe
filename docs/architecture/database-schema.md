# Database Schema

## PostgreSQL

### 核心设计原则

- **统一事件日志:** `domain_events` 表是整个系统所有业务事实的唯一、不可变来源。
- **状态快照:** 核心业务表（如 `novels`, `chapters`, `genesis_sessions`）存储实体的当前状态快照，用于高效查询，其状态由领域事件驱动更新。
- **可靠的异步通信:** `command_inbox` (幂等性), `event_outbox` (事务性事件发布), 和 `flow_resume_handles` (工作流恢复) 这三张表共同构成了我们健壮的异步通信和编排的基石。
- **混合外键策略:** 在代表核心领域模型的表之间保留数据库级外键约束以保证强一致性。在高吞吐量的日志和追踪类表中，则不使用外键以获得更好的写入性能和灵活性。

### SQL 定义

```sql
-- 自动更新 'updated_at' 字段的函数
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ENUM 类型定义
CREATE TYPE agent_type AS ENUM ('worldsmith', 'plotmaster', 'outliner', 'director', 'character_expert', 'worldbuilder', 'writer', 'critic', 'fact_checker', 'rewriter');
CREATE TYPE novel_status AS ENUM ('GENESIS', 'GENERATING', 'PAUSED', 'COMPLETED', 'FAILED');
CREATE TYPE chapter_status AS ENUM ('DRAFT', 'REVIEWING', 'REVISING', 'PUBLISHED');
CREATE TYPE command_status AS ENUM ('RECEIVED', 'PROCESSING', 'COMPLETED', 'FAILED');
CREATE TYPE task_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE outbox_status AS ENUM ('PENDING', 'SENT');
CREATE TYPE handle_status AS ENUM ('PENDING_PAUSE', 'PAUSED', 'RESUMED', 'EXPIRED');
CREATE TYPE genesis_status AS ENUM ('IN_PROGRESS', 'COMPLETED', 'ABANDONED');
CREATE TYPE genesis_stage AS ENUM ('CONCEPT_SELECTION', 'STORY_CONCEPTION', 'WORLDVIEW', 'CHARACTERS', 'PLOT_OUTLINE', 'FINISHED');

--- 核心业务实体表 ---

CREATE TABLE novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 小说唯一ID
    title VARCHAR(255) NOT NULL, -- 小说标题
    theme TEXT, -- 小说主题
    writing_style TEXT, -- 写作风格
    status novel_status NOT NULL DEFAULT 'GENESIS', -- 当前状态
    target_chapters INTEGER NOT NULL DEFAULT 0, -- 目标章节数
    completed_chapters INTEGER NOT NULL DEFAULT 0, -- 已完成章节数
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 最后更新时间
);
COMMENT ON TABLE novels IS '存储每个独立小说项目的核心元数据。';

CREATE TABLE chapter_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 章节版本的唯一ID
    chapter_id UUID NOT NULL, -- 关联的章节ID (外键后加)
    version_number INTEGER NOT NULL, -- 版本号，从1开始递增
    content_url TEXT NOT NULL, -- 指向Minio中该版本内容的URL
    word_count INTEGER, -- 该版本的字数
    created_by_agent_type agent_type NOT NULL, -- 创建此版本的Agent类型
    change_reason TEXT, -- (可选) 修改原因，如“根据评论家意见修改”
    parent_version_id UUID REFERENCES chapter_versions(id) ON DELETE SET NULL, -- 指向上一个版本的ID，形成版本链
    metadata JSONB, -- 存储与此版本相关的额外元数据
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 版本创建时间
    UNIQUE(chapter_id, version_number)
);
COMMENT ON TABLE chapter_versions IS '存储一个章节的每一次具体内容的迭代版本，实现版本控制。';

CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 章节唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    chapter_number INTEGER NOT NULL, -- 章节序号
    title VARCHAR(255), -- 章节标题
    status chapter_status NOT NULL DEFAULT 'DRAFT', -- 章节当前状态
    published_version_id UUID REFERENCES chapter_versions(id) ON DELETE SET NULL, -- 指向当前已发布版本的ID
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    UNIQUE (novel_id, chapter_number)
);
COMMENT ON TABLE chapters IS '存储章节的元数据，与具体的版本内容分离。';

ALTER TABLE chapter_versions ADD CONSTRAINT fk_chapter_versions_chapter_id FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE;
ALTER TABLE chapters ADD CONSTRAINT check_published_version CHECK (published_version_id IS NULL OR EXISTS (SELECT 1 FROM chapter_versions cv WHERE cv.id = chapters.published_version_id AND cv.chapter_id = chapters.id));

CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 角色唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    name VARCHAR(255) NOT NULL, -- 角色名称
    role VARCHAR(50), -- 角色定位 (如主角, 反派)
    description TEXT, -- 角色外貌、性格等简述
    background_story TEXT, -- 角色背景故事
    personality_traits TEXT[], -- 性格特点列表
    goals TEXT[], -- 角色的主要目标列表
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 最后更新时间
);
COMMENT ON TABLE characters IS '存储小说中所有角色的详细设定信息。';

CREATE TABLE worldview_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 世界观条目唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小শনেরID
    entry_type VARCHAR(50) NOT NULL, -- 条目类型 (如 'LOCATION', 'ORGANIZATION')
    name VARCHAR(255) NOT NULL, -- 条目名称
    description TEXT, -- 详细描述
    tags TEXT[], -- 标签，用于分类和检索
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    UNIQUE (novel_id, name, entry_type)
);
COMMENT ON TABLE worldview_entries IS '存储世界观中的所有设定条目，如地点、组织、物品等。';

CREATE TABLE story_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 故事弧唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    title VARCHAR(255) NOT NULL, -- 故事弧标题
    summary TEXT, -- 故事弧摘要
    start_chapter_number INTEGER, -- 开始章节号
    end_chapter_number INTEGER, -- 结束章节号
    status VARCHAR(50) DEFAULT 'PLANNED', -- 状态 (如 'PLANNED', 'ACTIVE', 'COMPLETED')
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 最后更新时间
);
COMMENT ON TABLE story_arcs IS '存储主要的情节线或故事阶段的规划。';

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 评审记录唯一ID
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE, -- 关联的章节ID
    chapter_version_id UUID NOT NULL REFERENCES chapter_versions(id) ON DELETE CASCADE, -- 评审针对的具体章节版本ID
    agent_type agent_type NOT NULL, -- 执行评审的Agent类型
    review_type VARCHAR(50) NOT NULL, -- 评审类型 (如 'CRITIC', 'FACT_CHECK')
    score NUMERIC(3, 1), -- 评论家评分
    comment TEXT, -- 评论家评语
    is_consistent BOOLEAN, -- 事实核查员判断是否一致
    issues_found TEXT[], -- 事实核查员发现的问题列表
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 评审创建时间
);
COMMENT ON TABLE reviews IS '记录每一次对章节草稿的评审结果。';

--- 状态快照表 ---

CREATE TABLE genesis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 会话的唯一标识符
    novel_id UUID REFERENCES novels(id) ON DELETE SET NULL, -- 流程完成后关联的小说ID
    user_id UUID, -- 关联的用户ID
    status genesis_status NOT NULL DEFAULT 'IN_PROGRESS', -- 整个会话的状态
    current_stage genesis_stage NOT NULL DEFAULT 'CONCEPT_SELECTION', -- 当前所处的业务阶段
    confirmed_data JSONB, -- 存储每个阶段已确认的最终数据
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE genesis_sessions IS '作为创世流程的“状态快照”，用于高效查询当前流程的状态，其状态由领域事件驱动更新。';

--- 核心架构机制表 ---

CREATE TABLE domain_events (
    id BIGSERIAL PRIMARY KEY, -- 使用自增整数，保证事件的严格顺序
    event_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(), -- 事件的全局唯一标识符
    correlation_id UUID, -- 用于追踪一个完整的业务流程或请求链
    causation_id UUID,   -- 指向触发此事件的上一个事件的event_id，形成因果链
    event_type TEXT NOT NULL, -- 事件的唯一类型标识 (e.g., 'genesis.concept.proposed')
    event_version INTEGER NOT NULL DEFAULT 1, -- 事件模型的版本号
    aggregate_type TEXT NOT NULL, -- 聚合根类型 (e.g., 'GENESIS_SESSION', 'NOVEL')
    aggregate_id TEXT NOT NULL,   -- 聚合根的ID
    payload JSONB, -- 事件的具体数据
    metadata JSONB, -- 附加元数据 (如 user_id, source_service)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE domain_events IS '统一的领域事件日志，是整个系统所有业务事实的唯一、不可变来源（Source of Truth）。';

CREATE TABLE command_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 命令的唯一ID
    session_id UUID NOT NULL, -- 关联的会话ID，用于限定作用域
    command_type TEXT NOT NULL, -- 命令类型 (e.g., 'RequestConceptGeneration')
    idempotency_key TEXT NOT NULL, -- 用于防止重复的幂等键
    payload JSONB, -- 命令的参数
    status command_status NOT NULL DEFAULT 'RECEIVED', -- 命令处理状态
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE command_inbox IS '命令收件箱，通过唯一性约束为需要异步处理的命令提供幂等性保证。';
CREATE UNIQUE INDEX idx_command_inbox_unique_pending_command ON command_inbox (session_id, command_type) WHERE status IN ('RECEIVED', 'PROCESSING');


CREATE TABLE async_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 任务的唯一ID
    task_type TEXT NOT NULL, -- 任务类型 (e.g., 'genesis.concept_generation')
    triggered_by_command_id UUID, -- 触发此任务的命令ID
    status task_status NOT NULL DEFAULT 'PENDING', -- 任务执行状态
    progress DECIMAL(5, 2) NOT NULL DEFAULT 0.0, -- 任务进度
    input_data JSONB, -- 任务的输入参数
    result_data JSONB, -- 任务成功后的结果
    error_data JSONB, -- 任务失败时的错误信息
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE async_tasks IS '通用的异步任务表，用于追踪所有后台技术任务（如调用LLM）的执行状态。';

CREATE TABLE event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 发件箱记录ID
    topic TEXT NOT NULL, -- 目标Kafka主题
    key TEXT, -- Kafka消息的Key
    payload JSONB NOT NULL, -- 消息的完整内容
    status outbox_status NOT NULL DEFAULT 'PENDING', -- 消息发送状态
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE event_outbox IS '事务性发件箱，保证数据库写入与向Kafka发布事件之间的原子性。';

CREATE TABLE flow_resume_handles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 句柄记录ID
    correlation_id TEXT NOT NULL, -- 用于查找的关联ID (如task_id, command_id)
    resume_handle JSONB NOT NULL, -- Prefect提供的、用于恢复的完整JSON对象
    status handle_status NOT NULL DEFAULT 'PENDING_PAUSE', -- 回调句柄的状态
    resume_payload JSONB, -- 用于存储提前到达的恢复数据，解决竞态条件
    expires_at TIMESTAMPTZ, -- 过期时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE flow_resume_handles IS '持久化存储Prefect工作流的暂停/恢复句柄，以应对缓存失效，确保系统容错性。';
CREATE UNIQUE INDEX idx_flow_resume_handles_unique_correlation ON flow_resume_handles (correlation_id) WHERE status IN ('PENDING_PAUSE', 'PAUSED');

--- 索引与触发器 ---

-- 性能关键索引
CREATE INDEX idx_domain_events_aggregate ON domain_events(aggregate_type, aggregate_id);
CREATE INDEX idx_async_tasks_status_type ON async_tasks(status, task_type);
CREATE INDEX idx_reviews_chapter_version ON reviews(chapter_id, chapter_version_id);

-- 为所有有 updated_at 的表创建触发器
CREATE TRIGGER set_timestamp_novels BEFORE UPDATE ON novels FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_chapters BEFORE UPDATE ON chapters FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_characters BEFORE UPDATE ON characters FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_worldview_entries BEFORE UPDATE ON worldview_entries FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_story_arcs BEFORE UPDATE ON story_arcs FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_genesis_sessions BEFORE UPDATE ON genesis_sessions FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_async_tasks BEFORE UPDATE ON async_tasks FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_flow_resume_handles BEFORE UPDATE ON flow_resume_handles FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

```

## Neo4j

- **核心原则:** Neo4j用于存储和查询**每个小说项目内部的**知识图谱。它的核心价值在于管理和推理实体之间复杂的、动态演变的关系，这是传统关系型数据库难以高效处理的。
  - **关联性:** 所有Neo4j中的核心节点都应有一个 `app_id` 属性，其值对应其在PostgreSQL中对应表的主键ID，以便于跨数据库关联和数据补充。
  - **数据职责:** PostgreSQL负责存储实体的核心“属性”和“版本化内容”，而Neo4j专注于存储这些实体之间的“关系”、“上下文”和“随时间演变的互动状态”。
  - **范围隔离:** 所有图数据都必须通过关系连接到唯一的 `:Novel` 节点，确保每个小说的知识图谱是完全隔离的。

- **节点标签 (Node Labels) - 示例:**
  - `:Novel` (属性: `app_id: string` (来自PG `novels.id`), `title: string`) - 图谱的根节点。
  - `:Chapter` (属性: `app_id: string` (来自PG `chapters.id`), `chapter_number: integer`, `title: string`) - 章节的元数据节点。
  - `:ChapterVersion` (属性: `app_id: string` (来自PG `chapter_versions.id`), `version_number: integer`, `created_by_agent_type: string`) - 代表一个具体的章节版本，是大多数事件和互动的关联点。
  - `:Character` (属性: `app_id: string` (来自PG `characters.id`), `name: string`, `role: string`) - 角色节点。
  - `:WorldviewEntry` (属性: `app_id: string` (来自PG `worldview_entries.id`), `name: string`, `entry_type: string`) - 世界观实体，如地点、组织、物品等。
  - `:StoryArc` (属性: `app_id: string` (来自PG `story_arcs.id`), `title: string`, `status: string`) - 故事弧线节点。
  - `:Outline` (属性: `app_id: string` (来自PG `outlines.id`), `version: integer`) - 大纲节点。
  - `:SceneCard` (属性: `app_id: string` (来自PG `scene_cards.id`), `scene_number: integer`) - 场景卡节点。
  - `:Interaction` (属性: `app_id: string` (来自PG `character_interactions.id`), `interaction_type: string`) - 具体的互动事件节点，如对话。
  - `:Review` (属性: `app_id: string` (来自PG `reviews.id`), `agent_type: string`, `score: float`, `is_consistent: boolean`) - 评审结果节点。
  - `:PlotPoint` (属性: `description: string`, `significance: float`) - (可选) 用于更细致的情节跟踪，可能没有直接的PG对应。

- **关系类型 (Relationship Types) - 示例 (所有关系都应隐含地属于某个Novel的上下文):**
  - **结构性关系 (Structural Relationships):**
    - `(:Chapter)-[:BELONGS_TO_NOVEL]->(:Novel)`
    - `(:Character)-[:APPEARS_IN_NOVEL]->(:Novel)`
    - `(:WorldviewEntry)-[:PART_OF_WORLDVIEW]->(:Novel)`
    - `(:StoryArc)-[:PART_OF_PLOT]->(:Novel)`
    - `(:ChapterVersion)-[:VERSION_OF]->(:Chapter)`
    - `(:Outline)-[:OUTLINE_FOR]->(:ChapterVersion)`
    - `(:SceneCard)-[:SCENE_IN]->(:Outline)`
    - `(:Interaction)-[:INTERACTION_IN]->(:SceneCard)`
    - `(:Review)-[:REVIEWS]->(:ChapterVersion)`
  - **时序与因果关系 (Temporal & Causal Relationships):**
    - `(:Chapter)-[:PRECEDES {order: 1}]->(:Chapter {order: 2})`
    - `(:StoryArc)-[:PRECEDES_ARC]->(:StoryArc)`
    - `(:WorldviewEntry {entry_type: 'EVENT'})-[:LEADS_TO_EVENT]->(:WorldviewEntry {entry_type: 'EVENT'})`
    - `(:PlotPoint)-[:CAUSES]->(:PlotPoint)`
  - **角色关系 (Character Relationships):**
    - `(:Character)-[:HAS_RELATIONSHIP {type: 'FRIENDLY', strength: 0.9, since_chapter: 5}]->(:Character)`
    - `(:Character)-[:HAS_RELATIONSHIP {type: 'HOSTILE', reason: 'Betrayal'}]->(:Character)`
    - `(:Character)-[:MEMBER_OF]->(:WorldviewEntry {entry_type:'ORGANIZATION'})`
    - `(:Character)-[:HAS_GOAL]->(:PlotPoint)`
  - **互动与事件关系 (Interaction & Event Relationships):**
    - `(:ChapterVersion)-[:FEATURES_CHARACTER]->(:Character)`
    - `(:ChapterVersion)-[:TAKES_PLACE_IN]->(:WorldviewEntry {entry_type:'LOCATION'})`
    - `(:Interaction)-[:INVOLVES]->(:Character)`
    - `(:Character)-[:USED_ITEM_IN {chapter_version_id: '...'}]->(:WorldviewEntry {entry_type:'ITEM'})`
    - `(:ChapterVersion)-[:ADVANCES_ARC]->(:StoryArc)`
    - `(:ChapterVersion)-[:REVEALS_INFO_ABOUT]->(:WorldviewEntry)`

- **Cypher 查询示例 (展示图数据库的威力):**
  - **简单查询 (角色出场章节):**
    ```cypher
    MATCH (c:Character {name: '艾拉'})<-[:FEATURES_CHARACTER]-(cv:ChapterVersion)-[:VERSION_OF]->(chap:Chapter)
    WHERE (chap)-[:BELONGS_TO_NOVEL]->(:Novel {app_id: '指定小说ID'})
    RETURN chap.chapter_number, chap.title
    ORDER BY chap.chapter_number;
    ```
  - **中等查询 (复杂关系查找):** 找出在“暗影森林”中出现过，并且是“光明教会”敌人的所有角色。
    ```cypher
    MATCH (c:Character)-[:APPEARS_IN_NOVEL]->(:Novel {app_id: '指定小说ID'}),
          (c)-[:TAKES_PLACE_IN]->(:WorldviewEntry {name: '暗影森林'}),
          (c)-[:HAS_RELATIONSHIP {type: 'HOSTILE'}]->(:WorldviewEntry {name: '光明教会', entry_type: 'ORGANIZATION'})
    RETURN c.name, c.role;
    ```
  - **复杂查询 (事实一致性检查):** 检查角色“艾拉”在第5章的版本中，是否既有在“北境”的互动，又有在“南都”的互动（逻辑矛盾）。
    ```cypher
    MATCH (cv:ChapterVersion)-[:VERSION_OF]->(:Chapter {chapter_number: 5}),
          (cv)-[:BELONGS_TO_NOVEL]->(:Novel {app_id: '指定小说ID'})
    MATCH (cv)-[:FEATURES_CHARACTER]->(c:Character {name: '艾拉'})
    MATCH (c)<-[:INVOLVES]-(:Interaction)-[:INTERACTION_IN]->(:SceneCard)-[:SCENE_IN]->(:Outline)-[:OUTLINE_FOR]->(cv),
          (interaction_location:WorldviewEntry {entry_type: 'LOCATION'})<-[:TAKES_PLACE_IN]-(cv)
    WITH interaction_location.name AS location_name
    RETURN count(DISTINCT location_name) > 1 AS has_contradiction, collect(DISTINCT location_name) AS locations;
    ```

- **索引策略 (Indexing Strategy):**
  - 为了保证查询性能，必须为节点上频繁用于查找的属性创建索引。
  - **必须创建的索引:**
    - `CREATE INDEX novel_app_id FOR (n:Novel) ON (n.app_id);`
    - `CREATE INDEX chapter_app_id FOR (c:Chapter) ON (c.app_id);`
    - `CREATE INDEX character_app_id FOR (c:Character) ON (c.app_id);`
    - `CREATE INDEX worldview_app_id FOR (w:WorldviewEntry) ON (w.app_id);`
  - **推荐创建的索引:**
    - `CREATE INDEX character_name FOR (c:Character) ON (c.name);`
    - `CREATE INDEX worldview_name_type FOR (w:WorldviewEntry) ON (w.name, w.entry_type);`

- **数据同步策略 (Data Synchronization Strategy):**
  - **挑战:** 保持PostgreSQL（作为事实来源 Source of Truth）和Neo4j（作为关系视图）之间的数据同步至关重要。
  - **方案1 (双写模式 - MVP适用):** 应用层的服务在完成一个业务逻辑时，同时向PostgreSQL和Neo4j进行写入。例如，创建一个新角色时，服务先在PG中插入记录，成功后获取ID，再在Neo4j中创建对应的节点。
    - **优点:** 实现简单直接。
    - **缺点:** 缺乏事务保证，可能导致数据不一致（例如PG写入成功，Neo4j写入失败）。
  - **方案2 (事件驱动的CDC模式 - 长期推荐):**
    1.  所有数据变更只写入PostgreSQL。
    2.  使用变更数据捕获（Change Data Capture, CDC）工具（如 Debezium）监控PostgreSQL的预写日志（WAL）。
    3.  Debezium将数据变更（INSERT, UPDATE, DELETE）作为事件发布到Kafka。
    4.  创建一个专门的“图同步服务（Graph Sync Service）”，订阅这些Kafka事件。
    5.  该服务根据接收到的事件，在Neo4j中创建、更新或删除相应的节点和关系。
    - **优点:** 高度解耦、可靠、可扩展，保证最终一致性。
    - **缺点:** 架构更复杂，需要引入额外的组件。

## WorldviewEntry 的关系模型详解

`WorldviewEntry` 是知识图谱中最多样化的节点，代表了世界观中的所有非角色实体，如地点、组织、物品、概念等。因此，它拥有最丰富的关系类型，用于构建一个逻辑严密、细节丰富的虚拟世界。

以下是 `WorldviewEntry` 节点作为关系起点或终点的详细关系类型列表：

### 1. 结构性与层级关系 (Structural & Hierarchical)

这些关系定义了世界观条目之间的基本结构和归属。

- **`(:WorldviewEntry)-[:PART_OF_WORLDVIEW]->(:Novel)`**
  - **含义:** 声明一个世界观条目属于某部小说的世界观。这是所有世界观条目的根关系。
  - **示例:** `(:WorldviewEntry {name: '霍格沃茨'})-[:PART_OF_WORLDVIEW]->(:Novel {title: '哈利·波特'})`

- **`(:WorldviewEntry)-[:CONTAINS]->(:WorldviewEntry)`**
  - **含义:** 表示一个实体在物理上或概念上包含另一个实体。常用于地点、组织等。
  - **示例 (地点):** `(:WorldviewEntry {name: '英国', entry_type: 'LOCATION'})-[:CONTAINS]->(:WorldviewEntry {name: '伦敦', entry_type: 'LOCATION'})`
  - **示例 (组织):** `(:WorldviewEntry {name: '魔法部', entry_type: 'ORGANIZATION'})-[:CONTAINS]->(:WorldviewEntry {name: '傲罗办公室', entry_type: 'ORGANIZATION'})`

- **`(:WorldviewEntry)-[:DERIVED_FROM]->(:WorldviewEntry)`**
  - **含义:** 表示一个概念、技术或律法源自于另一个。
  - **示例:** `(:WorldviewEntry {name: '曲速引擎', entry_type: 'TECHNOLOGY'})-[:DERIVED_FROM]->(:WorldviewEntry {name: '空间折叠理论', entry_type: 'CONCEPT'})`

### 2. 实体间交互关系 (Inter-Entity Interactions)

这些关系描述了不同世界观条目之间的动态或静态互动。

- **`(:WorldviewEntry)-[:HOSTILE_TO | ALLIED_WITH | NEUTRAL_TO]->(:WorldviewEntry)`**
  - **含义:** 定义组织、国家等实体之间的阵营关系。
  - **属性示例:** `{ since_year: 1941, reason: "Territorial dispute" }`
  - **示例:** `(:WorldviewEntry {name: '光明教会'})-[:HOSTILE_TO]->(:WorldviewEntry {name: '暗影兄弟会'})`

- **`(:WorldviewEntry)-[:REQUIRES]->(:WorldviewEntry)`**
  - **含义:** 表示一个技术、物品或事件的发生需要另一个物品、技术或概念作为前提。
  - **示例:** `(:WorldviewEntry {name: '传送法术', entry_type: 'TECHNOLOGY'})-[:REQUIRES]->(:WorldviewEntry {name: '魔力水晶', entry_type: 'ITEM'})`

- **`(:WorldviewEntry)-[:PRODUCES | YIELDS]->(:WorldviewEntry)`**
  - **含义:** 表示一个地点、组织或技术能够产出某种物品或资源。
  - **示例:** `(:WorldviewEntry {name: '矮人矿山', entry_type: 'LOCATION'})-[:PRODUCES]->(:WorldviewEntry {name: '秘银', entry_type: 'ITEM'})`

- **`(:WorldviewEntry)-[:GOVERNED_BY]->(:WorldviewEntry)`**
  - **含义:** 表示一个地点或组织受到某个律法或另一个组织的管辖。
  - **示例:** `(:WorldviewEntry {name: '对角巷', entry_type: 'LOCATION'})-[:GOVERNED_BY]->(:WorldviewEntry {name: '魔法不滥用法', entry_type: 'LAW'})`

### 3. 与角色（Character）的交互关系

这些关系将非生命实体与角色紧密联系起来。

- **`(:Character)-[:MEMBER_OF | LEADS | FOUNDED]->(:WorldviewEntry {entry_type: 'ORGANIZATION'})`**
  - **含义:** 定义角色与组织之间的关系。
  - **属性示例:** `{ rank: 'Captain', join_chapter: 3 }`
  - **示例:** `(:Character {name: '阿拉贡'})-[:MEMBER_OF]->(:WorldviewEntry {name: '护戒远征队'})`

- **`(:Character)-[:RESIDES_IN | BORN_IN | DIED_IN]->(:WorldviewEntry {entry_type: 'LOCATION'})`**
  - **含义:** 定义角色的关键生命事件发生的地点。
  - **属性示例:** `{ start_year: 20, end_year: 35, duration_description: "青年时期" }`
  - **示例:** `(:Character {name: '弗罗多'})-[:RESIDES_IN]->(:WorldviewEntry {name: '夏尔'})`

- **`(:Character)-[:POSSESSES | OWNS]->(:WorldviewEntry {entry_type: 'ITEM'})`**
  - **含义:** 表示角色拥有某个特定物品。
  - **属性示例:** `{ acquisition_method: "Inherited", acquisition_chapter: 1 }`
  - **示例:** `(:Character {name: '哈利'})-[:POSSESSES]->(:WorldviewEntry {name: '隐形斗篷'})`

- **`(:Character)-[:USED_ITEM_IN {chapter_version_id: '...'}]->(:WorldviewEntry {entry_type: 'ITEM'})`**
  - **含义:** 记录角色在特定章节版本中使用过某个物品。这是一个事件性关系。
  - **示例:** `(:Character {name: '赫敏'})-[:USED_ITEM_IN {chapter_version_id: '...'}]->(:WorldviewEntry {name: '时间转换器'})`

- **`(:Character)-[:BELIEVES_IN]->(:WorldviewEntry {entry_type: 'CONCEPT'})`**
  - **含义:** 表示角色的信仰或所遵循的理念。
  - **示例:** `(:Character {name: '奈德·史塔克'})-[:BELIEVES_IN]->(:WorldviewEntry {name: '荣誉高于一切'})`

### 4. 与章节版本（ChapterVersion）的叙事关系

这些关系将世界观实体嵌入到具体的故事叙述中。

- **`(:ChapterVersion)-[:TAKES_PLACE_IN]->(:WorldviewEntry {entry_type: 'LOCATION'})`**
  - **含义:** 表明某个章节版本的主要故事发生在某个地点。
  - **示例:** `(:ChapterVersion {version_number: 1, chapter_id: '...' })-[:TAKES_PLACE_IN]->(:WorldviewEntry {name: '禁林'})`

- **`(:ChapterVersion)-[:MENTIONS]->(:WorldviewEntry)`**
  - **含义:** 表示某个章节版本中提到了一个世界观条目，但故事不一定发生在那里。用于追踪信息的分布。
  - **示例:** `(:ChapterVersion { ... })-[:MENTIONS]->(:WorldviewEntry {name: '瓦雷利亚'})`

- **`(:ChapterVersion)-[:REVEALS_INFO_ABOUT]->(:WorldviewEntry)`**
  - **含义:** 表示某个章节版本揭示了关于某个世界观条目的关键信息或背景故事。
  - **属性示例:** `{ info_summary: "揭示了魂器的制作方法" }`
  - **示例:** `(:ChapterVersion { ... })-[:REVEALS_INFO_ABOUT]->(:WorldviewEntry {name: '魂器', entry_type: 'CONCEPT'})`

- **`(:ChapterVersion)-[:AFFECTS_STATUS_OF]->(:WorldviewEntry)`**
  - **含义:** 表示某个章节版本的事件改变了一个世界观实体的状态。
  - **属性示例:** `{ change_description: "从繁荣变为废墟" }`
  - **示例:** `(:ChapterVersion { ... })-[:AFFECTS_STATUS_OF]->(:WorldviewEntry {name: '临冬城', entry_type: 'LOCATION'})`

通过这些丰富的关系，Neo4j能够构建一个动态、互联的世界观知识库，为 `FactCheckerAgent` 提供强大的事实核查依据，也为 `PlotMasterAgent` 和 `OutlinerAgent` 在规划后续情节时提供无限的灵感和素材。
