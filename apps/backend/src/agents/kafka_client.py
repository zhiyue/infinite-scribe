"""Kafka client management for agents."""

import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from ..core.config import settings
from ..core.logging.config import get_logger

logger = logging.getLogger(__name__)


class KafkaClientManager:
    """Manages Kafka consumer and producer creation and lifecycle."""

    def __init__(self, agent_name: str, consume_topics: list[str], produce_topics: list[str] | None = None):
        self.agent_name = agent_name
        self.consume_topics = consume_topics
        self.produce_topics = produce_topics or []

        # Kafka configuration
        self.kafka_bootstrap_servers = settings.kafka_bootstrap_servers
        self.kafka_group_id = f"{settings.kafka_group_id_prefix}-{agent_name}-agent-group"

        # Structured logger bound with agent context
        self.log: Any = get_logger("kafka").bind(agent=agent_name)

        # Client instances
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None

        # Status tracking
        self.connected: bool = False
        self.assigned_partitions: list[str] = []

    async def create_consumer(self) -> AIOKafkaConsumer:
        """Create and start Kafka consumer."""
        if not self.consume_topics:
            self.log.warning("consumer_skipped_idle", reason="no_consume_topics")
            raise RuntimeError("No consume topics configured")

        consumer = AIOKafkaConsumer(
            *self.consume_topics,
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.kafka_group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset=settings.kafka_auto_offset_reset,
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

        self.log.info(
            "consumer_started",
            topics=self.consume_topics,
            connected=self.connected,
            assignment=self.assigned_partitions,
        )
        self.consumer = consumer
        return consumer

    async def create_producer(self) -> AIOKafkaProducer:
        """Create and start Kafka producer."""
        producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            enable_idempotence=True,
            linger_ms=5,
        )
        await producer.start()
        self.log.info("producer_started")
        self.producer = producer
        return producer

    async def get_or_create_producer(self) -> AIOKafkaProducer:
        """Get existing producer or create new one."""
        if self.producer is None:
            self.producer = await self.create_producer()
        return self.producer

    async def stop_consumer(self) -> None:
        """Stop and cleanup consumer."""
        if self.consumer:
            try:
                await self.consumer.stop()
                self.log.info("consumer_stopped")
            except Exception:
                self.log.warning("consumer_stop_failed", exc_info=True)
            finally:
                self.consumer = None
                self.connected = False
                self.assigned_partitions = []

    async def stop_producer(self) -> None:
        """Stop and cleanup producer."""
        if self.producer:
            try:
                await self.producer.stop()
                self.log.info("producer_stopped")
            except Exception:
                self.log.warning("producer_stop_failed", exc_info=True)
            finally:
                self.producer = None

    async def stop_all(self) -> None:
        """Stop all Kafka clients."""
        await self.stop_consumer()
        await self.stop_producer()
