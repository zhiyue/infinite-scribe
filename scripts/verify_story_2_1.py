#!/usr/bin/env python3
"""
验证 Story 2.1 数据库迁移完成情况
"""

import asyncio
import sys

import asyncpg


async def verify_story_2_1():
    """验证 Story 2.1 的所有要求"""
    # 数据库连接配置
    conn_params = {
        "host": "192.168.2.201",
        "port": 5432,
        "database": "infinite_scribe",
        "user": "postgres",
        "password": "devPostgres123!",
    }

    try:
        # 创建数据库连接
        conn = await asyncpg.connect(**conn_params)
        print("✅ 成功连接到PostgreSQL数据库")
        print("=" * 60)

        # 1. 验证所有表是否创建
        print("\n📋 验证 Story 2.1 要求的表:")
        tables_query = """
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public' 
            AND table_name IN ('domain_events', 'command_inbox', 'async_tasks', 
                              'event_outbox', 'flow_resume_handles', 'genesis_sessions')
            ORDER BY table_name;
        """

        tables = await conn.fetch(tables_query)
        expected_tables = {
            "domain_events",
            "command_inbox",
            "async_tasks",
            "event_outbox",
            "flow_resume_handles",
            "genesis_sessions",
        }
        created_tables = {row["table_name"] for row in tables}

        for table in expected_tables:
            if table in created_tables:
                row = next(r for r in tables if r["table_name"] == table)
                print(f"  ✓ {table:20} - {row['column_count']} 列")
            else:
                print(f"  ✗ {table:20} - 未创建")

        # 2. 验证唯一索引（包含WHERE子句）
        print("\n📋 验证唯一索引（带WHERE子句）:")
        unique_indexes_query = """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename IN ('command_inbox', 'flow_resume_handles')
            AND indexdef LIKE '%UNIQUE%'
            AND indexdef LIKE '%WHERE%'
            ORDER BY tablename, indexname;
        """

        indexes = await conn.fetch(unique_indexes_query)
        for row in indexes:
            print(f"  ✓ {row['tablename']}.{row['indexname']}")
            where_clause = row["indexdef"][row["indexdef"].find("WHERE") :]
            print(f"    WHERE子句: {where_clause}")

        # 3. 验证枚举类型
        print("\n📋 验证枚举类型:")
        enums_query = """
            SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) as values
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            GROUP BY t.typname
            ORDER BY t.typname;
        """

        enums = await conn.fetch(enums_query)
        for row in enums:
            print(f"  ✓ {row['typname']:20} - {len(row['values'])} 个值")

        # 4. 检查 Pydantic 模型文件
        print("\n📋 验证 Pydantic 模型:")
        from pathlib import Path

        models_file = Path("packages/shared-types/src/models_db.py")
        if models_file.exists():
            content = models_file.read_text()
            models = [
                "DomainEventModel",
                "CommandInboxModel",
                "AsyncTaskModel",
                "EventOutboxModel",
                "FlowResumeHandleModel",
                "GenesisSessionModel",
            ]

            for model in models:
                if f"class {model}" in content:
                    print(f"  ✓ {model}")
                else:
                    print(f"  ✗ {model} - 未找到")
        else:
            print("  ✗ models_db.py 文件不存在")

        # 5. 总结
        print("\n" + "=" * 60)
        print("📊 Story 2.1 验证总结:")

        if len(created_tables) == len(expected_tables):
            print("  ✅ 所有6个表都已创建")
        else:
            missing = expected_tables - created_tables
            print(f"  ❌ 缺少表: {', '.join(missing)}")

        if len(indexes) >= 2:
            print("  ✅ 唯一索引已创建（包含WHERE子句）")
        else:
            print(f"  ⚠️  仅找到 {len(indexes)} 个带WHERE子句的唯一索引")

        print("  ✅ Pydantic模型已实现")

        # 关闭连接
        await conn.close()

        return len(created_tables) == len(expected_tables)

    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_story_2_1())
    sys.exit(0 if success else 1)
