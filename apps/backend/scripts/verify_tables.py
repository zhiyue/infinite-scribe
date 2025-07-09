#!/usr/bin/env python
"""验证数据库中的表是否已成功创建"""

import asyncio

from sqlalchemy import text
from src.database import engine
from src.models.orm_models import Base


async def verify_tables():
    """验证所有 ORM 定义的表是否存在于数据库中"""
    print("验证数据库表...")

    # 获取所有 ORM 定义的表名
    orm_tables = {table.name for table in Base.metadata.tables.values()}

    # 查询数据库中实际存在的表
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT IN ('alembic_version')
                ORDER BY tablename
            """)
        )
        db_tables = {row[0] for row in result}

    print(f"\n📊 ORM 定义的表数量: {len(orm_tables)}")
    print(f"📊 数据库中的表数量: {len(db_tables)}")

    # 找出差异
    missing_tables = orm_tables - db_tables
    extra_tables = db_tables - orm_tables

    if missing_tables:
        print(f"\n❌ 缺失的表 ({len(missing_tables)}):")
        for table in sorted(missing_tables):
            print(f"   - {table}")
    else:
        print("\n✅ 所有 ORM 定义的表都已创建")

    if extra_tables:
        print(f"\n⚠️  额外的表 ({len(extra_tables)}):")
        for table in sorted(extra_tables):
            print(f"   - {table}")

    # 列出所有成功创建的表
    created_tables = orm_tables & db_tables
    if created_tables:
        print(f"\n✅ 成功创建的表 ({len(created_tables)}):")

        # 按类别分组显示
        core_tables = [
            "novels",
            "chapters",
            "chapter_versions",
            "characters",
            "worldview_entries",
            "story_arcs",
            "reviews",
        ]
        genesis_tables = ["genesis_sessions", "concept_templates"]
        arch_tables = ["domain_events", "command_inbox", "async_tasks", "event_outbox", "flow_resume_handles"]
        auth_tables = ["users", "sessions", "email_verifications"]

        print("\n  核心业务表:")
        for table in core_tables:
            if table in created_tables:
                print(f"    ✓ {table}")

        print("\n  创世流程表:")
        for table in genesis_tables:
            if table in created_tables:
                print(f"    ✓ {table}")

        print("\n  架构机制表:")
        for table in arch_tables:
            if table in created_tables:
                print(f"    ✓ {table}")

        print("\n  用户认证表:")
        for table in auth_tables:
            if table in created_tables:
                print(f"    ✓ {table}")

    # 检查枚举类型
    async with engine.begin() as conn:
        result = await conn.execute(
            text("""
                SELECT typname
                FROM pg_type
                WHERE typtype = 'e'
                AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                ORDER BY typname
            """)
        )
        enum_types = [row[0] for row in result]

    if enum_types:
        print(f"\n📊 创建的枚举类型 ({len(enum_types)}):")
        for enum in enum_types:
            print(f"    ✓ {enum}")

    return len(missing_tables) == 0


if __name__ == "__main__":
    success = asyncio.run(verify_tables())
    exit(0 if success else 1)
