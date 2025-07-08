-- ================================================
-- 04a-concept-templates.sql
-- 立意模板表定义和初始化数据脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建立意模板表
-- 2. 插入预定义的立意模板示例数据
-- 3. 建立索引和约束
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：02-init-enums.sql（需要枚举类型）
-- ================================================

-- ===========================================
-- 立意模板表 - 存储抽象的哲学立意供用户选择
-- ===========================================
CREATE TABLE concept_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 立意模板的唯一标识符
    core_idea VARCHAR(200) NOT NULL, -- 核心抽象思想
    description VARCHAR(800) NOT NULL, -- 立意的深层含义阐述
    
    -- 哲学维度
    philosophical_depth VARCHAR(1000) NOT NULL, -- 哲学思辨的深度表达
    emotional_core VARCHAR(500) NOT NULL, -- 情感核心与内在冲突
    
    -- 分类标签(抽象层面)
    philosophical_category VARCHAR(100), -- 哲学类别
    thematic_tags JSONB NOT NULL DEFAULT '[]', -- 主题标签数组
    complexity_level VARCHAR(20) NOT NULL DEFAULT 'medium', -- 思辨复杂度
    
    -- 适用性
    universal_appeal BOOLEAN NOT NULL DEFAULT true, -- 是否具有普遍意义
    cultural_specificity VARCHAR(100), -- 文化特异性
    
    -- 元数据
    is_active BOOLEAN NOT NULL DEFAULT true, -- 是否启用
    created_by VARCHAR(50) DEFAULT 'system', -- 创建者
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE concept_templates IS '立意模板表：存储抽象的哲学立意供用户在创世流程中选择和发展';
COMMENT ON COLUMN concept_templates.id IS '立意模板的唯一标识符';
COMMENT ON COLUMN concept_templates.core_idea IS '核心抽象思想，如"知识与无知的深刻对立"';
COMMENT ON COLUMN concept_templates.description IS '立意的深层含义阐述，不超过800字符';
COMMENT ON COLUMN concept_templates.philosophical_depth IS '哲学思辨的深度表达，探讨存在、认知、道德等层面';
COMMENT ON COLUMN concept_templates.emotional_core IS '情感核心与内在冲突，描述人物可能面临的情感挑战';
COMMENT ON COLUMN concept_templates.philosophical_category IS '哲学类别，如"存在主义"、"人道主义"、"理想主义"';
COMMENT ON COLUMN concept_templates.thematic_tags IS '主题标签，如["成长","选择","牺牲","真理"]，JSON数组格式';
COMMENT ON COLUMN concept_templates.complexity_level IS '思辨复杂度：simple, medium, complex';
COMMENT ON COLUMN concept_templates.universal_appeal IS '是否具有普遍意义，跨文化的普适性';
COMMENT ON COLUMN concept_templates.cultural_specificity IS '文化特异性，如"东方哲学"、"西方哲学"、"普世价值"';
COMMENT ON COLUMN concept_templates.is_active IS '是否启用，用于管理可用的立意模板';
COMMENT ON COLUMN concept_templates.created_by IS '创建者，如"system"、"admin"或具体用户';

-- 添加检查约束
ALTER TABLE concept_templates ADD CONSTRAINT check_complexity_level 
    CHECK (complexity_level IN ('simple', 'medium', 'complex'));

ALTER TABLE concept_templates ADD CONSTRAINT check_core_idea_length 
    CHECK (char_length(core_idea) >= 10);

ALTER TABLE concept_templates ADD CONSTRAINT check_description_length 
    CHECK (char_length(description) >= 50);

COMMENT ON CONSTRAINT check_complexity_level ON concept_templates IS '确保复杂度级别为有效值';
COMMENT ON CONSTRAINT check_core_idea_length ON concept_templates IS '确保核心思想不少于10个字符';
COMMENT ON CONSTRAINT check_description_length ON concept_templates IS '确保描述不少于50个字符';

-- 创建索引用于查询优化
CREATE INDEX idx_concept_templates_philosophical_category ON concept_templates(philosophical_category);
CREATE INDEX idx_concept_templates_complexity_level ON concept_templates(complexity_level);
CREATE INDEX idx_concept_templates_universal_appeal ON concept_templates(universal_appeal);
CREATE INDEX idx_concept_templates_is_active ON concept_templates(is_active);
CREATE INDEX idx_concept_templates_cultural_specificity ON concept_templates(cultural_specificity);

-- 创建GIN索引用于主题标签的高效查询
CREATE INDEX idx_concept_templates_thematic_tags ON concept_templates USING GIN(thematic_tags);

-- 创建复合索引用于常见查询场景
CREATE INDEX idx_concept_templates_active_complexity ON concept_templates(is_active, complexity_level);
CREATE INDEX idx_concept_templates_category_appeal ON concept_templates(philosophical_category, universal_appeal);

-- ===========================================
-- 插入预定义的立意模板示例数据
-- ===========================================

INSERT INTO concept_templates (
    core_idea, 
    description, 
    philosophical_depth, 
    emotional_core,
    philosophical_category,
    thematic_tags,
    complexity_level,
    universal_appeal,
    cultural_specificity,
    created_by
) VALUES 

-- 存在主义立意
(
    '存在与虚无的永恒博弈',
    '探讨个体在面对生命本质时的选择与责任。当现实的表象被揭开，人们发现存在本身可能是一种幻象，而真正的自我在这种认知中如何定义自己的价值和意义。',
    '从萨特的"存在先于本质"出发，深入探讨个体在认识到生命无固有意义时，如何通过自由选择创造意义。这种哲学思辨涉及责任、焦虑、真实性等存在主义核心概念。',
    '主人公面临的核心冲突是对虚无的恐惧与对真实存在的渴望之间的张力。这种内在的撕裂产生深刻的孤独感、责任感，以及对选择的焦虑。',
    '存在主义',
    '["存在", "虚无", "选择", "责任", "焦虑", "真实性", "自由"]',
    'complex',
    true,
    '西方哲学',
    'system'
),

-- 认知哲学立意
(
    '知识与无知的深刻对立',
    '当一个人越深入地探索真理，越发现自己的无知。真正的智慧不在于拥有答案，而在于提出正确的问题。这种认知的悖论构成了求知者永恒的困境。',
    '基于苏格拉底的"我知道我无知"，探讨认知的边界和知识的本质。真正的智慧来自于对自己认知局限的深刻理解，以及对未知领域的敬畏与好奇。',
    '求知者在追求真理的过程中体验到的挫折感、谦卑感，以及面对无限未知时的敬畏之情。智慧与愚昧的界限模糊产生的内心冲突。',
    '认知哲学',
    '["知识", "无知", "智慧", "真理", "认知", "学习", "谦卑"]',
    'medium',
    true,
    '普世价值',
    'system'
),

-- 道德伦理立意
(
    '善恶标准的相对性与绝对性',
    '在不同的文化、时代和情境中，善恶的标准似乎在变化，但人类内心深处是否存在一种普遍的道德直觉？当个人的道德判断与社会标准发生冲突时，应该如何选择？',
    '探讨道德相对主义与道德绝对主义的哲学争论。通过具体的道德两难困境，审视人类道德判断的基础，以及个体道德责任与社会伦理规范之间的关系。',
    '道德选择带来的内疚、矛盾、坚持与妥协之间的痛苦挣扎。面对道德两难时的恐惧、愤怒、以及对正义的渴望所产生的情感风暴。',
    '道德哲学',
    '["善恶", "道德", "伦理", "正义", "价值观", "选择", "责任"]',
    'complex',
    true,
    '普世价值',
    'system'
),

-- 时间哲学立意
(
    '时间的循环与线性矛盾',
    '时间是直线前进的历史进程，还是永恒循环的轮回？个体的生命在这种时间观念中如何找到自己的位置和意义？过去、现在、未来的关系如何塑造我们的身份认同？',
    '结合东方的轮回时间观和西方的线性时间观，探讨时间本质对人类意识和行为的深层影响。涉及记忆、预期、当下体验等时间意识的哲学问题。',
    '对时间流逝的焦虑，对过去的眷恋，对未来的恐惧，以及对当下的困惑所交织成的复杂情感体验。时间意识带来的存在焦虑和意义追寻。',
    '时间哲学',
    '["时间", "循环", "线性", "历史", "记忆", "当下", "永恒"]',
    'medium',
    true,
    '东西方融合',
    'system'
),

-- 人性本质立意
(
    '理性与感性的内在冲突',
    '人类既是理性的存在，也是感性的动物。当理智告诉我们一种选择，而情感驱使我们走向另一个方向时，哪一个更能代表真实的自我？这种内在的分裂是人性的缺陷还是丰富性的体现？',
    '从古希腊哲学到现代心理学，探讨理性与感性在人性中的地位和作用。理性的启蒙价值与感性的人文关怀如何在个体生命中达成平衡或产生冲突。',
    '理智与情感的拉扯产生的内心撕裂感，对纯粹理性的向往与对丰富情感的需要之间的矛盾，以及寻求内在和谐的渴望。',
    '人性哲学',
    '["理性", "感性", "人性", "冲突", "平衡", "自我", "和谐"]',
    'medium',
    true,
    '普世价值',
    'system'
),

-- 权力与自由立意
(
    '个体自由与集体秩序的博弈',
    '真正的自由需要什么样的代价？当个人的自由与集体的秩序发生冲突时，如何在不损害他人的前提下追求自己的自由？权力与自由的关系如何影响社会的发展？',
    '探讨政治哲学中的核心问题：自由与秩序的平衡。从霍布斯的利维坦到卢梭的社会契约，审视个体权利与集体责任的哲学基础。',
    '追求自由时的激昂与热忱，面对限制时的愤怒与抗争，以及在集体利益面前的妥协与坚持之间的情感冲突。',
    '政治哲学',
    '["自由", "秩序", "权力", "个体", "集体", "权利", "责任"]',
    'complex',
    true,
    '普世价值',
    'system'
),

-- 生命意义立意
(
    '有限生命中的无限追求',
    '人的生命是有限的，但人的梦想和追求似乎是无限的。如何在有限的时间里实现无限的价值？生命的意义是在于过程还是结果？',
    '探讨生命哲学的核心问题：死亡意识如何影响生命意义的构建。从海德格尔的"向死而生"到加缪的荒诞哲学，审视有限性与超越性的关系。',
    '对死亡的恐惧与对生命的热爱之间的张力，有限感带来的紧迫感与渺小感，以及对永恒价值的渴望与追求。',
    '生命哲学',
    '["生命", "死亡", "有限", "无限", "意义", "价值", "超越"]',
    'complex',
    true,
    '普世价值',
    'system'
),

-- 真理与信仰立意
(
    '科学理性与精神信仰的对话',
    '当科学能够解释越来越多的自然现象时，传统的精神信仰是否还有存在的必要？理性的真理与信仰的真理是否可以共存？现代人如何在科学与信仰之间找到平衡？',
    '探讨科学与宗教、理性与信仰的哲学关系。从启蒙时代的理性主义到后现代的多元主义，审视不同真理观念的合理性和局限性。',
    '理性质疑带来的困惑与解脱，信仰坚持中的温暖与固执，以及在真理追求中的孤独与充实交织的复杂情感。',
    '真理哲学',
    '["真理", "信仰", "科学", "理性", "精神", "宗教", "平衡"]',
    'complex',
    false,
    '现代西方',
    'system'
),

-- 东方哲学立意
(
    '天人合一与个体觉醒的统一',
    '东方哲学强调人与自然的和谐统一，但现代社会中的个体如何在保持这种和谐的同时实现自我觉醒和个性发展？集体和谐与个体成长是否存在内在的冲突？',
    '结合中国古典哲学的天人合一思想和现代个体主义，探讨如何在尊重自然和社会和谐的前提下实现个人的精神成长和自我实现。',
    '对和谐的向往与对个性的坚持之间的矛盾，传统智慧的温暖与现代困惑的碰撞，以及寻求内外统一的渴望。',
    '东方哲学',
    '["天人合一", "和谐", "个体", "觉醒", "自然", "传统", "现代"]',
    'medium',
    false,
    '东方哲学',
    'system'
),

-- 爱与孤独立意
(
    '爱的连接与存在的孤独',
    '每个人本质上都是孤独的存在，但爱能够真正打破这种孤独吗？还是爱只是我们逃避孤独的一种方式？真正的爱需要怎样的理解和接纳？',
    '探讨爱的哲学本质：爱是否能够真正消除人存在的根本孤独，还是只是提供暂时的慰藉。从柏拉图的理念之爱到现代心理学的依恋理论。',
    '对连接的渴望与对孤独的恐惧，爱情中的欣喜与失望，以及在关系中寻找自我认同时的困惑与满足。',
    '爱的哲学',
    '["爱", "孤独", "连接", "理解", "接纳", "关系", "自我"]',
    'simple',
    true,
    '普世价值',
    'system'
);

-- 验证立意模板表创建和数据插入
DO $$
DECLARE
    table_exists BOOLEAN;
    constraint_count INTEGER;
    index_count INTEGER;
    data_count INTEGER;
BEGIN
    -- 检查表是否创建成功
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'concept_templates'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'concept_templates表创建失败';
    END IF;
    
    -- 检查约束数量
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.check_constraints 
    WHERE constraint_schema = 'public' 
    AND constraint_name LIKE '%concept_templates%';
    
    -- 检查索引数量（包括主键索引）
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'concept_templates';
    
    -- 检查数据数量
    SELECT COUNT(*) INTO data_count
    FROM concept_templates;
    
    RAISE NOTICE '立意模板表创建完成：';
    RAISE NOTICE '- concept_templates: 立意模板表';
    RAISE NOTICE '- 已创建%个检查约束确保数据一致性', constraint_count;
    RAISE NOTICE '- 已创建%个索引优化查询性能', index_count;
    RAISE NOTICE '- 已插入%个预定义立意模板', data_count;
    RAISE NOTICE '- 支持哲学分类、复杂度分级和主题标签查询';
    RAISE NOTICE '- 为创世流程的立意选择阶段提供丰富的素材基础';
END $$;