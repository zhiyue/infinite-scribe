"""
CommandStatusUpdater - 核心状态更新逻辑

负责监听 Agent 产出的命令结果事件，更新 CommandInbox 状态，并推送前端通知。
实现单一写入者模式，确保状态一致性和幂等性。
"""

import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.common.utils.datetime_utils import utc_now
from src.models.workflow import CommandInbox
from src.schemas.enums import CommandStatus
from src.services.command.event_publisher import DomainEventPublisher, NoOpEventPublisher

logger = logging.getLogger(__name__)


class CommandEventType(str, Enum):
    """Agent 产出的命令事件类型"""

    STARTED = "Command.Started"  # Agent 开始处理
    PROGRESS = "Command.Progress"  # 处理进度更新
    COMPLETED = "Command.Completed"  # 处理成功
    FAILED = "Command.Failed"  # 处理失败
    TIMEOUT = "Command.Timeout"  # 处理超时
    CANCELLED = "Command.Cancelled"  # 处理取消


@dataclass(frozen=True)
class CommandStatusTransition:
    """命令状态转换规则"""

    from_status: CommandStatus
    to_status: CommandStatus
    event_type: CommandEventType
    description: str


@dataclass
class CommandUpdateResult:
    """状态更新结果"""

    success: bool
    command_id: UUID
    old_status: CommandStatus
    new_status: CommandStatus
    updated_at: datetime
    error_message: str | None = None
    should_notify: bool = True


class CommandStatusUpdater:
    """命令状态更新器 - 单一写入者模式"""

    # 定义状态转换规则
    VALID_TRANSITIONS: dict[CommandEventType, set[CommandStatusTransition]] = {
        CommandEventType.STARTED: {
            CommandStatusTransition(
                CommandStatus.RECEIVED, CommandStatus.PROCESSING, CommandEventType.STARTED, "Agent开始处理命令"
            )
        },
        CommandEventType.PROGRESS: {
            CommandStatusTransition(
                CommandStatus.PROCESSING, CommandStatus.PROCESSING, CommandEventType.PROGRESS, "处理进度更新"
            )
        },
        CommandEventType.COMPLETED: {
            CommandStatusTransition(
                CommandStatus.PROCESSING, CommandStatus.COMPLETED, CommandEventType.COMPLETED, "命令处理成功完成"
            )
        },
        CommandEventType.FAILED: {
            CommandStatusTransition(
                CommandStatus.RECEIVED, CommandStatus.FAILED, CommandEventType.FAILED, "命令处理失败(未开始)"
            ),
            CommandStatusTransition(
                CommandStatus.PROCESSING, CommandStatus.FAILED, CommandEventType.FAILED, "命令处理失败(进行中)"
            ),
        },
        CommandEventType.TIMEOUT: {
            CommandStatusTransition(
                CommandStatus.PROCESSING, CommandStatus.FAILED, CommandEventType.TIMEOUT, "命令处理超时"
            )
        },
        CommandEventType.CANCELLED: {
            CommandStatusTransition(
                CommandStatus.RECEIVED, CommandStatus.FAILED, CommandEventType.CANCELLED, "命令被取消(未开始)"
            ),
            CommandStatusTransition(
                CommandStatus.PROCESSING, CommandStatus.FAILED, CommandEventType.CANCELLED, "命令被取消(进行中)"
            ),
        },
    }

    def __init__(self, event_publisher: DomainEventPublisher | None = None):
        """初始化状态更新器

        Args:
            event_publisher: 领域事件发布器，可选，默认使用 NoOp 发布器
        """
        self.event_publisher = event_publisher or NoOpEventPublisher()

    async def handle_command_event(
        self, db: AsyncSession, event: dict[str, Any], context: dict[str, Any] | None = None
    ) -> CommandUpdateResult:
        """处理 Agent 产出的命令事件

        Args:
            db: 数据库会话
            event: 命令事件数据
            context: 可选上下文信息

        Returns:
            CommandUpdateResult: 更新结果
        """
        try:
            # 1. 解析事件数据
            event_type_str = event.get("event_type", "")
            command_id_str = event.get("correlation_id") or event.get("command_id")
            payload = event.get("payload", {})

            # 验证事件类型
            try:
                event_type = CommandEventType(event_type_str)
            except ValueError:
                logger.warning(f"Unknown command event type: {event_type_str}")
                # 安全地解析 UUID，避免在无效 UUID 时再次抛出异常
                try:
                    parsed_command_id = UUID(command_id_str) if command_id_str else uuid4()
                except (ValueError, TypeError):
                    logger.warning(f"Invalid command_id format: {command_id_str}")
                    return CommandUpdateResult(
                        success=False,
                        command_id=uuid4(),
                        old_status=CommandStatus.RECEIVED,
                        new_status=CommandStatus.RECEIVED,
                        updated_at=utc_now(),
                        error_message="Invalid command_id format",
                        should_notify=False,
                    )
                return CommandUpdateResult(
                    success=False,
                    command_id=parsed_command_id,
                    old_status=CommandStatus.RECEIVED,
                    new_status=CommandStatus.RECEIVED,
                    updated_at=utc_now(),
                    error_message=f"Unknown event type: {event_type_str}",
                    should_notify=False,
                )

            # 验证命令ID
            if not command_id_str:
                logger.error("Missing command_id in event", extra={"event": event})
                return CommandUpdateResult(
                    success=False,
                    command_id=uuid4(),
                    old_status=CommandStatus.RECEIVED,
                    new_status=CommandStatus.RECEIVED,
                    updated_at=utc_now(),
                    error_message="Missing command_id in event",
                    should_notify=False,
                )

            try:
                command_id = UUID(command_id_str)
            except (ValueError, TypeError):
                logger.error(f"Invalid command_id format: {command_id_str}")
                return CommandUpdateResult(
                    success=False,
                    command_id=uuid4(),
                    old_status=CommandStatus.RECEIVED,
                    new_status=CommandStatus.RECEIVED,
                    updated_at=utc_now(),
                    error_message=f"Invalid command_id format: {command_id_str}",
                    should_notify=False,
                )

            # 2. 查询当前命令状态
            cmd = await db.scalar(
                select(CommandInbox)
                .where(CommandInbox.id == command_id)
                .options(selectinload(CommandInbox.async_tasks))
            )

            if not cmd:
                logger.error(f"Command not found: {command_id}")
                return CommandUpdateResult(
                    success=False,
                    command_id=command_id,
                    old_status=CommandStatus.RECEIVED,
                    new_status=CommandStatus.RECEIVED,
                    updated_at=utc_now(),
                    error_message=f"Command not found: {command_id}",
                    should_notify=False,
                )

            # 3. 验证状态转换合法性或检查幂等性
            transition = self._find_valid_transition(cmd.status, event_type)
            if not transition:
                # 检查是否为幂等重复事件（已处于目标状态）
                if self._is_idempotent_duplicate(cmd.status, event_type):
                    logger.info(
                        f"Idempotent duplicate event for command {command_id}: "
                        f"{cmd.status} + {event_type} (already in target state)",
                        extra={
                            "command_id": str(command_id),
                            "current_status": cmd.status.value,
                            "event_type": event_type.value,
                            "idempotent": True,
                        },
                    )
                    return CommandUpdateResult(
                        success=True,
                        command_id=command_id,
                        old_status=cmd.status,
                        new_status=cmd.status,  # 保持当前状态
                        updated_at=utc_now(),
                        should_notify=False,  # 幂等事件不需要通知
                    )

                # 真正的无效状态转换
                logger.warning(
                    f"Invalid state transition for command {command_id}: " f"{cmd.status} -> {event_type}",
                    extra={
                        "command_id": str(command_id),
                        "current_status": cmd.status.value,
                        "event_type": event_type.value,
                    },
                )
                return CommandUpdateResult(
                    success=False,
                    command_id=command_id,
                    old_status=cmd.status,
                    new_status=cmd.status,
                    updated_at=utc_now(),
                    error_message=f"Invalid state transition: {cmd.status} -> {event_type}",
                    should_notify=False,
                )

            # 4. 执行状态更新 (幂等性保证)
            old_status = cmd.status
            new_status = transition.to_status
            updated_at = utc_now()

            # 准备更新数据
            update_data = {"status": new_status, "updated_at": updated_at}

            # 处理特定事件类型的额外数据
            if event_type in [CommandEventType.FAILED, CommandEventType.TIMEOUT]:
                error_msg = payload.get("error_message") or payload.get("message", "命令处理失败")
                update_data["error_message"] = error_msg
                if event_type == CommandEventType.TIMEOUT:
                    update_data["error_message"] = f"超时: {error_msg}"

            elif event_type == CommandEventType.CANCELLED:
                update_data["error_message"] = payload.get("reason", "命令被取消")

            # 更新重试次数（如果提供）
            if "retry_count" in payload:
                try:
                    retry_count = int(payload["retry_count"])
                    if retry_count >= 0:
                        update_data["retry_count"] = retry_count
                except (ValueError, TypeError):
                    pass

            # 执行数据库更新（基于期望状态的幂等更新，避免并发覆盖）
            result = await db.execute(
                update(CommandInbox)
                .where(CommandInbox.id == command_id, CommandInbox.status == old_status)
                .values(**update_data)
            )

            if result.rowcount == 0:
                logger.error(f"Failed to update command {command_id}: no rows affected (stale state or not found)")
                return CommandUpdateResult(
                    success=False,
                    command_id=command_id,
                    old_status=old_status,
                    new_status=old_status,
                    updated_at=updated_at,
                    error_message="Database update failed: no rows affected",
                    should_notify=False,
                )

            # 5. 提交事务 (先更新数据库再推送通知)
            await db.commit()

            logger.info(
                f"Command status updated: {command_id} {old_status} -> {new_status}",
                extra={
                    "command_id": str(command_id),
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "event_type": event_type.value,
                    "transition_description": transition.description,
                },
            )

            # 6. 发布领域事件到 EventBridge (在事务提交后)
            update_result = CommandUpdateResult(
                success=True,
                command_id=command_id,
                old_status=old_status,
                new_status=new_status,
                updated_at=updated_at,
                should_notify=True,
            )

            if update_result.should_notify:
                await self._publish_status_updated_event(db, cmd, update_result, payload)

            return update_result

        except Exception as e:
            logger.error(
                f"Error handling command event: {e}", extra={"event": event, "context": context}, exc_info=True
            )
            await db.rollback()

            # 安全地构造 command_id，避免在异常处理中再次抛出异常
            safe_command_id = uuid4()
            if command_id_str:
                with contextlib.suppress(ValueError, TypeError):
                    safe_command_id = UUID(command_id_str)

            return CommandUpdateResult(
                success=False,
                command_id=safe_command_id,
                old_status=CommandStatus.RECEIVED,
                new_status=CommandStatus.RECEIVED,
                updated_at=utc_now(),
                error_message=f"Internal error: {e!s}",
                should_notify=False,
            )

    def _is_idempotent_duplicate(self, current_status: CommandStatus, event_type: CommandEventType) -> bool:
        """检查是否为幂等的重复事件（已处于目标状态）

        Args:
            current_status: 当前状态
            event_type: 事件类型

        Returns:
            是否为幂等重复事件
        """
        # 定义事件类型到目标状态的映射
        event_to_target_status = {
            CommandEventType.STARTED: CommandStatus.PROCESSING,
            CommandEventType.COMPLETED: CommandStatus.COMPLETED,
            CommandEventType.FAILED: CommandStatus.FAILED,
            CommandEventType.TIMEOUT: CommandStatus.FAILED,
            CommandEventType.CANCELLED: CommandStatus.FAILED,
            # PROGRESS 事件不改变状态，始终是幂等的
            CommandEventType.PROGRESS: current_status,
        }

        target_status = event_to_target_status.get(event_type)
        return target_status is not None and current_status == target_status

    def _find_valid_transition(
        self, current_status: CommandStatus, event_type: CommandEventType
    ) -> CommandStatusTransition | None:
        """查找有效的状态转换

        Args:
            current_status: 当前状态
            event_type: 事件类型

        Returns:
            找到的状态转换规则，如果无效则返回 None
        """
        if event_type not in self.VALID_TRANSITIONS:
            return None

        for transition in self.VALID_TRANSITIONS[event_type]:
            if transition.from_status == current_status:
                return transition

        return None

    async def _publish_status_updated_event(
        self, db: AsyncSession, command: CommandInbox, update_result: CommandUpdateResult, event_payload: dict[str, Any]
    ) -> None:
        """发布命令状态更新域事件

        Args:
            db: 数据库会话
            command: 命令对象
            update_result: 更新结果
            event_payload: 原始事件载荷
        """
        try:
            # 查询 user_id (从 session_id -> novel_id -> user_id)
            user_id = await self._get_user_id_for_session(db, command.session_id)

            # 映射到 Genesis 域事件类型
            genesis_event_type = self._map_to_genesis_event_type(update_result.new_status)

            # 构建域事件数据
            domain_event = {
                "event_type": genesis_event_type,
                "aggregate_type": "Session",
                "aggregate_id": str(command.session_id),
                "payload": {
                    "command_id": str(update_result.command_id),
                    "command_type": command.command_type,
                    "session_id": str(command.session_id),
                    "user_id": user_id,
                    "old_status": update_result.old_status.value,
                    "new_status": update_result.new_status.value,
                    "updated_at": update_result.updated_at.isoformat(),
                    "timestamp": update_result.updated_at.isoformat(),
                    "retry_count": command.retry_count,
                },
                "metadata": {
                    "source": "command-status-updater",
                    "correlation_id": str(update_result.command_id),
                    "causation_id": str(update_result.command_id),
                    "user_id": user_id,  # 添加 user_id 便于跨服务排障
                },
            }

            # 添加错误信息（如果有）
            if update_result.error_message:
                domain_event["payload"]["error_message"] = update_result.error_message

            # 添加原始事件的额外数据
            if "progress" in event_payload:
                domain_event["payload"]["progress"] = event_payload["progress"]

            if "result" in event_payload:
                domain_event["payload"]["result"] = event_payload["result"]

            # 添加阶段信息（创世阶段特有）
            if "stage" in event_payload:
                domain_event["payload"]["stage"] = event_payload["stage"]

            if "stage_progress" in event_payload:
                domain_event["payload"]["stage_progress"] = event_payload["stage_progress"]

            # 发布事件到 EventBridge
            published = await self.event_publisher.publish_event(domain_event)

            # 增强结构化日志
            log_context = {
                "command_id": str(update_result.command_id),
                "session_id": str(command.session_id),
                "user_id": user_id,
                "event_type": genesis_event_type,
                "new_status": update_result.new_status.value,
                "old_status": update_result.old_status.value,
                "command_type": command.command_type,
                "retry_count": command.retry_count,
            }

            if published:
                logger.info(
                    f"Published Genesis domain event for command {update_result.command_id}",
                    extra=log_context,
                )
            else:
                logger.warning(
                    f"Failed to publish Genesis domain event for command {update_result.command_id}",
                    extra=log_context,
                )

        except Exception as e:
            # 增强错误日志
            error_context = {
                "command_id": str(update_result.command_id),
                "session_id": str(command.session_id),
                "new_status": update_result.new_status.value,
                "command_type": command.command_type,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(
                f"Error publishing Genesis domain event for command {update_result.command_id}: {e}",
                extra=error_context,
                exc_info=True,
            )

    def _map_to_genesis_event_type(self, command_status: CommandStatus) -> str:
        """映射命令状态到 Genesis 域事件类型

        Args:
            command_status: 命令状态

        Returns:
            Genesis 域事件类型字符串
        """
        mapping = {
            CommandStatus.PROCESSING: "Genesis.Session.Command.Started",
            CommandStatus.COMPLETED: "Genesis.Session.Command.Completed",
            CommandStatus.FAILED: "Genesis.Session.Command.Failed",
        }
        return mapping.get(command_status, "Genesis.Session.Command.Failed")

    async def _get_user_id_for_session(self, db: AsyncSession, session_id: UUID) -> int | None:
        """从会话ID查询用户ID

        Args:
            db: 数据库会话
            session_id: 会话ID

        Returns:
            用户ID，如果查询失败返回 None
        """
        try:
            from sqlalchemy import select
            from src.models.conversation import ConversationSession
            from src.models.novel import Novel

            # 查询会话的 scope_id (novel_id)
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))

            if not session:
                logger.warning(f"Session {session_id} not found", extra={"session_id": str(session_id)})
                return None

            # 对于 Genesis 会话，scope_id 是 novel_id
            if session.scope_type != "GENESIS":
                logger.warning(
                    f"Session {session_id} has unsupported scope_type: {session.scope_type}",
                    extra={"session_id": str(session_id), "scope_type": session.scope_type},
                )
                return None

            try:
                novel_id = UUID(session.scope_id)
            except (ValueError, TypeError):
                logger.warning(
                    f"Invalid novel_id format in session {session_id}: {session.scope_id}",
                    extra={"session_id": str(session_id), "scope_id": session.scope_id},
                )
                return None

            # 查询小说的 user_id
            novel = await db.scalar(select(Novel).where(Novel.id == novel_id))

            if not novel:
                logger.warning(
                    f"Novel {novel_id} not found for session {session_id}",
                    extra={"session_id": str(session_id), "novel_id": str(novel_id)},
                )
                return None

            return novel.user_id

        except Exception as e:
            logger.error(
                f"Error querying user_id for session {session_id}: {e}",
                extra={"session_id": str(session_id), "error": str(e)},
                exc_info=True,
            )
            return None

    # (duplicate method definitions removed)

    async def handle_timeout_commands(
        self,
        db: AsyncSession,
        timeout_seconds: int = 3600,  # 默认1小时超时
    ) -> int:
        """处理超时命令 - 看门狗机制

        Args:
            db: 数据库会话
            timeout_seconds: 超时时间（秒）

        Returns:
            处理的超时命令数量
        """
        try:
            # 查询超时的处理中命令 - 使用 timezone-aware 计算
            timeout_threshold = utc_now() - timedelta(seconds=timeout_seconds)

            timeout_commands = await db.scalars(
                select(CommandInbox).where(
                    CommandInbox.status == CommandStatus.PROCESSING,
                    CommandInbox.updated_at < timeout_threshold,
                )
            )

            timeout_count = 0
            for cmd in timeout_commands:
                # 构造超时事件
                timeout_event = {
                    "event_type": CommandEventType.TIMEOUT.value,
                    "correlation_id": str(cmd.id),
                    "payload": {"message": f"命令处理超时({timeout_seconds}秒)", "timeout_seconds": timeout_seconds},
                }

                # 处理超时事件
                result = await self.handle_command_event(db, timeout_event)
                if result.success:
                    timeout_count += 1
                    logger.warning(
                        f"Command {cmd.id} marked as timeout",
                        extra={
                            "command_id": str(cmd.id),
                            "command_type": cmd.command_type,
                            "session_id": str(cmd.session_id),
                            "timeout_seconds": timeout_seconds,
                        },
                    )

            return timeout_count

        except Exception as e:
            logger.error(f"Error handling timeout commands: {e}", exc_info=True)
            return 0

    def is_event_supported(self, event_type: str) -> bool:
        """检查是否支持指定的事件类型

        Args:
            event_type: 事件类型字符串

        Returns:
            是否支持该事件类型
        """
        try:
            CommandEventType(event_type)
            return True
        except ValueError:
            return False

    def get_valid_next_statuses(self, current_status: CommandStatus) -> set[CommandStatus]:
        """获取当前状态的所有有效下一状态

        Args:
            current_status: 当前状态

        Returns:
            有效的下一状态集合
        """
        next_statuses = set()
        for transitions in self.VALID_TRANSITIONS.values():
            for transition in transitions:
                if transition.from_status == current_status:
                    next_statuses.add(transition.to_status)
        return next_statuses
