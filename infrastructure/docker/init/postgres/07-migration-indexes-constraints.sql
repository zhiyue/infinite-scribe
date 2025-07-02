-- =====================================================
-- 数据库迁移脚本 - 索引和约束
-- Story 2.1 Task 2: 创建完整的数据库迁移脚本
-- =====================================================

-- 创建所有必要的性能索引和数据完整性约束

-- 1. 核心实体表的性能索引

-- novels表索引（扩展现有索引）
CREATE INDEX IF NOT EXISTS idx_novels_status ON novels(status);
CREATE INDEX IF NOT EXISTS idx_novels_created_at ON novels(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_novels_title ON novels(title);

-- chapters表索引（扩展现有索引）
CREATE INDEX IF NOT EXISTS idx_chapters_status ON chapters(status);
CREATE INDEX IF NOT EXISTS idx_chapters_novel_status ON chapters(novel_id, status);
CREATE INDEX IF NOT EXISTS idx_chapters_published_version ON chapters(published_version_id);

-- chapter_versions表关键索引
CREATE INDEX IF NOT EXISTS idx_chapter_versions_chapter ON chapter_versions(chapter_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_chapter_versions_agent ON chapter_versions(created_by_agent_type);
CREATE INDEX IF NOT EXISTS idx_chapter_versions_created ON chapter_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chapter_versions_parent ON chapter_versions(parent_version_id);

-- characters表索引（扩展现有索引）
CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(name);
CREATE INDEX IF NOT EXISTS idx_characters_role ON characters(role);
CREATE INDEX IF NOT EXISTS idx_characters_novel_role ON characters(novel_id, role);

-- worldview_entries表索引（扩展现有索引）
CREATE INDEX IF NOT EXISTS idx_worldview_entries_type ON worldview_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_worldview_entries_name ON worldview_entries(name);
CREATE INDEX IF NOT EXISTS idx_worldview_entries_novel_type ON worldview_entries(novel_id, entry_type);
CREATE INDEX IF NOT EXISTS idx_worldview_entries_tags ON worldview_entries USING GIN(tags);

-- story_arcs表索引（扩展现有索引）
CREATE INDEX IF NOT EXISTS idx_story_arcs_status ON story_arcs(status);
CREATE INDEX IF NOT EXISTS idx_story_arcs_novel_status ON story_arcs(novel_id, status);
CREATE INDEX IF NOT EXISTS idx_story_arcs_chapters ON story_arcs(start_chapter_number, end_chapter_number);

-- 2. 中间产物表索引

-- outlines表索引
CREATE INDEX IF NOT EXISTS idx_outlines_chapter ON outlines(chapter_id);
-- 注意: idx_outlines_version 与 UNIQUE(chapter_id, version) 冗余，已删除
CREATE INDEX IF NOT EXISTS idx_outlines_agent ON outlines(created_by_agent_type);

-- scene_cards表索引
CREATE INDEX IF NOT EXISTS idx_scene_cards_chapter ON scene_cards(chapter_id, scene_number);
CREATE INDEX IF NOT EXISTS idx_scene_cards_outline ON scene_cards(outline_id);
CREATE INDEX IF NOT EXISTS idx_scene_cards_pov_character ON scene_cards(pov_character_id);
CREATE INDEX IF NOT EXISTS idx_scene_cards_novel ON scene_cards(novel_id);

-- character_interactions表索引
CREATE INDEX IF NOT EXISTS idx_character_interactions_scene ON character_interactions(scene_card_id);
CREATE INDEX IF NOT EXISTS idx_character_interactions_type ON character_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_character_interactions_novel ON character_interactions(novel_id);
CREATE INDEX IF NOT EXISTS idx_character_interactions_chapter ON character_interactions(chapter_id);

-- reviews表索引
CREATE INDEX IF NOT EXISTS idx_reviews_chapter_version ON reviews(chapter_id, chapter_version_id);
CREATE INDEX IF NOT EXISTS idx_reviews_agent_type ON reviews(agent_type);
CREATE INDEX IF NOT EXISTS idx_reviews_type ON reviews(review_type);
CREATE INDEX IF NOT EXISTS idx_reviews_score ON reviews(score) WHERE score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reviews_workflow ON reviews(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at DESC);

-- 3. JSON字段的GIN索引（用于快速JSON查询）

-- chapter_versions表的metadata字段
CREATE INDEX IF NOT EXISTS idx_chapter_versions_metadata ON chapter_versions USING GIN(metadata);

-- outlines表的metadata字段
CREATE INDEX IF NOT EXISTS idx_outlines_metadata ON outlines USING GIN(metadata);

-- scene_cards表的content字段
CREATE INDEX IF NOT EXISTS idx_scene_cards_content ON scene_cards USING GIN(content);

-- character_interactions表的content字段
CREATE INDEX IF NOT EXISTS idx_character_interactions_content ON character_interactions USING GIN(content);

-- genesis_sessions表的JSON字段
CREATE INDEX IF NOT EXISTS idx_genesis_sessions_initial_input ON genesis_sessions USING GIN(initial_user_input);
CREATE INDEX IF NOT EXISTS idx_genesis_sessions_final_settings ON genesis_sessions USING GIN(final_settings);

-- genesis_steps表的JSON字段
CREATE INDEX IF NOT EXISTS idx_genesis_steps_ai_output ON genesis_steps USING GIN(ai_output);

-- 4. 复合索引（用于常见查询模式）

-- 按小说和Agent类型查询活动
CREATE INDEX IF NOT EXISTS idx_characters_novel_agent ON characters(novel_id, created_by_agent_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_worldview_entries_novel_agent ON worldview_entries(novel_id, created_by_agent_type, created_at DESC);

-- 按章节和版本查询
CREATE INDEX IF NOT EXISTS idx_reviews_chapter_agent ON reviews(chapter_id, agent_type, created_at DESC);

-- 按时间范围查询
CREATE INDEX IF NOT EXISTS idx_chapter_versions_time_range ON chapter_versions(created_at DESC, created_by_agent_type);

-- 5. 数据完整性约束

-- 注意: 原本想确保published_version_id指向的版本属于同一章节，但PostgreSQL不允许CHECK约束中使用跨表子查询
-- 改为依赖现有的外键约束 FOREIGN KEY (published_version_id) REFERENCES chapter_versions(id) 
-- 如需额外的"版本属于同一章节"校验，应通过触发器或应用层实现
-- ALTER TABLE chapters 
--     DROP CONSTRAINT IF EXISTS check_published_version;

-- 确保章节版本号的连续性
CREATE OR REPLACE FUNCTION validate_chapter_version_sequence()
RETURNS TRIGGER AS $$
BEGIN
    -- 检查版本号是否合理（应该是递增的）
    IF NEW.version_number <= 0 THEN
        RAISE EXCEPTION '章节版本号必须大于0';
    END IF;
    
    -- 对于新版本，检查是否存在前一个版本（除了版本1）
    IF NEW.version_number > 1 AND TG_OP = 'INSERT' THEN
        IF NOT EXISTS (
            SELECT 1 FROM chapter_versions 
            WHERE chapter_id = NEW.chapter_id AND version_number = NEW.version_number - 1
        ) THEN
            RAISE EXCEPTION '章节版本号必须连续，缺少版本号 %', NEW.version_number - 1;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_chapter_version_sequence
    BEFORE INSERT OR UPDATE ON chapter_versions
    FOR EACH ROW
    EXECUTE FUNCTION validate_chapter_version_sequence();

-- 确保story_arcs的章节范围合理
ALTER TABLE story_arcs 
    ADD CONSTRAINT check_chapter_range 
    CHECK (start_chapter_number IS NULL OR end_chapter_number IS NULL OR start_chapter_number <= end_chapter_number);

-- 确保reviews的评分范围合理
ALTER TABLE reviews 
    ADD CONSTRAINT check_score_range 
    CHECK (score IS NULL OR (score >= 0.0 AND score <= 10.0));

-- 确保agent_activities的时间逻辑合理
ALTER TABLE agent_activities 
    ADD CONSTRAINT check_activity_time_logic 
    CHECK (completed_at IS NULL OR completed_at >= started_at);

-- 6. 唯一性约束（避免重复数据）

-- 注意：原来这里试图用子查询创建唯一索引，但PostgreSQL不支持这种语法
-- 改为在触发器脚本中用触发器实现同一章节同一Agent类型只有一个最新大纲的约束
-- 这里创建一个基本的索引用于性能
CREATE INDEX IF NOT EXISTS idx_outlines_chapter_agent_created 
    ON outlines(chapter_id, created_by_agent_type, created_at DESC);

-- 7. 部分索引（提高特定查询的性能）

-- 只为活跃的配置创建索引
CREATE INDEX IF NOT EXISTS idx_agent_configurations_active_only 
    ON agent_configurations(novel_id, agent_type, config_key) 
    WHERE is_active = true;

-- 只为未完成的工作流创建索引
CREATE INDEX IF NOT EXISTS idx_workflow_runs_active 
    ON workflow_runs(novel_id, workflow_type, started_at DESC) 
    WHERE status IN ('PENDING', 'RUNNING', 'PAUSED');

-- 只为待处理的事件创建索引
CREATE INDEX IF NOT EXISTS idx_events_pending 
    ON events(event_type, created_at) 
    WHERE status IN ('PENDING', 'PROCESSING');

-- 只为失败的活动创建索引（用于重试逻辑）
CREATE INDEX IF NOT EXISTS idx_agent_activities_failed 
    ON agent_activities(agent_type, activity_type, started_at DESC) 
    WHERE status = 'FAILED';

-- 8. 外键约束检查函数（用于无外键表的引用完整性验证）

-- 验证workflow_run_id引用的有效性
CREATE OR REPLACE FUNCTION validate_workflow_run_references()
RETURNS void AS $$
DECLARE
    invalid_count INTEGER;
BEGIN
    -- 检查agent_activities表中的无效workflow_run_id
    SELECT COUNT(*) INTO invalid_count
    FROM agent_activities aa
    WHERE aa.workflow_run_id IS NOT NULL 
    AND NOT EXISTS (SELECT 1 FROM workflow_runs wr WHERE wr.id = aa.workflow_run_id);
    
    IF invalid_count > 0 THEN
        RAISE WARNING '发现 % 条agent_activities记录引用了不存在的workflow_run_id', invalid_count;
    END IF;
    
    -- 检查events表中的无效workflow_run_id
    SELECT COUNT(*) INTO invalid_count
    FROM events e
    WHERE e.workflow_run_id IS NOT NULL 
    AND NOT EXISTS (SELECT 1 FROM workflow_runs wr WHERE wr.id = e.workflow_run_id);
    
    IF invalid_count > 0 THEN
        RAISE WARNING '发现 % 条events记录引用了不存在的workflow_run_id', invalid_count;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_workflow_run_references() IS '验证无外键表中workflow_run_id引用的有效性';

-- 9. 性能监控索引使用统计

-- 创建视图来监控索引使用情况
CREATE OR REPLACE VIEW index_usage_stats AS
SELECT 
    i.schemaname,
    i.tablename,
    i.indexname,
    i.idx_tup_read,
    i.idx_tup_fetch,
    i.idx_scan,
    t.seq_scan,
    ROUND(100.0 * i.idx_scan / NULLIF(i.idx_scan + t.seq_scan, 0), 2) AS index_usage_pct
FROM pg_stat_user_indexes i
JOIN pg_stat_user_tables t ON (i.relid = t.relid)
ORDER BY i.idx_scan DESC;

COMMENT ON VIEW index_usage_stats IS '索引使用统计视图：监控索引的使用效率，包含索引扫描与顺序扫描的比例';