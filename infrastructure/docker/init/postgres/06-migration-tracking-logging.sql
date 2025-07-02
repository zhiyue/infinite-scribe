-- =====================================================
-- 数据库迁移脚本 - 追踪与日志表（包括分区配置）
-- Story 2.1 Task 2: 创建完整的数据库迁移脚本
-- =====================================================

-- ⚠️ 依赖检查：此脚本依赖 03-migration-enums.sql 中定义的ENUM类型
-- 需要的类型：agent_type, workflow_status, activity_status, event_status
-- 确保 03-migration-enums.sql 已成功执行

-- 追踪与日志表：用于记录Agent活动、工作流运行、事件处理等系统级信息
-- 注意：这些表不使用外键约束，以提高写入性能和系统灵活性

-- 1. 工作流运行表：记录业务流程的执行状态
CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL, -- 关联的小说ID（无外键约束）
    workflow_type VARCHAR(100) NOT NULL,
    status workflow_status NOT NULL,
    parameters JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_details JSONB
);

COMMENT ON TABLE workflow_runs IS '工作流运行表：记录复杂业务流程的执行状态和结果';
COMMENT ON COLUMN workflow_runs.id IS '工作流运行实例的唯一ID';
COMMENT ON COLUMN workflow_runs.novel_id IS '关联的小说ID（无外键约束，由应用层维护）';
COMMENT ON COLUMN workflow_runs.workflow_type IS '工作流类型（如"chapter_generation"、"character_development"）';
COMMENT ON COLUMN workflow_runs.status IS '工作流当前状态';
COMMENT ON COLUMN workflow_runs.parameters IS '启动工作流时传入的参数，JSON格式';
COMMENT ON COLUMN workflow_runs.started_at IS '工作流开始执行时间';
COMMENT ON COLUMN workflow_runs.completed_at IS '工作流完成时间（成功或失败）';
COMMENT ON COLUMN workflow_runs.error_details IS '如果失败，记录详细的错误信息，JSON格式';

-- 2. Agent活动表：记录所有Agent的详细活动日志
CREATE TABLE IF NOT EXISTS agent_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_run_id UUID, -- 关联的工作流运行ID（无外键约束）
    novel_id UUID NOT NULL, -- 关联的小说ID（无外键约束）
    target_entity_id UUID, -- 活动操作的目标实体ID
    target_entity_type VARCHAR(50), -- 目标实体类型
    agent_type agent_type,
    activity_type VARCHAR(100) NOT NULL,
    status activity_status NOT NULL,
    input_data JSONB,
    output_data JSONB,
    error_details JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER GENERATED ALWAYS AS (EXTRACT(EPOCH FROM (completed_at - started_at))::INTEGER) STORED,
    llm_tokens_used INTEGER,
    llm_cost_estimate DECIMAL(10, 6),
    retry_count INTEGER DEFAULT 0
);

COMMENT ON TABLE agent_activities IS 'Agent活动表：记录所有AI智能体的详细活动日志';
COMMENT ON COLUMN agent_activities.id IS 'Agent活动的唯一ID';
COMMENT ON COLUMN agent_activities.workflow_run_id IS '关联的工作流运行ID（无外键约束）';
COMMENT ON COLUMN agent_activities.novel_id IS '关联的小说ID（无外键约束）';
COMMENT ON COLUMN agent_activities.target_entity_id IS '活动操作的目标实体ID（如chapter_id、character_id）';
COMMENT ON COLUMN agent_activities.target_entity_type IS '目标实体类型（如"CHAPTER"、"CHARACTER"）';
COMMENT ON COLUMN agent_activities.agent_type IS '执行活动的Agent类型';
COMMENT ON COLUMN agent_activities.activity_type IS '活动类型（如"GENERATE_OUTLINE"、"WRITE_DRAFT"）';
COMMENT ON COLUMN agent_activities.status IS '活动执行状态';
COMMENT ON COLUMN agent_activities.input_data IS '活动的输入数据摘要，JSON格式';
COMMENT ON COLUMN agent_activities.output_data IS '活动的输出数据摘要，JSON格式';
COMMENT ON COLUMN agent_activities.error_details IS '如果失败，记录错误详情，JSON格式';
COMMENT ON COLUMN agent_activities.started_at IS '活动开始时间';
COMMENT ON COLUMN agent_activities.completed_at IS '活动完成时间';
COMMENT ON COLUMN agent_activities.duration_seconds IS '活动持续时间（秒），自动计算字段';
COMMENT ON COLUMN agent_activities.llm_tokens_used IS '调用LLM消耗的Token数量';
COMMENT ON COLUMN agent_activities.llm_cost_estimate IS '调用LLM的估算成本（美元）';
COMMENT ON COLUMN agent_activities.retry_count IS '活动重试次数';

-- 3. 事件表：记录系统中的事件流
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    novel_id UUID, -- 关联的小说ID（无外键约束）
    workflow_run_id UUID, -- 关联的工作流运行ID（无外键约束）
    payload JSONB NOT NULL,
    status event_status NOT NULL DEFAULT 'PENDING',
    processed_by_agent_type agent_type,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    error_details JSONB
);

COMMENT ON TABLE events IS '事件表：记录系统中的事件流和处理状态';
COMMENT ON COLUMN events.id IS '事件唯一ID';
COMMENT ON COLUMN events.event_type IS '事件类型（如"Outline.Created"、"Chapter.Published"）';
COMMENT ON COLUMN events.novel_id IS '关联的小说ID（无外键约束）';
COMMENT ON COLUMN events.workflow_run_id IS '关联的工作流运行ID（无外键约束）';
COMMENT ON COLUMN events.payload IS '事件的完整载荷，JSON格式';
COMMENT ON COLUMN events.status IS '事件处理状态';
COMMENT ON COLUMN events.processed_by_agent_type IS '处理此事件的Agent类型';
COMMENT ON COLUMN events.created_at IS '事件创建时间';
COMMENT ON COLUMN events.processed_at IS '事件处理完成时间';
COMMENT ON COLUMN events.error_details IS '如果处理失败，记录错误详情';

-- 4. Agent配置表：管理Agent的配置参数
CREATE TABLE IF NOT EXISTS agent_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID, -- 关联的小说ID（NULL表示全局配置，无外键约束）
    agent_type agent_type,
    config_key VARCHAR(255) NOT NULL,
    config_value TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(novel_id, agent_type, config_key)
);

COMMENT ON TABLE agent_configurations IS 'Agent配置表：管理各个Agent的配置参数';
COMMENT ON COLUMN agent_configurations.id IS '配置项唯一ID';
COMMENT ON COLUMN agent_configurations.novel_id IS '关联的小说ID（NULL表示全局配置）';
COMMENT ON COLUMN agent_configurations.agent_type IS '配置作用的Agent类型';
COMMENT ON COLUMN agent_configurations.config_key IS '配置项名称（如"llm_model"、"temperature"）';
COMMENT ON COLUMN agent_configurations.config_value IS '配置项的值';
COMMENT ON COLUMN agent_configurations.is_active IS '是否启用此配置';

-- 5. Agent活动表索引（已改为普通表，不再使用分区）

-- Agent活动表索引
CREATE INDEX IF NOT EXISTS idx_agent_activities_novel_agent ON agent_activities(novel_id, agent_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_activities_workflow_run ON agent_activities(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_activities_status ON agent_activities(status);
CREATE INDEX IF NOT EXISTS idx_agent_activities_started_at ON agent_activities(started_at DESC);

-- 注释：分区管理函数和分区创建逻辑已移除
-- 如果未来需要分区功能，可以重新启用以下代码：
-- 
-- CREATE OR REPLACE FUNCTION create_monthly_partition(target_table TEXT, target_date DATE DEFAULT CURRENT_DATE)
-- RETURNS void AS $$
-- DECLARE
--     start_date date;
--     end_date date;
--     partition_name text;
-- BEGIN
--     start_date := date_trunc('month', target_date);
--     end_date := start_date + interval '1 month';
--     partition_name := target_table || '_' || to_char(start_date, 'YYYY_MM');
--     
--     IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = partition_name) THEN
--         EXECUTE format(
--             'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
--             partition_name, target_table, start_date, end_date
--         );
--         
--         EXECUTE format('CREATE INDEX %I ON %I (novel_id, agent_type, started_at DESC)', 
--                       'idx_' || partition_name || '_novel_agent', partition_name);
--         EXECUTE format('CREATE INDEX %I ON %I (workflow_run_id)', 
--                       'idx_' || partition_name || '_workflow', partition_name);
--         EXECUTE format('CREATE INDEX %I ON %I (status)', 
--                       'idx_' || partition_name || '_status', partition_name);
--                       
--         RAISE NOTICE '创建分区: %', partition_name;
--     END IF;
-- END;
-- $$ LANGUAGE plpgsql;

-- 6. 创建基本索引（非分区表）

-- 工作流运行表索引
CREATE INDEX IF NOT EXISTS idx_workflow_runs_novel_status ON workflow_runs(novel_id, status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_type_status ON workflow_runs(workflow_type, status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_started_at ON workflow_runs(started_at DESC);

-- 事件表索引
CREATE INDEX IF NOT EXISTS idx_events_type_status ON events(event_type, status);
CREATE INDEX IF NOT EXISTS idx_events_novel_created ON events(novel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_workflow_run ON events(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_events_status_created ON events(status, created_at);

-- Agent配置表索引
CREATE INDEX IF NOT EXISTS idx_agent_configurations_novel_agent ON agent_configurations(novel_id, agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_configurations_agent_key ON agent_configurations(agent_type, config_key);
CREATE INDEX IF NOT EXISTS idx_agent_configurations_active ON agent_configurations(is_active) WHERE is_active = true;

-- 7. 可选的通用审计日志表（用于更底层的数据变更追踪）
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(63) NOT NULL,
    record_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    changed_by_agent_type agent_type,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    old_values JSONB,
    new_values JSONB
);

COMMENT ON TABLE audit_log IS '通用审计日志表：记录所有表的数据变更历史（可选使用）';
COMMENT ON COLUMN audit_log.table_name IS '发生变更的表名';
COMMENT ON COLUMN audit_log.record_id IS '发生变更的记录ID';
COMMENT ON COLUMN audit_log.operation IS '操作类型：INSERT、UPDATE、DELETE';
COMMENT ON COLUMN audit_log.changed_by_agent_type IS '执行变更的Agent类型';
COMMENT ON COLUMN audit_log.old_values IS '对于UPDATE和DELETE，记录变更前的值';
COMMENT ON COLUMN audit_log.new_values IS '对于INSERT和UPDATE，记录变更后的值';

-- 审计日志表索引
CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit_log(changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_operation ON audit_log(operation);