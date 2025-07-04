-- ================================================
-- 09-flow-resume-handles.sql
-- 工作流恢复句柄表定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建工作流恢复句柄持久化表
-- 2. 支持Prefect工作流的暂停和恢复机制
-- 3. 提供缓存失效时的容错处理
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：02-init-enums.sql（需要handle_status枚举）
-- ================================================

-- ===========================================
-- 工作流恢复句柄表 - 持久化存储Prefect工作流的暂停/恢复句柄，确保系统容错性
-- ===========================================
CREATE TABLE flow_resume_handles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 句柄记录ID
    correlation_id TEXT NOT NULL, -- 用于查找的关联ID (如task_id, command_id)
    flow_run_id TEXT, -- Prefect工作流运行ID
    task_name TEXT, -- 暂停的任务名称
    resume_handle JSONB NOT NULL, -- Prefect提供的、用于恢复的完整JSON对象
    status handle_status NOT NULL DEFAULT 'PENDING_PAUSE', -- 回调句柄的状态
    resume_payload JSONB, -- 用于存储提前到达的恢复数据，解决竞态条件
    timeout_seconds INTEGER, -- 句柄超时时间（秒）
    context_data JSONB, -- 额外的上下文信息
    expires_at TIMESTAMPTZ, -- 过期时间
    resumed_at TIMESTAMPTZ, -- 实际恢复时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE flow_resume_handles IS '持久化存储Prefect工作流的暂停/恢复句柄，以应对缓存失效，确保系统容错性。';
COMMENT ON COLUMN flow_resume_handles.id IS '句柄记录的唯一标识符';
COMMENT ON COLUMN flow_resume_handles.correlation_id IS '关联ID，用于将句柄与业务实体关联，如task_id或command_id';
COMMENT ON COLUMN flow_resume_handles.flow_run_id IS 'Prefect工作流运行的唯一标识符';
COMMENT ON COLUMN flow_resume_handles.task_name IS '暂停的任务名称，便于识别和调试';
COMMENT ON COLUMN flow_resume_handles.resume_handle IS 'Prefect提供的完整恢复句柄，JSONB格式，包含恢复工作流所需的所有信息';
COMMENT ON COLUMN flow_resume_handles.status IS '句柄状态，使用handle_status枚举';
COMMENT ON COLUMN flow_resume_handles.resume_payload IS '提前到达的恢复数据，用于解决时序竞态条件';
COMMENT ON COLUMN flow_resume_handles.timeout_seconds IS '句柄的超时时间（秒），超时后自动标记为过期';
COMMENT ON COLUMN flow_resume_handles.context_data IS '额外的上下文信息，JSONB格式，包含恢复时可能需要的业务数据';
COMMENT ON COLUMN flow_resume_handles.expires_at IS '句柄过期时间，超过此时间的句柄将无法使用';
COMMENT ON COLUMN flow_resume_handles.resumed_at IS '实际恢复工作流的时间戳';
COMMENT ON COLUMN flow_resume_handles.created_at IS '句柄记录创建时间';
COMMENT ON COLUMN flow_resume_handles.updated_at IS '句柄记录最后更新时间';

-- 创建唯一索引确保活跃句柄的唯一性：同一correlation_id在活跃状态下只能有一个句柄
CREATE UNIQUE INDEX idx_flow_resume_handles_unique_correlation 
    ON flow_resume_handles (correlation_id) 
    WHERE status IN ('PENDING_PAUSE', 'PAUSED');

COMMENT ON INDEX idx_flow_resume_handles_unique_correlation IS '确保同一关联ID在活跃状态下只能有一个恢复句柄';

-- 创建核心查询索引
CREATE INDEX idx_flow_resume_handles_correlation_id ON flow_resume_handles(correlation_id);
CREATE INDEX idx_flow_resume_handles_status ON flow_resume_handles(status);
CREATE INDEX idx_flow_resume_handles_flow_run_id ON flow_resume_handles(flow_run_id) WHERE flow_run_id IS NOT NULL;
CREATE INDEX idx_flow_resume_handles_expires_at ON flow_resume_handles(expires_at) WHERE expires_at IS NOT NULL;

-- 复合索引用于常见查询场景
CREATE INDEX idx_flow_resume_handles_status_expires ON flow_resume_handles(status, expires_at);
CREATE INDEX idx_flow_resume_handles_correlation_status ON flow_resume_handles(correlation_id, status);

-- JSONB字段的GIN索引用于复杂查询
CREATE INDEX idx_flow_resume_handles_resume_handle_gin ON flow_resume_handles USING GIN (resume_handle);
CREATE INDEX idx_flow_resume_handles_context_data_gin ON flow_resume_handles USING GIN (context_data);

-- 添加检查约束确保数据完整性
ALTER TABLE flow_resume_handles ADD CONSTRAINT check_timeout_positive 
    CHECK (timeout_seconds IS NULL OR timeout_seconds > 0);

ALTER TABLE flow_resume_handles ADD CONSTRAINT check_expires_after_created 
    CHECK (expires_at IS NULL OR expires_at > created_at);

ALTER TABLE flow_resume_handles ADD CONSTRAINT check_resumed_has_timestamp 
    CHECK (
        (status != 'RESUMED') OR 
        (status = 'RESUMED' AND resumed_at IS NOT NULL)
    );

ALTER TABLE flow_resume_handles ADD CONSTRAINT check_paused_has_handle 
    CHECK (
        (status NOT IN ('PAUSED', 'RESUMED')) OR 
        (status IN ('PAUSED', 'RESUMED') AND resume_handle IS NOT NULL)
    );

COMMENT ON CONSTRAINT check_timeout_positive ON flow_resume_handles IS '确保超时时间为正数';
COMMENT ON CONSTRAINT check_expires_after_created ON flow_resume_handles IS '确保过期时间晚于创建时间';
COMMENT ON CONSTRAINT check_resumed_has_timestamp ON flow_resume_handles IS '确保已恢复的句柄有恢复时间戳';
COMMENT ON CONSTRAINT check_paused_has_handle ON flow_resume_handles IS '确保暂停或已恢复的句柄包含恢复数据';

-- 创建获取可恢复句柄的函数
CREATE OR REPLACE FUNCTION get_resumable_handle(correlation_key TEXT)
RETURNS TABLE(
    id UUID,
    resume_handle JSONB,
    resume_payload JSONB,
    context_data JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        frh.id,
        frh.resume_handle,
        frh.resume_payload,
        frh.context_data
    FROM flow_resume_handles frh
    WHERE frh.correlation_id = correlation_key
    AND frh.status = 'PAUSED'
    AND (frh.expires_at IS NULL OR frh.expires_at > NOW())
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_resumable_handle(TEXT) IS '根据关联ID获取可恢复的句柄信息';

-- 创建标记句柄为已恢复的函数
CREATE OR REPLACE FUNCTION mark_handle_resumed(handle_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE flow_resume_handles 
    SET status = 'RESUMED', 
        resumed_at = NOW(),
        updated_at = NOW()
    WHERE id = handle_id 
    AND status = 'PAUSED'
    AND (expires_at IS NULL OR expires_at > NOW());
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mark_handle_resumed(UUID) IS '标记句柄为已恢复状态';

-- 创建存储恢复数据的函数（用于处理竞态条件）
CREATE OR REPLACE FUNCTION store_resume_payload(correlation_key TEXT, payload_data JSONB)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- 如果句柄还未暂停，先存储恢复数据
    UPDATE flow_resume_handles 
    SET resume_payload = payload_data,
        updated_at = NOW()
    WHERE correlation_id = correlation_key 
    AND status IN ('PENDING_PAUSE', 'PAUSED')
    AND (expires_at IS NULL OR expires_at > NOW());
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION store_resume_payload(TEXT, JSONB) IS '存储恢复数据，用于处理时序竞态条件';

-- 创建清理过期句柄的函数
CREATE OR REPLACE FUNCTION cleanup_expired_handles()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    -- 将过期的句柄标记为EXPIRED
    UPDATE flow_resume_handles 
    SET status = 'EXPIRED',
        updated_at = NOW()
    WHERE status IN ('PENDING_PAUSE', 'PAUSED')
    AND expires_at IS NOT NULL 
    AND expires_at <= NOW();
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RAISE NOTICE '已标记%个过期的工作流恢复句柄', updated_count;
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_handles() IS '清理过期的工作流恢复句柄';

-- 创建删除旧记录的函数
CREATE OR REPLACE FUNCTION delete_old_resume_handles()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 删除7天前已恢复或过期的句柄记录
    DELETE FROM flow_resume_handles 
    WHERE status IN ('RESUMED', 'EXPIRED') 
    AND updated_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '已删除%个旧的工作流恢复句柄记录', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION delete_old_resume_handles() IS '删除7天前已恢复或过期的句柄记录';

-- 创建工作流恢复句柄统计视图
CREATE VIEW flow_resume_handle_statistics AS
SELECT 
    status,
    COUNT(*) as handle_count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(resumed_at, updated_at) - created_at))) as avg_lifetime_seconds,
    MIN(created_at) as earliest_handle,
    MAX(created_at) as latest_handle
FROM flow_resume_handles
GROUP BY status;

COMMENT ON VIEW flow_resume_handle_statistics IS '工作流恢复句柄统计视图，提供按状态的句柄统计信息';

-- 验证工作流恢复句柄表创建
DO $$
DECLARE
    table_exists BOOLEAN;
    unique_index_count INTEGER;
    regular_index_count INTEGER;
    constraint_count INTEGER;
    function_count INTEGER;
BEGIN
    -- 检查表是否创建成功
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'flow_resume_handles'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'flow_resume_handles表创建失败';
    END IF;
    
    -- 检查唯一索引数量
    SELECT COUNT(*) INTO unique_index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'flow_resume_handles'
    AND indexdef LIKE '%UNIQUE%';
    
    -- 检查常规索引数量
    SELECT COUNT(*) INTO regular_index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'flow_resume_handles';
    
    -- 检查约束数量
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.check_constraints 
    WHERE constraint_schema = 'public' 
    AND constraint_name LIKE '%flow_resume_handles%';
    
    -- 检查函数数量
    SELECT COUNT(*) INTO function_count
    FROM pg_proc 
    WHERE proname IN ('get_resumable_handle', 'mark_handle_resumed', 'store_resume_payload', 'cleanup_expired_handles', 'delete_old_resume_handles');
    
    RAISE NOTICE '工作流恢复句柄表创建完成：';
    RAISE NOTICE '- flow_resume_handles: 工作流恢复句柄表';
    RAISE NOTICE '- 已创建%个唯一索引确保句柄唯一性', unique_index_count;
    RAISE NOTICE '- 已创建%个索引优化查询性能', regular_index_count;
    RAISE NOTICE '- 已创建%个检查约束确保数据完整性', constraint_count;
    RAISE NOTICE '- 已创建%个管理函数', function_count;
    RAISE NOTICE '- 支持Prefect工作流暂停/恢复机制';
    RAISE NOTICE '- 提供竞态条件处理和过期管理';
    RAISE NOTICE '- 包含统计视图和清理功能';
END $$;