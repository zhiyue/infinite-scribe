"""Message processing pipeline for agent services."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import Any, Literal, cast

from src.agents.agent_metrics import AgentMetrics
from src.agents.error_handler import ErrorHandler
from src.agents.message import decode_message, encode_message
from src.agents.metrics import record_latency
from src.common.outbox import BaseOutboxManager
from src.core.logging.config import get_logger


class MessageProcessor:
    """处理消息处理管道，包含重试和错误处理机制。

    负责消息的解码、处理、重试逻辑和错误分类，确保消息的可靠传递。
    """

    def __init__(
        self,
        agent_name: str,
        error_handler: ErrorHandler,
        classify_error: Callable[[Exception, dict[str, Any]], Literal["retriable", "non_retriable"]] | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.error_handler = error_handler
        # 允许自定义错误分类逻辑，提高灵活性
        self.classify_error_func = classify_error or error_handler.classify_error

        # 绑定agent上下文的结构化日志器，便于追踪特定agent的日志
        self.log: Any = get_logger("processor").bind(agent=agent_name)

    def decode_message_with_context(self, msg: Any) -> tuple[dict[str, Any], dict[str, Any], str | None, str | None]:
        """解码消息并构建上下文元数据。

        Returns:
            Tuple of (decoded_message, context, correlation_id, message_id)
        """
        # 从Kafka消息中提取value字段，兼容Envelope或原始dict格式
        message_value = cast(dict[str, Any] | None, getattr(msg, "value", None))
        raw_value: dict[str, Any] = message_value if isinstance(message_value, dict) else {}
        safe_message, meta = decode_message(raw_value)
        correlation_id = cast(str | None, meta.get("correlation_id"))
        message_id = cast(str | None, meta.get("message_id") or meta.get("id"))

        # 构建包含Kafka元数据的上下文信息，用于追踪和调试
        headers_list = getattr(msg, "headers", None)
        headers_dict: dict[str, Any] | None = None
        if headers_list:
            try:
                # 安全地解码headers中的字节数据为UTF-8字符串
                headers_dict = {
                    k: (v.decode("utf-8") if isinstance(v, bytes | bytearray) else v) for k, v in headers_list
                }
            except Exception:
                # 解码失败时保持原始格式，避免处理中断
                headers_dict = None

        context = {
            "topic": getattr(msg, "topic", None),
            "partition": getattr(msg, "partition", None),
            "offset": getattr(msg, "offset", None),
            "timestamp": getattr(msg, "timestamp", None),
            "key": getattr(msg, "key", None),
            "headers": headers_dict or headers_list,
            "meta": meta,
        }

        return safe_message, context, correlation_id, message_id

    async def process_message_with_retry(
        self,
        msg: Any,
        safe_message: dict[str, Any],
        context: dict[str, Any],
        correlation_id: str | None,
        message_id: str | None,
        process_func: Callable[[dict[str, Any], dict[str, Any] | None], Any],
        agent_metrics: AgentMetrics,
        outbox_manager: BaseOutboxManager | None,
    ) -> dict[str, Any]:
        """带重试逻辑的消息处理核心方法。

        Args:
            msg: 原始Kafka消息
            safe_message: 解码后的消息内容
            context: 消息上下文
            correlation_id: 用于链路追踪的关联ID
            message_id: 消息ID
            process_func: 处理消息的业务函数
            agent_metrics: Agent指标收集器
            outbox_manager: 可靠消息传递的发件箱管理器（必需）

        Returns:
            dict with keys:
            - handled: bool - 消息是否已处理（成功或发送到DLT）
            - success: bool - 仅在消息成功处理时为True
        """
        attempt = 0
        start = asyncio.get_event_loop().time()

        while True:
            try:
                result: dict[str, Any] | None = await process_func(safe_message, context)
                if result:
                    await self._send_result(
                        result,
                        retries=attempt,
                        correlation_id=correlation_id,
                        message_id=message_id,
                        outbox_manager=outbox_manager,
                    )

                # 只记录处理延迟，处理计数由BaseAgent处理
                end = asyncio.get_event_loop().time()
                latency_ms = (end - start) * 1000.0
                agent_metrics.record_processing_latency(latency_ms)

                # 可选的延迟指标记录，忽略任何异常避免影响主流程
                with suppress(Exception):
                    record_latency(self.agent_name, end - start)

                return {"handled": True, "success": True}

            except asyncio.CancelledError:
                # 协程取消异常需要向上传播，不进行重试处理
                raise
            except Exception as e:
                # 使用传入的错误分类函数而不是error_handler.classify_error
                classification = self.classify_error_func(e, safe_message)

                if classification == "non_retriable":
                    # 不可重试错误立即发送到死信队列
                    await self._handle_non_retriable_error(
                        msg,
                        safe_message,
                        e,
                        attempt,
                        correlation_id,
                        message_id,
                        agent_metrics,
                        outbox_manager,
                    )
                    return {"handled": True, "success": False}
                else:
                    # 可重试错误进行重试处理
                    attempt += 1
                    if await self.error_handler.handle_retry(e, attempt, message_id, correlation_id):
                        agent_metrics.increment_retries()
                        continue
                    else:
                        # 重试次数耗尽，发送到死信队列
                        await self._handle_exhausted_retries(
                            msg,
                            safe_message,
                            e,
                            attempt,
                            correlation_id,
                            message_id,
                            agent_metrics,
                            outbox_manager,
                        )
                        return {"handled": True, "success": False}

    async def _handle_non_retriable_error(
        self,
        msg: Any,
        safe_message: dict[str, Any],
        error: Exception,
        attempts: int,
        correlation_id: str | None,
        message_id: str | None,
        agent_metrics: Any,  # AgentMetrics对象
        outbox_manager: "BaseOutboxManager | None" = None,
    ) -> None:
        """处理不可重试错误，通过发件箱发送到死信队列。"""
        if outbox_manager:
            try:
                await self.error_handler.send_to_dlt(
                    msg,
                    safe_message,
                    error,
                    attempts=attempts,
                    correlation_id=correlation_id,
                    message_id=message_id,
                    outbox_manager=outbox_manager,
                )
            except Exception:
                # DLT发送失败，记录错误但不影响主流程
                self.log.error("dlt_send_failed", exc_info=True)
        else:
            self.log.error("no_outbox_for_dlt", message_id=message_id)

        # 更新相关指标统计
        agent_metrics.increment_failed()
        agent_metrics.increment_dlt()
        agent_metrics.record_error(str(error))
        self.error_handler.record_error_metrics("non_retriable")

    async def _handle_exhausted_retries(
        self,
        msg: Any,
        safe_message: dict[str, Any],
        error: Exception,
        attempts: int,
        correlation_id: str | None,
        message_id: str | None,
        agent_metrics: Any,  # AgentMetrics对象
        outbox_manager: "BaseOutboxManager | None" = None,
    ) -> None:
        """处理重试次数耗尽的情况，通过发件箱发送到死信队列。"""
        if outbox_manager:
            try:
                await self.error_handler.send_to_dlt(
                    msg,
                    safe_message,
                    error,
                    attempts=attempts,
                    correlation_id=correlation_id,
                    message_id=message_id,
                    outbox_manager=outbox_manager,
                )
            except Exception:
                # DLT发送失败，记录错误但不影响主流程
                self.log.error("dlt_send_failed", exc_info=True)
        else:
            self.log.error("no_outbox_for_dlt", message_id=message_id)

        # 更新相关指标统计
        agent_metrics.increment_failed()
        agent_metrics.increment_dlt()
        agent_metrics.record_error(str(error))
        self.error_handler.record_error_metrics("exhausted")

    async def _send_result(
        self,
        result: dict[str, Any],
        *,
        retries: int,
        correlation_id: str | None,
        message_id: str | None,
        outbox_manager: "BaseOutboxManager | None" = None,
    ) -> None:
        """通过发件箱将处理结果发送到输出主题。

        Args:
            result: 包含可选_topic和_key字段的处理结果
            retries: 重试次数
            correlation_id: 用于链路追踪的关联ID
            message_id: 消息ID
            outbox_manager: 可靠传递的发件箱管理器（必需）
        """
        # 获取目标主题，从结果中移除避免传播到下游
        topic = result.pop("_topic", None)

        if not topic:
            self.log.warning("no_topic_for_result", message_id=message_id)
            return

        # 分区键支持：优先使用显式_key，然后回退到业务字段
        key_value = result.pop("_key", None)
        if not key_value:
            # 智能回退：使用session_id或user_id进行分区，确保相同会话的消息有序
            key_value = result.get("session_id") or result.get("user_id")
            if key_value:
                self.log.debug(
                    "using_fallback_partition_key",
                    key=key_value,
                    source="session_id" if "session_id" in result else "user_id",
                )

        # 如果业务逻辑未提供重试信息，则附加重试次数
        result.setdefault("retries", retries)

        # 编码为Envelope格式
        encoded = encode_message(self.agent_name, result, correlation_id=correlation_id, retries=retries)

        # 通过发件箱发送以确保可靠传递
        if outbox_manager:
            try:
                outbox_id = await outbox_manager.enqueue_message(
                    topic=topic,
                    payload=encoded,
                    key=str(key_value) if key_value is not None else None,
                    correlation_id=correlation_id,
                )
                self.log.debug(
                    "result_enqueued_to_outbox",
                    topic=topic,
                    key=key_value,
                    retries=retries,
                    correlation_id=correlation_id,
                    message_id=message_id,
                    outbox_id=outbox_id,
                )
            except Exception as e:
                self.log.error("outbox_enqueue_failed", error=str(e), topic=topic)
                raise
        else:
            self.log.error(
                "no_outbox_for_result",
                message="Outbox manager not provided",
                topic=topic,
                message_id=message_id,
            )
            raise ValueError("Outbox manager required for sending result")
