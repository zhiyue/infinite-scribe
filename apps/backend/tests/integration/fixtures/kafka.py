"""Kafka testcontainer fixtures and clients."""

import os
from collections.abc import Generator

import pytest
from testcontainers.kafka import KafkaContainer


@pytest.fixture(scope="session")
def kafka_container(pytestconfig: pytest.Config) -> Generator[KafkaContainer, None, None]:
    """
    会话级 Kafka 容器：启动一次，所有用例复用。
    """
    image = os.getenv("TEST_KAFKA_IMAGE", "confluentinc/cp-kafka:latest")

    container = KafkaContainer(image=image)
    # 启用 KRaft 模式
    container.with_kraft()

    # 进入 with 后自动启动，并在退出时自动清理（Ryuk 管理）
    with container as c:
        yield c


def _get_kafka_host_port(c: KafkaContainer) -> tuple[str, int]:
    """Extract Kafka connection details from container."""
    host = c.get_container_host_ip()
    port = int(c.get_exposed_port(c.port))
    return host, port


@pytest.fixture(scope="session")
def kafka_connection_info(kafka_container: KafkaContainer) -> dict[str, str]:
    """
    导出统一的连接信息，方便注入到被测应用（环境变量/配置）。
    """
    host, port = _get_kafka_host_port(kafka_container)
    info = {
        "host": host,
        "port": str(port),
        "bootstrap_servers": kafka_container.get_bootstrap_server(),
    }
    return info


@pytest.fixture(scope="session")
def kafka_bootstrap_servers(kafka_connection_info: dict[str, str]) -> str:
    return kafka_connection_info["bootstrap_servers"]


@pytest.fixture
def kafka_service(kafka_connection_info: dict[str, str]) -> dict[str, str]:
    """
    提供 Kafka 服务配置，与现有测试兼容。
    """
    return kafka_connection_info
