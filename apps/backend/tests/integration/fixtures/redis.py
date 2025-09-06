"""Redis testcontainer fixtures and clients."""

import os
import re
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
import redis as redislib  # Sync Redis for JWT service
import redis.asyncio as aioredis  # Async Redis for main services
import src.common.services.redis_service as redis_mod
from src.common.services.redis_service import RedisService
from src.core.config import settings
from testcontainers.redis import RedisContainer
from tests.helpers.prefix_client import AsyncPrefixedRedis, PrefixedRedis


@pytest.fixture(scope="session")
def redis_container(pytestconfig: pytest.Config) -> Generator[RedisContainer, None, None]:
    """
    会话级 Redis 容器：启动一次，所有用例复用。
    """
    image = os.getenv("TEST_REDIS_IMAGE", "redis:7-alpine")

    container = RedisContainer(image=image)

    # 进入 with 后自动启动，并在退出时自动清理（Ryuk 管理）
    with container as c:
        yield c


def _get_redis_host_port_password(c: RedisContainer) -> tuple[str, int, str | None]:
    """Extract Redis connection details from container."""
    host = c.get_container_host_ip()
    port = int(c.get_exposed_port(c.port))
    # RedisContainer.__init__ 有 password 参数，保存于属性
    password = getattr(c, "password", None)
    return host, port, password


@pytest.fixture(scope="session")
def redis_connection_info(redis_container: RedisContainer) -> dict[str, str]:
    """
    导出统一的连接信息，方便注入到被测应用（环境变量/配置）。
    """
    host, port, password = _get_redis_host_port_password(redis_container)
    info = {
        "host": host,
        "port": str(port),
        "password": password or "",
        "url": (f"redis://:{password}@{host}:{port}/0" if password else f"redis://{host}:{port}/0"),
    }
    return info


@pytest.fixture(scope="session")
def redis_url(redis_connection_info: dict[str, str]) -> str:
    return redis_connection_info["url"]


@pytest.fixture(scope="session")
def redis_session_client(redis_container: RedisContainer) -> redislib.Redis:
    """
    会话级同步客户端（适用于 JWT service 等同步场景）。
    decode_responses=True 返回 str，断言更直观。
    """
    host, port, password = _get_redis_host_port_password(redis_container)
    client = redislib.Redis(host=host, port=port, password=password, db=0, decode_responses=True)
    # 触发一次 PING 确认就绪
    client.ping()
    return client


@pytest.fixture(scope="session")
async def redis_async_session_client(redis_container: RedisContainer) -> aioredis.Redis:
    """
    会话级异步客户端（适用于 RedisService 等异步场景）。
    decode_responses=True 返回 str，断言更直观。
    """
    host, port, password = _get_redis_host_port_password(redis_container)
    client = aioredis.Redis(host=host, port=port, password=password, db=0, decode_responses=True)
    # 触发一次 PING 确认就绪
    await client.ping()
    return client


def _xdist_worker_suffix() -> str:
    """
    pytest-xdist 并发时会设置 env: PYTEST_XDIST_WORKER=gw0/gw1/...
    我们为 key 前缀带上 worker id，减少并发写入冲突。
    """
    wid = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    # 清理一下可能的非字母数字字符
    wid = re.sub(r"[^A-Za-z0-9]+", "", wid)
    return wid


@pytest.fixture(scope="function")
def redis_test_prefix() -> str:
    """
    生成当前用例专用 Key 前缀，形如：t:gw0:7b9c5f2f
    """
    return f"t:{_xdist_worker_suffix()}:{uuid.uuid4().hex[:8]}:"


@pytest.fixture(scope="function")
def redis_client(
    request: pytest.FixtureRequest,
    pytestconfig: pytest.Config,
    redis_session_client: redislib.Redis,
    redis_test_prefix: str,
):
    """
    用例级同步客户端 + 清理策略（适用于 JWT service 等）：
    - 推荐：prefix 模式（仅删除以该前缀开的 keys，速度快、风险低）
    - 备选：flushdb 模式（每用例清库，最干净但影响并发）
    """
    clean_strategy = str(pytestconfig.getoption("--redis-clean-strategy"))

    # —— 用例开始前：先做一次清理（幂等）
    if clean_strategy == "flushdb":
        redis_session_client.flushdb()
    else:
        # prefix: 先删掉历史残留（基本不会有，但保证幂等）
        keys = list(redis_session_client.scan_iter(match=f"{redis_test_prefix}*"))
        if keys:
            redis_session_client.delete(*keys)

    # 使用独立的 PrefixedRedis 辅助类
    prefixed = PrefixedRedis(redis_session_client, redis_test_prefix)

    yield prefixed

    # —— 用例结束后：根据策略清理
    if clean_strategy == "flushdb":
        redis_session_client.flushdb()
    else:
        prefixed.delete_prefixed()


@pytest.fixture(scope="function")
async def redis_async_client(
    request: pytest.FixtureRequest,
    pytestconfig: pytest.Config,
    redis_async_session_client: aioredis.Redis,
    redis_test_prefix: str,
):
    """
    用例级异步客户端 + 清理策略（适用于 RedisService 等）：
    - 推荐：prefix 模式（仅删除以该前缀开的 keys，速度快、风险低）
    - 备选：flushdb 模式（每用例清库，最干净但影响并发）
    """
    clean_strategy = str(pytestconfig.getoption("--redis-clean-strategy"))

    # —— 用例开始前：先做一次清理（幂等）
    if clean_strategy == "flushdb":
        await redis_async_session_client.flushdb()
    else:
        # prefix: 先删掉历史残留（基本不会有，但保证幂等）
        keys = []
        async for key in redis_async_session_client.scan_iter(match=f"{redis_test_prefix}*"):
            keys.append(key)
        if keys:
            await redis_async_session_client.delete(*keys)

    # 使用独立的 AsyncPrefixedRedis 辅助类
    prefixed = AsyncPrefixedRedis(redis_async_session_client, redis_test_prefix)

    yield prefixed

    # —— 用例结束后：根据策略清理
    if clean_strategy == "flushdb":
        await redis_async_session_client.flushdb()
    else:
        await prefixed.delete_prefixed()


@pytest.fixture(scope="function")
async def redis_service_test(
    monkeypatch: pytest.MonkeyPatch,
    redis_url: str,
) -> AsyncGenerator[RedisService, None]:
    """
    - 替换模块级单例 redis_service 为新实例
    - 覆盖 settings.database.redis_url，确保只连测试容器
    - 用例前后 FLUSHDB，保证数据隔离
    """
    # 创建新实例并替换模块级单例，防止旧引用/旧连接残留
    svc = RedisService()
    monkeypatch.setattr(redis_mod, "redis_service", svc, raising=True)

    try:
        # 若 settings.database.redis_url 可写，直接覆盖
        settings.database.redis_url = redis_url  # type: ignore[attr-defined]
    except Exception:
        pass

    # 建立连接
    await svc.connect()

    # 用例前清库
    async with svc.acquire() as client:
        await client.flushdb()

    try:
        yield svc
    finally:
        # 用例后清库 + 断开连接，确保无泄漏
        try:
            async with svc.acquire() as client:
                await client.flushdb()
        finally:
            await svc.disconnect()
