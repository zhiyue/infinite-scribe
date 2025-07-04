-- ================================================
-- 10-indexes.sql
-- 性能关键索引创建脚本
-- ================================================
--
-- 此脚本负责：
-- 1. 创建系统性能关键的补充索引
-- 2. 优化跨表查询和复杂业务场景
-- 3. 确保高频查询的最佳性能
--

-- 设置搜索路径，避免多schema环境问题
SET search_path TO public;

-- 依赖关系：09-flow-resume-handles.sql（所有表已创建）
-- 
-- 注意：各表的基础索引已在对应的创建脚本中定义，
-- 本脚本主要包含补充性和优化性索引
-- ================================================

-- ===========================================
-- 核心业务实体表的补充索引
-- ===========================================

-- 小说表的复合查询索引
CREATE INDEX idx_novels_status_updated ON novels(status, updated_at);
CREATE INDEX idx_novels_target_completed ON novels(target_chapters, completed_chapters) 
    WHERE status IN ('GENERATING', 'PAUSED');

COMMENT ON INDEX idx_novels_status_updated IS '按状态和更新时间查询小说，用于监控和报表';
COMMENT ON INDEX idx_novels_target_completed IS '按目标章节数和完成数查询，用于进度统计';

-- 章节表的高级查询索引
CREATE INDEX idx_chapters_novel_status_number ON chapters(novel_id, status, chapter_number);
CREATE INDEX idx_chapters_published_version_lookup ON chapters(published_version_id) 
    WHERE published_version_id IS NOT NULL;

COMMENT ON INDEX idx_chapters_novel_status_number IS '按小说、状态、章节号的复合查询';
COMMENT ON INDEX idx_chapters_published_version_lookup IS '快速查找已发布版本对应的章节';

-- 章节版本表的版本链查询索引
CREATE INDEX idx_chapter_versions_parent_chain ON chapter_versions(parent_version_id) 
    WHERE parent_version_id IS NOT NULL;
CREATE INDEX idx_chapter_versions_agent_created ON chapter_versions(created_by_agent_type, created_at);

COMMENT ON INDEX idx_chapter_versions_parent_chain IS '支持版本链的向上遍历查询';
COMMENT ON INDEX idx_chapter_versions_agent_created IS '按智能体类型和创建时间查询版本';

-- 角色表的名称搜索索引
CREATE INDEX idx_characters_name_search ON characters USING GIN (to_tsvector('simple', name));
CREATE INDEX idx_characters_novel_role ON characters(novel_id, role);

COMMENT ON INDEX idx_characters_name_search IS '支持角色名称的全文搜索';
COMMENT ON INDEX idx_characters_novel_role IS '按小说和角色类型查询';

-- 世界观条目的分类查询索引
CREATE INDEX idx_worldview_entries_type_novel ON worldview_entries(entry_type, novel_id);
CREATE INDEX idx_worldview_entries_name_search ON worldview_entries USING GIN (to_tsvector('simple', name || ' ' || COALESCE(description, '')));
CREATE INDEX idx_worldview_entries_tags_gin ON worldview_entries USING GIN (tags);

COMMENT ON INDEX idx_worldview_entries_type_novel IS '按条目类型和小说ID查询世界观元素';
COMMENT ON INDEX idx_worldview_entries_name_search IS '支持世界观条目名称和描述的全文搜索';
COMMENT ON INDEX idx_worldview_entries_tags_gin IS '支持标签数组的快速查询';

-- 评审记录的聚合查询索引
CREATE INDEX idx_reviews_chapter_version_agent ON reviews(chapter_id, chapter_version_id, agent_type);
CREATE INDEX idx_reviews_score_range ON reviews(score) WHERE score IS NOT NULL;

COMMENT ON INDEX idx_reviews_chapter_version_agent IS '按章节版本和智能体类型查询评审';
COMMENT ON INDEX idx_reviews_score_range IS '支持评分范围查询和统计';

-- ===========================================
-- 架构机制表的高性能索引
-- ===========================================

-- 领域事件的高级查询索引
-- 基础索引已在05-domain-events.sql中创建，这里添加补充索引
CREATE INDEX idx_domain_events_correlation_causation ON domain_events(correlation_id, causation_id) 
    WHERE correlation_id IS NOT NULL AND causation_id IS NOT NULL;
CREATE INDEX idx_domain_events_aggregate_event_type ON domain_events(aggregate_type, event_type, created_at);

COMMENT ON INDEX idx_domain_events_correlation_causation IS '支持事件关联链的复杂查询';
COMMENT ON INDEX idx_domain_events_aggregate_event_type IS '按聚合根和事件类型的时序查询';

-- 命令收件箱的监控索引
CREATE INDEX idx_command_inbox_retry_status ON command_inbox(retry_count, status, created_at) 
    WHERE status IN ('RECEIVED', 'PROCESSING', 'FAILED');

COMMENT ON INDEX idx_command_inbox_retry_status IS '监控需要重试的命令';

-- 异步任务的执行监控索引
CREATE INDEX idx_async_tasks_execution_monitoring ON async_tasks(status, execution_node, started_at) 
    WHERE status = 'RUNNING';
CREATE INDEX idx_async_tasks_retry_analysis ON async_tasks(task_type, retry_count, status);

COMMENT ON INDEX idx_async_tasks_execution_monitoring IS '监控运行中任务的执行节点分布';
COMMENT ON INDEX idx_async_tasks_retry_analysis IS '分析任务类型的重试模式';

-- ===========================================
-- 业务逻辑优化索引
-- ===========================================

-- 小说进度统计的优化索引
CREATE INDEX idx_novel_progress_stats ON chapters(novel_id, status) 
    WHERE status = 'PUBLISHED';

COMMENT ON INDEX idx_novel_progress_stats IS '快速统计小说的完成进度';

-- 智能体工作量分析索引
CREATE INDEX idx_agent_workload_analysis ON chapter_versions(created_by_agent_type, created_at);
CREATE INDEX idx_agent_review_workload ON reviews(agent_type, created_at);

COMMENT ON INDEX idx_agent_workload_analysis IS '分析智能体的内容创作工作量';
COMMENT ON INDEX idx_agent_review_workload IS '分析智能体的评审工作量';

-- 创世流程分析索引
CREATE INDEX idx_genesis_flow_analysis ON genesis_sessions(status, current_stage, created_at);
CREATE INDEX idx_genesis_user_sessions ON genesis_sessions(user_id, status, created_at);

COMMENT ON INDEX idx_genesis_flow_analysis IS '分析创世流程的阶段分布和耗时';
COMMENT ON INDEX idx_genesis_user_sessions IS '查询用户的创世会话历史';

-- ===========================================
-- 时间序列查询优化
-- ===========================================

-- 创建按时间分区的查询索引（为未来分区做准备）
CREATE INDEX idx_domain_events_daily_partition ON domain_events(DATE(created_at), aggregate_type);
CREATE INDEX idx_async_tasks_daily_stats ON async_tasks(DATE(created_at), task_type, status);

COMMENT ON INDEX idx_domain_events_daily_partition IS '支持按日期的事件查询，为将来分区优化做准备';
COMMENT ON INDEX idx_async_tasks_daily_stats IS '支持按日期的任务统计查询';

-- ===========================================
-- 外键约束性能优化
-- ===========================================

-- 确保所有外键都有对应的索引（PostgreSQL不会自动创建）
-- 外键索引对JOIN性能至关重要，PostgreSQL不会自动为外键创建索引

-- 动态检查和创建所有缺失的外键索引
DO $$
DECLARE
    indexes_created INTEGER := 0;
BEGIN
    -- 1. chapters.novel_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'chapters' 
        AND (indexname = 'idx_chapters_novel_id' OR indexname LIKE '%novel_id' AND indexname NOT LIKE '%status%')
    ) THEN
        CREATE INDEX idx_chapters_novel_id ON chapters(novel_id);
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建chapters.novel_id索引';
    END IF;

    -- 2. chapters.published_version_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'chapters' 
        AND indexname LIKE '%published_version_id%'
    ) THEN
        CREATE INDEX idx_chapters_published_version_id ON chapters(published_version_id) 
            WHERE published_version_id IS NOT NULL;
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建chapters.published_version_id索引';
    END IF;

    -- 3. chapter_versions.chapter_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'chapter_versions' 
        AND (indexname = 'idx_chapter_versions_chapter_id' OR indexname LIKE '%chapter_id' AND indexname NOT LIKE '%agent%')
    ) THEN
        CREATE INDEX idx_chapter_versions_chapter_id ON chapter_versions(chapter_id);
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建chapter_versions.chapter_id索引';
    END IF;

    -- 4. characters.novel_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'characters' 
        AND (indexname = 'idx_characters_novel_id' OR indexname LIKE '%novel_id' AND indexname NOT LIKE '%role%')
    ) THEN
        CREATE INDEX idx_characters_novel_id ON characters(novel_id);
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建characters.novel_id索引';
    END IF;

    -- 5. worldview_entries.novel_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'worldview_entries' 
        AND (indexname = 'idx_worldview_entries_novel_id' OR indexname LIKE '%novel_id' AND indexname NOT LIKE '%type%')
    ) THEN
        CREATE INDEX idx_worldview_entries_novel_id ON worldview_entries(novel_id);
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建worldview_entries.novel_id索引';
    END IF;

    -- 6. story_arcs.novel_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'story_arcs' 
        AND indexname LIKE '%novel_id%'
    ) THEN
        CREATE INDEX idx_story_arcs_novel_id ON story_arcs(novel_id);
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建story_arcs.novel_id索引';
    END IF;

    -- 7. reviews.chapter_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'reviews' 
        AND (indexname = 'idx_reviews_chapter_id' OR indexname LIKE '%chapter_id' AND indexname NOT LIKE '%version%' AND indexname NOT LIKE '%agent%')
    ) THEN
        CREATE INDEX idx_reviews_chapter_id ON reviews(chapter_id);
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建reviews.chapter_id索引';
    END IF;

    -- 8. reviews.chapter_version_id 索引
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND tablename = 'reviews' 
        AND (indexname = 'idx_reviews_chapter_version_id' OR indexname LIKE '%chapter_version_id' AND indexname NOT LIKE '%agent%')
    ) THEN
        CREATE INDEX idx_reviews_chapter_version_id ON reviews(chapter_version_id);
        indexes_created := indexes_created + 1;
        RAISE NOTICE '已创建reviews.chapter_version_id索引';
    END IF;

    RAISE NOTICE '外键索引检查完成，新创建了%个索引', indexes_created;
END $$;

-- ===========================================
-- 查询性能监控
-- ===========================================

-- 创建查询性能监控视图
CREATE VIEW query_performance_summary AS
SELECT 
    schemaname,
    tablename,
    attname as column_name,
    n_distinct,
    correlation,
    most_common_vals,
    most_common_freqs
FROM pg_stats 
WHERE schemaname = 'public'
AND tablename IN (
    'novels', 'chapters', 'chapter_versions', 'characters', 
    'worldview_entries', 'story_arcs', 'reviews', 
    'genesis_sessions', 'domain_events', 'command_inbox', 
    'async_tasks', 'event_outbox', 'flow_resume_handles'
)
ORDER BY tablename, attname;

COMMENT ON VIEW query_performance_summary IS '查询性能分析视图，显示各表字段的统计信息';

-- 创建索引使用情况监控视图
CREATE VIEW index_usage_statistics AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    CASE 
        WHEN idx_scan = 0 THEN 'Never Used'
        WHEN idx_scan < 100 THEN 'Low Usage'
        WHEN idx_scan < 1000 THEN 'Medium Usage'
        ELSE 'High Usage'
    END as usage_level
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

COMMENT ON VIEW index_usage_statistics IS '索引使用统计视图，帮助识别未使用或低效的索引';

-- 验证索引创建
DO $$
DECLARE
    total_indexes INTEGER;
    table_count INTEGER;
BEGIN
    -- 统计所有创建的索引数量
    SELECT COUNT(*) INTO total_indexes
    FROM pg_indexes 
    WHERE schemaname = 'public';
    
    -- 统计表数量
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    
    RAISE NOTICE '性能优化索引创建完成：';
    RAISE NOTICE '- 当前数据库共有%个表', table_count;
    RAISE NOTICE '- 总计创建了%个索引（包括主键和约束索引）', total_indexes;
    RAISE NOTICE '- 平均每表%.1f个索引', total_indexes::FLOAT / table_count;
    RAISE NOTICE '- 已创建性能监控视图';
    RAISE NOTICE '- 索引覆盖：基础查询、复合查询、全文搜索、时序分析';
    RAISE NOTICE '- 为未来数据分区和性能优化做好准备';
END $$;