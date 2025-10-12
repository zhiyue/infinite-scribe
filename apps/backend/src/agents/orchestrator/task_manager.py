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
from src.common.utils.uuid_utils import safe_uuid_conversion
from src.db.sql.session import create_sql_session
from src.models.workflow import AsyncTask
from src.schemas.enums import TaskStatus


class TaskIdempotencyChecker:
    """任务幂等性检查器

    确保同一命令不会创建重复的任务实例。
    在分布式系统中，由于网络重试或并发请求，可能会多次收到相同的命令。
    通过检查现有的活动任务（RUNNING/PENDING状态），防止重复执行。
    """

    @staticmethod
    async def check_existing_task(trig_cmd_id: UUID, task_type: str, db_session) -> AsyncTask | None:
        """检查是否已存在活动状态的任务

        只检查RUNNING和PENDING状态，因为：
        - RUNNING: 任务正在执行中，不应重复创建
        - PENDING: 任务已排队等待执行，不应重复创建
        - COMPLETED/FAILED: 已结束的任务不影响新任务创建，允许重试

        Args:
            trig_cmd_id: 触发命令ID，用于关联任务
            task_type: 任务类型，确保类型匹配
            db_session: 数据库会话对象

        Returns:
            如果存在活动任务则返回AsyncTask对象，否则返回None
        """
        # 查询同一命令触发的、相同类型的、仍在活动状态的任务
        existing_stmt = select(AsyncTask).where(
            and_(
                AsyncTask.triggered_by_command_id == trig_cmd_id,
                AsyncTask.task_type == task_type,
                # 只检查活动状态，避免阻止合理的重试
                AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
            )
        )
        return await db_session.scalar(existing_stmt)


class TaskCreator:
    """任务创建器

    负责创建异步任务记录，用于跟踪能力代理的执行状态。
    提供幂等性保护，确保同一命令不会创建重复任务。
    """

    def __init__(self, logger):
        """初始化任务创建器

        Args:
            logger: 日志记录器实例，用于记录任务创建过程的关键事件
        """
        self.log = logger
        self.idempotency_checker = TaskIdempotencyChecker()

    async def create_task(
        self, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """创建异步任务记录，带有幂等性保护

        通过correlation_id关联命令与任务，实现任务跟踪。
        在创建前检查是否已存在活动任务，避免重复执行。

        Args:
            correlation_id: 关联ID，通常是触发命令的UUID，用于任务溯源
            session_id: 会话ID，标识用户会话上下文
            task_type: 任务类型，标识具体的能力代理任务（如"Character.Design.Generation"）
            input_data: 输入数据字典，包含任务执行所需的参数
        """
        self.log.info(
            "orchestrator_creating_async_task",
            correlation_id=correlation_id,
            session_id=session_id,
            task_type=task_type,
            input_data_keys=list(input_data.keys()) if input_data else [],
        )

        # 验证必需参数：task_type是任务标识的核心
        if not task_type:
            self.log.warning(
                "orchestrator_async_task_skipped",
                reason="empty_task_type",
                correlation_id=correlation_id,
                session_id=session_id,
            )
            return

        # 解析correlation_id为UUID格式，用于数据库查询
        trig_cmd_id = self._parse_correlation_id(correlation_id)
        if correlation_id and not trig_cmd_id:
            return  # 解析失败，已记录错误日志

        async with create_sql_session() as db:
            # 幂等性检查：防止网络重试或并发请求导致的重复任务创建
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
        """解析correlation_id为UUID

        correlation_id用于将任务与触发命令关联，必须是有效的UUID格式。
        解析失败时记录警告日志，但不中断流程，因为某些场景下可能没有correlation_id。

        Args:
            correlation_id: 关联ID字符串，通常来自消息信封的元数据

        Returns:
            成功返回UUID对象，失败或为空返回None
        """
        if not correlation_id:
            return None

        trig_cmd_id = safe_uuid_conversion(correlation_id)
        if trig_cmd_id:
            self.log.debug(
                "orchestrator_async_task_correlation_parsed",
                correlation_id=correlation_id,
                trig_cmd_id=str(trig_cmd_id),
            )
        else:
            # 解析失败可能是格式错误或非UUID字符串，需要记录以便排查
            self.log.warning(
                "orchestrator_async_task_correlation_parse_failed",
                correlation_id=correlation_id,
                error="Invalid UUID format",
            )
        return trig_cmd_id

    async def _create_new_task(
        self, trig_cmd_id: UUID | None, session_id: str, task_type: str, input_data: dict, db_session
    ) -> None:
        """在数据库中创建新的异步任务记录

        任务创建时立即设置为RUNNING状态，表示能力代理已开始处理。
        input_data会合并session_id，确保任务执行时有完整的上下文信息。

        Args:
            trig_cmd_id: 触发命令ID，可为None（无关联命令的任务）
            session_id: 会话ID，必需，用于关联用户会话
            task_type: 任务类型，标识具体的能力代理任务
            input_data: 输入数据字典，包含任务执行参数
            db_session: 数据库会话对象，用于持久化任务
        """
        self.log.info(
            "orchestrator_creating_new_async_task",
            task_type=task_type,
            trig_cmd_id=str(trig_cmd_id) if trig_cmd_id else None,
            session_id=session_id,
        )

        # 创建任务记录，初始状态为RUNNING（任务已被派发到能力代理）
        task = AsyncTask(
            task_type=task_type,
            triggered_by_command_id=trig_cmd_id,
            status=TaskStatus.RUNNING,  # 立即标记为运行中，因为能力代理已接收到任务
            started_at=datetime.now(UTC),  # 使用UTC时间确保时区一致性
            # 确保session_id始终存在于input_data中，方便任务执行时获取上下文
            input_data={"session_id": session_id, **(input_data or {})},
        )
        db_session.add(task)
        # 立即刷新以获取数据库生成的ID，用于日志记录
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
    """任务完成器

    负责将能力代理执行完成的任务标记为已完成状态。
    通过correlation_id查找对应的活动任务，并保存执行结果。
    支持前缀匹配，允许灵活处理不同层级的任务类型。
    """

    def __init__(self, logger):
        """初始化任务完成器

        Args:
            logger: 日志记录器实例，用于记录任务完成过程的关键事件
        """
        self.log = logger

    async def complete_task(
        self, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """标记任务为已完成状态

        根据correlation_id找到最新的活动任务，并保存执行结果。
        使用前缀匹配而非精确匹配，因为任务类型可能包含层级结构（如"Character.Design.Generation"）。
        只处理RUNNING/PENDING状态的任务，避免重复完成或修改已完成的任务。

        Args:
            correlation_id: 关联ID，来自能力代理响应消息的元数据，用于关联原始命令
            expect_task_prefix: 任务类型前缀，用于匹配特定类型的任务（如"Character.Design"匹配所有角色设计任务）
            result_data: 任务执行结果数据，将存储到数据库供后续查询使用
        """
        self.log.info(
            "orchestrator_completing_async_task",
            correlation_id=correlation_id,
            expect_task_prefix=expect_task_prefix,
            result_data_keys=list(result_data.keys()) if result_data else [],
        )

        # 验证必需参数：没有correlation_id无法定位要完成的任务
        if not correlation_id:
            self.log.warning(
                "orchestrator_async_task_complete_skipped",
                reason="no_correlation_id",
                expect_task_prefix=expect_task_prefix,
            )
            return

        # 解析correlation_id为UUID格式，用于数据库查询
        trig_cmd_id = self._parse_correlation_id(correlation_id)
        if not trig_cmd_id:
            return  # 解析失败，已记录错误日志

        async with create_sql_session() as db:
            # 查找匹配的活动任务
            task = await self._find_task_to_complete(trig_cmd_id, expect_task_prefix, db)
            if task:
                # 更新任务状态和结果数据
                await self._mark_task_completed(task, result_data, db)

    def _parse_correlation_id(self, correlation_id: str) -> UUID | None:
        """解析correlation_id为UUID

        correlation_id必须是有效的UUID格式才能用于数据库查询。
        解析失败时记录警告日志，返回None表示无法继续完成任务。

        Args:
            correlation_id: 关联ID字符串，来自能力代理响应消息

        Returns:
            成功返回UUID对象，失败返回None
        """
        trig_cmd_id = safe_uuid_conversion(correlation_id)
        if trig_cmd_id:
            self.log.debug(
                "orchestrator_async_task_complete_correlation_parsed",
                correlation_id=correlation_id,
                trig_cmd_id=str(trig_cmd_id),
            )
        else:
            # 解析失败意味着无法查找对应的任务，需要记录以便排查数据流问题
            self.log.warning(
                "orchestrator_async_task_complete_correlation_parse_failed",
                correlation_id=correlation_id,
                error="Invalid UUID format",
            )
        return trig_cmd_id

    async def _find_task_to_complete(self, trig_cmd_id: UUID, expect_task_prefix: str, db_session) -> AsyncTask | None:
        """查找待完成的活动任务

        通过correlation_id和任务类型前缀查找最新的活动任务。
        使用前缀匹配支持任务类型的层级结构（如"Character.Design.Generation"可以被"Character.Design"匹配）。
        按创建时间倒序排列，确保处理最新的任务（处理重试或多任务场景）。

        Args:
            trig_cmd_id: 触发命令ID，用于关联任务
            expect_task_prefix: 任务类型前缀，用于模糊匹配任务类型
            db_session: 数据库会话对象

        Returns:
            找到的AsyncTask对象，未找到返回None
        """
        self.log.debug(
            "orchestrator_searching_async_task_to_complete",
            trig_cmd_id=str(trig_cmd_id),
            expect_task_prefix=expect_task_prefix,
        )

        # 查询条件：同一命令触发 + 活动状态 + 任务类型前缀匹配
        stmt = (
            select(AsyncTask)
            .where(
                and_(
                    AsyncTask.triggered_by_command_id == trig_cmd_id,
                    # 只处理活动任务，避免重复完成已完成的任务
                    AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
                    # 使用LIKE前缀匹配，支持层级任务类型
                    AsyncTask.task_type.like(f"{expect_task_prefix}%"),
                )
            )
            # 按创建时间倒序，优先处理最新的任务（处理重试场景）
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
        """更新任务为已完成状态并保存结果

        更新任务的状态、完成时间和结果数据。
        使用UTC时间确保时区一致性。
        result_data可能包含生成的内容、执行摘要等，供后续查询和分析使用。

        Args:
            task: 要完成的AsyncTask对象，来自数据库查询
            result_data: 任务执行结果数据，由能力代理提供
            db_session: 数据库会话对象，用于持久化更新
        """
        task.status = TaskStatus.COMPLETED
        task.completed_at = utc_now()  # 记录完成时间，用于计算任务执行时长
        task.result_data = result_data or {}  # 保存结果数据，空结果使用空字典
        db_session.add(task)  # 标记为需要更新（实际提交由session上下文管理）

        self.log.info(
            "orchestrator_async_task_completed_success",
            task_id=str(task.id),
            task_type=task.task_type,
            correlation_id=str(task.triggered_by_command_id),
            result_data_size=len(str(result_data)) if result_data else 0,
        )


class TaskManager:
    """任务管理器统一接口

    提供异步任务的完整生命周期管理：创建和完成。
    整合TaskCreator和TaskCompleter，为编排器提供简洁的API。
    确保所有任务操作都具有幂等性保护和完整的日志记录。

    使用场景：
    - 编排器派发能力代理任务时，调用create_async_task创建跟踪记录
    - 能力代理完成任务后，调用complete_async_task更新状态和结果
    """

    def __init__(self, logger: Any) -> None:
        """初始化任务管理器

        Args:
            logger: 日志记录器实例，将传递给内部的创建器和完成器
        """
        self.log = logger
        self.creator = TaskCreator(logger)
        self.completer = TaskCompleter(logger)

    async def create_async_task(
        self, *, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """创建异步任务跟踪记录

        在能力代理开始执行前创建任务记录，用于跟踪执行状态。
        自动检查重复任务，确保幂等性。

        Args:
            correlation_id: 关联ID，用于将任务与触发命令关联
            session_id: 会话ID，标识用户会话上下文
            task_type: 任务类型，如"Character.Design.Generation"
            input_data: 任务输入参数
        """
        await self.creator.create_task(correlation_id, session_id, task_type, input_data)

    async def complete_async_task(
        self, *, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """完成异步任务并保存结果

        通过correlation_id定位任务，更新为完成状态并保存执行结果。
        使用前缀匹配支持灵活的任务类型层级。

        Args:
            correlation_id: 关联ID，用于定位要完成的任务
            expect_task_prefix: 任务类型前缀，如"Character.Design"
            result_data: 任务执行结果数据
        """
        await self.completer.complete_task(correlation_id, expect_task_prefix, result_data)
