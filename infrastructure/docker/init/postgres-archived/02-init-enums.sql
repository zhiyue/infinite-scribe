-- ================================================
-- 02-init-enums.sql
-- 枚举类型定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建所有系统使用的枚举类型
-- 2. 为各种状态和类型字段提供严格的约束
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：01-init-functions.sql
-- ================================================

-- Agent类型枚举 - 定义系统中所有AI智能体的类型
CREATE TYPE agent_type AS ENUM (
    'worldsmith',     -- 世界构建师：负责世界观设定
    'plotmaster',     -- 情节大师：负责主线剧情规划
    'outliner',       -- 大纲师：负责章节大纲制作
    'director',       -- 导演：负责场景编排
    'character_expert', -- 角色专家：负责角色设定和发展
    'worldbuilder',   -- 世界建设者：负责世界观细节
    'writer',         -- 作家：负责具体内容写作
    'critic',         -- 评论家：负责内容质量评审
    'fact_checker',   -- 事实核查员：负责逻辑一致性检查
    'rewriter'        -- 重写师：负责内容修改和优化
);

COMMENT ON TYPE agent_type IS 'AI智能体类型枚举，定义系统中各种专业化智能体的角色';

-- 小说状态枚举 - 定义小说项目的生命周期状态
CREATE TYPE novel_status AS ENUM (
    'GENESIS',        -- 创世阶段：正在进行初始设定
    'GENERATING',     -- 生成阶段：正在生成章节内容
    'PAUSED',         -- 暂停状态：用户主动暂停或系统暂停
    'COMPLETED',      -- 完成状态：小说创作完成
    'FAILED'          -- 失败状态：因错误或其他原因无法继续
);

COMMENT ON TYPE novel_status IS '小说项目状态枚举，追踪整个创作流程的进展';

-- 章节状态枚举 - 定义单个章节的工作流状态
CREATE TYPE chapter_status AS ENUM (
    'DRAFT',          -- 草稿：初始创作状态
    'REVIEWING',      -- 审查中：正在进行质量评审
    'REVISING',       -- 修订中：根据评审意见进行修改
    'PUBLISHED'       -- 已发布：章节完成并对外可见
);

COMMENT ON TYPE chapter_status IS '章节工作流状态枚举，管理单个章节的创作进度';

-- 命令状态枚举 - 定义异步命令处理的状态
CREATE TYPE command_status AS ENUM (
    'RECEIVED',       -- 已接收：命令已进入处理队列
    'PROCESSING',     -- 处理中：命令正在执行
    'COMPLETED',      -- 已完成：命令执行成功
    'FAILED'          -- 执行失败：命令执行出错
);

COMMENT ON TYPE command_status IS '命令处理状态枚举，用于异步命令的生命周期管理';

-- 任务状态枚举 - 定义后台异步任务的执行状态
CREATE TYPE task_status AS ENUM (
    'PENDING',        -- 待执行：任务已创建但未开始
    'RUNNING',        -- 运行中：任务正在执行
    'COMPLETED',      -- 已完成：任务执行成功
    'FAILED',         -- 执行失败：任务执行出错
    'CANCELLED'       -- 已取消：任务被用户或系统取消
);

COMMENT ON TYPE task_status IS '异步任务状态枚举，追踪后台任务的执行进度';

-- 发件箱状态枚举 - 定义事件发布的状态
CREATE TYPE outbox_status AS ENUM (
    'PENDING',        -- 待发送：事件待发布到消息队列
    'SENT'            -- 已发送：事件已成功发布
);

COMMENT ON TYPE outbox_status IS '事件发件箱状态枚举，确保事件发布的可靠性';

-- 工作流恢复句柄状态枚举 - 定义Prefect工作流暂停/恢复的状态
CREATE TYPE handle_status AS ENUM (
    'PENDING_PAUSE',  -- 等待暂停：工作流即将暂停
    'PAUSED',         -- 已暂停：工作流处于暂停状态
    'RESUMED',        -- 已恢复：工作流恢复执行
    'EXPIRED'         -- 已过期：恢复句柄超时失效
);

COMMENT ON TYPE handle_status IS '工作流恢复句柄状态枚举，管理Prefect工作流的暂停和恢复';

-- 创世会话状态枚举 - 定义创世流程的整体状态
CREATE TYPE genesis_status AS ENUM (
    'IN_PROGRESS',    -- 进行中：创世流程正在执行
    'COMPLETED',      -- 已完成：创世流程成功完成
    'ABANDONED'       -- 已放弃：用户放弃或流程异常终止
);

COMMENT ON TYPE genesis_status IS '创世会话状态枚举，追踪整个创世流程的进展';

-- 创世阶段枚举 - 定义创世流程中的具体业务阶段
CREATE TYPE genesis_stage AS ENUM (
    'CONCEPT_SELECTION',  -- 立意选择：选择小说的核心概念和主题
    'STORY_CONCEPTION',   -- 故事构思：基于选定立意进行故事构思
    'WORLDVIEW',          -- 世界观设定：构建小说的世界观体系
    'CHARACTERS',         -- 角色设定：创建和完善主要角色
    'PLOT_OUTLINE',       -- 情节大纲：制定整体情节结构
    'FINISHED'            -- 已完成：创世流程全部完成
);

COMMENT ON TYPE genesis_stage IS '创世流程阶段枚举，定义创世过程中的业务里程碑';

-- 世界观条目类型枚举 - 定义世界观设定中各种元素的类型
CREATE TYPE worldview_entry_type AS ENUM (
    'LOCATION',      -- 地点：地理位置、城市、建筑等
    'ORGANIZATION',  -- 组织：机构、团体、势力等
    'TECHNOLOGY',    -- 科技：技术体系、工具、武器等
    'LAW',          -- 法则：自然法则、魔法规则、社会制度等
    'CONCEPT',      -- 概念：抽象概念、哲学思想等
    'EVENT',        -- 事件：历史事件、传说故事等
    'ITEM',         -- 物品：重要物品、神器、道具等
    'CULTURE',      -- 文化：风俗习惯、宗教信仰等
    'SPECIES',      -- 种族：人种、种族、生物等
    'OTHER'         -- 其他：未分类的设定元素
);

COMMENT ON TYPE worldview_entry_type IS '世界观条目类型枚举，用于严格约束世界观设定元素的分类';

-- 验证枚举类型创建
DO $$
DECLARE
    enum_count INTEGER;
BEGIN
    -- 统计创建的枚举类型数量
    SELECT COUNT(*) INTO enum_count
    FROM pg_type 
    WHERE typname IN (
        'agent_type', 'novel_status', 'chapter_status', 'command_status',
        'task_status', 'outbox_status', 'handle_status', 'genesis_status', 
        'genesis_stage', 'worldview_entry_type'
    );
    
    IF enum_count != 10 THEN
        RAISE EXCEPTION '枚举类型创建不完整，期望10个，实际创建%个', enum_count;
    END IF;
    
    RAISE NOTICE '枚举类型创建完成：';
    RAISE NOTICE '- agent_type: AI智能体类型（10个值）';
    RAISE NOTICE '- novel_status: 小说状态（5个值）';
    RAISE NOTICE '- chapter_status: 章节状态（4个值）';
    RAISE NOTICE '- command_status: 命令状态（4个值）';
    RAISE NOTICE '- task_status: 任务状态（5个值）';
    RAISE NOTICE '- outbox_status: 发件箱状态（2个值）';
    RAISE NOTICE '- handle_status: 句柄状态（4个值）';
    RAISE NOTICE '- genesis_status: 创世状态（3个值）';
    RAISE NOTICE '- genesis_stage: 创世阶段（6个值）';
    RAISE NOTICE '- worldview_entry_type: 世界观条目类型（10个值）';
END $$;