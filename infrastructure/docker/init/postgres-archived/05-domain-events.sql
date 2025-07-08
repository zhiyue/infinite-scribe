-- ================================================
-- 05-domain-events.sql
-- 统一领域事件日志表定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建统一的领域事件日志表
-- 2. 建立事件溯源的核心基础设施
-- 3. 提供系统所有业务事实的唯一、不可变来源
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：04-genesis-sessions.sql（可能会记录相关事件）
-- ================================================

-- ===========================================
-- 领域事件表 - 统一的领域事件日志，是整个系统所有业务事实的唯一、不可变来源
-- ===========================================
CREATE TABLE domain_events (
    id BIGSERIAL PRIMARY KEY, -- 使用自增整数，保证事件的严格顺序
    event_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(), -- 事件的全局唯一标识符
    correlation_id UUID, -- 用于追踪一个完整的业务流程或请求链
    causation_id UUID,   -- 指向触发此事件的上一个事件的event_id，形成因果链
    event_type TEXT NOT NULL, -- 事件的唯一类型标识 (e.g., 'genesis.concept.proposed')
    event_version INTEGER NOT NULL DEFAULT 1, -- 事件模型的版本号
    aggregate_type TEXT NOT NULL, -- 聚合根类型 (e.g., 'GENESIS_SESSION', 'NOVEL')
    aggregate_id TEXT NOT NULL,   -- 聚合根的ID
    payload JSONB, -- 事件的具体数据
    metadata JSONB, -- 附加元数据 (如 user_id, source_service)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE domain_events IS '统一的领域事件日志，是整个系统所有业务事实的唯一、不可变来源（Source of Truth）。';
COMMENT ON COLUMN domain_events.id IS '事件的自增序号，保证严格的时间顺序';
COMMENT ON COLUMN domain_events.event_id IS '事件的全局唯一标识符，用于外部引用和去重';
COMMENT ON COLUMN domain_events.correlation_id IS '用于追踪一个完整的业务流程或请求链，相同流程的事件具有相同的correlation_id';
COMMENT ON COLUMN domain_events.causation_id IS '指向触发此事件的上一个事件的event_id，形成因果链，便于追踪事件传播';
COMMENT ON COLUMN domain_events.event_type IS '事件的唯一类型标识，采用分层命名如"genesis.concept.proposed"';
COMMENT ON COLUMN domain_events.event_version IS '事件模型的版本号，用于事件结构的向后兼容';
COMMENT ON COLUMN domain_events.aggregate_type IS '聚合根类型，如GENESIS_SESSION、NOVEL、CHAPTER等';
COMMENT ON COLUMN domain_events.aggregate_id IS '聚合根的ID，与aggregate_type结合唯一标识业务实体';
COMMENT ON COLUMN domain_events.payload IS '事件的具体数据内容，JSONB格式，包含事件的所有业务信息';
COMMENT ON COLUMN domain_events.metadata IS '附加元数据，JSONB格式，包含user_id、source_service、ip_address等上下文信息';
COMMENT ON COLUMN domain_events.created_at IS '事件创建时间戳，不可修改，确保事件的不可变性';

-- 创建核心索引用于高性能查询
-- 聚合根查询索引（最重要）
CREATE INDEX idx_domain_events_aggregate ON domain_events(aggregate_type, aggregate_id);

-- 事件类型查询索引
CREATE INDEX idx_domain_events_event_type ON domain_events(event_type);

-- 时间范围查询索引
CREATE INDEX idx_domain_events_created_at ON domain_events(created_at);

-- 关联追踪索引
CREATE INDEX idx_domain_events_correlation_id ON domain_events(correlation_id) WHERE correlation_id IS NOT NULL;

-- 因果链追踪索引  
CREATE INDEX idx_domain_events_causation_id ON domain_events(causation_id) WHERE causation_id IS NOT NULL;

-- 复合查询索引
CREATE INDEX idx_domain_events_aggregate_type_time ON domain_events(aggregate_type, created_at);
CREATE INDEX idx_domain_events_event_type_time ON domain_events(event_type, created_at);

-- JSONB字段的GIN索引用于复杂查询
CREATE INDEX idx_domain_events_payload_gin ON domain_events USING GIN (payload);
CREATE INDEX idx_domain_events_metadata_gin ON domain_events USING GIN (metadata);

-- 确保事件的不可变性：禁止UPDATE和DELETE操作
CREATE OR REPLACE FUNCTION prevent_domain_events_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION '禁止修改领域事件：事件日志必须保持不可变性';
    END IF;
    
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION '禁止删除领域事件：事件日志必须保持完整性';
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器防止事件被修改或删除
CREATE TRIGGER prevent_domain_events_update
    BEFORE UPDATE ON domain_events
    FOR EACH ROW EXECUTE FUNCTION prevent_domain_events_modification();

CREATE TRIGGER prevent_domain_events_delete
    BEFORE DELETE ON domain_events
    FOR EACH ROW EXECUTE FUNCTION prevent_domain_events_modification();

-- 添加分区准备（未来扩展）
-- 为了支持大规模数据，可以按时间分区
COMMENT ON TABLE domain_events IS '统一的领域事件日志，是整个系统所有业务事实的唯一、不可变来源（Source of Truth）。表设计支持未来按时间分区以应对大规模数据。';

-- 验证领域事件表创建
DO $$
DECLARE
    table_exists BOOLEAN;
    index_count INTEGER;
    trigger_count INTEGER;
BEGIN
    -- 检查表是否创建成功
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'domain_events'
    ) INTO table_exists;
    
    IF NOT table_exists THEN
        RAISE EXCEPTION 'domain_events表创建失败';
    END IF;
    
    -- 检查索引数量
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public' 
    AND tablename = 'domain_events';
    
    -- 检查触发器数量
    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers 
    WHERE trigger_schema = 'public' 
    AND event_object_table = 'domain_events';
    
    RAISE NOTICE '领域事件表创建完成：';
    RAISE NOTICE '- domain_events: 统一领域事件日志表';
    RAISE NOTICE '- 已创建%个索引优化查询性能', index_count;
    RAISE NOTICE '- 已创建%个触发器确保事件不可变性', trigger_count;
    RAISE NOTICE '- 支持事件溯源架构模式';
    RAISE NOTICE '- 提供完整的业务审计日志';
    RAISE NOTICE '- 支持correlation_id和causation_id追踪事件关系';
    RAISE NOTICE '- 通过JSONB格式灵活存储事件数据';
END $$;