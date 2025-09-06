"""Integration test specific fixtures."""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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


def pytest_configure(config: pytest.Config) -> None:
    """注册自定义 markers，避免 UnknownMark 警告。"""
    config.addinivalue_line("markers", "redis_container: use Testcontainers Redis for this test")


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
    """
    from src.common.services.jwt_service import jwt_service
    from src.common.services.redis_service import (
        RedisService,
    )
    from src.common.services.redis_service import (
        redis_service as async_redis_service,
    )

    from tests.unit.test_mocks import mock_redis

    # 如果当前用例标记为使用 Testcontainers Redis，则跳过内存 mock
    if request.node.get_closest_marker("redis_container"):
        yield
        return

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
    if request.node.get_closest_marker("redis_container"):
        yield
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


# 提供可选的 Testcontainers Redis 容器
@pytest.fixture(scope="session")
def redis_container() -> Generator[tuple[str, int, str], None, None]:
    try:
        from testcontainers.redis import RedisContainer  # type: ignore
    except Exception as e:  # pragma: no cover
        pytest.skip(f"testcontainers not available for Redis: {e}")

    with RedisContainer("redis:7-alpine") as container:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(6379))
        password = ""
        yield host, port, password


@pytest.fixture
async def use_redis_container(redis_container) -> AsyncGenerator[None, None]:
    """让当前测试使用 Testcontainers Redis。

    使用：
      - 标记测试：@pytest.mark.redis_container
      - 添加参数：use_redis_container（无需使用返回值）
    """
    host, port, password = redis_container
    import redis.asyncio as aioredis
    from redis import Redis
    from src.common.services.jwt_service import jwt_service
    from src.common.services.redis_service import redis_service as async_redis_service
    from src.core.config import settings

    # 更新 settings
    settings.database.redis_host = host
    settings.database.redis_port = port
    settings.database.redis_password = password

    # 重新初始化同步 Redis（JWT 黑名单）
    jwt_service._redis_pool = None  # type: ignore[attr-defined]
    jwt_service._redis_client = Redis(host=host, port=port, decode_responses=True)  # type: ignore[call-arg]

    # 重新初始化异步 Redis（会话缓存）
    async_redis_service._client = aioredis.from_url(  # type: ignore[attr-defined]
        settings.database.redis_url,
        decode_responses=True,
        health_check_interval=30,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    yield

    # 清理异步客户端
    try:
        if async_redis_service._client:  # type: ignore[attr-defined]
            await async_redis_service._client.close()  # type: ignore[union-attr]
    except Exception:
        pass
