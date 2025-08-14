#!/usr/bin/env python
"""显示数据库表的详细信息"""

import asyncio

from sqlalchemy import text
from src.database import engine


async def show_table_info():
    """显示选定表的列信息"""
    tables_to_check = ["novels", "chapters", "domain_events", "command_inbox"]

    for table_name in tables_to_check:
        print(f"\n📋 表: {table_name}")
        print("=" * 80)

        async with engine.begin() as conn:
            # 获取列信息
            result = await conn.execute(
                text("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                    ORDER BY ordinal_position
                """),
                {"table_name": table_name},
            )

            columns = result.fetchall()

            print(f"{'列名':<30} {'类型':<20} {'可空':<6} {'默认值'}")
            print("-" * 80)

            for col in columns:
                col_name, data_type, is_nullable, default = col
                nullable = "是" if is_nullable == "YES" else "否"
                default_str = str(default)[:30] if default else "-"

                print(f"{col_name:<30} {data_type:<20} {nullable:<6} {default_str}")

            # 获取索引信息
            result = await conn.execute(
                text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename = :table_name
                    ORDER BY indexname
                """),
                {"table_name": table_name},
            )

            indexes = [row[0] for row in result]

            if indexes:
                print(f"\n索引 ({len(indexes)}):")
                for idx in indexes:
                    print(f"  - {idx}")


if __name__ == "__main__":
    asyncio.run(show_table_info())
