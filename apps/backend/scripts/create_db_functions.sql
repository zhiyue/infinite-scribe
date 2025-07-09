-- 创建数据库触发器和函数
-- 这些功能在 SQL 初始化脚本中定义，但需要在 ORM 创建的表上应用

-- 1. 更新 updated_at 时间戳的触发器函数（如果不存在）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 2. 为需要自动更新 updated_at 的表创建触发器
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN (
            'novels', 'chapters', 'characters', 'worldview_entries', 
            'story_arcs', 'genesis_sessions', 'command_inbox', 
            'async_tasks', 'flow_resume_handles'
        )
    LOOP
        EXECUTE format('
            CREATE TRIGGER set_timestamp_%I
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        ', t, t);
    END LOOP;
END $$;

-- 3. 版本号自增触发器函数
CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 4. 为需要版本控制的表创建触发器
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN (
            'novels', 'chapters', 'characters', 'worldview_entries', 
            'story_arcs', 'genesis_sessions'
        )
    LOOP
        EXECUTE format('
            CREATE TRIGGER increment_version_%I_trigger
            BEFORE UPDATE ON %I
            FOR EACH ROW
            WHEN (OLD.* IS DISTINCT FROM NEW.*)
            EXECUTE FUNCTION increment_version();
        ', t, t);
    END LOOP;
END $$;

-- 5. 防止修改领域事件的触发器
CREATE OR REPLACE FUNCTION prevent_domain_event_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '领域事件不可修改';
END;
$$ language 'plpgsql';

CREATE TRIGGER prevent_domain_event_update
BEFORE UPDATE OR DELETE ON domain_events
FOR EACH ROW
EXECUTE FUNCTION prevent_domain_event_modification();

-- 6. 更新小说完成章节数的函数
CREATE OR REPLACE FUNCTION update_novel_completed_chapters()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE novels
    SET completed_chapters = (
        SELECT COUNT(*)
        FROM chapters
        WHERE novel_id = COALESCE(NEW.novel_id, OLD.novel_id)
        AND status = 'PUBLISHED'
    )
    WHERE id = COALESCE(NEW.novel_id, OLD.novel_id);
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 7. 章节状态变更触发器
CREATE TRIGGER update_novel_progress_on_chapter_change
AFTER INSERT OR UPDATE OF status OR DELETE ON chapters
FOR EACH ROW
EXECUTE FUNCTION update_novel_completed_chapters();

-- 8. 事件发件箱相关函数
CREATE OR REPLACE FUNCTION get_pending_outbox_messages(
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    id UUID,
    topic TEXT,
    key TEXT,
    partition_key TEXT,
    payload JSONB,
    headers JSONB,
    retry_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.topic,
        e.key,
        e.partition_key,
        e.payload,
        e.headers,
        e.retry_count
    FROM event_outbox e
    WHERE e.status = 'PENDING'
    AND e.retry_count < e.max_retries
    AND (e.scheduled_at IS NULL OR e.scheduled_at <= CURRENT_TIMESTAMP)
    ORDER BY e.created_at
    LIMIT p_limit
    FOR UPDATE SKIP LOCKED;
END;
$$;

CREATE OR REPLACE FUNCTION mark_outbox_message_sent(
    p_message_id UUID
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE event_outbox
    SET 
        status = 'SENT',
        sent_at = CURRENT_TIMESTAMP
    WHERE id = p_message_id;
END;
$$;

CREATE OR REPLACE FUNCTION mark_outbox_message_failed(
    p_message_id UUID,
    p_error_message TEXT,
    p_retry_delay_seconds INTEGER DEFAULT 60
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE event_outbox
    SET 
        retry_count = retry_count + 1,
        last_error = p_error_message,
        scheduled_at = CURRENT_TIMESTAMP + (p_retry_delay_seconds || ' seconds')::INTERVAL
    WHERE id = p_message_id;
END;
$$;

CREATE OR REPLACE FUNCTION cleanup_sent_outbox_messages(
    p_older_than_days INTEGER DEFAULT 7
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM event_outbox
    WHERE status = 'SENT'
    AND sent_at < CURRENT_TIMESTAMP - (p_older_than_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$;

-- 9. 创建异步任务统计视图
CREATE OR REPLACE VIEW async_task_statistics AS
SELECT 
    task_type,
    status,
    COUNT(*) as task_count,
    AVG(
        CASE 
            WHEN completed_at IS NOT NULL AND started_at IS NOT NULL 
            THEN EXTRACT(EPOCH FROM (completed_at - started_at))
            ELSE NULL 
        END
    ) as avg_duration_seconds,
    MAX(created_at) as latest_created_at,
    MAX(completed_at) as latest_completed_at
FROM async_tasks
GROUP BY task_type, status;

-- 显示创建结果
SELECT '✅ 数据库触发器和函数创建完成' as 结果;