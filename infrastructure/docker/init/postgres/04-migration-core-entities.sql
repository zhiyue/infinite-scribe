-- =====================================================
-- 数据库迁移脚本 - 核心实体表更新和创建
-- Story 2.1 Task 2: 创建完整的数据库迁移脚本
-- =====================================================

-- ⚠️ 重要依赖警告：
-- 此脚本必须在 03-migration-enums.sql 之后执行！
-- 本脚本使用了以下ENUM类型，如果这些类型不存在会导致执行失败：
-- * agent_type, novel_status, chapter_status, activity_status等
-- 
-- 执行前请确认：03-migration-enums.sql 已成功执行

-- 1. 更新现有核心实体表，添加缺失字段

-- 更新 novels 表：添加版本控制和Agent追踪字段
ALTER TABLE novels 
    -- 删除旧的status CHECK约束
    DROP CONSTRAINT IF EXISTS novels_status_check,
    -- 添加版本控制字段
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    -- 添加Agent追踪字段
    ADD COLUMN IF NOT EXISTS created_by_agent_type agent_type,
    ADD COLUMN IF NOT EXISTS updated_by_agent_type agent_type;

-- 单独处理 status 字段类型转换（先删除默认值，再修改类型，最后重设默认值）
ALTER TABLE novels ALTER COLUMN status DROP DEFAULT;
ALTER TABLE novels ALTER COLUMN status TYPE novel_status USING status::novel_status;
ALTER TABLE novels ALTER COLUMN status SET DEFAULT 'GENESIS';

-- 更新 chapters 表：添加版本控制和Agent追踪字段
ALTER TABLE chapters
    -- 删除旧的status CHECK约束
    DROP CONSTRAINT IF EXISTS chapters_status_check,
    -- 添加版本控制字段
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    -- 添加Agent追踪字段
    ADD COLUMN IF NOT EXISTS created_by_agent_type agent_type,
    ADD COLUMN IF NOT EXISTS updated_by_agent_type agent_type,
    -- 添加发布版本关联字段
    ADD COLUMN IF NOT EXISTS published_version_id UUID;

-- 单独处理 status 字段类型转换
ALTER TABLE chapters ALTER COLUMN status DROP DEFAULT;
ALTER TABLE chapters ALTER COLUMN status TYPE chapter_status USING status::chapter_status;
ALTER TABLE chapters ALTER COLUMN status SET DEFAULT 'DRAFT';

-- 更新 characters 表：添加缺失字段
ALTER TABLE characters
    -- 删除旧的role CHECK约束
    DROP CONSTRAINT IF EXISTS characters_role_check,
    -- 添加版本控制字段
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    -- 添加Agent追踪字段  
    ADD COLUMN IF NOT EXISTS created_by_agent_type agent_type,
    ADD COLUMN IF NOT EXISTS updated_by_agent_type agent_type,
    -- 修改role字段约束
    ALTER COLUMN role DROP NOT NULL,
    ADD CONSTRAINT characters_role_check CHECK (role IN ('PROTAGONIST', 'ANTAGONIST', 'ALLY', 'SUPPORTING'));

-- 更新 worldview_entries 表：添加版本控制和Agent追踪字段
ALTER TABLE worldview_entries
    -- 添加版本控制字段
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    -- 添加Agent追踪字段
    ADD COLUMN IF NOT EXISTS created_by_agent_type agent_type,
    ADD COLUMN IF NOT EXISTS updated_by_agent_type agent_type;

-- 更新 story_arcs 表：添加版本控制和Agent追踪字段
ALTER TABLE story_arcs
    -- 删除旧的status CHECK约束
    DROP CONSTRAINT IF EXISTS story_arcs_status_check,
    -- 添加版本控制字段
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1,
    -- 添加Agent追踪字段
    ADD COLUMN IF NOT EXISTS created_by_agent_type agent_type,
    ADD COLUMN IF NOT EXISTS updated_by_agent_type agent_type,
    -- 保持现有status约束（与架构一致）
    ADD CONSTRAINT story_arcs_status_check CHECK (status IN ('PLANNED', 'ACTIVE', 'COMPLETED'));

-- 2. 创建新的核心实体表

-- 章节版本表：支持章节的版本化管理
CREATE TABLE IF NOT EXISTS chapter_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL, -- 外键将在后面添加
    version_number INTEGER NOT NULL,
    content_url TEXT NOT NULL,
    word_count INTEGER,
    created_by_agent_type agent_type NOT NULL,
    change_reason TEXT,
    parent_version_id UUID REFERENCES chapter_versions(id) ON DELETE SET NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(chapter_id, version_number)
);

COMMENT ON TABLE chapter_versions IS '章节版本表：支持章节内容的版本化管理和历史追踪';
COMMENT ON COLUMN chapter_versions.id IS '章节版本唯一标识符';
COMMENT ON COLUMN chapter_versions.chapter_id IS '关联的章节ID，外键关联chapters表';
COMMENT ON COLUMN chapter_versions.version_number IS '版本号，从1开始递增';
COMMENT ON COLUMN chapter_versions.content_url IS '指向Minio中该版本内容的URL';
COMMENT ON COLUMN chapter_versions.word_count IS '该版本的字数统计';
COMMENT ON COLUMN chapter_versions.created_by_agent_type IS '创建此版本的Agent类型';
COMMENT ON COLUMN chapter_versions.change_reason IS '修改原因，如"根据评论家意见修改"';
COMMENT ON COLUMN chapter_versions.parent_version_id IS '指向上一个版本的ID，形成版本链';
COMMENT ON COLUMN chapter_versions.metadata IS '存储与此版本相关的额外元数据';
COMMENT ON COLUMN chapter_versions.created_at IS '版本创建时间';

-- 大纲表：存储章节大纲信息
CREATE TABLE IF NOT EXISTS outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    created_by_agent_type agent_type,
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    content_url TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(chapter_id, version)
);

COMMENT ON TABLE outlines IS '大纲表：存储章节的详细大纲信息';
COMMENT ON COLUMN outlines.id IS '大纲唯一标识符';
COMMENT ON COLUMN outlines.chapter_id IS '关联的章节ID';
COMMENT ON COLUMN outlines.created_by_agent_type IS '创建此大纲的Agent类型';
COMMENT ON COLUMN outlines.version IS '大纲版本号';
COMMENT ON COLUMN outlines.content IS '大纲文本内容';
COMMENT ON COLUMN outlines.content_url IS '指向Minio中存储的大纲文件URL';
COMMENT ON COLUMN outlines.metadata IS '额外的结构化元数据';

-- 场景卡表：存储详细的场景设计信息
CREATE TABLE IF NOT EXISTS scene_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    outline_id UUID NOT NULL REFERENCES outlines(id) ON DELETE CASCADE,
    created_by_agent_type agent_type,
    scene_number INTEGER NOT NULL,
    pov_character_id UUID REFERENCES characters(id),
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE scene_cards IS '场景卡表：存储章节内各个场景的详细设计信息';
COMMENT ON COLUMN scene_cards.id IS '场景卡唯一标识符';
COMMENT ON COLUMN scene_cards.novel_id IS '(冗余) 所属小说ID，用于性能优化';
COMMENT ON COLUMN scene_cards.chapter_id IS '(冗余) 所属章节ID，用于性能优化';
COMMENT ON COLUMN scene_cards.outline_id IS '关联的大纲ID';
COMMENT ON COLUMN scene_cards.created_by_agent_type IS '创建此场景卡的Agent类型';
COMMENT ON COLUMN scene_cards.scene_number IS '场景在章节内的序号';
COMMENT ON COLUMN scene_cards.pov_character_id IS '视角角色ID';
COMMENT ON COLUMN scene_cards.content IS '场景的详细设计（如节奏、目标、转折点）';

-- 角色互动表：记录角色之间的具体互动
CREATE TABLE IF NOT EXISTS character_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    scene_card_id UUID NOT NULL REFERENCES scene_cards(id) ON DELETE CASCADE,
    created_by_agent_type agent_type,
    interaction_type VARCHAR(50),
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE character_interactions IS '角色互动表：记录场景中角色之间的具体互动内容';
COMMENT ON COLUMN character_interactions.id IS '角色互动唯一标识符';
COMMENT ON COLUMN character_interactions.novel_id IS '(冗余) 所属小说ID';
COMMENT ON COLUMN character_interactions.chapter_id IS '(冗余) 所属章节ID';
COMMENT ON COLUMN character_interactions.scene_card_id IS '关联的场景卡ID';
COMMENT ON COLUMN character_interactions.created_by_agent_type IS '创建此互动的Agent类型';
COMMENT ON COLUMN character_interactions.interaction_type IS '互动类型（如"dialogue", "action"）';
COMMENT ON COLUMN character_interactions.content IS '互动的详细内容（如对话文本）';

-- 更新评审表：使用新的ENUM类型和字段
-- 注意：这里使用ALTER TABLE而不是DROP TABLE来避免数据丢失
-- 首先检查表是否存在，如果不存在则创建，如果存在则更新结构

DO $$
BEGIN
    -- 检查reviews表是否存在
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'reviews') THEN
        -- 表存在，进行安全的结构更新
        
        -- 添加新字段（如果不存在）
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'reviews' AND column_name = 'chapter_version_id') THEN
            ALTER TABLE reviews ADD COLUMN chapter_version_id UUID;
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'reviews' AND column_name = 'workflow_run_id') THEN
            ALTER TABLE reviews ADD COLUMN workflow_run_id UUID;
        END IF;
        
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'reviews' AND column_name = 'agent_type') THEN
            ALTER TABLE reviews ADD COLUMN agent_type agent_type;
        END IF;
        
        -- 删除旧的agent_id字段（如果存在）
        IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'reviews' AND column_name = 'agent_id') THEN
            ALTER TABLE reviews DROP COLUMN IF EXISTS agent_id;
        END IF;
        
        -- 更新约束（先删除旧的，再添加新的）
        ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_review_type_check;
        ALTER TABLE reviews DROP CONSTRAINT IF EXISTS reviews_type_check;
        ALTER TABLE reviews ADD CONSTRAINT reviews_type_check CHECK (review_type IN ('CRITIC', 'FACT_CHECK'));
        
    ELSE
        -- 表不存在，创建新表
        CREATE TABLE reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
            chapter_version_id UUID, -- 外键将在后面添加
            workflow_run_id UUID, -- 关联的工作流运行ID (无外键)
            agent_type agent_type NOT NULL,
            review_type VARCHAR(50) NOT NULL,
            score NUMERIC(3, 1),
            comment TEXT,
            is_consistent BOOLEAN,
            issues_found TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT reviews_type_check CHECK (review_type IN ('CRITIC', 'FACT_CHECK'))
        );
    END IF;
END $$;

COMMENT ON TABLE reviews IS '评审记录表：存储AI智能体对章节版本的评审结果';
COMMENT ON COLUMN reviews.id IS '评审记录唯一标识符';
COMMENT ON COLUMN reviews.chapter_id IS '被评审的章节ID';
COMMENT ON COLUMN reviews.chapter_version_id IS '评审针对的具体章节版本ID';
COMMENT ON COLUMN reviews.workflow_run_id IS '关联的工作流运行ID（无外键约束）';
COMMENT ON COLUMN reviews.agent_type IS '执行评审的Agent类型';
COMMENT ON COLUMN reviews.review_type IS '评审类型：CRITIC(评论家审查)、FACT_CHECK(事实核查)';
COMMENT ON COLUMN reviews.score IS '评论家评分，范围0.0-10.0';
COMMENT ON COLUMN reviews.comment IS '评论家评语';
COMMENT ON COLUMN reviews.is_consistent IS '事实核查员判断是否一致';
COMMENT ON COLUMN reviews.issues_found IS '事实核查员发现的问题列表';

-- 3. 添加外键约束（在所有表创建完成后）

-- 为 chapter_versions 表添加外键约束
ALTER TABLE chapter_versions 
    ADD CONSTRAINT fk_chapter_versions_chapter_id 
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE;

-- 为 chapters 表添加发布版本外键约束
ALTER TABLE chapters 
    ADD CONSTRAINT fk_chapters_published_version 
    FOREIGN KEY (published_version_id) REFERENCES chapter_versions(id) ON DELETE SET NULL;

-- 为 reviews 表添加章节版本外键约束
ALTER TABLE reviews 
    ADD CONSTRAINT fk_reviews_chapter_version 
    FOREIGN KEY (chapter_version_id) REFERENCES chapter_versions(id) ON DELETE CASCADE;