-- ================================================
-- 06-command-inbox.sql
-- 命令收件箱表定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建命令收件箱表
-- 2. 建立幂等性保证机制
-- 3. 提供异步命令处理的基础设施
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：02-init-enums.sql（需要command_status枚举）
-- ================================================

-- ===========================================
-- 命令收件箱表 - 通过唯一性约束为需要异步处理的命令提供幂等性保证
-- ===========================================
CREATE TABLE command_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 命令的唯一ID
    session_id UUID NOT NULL, -- 关联的会话ID，用于限定作用域
    command_type TEXT NOT NULL, -- 命令类型 (e.g., 'RequestConceptGeneration')
    idempotency_key TEXT NOT NULL, -- 用于防止重复的幂等键
    payload JSONB, -- 命令的参数
    status command_status NOT NULL DEFAULT 'RECEIVED', -- 命令处理状态
    error_message TEXT, -- 处理失败时的错误信息
    retry_count INTEGER NOT NULL DEFAULT 0, -- 重试次数
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE command_inbox IS '命令收件箱，通过唯一性约束为需要异步处理的命令提供幂等性保证。';
COMMENT ON COLUMN command_inbox.id IS '命令记录的唯一标识符';
COMMENT ON COLUMN command_inbox.session_id IS '关联的会话ID，用于限定命令的作用域和权限控制';
COMMENT ON COLUMN command_inbox.command_type IS '命令类型标识，如"RequestConceptGeneration"、"UpdateWorldview"等';
COMMENT ON COLUMN command_inbox.idempotency_key IS '幂等键，用于防止重复处理同一命令，通常是业务层面的唯一标识';
COMMENT ON COLUMN command_inbox.payload IS '命令的参数和数据，JSONB格式，包含执行命令所需的所有信息';
COMMENT ON COLUMN command_inbox.status IS '命令处理状态，使用command_status枚举';
COMMENT ON COLUMN command_inbox.error_message IS '命令处理失败时的详细错误信息';
COMMENT ON COLUMN command_inbox.retry_count IS '命令重试次数，用于重试机制和故障排查';
COMMENT ON COLUMN command_inbox.created_at IS '命令接收时间';
COMMENT ON COLUMN command_inbox.updated_at IS '命令状态最后更新时间';

-- 创建唯一索引确保幂等性：同一会话内同一类型的待处理命令只能有一个
CREATE UNIQUE INDEX idx_command_inbox_unique_pending_command 
    ON command_inbox (session_id, command_type) 
    WHERE status IN ('RECEIVED', 'PROCESSING');

COMMENT ON INDEX idx_command_inbox_unique_pending_command IS '确保同一会话内同一类型的命令在处理期间的唯一性，实现幂等性保证';

-- 创建其他查询优化索引
CREATE INDEX idx_command_inbox_session_id ON command_inbox(session_id);
CREATE INDEX idx_command_inbox_status ON command_inbox(status);
CREATE INDEX idx_command_inbox_command_type ON command_inbox(command_type);
CREATE INDEX idx_command_inbox_created_at ON command_inbox(created_at);

-- 复合索引用于常见查询场景
CREATE INDEX idx_command_inbox_session_status ON command_inbox(session_id, status);
CREATE INDEX idx_command_inbox_status_created ON command_inbox(status, created_at);

-- 创建幂等键的唯一索引（跨会话的全局幂等性）
CREATE UNIQUE INDEX idx_command_inbox_idempotency_key 
    ON command_inbox(idempotency_key);

COMMENT ON INDEX idx_command_inbox_idempotency_key IS '全局幂等键唯一索引，确保相同的幂等键不会被重复处理';

-- 添加检查约束确保数据完整性
ALTER TABLE command_inbox ADD CONSTRAINT check_retry_count_non_negative 
    CHECK (retry_count >= 0);

ALTER TABLE command_inbox ADD CONSTRAINT check_failed_has_error_message 
    CHECK (
        (status != 'FAILED') OR 
        (status = 'FAILED' AND error_message IS NOT NULL)
    );

COMMENT ON CONSTRAINT check_retry_count_non_negative ON command_inbox IS '确保重试次数不能为负数';
COMMENT ON CONSTRAINT check_failed_has_error_message ON command_inbox IS '确保失败状态的命令必须包含错误信息';

-- 创建JSONB索引用于复杂查询
CREATE INDEX idx_command_inbox_payload_gin ON command_inbox USING GIN (payload);

-- 创建自动清理函数：清理已完成的旧命令记录
CREATE OR REPLACE FUNCTION cleanup_old_command_inbox_records()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 删除30天前已完成或失败的命令记录
    DELETE FROM command_inbox 
    WHERE status IN ('COMPLETED', 'FAILED') 
    AND created_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '已清理%个过期的命令收件箱记录', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_command_inbox_records() IS '清理30天前已完成或失败的命令记录，避免表过度增长';

-- 验证命令收件箱表创建
DO $$
DECLARE
    table_exists BOOLEAN;
    unique_index_count INTEGER;
    regular_index_count INTEGER;
    constraint_count INTEGER;
BEGIN
    -- 检查表是否创建成功
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'command_inbox'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'command_inbox表创建失败';
    END IF;
    
    -- 检查唯一索引数量（用于幂等性保证）
    SELECT COUNT(*) INTO unique_index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'command_inbox'
    AND indexdef LIKE '%UNIQUE%';
    
    -- 检查常规索引数量
    SELECT COUNT(*) INTO regular_index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'command_inbox';
    
    -- 检查约束数量
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.check_constraints 
    WHERE constraint_schema = 'public' 
    AND constraint_name LIKE '%command_inbox%';
    
    RAISE NOTICE '命令收件箱表创建完成：';
    RAISE NOTICE '- command_inbox: 命令收件箱表';
    RAISE NOTICE '- 已创建%个唯一索引确保幂等性', unique_index_count;
    RAISE NOTICE '- 已创建%个索引优化查询性能', regular_index_count;
    RAISE NOTICE '- 已创建%个检查约束确保数据完整性', constraint_count;
    RAISE NOTICE '- 支持会话级别和全局级别的命令幂等性';
    RAISE NOTICE '- 提供命令重试和错误处理机制';
    RAISE NOTICE '- 包含自动清理函数避免数据积累';
END $$;