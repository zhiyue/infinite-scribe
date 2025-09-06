"""Other service fixtures (Neo4j, Kafka, Milvus) for testing."""

import os
import time
from collections.abc import Generator
from contextlib import suppress
from typing import Any

import pytest
from pymilvus import connections, utility
from testcontainers.milvus import MilvusContainer
from testcontainers.neo4j import Neo4jContainer

# Import Kafka testcontainer conditionally since it's not always available
try:
    from testcontainers.kafka import KafkaContainer
except ImportError:
    KafkaContainer = None


@pytest.fixture(scope="session")
def neo4j_container() -> Generator[dict[str, str], Any, None]:
    """Provide Neo4j testcontainer configuration."""
    container = Neo4jContainer("neo4j:5")

    with container as c:
        yield {
            "host": c.get_container_host_ip(),
            "port": c.get_exposed_port(7687),
            "user": "neo4j",
            "password": c.password,
        }


@pytest.fixture(scope="session")
def kafka_container() -> Generator[dict[str, Any], Any, None]:
    """Provide Kafka testcontainer configuration with KRaft mode and pre-created topics."""
    if KafkaContainer is None:
        pytest.skip("KafkaContainer not available in testcontainers")

    # Start Kafka with KRaft and auto topic creation enabled
    container = (
        KafkaContainer()
        .with_kraft()
        .with_env("KAFKA_AUTO_CREATE_TOPICS_ENABLE", "true")
        .with_env("KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR", "1")
        .with_env("KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR", "1")
        .with_env("KAFKA_TRANSACTION_STATE_LOG_MIN_ISR", "1")
    )

    with container as c:
        bootstrap_server = c.get_bootstrap_server()
        print(f"Kafka testcontainer started: {bootstrap_server}")

        # Pre-create all topics used by tests and wait briefly for metadata
        try:
            import asyncio as _asyncio
            import time as _time

            from aiokafka.admin import AIOKafkaAdminClient, NewTopic

            topic_names = set(
                [
                    # Kafka integration test topics
                    "integration.test.e2e",
                    "integration.test.multi",
                    "integration.test.large",
                    "integration.test.concurrent",
                    "integration.test.headers",
                    "integration.test.scheduled",
                    "integration.test.retry",
                    "integration.test.shutdown",
                ]
                + [f"concurrency.test.{i}" for i in range(10)]
                + [f"immediate.topic.{i}" for i in range(5)]
                + [f"scheduled.topic.{i}" for i in range(3)]
                + [f"large.topic.{i}" for i in range(10)]
                + [f"test.topic.{i}" for i in range(10)]
            )

            async def _precreate(_bootstrap: str):
                admin = AIOKafkaAdminClient(bootstrap_servers=_bootstrap, request_timeout_ms=30000)
                await admin.start()
                try:
                    new_topics = [NewTopic(name=t, num_partitions=1, replication_factor=1) for t in topic_names]
                    try:
                        await admin.create_topics(new_topics=new_topics, validate_only=False)
                    except Exception as e:
                        # Ignore already exists and transient errors
                        if "exists" not in str(e).lower():
                            print(f"Warning: create_topics error: {e}")
                finally:
                    await admin.close()

            _asyncio.run(_precreate(bootstrap_server))
            # Brief pause to allow metadata propagation
            _time.sleep(1.0)
        except Exception as e:
            print(f"Warning: pre-creating topics failed or skipped: {e}")

        host, port = bootstrap_server.split(":")
        yield {
            "bootstrap_servers": [bootstrap_server],
            "host": host,
            "port": int(port),
        }


MILVUS_IMAGE = os.getenv("MILVUS_IMAGE", "milvusdb/milvus:v2.4.10")  # 固定版本
CONNECT_TIMEOUT_S = int(os.getenv("MILVUS_CONNECT_TIMEOUT", "60"))


@pytest.fixture(scope="session")
def milvus_container():
    """Provide Milvus connection (skip gracefully if container healthcheck fails)."""
    container = MilvusContainer(MILVUS_IMAGE)

    try:
        with container as c:
            host = c.get_container_host_ip()
            port = c.get_exposed_port(c.port)  # 默认 19530

            # 等待就绪：用 PyMilvus API 轮询而非盲睡
            deadline = time.time() + CONNECT_TIMEOUT_S
            last_err = None
            while time.time() < deadline:
                try:
                    connections.disconnect("default")
                    connections.connect(alias="default", host=host, port=port)
                    utility.list_collections()  # 触发一次请求验证
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(1)
            else:
                pytest.skip(f"Milvus not ready: {last_err}")

            try:
                yield {"host": host, "port": port}
            finally:
                with suppress(Exception):
                    connections.disconnect("default")
    except Exception as e:
        pytest.skip(f"Milvus container failed to start in this environment: {e}")
