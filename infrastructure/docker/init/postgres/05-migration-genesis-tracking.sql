-- =====================================================
-- 数据库迁移脚本 - 创世流程追踪表
-- Story 2.1 Task 2: 创建完整的数据库迁移脚本
-- =====================================================

-- ⚠️ 依赖检查：此脚本依赖 03-migration-enums.sql 中定义的ENUM类型
-- 需要的类型：genesis_status, genesis_stage
-- 确保 03-migration-enums.sql 已成功执行

-- 创世流程追踪表：用于跟踪用户创建小说的整个过程

-- 1. 创世会话表：追踪每个创世会话的整体状态
CREATE TABLE IF NOT EXISTS genesis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    user_id UUID,
    status genesis_status NOT NULL DEFAULT 'IN_PROGRESS',
    current_stage genesis_stage NOT NULL DEFAULT 'INITIAL_PROMPT',
    initial_user_input JSONB,
    final_settings JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE genesis_sessions IS '创世会话表：追踪用户创建小说的整个会话过程';
COMMENT ON COLUMN genesis_sessions.id IS '创世会话唯一标识符';
COMMENT ON COLUMN genesis_sessions.novel_id IS '关联的小说ID，外键关联novels表';
COMMENT ON COLUMN genesis_sessions.user_id IS '发起创世的用户ID（预留字段，暂时可为空）';
COMMENT ON COLUMN genesis_sessions.status IS '创世会话状态：IN_PROGRESS(进行中)、COMPLETED(已完成)、ABANDONED(已放弃)';
COMMENT ON COLUMN genesis_sessions.current_stage IS '当前创世阶段：INITIAL_PROMPT(初始提示) -> WORLDVIEW(世界观) -> CHARACTERS(角色) -> PLOT_OUTLINE(剧情大纲) -> FINISHED(完成)';
COMMENT ON COLUMN genesis_sessions.initial_user_input IS '用户最初输入的创世提示词和设定，JSON格式存储';
COMMENT ON COLUMN genesis_sessions.final_settings IS '创世过程完成后的最终设定汇总，JSON格式存储';
COMMENT ON COLUMN genesis_sessions.created_at IS '创世会话开始时间';
COMMENT ON COLUMN genesis_sessions.updated_at IS '创世会话最后更新时间';

-- 2. 创世步骤表：记录创世过程中的每个具体步骤
CREATE TABLE IF NOT EXISTS genesis_steps (
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

COMMENT ON TABLE genesis_steps IS '创世步骤表：记录创世过程中每个阶段的具体交互步骤';
COMMENT ON COLUMN genesis_steps.id IS '创世步骤唯一标识符';
COMMENT ON COLUMN genesis_steps.session_id IS '所属创世会话ID，外键关联genesis_sessions表';
COMMENT ON COLUMN genesis_steps.stage IS '当前步骤所属的创世阶段';
COMMENT ON COLUMN genesis_steps.iteration_count IS '在当前阶段的迭代次数（从1开始）';
COMMENT ON COLUMN genesis_steps.ai_prompt IS 'AI生成内容时使用的提示词';
COMMENT ON COLUMN genesis_steps.ai_output IS 'AI生成的输出内容，JSON格式存储（如世界观要素、角色设定等）';
COMMENT ON COLUMN genesis_steps.user_feedback IS '用户对AI输出的反馈意见';
COMMENT ON COLUMN genesis_steps.is_confirmed IS '用户是否确认此步骤的结果（true表示用户满意并继续下一步）';
COMMENT ON COLUMN genesis_steps.created_at IS '步骤创建时间';

-- 3. 创建基本索引
CREATE INDEX IF NOT EXISTS idx_genesis_sessions_novel_id ON genesis_sessions(novel_id);
CREATE INDEX IF NOT EXISTS idx_genesis_sessions_status ON genesis_sessions(status);
CREATE INDEX IF NOT EXISTS idx_genesis_sessions_current_stage ON genesis_sessions(current_stage);

CREATE INDEX IF NOT EXISTS idx_genesis_steps_session_id ON genesis_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_genesis_steps_stage ON genesis_steps(stage);
CREATE INDEX IF NOT EXISTS idx_genesis_steps_confirmed ON genesis_steps(is_confirmed);
CREATE INDEX IF NOT EXISTS idx_genesis_steps_session_stage ON genesis_steps(session_id, stage, iteration_count);

-- 4. 添加数据完整性约束

-- 确保iteration_count从1开始
ALTER TABLE genesis_steps 
    ADD CONSTRAINT check_iteration_count_positive 
    CHECK (iteration_count > 0);

-- 确保会话状态转换的逻辑合理性（通过触发器实现复杂约束）
CREATE OR REPLACE FUNCTION validate_genesis_session_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果状态从 IN_PROGRESS 变为 COMPLETED，确保 current_stage 为 FINISHED
    IF OLD.status = 'IN_PROGRESS' AND NEW.status = 'COMPLETED' AND NEW.current_stage != 'FINISHED' THEN
        RAISE EXCEPTION '创世会话只有在current_stage为FINISHED时才能标记为COMPLETED';
    END IF;
    
    -- 如果状态为 COMPLETED，不允许再修改为其他状态
    IF OLD.status = 'COMPLETED' AND NEW.status != 'COMPLETED' THEN
        RAISE EXCEPTION '已完成的创世会话状态不能被修改';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_genesis_session_status
    BEFORE UPDATE ON genesis_sessions
    FOR EACH ROW
    EXECUTE FUNCTION validate_genesis_session_status_transition();

-- 5. 用于创世流程管理的辅助函数

-- 获取创世会话的当前进度
CREATE OR REPLACE FUNCTION get_genesis_progress(session_uuid UUID)
RETURNS TABLE (
    session_id UUID,
    novel_title VARCHAR(255),
    current_stage genesis_stage,
    status genesis_status,
    completed_steps_count INTEGER,
    last_step_time TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gs.id,
        n.title,
        gs.current_stage,
        gs.status,
        COUNT(gst.id)::INTEGER as completed_steps_count,
        MAX(gst.created_at) as last_step_time
    FROM genesis_sessions gs
    JOIN novels n ON gs.novel_id = n.id
    LEFT JOIN genesis_steps gst ON gs.id = gst.session_id AND gst.is_confirmed = true
    WHERE gs.id = session_uuid
    GROUP BY gs.id, n.title, gs.current_stage, gs.status;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_genesis_progress(UUID) IS '获取指定创世会话的详细进度信息';