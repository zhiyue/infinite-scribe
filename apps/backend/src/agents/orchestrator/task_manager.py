"""任务管理模块

处理编排器的异步任务生命周期管理。
提供具有幂等性保护的创建和完成操作。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from src.common.utils.datetime_utils import utc_now
from src.db.sql.session import create_sql_session
from src.models.workflow import AsyncTask
from src.schemas.enums import TaskStatus


class TaskIdempotencyChecker:
    """任务幂等性检查器，处理任务的幂等性验证。"""

    @staticmethod
    async def check_existing_task(trig_cmd_id: UUID, task_type: str, db_session) -> AsyncTask | None:
        """检查是否已存在RUNNING/PENDING状态的任务，以防止重复创建。

        Args:
            trig_cmd_id: 触发命令ID
            task_type: 任务类型
            db_session: 数据库会话对象

        Returns:
            如果存在则返回AsyncTask对象，否则返回None
        """
        existing_stmt = select(AsyncTask).where(
            and_(
                AsyncTask.triggered_by_command_id == trig_cmd_id,
                AsyncTask.task_type == task_type,
                AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
            )
        )
        return await db_session.scalar(existing_stmt)


class TaskCreator:
    """任务创建器，处理任务创建逻辑。"""

    def __init__(self, logger):
        """初始化任务创建器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger
        self.idempotency_checker = TaskIdempotencyChecker()

    async def create_task(
        self, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """创建AsyncTask行来跟踪能力执行，具有幂等性保护。

        Args:
            correlation_id: 关联ID
            session_id: 会话ID
            task_type: 任务类型
            input_data: 输入数据
        """
        self.log.info(
            "orchestrator_creating_async_task",
            correlation_id=correlation_id,
            session_id=session_id,
            task_type=task_type,
            input_data_keys=list(input_data.keys()) if input_data else [],
        )

        if not task_type:
            self.log.warning(
                "orchestrator_async_task_skipped",
                reason="empty_task_type",
                correlation_id=correlation_id,
                session_id=session_id,
            )
            return

        trig_cmd_id = self._parse_correlation_id(correlation_id)
        if correlation_id and not trig_cmd_id:
            return  # 已在_parse_correlation_id中记录日志

        async with create_sql_session() as db:
            # 检查现有的RUNNING/PENDING任务以防止重复
            if trig_cmd_id:
                existing_task = await self.idempotency_checker.check_existing_task(trig_cmd_id, task_type, db)
                if existing_task:
                    self.log.info(
                        "async_task_already_exists",
                        correlation_id=correlation_id,
                        task_type=task_type,
                        existing_task_id=str(existing_task.id),
                        existing_status=existing_task.status.value
                        if hasattr(existing_task.status, "value")
                        else str(existing_task.status),
                    )
                    return

            await self._create_new_task(trig_cmd_id, session_id, task_type, input_data, db)

    def _parse_correlation_id(self, correlation_id: str | None) -> UUID | None:
        """将correlation_id字符串解析为UUID，带有错误处理。

        Args:
            correlation_id: 关联ID字符串

        Returns:
            解析后的UUID或None
        """
        if not correlation_id:
            return None

        try:
            trig_cmd_id = UUID(str(correlation_id))
            self.log.debug(
                "orchestrator_async_task_correlation_parsed",
                correlation_id=correlation_id,
                trig_cmd_id=str(trig_cmd_id),
            )
            return trig_cmd_id
        except Exception as e:
            self.log.warning(
                "orchestrator_async_task_correlation_parse_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return None

    async def _create_new_task(
        self, trig_cmd_id: UUID | None, session_id: str, task_type: str, input_data: dict, db_session
    ) -> None:
        """在数据库中创建新的AsyncTask。

        Args:
            trig_cmd_id: 触发命令ID
            session_id: 会话ID
            task_type: 任务类型
            input_data: 输入数据
            db_session: 数据库会话对象
        """
        self.log.info(
            "orchestrator_creating_new_async_task",
            task_type=task_type,
            trig_cmd_id=str(trig_cmd_id) if trig_cmd_id else None,
            session_id=session_id,
        )

        task = AsyncTask(
            task_type=task_type,
            triggered_by_command_id=trig_cmd_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(UTC),
            input_data={"session_id": session_id, **(input_data or {})},
        )
        db_session.add(task)
        await db_session.flush()

        self.log.info(
            "orchestrator_async_task_created_success",
            task_id=str(task.id),
            task_type=task_type,
            status=task.status.value if hasattr(task.status, "value") else str(task.status),
            correlation_id=str(trig_cmd_id) if trig_cmd_id else None,
            session_id=session_id,
        )


class TaskCompleter:
    """任务完成器，处理任务完成逻辑。"""

    def __init__(self, logger):
        """初始化任务完成器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger

    async def complete_task(
        self, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """将最新的RUNNING/PENDING AsyncTask（通过correlation）标记为COMPLETED。

        Args:
            correlation_id: 来自envelope meta的UUID字符串
            expect_task_prefix: 要匹配的task_type前缀（例如："Character.Design.Generation"）
            result_data: 要存储在任务中的结果数据
        """
        self.log.info(
            "orchestrator_completing_async_task",
            correlation_id=correlation_id,
            expect_task_prefix=expect_task_prefix,
            result_data_keys=list(result_data.keys()) if result_data else [],
        )

        if not correlation_id:
            self.log.warning(
                "orchestrator_async_task_complete_skipped",
                reason="no_correlation_id",
                expect_task_prefix=expect_task_prefix,
            )
            return

        trig_cmd_id = self._parse_correlation_id(correlation_id)
        if not trig_cmd_id:
            return  # 已在_parse_correlation_id中记录日志

        async with create_sql_session() as db:
            task = await self._find_task_to_complete(trig_cmd_id, expect_task_prefix, db)
            if task:
                await self._mark_task_completed(task, result_data, db)

    def _parse_correlation_id(self, correlation_id: str) -> UUID | None:
        """将correlation_id字符串解析为UUID，带有错误处理。

        Args:
            correlation_id: 关联ID字符串

        Returns:
            解析后的UUID或None
        """
        try:
            trig_cmd_id = UUID(str(correlation_id))
            self.log.debug(
                "orchestrator_async_task_complete_correlation_parsed",
                correlation_id=correlation_id,
                trig_cmd_id=str(trig_cmd_id),
            )
            return trig_cmd_id
        except Exception as e:
            self.log.warning(
                "orchestrator_async_task_complete_correlation_parse_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return None

    async def _find_task_to_complete(self, trig_cmd_id: UUID, expect_task_prefix: str, db_session) -> AsyncTask | None:
        """查找具有匹配前缀的最新RUNNING/PENDING任务。

        Args:
            trig_cmd_id: 触发命令ID
            expect_task_prefix: 期望的任务前缀
            db_session: 数据库会话对象

        Returns:
            找到的AsyncTask对象或None
        """
        self.log.debug(
            "orchestrator_searching_async_task_to_complete",
            trig_cmd_id=str(trig_cmd_id),
            expect_task_prefix=expect_task_prefix,
        )

        # 选择具有匹配前缀的最新RUNNING/PENDING任务
        stmt = (
            select(AsyncTask)
            .where(
                and_(
                    AsyncTask.triggered_by_command_id == trig_cmd_id,
                    AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
                    AsyncTask.task_type.like(f"{expect_task_prefix}%"),
                )
            )
            .order_by(AsyncTask.created_at.desc())
        )
        task = await db_session.scalar(stmt)

        if not task:
            self.log.warning(
                "orchestrator_async_task_not_found_for_completion",
                correlation_id=str(trig_cmd_id),
                expect_task_prefix=expect_task_prefix,
                trig_cmd_id=str(trig_cmd_id),
            )
            return None

        self.log.info(
            "orchestrator_async_task_found_for_completion",
            task_id=str(task.id),
            task_type=task.task_type,
            current_status=task.status.value if hasattr(task.status, "value") else str(task.status),
            created_at=str(task.created_at),
        )

        return task

    async def _mark_task_completed(self, task: AsyncTask, result_data: dict, db_session) -> None:
        """将任务标记为已完成并保存结果数据。

        Args:
            task: 要完成的AsyncTask对象
            result_data: 结果数据
            db_session: 数据库会话对象
        """
        task.status = TaskStatus.COMPLETED
        task.completed_at = utc_now()
        task.result_data = result_data or {}
        db_session.add(task)

        self.log.info(
            "orchestrator_async_task_completed_success",
            task_id=str(task.id),
            task_type=task.task_type,
            correlation_id=str(task.triggered_by_command_id),
            result_data_size=len(str(result_data)) if result_data else 0,
        )


class TaskManager:
    """统一的任务管理接口，提供异步任务创建和完成的统一操作。"""

    def __init__(self, logger):
        """初始化任务管理器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger
        self.creator = TaskCreator(logger)
        self.completer = TaskCompleter(logger)

    async def create_async_task(
        self, *, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """创建具有幂等性保护的异步任务。

        Args:
            correlation_id: 关联ID
            session_id: 会话ID
            task_type: 任务类型
            input_data: 输入数据
        """
        await self.creator.create_task(correlation_id, session_id, task_type, input_data)

    async def complete_async_task(
        self, *, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """通过correlation_id和任务前缀完成异步任务。

        Args:
            correlation_id: 关联ID
            expect_task_prefix: 期望的任务前缀
            result_data: 结果数据
        """
        await self.completer.complete_task(correlation_id, expect_task_prefix, result_data)
