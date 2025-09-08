import os
import time
from contextlib import suppress

import pytest
from pymilvus import connections, utility
from testcontainers.milvus import MilvusContainer

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
