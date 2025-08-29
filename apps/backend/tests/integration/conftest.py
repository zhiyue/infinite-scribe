"""Integration test specific fixtures."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 使用 PostgreSQL 的集成测试专用 fixtures


@pytest.fixture
async def db_session(postgres_test_session) -> AsyncSession:
    """提供 PostgreSQL 数据库会话用于集成测试，并在每个测试后清理数据。"""
    # 在测试开始前清理数据库
    await postgres_test_session.execute(
        text("TRUNCATE TABLE users, sessions, email_verifications, domain_events CASCADE")
    )
    await postgres_test_session.commit()

    # 提供会话给测试
    yield postgres_test_session

    # 测试后再次清理（可选，但有助于确保隔离）
    await postgres_test_session.execute(
        text("TRUNCATE TABLE users, sessions, email_verifications, domain_events CASCADE")
    )
    await postgres_test_session.commit()


@pytest.fixture
async def client(postgres_async_client) -> AsyncClient:
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

    async def ping(self) -> bool:
        return True

    async def get(self, key: str):
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.data[key] = value
        return True

    async def delete(self, key: str):
        return 1 if self.data.pop(key, None) is not None else 0

    async def exists(self, key: str):
        return 1 if key in self.data else 0

    async def close(self):
        self.data.clear()


@pytest.fixture(autouse=True)
def _mock_redis_services():
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
        return True

    def pubsub(self) -> _PubSubStub:
        return _PubSubStub()


@pytest.fixture(autouse=True)
def _stub_redis_sse_pubsub():
    from src.common.services.redis_sse_service import RedisSSEService

    original_init = RedisSSEService.init_pubsub_client

    async def _fake_init(self) -> None:  # type: ignore[override]
        self._pubsub_client = _PubSubClientStub()

    RedisSSEService.init_pubsub_client = _fake_init  # type: ignore[assignment]
    try:
        yield
    finally:
        RedisSSEService.init_pubsub_client = original_init  # type: ignore[assignment]
