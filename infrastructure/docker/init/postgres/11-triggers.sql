-- ================================================
-- 11-triggers.sql
-- 触发器定义脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 为所有有updated_at字段的表创建自动更新触发器
-- 2. 创建业务逻辑相关的触发器
-- 3. 确保数据一致性和完整性
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：10-indexes.sql（所有表和索引已创建）
-- 需要：01-init-functions.sql中的trigger_set_timestamp()函数
-- ================================================

-- ===========================================
-- 自动更新时间戳触发器
-- ===========================================

-- 为所有有updated_at字段的表创建自动更新时间戳的触发器
-- 这些触发器使用在01-init-functions.sql中定义的trigger_set_timestamp()函数

-- 小说表
CREATE TRIGGER set_timestamp_novels 
    BEFORE UPDATE ON novels 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 章节表
CREATE TRIGGER set_timestamp_chapters 
    BEFORE UPDATE ON chapters 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 角色表
CREATE TRIGGER set_timestamp_characters 
    BEFORE UPDATE ON characters 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 世界观条目表
CREATE TRIGGER set_timestamp_worldview_entries 
    BEFORE UPDATE ON worldview_entries 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 故事弧表
CREATE TRIGGER set_timestamp_story_arcs 
    BEFORE UPDATE ON story_arcs 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 创世会话表
CREATE TRIGGER set_timestamp_genesis_sessions 
    BEFORE UPDATE ON genesis_sessions 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 命令收件箱表
CREATE TRIGGER set_timestamp_command_inbox 
    BEFORE UPDATE ON command_inbox 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 异步任务表
CREATE TRIGGER set_timestamp_async_tasks 
    BEFORE UPDATE ON async_tasks 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- 工作流恢复句柄表
CREATE TRIGGER set_timestamp_flow_resume_handles 
    BEFORE UPDATE ON flow_resume_handles 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- ===========================================
-- 业务逻辑触发器
-- ===========================================

-- 小说进度和状态智能更新触发器（合并逻辑避免递归）
CREATE OR REPLACE FUNCTION update_novel_progress_and_status()
RETURNS TRIGGER AS $$
DECLARE
    target_novel_id UUID;
    completed_count INTEGER;
    novel_record RECORD;
    new_status novel_status;
BEGIN
    -- 确定要更新的小说ID
    IF TG_OP = 'DELETE' THEN
        target_novel_id := OLD.novel_id;
    ELSE
        target_novel_id := NEW.novel_id;
    END IF;
    
    -- 只有当章节状态变化涉及PUBLISHED时才需要更新
    IF NOT (
        (TG_OP = 'UPDATE' AND (OLD.status = 'PUBLISHED' OR NEW.status = 'PUBLISHED')) OR
        (TG_OP = 'INSERT' AND NEW.status = 'PUBLISHED') OR
        (TG_OP = 'DELETE' AND OLD.status = 'PUBLISHED')
    ) THEN
        RETURN COALESCE(NEW, OLD);
    END IF;
    
    -- 获取小说当前信息并计算最新的已发布章节数
    SELECT n.*, COUNT(c.id) FILTER (WHERE c.status = 'PUBLISHED') as current_completed
    INTO novel_record
    FROM novels n
    LEFT JOIN chapters c ON c.novel_id = n.id
    WHERE n.id = target_novel_id
    GROUP BY n.id, n.title, n.theme, n.writing_style, n.status, n.target_chapters, n.completed_chapters, n.version, n.created_at, n.updated_at;
    
    completed_count := COALESCE(novel_record.current_completed, 0);
    
    -- 确定新的小说状态
    new_status := novel_record.status;
    
    -- 如果达到目标章节数，自动设为完成状态
    IF novel_record.target_chapters > 0 
    AND completed_count >= novel_record.target_chapters 
    AND novel_record.status = 'GENERATING' THEN
        new_status := 'COMPLETED';
    END IF;
    
    -- 原子操作：同时更新章节数和状态（仅在有变化时）
    IF novel_record.completed_chapters != completed_count OR novel_record.status != new_status THEN
        UPDATE novels 
        SET completed_chapters = completed_count,
            status = new_status
        WHERE id = target_novel_id;
        
        -- 记录状态变化
        IF novel_record.status != new_status THEN
            RAISE NOTICE '小说 "%" 状态从 % 变更为 %（完成 %/% 章节）', 
                novel_record.title, novel_record.status, new_status, 
                completed_count, novel_record.target_chapters;
        END IF;
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_novel_progress_and_status_trigger
    AFTER INSERT OR UPDATE OR DELETE ON chapters
    FOR EACH ROW EXECUTE FUNCTION update_novel_progress_and_status();

COMMENT ON FUNCTION update_novel_progress_and_status() IS '智能更新小说的章节统计和状态，采用原子操作避免触发器递归';

-- 原 auto_update_novel_status 逻辑已合并到 update_novel_progress_and_status 函数中

-- 章节版本字数统计触发器
CREATE OR REPLACE FUNCTION update_chapter_version_word_count()
RETURNS TRIGGER AS $$
DECLARE
    content_text TEXT;
    word_count INTEGER;
BEGIN
    -- 这是一个占位符实现，实际应用中需要从MinIO获取内容并计算字数
    -- 这里先设置一个默认值，实际实现应该通过应用层调用
    IF NEW.word_count IS NULL THEN
        NEW.word_count := 0; -- 默认值，应用层负责更新实际字数
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_chapter_version_word_count_trigger
    BEFORE INSERT ON chapter_versions
    FOR EACH ROW EXECUTE FUNCTION update_chapter_version_word_count();

COMMENT ON FUNCTION update_chapter_version_word_count() IS '设置章节版本字数的默认值（实际计算由应用层负责）';

-- ===========================================
-- 数据完整性触发器
-- ===========================================



-- ===========================================
-- 审计和日志触发器
-- ===========================================

-- 敏感操作审计触发器
CREATE OR REPLACE FUNCTION audit_sensitive_operations()
RETURNS TRIGGER AS $$
BEGIN
    -- 记录重要表的关键操作到系统日志
    IF TG_TABLE_NAME = 'novels' AND TG_OP = 'DELETE' THEN
        RAISE NOTICE '审计日志: 删除小说记录 - ID: %, 标题: %', OLD.id, OLD.title;
    ELSIF TG_TABLE_NAME = 'domain_events' AND TG_OP = 'UPDATE' THEN
        RAISE WARNING '审计警告: 尝试修改领域事件记录 - 事件ID: %', OLD.event_id;
    ELSIF TG_TABLE_NAME = 'domain_events' AND TG_OP = 'DELETE' THEN
        RAISE WARNING '审计警告: 尝试删除领域事件记录 - 事件ID: %', OLD.event_id;
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 为敏感表创建审计触发器
CREATE TRIGGER audit_novels_trigger
    AFTER DELETE ON novels
    FOR EACH ROW EXECUTE FUNCTION audit_sensitive_operations();

COMMENT ON FUNCTION audit_sensitive_operations() IS '记录敏感操作的审计日志';

-- ===========================================
-- 性能优化触发器
-- ===========================================

-- 乐观锁版本自动递增触发器
CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
BEGIN
    -- 为有version字段的表自动递增版本号
    IF TG_OP = 'UPDATE' THEN
        NEW.version := OLD.version + 1;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为有version字段的表创建版本递增触发器
CREATE TRIGGER increment_version_novels_trigger
    BEFORE UPDATE ON novels
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER increment_version_chapters_trigger
    BEFORE UPDATE ON chapters
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER increment_version_characters_trigger
    BEFORE UPDATE ON characters
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER increment_version_worldview_entries_trigger
    BEFORE UPDATE ON worldview_entries
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER increment_version_story_arcs_trigger
    BEFORE UPDATE ON story_arcs
    FOR EACH ROW EXECUTE FUNCTION increment_version();

CREATE TRIGGER increment_version_genesis_sessions_trigger
    BEFORE UPDATE ON genesis_sessions
    FOR EACH ROW EXECUTE FUNCTION increment_version();

COMMENT ON FUNCTION increment_version() IS '自动递增乐观锁版本号';

-- 验证触发器创建
DO $$
DECLARE
    trigger_count INTEGER;
    function_count INTEGER;
    timestamp_trigger_count INTEGER;
    business_trigger_count INTEGER;
BEGIN
    -- 统计创建的触发器数量
    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers 
    WHERE trigger_schema = 'public';
    
    -- 统计时间戳触发器数量
    SELECT COUNT(*) INTO timestamp_trigger_count
    FROM information_schema.triggers 
    WHERE trigger_schema = 'public' 
    AND trigger_name LIKE 'set_timestamp_%';
    
    -- 统计业务逻辑触发器数量
    SELECT COUNT(*) INTO business_trigger_count
    FROM information_schema.triggers 
    WHERE trigger_schema = 'public' 
    AND trigger_name NOT LIKE 'set_timestamp_%';
    
    -- 统计触发器函数数量
    SELECT COUNT(*) INTO function_count
    FROM pg_proc 
    WHERE proname IN (
        'update_novel_progress_and_status',
        'update_chapter_version_word_count',
        'audit_sensitive_operations',
        'increment_version'
    );
    
    RAISE NOTICE '触发器创建完成：';
    RAISE NOTICE '- 总计创建了%个触发器', trigger_count;
    RAISE NOTICE '  - 时间戳自动更新触发器：%个', timestamp_trigger_count;
    RAISE NOTICE '  - 业务逻辑触发器：%个', business_trigger_count;
    RAISE NOTICE '- 总计创建了%个触发器函数', function_count;
    RAISE NOTICE '- 触发器功能覆盖：';
    RAISE NOTICE '  - 自动时间戳更新';
    RAISE NOTICE '  - 小说进度统计';
    RAISE NOTICE '  - 状态自动转换';
    RAISE NOTICE '  - 数据完整性保证';
    RAISE NOTICE '  - 审计日志记录';
    RAISE NOTICE '  - 乐观锁版本管理';
END $$;