-- ================================================
-- 03-core-entities.sql
-- 核心业务实体表定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建核心业务实体表（小说、章节、角色、世界观等）
-- 2. 建立表之间的外键关系和约束
-- 3. 添加必要的注释和文档
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：02-init-enums.sql（需要所有枚举类型）
-- ================================================

-- 清理可能存在的旧表（按照依赖关系倒序删除）
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS story_arcs CASCADE;
DROP TABLE IF EXISTS worldview_entries CASCADE;
DROP TABLE IF EXISTS characters CASCADE;
DROP TABLE IF EXISTS chapter_versions CASCADE;
DROP TABLE IF EXISTS chapters CASCADE;
DROP TABLE IF EXISTS novels CASCADE;

-- ===========================================
-- 小说主表 - 存储每个独立小说项目的核心元数据
-- ===========================================
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
COMMENT ON COLUMN novels.id IS '小说唯一标识符，自动生成的UUID';
COMMENT ON COLUMN novels.title IS '小说标题，必填，最长255个字符';
COMMENT ON COLUMN novels.theme IS '小说主题描述，如"科幻冒险"、"都市言情"等';
COMMENT ON COLUMN novels.writing_style IS '写作风格描述，如"幽默诙谐"、"严肃写实"等';
COMMENT ON COLUMN novels.status IS '小说生成状态，使用novel_status枚举';
COMMENT ON COLUMN novels.target_chapters IS '目标章节数，用户设定的计划章节总数';
COMMENT ON COLUMN novels.completed_chapters IS '已完成章节数，系统自动统计';
COMMENT ON COLUMN novels.version IS '乐观锁版本号，用于并发控制';
COMMENT ON COLUMN novels.created_at IS '创建时间，带时区的时间戳';
COMMENT ON COLUMN novels.updated_at IS '最后更新时间，通过触发器自动维护';

-- ===========================================
-- 章节元数据表 - 存储章节的元数据，与具体版本内容分离
-- ===========================================
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 章节唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    chapter_number INTEGER NOT NULL, -- 章节序号
    title VARCHAR(255), -- 章节标题
    status chapter_status NOT NULL DEFAULT 'DRAFT', -- 章节当前状态
    published_version_id UUID, -- 指向当前已发布版本的ID（稍后添加外键）
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    UNIQUE (novel_id, chapter_number)
);

COMMENT ON TABLE chapters IS '存储章节的元数据，与具体的版本内容分离。';
COMMENT ON COLUMN chapters.id IS '章节唯一标识符，自动生成的UUID';
COMMENT ON COLUMN chapters.novel_id IS '所属小说ID，外键关联novels表，级联删除';
COMMENT ON COLUMN chapters.chapter_number IS '章节序号，从1开始递增，同一小说内唯一';
COMMENT ON COLUMN chapters.title IS '章节标题，可选字段';
COMMENT ON COLUMN chapters.status IS '章节当前状态，使用chapter_status枚举';
COMMENT ON COLUMN chapters.published_version_id IS '指向当前已发布版本的ID，外键将在chapter_versions表创建后添加';
COMMENT ON COLUMN chapters.version IS '乐观锁版本号，用于并发控制';
COMMENT ON COLUMN chapters.created_at IS '章节创建时间';
COMMENT ON COLUMN chapters.updated_at IS '章节最后更新时间';

-- ===========================================
-- 章节版本表 - 存储一个章节的每一次具体内容的迭代版本，实现版本控制
-- ===========================================
CREATE TABLE chapter_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 章节版本的唯一ID
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE, -- 关联的章节ID
    version_number INTEGER NOT NULL, -- 版本号，从1开始递增
    content_url TEXT NOT NULL, -- 指向Minio中该版本内容的URL
    word_count INTEGER, -- 该版本的字数
    created_by_agent_type agent_type NOT NULL, -- 创建此版本的Agent类型
    change_reason TEXT, -- (可选) 修改原因，如"根据评论家意见修改"
    parent_version_id UUID REFERENCES chapter_versions(id) ON DELETE SET NULL, -- 指向上一个版本的ID，形成版本链
    metadata JSONB, -- 存储与此版本相关的额外元数据
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 版本创建时间
    UNIQUE(chapter_id, version_number)
);

COMMENT ON TABLE chapter_versions IS '存储一个章节的每一次具体内容的迭代版本，实现版本控制。';
COMMENT ON COLUMN chapter_versions.id IS '章节版本的唯一标识符';
COMMENT ON COLUMN chapter_versions.chapter_id IS '关联的章节ID，外键关联chapters表';
COMMENT ON COLUMN chapter_versions.version_number IS '版本号，从1开始递增，同一章节内唯一';
COMMENT ON COLUMN chapter_versions.content_url IS '指向MinIO中该版本内容的URL';
COMMENT ON COLUMN chapter_versions.word_count IS '该版本的字数统计';
COMMENT ON COLUMN chapter_versions.created_by_agent_type IS '创建此版本的AI智能体类型';
COMMENT ON COLUMN chapter_versions.change_reason IS '修改原因说明，如"根据评论家意见修改"';
COMMENT ON COLUMN chapter_versions.parent_version_id IS '指向上一个版本的ID，形成版本链';
COMMENT ON COLUMN chapter_versions.metadata IS '存储与此版本相关的额外元数据，JSONB格式';
COMMENT ON COLUMN chapter_versions.created_at IS '版本创建时间';


-- 注意：检查published_version_id是否属于该章节的验证需要在应用层实现
-- PostgreSQL不支持在CHECK约束中使用子查询

-- ===========================================
-- 角色表 - 存储小说中所有角色的详细设定信息
-- ===========================================
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
COMMENT ON COLUMN characters.id IS '角色唯一标识符，对应Neo4j中的app_id';
COMMENT ON COLUMN characters.novel_id IS '所属小说ID，外键关联novels表';
COMMENT ON COLUMN characters.name IS '角色姓名，必填';
COMMENT ON COLUMN characters.role IS '角色定位，如"主角"、"反派"、"配角"等';
COMMENT ON COLUMN characters.description IS '角色外观、特征等描述信息';
COMMENT ON COLUMN characters.background_story IS '角色背景故事，包括身世、经历等';
COMMENT ON COLUMN characters.personality_traits IS '性格特征数组，如["勇敢", "正直", "幽默"]';
COMMENT ON COLUMN characters.goals IS '角色目标数组，如["寻找失散的妹妹", "成为最强剑士"]';
COMMENT ON COLUMN characters.version IS '乐观锁版本号，用于并发控制';
COMMENT ON COLUMN characters.created_at IS '角色创建时间';
COMMENT ON COLUMN characters.updated_at IS '角色信息最后更新时间';

-- ===========================================
-- 世界观条目表 - 存储世界观中的所有设定条目，如地点、组织、物品等
-- ===========================================
CREATE TABLE worldview_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 世界观条目唯一ID
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE, -- 所属小说的ID
    entry_type worldview_entry_type NOT NULL, -- 条目类型，使用worldview_entry_type枚举
    name VARCHAR(255) NOT NULL, -- 条目名称
    description TEXT, -- 详细描述
    tags TEXT[], -- 标签，用于分类和检索
    version INTEGER NOT NULL DEFAULT 1, -- 乐观锁版本号
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 创建时间
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 最后更新时间
    UNIQUE (novel_id, name, entry_type)
);

COMMENT ON TABLE worldview_entries IS '存储世界观中的所有设定条目，如地点、组织、物品等。';
COMMENT ON COLUMN worldview_entries.id IS '条目唯一标识符，与Neo4j图数据库中节点的app_id属性对应';
COMMENT ON COLUMN worldview_entries.novel_id IS '所属小说ID，外键关联novels表';
COMMENT ON COLUMN worldview_entries.entry_type IS '条目类型，使用worldview_entry_type枚举，包括LOCATION(地点)、ORGANIZATION(组织)、TECHNOLOGY(科技)、LAW(法则)、CONCEPT(概念)、EVENT(事件)、ITEM(物品)、CULTURE(文化)、SPECIES(种族)、OTHER(其他)';
COMMENT ON COLUMN worldview_entries.name IS '条目名称，如"魔法学院"、"时空传送门"等，同一小说内按类型唯一';
COMMENT ON COLUMN worldview_entries.description IS '条目详细描述，包含其特征、作用、历史等信息';
COMMENT ON COLUMN worldview_entries.tags IS '标签数组，用于分类和快速检索，如["魔法", "禁地", "古代遗迹"]';
COMMENT ON COLUMN worldview_entries.version IS '乐观锁版本号，用于并发控制';
COMMENT ON COLUMN worldview_entries.created_at IS '条目创建时间';
COMMENT ON COLUMN worldview_entries.updated_at IS '条目最后更新时间';

-- ===========================================
-- 故事弧表 - 存储主要的情节线或故事阶段的规划
-- ===========================================
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
COMMENT ON COLUMN story_arcs.id IS '故事弧唯一标识符';
COMMENT ON COLUMN story_arcs.novel_id IS '所属小说ID，外键关联novels表';
COMMENT ON COLUMN story_arcs.title IS '故事弧标题，如"主角觉醒篇"、"魔王讨伐篇"';
COMMENT ON COLUMN story_arcs.summary IS '故事弧概要，描述这条线索的主要内容和发展';
COMMENT ON COLUMN story_arcs.start_chapter_number IS '故事弧开始的章节号';
COMMENT ON COLUMN story_arcs.end_chapter_number IS '故事弧结束的章节号';
COMMENT ON COLUMN story_arcs.status IS '故事弧状态，如PLANNED(已规划)、ACTIVE(进行中)、COMPLETED(已完成)';
COMMENT ON COLUMN story_arcs.version IS '乐观锁版本号，用于并发控制';
COMMENT ON COLUMN story_arcs.created_at IS '故事弧创建时间';
COMMENT ON COLUMN story_arcs.updated_at IS '故事弧最后更新时间';

-- ===========================================
-- 评审记录表 - 记录每一次对章节草稿的评审结果
-- ===========================================
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
COMMENT ON COLUMN reviews.id IS '评审记录唯一标识符';
COMMENT ON COLUMN reviews.chapter_id IS '被评审的章节ID，外键关联chapters表';
COMMENT ON COLUMN reviews.chapter_version_id IS '评审针对的具体章节版本ID，外键关联chapter_versions表';
COMMENT ON COLUMN reviews.agent_type IS '执行评审的AI智能体类型';
COMMENT ON COLUMN reviews.review_type IS '评审类型，如CRITIC(评论家审查)、FACT_CHECK(事实核查)';
COMMENT ON COLUMN reviews.score IS '评分，范围0.0-10.0，保留一位小数';
COMMENT ON COLUMN reviews.comment IS '评审意见和建议的详细文本';
COMMENT ON COLUMN reviews.is_consistent IS '是否与小说设定一致，用于事实核查';
COMMENT ON COLUMN reviews.issues_found IS '发现的问题列表，如["时间线冲突", "角色性格不一致"]';
COMMENT ON COLUMN reviews.created_at IS '评审创建时间，不会更新';

-- 验证核心实体表创建
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    -- 统计创建的核心实体表数量
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN (
        'novels', 'chapters', 'chapter_versions', 'characters', 
        'worldview_entries', 'story_arcs', 'reviews'
    );
    
    IF table_count != 7 THEN
        RAISE EXCEPTION '核心实体表创建不完整，期望7个，实际创建%个', table_count;
    END IF;
    
    RAISE NOTICE '核心业务实体表创建完成：';
    RAISE NOTICE '- novels: 小说主表';
    RAISE NOTICE '- chapters: 章节元数据表';
    RAISE NOTICE '- chapter_versions: 章节版本表（版本控制）';
    RAISE NOTICE '- characters: 角色表';
    RAISE NOTICE '- worldview_entries: 世界观条目表';
    RAISE NOTICE '- story_arcs: 故事弧表';
    RAISE NOTICE '- reviews: 评审记录表';
    RAISE NOTICE '所有外键约束和检查约束已建立';
END $$;