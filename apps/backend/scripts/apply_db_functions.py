#!/usr/bin/env python
"""应用数据库触发器和函数"""

import asyncio

from sqlalchemy import text
from src.database import engine


async def apply_db_functions():
    """分步骤应用数据库函数和触发器"""

    # SQL 语句列表
    statements = [
        # 1. 更新 updated_at 时间戳的触发器函数
        (
            "创建 update_updated_at_column 函数",
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
            """,
        ),
        # 2. 版本号自增触发器函数
        (
            "创建 increment_version 函数",
            """
            CREATE OR REPLACE FUNCTION increment_version()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.version = OLD.version + 1;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
            """,
        ),
        # 3. 防止修改领域事件的触发器函数
        (
            "创建 prevent_domain_event_modification 函数",
            """
            CREATE OR REPLACE FUNCTION prevent_domain_event_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION '领域事件不可修改';
            END;
            $$ language 'plpgsql'
            """,
        ),
        # 4. 更新小说完成章节数的函数
        (
            "创建 update_novel_completed_chapters 函数",
            """
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
            $$ language 'plpgsql'
            """,
        ),
        # 5. 事件发件箱函数
        (
            "创建 get_pending_outbox_messages 函数",
            """
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
            $$
            """,
        ),
        (
            "创建 mark_outbox_message_sent 函数",
            """
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
            $$
            """,
        ),
        (
            "创建 mark_outbox_message_failed 函数",
            """
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
            $$
            """,
        ),
        (
            "创建 cleanup_sent_outbox_messages 函数",
            """
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
            $$
            """,
        ),
        # 6. 创建异步任务统计视图
        (
            "创建 async_task_statistics 视图",
            """
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
            GROUP BY task_type, status
            """,
        ),
    ]

    # 动态生成的触发器
    dynamic_triggers = []

    # updated_at 触发器
    tables_with_updated_at = [
        "novels",
        "chapters",
        "characters",
        "worldview_entries",
        "story_arcs",
        "conversation_sessions",
        "command_inbox",
        "async_tasks",
        "flow_resume_handles",
    ]

    for table in tables_with_updated_at:
        dynamic_triggers.append(
            (
                f"创建 {table} 表的 updated_at 触发器",
                f"""
            CREATE OR REPLACE TRIGGER set_timestamp_{table}
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
            """,
            )
        )

    # version 触发器
    tables_with_version = [
        "novels",
        "chapters",
        "characters",
        "worldview_entries",
        "story_arcs",
        "conversation_sessions",
    ]

    for table in tables_with_version:
        dynamic_triggers.append(
            (
                f"创建 {table} 表的 version 触发器",
                f"""
            CREATE OR REPLACE TRIGGER increment_version_{table}_trigger
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            WHEN (OLD.* IS DISTINCT FROM NEW.*)
            EXECUTE FUNCTION increment_version()
            """,
            )
        )

    # 特定触发器
    dynamic_triggers.extend(
        [
            (
                "创建防止修改领域事件的触发器",
                """
            CREATE OR REPLACE TRIGGER prevent_domain_event_update
            BEFORE UPDATE OR DELETE ON domain_events
            FOR EACH ROW
            EXECUTE FUNCTION prevent_domain_event_modification()
            """,
            ),
            (
                "创建章节状态变更触发器",
                """
            CREATE OR REPLACE TRIGGER update_novel_progress_on_chapter_change
            AFTER INSERT OR UPDATE OF status OR DELETE ON chapters
            FOR EACH ROW
            EXECUTE FUNCTION update_novel_completed_chapters()
            """,
            ),
        ]
    )

    # 执行所有语句
    all_statements = statements + dynamic_triggers
    success_count = 0

    async with engine.begin() as conn:
        for description, sql in all_statements:
            try:
                await conn.execute(text(sql))
                print(f"✅ {description}")
                success_count += 1
            except Exception as e:
                print(f"❌ {description}")
                print(f"   错误: {e}")

    print(f"\n📊 执行结果: {success_count}/{len(all_statements)} 成功")

    # 验证创建的对象
    async with engine.begin() as conn:
        # 检查函数
        result = await conn.execute(
            text("""
            SELECT proname
            FROM pg_proc
            JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid
            WHERE nspname = 'public'
            AND proname IN (
                'update_updated_at_column',
                'increment_version',
                'prevent_domain_event_modification',
                'update_novel_completed_chapters',
                'get_pending_outbox_messages',
                'mark_outbox_message_sent',
                'mark_outbox_message_failed',
                'cleanup_sent_outbox_messages'
            )
            ORDER BY proname
        """)
        )

        functions = [row[0] for row in result]
        print(f"\n✅ 已创建的函数 ({len(functions)}):")
        for func in functions:
            print(f"    ✓ {func}()")

        # 检查触发器
        result = await conn.execute(
            text("""
            SELECT
                c.relname as tablename,
                t.tgname as triggername
            FROM pg_trigger t
            JOIN pg_class c ON t.tgrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = 'public'
            AND t.tgname NOT LIKE 'RI_ConstraintTrigger%'
            ORDER BY c.relname, t.tgname
        """)
        )

        triggers = result.fetchall()
        if triggers:
            print(f"\n✅ 已创建的触发器 ({len(triggers)}):")
            for table, trigger in triggers:
                print(f"    ✓ {table}.{trigger}")

        # 检查视图
        result = await conn.execute(
            text("""
            SELECT viewname
            FROM pg_views
            WHERE schemaname = 'public'
            ORDER BY viewname
        """)
        )

        views = [row[0] for row in result]
        if views:
            print(f"\n✅ 已创建的视图 ({len(views)}):")
            for view in views:
                print(f"    ✓ {view}")


if __name__ == "__main__":
    asyncio.run(apply_db_functions())
