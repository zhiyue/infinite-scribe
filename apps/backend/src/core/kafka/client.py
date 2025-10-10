"""Kafka client management for agents."""

import asyncio
import contextlib
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import UnknownTopicOrPartitionError

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

    async def ensure_topics_exist(self, topics: list[str], max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """
        Ensure topics exist by triggering auto-creation through producer metadata refresh.

        Args:
            topics: List of topic names to ensure exist
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            True if all topics exist or were created, False otherwise
        """
        if not topics:
            return True

        # Create a temporary producer to trigger topic auto-creation
        temp_producer = None
        try:
            temp_producer = AIOKafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                enable_idempotence=True,
            )
            await temp_producer.start()

            for topic in topics:
                for attempt in range(max_retries):
                    try:
                        # Request metadata for the topic - this will trigger auto-creation if enabled
                        metadata = await temp_producer.client.fetch_all_metadata()
                        # Use partitions_for_topic to check if topic exists (recommended approach)
                        if metadata.partitions_for_topic(topic) is not None:
                            self.log.info("topic_metadata_fetched", topic=topic, attempt=attempt + 1)
                            break
                        else:
                            # Topic not found in metadata, but auto-creation should handle it
                            raise UnknownTopicOrPartitionError(f"Topic {topic} not found")
                    except UnknownTopicOrPartitionError:
                        if attempt < max_retries - 1:
                            self.log.info(
                                "topic_not_found_retrying", topic=topic, attempt=attempt + 1, max_retries=max_retries
                            )
                            await asyncio.sleep(retry_delay)
                        else:
                            self.log.warning(
                                "topic_creation_failed_after_retries", topic=topic, max_retries=max_retries
                            )
                            return False
                    except Exception as e:
                        self.log.warning("topic_metadata_fetch_error", topic=topic, error=str(e))
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                        else:
                            return False

            self.log.info("topics_ensured", topics=topics)
            return True

        except Exception as e:
            self.log.error("ensure_topics_failed", topics=topics, error=str(e))
            return False
        finally:
            if temp_producer:
                with contextlib.suppress(Exception):
                    await temp_producer.stop()

    async def create_producer_with_topic_check(self, ensure_topics: bool = True) -> AIOKafkaProducer:
        """
        Create producer and optionally ensure produce topics exist.

        Args:
            ensure_topics: Whether to check/create topics before returning producer

        Returns:
            Configured and started producer
        """
        producer = await self.create_producer()

        if ensure_topics and self.produce_topics:
            success = await self.ensure_topics_exist(self.produce_topics)
            if not success:
                self.log.warning("producer_created_with_topic_warnings", topics=self.produce_topics)

        return producer
