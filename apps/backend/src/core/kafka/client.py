"""Kafka client management for agents."""

import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from ..config import settings
from ..logging.config import get_logger

logger = logging.getLogger(__name__)


class KafkaClientManager:
    """Manages Kafka consumer and producer creation and lifecycle."""

    def __init__(
        self,
        client_id: str,
        consume_topics: list[str],
        produce_topics: list[str] | None = None,
        group_id: str | None = None,
        logger_context: dict | None = None,
    ):
        """
        Initialize KafkaClientManager.

        Args:
            client_id: Unique identifier for this client (e.g., agent name, service name)
            consume_topics: List of topics to consume from
            produce_topics: Optional list of topics to produce to
            group_id: Optional custom group ID. If not provided, defaults to a generated one
            logger_context: Optional context for structured logging (e.g., {"agent": "name"})
        """
        self.client_id = client_id
        self.consume_topics = consume_topics
        self.produce_topics = produce_topics or []

        # Kafka configuration
        self.kafka_bootstrap_servers = settings.kafka_bootstrap_servers
        self.kafka_group_id = group_id or f"{settings.kafka_group_id_prefix}-{client_id}-group"

        # Structured logger with configurable context
        base_logger = get_logger("kafka")
        context = logger_context or {"client": client_id}
        self.log: Any = base_logger.bind(**context)

        # Client instances
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None

        # Status tracking
        self.connected: bool = False
        self.assigned_partitions: list[str] = []

    async def create_consumer(self) -> AIOKafkaConsumer:
        """Create and start Kafka consumer without subscribing to topics."""
        if not self.consume_topics:
            self.log.warning("consumer_skipped_idle", reason="no_consume_topics")
            raise RuntimeError("No consume topics configured")

        consumer = AIOKafkaConsumer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.kafka_group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset=settings.kafka_auto_offset_reset,
            enable_auto_commit=False,
        )
        await consumer.start()
        self.connected = True

        # Assignment will be available after subscribe() is called
        self.assigned_partitions = []

        self.log.info(
            "consumer_created",
            topics=self.consume_topics,
            connected=self.connected,
        )
        self.consumer = consumer
        return consumer

    def subscribe_consumer(self, listener=None) -> None:
        """
        Subscribe consumer to configured topics with optional rebalance listener.

        Args:
            listener: Optional rebalance listener for partition management
        """
        if not self.consumer:
            raise RuntimeError("Consumer not created. Call create_consumer() first.")

        if not self.consume_topics:
            raise RuntimeError("No consume topics configured")

        # Subscribe with or without listener
        if listener:
            self.consumer.subscribe(self.consume_topics, listener=listener)
            self.log.info(
                "consumer_subscribed_with_listener",
                topics=self.consume_topics,
                listener_type=type(listener).__name__,
            )
        else:
            self.consumer.subscribe(self.consume_topics)
            self.log.info(
                "consumer_subscribed",
                topics=self.consume_topics,
            )

    def update_assigned_partitions(self) -> None:
        """Update assigned partitions tracking after subscription."""
        if self.consumer:
            try:
                assignment = self.consumer.assignment()
                self.assigned_partitions = [f"{tp.topic}:{tp.partition}" for tp in assignment] if assignment else []
                self.log.info(
                    "consumer_assignment_updated",
                    assignment=self.assigned_partitions,
                )
            except Exception:
                self.assigned_partitions = []

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
