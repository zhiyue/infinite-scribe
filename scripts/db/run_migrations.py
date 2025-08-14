#!/usr/bin/env python3
"""
运行数据库迁移脚本
按照正确的顺序执行所有迁移文件
"""

import asyncio
import sys
from pathlib import Path

import asyncpg


async def run_migrations():
    """运行所有数据库迁移脚本"""
    # 数据库连接配置
    conn_params = {
        "host": "192.168.2.201",
        "port": 5432,
        "database": "infinite_scribe",
        "user": "postgres",
        "password": "devPostgres123!",
    }

    # 迁移脚本目录
    migration_dir = Path("infrastructure/docker/init/postgres")

    # 需要执行的迁移脚本（按顺序）
    migration_files = [
        "05-domain-events.sql",
        "06-command-inbox.sql",
        "07-async-tasks.sql",
        "08-event-outbox.sql",
        "09-flow-resume-handles.sql",
    ]

    try:
        # 创建数据库连接
        conn = await asyncpg.connect(**conn_params)
        print("成功连接到PostgreSQL数据库")
        print("=" * 60)

        # 执行每个迁移脚本
        for migration_file in migration_files:
            file_path = migration_dir / migration_file

            if not file_path.exists():
                print(f"✗ 迁移文件不存在: {file_path}")
                continue

            print(f"\n执行迁移脚本: {migration_file}")
            print("-" * 40)

            try:
                # 读取SQL文件内容
                with open(file_path, encoding="utf-8") as f:
                    sql_content = f.read()

                # 执行SQL脚本
                await conn.execute(sql_content)
                print(f"✓ {migration_file} 执行成功")

            except Exception as e:
                print(f"✗ {migration_file} 执行失败: {e}")
                # 继续执行下一个脚本

        # 验证表是否创建成功
        print("\n" + "=" * 60)
        print("验证表创建结果:")

        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name IN ('domain_events', 'command_inbox', 'async_tasks', 
                              'event_outbox', 'flow_resume_handles')
            ORDER BY table_name;
        """

        tables = await conn.fetch(tables_query)
        for row in tables:
            print(f"  ✓ {row['table_name']}")

        # 关闭连接
        await conn.close()

        print("\n迁移完成!")
        return True

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)
