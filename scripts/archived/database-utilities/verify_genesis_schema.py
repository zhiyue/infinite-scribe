#!/usr/bin/env python3
"""
数据库模式验证脚本
验证AI-Driven Genesis Studio的六个核心表是否正确创建，包括约束和索引
"""

import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Inspector
from src.core.config import settings


class SchemaValidator:
    """数据库模式验证器"""

    def __init__(self):
        # 创建同步引擎用于验证
        database_url = settings.database.postgres_url.replace("+asyncpg", "")
        self.engine = create_engine(database_url)
        self.inspector: Inspector = inspect(self.engine)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all_tables(self) -> bool:
        """验证所有核心表"""
        print("🔍 开始验证AI-Driven Genesis Studio数据库模式...")

        # 验证六个核心表
        core_tables = [
            "domain_events",
            "command_inbox",
            "async_tasks",
            "event_outbox",
            "flow_resume_handles",
            "genesis_sessions",
        ]

        success = True
        for table_name in core_tables:
            print(f"\n📋 验证表: {table_name}")
            if not self._validate_table_exists(table_name):
                success = False
                continue

            if not self._validate_table_structure(table_name):
                success = False

        return success

    def _validate_table_exists(self, table_name: str) -> bool:
        """验证表是否存在"""
        if table_name not in self.inspector.get_table_names():
            self.errors.append(f"❌ 表 {table_name} 不存在")
            return False
        print(f"✅ 表 {table_name} 存在")
        return True

    def _validate_table_structure(self, table_name: str) -> bool:
        """验证表结构"""
        success = True

        # 验证列
        if not self._validate_columns(table_name):
            success = False

        # 验证索引
        if not self._validate_indexes(table_name):
            success = False

        # 验证约束
        if not self._validate_constraints(table_name):
            success = False

        return success

    def _validate_columns(self, table_name: str) -> bool:
        """验证表列"""
        columns = self.inspector.get_columns(table_name)
        column_names = [col["name"] for col in columns]

        # 定义每个表的必需列
        required_columns = {
            "domain_events": [
                "id",
                "event_id",
                "correlation_id",
                "causation_id",
                "event_type",
                "event_version",
                "aggregate_type",
                "aggregate_id",
                "payload",
                "metadata",
                "created_at",
            ],
            "command_inbox": [
                "id",
                "session_id",
                "command_type",
                "idempotency_key",
                "payload",
                "status",
                "error_message",
                "retry_count",
                "created_at",
                "updated_at",
            ],
            "async_tasks": [
                "id",
                "task_type",
                "triggered_by_command_id",
                "status",
                "progress",
                "input_data",
                "result_data",
                "error_data",
                "execution_node",
                "retry_count",
                "max_retries",
                "started_at",
                "completed_at",
                "created_at",
                "updated_at",
            ],
            "event_outbox": [
                "id",
                "topic",
                "key",
                "partition_key",
                "payload",
                "headers",
                "status",
                "retry_count",
                "max_retries",
                "last_error",
                "scheduled_at",
                "sent_at",
                "created_at",
            ],
            "flow_resume_handles": [
                "id",
                "correlation_id",
                "flow_run_id",
                "task_name",
                "resume_handle",
                "status",
                "resume_payload",
                "timeout_seconds",
                "context_data",
                "expires_at",
                "resumed_at",
                "created_at",
                "updated_at",
            ],
            "genesis_sessions": [
                "id",
                "novel_id",
                "user_id",
                "status",
                "current_stage",
                "confirmed_data",
                "version",
                "created_at",
                "updated_at",
            ],
        }

        success = True
        required = required_columns.get(table_name, [])

        for col in required:
            if col not in column_names:
                self.errors.append(f"❌ 表 {table_name} 缺少列: {col}")
                success = False

        if success:
            print(f"✅ 表 {table_name} 列结构正确")

        return success

    def _validate_indexes(self, table_name: str) -> bool:
        """验证索引"""
        indexes = self.inspector.get_indexes(table_name)
        index_names = [idx["name"] for idx in indexes]

        # 定义每个表的关键索引
        required_indexes = {
            "domain_events": [
                "idx_domain_events_aggregate",
                "idx_domain_events_event_type",
                "idx_domain_events_created_at",
            ],
            "command_inbox": [
                "idx_command_inbox_unique_pending_command",
                "idx_command_inbox_session_id",
                "idx_command_inbox_status",
            ],
            "async_tasks": ["idx_async_tasks_status", "idx_async_tasks_task_type", "idx_async_tasks_created_at"],
            "event_outbox": ["idx_event_outbox_status", "idx_event_outbox_topic", "idx_event_outbox_created_at"],
            "flow_resume_handles": [
                "idx_flow_resume_handles_unique_correlation",
                "idx_flow_resume_handles_correlation_id",
                "idx_flow_resume_handles_status",
            ],
            "genesis_sessions": [
                "idx_genesis_sessions_user_id",
                "idx_genesis_sessions_status",
                "idx_genesis_sessions_current_stage",
            ],
        }

        success = True
        required = required_indexes.get(table_name, [])

        for idx in required:
            if idx not in index_names:
                self.warnings.append(f"⚠️  表 {table_name} 缺少索引: {idx}")
                # 索引缺失不算致命错误，只是警告

        print(f"✅ 表 {table_name} 索引检查完成")
        return success

    def _validate_constraints(self, table_name: str) -> bool:
        """验证约束"""
        # 获取检查约束
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT conname, pg_get_constraintdef(oid) as definition
                FROM pg_constraint 
                WHERE conrelid = (
                    SELECT oid FROM pg_class 
                    WHERE relname = :table_name
                ) AND contype = 'c'
            """),
                {"table_name": table_name},
            )

            constraints = result.fetchall()

        # 定义每个表的关键约束
        required_constraints = {
            "command_inbox": ["check_retry_count_non_negative", "check_failed_has_error_message"],
            "async_tasks": ["check_progress_range", "check_retry_count_valid", "check_max_retries_non_negative"],
            "event_outbox": ["check_retry_count_valid", "check_max_retries_non_negative", "check_sent_has_timestamp"],
            "flow_resume_handles": [
                "check_timeout_positive",
                "check_expires_after_created",
                "check_resumed_has_timestamp",
            ],
            "genesis_sessions": ["check_genesis_stage_progression", "check_completed_has_novel"],
        }

        success = True
        required = required_constraints.get(table_name, [])
        constraint_names = [c[0] for c in constraints]

        for constraint in required:
            if constraint not in constraint_names:
                self.warnings.append(f"⚠️  表 {table_name} 缺少约束: {constraint}")
                # 约束缺失不算致命错误，只是警告

        print(f"✅ 表 {table_name} 约束检查完成")
        return success

    def _validate_unique_constraints(self, table_name: str) -> bool:
        """验证唯一约束"""
        unique_constraints = self.inspector.get_unique_constraints(table_name)

        # 定义关键唯一约束
        required_unique = {
            "command_inbox": ["idempotency_key"],
            "domain_events": ["event_id"],
            "flow_resume_handles": ["correlation_id"],
        }

        success = True
        required = required_unique.get(table_name, [])

        for constraint_cols in required:
            found = False
            for uc in unique_constraints:
                if set(uc["column_names"]) == {constraint_cols}:
                    found = True
                    break

            if not found:
                self.errors.append(f"❌ 表 {table_name} 缺少唯一约束: {constraint_cols}")
                success = False

        return success

    def print_summary(self) -> bool:
        """打印验证摘要"""
        print("\n" + "=" * 60)
        print("📊 数据库模式验证摘要")
        print("=" * 60)

        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"  {warning}")

        if not self.errors and not self.warnings:
            print("\n🎉 所有验证通过！数据库模式完全符合要求。")
            return True
        elif not self.errors:
            print(f"\n✅ 核心验证通过，但有 {len(self.warnings)} 个警告需要注意。")
            return True
        else:
            print(f"\n💥 验证失败！发现 {len(self.errors)} 个错误。")
            return False


def main():
    """主函数"""
    try:
        validator = SchemaValidator()
        success = validator.validate_all_tables()
        final_result = validator.print_summary()

        if not final_result:
            sys.exit(1)
        else:
            print("\n🚀 数据库模式验证完成！")
            sys.exit(0)

    except Exception as e:
        print(f"💥 验证过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
