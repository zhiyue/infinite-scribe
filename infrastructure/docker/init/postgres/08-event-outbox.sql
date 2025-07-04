-- ================================================
-- 08-event-outbox.sql
-- 事件发件箱表定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建事务性事件发件箱表
-- 2. 保证数据库写入与消息发布的原子性
-- 3. 提供可靠的事件发布机制
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：02-init-enums.sql（需要outbox_status枚举）
-- ================================================

-- ===========================================
-- 事件发件箱表 - 事务性发件箱，保证数据库写入与向Kafka发布事件之间的原子性
-- ===========================================
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- 发件箱记录ID
    topic TEXT NOT NULL, -- 目标Kafka主题
    key TEXT, -- Kafka消息的Key
    partition_key TEXT, -- 分区键，用于确定消息发往哪个分区
    payload JSONB NOT NULL, -- 消息的完整内容
    headers JSONB, -- 消息头信息，JSONB格式
    status outbox_status NOT NULL DEFAULT 'PENDING', -- 消息发送状态
    retry_count INTEGER NOT NULL DEFAULT 0, -- 重试次数
    max_retries INTEGER NOT NULL DEFAULT 5, -- 最大重试次数
    last_error TEXT, -- 最后一次发送失败的错误信息
    scheduled_at TIMESTAMPTZ, -- 计划发送时间（用于延迟发送）
    sent_at TIMESTAMPTZ, -- 实际发送成功时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE event_outbox IS '事务性发件箱，保证数据库写入与向Kafka发布事件之间的原子性。';
COMMENT ON COLUMN event_outbox.id IS '发件箱记录的唯一标识符';
COMMENT ON COLUMN event_outbox.topic IS '目标Kafka主题名称，如"domain-events"、"notifications"等';
COMMENT ON COLUMN event_outbox.key IS 'Kafka消息的Key，用于确保相关消息的顺序性';
COMMENT ON COLUMN event_outbox.partition_key IS '分区键，用于路由算法确定消息发往哪个分区，可与key不同';
COMMENT ON COLUMN event_outbox.payload IS '消息的完整内容，JSONB格式，包含所有需要发布的数据';
COMMENT ON COLUMN event_outbox.headers IS '消息头信息，JSONB格式，包含元数据如message_type、correlation_id等';
COMMENT ON COLUMN event_outbox.status IS '消息发送状态，使用outbox_status枚举';
COMMENT ON COLUMN event_outbox.retry_count IS '重试次数，用于重试机制';
COMMENT ON COLUMN event_outbox.max_retries IS '最大重试次数，超过后标记为失败';
COMMENT ON COLUMN event_outbox.last_error IS '最后一次发送失败的错误信息';
COMMENT ON COLUMN event_outbox.scheduled_at IS '计划发送时间，支持延迟发送功能';
COMMENT ON COLUMN event_outbox.sent_at IS '实际发送成功的时间戳';
COMMENT ON COLUMN event_outbox.created_at IS '记录创建时间';

-- 创建核心查询索引
CREATE INDEX idx_event_outbox_status ON event_outbox(status);
CREATE INDEX idx_event_outbox_topic ON event_outbox(topic);
CREATE INDEX idx_event_outbox_created_at ON event_outbox(created_at);

-- 待发送消息的查询索引（最重要的查询场景）
CREATE INDEX idx_event_outbox_pending_scheduled ON event_outbox(status, scheduled_at) 
    WHERE status = 'PENDING';

-- 重试相关索引
CREATE INDEX idx_event_outbox_retry_count ON event_outbox(retry_count);

-- 复合索引用于常见查询场景
CREATE INDEX idx_event_outbox_topic_status ON event_outbox(topic, status);
CREATE INDEX idx_event_outbox_status_created ON event_outbox(status, created_at);

-- Kafka消息键的索引
CREATE INDEX idx_event_outbox_key ON event_outbox(key) WHERE key IS NOT NULL;
CREATE INDEX idx_event_outbox_partition_key ON event_outbox(partition_key) WHERE partition_key IS NOT NULL;

-- JSONB字段的GIN索引用于复杂查询
CREATE INDEX idx_event_outbox_payload_gin ON event_outbox USING GIN (payload);
CREATE INDEX idx_event_outbox_headers_gin ON event_outbox USING GIN (headers);

-- 添加检查约束确保数据完整性
ALTER TABLE event_outbox ADD CONSTRAINT check_retry_count_valid 
    CHECK (retry_count >= 0 AND retry_count <= max_retries);

ALTER TABLE event_outbox ADD CONSTRAINT check_max_retries_non_negative 
    CHECK (max_retries >= 0);

ALTER TABLE event_outbox ADD CONSTRAINT check_sent_has_timestamp 
    CHECK (
        (status != 'SENT') OR 
        (status = 'SENT' AND sent_at IS NOT NULL)
    );

ALTER TABLE event_outbox ADD CONSTRAINT check_scheduled_at_future 
    CHECK (scheduled_at IS NULL OR scheduled_at >= created_at);

COMMENT ON CONSTRAINT check_retry_count_valid ON event_outbox IS '确保重试次数在有效范围内';
COMMENT ON CONSTRAINT check_max_retries_non_negative ON event_outbox IS '确保最大重试次数为非负数';
COMMENT ON CONSTRAINT check_sent_has_timestamp ON event_outbox IS '确保已发送的消息有发送时间戳';
COMMENT ON CONSTRAINT check_scheduled_at_future ON event_outbox IS '确保计划发送时间不早于创建时间';

-- 创建获取待发送消息的函数
CREATE OR REPLACE FUNCTION get_pending_outbox_messages(batch_size INTEGER DEFAULT 100)
RETURNS TABLE(
    id UUID,
    topic TEXT,
    key TEXT,
    partition_key TEXT,
    payload JSONB,
    headers JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        eo.id, 
        eo.topic, 
        eo.key, 
        eo.partition_key, 
        eo.payload, 
        eo.headers
    FROM event_outbox eo
    WHERE eo.status = 'PENDING'
    AND (eo.scheduled_at IS NULL OR eo.scheduled_at <= NOW())
    AND eo.retry_count < eo.max_retries
    ORDER BY eo.created_at
    LIMIT batch_size
    FOR UPDATE SKIP LOCKED;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_pending_outbox_messages(INTEGER) IS '获取待发送的消息，使用FOR UPDATE SKIP LOCKED确保并发安全';

-- 创建标记消息发送成功的函数
CREATE OR REPLACE FUNCTION mark_outbox_message_sent(message_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE event_outbox 
    SET status = 'SENT', 
        sent_at = NOW()
    WHERE id = message_id 
    AND status = 'PENDING';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mark_outbox_message_sent(UUID) IS '标记消息为已发送状态';

-- 创建标记消息发送失败的函数
CREATE OR REPLACE FUNCTION mark_outbox_message_failed(message_id UUID, error_message TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE event_outbox 
    SET retry_count = retry_count + 1,
        last_error = error_message
    WHERE id = message_id 
    AND status = 'PENDING'
    AND retry_count < max_retries;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mark_outbox_message_failed(UUID, TEXT) IS '增加消息重试次数并记录错误信息';

-- 创建清理已发送消息的函数
CREATE OR REPLACE FUNCTION cleanup_sent_outbox_messages()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 删除24小时前已发送的消息
    DELETE FROM event_outbox 
    WHERE status = 'SENT' 
    AND sent_at < NOW() - INTERVAL '24 hours';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE '已清理%个已发送的发件箱消息', deleted_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_sent_outbox_messages() IS '清理24小时前已发送的消息，避免表过度增长';

-- 创建发件箱统计视图
CREATE VIEW event_outbox_statistics AS
SELECT 
    topic,
    status,
    COUNT(*) as message_count,
    MIN(created_at) as earliest_message,
    MAX(created_at) as latest_message,
    AVG(retry_count) as avg_retry_count
FROM event_outbox
GROUP BY topic, status;

COMMENT ON VIEW event_outbox_statistics IS '事件发件箱统计视图，提供按主题和状态的消息统计信息';

-- 验证事件发件箱表创建
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
        WHERE table_schema = 'public' AND table_name = 'event_outbox'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'event_outbox表创建失败';
    END IF;
    
    -- 检查索引数量
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'event_outbox';
    
    -- 检查约束数量
    SELECT COUNT(*) INTO constraint_count
    FROM information_schema.check_constraints 
    WHERE constraint_schema = 'public' 
    AND constraint_name LIKE '%event_outbox%';
    
    -- 检查函数数量
    SELECT COUNT(*) INTO function_count
    FROM pg_proc 
    WHERE proname IN ('get_pending_outbox_messages', 'mark_outbox_message_sent', 'mark_outbox_message_failed', 'cleanup_sent_outbox_messages');
    
    RAISE NOTICE '事件发件箱表创建完成：';
    RAISE NOTICE '- event_outbox: 事务性事件发件箱表';
    RAISE NOTICE '- 已创建%个索引优化查询性能', index_count;
    RAISE NOTICE '- 已创建%个检查约束确保数据完整性', constraint_count;
    RAISE NOTICE '- 已创建%个管理函数', function_count;
    RAISE NOTICE '- 支持事务性事件发布模式';
    RAISE NOTICE '- 提供重试机制和错误处理';
    RAISE NOTICE '- 支持延迟发送和分区键';
    RAISE NOTICE '- 包含统计视图和清理功能';
END $$;