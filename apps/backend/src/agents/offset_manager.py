"""Offset management for Kafka consumers."""

import asyncio
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import OffsetAndMetadata, TopicPartition

from src.core.logging.config import get_logger


class OffsetManager:
    """Manages Kafka consumer offsets with batching support."""

    def __init__(self, agent_name: str, commit_batch_size: int, commit_interval_ms: int):
        self.agent_name = agent_name
        self.commit_batch_size = commit_batch_size
        self.commit_interval_ms = commit_interval_ms

        # Structured logger bound with agent context
        self.log: Any = get_logger("offset").bind(agent=agent_name)

        # Batching state
        self._pending_offsets: dict[TopicPartition, int] = {}
        self._since_last_commit: int = 0
        # 统一时间源：初始化时设为0，首次使用时会设置为当前时间
        self._last_commit_time: float = 0.0

    async def commit_offset_for_message(self, consumer: AIOKafkaConsumer, msg: Any) -> None:
        """Commit offset for specific message immediately (not recommended for frequent use)."""
        tp = TopicPartition(msg.topic, msg.partition)
        offsets = {tp: OffsetAndMetadata(msg.offset + 1, "")}
        await consumer.commit(offsets=offsets)
        self.log.debug("offset_committed", topic=msg.topic, partition=msg.partition, offset=msg.offset)

    async def record_offset_and_maybe_commit(self, consumer: AIOKafkaConsumer, msg: Any, force: bool = False) -> None:
        """Record offset and evaluate whether to perform batch commit."""
        tp = TopicPartition(msg.topic, msg.partition)
        commit_offset = msg.offset + 1
        prev = self._pending_offsets.get(tp)
        if prev is None or commit_offset > prev:
            self._pending_offsets[tp] = commit_offset
        self._since_last_commit += 1
        await self._maybe_commit_offsets(consumer, force=force)

    async def _maybe_commit_offsets(self, consumer: AIOKafkaConsumer, force: bool = False) -> None:
        """Commit pending offsets if thresholds are met."""
        if not self._pending_offsets:
            return

        now = asyncio.get_event_loop().time()

        # 初始化时间（首次调用时）
        if self._last_commit_time == 0.0:
            self._last_commit_time = now

        interval_exceeded = (now - self._last_commit_time) * 1000.0 >= self.commit_interval_ms
        size_exceeded = self._since_last_commit >= self.commit_batch_size

        if force or interval_exceeded or size_exceeded:
            offsets = {tp: OffsetAndMetadata(offset, "") for tp, offset in self._pending_offsets.items()}
            await consumer.commit(offsets=offsets)
            self.log.debug(
                "offsets_batch_committed", offsets={f"{tp.topic}:{tp.partition}": off for tp, off in offsets.items()}
            )
            self._pending_offsets.clear()
            self._since_last_commit = 0
            self._last_commit_time = now

    async def flush_pending_offsets(self, consumer: AIOKafkaConsumer) -> None:
        """Force commit all pending offsets."""
        await self._maybe_commit_offsets(consumer, force=True)
