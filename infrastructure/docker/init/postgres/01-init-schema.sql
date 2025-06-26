-- Novels Table
CREATE TABLE novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    theme TEXT,
    writing_style TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'GENESIS' CHECK (status IN ('GENESIS', 'GENERATING', 'PAUSED', 'COMPLETED', 'FAILED')),
    target_chapters INTEGER NOT NULL DEFAULT 0,
    completed_chapters INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for novels table
COMMENT ON TABLE novels IS '小说主表，存储小说项目的基本信息和生成状态';
COMMENT ON COLUMN novels.id IS '小说唯一标识符，自动生成的UUID';
COMMENT ON COLUMN novels.title IS '小说标题，必填，最长255个字符';
COMMENT ON COLUMN novels.theme IS '小说主题描述，如"科幻冒险"、"都市言情"等';
COMMENT ON COLUMN novels.writing_style IS '写作风格描述，如"幽默诙谐"、"严肃写实"等';
COMMENT ON COLUMN novels.status IS '小说生成状态：GENESIS(创世中)、GENERATING(生成中)、PAUSED(已暂停)、COMPLETED(已完成)、FAILED(失败)';
COMMENT ON COLUMN novels.target_chapters IS '目标章节数，用户设定的计划章节总数';
COMMENT ON COLUMN novels.completed_chapters IS '已完成章节数，系统自动统计';
COMMENT ON COLUMN novels.created_at IS '创建时间，带时区的时间戳';
COMMENT ON COLUMN novels.updated_at IS '最后更新时间，通过触发器自动维护';

-- Chapters Table
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title VARCHAR(255),
    content_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'REVIEWING', 'REVISING', 'PUBLISHED')),
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (novel_id, chapter_number)
);

-- Comments for chapters table
COMMENT ON TABLE chapters IS '章节表，存储小说各章节的元数据和内容位置';
COMMENT ON COLUMN chapters.id IS '章节唯一标识符，自动生成的UUID';
COMMENT ON COLUMN chapters.novel_id IS '所属小说ID，外键关联novels表，级联删除';
COMMENT ON COLUMN chapters.chapter_number IS '章节序号，从1开始递增，同一小说内唯一';
COMMENT ON COLUMN chapters.title IS '章节标题，可选字段';
COMMENT ON COLUMN chapters.content_url IS '章节内容在MinIO中的存储路径URL';
COMMENT ON COLUMN chapters.status IS '章节状态：DRAFT(草稿)、REVIEWING(审查中)、REVISING(修订中)、PUBLISHED(已发布)';
COMMENT ON COLUMN chapters.word_count IS '章节字数统计，默认为0';
COMMENT ON COLUMN chapters.created_at IS '章节创建时间';
COMMENT ON COLUMN chapters.updated_at IS '章节最后更新时间';

-- Characters Table
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) CHECK (role IN ('PROTAGONIST', 'ANTAGONIST', 'ALLY', 'SUPPORTING')),
    description TEXT,
    background_story TEXT,
    personality_traits TEXT[],
    goals TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for characters table
COMMENT ON TABLE characters IS '角色表，存储小说中所有角色的详细信息';
COMMENT ON COLUMN characters.id IS '角色唯一标识符，自动生成的UUID，对应Neo4j中的app_id';
COMMENT ON COLUMN characters.novel_id IS '所属小说ID，外键关联novels表';
COMMENT ON COLUMN characters.name IS '角色姓名，必填';
COMMENT ON COLUMN characters.role IS '角色类型：PROTAGONIST(主角)、ANTAGONIST(反派)、ALLY(盟友)、SUPPORTING(配角)';
COMMENT ON COLUMN characters.description IS '角色外观、特征等描述信息';
COMMENT ON COLUMN characters.background_story IS '角色背景故事，包括身世、经历等';
COMMENT ON COLUMN characters.personality_traits IS '性格特征数组，如["勇敢", "正直", "幽默"]';
COMMENT ON COLUMN characters.goals IS '角色目标数组，如["寻找失散的妹妹", "成为最强剑士"]';
COMMENT ON COLUMN characters.created_at IS '角色创建时间';
COMMENT ON COLUMN characters.updated_at IS '角色信息最后更新时间';

-- Worldview Entries Table (Stores attributes of worldview entities)
CREATE TABLE worldview_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    entry_type VARCHAR(50) NOT NULL CHECK (entry_type IN ('LOCATION', 'ORGANIZATION', 'TECHNOLOGY', 'LAW', 'CONCEPT', 'EVENT', 'ITEM')),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (novel_id, name, entry_type) 
);

-- Comments for worldview_entries table
COMMENT ON TABLE worldview_entries IS '世界观条目表，存储小说世界观中的各种实体元素';
COMMENT ON COLUMN worldview_entries.id IS '条目唯一标识符，与Neo4j图数据库中节点的app_id属性对应';
COMMENT ON COLUMN worldview_entries.novel_id IS '所属小说ID，外键关联novels表';
COMMENT ON COLUMN worldview_entries.entry_type IS '条目类型：LOCATION(地点)、ORGANIZATION(组织)、TECHNOLOGY(科技)、LAW(法则)、CONCEPT(概念)、EVENT(事件)、ITEM(物品)';
COMMENT ON COLUMN worldview_entries.name IS '条目名称，如"魔法学院"、"时空传送门"等，同一小说内按类型唯一';
COMMENT ON COLUMN worldview_entries.description IS '条目详细描述，包含其特征、作用、历史等信息';
COMMENT ON COLUMN worldview_entries.tags IS '标签数组，用于分类和快速检索，如["魔法", "禁地", "古代遗迹"]';
COMMENT ON COLUMN worldview_entries.created_at IS '条目创建时间';
COMMENT ON COLUMN worldview_entries.updated_at IS '条目最后更新时间';

-- Reviews Table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL, 
    review_type VARCHAR(50) NOT NULL CHECK (review_type IN ('CRITIC', 'FACT_CHECK')),
    score NUMERIC(3, 1), 
    comment TEXT, 
    is_consistent BOOLEAN, 
    issues_found TEXT[], 
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for reviews table
COMMENT ON TABLE reviews IS '评审记录表，存储AI智能体对章节的评审结果';
COMMENT ON COLUMN reviews.id IS '评审记录唯一标识符';
COMMENT ON COLUMN reviews.chapter_id IS '被评审的章节ID，外键关联chapters表';
COMMENT ON COLUMN reviews.agent_id IS '执行评审的AI智能体标识，如"critic-agent-01"';
COMMENT ON COLUMN reviews.review_type IS '评审类型：CRITIC(评论家审查)、FACT_CHECK(事实核查)';
COMMENT ON COLUMN reviews.score IS '评分，范围0.0-10.0，保留一位小数';
COMMENT ON COLUMN reviews.comment IS '评审意见和建议的详细文本';
COMMENT ON COLUMN reviews.is_consistent IS '是否与小说设定一致，用于事实核查';
COMMENT ON COLUMN reviews.issues_found IS '发现的问题列表，如["时间线冲突", "角色性格不一致"]';
COMMENT ON COLUMN reviews.created_at IS '评审创建时间，不会更新';

-- Story Arcs Table
CREATE TABLE story_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    start_chapter_number INTEGER,
    end_chapter_number INTEGER,
    status VARCHAR(50) DEFAULT 'PLANNED' CHECK (status IN ('PLANNED', 'ACTIVE', 'COMPLETED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments for story_arcs table
COMMENT ON TABLE story_arcs IS '故事线表，管理小说中的主要情节线索和故事弧';
COMMENT ON COLUMN story_arcs.id IS '故事线唯一标识符';
COMMENT ON COLUMN story_arcs.novel_id IS '所属小说ID，外键关联novels表';
COMMENT ON COLUMN story_arcs.title IS '故事线标题，如"主角觉醒篇"、"魔王讨伐篇"';
COMMENT ON COLUMN story_arcs.summary IS '故事线概要，描述这条线索的主要内容和发展';
COMMENT ON COLUMN story_arcs.start_chapter_number IS '故事线开始的章节号';
COMMENT ON COLUMN story_arcs.end_chapter_number IS '故事线结束的章节号';
COMMENT ON COLUMN story_arcs.status IS '故事线状态：PLANNED(已规划)、ACTIVE(进行中)、COMPLETED(已完成)';
COMMENT ON COLUMN story_arcs.created_at IS '故事线创建时间';
COMMENT ON COLUMN story_arcs.updated_at IS '故事线最后更新时间';

-- Indexes for performance
CREATE INDEX idx_chapters_novel_id ON chapters(novel_id);
CREATE INDEX idx_characters_novel_id ON characters(novel_id);
CREATE INDEX idx_worldview_entries_novel_id ON worldview_entries(novel_id);
CREATE INDEX idx_reviews_chapter_id ON reviews(chapter_id);
CREATE INDEX idx_story_arcs_novel_id ON story_arcs(novel_id);