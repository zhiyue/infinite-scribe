-- ================================================
-- 04-genesis-sessions.sql
-- 状态快照表定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建创世会话状态快照表
-- 2. 建立与核心实体表的关联关系
-- 3. 添加必要的约束和索引
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：03-core-entities.sql（需要novels表）
-- ================================================

-- ===========================================
-- 创世会话表 - 作为创世流程的"状态快照"，用于高效查询当前流程的状态
-- ===========================================
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

COMMENT ON TABLE genesis_sessions IS '作为创世流程的"状态快照"，用于高效查询当前流程的状态，其状态由领域事件驱动更新。';
COMMENT ON COLUMN genesis_sessions.id IS '创世会话的唯一标识符';
COMMENT ON COLUMN genesis_sessions.novel_id IS '流程完成后关联的小说ID，外键关联novels表，允许为空（流程未完成时）';
COMMENT ON COLUMN genesis_sessions.user_id IS '发起创世流程的用户ID，用于权限控制和用户关联';
COMMENT ON COLUMN genesis_sessions.status IS '整个创世会话的状态，使用genesis_status枚举';
COMMENT ON COLUMN genesis_sessions.current_stage IS '当前所处的业务阶段，使用genesis_stage枚举';
COMMENT ON COLUMN genesis_sessions.confirmed_data IS '存储每个阶段已确认的最终数据，JSONB格式，包含各阶段的输出结果';
COMMENT ON COLUMN genesis_sessions.version IS '乐观锁版本号，用于并发控制';
COMMENT ON COLUMN genesis_sessions.created_at IS '创世会话创建时间';
COMMENT ON COLUMN genesis_sessions.updated_at IS '创世会话最后更新时间';

-- 添加检查约束确保数据一致性
ALTER TABLE genesis_sessions ADD CONSTRAINT check_genesis_stage_progression 
    CHECK (
        (current_stage = 'CONCEPT_SELECTION' AND status = 'IN_PROGRESS') OR
        (current_stage = 'STORY_CONCEPTION' AND status = 'IN_PROGRESS') OR
        (current_stage = 'WORLDVIEW' AND status = 'IN_PROGRESS') OR
        (current_stage = 'CHARACTERS' AND status = 'IN_PROGRESS') OR
        (current_stage = 'PLOT_OUTLINE' AND status = 'IN_PROGRESS') OR
        (current_stage = 'FINISHED' AND status IN ('COMPLETED', 'ABANDONED'))
    );

COMMENT ON CONSTRAINT check_genesis_stage_progression ON genesis_sessions IS '确保创世阶段和状态的合理组合：只有FINISHED阶段可以有COMPLETED或ABANDONED状态';

-- 添加检查约束确保完成的会话必须关联小说
ALTER TABLE genesis_sessions ADD CONSTRAINT check_completed_has_novel 
    CHECK (
        (status != 'COMPLETED') OR 
        (status = 'COMPLETED' AND novel_id IS NOT NULL)
    );

COMMENT ON CONSTRAINT check_completed_has_novel ON genesis_sessions IS '确保完成状态的创世会话必须关联到一个小说项目';

-- 创建基础索引用于查询优化
CREATE INDEX idx_genesis_sessions_user_id ON genesis_sessions(user_id);
CREATE INDEX idx_genesis_sessions_status ON genesis_sessions(status);
CREATE INDEX idx_genesis_sessions_current_stage ON genesis_sessions(current_stage);
CREATE INDEX idx_genesis_sessions_novel_id ON genesis_sessions(novel_id) WHERE novel_id IS NOT NULL;

-- 创建复合索引用于常见查询场景
CREATE INDEX idx_genesis_sessions_user_status ON genesis_sessions(user_id, status);
CREATE INDEX idx_genesis_sessions_status_stage ON genesis_sessions(status, current_stage);

-- 验证状态快照表创建
DO $$
DECLARE
    table_exists BOOLEAN;
    constraint_count INTEGER;
    index_count INTEGER;
BEGIN
    -- 检查表是否创建成功
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'genesis_sessions'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'genesis_sessions表创建失败';
    END IF;
    
    -- 检查约束数量
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.check_constraints 
    WHERE constraint_schema = 'public' 
    AND constraint_name LIKE '%genesis_sessions%';
    
    -- 检查索引数量（包括主键索引）
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'genesis_sessions';
    
    RAISE NOTICE '状态快照表创建完成：';
    RAISE NOTICE '- genesis_sessions: 创世会话状态快照表';
    RAISE NOTICE '- 已创建%个检查约束确保数据一致性', constraint_count;
    RAISE NOTICE '- 已创建%个索引优化查询性能', index_count;
    RAISE NOTICE '- 支持用户级别的创世流程管理';
    RAISE NOTICE '- 通过领域事件驱动状态更新机制';
END $$;