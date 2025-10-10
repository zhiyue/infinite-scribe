# Data Models

以下是本系统的核心数据模型定义。前端类型定义在 `apps/frontend/src/types/` 中，后端模型在 `apps/backend/src/models/` 中实现。属性主要存储在PostgreSQL，**特定于项目的知识图谱关系主要存储在Neo4j**。

### Neo4j 版本与约定（统一）
- 版本与插件：Neo4j 5.x，启用 `apoc`、`graph-data-science` 插件（见 `deploy/docker-compose.yml`）。
- 节点ID映射：
  - `novel_id`：存在于 `:Novel` 节点上，唯一标识小说（即PG `novels.id`）。
  - `app_id`：存在于除 `:Novel` 外的各类节点上，指向其在PostgreSQL中的主键ID（如 `chapters.id`、`characters.id` 等）。
  - `novel_id`（推荐）：为提升查询性能与范围隔离，建议在所有核心节点上冗余 `novel_id` 字段（并创建索引），用于快速按小说范围过滤。
- 查询规范：所有 Cypher 查询必须显式绑定到某个 `novel_id` 的范围（参考 `docs/architecture/coding-standards.md` 第9条）。
- 语法：索引与约束采用 Neo4j 5.x 语法（`IF NOT EXISTS`、`REQUIRE ... IS UNIQUE`）。

## AgentActivity (活动日志) - PostgreSQL

*   **目的:** 记录系统中由智能体执行的每一个有意义的事件或操作。
*   **TypeScript 接口 (对应PG表):**
    ```typescript
    interface AgentActivity {
      id: string; // 活动的唯一标识符 (UUID)
      workflow_run_id?: string; // 关联的工作流运行ID (UUID)
      novel_id: string; // 关联的小说ID (UUID)
      target_entity_id?: string; // 活动所针对的目标实体的ID (如 chapter_id, character_id)
      target_entity_type?: string; // 目标实体的类型 (如 'CHAPTER', 'CHARACTER')
      agent_type?: 'worldsmith' | 'plotmaster' | 'outliner' | 'director' | 'character_expert' | 'worldbuilder' | 'writer' | 'critic' | 'fact_checker' | 'rewriter'; // 执行活动的Agent类型
      activity_type: string; // 活动的具体类型 (如 'CREATE', 'UPDATE', 'GENERATE_OUTLINE')
      status: 'STARTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'RETRYING'; // 活动的当前状态
      input_data?: any; // 活动的输入数据 (JSONB)
      output_data?: any; // 活动的输出数据 (JSONB)
      error_details?: any; // 如果失败，记录错误详情 (JSONB)
      started_at: Date; // 活动开始时间
      completed_at?: Date; // 活动完成时间
      duration_seconds?: number; // 活动持续时间（秒），由数据库自动计算
      llm_tokens_used?: number; // 本次活动消耗的LLM Token数量
      llm_cost_estimate?: number; // 本次活动估算的LLM成本
      retry_count: number; // 活动重试次数
    }
    ```

## Novel (小说) - PostgreSQL & Neo4j Node :Novel

*   **目的:** 代表一个独立的小说项目，是所有其他数据的根实体。
*   **TypeScript 接口 (属性部分，对应PG表):**
    ```typescript
    interface Novel {
      id: string; // 小说的唯一标识符 (UUID), 主键
      title: string; // 小说标题
      theme: string; // 小说主题
      writing_style: string; // 写作风格描述
      status: 'GENESIS' | 'GENERATING' | 'PAUSED' | 'COMPLETED' | 'FAILED'; // 小说的当前状态
      target_chapters: number; // 目标总章节数
      completed_chapters: number; // 已完成章节数
      version: number; // 版本号，用于乐观锁控制并发更新
      created_by_agent_type?: string; // 创建此小说的Agent类型 (通常是 'worldsmith')
      updated_by_agent_type?: string; // 最后更新此小说元数据的Agent类型
      created_at: Date; // 创建时间
      updated_at: Date; // 最后更新时间
    }
    ```
*   **Neo4j Node `:Novel` 核心属性:** `novel_id: string` (对应PG的 `novels.id`，唯一), `title: string`。

## Chapter (章节) - PostgreSQL & Neo4j Node :Chapter

*   **目的:** 代表小说中的一个独立章节的元数据。实际内容存储在 `chapter_versions` 表中。
*   **TypeScript 接口 (属性部分，对应PG表):**
    ```typescript
    interface Chapter {
      id: string; // 章节的唯一标识符 (UUID), 主键
      novel_id: string; // 所属小说的ID (UUID), 外键
      chapter_number: number; // 章节序号
      title: string; // 章节标题
      status: 'DRAFT' | 'REVIEWING' | 'REVISING' | 'PUBLISHED'; // 章节的当前状态
      published_version_id?: string; // 指向当前已发布版本的ID (来自 chapter_versions 表)
      version: number; // 版本号，用于乐观锁
      created_by_agent_type?: string; // 创建此章节记录的Agent类型
      updated_by_agent_type?: string; // 最后更新此章节元数据的Agent类型
      created_at: Date; // 创建时间
      updated_at: Date; // 最后更新时间
    }
    ```
*   **Neo4j Node `:Chapter` 核心属性:** `app_id: string` (对应PG的 `chapters.id`), `novel_id: string`, `chapter_number: integer`, `title: string`。
*   **Neo4j关系示例:** `(:Chapter {app_id: 'chapter_uuid'})-[:BELONGS_TO_NOVEL]->(:Novel {novel_id: 'novel_uuid'})`

## ChapterVersion (章节版本) - PostgreSQL

*   **目的:** 存储一个章节的每一次具体内容的迭代版本。
*   **TypeScript 接口 (对应PG表):**
    ```typescript
    interface ChapterVersion {
      id: string; // 章节版本的唯一标识符 (UUID), 主键
      chapter_id: string; // 所属章节的ID (UUID), 外键
      version_number: number; // 版本号
      content_url: string; // 指向Minio中存储的该版本章节文本内容的URL
      word_count?: number; // 该版本的字数
      created_by_agent_type: string; // 创建此版本的Agent类型 (如 'writer', 'rewriter')
      change_reason?: string; // (可选) 修改原因，如“根据评论家意见修改”
      parent_version_id?: string; // (可选) 指向上一个版本的ID，形成版本链
      metadata?: any; // (可选) 与此版本相关的其他元数据 (JSONB)
      created_at: Date; // 创建时间
    }
    ```

## GenesisSession (创世会话) - PostgreSQL

*   **目的:** 作为创世流程的“状态快照”，用于高效查询当前流程的状态。它的状态由`domain_events`驱动更新。
*   **TypeScript 接口:**
    ```typescript
    interface GenesisSession {
      id: string; // UUID, 会话的唯一标识符
      novel_id?: string; // UUID, 流程完成后关联的小说ID
      user_id?: string; // UUID, 关联的用户
      status: 'IN_PROGRESS' | 'COMPLETED' | 'ABANDONED'; // 整个会话的状态
      current_stage: 'CONCEPT_SELECTION' | 'STORY_CONCEPTION' | 'WORLDVIEW' | 'CHARACTERS' | 'PLOT_OUTLINE' | 'FINISHED'; // 当前所处的业务阶段
      confirmed_data: any; // JSONB, 存储每个阶段已确认的最终数据
      created_at: Date;
      updated_at: Date;
    }
    ```

## Character (角色) - PostgreSQL & Neo4j Node :Character

*   **目的:** 代表小说中的一个角色，包含其所有核心设定。
*   **TypeScript 接口 (属性部分，对应PG表):**
    ```typescript
    interface Character {
      id: string; // 角色的唯一标识符 (UUID), 主键
      novel_id: string; // 所属小说的ID (UUID), 外键
      name: string; // 角色名称
      role: 'PROTAGONIST' | 'ANTAGONIST' | 'ALLY' | 'SUPPORTING'; // 角色定位
      description: string; // 外貌、性格等简述
      background_story: string; // 背景故事
      personality_traits: string[]; // 性格特点列表
      goals: string[]; // 角色的主要目标列表
      version: number; // 版本号，用于乐观锁
      created_by_agent_type?: string; // 创建此角色的Agent类型
      updated_by_agent_type?: string; // 最后更新此角色的Agent类型
      created_at: Date; // 创建时间
      updated_at: Date; // 最后更新时间
    }
    ```
*   **Neo4j Node `:Character` 核心属性:** `app_id: string` (对应PG的 `characters.id`), `name: string`, `role: string`。
*   **Neo4j关系示例:** `(:Character {app_id: 'char1_uuid'})-[:APPEARS_IN_NOVEL]->(:Novel {app_id: 'novel_uuid'})`, `(:Character {app_id: 'char1_uuid'})-[:INTERACTS_WITH {type: "FRIENDSHIP", in_chapter: 5}]->(:Character {app_id: 'char2_uuid'})`

## WorldviewEntry (世界观条目) - PostgreSQL & Neo4j Node :WorldviewEntry

*   **目的:** 代表世界观中的一个独立设定条目（如地点、组织、物品、概念等）。
*   **TypeScript 接口 (属性部分，对应PG表):**
    ```typescript
    interface WorldviewEntry {
      id: string; // 世界观条目的唯一标识符 (UUID), 主键
      novel_id: string; // 所属小说的ID (UUID), 外键
      entry_type: 'LOCATION' | 'ORGANIZATION' | 'TECHNOLOGY' | 'LAW' | 'CONCEPT' | 'EVENT' | 'ITEM'; // 条目类型
      name: string; // 条目名称
      description: string; // 详细描述
      tags?: string[]; // 标签，用于分类和检索
      version: number; // 版本号，用于乐观锁
      created_by_agent_type?: string; // 创建此条目的Agent类型
      updated_by_agent_type?: string; // 最后更新此条目的Agent类型
      created_at: Date; // 创建时间
      updated_at: Date; // 最后更新时间
    }
    ```
*   **Neo4j Node `:WorldviewEntry` 核心属性:** `app_id: string` (对应PG的 `worldview_entries.id`), `name: string`, `entry_type: string`。
*   **Neo4j关系示例:** `(:WorldviewEntry {name:'Kyoto'})-[:PART_OF_NOVEL_WORLDVIEW]->(:Novel)`, `(:Character)-[:RESIDES_IN]->(:WorldviewEntry {name:'Kyoto'})`

## Review (评审) - PostgreSQL

*   **目的:** 记录一次对章节草稿的评审结果。
*   **TypeScript 接口 (对应PG表):**
    ```typescript
    interface Review {
      id: string; // 评审记录的唯一标识符 (UUID)
      chapter_id: string; // 所属章节的ID (UUID), 外键
      chapter_version_id: string; // 评审针对的具体章节版本的ID (UUID), 外键
      workflow_run_id?: string; // 关联的工作流运行ID (UUID)
      agent_type: string; // 执行评审的Agent类型 (如 'critic', 'fact_checker')
      review_type: 'CRITIC' | 'FACT_CHECK'; // 评审类型
      score?: number; // 评论家评分 (可选)
      comment?: string; // 评论家评语 (可选)
      is_consistent?: boolean; // 事实核查员判断是否一致 (可选)
      issues_found?: string[]; // 事实核查员发现的问题列表 (可选)
      created_at: Date; // 创建时间
    }
    ```

## StoryArc (故事弧) - PostgreSQL & Neo4j Node :StoryArc

*   **目的:** 代表一个主要的情节线或故事阶段。
*   **TypeScript 接口 (属性部分，对应PG表):**
    ```typescript
    interface StoryArc {
      id: string; // 故事弧的唯一标识符 (UUID), 主键
      novel_id: string; // 所属小说的ID (UUID), 外键
      title: string; // 故事弧标题
      summary: string; // 故事弧摘要
      start_chapter_number?: number; // 开始章节号
      end_chapter_number?: number; // 结束章节号
      status: 'PLANNED' | 'ACTIVE' | 'COMPLETED'; // 故事弧状态
      version: number; // 版本号，用于乐观锁
      created_by_agent_type?: string; // 创建此故事弧的Agent类型
      updated_by_agent_type?: string; // 最后更新此故事弧的Agent类型
      created_at: Date; // 创建时间
      updated_at: Date; // 最后更新时间
    }
    ```
*   **Neo4j Node `:StoryArc` 核心属性:** `app_id: string` (对应PG的 `story_arcs.id`), `novel_id: string`, `title: string`。
*   **Neo4j关系示例:** `(:StoryArc)-[:PART_OF_NOVEL_PLOT]->(:Novel)`, `(:StoryArc)-[:PRECEDES_ARC]->(:StoryArc)`

## Neo4j 关系模型概念

Neo4j将用于存储**每个小说项目内部**的实体间的复杂关系，例如：
*   **角色间关系:** `(:Character)-[:KNOWS {strength: 0.8, sentiment: "positive"}]->(:Character)`
*   **角色与地点:** `(:Character)-[:LOCATED_IN {start_chapter: 1, end_chapter: 5, duration_description: "童年时期"}]->(:WorldviewEntry {entry_type: "LOCATION"})`
*   **事件顺序:** `(:WorldviewEntry {entry_type: "EVENT", name: "大灾变"})-[:PRECEDES_EVENT]->(:WorldviewEntry {entry_type: "EVENT", name: "重建期"})`
*   **章节与实体关联:**
    *   `(:Chapter)-[:FEATURES_CHARACTER {role_in_chapter: "POV"}]->(:Character)`
    *   `(:Chapter)-[:MENTIONS_LOCATION]->(:WorldviewEntry {entry_type: "LOCATION"})`
    *   `(:Chapter)-[:DEVELOPS_ARC]->(:StoryArc)`
*   **世界观条目间关系:**
    *   `(:WorldviewEntry {entry_type:"ORGANIZATION", name:"光明教会"})-[:HOSTILE_TO]->(:WorldviewEntry {entry_type:"ORGANIZATION", name:"暗影兄弟会"})`
    *   `(:WorldviewEntry {entry_type:"TECHNOLOGY", name:"曲速引擎"})-[:REQUIRES_MATERIAL]->(:WorldviewEntry {entry_type:"ITEM", name:"零点水晶"})`

---

## Neo4j 更新与对齐说明（与 ADR-005 同步）

为与知识图谱ADR（混合模型：层级+网状）与当前代码基线对齐，补充如下规范：

- 统一版本与插件：Neo4j 5.x；已启用 `apoc`、`graph-data-science`。
- 节点ID映射：
  - `:Novel` 节点使用 `novel_id`（唯一，对应PG `novels.id`）。
  - 其他节点使用 `app_id`（对应各PG表主键）；推荐冗余 `novel_id` 便于范围过滤与索引。
- 关系与标签建议：
  - 角色关系统一为 `:RELATES_TO {kind, strength, since_chapter}` 或采用多关系类型（如 `:FRIEND_OF` 等），务必固定一套标准以便查询与索引。
  - 世界观条目优先采用子标签：`WorldviewEntry:Location`、`WorldviewEntry:Organization`、`WorldviewEntry:Event` 等，避免完全依赖 `entry_type` 字段。
  - 场景与事件：引入 `:Scene` 与 `:Event` 节点；`(:Scene)-[:TAKES_PLACE_AT]->(:WorldviewEntry:Location)`，`(:Character)-[:PARTICIPATES_IN]->(:Scene)`；`(:Event)-[:HAPPENS_IN]->(:Scene)`，`(:Event)-[:TRIGGERS]->(:Event)`，`(:Event)-[:AFFECTS]->(:Character)`。

### 查询必须绑定 novel_id（示例）
```cypher
MATCH (n:Novel {novel_id: $novel_id})
MATCH (c:Character {name: $name})<-[:FEATURES_CHARACTER]-(cv:ChapterVersion)-[:VERSION_OF]->(chap:Chapter)-[:BELONGS_TO_NOVEL]->(n)
RETURN chap.chapter_number, chap.title
ORDER BY chap.chapter_number;
```

### 索引与约束（Neo4j 5.x 语法）
```cypher
// 唯一性约束
CREATE CONSTRAINT unique_novel_id IF NOT EXISTS FOR (n:Novel) REQUIRE n.novel_id IS UNIQUE;
CREATE CONSTRAINT unique_chapter_app_id IF NOT EXISTS FOR (c:Chapter) REQUIRE c.app_id IS UNIQUE;
CREATE CONSTRAINT unique_character_app_id IF NOT EXISTS FOR (c:Character) REQUIRE c.app_id IS UNIQUE;
CREATE CONSTRAINT unique_worldview_app_id IF NOT EXISTS FOR (w:WorldviewEntry) REQUIRE w.app_id IS UNIQUE;
CREATE CONSTRAINT unique_storyarc_app_id IF NOT EXISTS FOR (s:StoryArc) REQUIRE s.app_id IS UNIQUE;

// 推荐：范围隔离索引（基于 novel_id）
CREATE INDEX chapter_novel_id IF NOT EXISTS FOR (c:Chapter) ON (c.novel_id);
CREATE INDEX character_novel_id IF NOT EXISTS FOR (c:Character) ON (c.novel_id);
CREATE INDEX worldview_novel_id IF NOT EXISTS FOR (w:WorldviewEntry) ON (w.novel_id);
CREATE INDEX storyarc_novel_id IF NOT EXISTS FOR (s:StoryArc) ON (s.novel_id);

// 常用属性索引
CREATE INDEX character_name IF NOT EXISTS FOR (c:Character) ON (c.name);
CREATE INDEX worldview_name_type IF NOT EXISTS FOR (w:WorldviewEntry) ON (w.name, w.entry_type);
```

> 兼容性说明：早期文档/实现中 `:Novel` 可能使用 `app_id` 表示小说ID；自本规范起统一为 `novel_id`，并在所有查询中以 `MATCH (:Novel {novel_id: $novel_id})` 作为范围入口。
