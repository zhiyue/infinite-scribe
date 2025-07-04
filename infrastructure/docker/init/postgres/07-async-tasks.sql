-- ================================================
-- 07-async-tasks.sql
-- 异步任务表定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建通用的异步任务表
-- 2. 提供后台任务执行状态追踪
-- 3. 支持任务进度监控和错误处理
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：06-command-inbox.sql（任务可能由命令触发）
-- ================================================

-- ===========================================
-- 异步任务表 - 通用的异步任务表，用于追踪所有后台技术任务的执行状态
-- ===========================================
CREATE TABLE async_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 任务的唯一ID
    task_type TEXT NOT NULL, -- 任务类型 (e.g., 'genesis.concept_generation')
    triggered_by_command_id UUID, -- 触发此任务的命令ID
    status task_status NOT NULL DEFAULT 'PENDING', -- 任务执行状态
    progress DECIMAL(5, 2) NOT NULL DEFAULT 0.0, -- 任务进度（0.00 - 100.00）
    input_data JSONB, -- 任务的输入参数
    result_data JSONB, -- 任务成功后的结果
    error_data JSONB, -- 任务失败时的错误信息
    execution_node TEXT, -- 执行此任务的节点或服务实例标识
    retry_count INTEGER NOT NULL DEFAULT 0, -- 重试次数
    max_retries INTEGER NOT NULL DEFAULT 3, -- 最大重试次数
    started_at TIMESTAMPTZ, -- 任务开始执行时间
    completed_at TIMESTAMPTZ, -- 任务完成时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE async_tasks IS '通用的异步任务表，用于追踪所有后台技术任务（如调用LLM）的执行状态。';
COMMENT ON COLUMN async_tasks.id IS '任务的唯一标识符';
COMMENT ON COLUMN async_tasks.task_type IS '任务类型标识，如"genesis.concept_generation"、"llm.text_generation"、"image.processing"等';
COMMENT ON COLUMN async_tasks.triggered_by_command_id IS '触发此任务的命令ID，外键关联command_inbox表，可为空（系统内部任务）';
COMMENT ON COLUMN async_tasks.status IS '任务执行状态，使用task_status枚举';
COMMENT ON COLUMN async_tasks.progress IS '任务进度百分比，范围0.00-100.00';
COMMENT ON COLUMN async_tasks.input_data IS '任务输入参数，JSONB格式，包含执行任务所需的所有数据';
COMMENT ON COLUMN async_tasks.result_data IS '任务执行成功后的结果数据，JSONB格式';
COMMENT ON COLUMN async_tasks.error_data IS '任务执行失败时的错误信息，JSONB格式，包含错误码、错误消息、堆栈跟踪等';
COMMENT ON COLUMN async_tasks.execution_node IS '执行此任务的节点或服务实例标识，用于分布式环境下的任务分配和故障排查';
COMMENT ON COLUMN async_tasks.retry_count IS '当前重试次数';
COMMENT ON COLUMN async_tasks.max_retries IS '最大允许重试次数';
COMMENT ON COLUMN async_tasks.started_at IS '任务开始执行的时间戳';
COMMENT ON COLUMN async_tasks.completed_at IS '任务完成的时间戳';
COMMENT ON COLUMN async_tasks.created_at IS '任务创建时间';
COMMENT ON COLUMN async_tasks.updated_at IS '任务状态最后更新时间';

-- 添加外键约束（软引用，允许命令被删除后任务继续存在）
ALTER TABLE async_tasks ADD CONSTRAINT fk_async_tasks_command 
    FOREIGN KEY (triggered_by_command_id) REFERENCES command_inbox(id) ON DELETE SET NULL;

-- 创建核心查询索引
CREATE INDEX idx_async_tasks_status ON async_tasks(status);
CREATE INDEX idx_async_tasks_task_type ON async_tasks(task_type);
CREATE INDEX idx_async_tasks_created_at ON async_tasks(created_at);
CREATE INDEX idx_async_tasks_command_id ON async_tasks(triggered_by_command_id) WHERE triggered_by_command_id IS NOT NULL;

-- 复合索引用于常见查询场景
CREATE INDEX idx_async_tasks_status_type ON async_tasks(status, task_type);
CREATE INDEX idx_async_tasks_status_created ON async_tasks(status, created_at);
CREATE INDEX idx_async_tasks_type_created ON async_tasks(task_type, created_at);

-- 执行节点查询索引
CREATE INDEX idx_async_tasks_execution_node ON async_tasks(execution_node) WHERE execution_node IS NOT NULL;

-- JSONB字段的GIN索引用于复杂查询
CREATE INDEX idx_async_tasks_input_data_gin ON async_tasks USING GIN (input_data);
CREATE INDEX idx_async_tasks_result_data_gin ON async_tasks USING GIN (result_data);
CREATE INDEX idx_async_tasks_error_data_gin ON async_tasks USING GIN (error_data);

-- 添加检查约束确保数据完整性
ALTER TABLE async_tasks ADD CONSTRAINT check_progress_range 
    CHECK (progress >= 0.0 AND progress <= 100.0);

ALTER TABLE async_tasks ADD CONSTRAINT check_retry_count_valid 
    CHECK (retry_count >= 0 AND retry_count <= max_retries);

ALTER TABLE async_tasks ADD CONSTRAINT check_max_retries_non_negative 
    CHECK (max_retries >= 0);

ALTER TABLE async_tasks ADD CONSTRAINT check_completed_has_timestamp 
    CHECK (
        (status NOT IN ('COMPLETED', 'FAILED')) OR 
        (status IN ('COMPLETED', 'FAILED') AND completed_at IS NOT NULL)
    );

ALTER TABLE async_tasks ADD CONSTRAINT check_running_has_started 
    CHECK (
        (status != 'RUNNING') OR 
        (status = 'RUNNING' AND started_at IS NOT NULL)
    );

ALTER TABLE async_tasks ADD CONSTRAINT check_failed_has_error 
    CHECK (
        (status != 'FAILED') OR 
        (status = 'FAILED' AND error_data IS NOT NULL)
    );

ALTER TABLE async_tasks ADD CONSTRAINT check_completed_has_result 
    CHECK (
        (status != 'COMPLETED') OR 
        (status = 'COMPLETED' AND result_data IS NOT NULL)
    );

COMMENT ON CONSTRAINT check_progress_range ON async_tasks IS '确保进度值在有效范围内（0-100）';
COMMENT ON CONSTRAINT check_retry_count_valid ON async_tasks IS '确保重试次数不超过最大重试次数';
COMMENT ON CONSTRAINT check_max_retries_non_negative ON async_tasks IS '确保最大重试次数为非负数';
COMMENT ON CONSTRAINT check_completed_has_timestamp ON async_tasks IS '确保已完成或失败的任务有完成时间戳';
COMMENT ON CONSTRAINT check_running_has_started ON async_tasks IS '确保运行中的任务有开始时间戳';
COMMENT ON CONSTRAINT check_failed_has_error ON async_tasks IS '确保失败的任务包含错误信息';
COMMENT ON CONSTRAINT check_completed_has_result ON async_tasks IS '确保成功完成的任务包含结果数据';

-- 创建任务超时检测函数
CREATE OR REPLACE FUNCTION detect_timeout_tasks(timeout_minutes INTEGER DEFAULT 60)
RETURNS TABLE(task_id UUID, task_type TEXT, started_at TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    SELECT at.id, at.task_type, at.started_at
    FROM async_tasks at
    WHERE at.status = 'RUNNING'
    AND at.started_at < NOW() - (timeout_minutes || ' minutes')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION detect_timeout_tasks(INTEGER) IS '检测超时的运行中任务，默认超时时间为60分钟';

-- 创建任务清理函数
CREATE OR REPLACE FUNCTION cleanup_old_async_tasks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 删除7天前已完成的任务记录
    DELETE FROM async_tasks 
    WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED') 
    AND completed_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '已清理%个过期的异步任务记录', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_async_tasks() IS '清理7天前已完成的任务记录，避免表过度增长';

-- 创建任务统计视图
CREATE VIEW async_task_statistics AS
SELECT 
    task_type,
    status,
    COUNT(*) as task_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MIN(created_at) as earliest_task,
    MAX(created_at) as latest_task
FROM async_tasks
WHERE completed_at IS NOT NULL
GROUP BY task_type, status;

COMMENT ON VIEW async_task_statistics IS '异步任务统计视图，提供按类型和状态的任务执行统计信息';

-- 验证异步任务表创建
DO $$
DECLARE
    table_exists BOOLEAN;
    index_count INTEGER;
    constraint_count INTEGER;
    function_count INTEGER;
BEGIN
    -- 检查表是否创建成功
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'async_tasks'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'async_tasks表创建失败';
    END IF;
    
    -- 检查索引数量
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'async_tasks';
    
    -- 检查约束数量
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.check_constraints 
    WHERE constraint_schema = 'public' 
    AND constraint_name LIKE '%async_tasks%';
    
    -- 检查函数数量
    SELECT COUNT(*) INTO function_count
    FROM pg_proc 
    WHERE proname IN ('detect_timeout_tasks', 'cleanup_old_async_tasks');
    
    RAISE NOTICE '异步任务表创建完成：';
    RAISE NOTICE '- async_tasks: 异步任务表';
    RAISE NOTICE '- 已创建%个索引优化查询性能', index_count;
    RAISE NOTICE '- 已创建%个检查约束确保数据完整性', constraint_count;
    RAISE NOTICE '- 已创建%个管理函数', function_count;
    RAISE NOTICE '- 支持任务进度追踪（0-100%%）';
    RAISE NOTICE '- 提供重试机制和超时检测';
    RAISE NOTICE '- 包含统计视图和清理功能';
END $$;