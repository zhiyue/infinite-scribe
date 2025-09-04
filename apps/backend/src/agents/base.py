"""Base Agent class for all agent services."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import uuid4

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from aiokafka.structs import OffsetAndMetadata, TopicPartition

from ..core.config import settings
from ..core.logging.config import get_logger
from .errors import NonRetriableError
from .message import decode_message, encode_message

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agent services with Kafka integration."""

    def __init__(self, name: str, consume_topics: list[str], produce_topics: list[str] | None = None):
        self.name = name
        self.config = settings
        self.consume_topics = consume_topics
        self.produce_topics = produce_topics or []

        # Kafka 组件
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None

        # 运行状态
        self.is_running = False
        self._stopping = False
        self._stop_lock = asyncio.Lock()

        # Kafka 配置（遵循统一 Settings）
        self.kafka_bootstrap_servers = self.config.kafka_bootstrap_servers
        self.kafka_group_id = f"{self.config.kafka_group_id_prefix}-{self.name}-agent-group"

        # 处理策略配置（骨架，若 Settings 未定义则使用默认值）
        self.max_retries: int = self.config.agent_max_retries
        self.retry_backoff_ms: int = self.config.agent_retry_backoff_ms
        self.dlt_suffix: str = self.config.agent_dlt_suffix
        self.commit_batch_size: int = self.config.agent_commit_batch_size
        self.commit_interval_ms: int = self.config.agent_commit_interval_ms

        # 手动提交偏移批量状态
        self._pending_offsets: dict[TopicPartition, int] = {}
        self._since_last_commit: int = 0
        self._last_commit_monotonic: float = asyncio.get_event_loop().time()

        # 简易指标
        self.metrics: dict[str, int | float] = {
            "consumed": 0,
            "processed": 0,
            "failed": 0,
            "retries": 0,
            "dlt": 0,
            "processing_latency_ms_sum": 0.0,
        }

        # 配置校验
        self._validate_config()

        # Structured logger bound with agent context
        self.log: Any = get_logger("agent").bind(agent=self.name)

        # Agent status
        self.connected: bool = False
        self.ready: bool = False
        self.assigned_partitions: list[str] = []
        self.last_message_at: datetime | None = None
        self.lag: int | None = None

    def _validate_config(self) -> None:
        if self.max_retries < 0:
            raise ValueError("agent_max_retries must be >= 0")
        if self.retry_backoff_ms < 0:
            raise ValueError("agent_retry_backoff_ms must be >= 0")
        if self.commit_batch_size <= 0:
            raise ValueError("agent_commit_batch_size must be > 0")
        if self.commit_interval_ms < 0:
            raise ValueError("agent_commit_interval_ms must be >= 0")

    @abstractmethod
    async def process_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """处理接收到的消息

        Args:
            message: 解析后的消息内容

        Returns:
            需要发送的响应消息,如果不需要响应则返回 None
        """
        pass

    async def _create_consumer(self) -> AIOKafkaConsumer:
        """创建 Kafka 消费者"""
        if not self.consume_topics:
            self.log.warning("consumer_skipped_idle", reason="no_consume_topics")
            raise RuntimeError("No consume topics configured")

        consumer = AIOKafkaConsumer(
            *self.consume_topics,
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.kafka_group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset=self.config.kafka_auto_offset_reset,
            enable_auto_commit=False,
        )
        await consumer.start()
        self.connected = True
        # Attempt to get current assignment (may be empty until poll)
        try:
            assignment = consumer.assignment()
            self.assigned_partitions = [f"{tp.topic}:{tp.partition}" for tp in assignment] if assignment else []
        except Exception:
            self.assigned_partitions = []
        self.log.info("consumer_started", topics=self.consume_topics, connected=self.connected, assignment=self.assigned_partitions)
        return consumer

    async def _create_producer(self) -> AIOKafkaProducer:
        """创建 Kafka 生产者"""
        producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            enable_idempotence=True,
            linger_ms=5,
            retries=5,
        )
        await producer.start()
        self.log.info("producer_started")
        return producer

    async def _consume_messages(self):
        """消费 Kafka 消息的主循环"""
        try:
            consumer = self.consumer
            if consumer is None:
                self.log.error("consumer_not_initialized")
                return

            async for msg in consumer:
                if not self.is_running:
                    break

                try:
                    # 解码消息（Envelope 或原始 dict）
                    message_value = cast(dict[str, Any] | None, getattr(msg, "value", None))
                    raw_value: dict[str, Any] = message_value if isinstance(message_value, dict) else {}
                    safe_message, meta = decode_message(raw_value)
                    correlation_id = cast(str | None, meta.get("correlation_id"))
                    message_id = cast(str | None, meta.get("message_id") or meta.get("id"))

                    # 记录接收到的消息
                    self.log.debug(
                        "message_received",
                        topic=msg.topic,
                        partition=msg.partition,
                        offset=msg.offset,
                        message_id=message_id,
                        correlation_id=correlation_id,
                    )

                    # 处理消息（带重试与 DLT 骨架）

                    self.metrics["consumed"] = int(self.metrics.get("consumed", 0)) + 1

                    attempt = 0
                    start = asyncio.get_event_loop().time()
                    while True:
                        try:
                            result: dict[str, Any] | None = await self.process_message(safe_message)
                            if result:
                                await self._send_result(result, retries=attempt, correlation_id=correlation_id, message_id=message_id)
                            # 处理成功，记录 offset 并根据阈值批量提交
                            await self._record_offset_and_maybe_commit(msg)
                            self.metrics["processed"] = int(self.metrics.get("processed", 0)) + 1
                            self.last_message_at = datetime.now(UTC)
                            break
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            classification = self.classify_error(e, safe_message)
                            if classification == "non_retriable":
                                # 直接 DLT，不做重试
                                try:
                                    await self._send_to_dlt(msg, safe_message, e, attempts=attempt, correlation_id=correlation_id, message_id=message_id)
                                except Exception:
                                    self.log.error("dlt_send_failed", exc_info=True)
                                await self._record_offset_and_maybe_commit(msg)
                                self.metrics["failed"] = int(self.metrics.get("failed", 0)) + 1
                                self.metrics["dlt"] = int(self.metrics.get("dlt", 0)) + 1
                                break
                            else:
                                attempt += 1
                                if attempt <= self.max_retries:
                                    backoff = (self.retry_backoff_ms / 1000.0) * (2 ** (attempt - 1))
                                    self.log.warning(
                                        "message_retry",
                                        attempt=attempt,
                                        max_retries=self.max_retries,
                                        backoff_s=backoff,
                                        message_id=message_id,
                                        correlation_id=correlation_id,
                                        exc_info=True,
                                    )
                                    self.metrics["retries"] = int(self.metrics.get("retries", 0)) + 1
                                    await asyncio.sleep(backoff)
                                    continue
                                # 超过重试次数，发送到 DLT 并提交偏移
                                try:
                                    await self._send_to_dlt(msg, safe_message, e, attempts=attempt, correlation_id=correlation_id, message_id=message_id)
                                except Exception:
                                    self.log.error("dlt_send_failed", exc_info=True)
                                # 无论 DLT 成功与否，均记录偏移并触发批量提交
                                await self._record_offset_and_maybe_commit(msg)
                                self.metrics["failed"] = int(self.metrics.get("failed", 0)) + 1
                                self.metrics["dlt"] = int(self.metrics.get("dlt", 0)) + 1
                                break
                    end = asyncio.get_event_loop().time()
                    self.metrics["processing_latency_ms_sum"] = float(
                        self.metrics.get("processing_latency_ms_sum", 0.0)
                    ) + (end - start) * 1000.0

                except Exception as e:
                    self.log.error("message_loop_error", error=str(e), exc_info=True)

        except Exception as e:
            self.log.error("consume_loop_error", error=str(e), exc_info=True)

    async def _commit_offset_for_message(self, msg: Any) -> None:
        """提交指定消息的偏移（立即提交，不建议频繁调用）。"""
        consumer = self.consumer
        if consumer is None:
            return
        tp = TopicPartition(msg.topic, msg.partition)
        offsets = {tp: OffsetAndMetadata(msg.offset + 1, None)}
        await consumer.commit(offsets=offsets)
        self.log.debug("offset_committed", topic=msg.topic, partition=msg.partition, offset=msg.offset)

    async def _record_offset_and_maybe_commit(self, msg: Any, force: bool = False) -> None:
        """记录偏移并评估是否需要批量提交。"""
        consumer = self.consumer
        if consumer is None:
            return
        tp = TopicPartition(msg.topic, msg.partition)
        commit_offset = msg.offset + 1
        prev = self._pending_offsets.get(tp)
        if prev is None or commit_offset > prev:
            self._pending_offsets[tp] = commit_offset
        self._since_last_commit += 1
        await self._maybe_commit_offsets(force=force)

    async def _maybe_commit_offsets(self, force: bool = False) -> None:
        consumer = self.consumer
        if consumer is None or not self._pending_offsets:
            return
        now = asyncio.get_event_loop().time()
        interval_exceeded = (now - self._last_commit_monotonic) * 1000.0 >= self.commit_interval_ms
        size_exceeded = self._since_last_commit >= self.commit_batch_size
        if force or interval_exceeded or size_exceeded:
            offsets = {tp: OffsetAndMetadata(offset, None) for tp, offset in self._pending_offsets.items()}
            await consumer.commit(offsets=offsets)
            self.log.debug("offsets_batch_committed", offsets={f"{tp.topic}:{tp.partition}": off for tp, off in offsets.items()})
            self._pending_offsets.clear()
            self._since_last_commit = 0
            self._last_commit_monotonic = now

    async def _send_to_dlt(self, msg: Any, payload: dict[str, Any], error: Exception, *, attempts: int, correlation_id: str | None, message_id: str | None) -> None:
        """发送失败消息到 DLT 主题（简单骨架）。"""
        # 确保 producer 可用
        if self.producer is None:
            self.producer = await self._create_producer()

        dlt_topic = f"{msg.topic}{self.dlt_suffix}" if getattr(msg, "topic", None) else "deadletter"

        correlation_id = payload.get("correlation_id") if isinstance(payload, dict) else None

        body: dict[str, Any] = {
            "type": "error",
            "agent": self.name,
            "original_topic": getattr(msg, "topic", None),
            "partition": getattr(msg, "partition", None),
            "offset": getattr(msg, "offset", None),
            "error": str(error),
            "payload": payload,
            # Envelope fields
            "id": str(uuid4()),
            "ts": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id,
            "message_id": message_id,
            # Metrics and retry info
            "retries": attempts,
        }

        assert self.producer is not None
        # Use correlation_id as key when available to keep ordering by correlation
        key_bytes = None
        if correlation_id is not None:
            key_bytes = str(correlation_id).encode("utf-8")
        await self.producer.send_and_wait(dlt_topic, body, key=key_bytes)
        self.log.warning("sent_to_dlt", dlt_topic=dlt_topic, correlation_id=correlation_id, message_id=message_id, retries=attempts)

    async def _send_result(self, result: dict[str, Any], *, retries: int, correlation_id: str | None, message_id: str | None) -> None:
        """发送处理结果"""
        # 从结果中获取目标主题,或使用默认主题
        topic = result.pop("_topic", None)
        if not topic and self.produce_topics:
            topic = self.produce_topics[0]

        if topic:
            producer = self.producer
            if producer is None:
                # 若未初始化生产者，则创建（允许生产者在仅消费型 agent 中被动创建）
                producer = await self._create_producer()
                self.producer = producer
            try:
                # Optional partitioning key support
                key_value = result.pop("_key", None)
                key_bytes = str(key_value).encode("utf-8") if key_value is not None else None
                # Attach retries info if not provided by business logic
                result.setdefault("retries", retries)
                # Encode envelope
                encoded = encode_message(self.name, result, correlation_id=correlation_id, retries=retries)
                await producer.send_and_wait(topic, encoded, key=key_bytes)
                self.log.debug("result_sent", topic=topic, key=key_value, retries=retries, correlation_id=correlation_id, message_id=message_id)
            except KafkaError as e:
                self.log.error("result_send_failed", error=str(e))
                # 抛出异常以触发上层重试/ DLT 逻辑
                raise

    def classify_error(self, error: Exception, message: dict[str, Any]) -> Literal["retriable", "non_retriable"]:
        """错误分类钩子：默认将 NonRetriableError 视为不可重试，其余为可重试。

        子类可覆盖此方法以按业务类型、错误码或内容进行分类。
        """
        if isinstance(error, NonRetriableError):
            return "non_retriable"
        return "retriable"

    async def start(self):
        """启动 agent 服务"""
        self.log.info("agent_starting")
        self.is_running = True
        self._stopping = False

        try:
            # 当未配置消费主题时，进入 idle 循环，避免任务立即退出
            if not self.consume_topics:
                self.log.info("agent_idle_mode")
                # 如果需要发送消息,创建生产者
                if self.produce_topics:
                    self.producer = await self._create_producer()

                await self.on_start()
                self.ready = True

                # Idle 循环，等待 stop 信号
                while self.is_running:
                    await asyncio.sleep(1)
            else:
                # 创建 Kafka 消费者
                self.consumer = await self._create_consumer()

                # 如果需要发送消息,创建生产者
                if self.produce_topics:
                    self.producer = await self._create_producer()

                # 调用子类的启动钩子
                await self.on_start()
                self.ready = True

                # 开始消费消息
                await self._consume_messages()

        except Exception as e:
            self.log.error("agent_start_failed", error=str(e), exc_info=True)
            raise
        finally:
            try:
                await self.stop()
            except Exception:
                # Swallow exceptions during cleanup to not mask original errors
                self.log.warning("agent_stop_during_finally_failed", exc_info=True)

    async def stop(self):
        """停止 agent 服务"""
        async with self._stop_lock:
            if self._stopping:
                logger.debug(f"{self.name} stop 已在进行中，跳过重复调用")
                return
            self._stopping = True
        self.log.info("agent_stopping")
        self.is_running = False

        # 调用子类的停止钩子
        try:
            await self.on_stop()
        except Exception:
            self.log.warning("agent_on_stop_failed", exc_info=True)

        # 关闭 Kafka 连接
        if self.consumer:
            # 优先冲刷提交未提交的偏移
            try:
                await self._maybe_commit_offsets(force=True)
            except Exception:
                self.log.warning("commit_remaining_offsets_failed", exc_info=True)
            try:
                await self.consumer.stop()
            except Exception:
                self.log.warning("consumer_stop_failed", exc_info=True)
            self.consumer = None

        if self.producer:
            try:
                await self.producer.stop()
            except Exception:
                self.log.warning("producer_stop_failed", exc_info=True)
            self.producer = None

        self.log.info("agent_stopped")

    def get_status(self) -> dict[str, Any]:
        """Return per-agent status for health reporting."""
        return {
            "running": self.is_running,
            "ready": self.ready,
            "connected": self.connected,
            "assigned_partitions": self.assigned_partitions,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "lag": self.lag,
            "metrics": self.metrics,
        }

    async def on_start(self):
        """启动时的钩子方法,子类可以重写"""
        # Provide a non-empty default implementation to satisfy linting rules
        logger.debug(f"{self.name} on_start hook invoked (default no-op)")

    async def on_stop(self):
        """停止时的钩子方法,子类可以重写"""
        # Provide a non-empty default implementation to satisfy linting rules
        logger.debug(f"{self.name} on_stop hook invoked (default no-op)")
