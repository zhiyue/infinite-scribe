"""Integration test specific fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pytest

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


@pytest.fixture
async def sse_provider_override():
    """提供一个简单的 SSEProvider 覆盖示例。

    用法：
        async def test_xxx(sse_provider_override):
            # 在该测试用例作用域内，所有对默认 provider 的解析都会使用这个实例
            provider = sse_provider_override
            # 可按需预热底层服务，或做行为替换/打桩
            await provider.get_redis_sse_service()
            await provider.get_connection_manager()
            ...

    说明：
    - 该 fixture 使用 `override_provider` 上下文管理器覆盖进程级默认 provider，
      退出后会自动关闭资源并恢复。
    - FastAPI 应用若在 lifespan 中初始化了 app-scoped provider，
      路由依赖会优先使用 app.state 的 provider；此 fixture 更适用于非 Web 上下文
     （或在单测中手动禁用/绕过 lifespan 初始化的场景）。
    """
    from src.services.sse.provider import SSEProvider, override_provider

    provider = SSEProvider()
    async with override_provider(provider) as p:
        yield p

