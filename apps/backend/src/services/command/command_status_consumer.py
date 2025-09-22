"""
CommandStatusConsumer - Kafka 消费者集成

监听 Agent 命令结果事件，调用 CommandStatusUpdater 进行状态更新。
实现可靠的事件处理和错误恢复机制。
"""

import asyncio
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.common.utils.datetime_utils import utc_now
from src.services.command.command_status_updater import CommandStatusUpdater
from src.services.command.event_publisher import DomainEventPublisher

logger = logging.getLogger(__name__)


class CommandStatusConsumer:
    """命令状态更新消费者"""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_publisher: DomainEventPublisher | None = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 1,
        batch_size: int = 100,
        enable_dlq: bool = True,
    ):
        """初始化消费者

        Args:
            session_factory: 数据库会话工厂
            event_publisher: 领域事件发布器
            max_retries: 最大重试次数
            retry_delay_seconds: 重试延迟（秒）
            batch_size: 批处理大小
            enable_dlq: 是否启用死信队列
        """
        self.session_factory = session_factory
        self.status_updater = CommandStatusUpdater(event_publisher)
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.batch_size = batch_size
        self.enable_dlq = enable_dlq

        # 统计信息
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.dlq_count = 0

    async def consume_command_events(
        self, events: list[dict[str, Any]], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """批量消费命令事件

        Args:
            events: 命令事件列表
            context: 可选上下文信息

        Returns:
            处理结果统计
        """
        if not events:
            return self._get_processing_stats()

        batch_start_time = utc_now()
        logger.info(f"Processing command event batch: {len(events)} events")

        success_events = []
        failed_events = []

        async with self.session_factory() as db:
            for event in events:
                try:
                    self.processed_count += 1
                    result = await self._process_single_event(db, event, context)

                    if result["success"]:
                        success_events.append(event)
                        self.success_count += 1
                    else:
                        failed_events.append(
                            {
                                "event": event,
                                "error": result.get("error", "Unknown error"),
                                "retry_count": result.get("retry_count", 0),
                            }
                        )
                        self.error_count += 1

                except Exception as e:
                    logger.error(
                        f"Unexpected error processing event: {e}",
                        extra={"event": event, "context": context},
                        exc_info=True,
                    )
                    failed_events.append({"event": event, "error": str(e), "retry_count": 0})
                    self.error_count += 1

        # 处理失败事件重试，获取重试结果统计
        retry_stats = {"retry_success": 0, "retry_failed": 0, "sent_to_dlq": 0}
        if failed_events:
            retry_stats = await self._handle_failed_events(failed_events, context)

        processing_time = (utc_now() - batch_start_time).total_seconds()

        # 重新计算最终的成功/失败数量（包含重试结果）
        final_success = len(success_events) + retry_stats["retry_success"]
        final_failed = len(failed_events) - retry_stats["retry_success"]  # 减去重试成功的

        logger.info(
            f"Batch processing completed: {final_success} success, "
            f"{final_failed} failed, {processing_time:.2f}s. "
            f"Retries: {retry_stats['retry_success']} success, {retry_stats['retry_failed']} failed, "
            f"{retry_stats['sent_to_dlq']} sent to DLQ"
        )

        return {
            **self._get_processing_stats(),
            "batch_size": len(events),
            "batch_success": final_success,
            "batch_failed": final_failed,
            "processing_time_seconds": processing_time,
            "retry_stats": retry_stats,
        }

    async def _process_single_event(
        self, db: AsyncSession, event: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """处理单个命令事件

        Args:
            db: 数据库会话
            event: 命令事件
            context: 上下文信息

        Returns:
            处理结果
        """
        try:
            # 验证事件格式
            if not self._validate_event_format(event):
                return {"success": False, "error": "Invalid event format", "retry_count": 0}

            # 检查是否为支持的事件类型
            event_type = event.get("event_type", "")
            if not self.status_updater.is_event_supported(event_type):
                logger.debug(f"Skipping unsupported event type: {event_type}")
                return {
                    "success": True,  # 跳过的事件视为成功，避免重试
                    "skipped": True,
                    "reason": f"Unsupported event type: {event_type}",
                }

            # 调用状态更新器
            update_result = await self.status_updater.handle_command_event(db, event, context)

            if update_result.success:
                logger.debug(
                    f"Successfully updated command {update_result.command_id}: "
                    f"{update_result.old_status} -> {update_result.new_status}"
                )
                return {
                    "success": True,
                    "command_id": str(update_result.command_id),
                    "old_status": update_result.old_status.value,
                    "new_status": update_result.new_status.value,
                    "updated_at": update_result.updated_at.isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": update_result.error_message or "Status update failed",
                    "command_id": str(update_result.command_id),
                    "retry_count": 0,
                }

        except Exception as e:
            logger.error(
                f"Error processing command event: {e}", extra={"event": event, "context": context}, exc_info=True
            )
            return {"success": False, "error": f"Processing error: {e!s}", "retry_count": 0}

    def _validate_event_format(self, event: dict[str, Any]) -> bool:
        """验证事件格式

        Args:
            event: 事件数据

        Returns:
            格式是否有效
        """
        required_fields = ["event_type"]

        # 检查必填字段
        for field in required_fields:
            if field not in event:
                logger.warning(f"Missing required field '{field}' in event", extra={"event": event})
                return False

        # 检查命令ID（correlation_id 或 command_id）
        if not event.get("correlation_id") and not event.get("command_id"):
            logger.warning("Missing command identifier (correlation_id or command_id)", extra={"event": event})
            return False

        return True

    async def _handle_failed_events(
        self, failed_events: list[dict[str, Any]], context: dict[str, Any] | None = None
    ) -> dict[str, int]:
        """处理失败事件的重试逻辑

        Args:
            failed_events: 失败的事件列表
            context: 上下文信息

        Returns:
            处理结果统计: {"retry_success": int, "retry_failed": int, "sent_to_dlq": int}
        """
        if not failed_events:
            return {"retry_success": 0, "retry_failed": 0, "sent_to_dlq": 0}

        logger.warning(f"Handling {len(failed_events)} failed events")

        retry_success = 0
        retry_failed = 0
        sent_to_dlq = 0

        for failed_item in failed_events:
            event = failed_item["event"]
            error = failed_item["error"]
            retry_count = failed_item.get("retry_count", 0)

            # 判断是否应该重试
            if self._should_retry(error, retry_count):
                retry_succeeded = await self._schedule_retry(event, retry_count + 1, context)
                if retry_succeeded:
                    retry_success += 1
                    # 重试成功，需要从错误计数中移除
                    self.error_count -= 1
                else:
                    retry_failed += 1
                    # 检查是否达到最大重试次数，如果是则发送到 DLQ
                    if retry_count + 1 >= self.max_retries:
                        if self.enable_dlq:
                            await self._send_to_dlq(event, error, retry_count + 1, context)
                            sent_to_dlq += 1
                        else:
                            logger.error(
                                f"Event processing failed permanently after {retry_count + 1} retries: {error}",
                                extra={"event": event, "retry_count": retry_count + 1, "dlq_enabled": self.enable_dlq},
                            )
            elif self.enable_dlq:
                await self._send_to_dlq(event, error, retry_count, context)
                sent_to_dlq += 1
                self.dlq_count += 1
            else:
                logger.error(
                    f"Event processing failed permanently: {error}",
                    extra={"event": event, "retry_count": retry_count, "dlq_enabled": self.enable_dlq},
                )

        logger.info(
            f"Failed events handled: {retry_success} retry success, {retry_failed} retry failed, {sent_to_dlq} sent to DLQ"
        )

        return {"retry_success": retry_success, "retry_failed": retry_failed, "sent_to_dlq": sent_to_dlq}

    def _should_retry(self, error: str, retry_count: int) -> bool:
        """判断错误是否应该重试

        Args:
            error: 错误信息
            retry_count: 当前重试次数

        Returns:
            是否应该重试
        """
        # 超过最大重试次数
        if retry_count >= self.max_retries:
            return False

        # 某些错误类型不应重试 - 与 CommandStatusUpdater 的错误信息保持一致
        non_retryable_errors = [
            "Invalid event format",
            "Missing command identifier",  # 消费者层面的错误
            "Missing command_id in event",  # CommandStatusUpdater 的错误信息
            "Unknown event type",
            "Invalid command_id format",
            "Command not found",
            "badly formed hexadecimal UUID string",  # UUID 解析错误
        ]

        # Handle None or empty error messages
        if not error:
            return True

        return not any(non_retryable in error for non_retryable in non_retryable_errors)

    async def _schedule_retry(
        self, event: dict[str, Any], retry_count: int, context: dict[str, Any] | None = None
    ) -> bool:
        """安排事件重试

        Args:
            event: 要重试的事件
            retry_count: 重试次数
            context: 上下文信息

        Returns:
            重试是否成功
        """
        # 计算退避延迟
        delay = self.retry_delay_seconds * (2 ** (retry_count - 1))  # 指数退避

        logger.info(
            f"Retrying event #{retry_count} after {delay}s delay",
            extra={
                "event_type": event.get("event_type"),
                "command_id": event.get("correlation_id") or event.get("command_id"),
                "retry_count": retry_count,
                "delay_seconds": delay,
            },
        )

        # 应用退避延迟
        await asyncio.sleep(delay)

        # 立即重新处理事件 - 这次重试会在当前批次中处理
        async with self.session_factory() as db:
            try:
                result = await self._process_single_event(db, event, context)

                if result["success"]:
                    logger.info(
                        f"Retry #{retry_count} succeeded for event",
                        extra={
                            "event_type": event.get("event_type"),
                            "command_id": event.get("correlation_id") or event.get("command_id"),
                            "retry_count": retry_count,
                        },
                    )
                    self.success_count += 1  # 增加成功计数
                    return True
                else:
                    logger.warning(
                        f"Retry #{retry_count} failed for event: {result.get('error', 'Unknown error')}",
                        extra={
                            "event_type": event.get("event_type"),
                            "command_id": event.get("correlation_id") or event.get("command_id"),
                            "retry_count": retry_count,
                            "error": result.get("error"),
                        },
                    )
                    return False

            except Exception as e:
                logger.error(
                    f"Retry #{retry_count} failed with exception: {e}",
                    extra={
                        "event_type": event.get("event_type"),
                        "command_id": event.get("correlation_id") or event.get("command_id"),
                        "retry_count": retry_count,
                    },
                    exc_info=True,
                )
                return False

    async def _send_to_dlq(
        self, event: dict[str, Any], error: str, retry_count: int, context: dict[str, Any] | None = None
    ) -> None:
        """发送事件到死信队列

        Args:
            event: 失败的事件
            error: 错误信息
            retry_count: 重试次数
            context: 上下文信息
        """
        dlq_message = {
            "original_event": event,
            "error": error,
            "retry_count": retry_count,
            "failed_at": utc_now().isoformat(),
            "context": context or {},
        }

        logger.error(
            f"Sending event to DLQ: {error}",
            extra={
                "event_type": event.get("event_type"),
                "command_id": event.get("correlation_id") or event.get("command_id"),
                "retry_count": retry_count,
                "dlq_message": dlq_message,
            },
        )

        # TODO: 实现实际的 DLQ 发送逻辑
        # 可以考虑：
        # 1. Kafka DLQ topic
        # 2. Redis DLQ list
        # 3. 数据库 DLQ 表
        # 4. 外部监控/告警系统
        pass

    def _get_processing_stats(self) -> dict[str, Any]:
        """获取处理统计信息

        Returns:
            统计信息字典
        """
        return {
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "dlq_count": self.dlq_count,
            "success_rate": self.success_count / max(self.processed_count, 1),
            "error_rate": self.error_count / max(self.processed_count, 1),
        }

    async def health_check(self) -> dict[str, Any]:
        """健康检查

        Returns:
            健康状态信息
        """
        try:
            # 检查数据库连接
            async with self.session_factory() as db:
                await db.execute(text("SELECT 1"))

            return {
                "status": "healthy",
                "component": "CommandStatusConsumer",
                "timestamp": utc_now().isoformat(),
                "stats": self._get_processing_stats(),
                "configuration": {
                    "max_retries": self.max_retries,
                    "retry_delay_seconds": self.retry_delay_seconds,
                    "batch_size": self.batch_size,
                    "enable_dlq": self.enable_dlq,
                },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "CommandStatusConsumer",
                "timestamp": utc_now().isoformat(),
                "error": str(e),
                "stats": self._get_processing_stats(),
            }

    async def process_timeout_watchdog(self) -> dict[str, Any]:
        """执行超时命令看门狗检查

        Returns:
            处理结果
        """
        try:
            async with self.session_factory() as db:
                timeout_count = await self.status_updater.handle_timeout_commands(db)

            logger.info(f"Timeout watchdog processed {timeout_count} commands")

            return {"success": True, "timeout_count": timeout_count, "timestamp": utc_now().isoformat()}

        except Exception as e:
            logger.error(f"Error in timeout watchdog: {e}", exc_info=True)
            return {"success": False, "error": str(e), "timestamp": utc_now().isoformat()}
