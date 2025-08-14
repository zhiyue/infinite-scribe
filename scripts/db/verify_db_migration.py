#!/usr/bin/env python3
"""
验证数据库迁移脚本
用于检查Story 2.1要求的所有表和索引是否正确创建
"""

import asyncio
import asyncpg
import sys


async def verify_database():
    """验证数据库表和索引是否正确创建"""
    # 数据库连接配置
    conn_params = {
        'host': '192.168.2.201',
        'port': 5432,
        'database': 'infinite_scribe',
        'user': 'postgres',
        'password': 'devPostgres123!'
    }
    
    try:
        # 创建数据库连接
        conn = await asyncpg.connect(**conn_params)
        
        print("成功连接到PostgreSQL数据库")
        print("=" * 60)
        
        # 检查所需的表是否存在
        required_tables = [
            'domain_events',
            'command_inbox',
            'async_tasks',
            'event_outbox',
            'flow_resume_handles',
            'genesis_sessions'
        ]
        
        # 查询现有表
        existing_tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name = ANY($1::text[])
            ORDER BY table_name;
        """
        
        existing_tables = await conn.fetch(existing_tables_query, required_tables)
        existing_table_names = [row['table_name'] for row in existing_tables]
        
        print(f"检查必需的表 ({len(required_tables)}个):")
        all_tables_exist = True
        for table in required_tables:
            if table in existing_table_names:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} - 未找到")
                all_tables_exist = False
        
        print("\n" + "=" * 60)
        
        # 检查关键索引
        print("检查唯一性约束索引:")
        
        # 检查 command_inbox 的唯一索引
        command_inbox_index_query = """
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'command_inbox' 
            AND indexname = 'idx_command_inbox_unique_pending_command';
        """
        command_inbox_index = await conn.fetchrow(command_inbox_index_query)
        
        if command_inbox_index:
            print(f"  ✓ command_inbox 唯一性约束索引存在")
            print(f"    定义: {command_inbox_index['indexdef']}")
            # 验证索引定义是否包含WHERE子句
            if "WHERE" in command_inbox_index['indexdef'] and "status" in command_inbox_index['indexdef']:
                print(f"    ✓ 包含正确的WHERE子句")
            else:
                print(f"    ✗ WHERE子句不正确")
        else:
            print(f"  ✗ command_inbox 唯一性约束索引未找到")
        
        # 检查 flow_resume_handles 的唯一索引
        flow_handles_index_query = """
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'flow_resume_handles' 
            AND indexname = 'idx_flow_resume_handles_unique_correlation';
        """
        flow_handles_index = await conn.fetchrow(flow_handles_index_query)
        
        if flow_handles_index:
            print(f"\n  ✓ flow_resume_handles 唯一性约束索引存在")
            print(f"    定义: {flow_handles_index['indexdef']}")
            # 验证索引定义是否包含WHERE子句
            if "WHERE" in flow_handles_index['indexdef'] and "status" in flow_handles_index['indexdef']:
                print(f"    ✓ 包含正确的WHERE子句")
            else:
                print(f"    ✗ WHERE子句不正确")
        else:
            print(f"\n  ✗ flow_resume_handles 唯一性约束索引未找到")
        
        print("\n" + "=" * 60)
        
        # 检查表的列数
        print("检查表结构:")
        for table in existing_table_names:
            column_count_query = """
                SELECT COUNT(*) as column_count
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = $1;
            """
            result = await conn.fetchrow(column_count_query, table)
            print(f"  {table}: {result['column_count']} 列")
        
        # 关闭连接
        await conn.close()
        
        print("\n" + "=" * 60)
        if all_tables_exist:
            print("✓ 所有必需的表都已成功创建")
            return True
        else:
            print("✗ 部分表未创建，请检查迁移脚本")
            return False
            
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_database())
    sys.exit(0 if success else 1)