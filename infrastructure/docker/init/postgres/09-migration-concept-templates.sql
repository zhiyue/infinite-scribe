-- =====================================================
-- 数据库迁移脚本 - 立意模板功能
-- 支持新的创世流程：立意选择 -> 故事构思 -> 世界观设计
-- =====================================================

-- ⚠️ 依赖检查：此脚本依赖已有的 ENUM 类型和表结构
-- 需要更新 genesis_stage 枚举类型以支持新的创世流程

-- 1. 更新创世阶段枚举，支持新的立意选择流程
-- 由于 PostgreSQL 不支持直接修改枚举，需要创建新类型并替换

-- 创建新的创世阶段枚举
CREATE TYPE genesis_stage_new AS ENUM (
    'CONCEPT_SELECTION',  -- 立意选择与迭代阶段：用户从AI生成的抽象立意中选择并优化
    'STORY_CONCEPTION',   -- 故事构思阶段：将确认的立意转化为具体故事框架
    'WORLDVIEW',          -- 世界观创建阶段：基于故事构思设计详细世界观
    'CHARACTERS',         -- 角色设定阶段：设计主要角色
    'PLOT_OUTLINE',       -- 情节大纲阶段：制定整体剧情框架
    'FINISHED'            -- 完成阶段：创世过程结束
);

COMMENT ON TYPE genesis_stage_new IS '创世过程阶段（新版）：定义用户创建小说时的具体步骤，包含立意选择和故事构思阶段';

-- 2. 创建立意模板表：存储AI生成的抽象哲学立意供用户选择
CREATE TABLE IF NOT EXISTS concept_templates (
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

COMMENT ON TABLE concept_templates IS '立意模板表：存储AI生成的抽象哲学立意，供用户选择和复用';
COMMENT ON COLUMN concept_templates.id IS '立意模板唯一标识符';
COMMENT ON COLUMN concept_templates.core_idea IS '核心抽象思想，如"知识与无知的深刻对立"';
COMMENT ON COLUMN concept_templates.description IS '立意的深层含义阐述';
COMMENT ON COLUMN concept_templates.philosophical_depth IS '哲学思辨的深度表达';
COMMENT ON COLUMN concept_templates.emotional_core IS '情感核心与内在冲突';
COMMENT ON COLUMN concept_templates.philosophical_category IS '哲学类别，如"存在主义"、"人道主义"、"理想主义"';
COMMENT ON COLUMN concept_templates.thematic_tags IS '主题标签数组，如["成长","选择","牺牲","真理"]';
COMMENT ON COLUMN concept_templates.complexity_level IS '思辨复杂度：simple(简单)、medium(中等)、complex(复杂)';
COMMENT ON COLUMN concept_templates.universal_appeal IS '是否具有普遍意义';
COMMENT ON COLUMN concept_templates.cultural_specificity IS '文化特异性，如"东方哲学"、"西方哲学"、"普世价值"';
COMMENT ON COLUMN concept_templates.usage_count IS '被选择使用的次数统计';
COMMENT ON COLUMN concept_templates.rating_sum IS '用户评分总和（用于计算平均分）';
COMMENT ON COLUMN concept_templates.rating_count IS '评分人数';
COMMENT ON COLUMN concept_templates.is_active IS '是否启用（用于软删除）';
COMMENT ON COLUMN concept_templates.created_by IS '创建者，如"system"、"admin"';

-- 3. 更新现有表以使用新的枚举类型
-- 备份当前数据（以防万一）
-- 注意：在生产环境中，这个操作需要更谨慎的处理

-- 更新 genesis_sessions 表
ALTER TABLE genesis_sessions 
    ALTER COLUMN current_stage DROP DEFAULT,
    ALTER COLUMN current_stage TYPE genesis_stage_new USING 
        CASE current_stage::text
            WHEN 'INITIAL_PROMPT' THEN 'CONCEPT_SELECTION'::genesis_stage_new
            ELSE current_stage::text::genesis_stage_new
        END,
    ALTER COLUMN current_stage SET DEFAULT 'CONCEPT_SELECTION'::genesis_stage_new;

-- 更新 genesis_steps 表
ALTER TABLE genesis_steps
    ALTER COLUMN stage TYPE genesis_stage_new USING
        CASE stage::text
            WHEN 'INITIAL_PROMPT' THEN 'CONCEPT_SELECTION'::genesis_stage_new
            ELSE stage::text::genesis_stage_new
        END;

-- 删除旧的枚举类型
DROP TYPE genesis_stage;

-- 重命名新枚举类型
ALTER TYPE genesis_stage_new RENAME TO genesis_stage;

-- 更新表注释以反映新的阶段流程
COMMENT ON COLUMN genesis_sessions.current_stage IS '当前创世阶段：CONCEPT_SELECTION(立意选择) -> STORY_CONCEPTION(故事构思) -> WORLDVIEW(世界观) -> CHARACTERS(角色) -> PLOT_OUTLINE(剧情大纲) -> FINISHED(完成)';

-- 4. 创建索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_concept_templates_philosophical_category 
    ON concept_templates(philosophical_category) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_concept_templates_complexity_level 
    ON concept_templates(complexity_level) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_concept_templates_thematic_tags 
    ON concept_templates USING GIN(thematic_tags) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_concept_templates_usage_count 
    ON concept_templates(usage_count DESC) 
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_concept_templates_rating 
    ON concept_templates((rating_sum::float / NULLIF(rating_count, 0)) DESC NULLS LAST) 
    WHERE is_active = true AND rating_count > 0;

CREATE INDEX IF NOT EXISTS idx_genesis_sessions_stage_status 
    ON genesis_sessions(current_stage, status) 
    WHERE status = 'IN_PROGRESS';

-- 5. 插入一些初始立意模板数据（用于测试和演示）
INSERT INTO concept_templates (
    core_idea, 
    description, 
    philosophical_depth, 
    emotional_core, 
    philosophical_category, 
    thematic_tags, 
    complexity_level, 
    created_by
) VALUES 
(
    '知识与无知的深刻对立',
    '探讨知识如何改变一个人的命运，以及无知所带来的悲剧与痛苦。当个体获得超越同辈的认知时，反而可能陷入更深的孤独。',
    '当个体获得超越同辈的知识时，他将面临孤独与责任的双重考验。真正的智慧不在于知识的多少，而在于理解知识的局限性。',
    '理解与被理解之间的渴望与隔阂，求知者的孤独与使命感',
    '认识论',
    '{"知识", "孤独", "责任", "成长"}',
    'medium',
    'system'
),
(
    '个体意志与集体命运的冲突',
    '个人的选择如何影响整个群体，以及个体在集体利益面前的道德抉择。探讨自由意志与社会责任之间的平衡。',
    '真正的英雄主义不在于力量，而在于在关键时刻做出正确选择的勇气。个体的价值在于能否在关键时刻承担起历史的重量。',
    '为了他人的幸福而牺牲自我的内心挣扎与升华',
    '道德哲学',
    '{"选择", "牺牲", "正义", "责任"}',
    'complex',
    'system'
),
(
    '成长中的代价与收获',
    '探讨成长过程中必须失去什么才能获得什么，以及这种交换的意义。每一次成长都伴随着某种形式的告别。',
    '真正的成熟来自于接受生活中无法改变的事实，同时保持改变可以改变事物的勇气。成长的本质是学会在失去中寻找意义。',
    '告别童真时的不舍与对未来的既期待又恐惧',
    '存在主义',
    '{"成长", "失去", "接受", "勇气"}',
    'medium',
    'system'
),
(
    '真实与虚假的界限模糊',
    '在信息时代，真相变得愈发难以辨识。探讨什么是真实，什么是虚假，以及这种模糊带来的恐惧与解脱。',
    '当现实与虚幻的界限变得模糊时，人们开始质疑一切，包括自己的存在。真实可能不在于客观事实，而在于主观体验的意义。',
    '对真相的渴望与对真相的恐惧并存',
    '后现代主义',
    '{"真实", "虚假", "认知", "怀疑"}',
    'complex',
    'system'
),
(
    '时间的不可逆与记忆的重构',
    '时间只能向前流淌，但记忆却可以被不断重新诠释。探讨过去、现在、未来之间的复杂关系。',
    '人类通过不断重新解读过去来重新定义自己，但这种重构本身也成为了新的束缚。时间的意义不在于流逝，而在于选择。',
    '对过去的眷恋与对未来的不确定性',
    '时间哲学',
    '{"时间", "记忆", "过去", "选择"}',
    'medium',
    'system'
);

-- 6. 创建触发器以自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_concept_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_concept_templates_updated_at
    BEFORE UPDATE ON concept_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_concept_templates_updated_at();

-- 7. 创建辅助函数计算平均评分
CREATE OR REPLACE FUNCTION get_concept_template_average_rating(template_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    avg_rating NUMERIC;
BEGIN
    SELECT 
        CASE 
            WHEN rating_count = 0 THEN NULL
            ELSE ROUND(rating_sum::NUMERIC / rating_count, 2)
        END
    INTO avg_rating
    FROM concept_templates
    WHERE id = template_id;
    
    RETURN avg_rating;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_concept_template_average_rating(UUID) IS '计算指定立意模板的平均评分';

-- 迁移完成提示
DO $$
BEGIN
    RAISE NOTICE '✅ 立意模板功能迁移已完成';
    RAISE NOTICE '📋 已创建 concept_templates 表';
    RAISE NOTICE '🔄 已更新 genesis_stage 枚举，新增 CONCEPT_SELECTION 和 STORY_CONCEPTION 阶段';
    RAISE NOTICE '📊 已插入 % 个初始立意模板', (SELECT COUNT(*) FROM concept_templates);
    RAISE NOTICE '⚡ 已创建相关索引和触发器';
END $$;