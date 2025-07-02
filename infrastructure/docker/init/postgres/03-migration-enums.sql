-- =====================================================
-- 数据库迁移脚本 - ENUM类型定义
-- Story 2.1 Task 2: 创建完整的数据库迁移脚本
-- =====================================================

-- 确保必要的扩展已安装（防止单独运行此脚本时缺少依赖）
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ENUM 类型定义 (按依赖顺序)
-- 这些ENUM类型为数据库提供强类型约束，确保数据一致性

-- Agent类型：定义系统中所有AI智能体的类型
CREATE TYPE agent_type AS ENUM (
    'worldsmith',       -- 世界铸造师：负责创建世界观框架
    'plotmaster',       -- 剧情策划师：负责整体剧情规划
    'outliner',         -- 大纲规划师：负责章节大纲规划
    'director',         -- 导演：负责场景设计和节奏控制
    'character_expert', -- 角色专家：负责角色设计和发展
    'worldbuilder',     -- 世界观构建师：负责详细世界观建设
    'writer',           -- 作家：负责实际内容创作
    'critic',           -- 评论家：负责内容评估和质量控制
    'fact_checker',     -- 事实核查员：负责逻辑一致性检查
    'rewriter'          -- 改写者：负责内容修订和优化
);

COMMENT ON TYPE agent_type IS 'AI智能体类型：定义系统中所有智能体的职责分工';

-- 活动状态：定义Agent活动的执行状态
CREATE TYPE activity_status AS ENUM (
    'STARTED',      -- 已开始：活动刚刚启动
    'IN_PROGRESS',  -- 进行中：活动正在执行
    'COMPLETED',    -- 已完成：活动成功完成
    'FAILED',       -- 失败：活动执行失败
    'RETRYING'      -- 重试中：活动失败后正在重试
);

COMMENT ON TYPE activity_status IS 'Agent活动执行状态：追踪每个Agent任务的执行状态';

-- 工作流状态：定义工作流运行的状态
CREATE TYPE workflow_status AS ENUM (
    'PENDING',    -- 等待中：工作流已创建但未开始
    'RUNNING',    -- 运行中：工作流正在执行
    'COMPLETED',  -- 已完成：工作流成功完成
    'FAILED',     -- 失败：工作流执行失败
    'CANCELLED',  -- 已取消：工作流被手动取消
    'PAUSED'      -- 已暂停：工作流被暂停，可恢复
);

COMMENT ON TYPE workflow_status IS '工作流执行状态：追踪复杂业务流程的整体状态';

-- 事件状态：定义事件的处理状态
CREATE TYPE event_status AS ENUM (
    'PENDING',     -- 等待处理：事件已创建但未处理
    'PROCESSING',  -- 处理中：事件正在被处理
    'PROCESSED',   -- 已处理：事件处理完成
    'FAILED',      -- 处理失败：事件处理过程中出错
    'DEAD_LETTER'  -- 死信：事件多次处理失败，进入死信队列
);

COMMENT ON TYPE event_status IS '事件处理状态：追踪事件驱动系统中消息的处理状态';

-- 小说状态：定义小说项目的生命周期状态
CREATE TYPE novel_status AS ENUM (
    'GENESIS',    -- 创世中：小说正在创建初始设定
    'GENERATING', -- 生成中：小说正在生成内容
    'PAUSED',     -- 已暂停：小说生成被暂停
    'COMPLETED',  -- 已完成：小说创作完成
    'FAILED'      -- 失败：小说创作失败
);

COMMENT ON TYPE novel_status IS '小说项目状态：追踪小说从创建到完成的整个生命周期';

-- 章节状态：定义章节的编辑状态
CREATE TYPE chapter_status AS ENUM (
    'DRAFT',      -- 草稿：章节初稿
    'REVIEWING',  -- 审查中：章节正在被评审
    'REVISING',   -- 修订中：章节正在被修改
    'PUBLISHED'   -- 已发布：章节已经发布
);

COMMENT ON TYPE chapter_status IS '章节编辑状态：追踪章节从草稿到发布的编辑流程';

-- 创世状态：定义创世会话的状态
CREATE TYPE genesis_status AS ENUM (
    'IN_PROGRESS', -- 进行中：创世过程正在进行
    'COMPLETED',   -- 已完成：创世过程完成
    'ABANDONED'    -- 已放弃：创世过程被用户放弃
);

COMMENT ON TYPE genesis_status IS '创世会话状态：追踪用户创建小说的整个过程状态';

-- 创世阶段：定义创世过程的具体阶段
CREATE TYPE genesis_stage AS ENUM (
    'INITIAL_PROMPT', -- 初始提示：用户输入初始想法
    'WORLDVIEW',      -- 世界观：构建世界观设定
    'CHARACTERS',     -- 角色：设计主要角色
    'PLOT_OUTLINE',   -- 剧情大纲：制定整体剧情框架
    'FINISHED'        -- 完成：创世过程结束
);

COMMENT ON TYPE genesis_stage IS '创世过程阶段：定义用户创建小说时的具体步骤';