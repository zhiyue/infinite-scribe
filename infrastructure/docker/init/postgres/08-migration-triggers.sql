-- =====================================================
-- 数据库迁移脚本 - 触发器
-- Story 2.1 Task 2: 创建完整的数据库迁移脚本
-- =====================================================

-- 创建所有必要的触发器，用于自动化数据维护和业务逻辑

-- 1. updated_at自动更新触发器（扩展现有的触发器）

-- 为新增的表创建updated_at触发器
CREATE TRIGGER set_timestamp_agent_configurations
    BEFORE UPDATE ON agent_configurations
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_genesis_sessions
    BEFORE UPDATE ON genesis_sessions
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_timestamp();

-- 2. 业务逻辑触发器

-- 自动更新小说的完成章节数
CREATE OR REPLACE FUNCTION update_novel_completed_chapters()
RETURNS TRIGGER AS $$
BEGIN
    -- 当章节状态变为PUBLISHED时，更新小说的completed_chapters计数
    IF TG_OP = 'UPDATE' AND OLD.status != 'PUBLISHED' AND NEW.status = 'PUBLISHED' THEN
        UPDATE novels 
        SET completed_chapters = (
            SELECT COUNT(*) 
            FROM chapters 
            WHERE novel_id = NEW.novel_id AND status = 'PUBLISHED'
        ),
        updated_by_agent_type = NEW.updated_by_agent_type
        WHERE id = NEW.novel_id;
    END IF;
    
    -- 当章节状态从PUBLISHED变为其他状态时，也要更新计数
    IF TG_OP = 'UPDATE' AND OLD.status = 'PUBLISHED' AND NEW.status != 'PUBLISHED' THEN
        UPDATE novels 
        SET completed_chapters = (
            SELECT COUNT(*) 
            FROM chapters 
            WHERE novel_id = NEW.novel_id AND status = 'PUBLISHED'
        ),
        updated_by_agent_type = NEW.updated_by_agent_type
        WHERE id = NEW.novel_id;
    END IF;
    
    -- 当章节被删除时，也要更新计数
    IF TG_OP = 'DELETE' AND OLD.status = 'PUBLISHED' THEN
        UPDATE novels 
        SET completed_chapters = (
            SELECT COUNT(*) 
            FROM chapters 
            WHERE novel_id = OLD.novel_id AND status = 'PUBLISHED'
        )
        WHERE id = OLD.novel_id;
        RETURN OLD;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_novel_completed_chapters
    AFTER INSERT OR UPDATE OR DELETE ON chapters
    FOR EACH ROW
    EXECUTE FUNCTION update_novel_completed_chapters();

-- 自动设置章节的published_version_id
CREATE OR REPLACE FUNCTION auto_set_published_version()
RETURNS TRIGGER AS $$
BEGIN
    -- 当章节状态变为PUBLISHED时，自动设置published_version_id为最新版本
    IF TG_OP = 'UPDATE' AND OLD.status != 'PUBLISHED' AND NEW.status = 'PUBLISHED' THEN
        NEW.published_version_id := (
            SELECT id 
            FROM chapter_versions 
            WHERE chapter_id = NEW.id 
            ORDER BY version_number DESC 
            LIMIT 1
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_set_published_version
    BEFORE UPDATE ON chapters
    FOR EACH ROW
    EXECUTE FUNCTION auto_set_published_version();

-- 3. 审计日志触发器（可选启用）

-- 通用审计日志函数
CREATE OR REPLACE FUNCTION audit_table_changes()
RETURNS TRIGGER AS $$
DECLARE
    audit_row audit_log%ROWTYPE;
    old_data JSONB;
    new_data JSONB;
    changed_by agent_type;
BEGIN
    -- 尝试从会话变量获取当前操作的Agent类型
    BEGIN
        changed_by := current_setting('app.current_agent_type')::agent_type;
    EXCEPTION WHEN OTHERS THEN
        changed_by := NULL;
    END;
    
    -- 准备审计记录
    audit_row.id := gen_random_uuid();
    audit_row.table_name := TG_TABLE_NAME;
    audit_row.operation := TG_OP;
    audit_row.changed_by_agent_type := changed_by;
    audit_row.changed_at := NOW();
    
    -- 根据操作类型设置记录ID和数据
    IF TG_OP = 'DELETE' THEN
        audit_row.record_id := OLD.id;
        audit_row.old_values := to_jsonb(OLD);
    ELSIF TG_OP = 'INSERT' THEN
        audit_row.record_id := NEW.id;
        audit_row.new_values := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        audit_row.record_id := NEW.id;
        audit_row.old_values := to_jsonb(OLD);
        audit_row.new_values := to_jsonb(NEW);
    END IF;
    
    -- 插入审计记录
    INSERT INTO audit_log VALUES (audit_row.*);
    
    -- 返回适当的行
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 为核心表创建审计触发器（默认禁用，可根据需要启用）
-- 要启用审计，取消注释以下触发器

/*
CREATE TRIGGER audit_novels_changes
    AFTER INSERT OR UPDATE OR DELETE ON novels
    FOR EACH ROW EXECUTE FUNCTION audit_table_changes();

CREATE TRIGGER audit_chapters_changes
    AFTER INSERT OR UPDATE OR DELETE ON chapters
    FOR EACH ROW EXECUTE FUNCTION audit_table_changes();

CREATE TRIGGER audit_characters_changes
    AFTER INSERT OR UPDATE OR DELETE ON characters
    FOR EACH ROW EXECUTE FUNCTION audit_table_changes();

CREATE TRIGGER audit_worldview_entries_changes
    AFTER INSERT OR UPDATE OR DELETE ON worldview_entries
    FOR EACH ROW EXECUTE FUNCTION audit_table_changes();
*/

-- 4. 数据一致性维护触发器

-- 确保同一章节的同一Agent类型只保留最新的大纲（实现复杂唯一性约束）
CREATE OR REPLACE FUNCTION ensure_latest_outline_only()
RETURNS TRIGGER AS $$
BEGIN
    -- 当插入新大纲时，将同一章节同一Agent的旧大纲标记为非活跃
    -- 这里我们使用一个简化的方法：允许多个大纲存在，但可以通过查询找到最新的
    -- 如果需要强制唯一性，可以删除旧记录或添加is_active字段
    
    -- 检查是否已存在同一章节同一Agent的大纲
    IF EXISTS (
        SELECT 1 FROM outlines 
        WHERE chapter_id = NEW.chapter_id 
        AND created_by_agent_type = NEW.created_by_agent_type 
        AND version = NEW.version
        AND id != NEW.id
    ) THEN
        RAISE EXCEPTION '同一章节的同一Agent类型不能有相同版本号的大纲';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_latest_outline_only
    BEFORE INSERT OR UPDATE ON outlines
    FOR EACH ROW
    EXECUTE FUNCTION ensure_latest_outline_only();

-- 确保章节版本的word_count与章节的word_count保持同步
CREATE OR REPLACE FUNCTION sync_chapter_word_count()
RETURNS TRIGGER AS $$
BEGIN
    -- 当创建新的章节版本时，更新章节的word_count为最新版本的word_count
    IF TG_OP = 'INSERT' THEN
        UPDATE chapters 
        SET word_count = NEW.word_count,
            updated_by_agent_type = NEW.created_by_agent_type
        WHERE id = NEW.chapter_id 
        AND NEW.version_number = (
            SELECT MAX(version_number) 
            FROM chapter_versions 
            WHERE chapter_id = NEW.chapter_id
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_chapter_word_count
    AFTER INSERT ON chapter_versions
    FOR EACH ROW
    EXECUTE FUNCTION sync_chapter_word_count();

-- 5. 自动创建默认配置

-- 为新小说自动创建默认的Agent配置
CREATE OR REPLACE FUNCTION create_default_agent_configs()
RETURNS TRIGGER AS $$
DECLARE
    agent agent_type;
    default_configs JSONB := '{
        "llm_model": "gpt-4",
        "temperature": "0.7",
        "max_tokens": "2000",
        "retry_count": "3"
    }';
    config_key TEXT;
    config_value TEXT;
BEGIN
    -- 为新创建的小说添加默认Agent配置
    IF TG_OP = 'INSERT' THEN
        FOR agent IN SELECT unnest(enum_range(NULL::agent_type)) LOOP
            FOR config_key, config_value IN SELECT * FROM jsonb_each_text(default_configs) LOOP
                INSERT INTO agent_configurations (
                    novel_id, 
                    agent_type, 
                    config_key, 
                    config_value,
                    is_active
                ) VALUES (
                    NEW.id,
                    agent,
                    config_key,
                    config_value,
                    true
                ) ON CONFLICT (novel_id, agent_type, config_key) DO NOTHING;
            END LOOP;
        END LOOP;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_default_agent_configs
    AFTER INSERT ON novels
    FOR EACH ROW
    EXECUTE FUNCTION create_default_agent_configs();

-- 6. 自动工作流状态管理

-- 工作流完成时自动设置completed_at时间戳
CREATE OR REPLACE FUNCTION auto_set_workflow_completion()
RETURNS TRIGGER AS $$
BEGIN
    -- 当工作流状态变为完成或失败时，自动设置completed_at
    IF TG_OP = 'UPDATE' AND OLD.status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED') 
       AND NEW.status IN ('COMPLETED', 'FAILED', 'CANCELLED') THEN
        NEW.completed_at := NOW();
    END IF;
    
    -- 当工作流状态从完成状态变回运行状态时，清除completed_at
    IF TG_OP = 'UPDATE' AND OLD.status IN ('COMPLETED', 'FAILED', 'CANCELLED')
       AND NEW.status IN ('PENDING', 'RUNNING', 'PAUSED') THEN
        NEW.completed_at := NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_set_workflow_completion
    BEFORE UPDATE ON workflow_runs
    FOR EACH ROW
    EXECUTE FUNCTION auto_set_workflow_completion();

-- Agent活动完成时自动设置completed_at时间戳
CREATE OR REPLACE FUNCTION auto_set_activity_completion()
RETURNS TRIGGER AS $$
BEGIN
    -- 当活动状态变为完成或失败时，自动设置completed_at
    IF TG_OP = 'UPDATE' AND OLD.status NOT IN ('COMPLETED', 'FAILED') 
       AND NEW.status IN ('COMPLETED', 'FAILED') THEN
        NEW.completed_at := NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_set_activity_completion
    BEFORE UPDATE ON agent_activities
    FOR EACH ROW
    EXECUTE FUNCTION auto_set_activity_completion();

-- 事件处理完成时自动设置processed_at时间戳
CREATE OR REPLACE FUNCTION auto_set_event_processing()
RETURNS TRIGGER AS $$
BEGIN
    -- 当事件状态变为已处理或失败时，自动设置processed_at
    IF TG_OP = 'UPDATE' AND OLD.status NOT IN ('PROCESSED', 'FAILED', 'DEAD_LETTER')
       AND NEW.status IN ('PROCESSED', 'FAILED', 'DEAD_LETTER') THEN
        NEW.processed_at := NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_set_event_processing
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION auto_set_event_processing();

-- 7. 分区管理触发器

-- 自动创建下个月的分区（当插入数据到最后一个分区时）
CREATE OR REPLACE FUNCTION auto_create_next_partition()
RETURNS TRIGGER AS $$
DECLARE
    next_month_start date;
    next_month_partition text;
BEGIN
    -- 检查插入的数据是否在当前月的最后几天
    IF EXTRACT(day FROM NEW.started_at) >= 25 THEN
        next_month_start := date_trunc('month', NEW.started_at) + interval '1 month';
        next_month_partition := 'agent_activities_' || to_char(next_month_start, 'YYYY_MM');
        
        -- 如果下个月的分区不存在，创建它
        IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = next_month_partition) THEN
            PERFORM create_monthly_partition('agent_activities');
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_create_next_partition
    AFTER INSERT ON agent_activities
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_next_partition();

-- 8. 辅助函数：设置当前Agent上下文

-- 用于在会话中设置当前操作的Agent类型（用于审计日志）
CREATE OR REPLACE FUNCTION set_current_agent(agent_name agent_type)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_agent_type', agent_name::text, false);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_current_agent(agent_type) IS '设置当前会话的Agent类型，用于审计日志记录';

-- 获取当前Agent类型
CREATE OR REPLACE FUNCTION get_current_agent()
RETURNS agent_type AS $$
BEGIN
    RETURN current_setting('app.current_agent_type', true)::agent_type;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_current_agent() IS '获取当前会话的Agent类型';

-- 9. 数据库维护触发器

-- 定期清理旧的分区（可以通过定时任务调用）
CREATE OR REPLACE FUNCTION cleanup_old_partitions(retention_months INTEGER DEFAULT 12)
RETURNS INTEGER AS $$
DECLARE
    partition_name TEXT;
    partition_date DATE;
    cutoff_date DATE;
    dropped_count INTEGER := 0;
BEGIN
    cutoff_date := date_trunc('month', CURRENT_DATE) - (retention_months || ' months')::interval;
    
    FOR partition_name IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE tablename LIKE 'agent_activities_%' 
        AND tablename ~ '^agent_activities_\d{4}_\d{2}$'
    LOOP
        -- 从分区名称解析日期
        partition_date := to_date(substring(partition_name from '\d{4}_\d{2}'), 'YYYY_MM');
        
        -- 如果分区太旧，删除它
        IF partition_date < cutoff_date THEN
            EXECUTE format('DROP TABLE %I', partition_name);
            dropped_count := dropped_count + 1;
            RAISE NOTICE '删除旧分区: %', partition_name;
        END IF;
    END LOOP;
    
    RETURN dropped_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_partitions(INTEGER) IS '清理超过指定月数的旧分区表，返回删除的分区数量';

-- 10. 触发器状态管理

-- 创建视图来查看所有触发器的状态
CREATE OR REPLACE VIEW trigger_status AS
SELECT 
    t.tgname AS trigger_name,
    c.relname AS table_name,
    n.nspname AS schema_name,
    CASE t.tgenabled 
        WHEN 'O' THEN 'enabled'
        WHEN 'D' THEN 'disabled'
        WHEN 'R' THEN 'replica'
        WHEN 'A' THEN 'always'
        ELSE 'unknown'
    END AS status,
    p.proname AS function_name
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE n.nspname = 'public'
ORDER BY c.relname, t.tgname;

COMMENT ON VIEW trigger_status IS '查看数据库中所有触发器的状态和配置信息';