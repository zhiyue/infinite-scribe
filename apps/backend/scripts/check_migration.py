#!/usr/bin/env python
"""检查 Alembic migration 是否可以正常应用（仅 SQL 生成，不实际执行）"""

import subprocess
import sys


def check_migration():
    """检查 migration 文件是否可以生成正确的 SQL"""
    print("检查 Alembic migration...")

    try:
        # 生成 SQL 但不执行（使用 --sql 选项）
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head", "--sql"],
            capture_output=True,
            text=True,
            check=True,
        )

        print("✅ Migration SQL 生成成功！")
        print("\n生成的 SQL 预览（前 1000 字符）：")
        print("-" * 80)
        print(result.stdout[:1000])
        if len(result.stdout) > 1000:
            print("\n... (更多内容已省略)")
        print("-" * 80)

        # 统计创建的表数量
        create_table_count = result.stdout.count("CREATE TABLE")
        create_index_count = result.stdout.count("CREATE INDEX")
        create_type_count = result.stdout.count("CREATE TYPE")

        print("\n统计信息：")
        print(f"- 创建表数量: {create_table_count}")
        print(f"- 创建索引数量: {create_index_count}")
        print(f"- 创建枚举类型数量: {create_type_count}")

        return True

    except subprocess.CalledProcessError as e:
        print("❌ Migration 检查失败！")
        print(f"错误信息: {e.stderr}")
        return False


if __name__ == "__main__":
    success = check_migration()
    sys.exit(0 if success else 1)
