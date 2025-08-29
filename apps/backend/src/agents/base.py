"""Base Agent class for all agent services."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from ..core.config import settings

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

        # Kafka 配置
        self.kafka_bootstrap_servers = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.kafka_group_id = f"{self.name}-agent-group"

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
        consumer = AIOKafkaConsumer(
            *self.consume_topics,
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.kafka_group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await consumer.start()
        logger.info(f"{self.name} agent 已连接到 Kafka,订阅主题: {self.consume_topics}")
        return consumer

    async def _create_producer(self) -> AIOKafkaProducer:
        """创建 Kafka 生产者"""
        producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await producer.start()
        logger.info(f"{self.name} agent 已创建 Kafka 生产者")
        return producer

    async def _consume_messages(self):
        """消费 Kafka 消息的主循环"""
        try:
            async for msg in self.consumer:
                if not self.is_running:
                    break

                try:
                    # 记录接收到的消息
                    logger.debug(
                        f"{self.name} 接收到消息 - "
                        f"主题: {msg.topic}, "
                        f"分区: {msg.partition}, "
                        f"偏移: {msg.offset}"
                    )

                    # 处理消息
                    result: dict[str, Any] | None = await self.process_message(msg.value)

                    # 如果有返回结果,发送到对应主题
                    if result and self.producer:
                        await self._send_result(result)

                except Exception as e:
                    logger.error(f"{self.name} 处理消息时出错: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"{self.name} 消费循环出错: {e}", exc_info=True)

    async def _send_result(self, result: dict[str, Any]):
        """发送处理结果"""
        # 从结果中获取目标主题,或使用默认主题
        topic = result.pop("_topic", None)
        if not topic and self.produce_topics:
            topic = self.produce_topics[0]

        if topic:
            try:
                await self.producer.send_and_wait(topic, result)
                logger.debug(f"{self.name} 发送结果到主题: {topic}")
            except KafkaError as e:
                logger.error(f"{self.name} 发送结果失败: {e}")

    async def start(self):
        """启动 agent 服务"""
        logger.info(f"正在启动 {self.name} agent")
        self.is_running = True

        try:
            # 创建 Kafka 消费者
            self.consumer = await self._create_consumer()

            # 如果需要发送消息,创建生产者
            if self.produce_topics:
                self.producer = await self._create_producer()

            # 调用子类的启动钩子
            await self.on_start()

            # 开始消费消息
            await self._consume_messages()

        except Exception as e:
            logger.error(f"{self.name} agent 启动失败: {e}", exc_info=True)
            raise
        finally:
            await self.stop()

    async def stop(self):
        """停止 agent 服务"""
        logger.info(f"正在停止 {self.name} agent")
        self.is_running = False

        # 调用子类的停止钩子
        await self.on_stop()

        # 关闭 Kafka 连接
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None

        if self.producer:
            await self.producer.stop()
            self.producer = None

        logger.info(f"{self.name} agent 已停止")

    async def on_start(self):
        """启动时的钩子方法,子类可以重写"""
        # Provide a non-empty default implementation to satisfy linting rules
        logger.debug(f"{self.name} on_start hook invoked (default no-op)")

    async def on_stop(self):
        """停止时的钩子方法,子类可以重写"""
        # Provide a non-empty default implementation to satisfy linting rules
        logger.debug(f"{self.name} on_stop hook invoked (default no-op)")
