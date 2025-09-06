"""Integration test specific fixtures."""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Dict, Optional, Tuple
from unittest.mock import AsyncMock, patch

import pytest
import redis as redislib
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.redis import RedisContainer

# 使用 PostgreSQL 的集成测试专用 fixtures


@pytest.fixture(autouse=True)
def _patch_outbox_relay_database_session(request: pytest.FixtureRequest):
    """Patch OutboxRelayService to use the test database session.

    This ensures that the OutboxRelayService uses the same testcontainer database
    as the integration tests, rather than the configured production database.
    """
    # Only apply this patch for integration tests that involve OutboxRelay
    test_name = request.node.name
    if "outbox" not in test_name.lower() and "relay" not in test_name.lower():
        yield
        return

    from contextlib import asynccontextmanager
    from unittest.mock import patch

    # Get the test database session from the request
    postgres_test_session_fixture = None
    for fixture_name in request.fixturenames:
        if fixture_name == "postgres_test_session":
            postgres_test_session_fixture = request.getfixturevalue("postgres_test_session")
            break

    if postgres_test_session_fixture is None:
        yield
        return

    # Create a mock create_sql_session that uses the test database
    @asynccontextmanager
    async def mock_create_sql_session():
        # Use the test database session instead of creating a new one
        try:
            yield postgres_test_session_fixture
            # Don't commit here since it's handled by the test session management
        except Exception:
            await postgres_test_session_fixture.rollback()
            raise

    with patch("src.services.outbox.relay.create_sql_session", mock_create_sql_session):
        yield


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add Redis-specific CLI options for integration tests."""
    group = parser.getgroup("redis")
    group.addoption(
        "--redis-image",
        action="store",
        default=os.getenv("TEST_REDIS_IMAGE", "redis:7-alpine"),
        help="Redis 镜像（默认：redis:7-alpine，可用 env TEST_REDIS_IMAGE 覆盖）",
    )
    group.addoption(
        "--redis-password",
        action="store",
        default=os.getenv("TEST_REDIS_PASSWORD", None),
        help="为测试 Redis 开启密码（默认禁用，可用 env TEST_REDIS_PASSWORD 设定）",
    )
    group.addoption(
        "--redis-aof",
        action="store_true",
        default=os.getenv("TEST_REDIS_AOF", "false").lower() == "true",
        help="是否启用 AOF 持久化（仅测试需要验证持久化时打开）",
    )
    group.addoption(
        "--redis-clean-strategy",
        action="store",
        choices=("prefix", "flushdb"),
        default=os.getenv("TEST_REDIS_CLEAN_STRATEGY", "prefix"),
        help="用例清理策略：prefix（推荐）或 flushdb",
    )


def pytest_configure(config: pytest.Config) -> None:
    """注册自定义 markers，避免 UnknownMark 警告。"""
    config.addinivalue_line(
        "markers",
        "redis_integration: 需要 Redis 集成测试的用例标记（用于选择性运行）",
    )


@pytest.fixture
async def db_session(postgres_test_session) -> AsyncGenerator[AsyncSession, None]:
    """提供 PostgreSQL 数据库会话用于集成测试，并在每个测试后清理数据。"""

    async def clean_all_tables():
        """清理数据库中的所有用户创建的表（跳过系统表）"""
        # 获取所有用户创建的表名
        result = await postgres_test_session.execute(
            text("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename != 'alembic_version'
                ORDER BY tablename
            """)
        )
        table_names = [row[0] for row in result.fetchall()]

        if table_names:
            # 使用 TRUNCATE CASCADE 清理所有表
            tables_list = ", ".join(table_names)
            await postgres_test_session.execute(text(f"TRUNCATE TABLE {tables_list} CASCADE"))

        await postgres_test_session.commit()

    # 在测试开始前清理数据库
    await clean_all_tables()

    # 提供会话给测试
    yield postgres_test_session

    # 测试后再次清理（可选，但有助于确保隔离）
    await clean_all_tables()


# -----------------------------
# Redis Container Setup for Integration Tests
# -----------------------------
@pytest.fixture(scope="session")
def redis_container(pytestconfig: pytest.Config) -> Generator[RedisContainer, None, None]:
    """
    会话级 Redis 容器：启动一次，所有用例复用。
    """
    image = pytestconfig.getoption("--redis-image")
    password = pytestconfig.getoption("--redis-password")
    enable_aof = pytestconfig.getoption("--redis-aof")

    container = RedisContainer(image=image, password=password)

    # 如需测试持久化或特殊参数，可通过 with_command 注入
    if enable_aof:
        container = container.with_command("redis-server --appendonly yes")

    # 进入 with 后自动启动，并在退出时自动清理（Ryuk 管理）
    with container as c:
        yield c


def _get_host_port_password(c: RedisContainer) -> Tuple[str, int, Optional[str]]:
    """Extract Redis connection details from container."""
    host = c.get_container_host_ip()
    port = int(c.get_exposed_port(c.port))
    # RedisContainer.__init__ 有 password 参数，保存于属性
    password = getattr(c, "password", None)
    return host, port, password


@pytest.fixture(scope="session")
def redis_connection_info(redis_container: RedisContainer) -> Dict[str, str]:
    """
    导出统一的连接信息，方便注入到被测应用（环境变量/配置）。
    """
    host, port, password = _get_host_port_password(redis_container)
    info = {
        "host": host,
        "port": str(port),
        "password": password or "",
        "url": (
            f"redis://:{password}@{host}:{port}/0" if password else f"redis://{host}:{port}/0"
        ),
    }
    return info


@pytest.fixture(scope="session")
def redis_session_client(redis_container: RedisContainer) -> redislib.Redis:
    """
    会话级客户端（decode_responses=True 返回 str，断言更直观）。
    如需每用例独立 DB/前缀，见后面的 function 级 fixture。
    """
    host, port, password = _get_host_port_password(redis_container)
    client = redislib.Redis(
        host=host, port=port, password=password, db=0, decode_responses=True
    )
    # 触发一次 PING 确认就绪
    client.ping()
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
    用例级客户端 + 清理策略：
    - 推荐：prefix 模式（仅删除以该前缀开的 keys，速度快、风险低）
    - 备选：flushdb 模式（每用例清库，最干净但影响并发）
    """
    clean_strategy: str = pytestconfig.getoption("--redis-clean-strategy")

    # —— 用例开始前：先做一次清理（幂等）
    if clean_strategy == "flushdb":
        redis_session_client.flushdb()
    else:
        # prefix: 先删掉历史残留（基本不会有，但保证幂等）
        keys = list(redis_session_client.scan_iter(match=f"{redis_test_prefix}*"))
        if keys:
            redis_session_client.delete(*keys)

    # 将「带前缀的便捷 set/get 包装」暴露给测试用例（可选）
    class PrefixedRedis:
        def __init__(self, client: redislib.Redis, prefix: str) -> None:
            self._c = client
            self._p = prefix

        @property
        def raw(self) -> redislib.Redis:
            return self._c  # 如需直接访问原生 client

        @property
        def prefix(self) -> str:
            return self._p

        # 常用操作都自动加前缀，避免键碰撞
        def set(self, key: str, value):
            return self._c.set(self._p + key, value)

        def get(self, key: str):
            return self._c.get(self._p + key)

        def hset(self, name: str, key: str, value):
            return self._c.hset(self._p + name, key, value)

        def hget(self, name: str, key: str):
            return self._c.hget(self._p + name, key)

        def incr(self, key: str):
            return self._c.incr(self._p + key)

        def delete_prefixed(self) -> int:
            keys = list(self._c.scan_iter(match=f"{self._p}*"))
            return self._c.delete(*keys) if keys else 0

    prefixed = PrefixedRedis(redis_session_client, redis_test_prefix)

    yield prefixed

    # —— 用例结束后：根据策略清理
    if clean_strategy == "flushdb":
        redis_session_client.flushdb()
    else:
        prefixed.delete_prefixed()


@pytest.fixture(scope="function")
def app_env_redis(monkeypatch: pytest.MonkeyPatch, redis_connection_info: Dict[str, str]) -> Dict[str, str]:
    """
    统一把 Redis 连接信息注入到被测应用（常见 FastAPI / Flask）。
    你的应用只要从这些变量读取即可：
    - REDIS_URL 或 (REDIS_HOST/REDIS_PORT/REDIS_PASSWORD)
    """
    info = redis_connection_info
    monkeypatch.setenv("REDIS_HOST", info["host"])
    monkeypatch.setenv("REDIS_PORT", info["port"])
    monkeypatch.setenv("REDIS_PASSWORD", info["password"])
    monkeypatch.setenv("REDIS_URL", info["url"])
    return {
        "REDIS_HOST": info["host"],
        "REDIS_PORT": info["port"],
        "REDIS_PASSWORD": info["password"],
        "REDIS_URL": info["url"],
    }


@pytest.fixture
async def client(postgres_async_client) -> AsyncGenerator[AsyncClient, None]:
    """提供使用 PostgreSQL 的异步客户端用于集成测试。"""
    # 直接使用已经配置好的 postgres_async_client
    yield postgres_async_client


# 全局邮件发送 mock（加速集成测试，避免真实外部调用与重试退避）
@pytest.fixture(autouse=True)
def _mock_email_tasks_send_with_retry():
    """在所有 integration 测试中，统一 mock 掉邮件重试发送。

    说明：
    - 许多认证相关用例会触发注册/验证/欢迎邮件。
      默认实现使用 tenacity 做指数退避重试，导致用例显著变慢。
    - 这里将 EmailTasks._send_email_with_retry 替换为快速成功的 AsyncMock，
      不侵入具体业务逻辑，也不改变响应结构，只避免真实外部调用与重试等待。
    """
    with patch(
        "src.common.services.email_tasks.EmailTasks._send_email_with_retry",
        new=AsyncMock(return_value=True),
    ):
        yield


# 全局 EmailService 实例方法 mock（覆盖直接调用 email_service 的场景）
@pytest.fixture(autouse=True)
def _mock_email_service_instance_methods():
    """统一将 email_service 的发送方法 mock 成快速成功，避免真实网络调用。

    适用于直接调用 UserService.register_user 等在无 background_tasks 情况下
    使用 email_service 同步发送邮件的路径。
    """
    with (
        patch(
            "src.common.services.email_service.email_service.send_verification_email", new=AsyncMock(return_value=True)
        ),
        patch("src.common.services.email_service.email_service.send_welcome_email", new=AsyncMock(return_value=True)),
        patch(
            "src.common.services.email_service.email_service.send_password_reset_email",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "src.common.services.email_service.email_service.send_password_changed_email",
            new=AsyncMock(return_value=True),
        ),
    ):
        yield


# 为集成测试提供一个内存版的异步 Redis 客户端，避免真实 Redis 依赖
class _AsyncMemoryRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}  # Store TTL values for keys

    async def ping(self) -> bool:
        return True

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.data[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns count of deleted keys."""
        deleted_count = 0
        for key in keys:
            if self.data.pop(key, None) is not None:
                deleted_count += 1
            self.ttls.pop(key, None)  # Remove TTL if key is deleted
        return deleted_count

    async def exists(self, key: str):
        return 1 if key in self.data else 0

    async def ttl(self, key: str) -> int:
        """Return TTL for key, or -1 if no TTL, or -2 if key doesn't exist."""
        if key not in self.data:
            return -2
        return self.ttls.get(key, -1)

    async def expire(self, key: str, seconds: int) -> int:
        """Set TTL for existing key. Returns 1 if successful, 0 if key doesn't exist."""
        if key in self.data:
            self.ttls[key] = seconds
            return 1
        return 0

    async def keys(self, pattern: str) -> list[str]:
        """Return keys matching pattern (simple * wildcard support)."""
        import fnmatch

        return [key for key in self.data if fnmatch.fnmatch(key, pattern)]

    async def close(self):
        self.data.clear()
        self.ttls.clear()


@pytest.fixture(autouse=True)
def _mock_redis_services(request: pytest.FixtureRequest):
    """同时 mock 同步与异步 Redis 客户端：
    - jwt_service 使用同步 redis 客户端（黑名单） -> 使用 tests 提供的 mock_redis
    - redis_service 使用异步 redis 客户端（会话缓存） -> 使用内存实现 _AsyncMemoryRedis
    
    对于需要真实 Redis 的集成测试，会跳过 mock 并使用 Redis 容器。
    """
    # Skip mocking for integration tests that need real Redis
    test_file_path = str(request.fspath)
    if ('integration' in test_file_path and 
        ('redis' in test_file_path.lower() or 'sse' in test_file_path.lower() or 'eventbridge' in test_file_path.lower())):
        # For tests that need real Redis, configure services to use container
        try:
            # Try to get Redis connection info if available
            redis_info = request.getfixturevalue("redis_connection_info")
            
            from src.common.services.redis_service import RedisService
            from src.common.services.redis_service import redis_service as async_redis_service
            
            # Configure async Redis service to use container
            import redis.asyncio as aioredis
            
            async def _container_connect(self) -> None:  # type: ignore[override]
                self._client = aioredis.Redis.from_url(redis_info["url"])
                
            async def _container_disconnect(self) -> None:  # type: ignore[override]
                if self._client:
                    await self._client.close()
                self._client = None
                
            original_connect = RedisService.connect
            original_disconnect = RedisService.disconnect
            
            RedisService.connect = _container_connect  # type: ignore[assignment]
            RedisService.disconnect = _container_disconnect  # type: ignore[assignment]
            
            try:
                yield
            finally:
                RedisService.connect = original_connect  # type: ignore[assignment] 
                RedisService.disconnect = original_disconnect  # type: ignore[assignment]
                
        except Exception:
            # If Redis container is not available, fall back to normal behavior
            yield
        return
    from src.common.services.jwt_service import jwt_service
    from src.common.services.redis_service import (
        RedisService,
    )
    from src.common.services.redis_service import (
        redis_service as async_redis_service,
    )

    from tests.unit.test_mocks import mock_redis


    # 覆盖 jwt_service 的同步 Redis 客户端
    jwt_service._redis_client = mock_redis  # type: ignore[attr-defined]

    # 打补丁：让 RedisService.connect/ disconnect 使用内存客户端，避免真实网络连接
    original_connect = RedisService.connect
    original_disconnect = RedisService.disconnect

    async def _fake_connect(self) -> None:  # type: ignore[override]
        self._client = _AsyncMemoryRedis()

    async def _fake_disconnect(self) -> None:  # type: ignore[override]
        self._client = None

    RedisService.connect = _fake_connect  # type: ignore[assignment]
    RedisService.disconnect = _fake_disconnect  # type: ignore[assignment]

    try:
        # 同时确保实例上的 client 已就绪
        async_redis_service._client = _AsyncMemoryRedis()  # type: ignore[attr-defined]
        yield
    finally:
        # 还原方法，防止影响其他环境
        RedisService.connect = original_connect  # type: ignore[assignment]
        RedisService.disconnect = original_disconnect  # type: ignore[assignment]
        async_redis_service._client = None  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _reset_sse_singletons():
    """重置 SSE 相关模块的单例，确保测试内的 patch 生效。

    例如：某些测试会 patch `RedisSSEService.init_pubsub_client` 抛错以验证错误返回，
    如果单例已初始化则不会再次调用 init，从而导致断言不匹配。这里将其重置为 None。
    """
    import src.api.routes.v1.events as events

    events._redis_sse_service = None  # type: ignore[attr-defined]
    events._sse_connection_manager = None  # type: ignore[attr-defined]
    yield


# 为 RedisSSEService 提供一个轻量 stub，避免健康检查时真实连接/超时
class _PubSubStub:
    async def subscribe(self, _channel: str) -> None:
        return None

    async def listen(self):  # type: ignore[override]
        if False:
            yield None
        return

    async def unsubscribe(self, _channel: str) -> None:
        return None

    async def close(self) -> None:
        return None


class _PubSubClientStub:
    async def ping(self) -> bool:
        # In test environment without real Redis, ping should fail to simulate unhealthy state
        raise Exception("Redis unavailable in test environment")

    def pubsub(self) -> _PubSubStub:
        return _PubSubStub()


@pytest.fixture(autouse=True)
def _stub_redis_sse_pubsub(request: pytest.FixtureRequest):
    """为 RedisSSEService 提供轻量 stub，避免健康检查时真实连接/超时。
    对于需要真实 Redis 的集成测试，会配置真实的 Redis 连接。
    """
    # Skip stubbing for integration tests that need real Redis
    test_file_path = str(request.fspath)
    if ('integration' in test_file_path and 
        ('redis' in test_file_path.lower() or 'sse' in test_file_path.lower() or 'eventbridge' in test_file_path.lower())):
        # For tests that need real Redis, configure SSE service to use container
        try:
            redis_info = request.getfixturevalue("redis_connection_info")
            
            from src.services.sse import RedisSSEService
            import redis.asyncio as aioredis
            
            original_init = RedisSSEService.init_pubsub_client
            
            async def _container_init(self) -> None:  # type: ignore[override]
                self._pubsub_client = aioredis.Redis.from_url(redis_info["url"])
                
            RedisSSEService.init_pubsub_client = _container_init  # type: ignore[assignment]
            
            try:
                yield
            finally:
                RedisSSEService.init_pubsub_client = original_init  # type: ignore[assignment]
                
        except Exception:
            # If Redis container is not available, fall back to stubbing
            from src.services.sse import RedisSSEService
            
            original_init = RedisSSEService.init_pubsub_client
            
            async def _fake_init(self) -> None:  # type: ignore[override]
                self._pubsub_client = _PubSubClientStub()
                
            RedisSSEService.init_pubsub_client = _fake_init  # type: ignore[assignment]
            try:
                yield
            finally:
                RedisSSEService.init_pubsub_client = original_init  # type: ignore[assignment]
        return
        
    from src.services.sse import RedisSSEService

    original_init = RedisSSEService.init_pubsub_client

    async def _fake_init(self) -> None:  # type: ignore[override]
        self._pubsub_client = _PubSubClientStub()

    RedisSSEService.init_pubsub_client = _fake_init  # type: ignore[assignment]
    try:
        yield
    finally:
        RedisSSEService.init_pubsub_client = original_init  # type: ignore[assignment]







