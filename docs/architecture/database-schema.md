# Database Schema

## PostgreSQL

### 混合外键策略说明
*   **核心领域模型**: 在代表小说核心结构和内容的表之间（如`novels`, `chapters`, `characters`等），**保留**数据库内建的外键约束（`REFERENCES`），以保证数据的强一致性和引用完整性。
*   **追踪与日志系统**: 在高吞吐量的追踪和日志类表（如`agent_activities`, `events`, `workflow_runs`）中，**不使用**内建外键约束。关联ID将作为普通字段存储，由应用层负责维护其有效性，以获得更好的写入性能和未来扩展的灵活性。

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
CREATE TYPE activity_status AS ENUM ('STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'RETRYING');
CREATE TYPE workflow_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'PAUSED');
CREATE TYPE event_status AS ENUM ('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', 'DEAD_LETTER');
CREATE TYPE novel_status AS ENUM ('GENESIS', 'GENERATING', 'PAUSED', 'COMPLETED', 'FAILED');
CREATE TYPE chapter_status AS ENUM ('DRAFT', 'REVIEWING', 'REVISING', 'PUBLISHED');

CREATE TYPE task_status AS ENUM (
    'PENDING',    -- 等待处理
    'RUNNING',    -- 正在运行
    'COMPLETED',  -- 已完成
    'FAILED',     -- 失败
    'CANCELLED'   -- 已取消
);
CREATE TYPE genesis_task_type AS ENUM (
    'concept_generation',     -- 立意生成
    'concept_refinement',     -- 立意优化
    'story_generation',       -- 故事构思生成
    'story_refinement',       -- 故事构思优化
    'worldview_generation',   -- 世界观生成
    'character_generation',   -- 角色生成
    'plot_generation'         -- 剧情生成
);

--- 核心实体表 ---

-- 异步任务管理表（用于创世流程中的AI agent交互）
CREATE TABLE genesis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 任务唯一标识符
    session_id UUID NOT NULL REFERENCES genesis_sessions(id) ON DELETE CASCADE, -- 关联的创世会话ID
    target_stage genesis_stage NOT NULL, -- 任务对应的创世阶段
    task_type genesis_task_type NOT NULL, -- 任务类型
    status task_status NOT NULL DEFAULT 'PENDING', -- 任务当前状态
    progress DECIMAL(4,3) NOT NULL DEFAULT 0.000, -- 任务进度百分比 (0.000-1.000)
    current_stage VARCHAR(100), -- 当前处理阶段的内部标识
    message TEXT, -- 面向用户的状态描述消息
    input_data JSONB NOT NULL, -- 任务输入数据
    result_data JSONB, -- 任务执行结果
    error_data JSONB, -- 任务失败时的错误信息
    result_step_id UUID REFERENCES genesis_steps(id) ON DELETE SET NULL, -- 任务成功时创建的genesis_step记录ID
    agent_type agent_type, -- 执行任务的Agent类型
    estimated_duration_seconds INTEGER, -- 预估任务执行时间（秒）
    actual_duration_seconds INTEGER, -- 实际任务执行时间（秒）
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    started_at TIMESTAMPTZ, -- 任务开始执行时间
    completed_at TIMESTAMPTZ, -- 任务完成时间
    
    -- 约束条件
    CONSTRAINT progress_range CHECK (progress >= 0.000 AND progress <= 1.000),
    CONSTRAINT valid_completed_task CHECK (
        status != 'COMPLETED' OR (result_data IS NOT NULL AND completed_at IS NOT NULL)
    ),
    CONSTRAINT valid_failed_task CHECK (
        status != 'FAILED' OR error_data IS NOT NULL
    ),
    CONSTRAINT valid_running_task CHECK (
        status != 'RUNNING' OR started_at IS NOT NULL
    )
);

-- 立意模板表（存储AI生成的抽象哲学立意供用户选择）
CREATE TABLE concept_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 立意模板唯一标识符
    core_idea VARCHAR(200) NOT NULL, -- 核心抽象思想
    description VARCHAR(800) NOT NULL, -- 立意的深层含义阐述
    philosophical_depth VARCHAR(1000) NOT NULL, -- 哲学思辨的深度表达
    emotional_core VARCHAR(500) NOT NULL, -- 情感核心与内在冲突
    philosophical_category VARCHAR(100), -- 哲学类别
    thematic_tags TEXT[] DEFAULT '{}', -- 主题标签数组
    complexity_level VARCHAR(20) NOT NULL DEFAULT 'medium', -- 思辨复杂度
    universal_appeal BOOLEAN NOT NULL DEFAULT true, -- 是否具有普遍意义
    cultural_specificity VARCHAR(100), -- 文化特异性
    usage_count INTEGER NOT NULL DEFAULT 0, -- 被选择使用的次数统计
    rating_sum INTEGER NOT NULL DEFAULT 0, -- 用户评分总和
    rating_count INTEGER NOT NULL DEFAULT 0, -- 评分人数
    is_active BOOLEAN NOT NULL DEFAULT true, -- 是否启用（用于软删除）
    created_by VARCHAR(50), -- 创建者
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    
    -- 约束条件
    CONSTRAINT complexity_level_check CHECK (complexity_level IN ('simple', 'medium', 'complex')),
    CONSTRAINT usage_count_non_negative CHECK (usage_count >= 0),
    CONSTRAINT rating_sum_non_negative CHECK (rating_sum >= 0),
    CONSTRAINT rating_count_non_negative CHECK (rating_count >= 0),
    CONSTRAINT core_idea_not_empty CHECK (LENGTH(TRIM(core_idea)) > 0),
    CONSTRAINT description_not_empty CHECK (LENGTH(TRIM(description)) > 0)
);

CREATE TABLE novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 小说唯一ID
    title VARCHAR(255) NOT NULL, -- 小说标题
    theme TEXT, -- 小说主题
    writing_style TEXT, -- 写作风格
    status novel_status NOT NULL DEFAULT 'GENESIS', -- 当前状态
    target_chapters INTEGER NOT NULL DEFAULT 0, -- 目标章节数
    completed_chapters INTEGER NOT NULL DEFAULT 0, -- 已完成章节数
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_by_agent_type agent_type, -- 创建此记录的Agent类型
    updated_by_agent_type agent_type, -- 最后更新此记录的Agent类型
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 最后更新时间
);

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

CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 章节唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    chapter_number INTEGER NOT NULL, -- 章节序号
    title VARCHAR(255), -- 章节标题
    status chapter_status NOT NULL DEFAULT 'DRAFT', -- 章节当前状态
    published_version_id UUID REFERENCES chapter_versions(id) ON DELETE SET NULL, -- 指向当前已发布版本的ID
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_by_agent_type agent_type, -- 创建此记录的Agent类型
    updated_by_agent_type agent_type, -- 最后更新此记录的Agent类型
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    UNIQUE (novel_id, chapter_number)
);

ALTER TABLE chapter_versions ADD CONSTRAINT fk_chapter_versions_chapter_id FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE;

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
    created_by_agent_type agent_type, -- 创建此记录的Agent类型
    updated_by_agent_type agent_type, -- 最后更新此记录的Agent类型
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 最后更新时间
);

CREATE TABLE worldview_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 世界观条目唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    entry_type VARCHAR(50) NOT NULL, -- 条目类型 (如 'LOCATION', 'ORGANIZATION')
    name VARCHAR(255) NOT NULL, -- 条目名称
    description TEXT, -- 详细描述
    tags TEXT[], -- 标签，用于分类和检索
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_by_agent_type agent_type, -- 创建此记录的Agent类型
    updated_by_agent_type agent_type, -- 最后更新此记录的Agent类型
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    UNIQUE (novel_id, name, entry_type)
);

CREATE TABLE story_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 故事弧唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    title VARCHAR(255) NOT NULL, -- 故事弧标题
    summary TEXT, -- 故事弧摘要
    start_chapter_number INTEGER, -- 开始章节号
    end_chapter_number INTEGER, -- 结束章节号
    status VARCHAR(50) DEFAULT 'PLANNED', -- 状态 (如 'PLANNED', 'ACTIVE', 'COMPLETED')
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_by_agent_type agent_type, -- 创建此记录的Agent类型
    updated_by_agent_type agent_type, -- 最后更新此记录的Agent类型
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 最后更新时间
);

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 评审记录唯一ID
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE, -- 关联的章节ID
    chapter_version_id UUID NOT NULL REFERENCES chapter_versions(id) ON DELETE CASCADE, -- 评审针对的具体章节版本ID
    workflow_run_id UUID, -- 关联的工作流运行ID (无外键)
    agent_type agent_type NOT NULL, -- 执行评审的Agent类型
    review_type VARCHAR(50) NOT NULL, -- 评审类型 (如 'CRITIC', 'FACT_CHECK')
    score NUMERIC(3, 1), -- 评论家评分
    comment TEXT, -- 评论家评语
    is_consistent BOOLEAN, -- 事实核查员判断是否一致
    issues_found TEXT[], -- 事实核查员发现的问题列表
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 评审创建时间
);

--- 中间产物表 ---

CREATE TABLE outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 大纲唯一ID
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE, -- 关联的章节ID
    created_by_agent_type agent_type, -- 创建此大纲的Agent类型
    version INTEGER NOT NULL DEFAULT 1, -- 大纲版本号
    content TEXT NOT NULL, -- 大纲文本内容
    content_url TEXT, -- 指向Minio中存储的大纲文件URL
    metadata JSONB, -- 额外的结构化元数据
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    UNIQUE(chapter_id, version)
);

CREATE TABLE scene_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 场景卡唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- (冗余) 所属小说ID，用于性能优化
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE, -- (冗余) 所属章节ID，用于性能优化
    outline_id UUID NOT NULL REFERENCES outlines(id) ON DELETE CASCADE, -- 关联的大纲ID
    created_by_agent_type agent_type, -- 创建此场景卡的Agent类型
    scene_number INTEGER NOT NULL, -- 场景在章节内的序号
    pov_character_id UUID REFERENCES characters(id), -- 视角角色ID
    content JSONB NOT NULL, -- 场景的详细设计 (如节奏、目标、转折点)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 创建时间
);

CREATE TABLE character_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 角色互动唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- (冗余) 所属小说ID
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE, -- (冗余) 所属章节ID
    scene_card_id UUID NOT NULL REFERENCES scene_cards(id) ON DELETE CASCADE, -- 关联的场景卡ID
    created_by_agent_type agent_type, -- 创建此互动的Agent类型
    interaction_type VARCHAR(50), -- 互动类型 (如 'dialogue', 'action')
    content JSONB NOT NULL, -- 互动的详细内容 (如对话文本)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- 创建时间
);

--- 追踪与配置表 (无外键) ---

CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 工作流运行实例的唯一ID
    novel_id UUID NOT NULL, -- 关联的小说ID
    workflow_type VARCHAR(100) NOT NULL, -- 工作流类型 (如 'chapter_generation')
    status workflow_status NOT NULL, -- 工作流当前状态
    parameters JSONB, -- 启动工作流时传入的参数
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 开始时间
    completed_at TIMESTAMPTZ, -- 完成时间
    error_details JSONB -- 如果失败，记录错误详情
);

CREATE TABLE agent_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Agent活动的唯一ID
    workflow_run_id UUID, -- 关联的工作流运行ID
    novel_id UUID NOT NULL, -- 关联的小说ID
    target_entity_id UUID, -- 活动操作的目标实体ID (如 chapter_id, character_id)
    target_entity_type VARCHAR(50), -- 目标实体类型 (如 'CHAPTER', 'CHARACTER')
    agent_type agent_type, -- 执行活动的Agent类型
    activity_type VARCHAR(100) NOT NULL, -- 活动类型 (如 'GENERATE_OUTLINE', 'WRITE_DRAFT')
    status activity_status NOT NULL, -- 活动状态
    input_data JSONB, -- 活动的输入数据摘要
    output_data JSONB, -- 活动的输出数据摘要
    error_details JSONB, -- 如果失败，记录错误详情
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 开始时间
    completed_at TIMESTAMPTZ, -- 完成时间
    duration_seconds INTEGER GENERATED ALWAYS AS (EXTRACT(EPOCH FROM (completed_at - started_at))::INTEGER) STORED, -- 持续时间（秒）
    llm_tokens_used INTEGER, -- 调用LLM消耗的Token数
    llm_cost_estimate DECIMAL(10, 6), -- 调用LLM的估算成本
    retry_count INTEGER DEFAULT 0 -- 重试次数
) PARTITION BY RANGE (started_at);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 事件唯一ID
    event_type VARCHAR(100) NOT NULL, -- 事件类型 (如 'Outline.Created')
    novel_id UUID, -- 关联的小说ID
    workflow_run_id UUID, -- 关联的工作流运行ID
    payload JSONB NOT NULL, -- 事件的完整载荷
    status event_status NOT NULL DEFAULT 'PENDING', -- 事件处理状态
    processed_by_agent_type agent_type, -- 处理此事件的Agent类型
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 事件创建时间
    processed_at TIMESTAMPTZ, -- 事件处理完成时间
    error_details JSONB -- 如果处理失败，记录错误详情
);

CREATE TABLE agent_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 配置项唯一ID
    novel_id UUID, -- 关联的小说ID (NULL表示全局配置)
    agent_type agent_type, -- 配置作用的Agent类型
    config_key VARCHAR(255) NOT NULL, -- 配置项名称 (如 'llm_model')
    config_value TEXT NOT NULL, -- 配置项的值
    is_active BOOLEAN DEFAULT true, -- 是否启用此配置
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    UNIQUE(novel_id, agent_type, config_key)
);

--- 创世流程追踪表 ---

CREATE TYPE genesis_status AS ENUM ('IN_PROGRESS', 'COMPLETED', 'ABANDONED');
CREATE TYPE genesis_stage AS ENUM (
    'CONCEPT_SELECTION',  -- 立意选择与迭代阶段：用户从AI生成的抽象立意中选择并优化
    'STORY_CONCEPTION',   -- 故事构思阶段：将确认的立意转化为具体故事框架
    'WORLDVIEW',          -- 世界观创建阶段：基于故事构思设计详细世界观
    'CHARACTERS',         -- 角色设定阶段：设计主要角色
    'PLOT_OUTLINE',       -- 情节大纲阶段：制定整体剧情框架
    'FINISHED'            -- 完成阶段：创世过程结束
);

-- 立意模板表：存储AI生成的抽象哲学立意供用户选择
CREATE TABLE concept_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 核心立意内容（抽象哲学思想）
    core_idea VARCHAR(200) NOT NULL,
    description VARCHAR(800) NOT NULL,
    
    -- 哲学维度
    philosophical_depth VARCHAR(1000) NOT NULL,
    emotional_core VARCHAR(500) NOT NULL,
    
    -- 分类标签（抽象层面）
    philosophical_category VARCHAR(100),
    thematic_tags TEXT[] DEFAULT '{}',
    complexity_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    
    -- 适用性
    universal_appeal BOOLEAN NOT NULL DEFAULT true,
    cultural_specificity VARCHAR(100),
    
    -- 使用统计
    usage_count INTEGER NOT NULL DEFAULT 0,
    rating_sum INTEGER NOT NULL DEFAULT 0,
    rating_count INTEGER NOT NULL DEFAULT 0,
    
    -- 元数据
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 约束条件
    CONSTRAINT complexity_level_check CHECK (complexity_level IN ('simple', 'medium', 'complex')),
    CONSTRAINT usage_count_non_negative CHECK (usage_count >= 0),
    CONSTRAINT rating_sum_non_negative CHECK (rating_sum >= 0),
    CONSTRAINT rating_count_non_negative CHECK (rating_count >= 0),
    CONSTRAINT core_idea_not_empty CHECK (LENGTH(TRIM(core_idea)) > 0),
    CONSTRAINT description_not_empty CHECK (LENGTH(TRIM(description)) > 0)
);

CREATE TABLE genesis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    user_id UUID,
    status genesis_status NOT NULL DEFAULT 'IN_PROGRESS',
    current_stage genesis_stage NOT NULL DEFAULT 'CONCEPT_SELECTION',
    initial_user_input JSONB,
    final_settings JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE genesis_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES genesis_sessions(id) ON DELETE CASCADE,
    stage genesis_stage NOT NULL,
    iteration_count INTEGER NOT NULL,
    ai_prompt TEXT,
    ai_output JSONB NOT NULL,
    user_feedback TEXT,
    is_confirmed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT unique_iteration_per_stage UNIQUE (session_id, stage, iteration_count)
);

--- 索引定义 ---

-- 性能关键索引
CREATE INDEX idx_agent_activities_novel_agent ON agent_activities(novel_id, agent_type, started_at DESC);
CREATE INDEX idx_workflow_runs_novel_status ON workflow_runs(novel_id, status);
CREATE INDEX idx_events_type_status ON events(event_type, status);
CREATE INDEX idx_chapter_versions_chapter ON chapter_versions(chapter_id, version_number DESC);

-- 用于关联查询的索引
CREATE INDEX idx_reviews_chapter_version ON reviews(chapter_id, chapter_version_id);
CREATE INDEX idx_scene_cards_chapter ON scene_cards(chapter_id, scene_number);
CREATE INDEX idx_outlines_chapter ON outlines(chapter_id);
CREATE INDEX idx_character_interactions_scene ON character_interactions(scene_card_id);

-- 创世流程相关索引
CREATE INDEX idx_genesis_sessions_stage_status ON genesis_sessions(current_stage, status) WHERE status = 'IN_PROGRESS';
CREATE INDEX idx_genesis_steps_session_stage_confirmed ON genesis_steps(session_id, stage, is_confirmed);
CREATE INDEX idx_genesis_steps_ai_output_step_type ON genesis_steps USING GIN ((ai_output->'step_type'));
CREATE INDEX idx_genesis_steps_confirmed_created_at ON genesis_steps(created_at) WHERE is_confirmed = true;

-- 立意模板相关索引
CREATE INDEX idx_concept_templates_philosophical_category ON concept_templates(philosophical_category) WHERE is_active = true;
CREATE INDEX idx_concept_templates_complexity_level ON concept_templates(complexity_level) WHERE is_active = true;
CREATE INDEX idx_concept_templates_thematic_tags ON concept_templates USING GIN(thematic_tags) WHERE is_active = true;
CREATE INDEX idx_concept_templates_usage_count ON concept_templates(usage_count DESC) WHERE is_active = true;
CREATE INDEX idx_concept_templates_rating ON concept_templates((rating_sum::float / NULLIF(rating_count, 0)) DESC NULLS LAST) WHERE is_active = true AND rating_count > 0;

--- 触发器定义 ---

-- 为所有有 updated_at 的表创建触发器
CREATE TRIGGER set_timestamp_novels BEFORE UPDATE ON novels FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_chapters BEFORE UPDATE ON chapters FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_characters BEFORE UPDATE ON characters FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_worldview_entries BEFORE UPDATE ON worldview_entries FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_story_arcs BEFORE UPDATE ON story_arcs FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_agent_configurations BEFORE UPDATE ON agent_configurations FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_concept_templates BEFORE UPDATE ON concept_templates FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();
CREATE TRIGGER set_timestamp_genesis_sessions BEFORE UPDATE ON genesis_sessions FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

--- 数据完整性约束 ---

-- 确保 published_version_id 指向的版本属于同一章节
ALTER TABLE chapters ADD CONSTRAINT check_published_version 
CHECK (published_version_id IS NULL OR EXISTS (
    SELECT 1 FROM chapter_versions cv 
    WHERE cv.id = chapters.published_version_id AND cv.chapter_id = chapters.id
));

-- 确保创世流程新阶段的数据完整性
-- 确保 CONCEPT_SELECTION 阶段的 ai_output 包含有效的 step_type
ALTER TABLE genesis_steps 
ADD CONSTRAINT valid_concept_selection_data 
CHECK (
    stage != 'CONCEPT_SELECTION' OR (
        ai_output ? 'step_type' AND 
        ai_output->>'step_type' IN ('ai_generation', 'user_selection', 'concept_refinement', 'concept_confirmation')
    )
);

-- 确保 STORY_CONCEPTION 阶段的 ai_output 包含有效的 step_type
ALTER TABLE genesis_steps 
ADD CONSTRAINT valid_story_conception_data 
CHECK (
    stage != 'STORY_CONCEPTION' OR (
        ai_output ? 'step_type' AND 
        ai_output->>'step_type' IN ('story_generation', 'story_refinement', 'story_confirmation')
    )
);

-- 确保每个阶段只能有一个已确认的最终步骤
CREATE UNIQUE INDEX idx_genesis_steps_unique_confirmed_per_stage 
    ON genesis_steps(session_id, stage) 
    WHERE is_confirmed = true;

--- 未来扩展性规划 (Post-MVP) ---

-- 分区表示例: 为 agent_activities 表自动创建每月分区
CREATE OR REPLACE FUNCTION create_monthly_partition(target_table TEXT)
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE);
    end_date := start_date + interval '1 month';
    partition_name := target_table || '_' || to_char(start_date, 'YYYY_MM');
    
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
            partition_name, target_table, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;
-- 注意: 需要一个定时任务 (如 pg_cron) 来定期调用此函数，例如: SELECT create_monthly_partition('agent_activities');

-- 可选的通用审计日志表
-- 目的: 提供一个更低级别的、由数据库触发器驱动的审计日志，记录所有表的变更。
-- 这与 agent_activities 表形成互补：agent_activities 记录“业务活动”，而 audit_log 记录“数据变更”。
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 审计日志唯一ID
    table_name VARCHAR(63) NOT NULL, -- 发生变更的表名
    record_id UUID NOT NULL, -- 发生变更的记录ID
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')), -- 操作类型
    changed_by_agent_type agent_type, -- 执行变更的Agent类型 (需要通过 session 变量等方式传入)
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 变更发生时间
    old_values JSONB, -- 对于UPDATE和DELETE，记录旧值
    new_values JSONB -- 对于INSERT和UPDATE，记录新值
);
```

## Neo4j
*   **核心原则:** Neo4j用于存储和查询**每个小说项目内部的**知识图谱。它的核心价值在于管理和推理实体之间复杂的、动态演变的关系，这是传统关系型数据库难以高效处理的。
    *   **关联性:** 所有Neo4j中的核心节点都应有一个 `app_id` 属性，其值对应其在PostgreSQL中对应表的主键ID，以便于跨数据库关联和数据补充。
    *   **数据职责:** PostgreSQL负责存储实体的核心“属性”和“版本化内容”，而Neo4j专注于存储这些实体之间的“关系”、“上下文”和“随时间演变的互动状态”。
    *   **范围隔离:** 所有图数据都必须通过关系连接到唯一的 `:Novel` 节点，确保每个小说的知识图谱是完全隔离的。

*   **节点标签 (Node Labels) - 示例:**
    *   `:Novel` (属性: `app_id: string` (来自PG `novels.id`), `title: string`) - 图谱的根节点。
    *   `:Chapter` (属性: `app_id: string` (来自PG `chapters.id`), `chapter_number: integer`, `title: string`) - 章节的元数据节点。
    *   `:ChapterVersion` (属性: `app_id: string` (来自PG `chapter_versions.id`), `version_number: integer`, `created_by_agent_type: string`) - 代表一个具体的章节版本，是大多数事件和互动的关联点。
    *   `:Character` (属性: `app_id: string` (来自PG `characters.id`), `name: string`, `role: string`) - 角色节点。
    *   `:WorldviewEntry` (属性: `app_id: string` (来自PG `worldview_entries.id`), `name: string`, `entry_type: string`) - 世界观实体，如地点、组织、物品等。
    *   `:StoryArc` (属性: `app_id: string` (来自PG `story_arcs.id`), `title: string`, `status: string`) - 故事弧线节点。
    *   `:Outline` (属性: `app_id: string` (来自PG `outlines.id`), `version: integer`) - 大纲节点。
    *   `:SceneCard` (属性: `app_id: string` (来自PG `scene_cards.id`), `scene_number: integer`) - 场景卡节点。
    *   `:Interaction` (属性: `app_id: string` (来自PG `character_interactions.id`), `interaction_type: string`) - 具体的互动事件节点，如对话。
    *   `:Review` (属性: `app_id: string` (来自PG `reviews.id`), `agent_type: string`, `score: float`, `is_consistent: boolean`) - 评审结果节点。
    *   `:PlotPoint` (属性: `description: string`, `significance: float`) - (可选) 用于更细致的情节跟踪，可能没有直接的PG对应。

*   **关系类型 (Relationship Types) - 示例 (所有关系都应隐含地属于某个Novel的上下文):**
    *   **结构性关系 (Structural Relationships):**
        *   `(:Chapter)-[:BELONGS_TO_NOVEL]->(:Novel)`
        *   `(:Character)-[:APPEARS_IN_NOVEL]->(:Novel)`
        *   `(:WorldviewEntry)-[:PART_OF_WORLDVIEW]->(:Novel)`
        *   `(:StoryArc)-[:PART_OF_PLOT]->(:Novel)`
        *   `(:ChapterVersion)-[:VERSION_OF]->(:Chapter)`
        *   `(:Outline)-[:OUTLINE_FOR]->(:ChapterVersion)`
        *   `(:SceneCard)-[:SCENE_IN]->(:Outline)`
        *   `(:Interaction)-[:INTERACTION_IN]->(:SceneCard)`
        *   `(:Review)-[:REVIEWS]->(:ChapterVersion)`
    *   **时序与因果关系 (Temporal & Causal Relationships):**
        *   `(:Chapter)-[:PRECEDES {order: 1}]->(:Chapter {order: 2})`
        *   `(:StoryArc)-[:PRECEDES_ARC]->(:StoryArc)`
        *   `(:WorldviewEntry {entry_type: 'EVENT'})-[:LEADS_TO_EVENT]->(:WorldviewEntry {entry_type: 'EVENT'})`
        *   `(:PlotPoint)-[:CAUSES]->(:PlotPoint)`
    *   **角色关系 (Character Relationships):**
        *   `(:Character)-[:HAS_RELATIONSHIP {type: 'FRIENDLY', strength: 0.9, since_chapter: 5}]->(:Character)`
        *   `(:Character)-[:HAS_RELATIONSHIP {type: 'HOSTILE', reason: 'Betrayal'}]->(:Character)`
        *   `(:Character)-[:MEMBER_OF]->(:WorldviewEntry {entry_type:'ORGANIZATION'})`
        *   `(:Character)-[:HAS_GOAL]->(:PlotPoint)`
    *   **互动与事件关系 (Interaction & Event Relationships):**
        *   `(:ChapterVersion)-[:FEATURES_CHARACTER]->(:Character)`
        *   `(:ChapterVersion)-[:TAKES_PLACE_IN]->(:WorldviewEntry {entry_type:'LOCATION'})`
        *   `(:Interaction)-[:INVOLVES]->(:Character)`
        *   `(:Character)-[:USED_ITEM_IN {chapter_version_id: '...'}]->(:WorldviewEntry {entry_type:'ITEM'})`
        *   `(:ChapterVersion)-[:ADVANCES_ARC]->(:StoryArc)`
        *   `(:ChapterVersion)-[:REVEALS_INFO_ABOUT]->(:WorldviewEntry)`

*   **Cypher 查询示例 (展示图数据库的威力):**
    *   **简单查询 (角色出场章节):**
        ```cypher
        MATCH (c:Character {name: '艾拉'})<-[:FEATURES_CHARACTER]-(cv:ChapterVersion)-[:VERSION_OF]->(chap:Chapter)
        WHERE (chap)-[:BELONGS_TO_NOVEL]->(:Novel {app_id: '指定小说ID'})
        RETURN chap.chapter_number, chap.title
        ORDER BY chap.chapter_number;
        ```
    *   **中等查询 (复杂关系查找):** 找出在“暗影森林”中出现过，并且是“光明教会”敌人的所有角色。
        ```cypher
        MATCH (c:Character)-[:APPEARS_IN_NOVEL]->(:Novel {app_id: '指定小说ID'}),
              (c)-[:TAKES_PLACE_IN]->(:WorldviewEntry {name: '暗影森林'}),
              (c)-[:HAS_RELATIONSHIP {type: 'HOSTILE'}]->(:WorldviewEntry {name: '光明教会', entry_type: 'ORGANIZATION'})
        RETURN c.name, c.role;
        ```
    *   **复杂查询 (事实一致性检查):** 检查角色“艾拉”在第5章的版本中，是否既有在“北境”的互动，又有在“南都”的互动（逻辑矛盾）。
        ```cypher
        MATCH (cv:ChapterVersion)-[:VERSION_OF]->(:Chapter {chapter_number: 5}),
              (cv)-[:BELONGS_TO_NOVEL]->(:Novel {app_id: '指定小说ID'})
        MATCH (cv)-[:FEATURES_CHARACTER]->(c:Character {name: '艾拉'})
        MATCH (c)<-[:INVOLVES]-(:Interaction)-[:INTERACTION_IN]->(:SceneCard)-[:SCENE_IN]->(:Outline)-[:OUTLINE_FOR]->(cv),
              (interaction_location:WorldviewEntry {entry_type: 'LOCATION'})<-[:TAKES_PLACE_IN]-(cv)
        WITH interaction_location.name AS location_name
        RETURN count(DISTINCT location_name) > 1 AS has_contradiction, collect(DISTINCT location_name) AS locations;
        ```

*   **索引策略 (Indexing Strategy):**
    *   为了保证查询性能，必须为节点上频繁用于查找的属性创建索引。
    *   **必须创建的索引:**
        *   `CREATE INDEX novel_app_id FOR (n:Novel) ON (n.app_id);`
        *   `CREATE INDEX chapter_app_id FOR (c:Chapter) ON (c.app_id);`
        *   `CREATE INDEX character_app_id FOR (c:Character) ON (c.app_id);`
        *   `CREATE INDEX worldview_app_id FOR (w:WorldviewEntry) ON (w.app_id);`
    *   **推荐创建的索引:**
        *   `CREATE INDEX character_name FOR (c:Character) ON (c.name);`
        *   `CREATE INDEX worldview_name_type FOR (w:WorldviewEntry) ON (w.name, w.entry_type);`

*   **数据同步策略 (Data Synchronization Strategy):**
    *   **挑战:** 保持PostgreSQL（作为事实来源 Source of Truth）和Neo4j（作为关系视图）之间的数据同步至关重要。
    *   **方案1 (双写模式 - MVP适用):** 应用层的服务在完成一个业务逻辑时，同时向PostgreSQL和Neo4j进行写入。例如，创建一个新角色时，服务先在PG中插入记录，成功后获取ID，再在Neo4j中创建对应的节点。
        *   **优点:** 实现简单直接。
        *   **缺点:** 缺乏事务保证，可能导致数据不一致（例如PG写入成功，Neo4j写入失败）。
    *   **方案2 (事件驱动的CDC模式 - 长期推荐):**
        1.  所有数据变更只写入PostgreSQL。
        2.  使用变更数据捕获（Change Data Capture, CDC）工具（如 Debezium）监控PostgreSQL的预写日志（WAL）。
        3.  Debezium将数据变更（INSERT, UPDATE, DELETE）作为事件发布到Kafka。
        4.  创建一个专门的“图同步服务（Graph Sync Service）”，订阅这些Kafka事件。
        5.  该服务根据接收到的事件，在Neo4j中创建、更新或删除相应的节点和关系。
        *   **优点:** 高度解耦、可靠、可扩展，保证最终一致性。
        *   **缺点:** 架构更复杂，需要引入额外的组件。

## WorldviewEntry 的关系模型详解

`WorldviewEntry` 是知识图谱中最多样化的节点，代表了世界观中的所有非角色实体，如地点、组织、物品、概念等。因此，它拥有最丰富的关系类型，用于构建一个逻辑严密、细节丰富的虚拟世界。

以下是 `WorldviewEntry` 节点作为关系起点或终点的详细关系类型列表：

### 1. 结构性与层级关系 (Structural & Hierarchical)

这些关系定义了世界观条目之间的基本结构和归属。

*   **`(:WorldviewEntry)-[:PART_OF_WORLDVIEW]->(:Novel)`**
    *   **含义:** 声明一个世界观条目属于某部小说的世界观。这是所有世界观条目的根关系。
    *   **示例:** `(:WorldviewEntry {name: '霍格沃茨'})-[:PART_OF_WORLDVIEW]->(:Novel {title: '哈利·波特'})`

*   **`(:WorldviewEntry)-[:CONTAINS]->(:WorldviewEntry)`**
    *   **含义:** 表示一个实体在物理上或概念上包含另一个实体。常用于地点、组织等。
    *   **示例 (地点):** `(:WorldviewEntry {name: '英国', entry_type: 'LOCATION'})-[:CONTAINS]->(:WorldviewEntry {name: '伦敦', entry_type: 'LOCATION'})`
    *   **示例 (组织):** `(:WorldviewEntry {name: '魔法部', entry_type: 'ORGANIZATION'})-[:CONTAINS]->(:WorldviewEntry {name: '傲罗办公室', entry_type: 'ORGANIZATION'})`

*   **`(:WorldviewEntry)-[:DERIVED_FROM]->(:WorldviewEntry)`**
    *   **含义:** 表示一个概念、技术或律法源自于另一个。
    *   **示例:** `(:WorldviewEntry {name: '曲速引擎', entry_type: 'TECHNOLOGY'})-[:DERIVED_FROM]->(:WorldviewEntry {name: '空间折叠理论', entry_type: 'CONCEPT'})`

### 2. 实体间交互关系 (Inter-Entity Interactions)

这些关系描述了不同世界观条目之间的动态或静态互动。

*   **`(:WorldviewEntry)-[:HOSTILE_TO | ALLIED_WITH | NEUTRAL_TO]->(:WorldviewEntry)`**
    *   **含义:** 定义组织、国家等实体之间的阵营关系。
    *   **属性示例:** `{ since_year: 1941, reason: "Territorial dispute" }`
    *   **示例:** `(:WorldviewEntry {name: '光明教会'})-[:HOSTILE_TO]->(:WorldviewEntry {name: '暗影兄弟会'})`

*   **`(:WorldviewEntry)-[:REQUIRES]->(:WorldviewEntry)`**
    *   **含义:** 表示一个技术、物品或事件的发生需要另一个物品、技术或概念作为前提。
    *   **示例:** `(:WorldviewEntry {name: '传送法术', entry_type: 'TECHNOLOGY'})-[:REQUIRES]->(:WorldviewEntry {name: '魔力水晶', entry_type: 'ITEM'})`

*   **`(:WorldviewEntry)-[:PRODUCES | YIELDS]->(:WorldviewEntry)`**
    *   **含义:** 表示一个地点、组织或技术能够产出某种物品或资源。
    *   **示例:** `(:WorldviewEntry {name: '矮人矿山', entry_type: 'LOCATION'})-[:PRODUCES]->(:WorldviewEntry {name: '秘银', entry_type: 'ITEM'})`

*   **`(:WorldviewEntry)-[:GOVERNED_BY]->(:WorldviewEntry)`**
    *   **含义:** 表示一个地点或组织受到某个律法或另一个组织的管辖。
    *   **示例:** `(:WorldviewEntry {name: '对角巷', entry_type: 'LOCATION'})-[:GOVERNED_BY]->(:WorldviewEntry {name: '魔法不滥用法', entry_type: 'LAW'})`

### 3. 与角色（Character）的交互关系

这些关系将非生命实体与角色紧密联系起来。

*   **`(:Character)-[:MEMBER_OF | LEADS | FOUNDED]->(:WorldviewEntry {entry_type: 'ORGANIZATION'})`**
    *   **含义:** 定义角色与组织之间的关系。
    *   **属性示例:** `{ rank: 'Captain', join_chapter: 3 }`
    *   **示例:** `(:Character {name: '阿拉贡'})-[:MEMBER_OF]->(:WorldviewEntry {name: '护戒远征队'})`

*   **`(:Character)-[:RESIDES_IN | BORN_IN | DIED_IN]->(:WorldviewEntry {entry_type: 'LOCATION'})`**
    *   **含义:** 定义角色的关键生命事件发生的地点。
    *   **属性示例:** `{ start_year: 20, end_year: 35, duration_description: "青年时期" }`
    *   **示例:** `(:Character {name: '弗罗多'})-[:RESIDES_IN]->(:WorldviewEntry {name: '夏尔'})`

*   **`(:Character)-[:POSSESSES | OWNS]->(:WorldviewEntry {entry_type: 'ITEM'})`**
    *   **含义:** 表示角色拥有某个特定物品。
    *   **属性示例:** `{ acquisition_method: "Inherited", acquisition_chapter: 1 }`
    *   **示例:** `(:Character {name: '哈利'})-[:POSSESSES]->(:WorldviewEntry {name: '隐形斗篷'})`

*   **`(:Character)-[:USED_ITEM_IN {chapter_version_id: '...'}]->(:WorldviewEntry {entry_type: 'ITEM'})`**
    *   **含义:** 记录角色在特定章节版本中使用过某个物品。这是一个事件性关系。
    *   **示例:** `(:Character {name: '赫敏'})-[:USED_ITEM_IN {chapter_version_id: '...'}]->(:WorldviewEntry {name: '时间转换器'})`

*   **`(:Character)-[:BELIEVES_IN]->(:WorldviewEntry {entry_type: 'CONCEPT'})`**
    *   **含义:** 表示角色的信仰或所遵循的理念。
    *   **示例:** `(:Character {name: '奈德·史塔克'})-[:BELIEVES_IN]->(:WorldviewEntry {name: '荣誉高于一切'})`

### 4. 与章节版本（ChapterVersion）的叙事关系

这些关系将世界观实体嵌入到具体的故事叙述中。

*   **`(:ChapterVersion)-[:TAKES_PLACE_IN]->(:WorldviewEntry {entry_type: 'LOCATION'})`**
    *   **含义:** 表明某个章节版本的主要故事发生在某个地点。
    *   **示例:** `(:ChapterVersion {version_number: 1, chapter_id: '...' })-[:TAKES_PLACE_IN]->(:WorldviewEntry {name: '禁林'})`

*   **`(:ChapterVersion)-[:MENTIONS]->(:WorldviewEntry)`**
    *   **含义:** 表示某个章节版本中提到了一个世界观条目，但故事不一定发生在那里。用于追踪信息的分布。
    *   **示例:** `(:ChapterVersion { ... })-[:MENTIONS]->(:WorldviewEntry {name: '瓦雷利亚'})`

*   **`(:ChapterVersion)-[:REVEALS_INFO_ABOUT]->(:WorldviewEntry)`**
    *   **含义:** 表示某个章节版本揭示了关于某个世界观条目的关键信息或背景故事。
    *   **属性示例:** `{ info_summary: "揭示了魂器的制作方法" }`
    *   **示例:** `(:ChapterVersion { ... })-[:REVEALS_INFO_ABOUT]->(:WorldviewEntry {name: '魂器', entry_type: 'CONCEPT'})`

*   **`(:ChapterVersion)-[:AFFECTS_STATUS_OF]->(:WorldviewEntry)`**
    *   **含义:** 表示某个章节版本的事件改变了一个世界观实体的状态。
    *   **属性示例:** `{ change_description: "从繁荣变为废墟" }`
    *   **示例:** `(:ChapterVersion { ... })-[:AFFECTS_STATUS_OF]->(:WorldviewEntry {name: '临冬城', entry_type: 'LOCATION'})`

通过这些丰富的关系，Neo4j能够构建一个动态、互联的世界观知识库，为 `FactCheckerAgent` 提供强大的事实核查依据，也为 `PlotMasterAgent` 和 `OutlinerAgent` 在规划后续情节时提供无限的灵感和素材。
