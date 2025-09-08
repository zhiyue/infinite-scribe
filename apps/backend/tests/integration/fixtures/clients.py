"""Test client fixtures for API testing."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import AsyncClient
from src.database import get_db


@asynccontextmanager
async def create_async_context_mock(return_value) -> AsyncGenerator[Any, None]:
    """创建异步上下文管理器 Mock 的工厂函数.

    使用 contextlib.asynccontextmanager 装饰器创建异步上下文管理器，
    比自定义类更简洁且符合 Python 惯用法。

    Args:
        return_value: 上下文管理器应该返回的值

    Yields:
        return_value: 传入的值

    Example:
        # Neo4j 测试
        mock_driver.session = lambda: create_async_context_mock(mock_session)

        # PostgreSQL 测试
        mock_pool.acquire = lambda: create_async_context_mock(mock_conn)
    """
    yield return_value


@pytest.fixture
async def test_user(pg_session):
    """Create a test user for integration tests."""
    import random
    import time

    from src.models.user import User

    timestamp = str(int(time.time() * 1000000))
    random_suffix = str(random.randint(1000, 9999))
    unique_id = f"{timestamp}_{random_suffix}"

    user = User(
        username=f"testuser_{unique_id}",
        email=f"testuser_{unique_id}@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QlTUpSxKO",  # "testpass"
        is_active=True,
        is_verified=True,
    )
    pg_session.add(user)
    await pg_session.commit()
    await pg_session.refresh(user)
    return user


@pytest.fixture
async def test_user_common(pg_session):
    """Create a test user for authentication tests."""
    from sqlalchemy import select
    from src.common.utils.datetime_utils import utc_now
    from src.models.user import User

    # Check if user already exists
    result = await pg_session.execute(select(User).where(User.id == 123))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        yield existing_user
    else:
        test_user = User(
            id=123,
            username="testuser",
            email="testuser@example.com",
            password_hash="$2b$12$test_hash",
            created_at=utc_now(),
            updated_at=utc_now(),
        )

        pg_session.add(test_user)
        await pg_session.commit()
        await pg_session.refresh(test_user)

        yield test_user


@pytest.fixture
async def async_client(pg_session, redis_session_client):
    """Create async test client with dependency overrides."""
    from unittest.mock import AsyncMock, patch

    from src.api.main import app
    from src.middleware.auth import get_current_user, require_auth
    from src.models.user import User
    from tests.unit.test_mocks import mock_email_service

    # Create a mock user for authentication
    mock_user = User(
        id=999,
        username="testuser",
        email="test@example.com",
        password_hash="mock_hash",
        is_active=True,
        is_verified=True,
    )

    # Apply comprehensive dependency overrides
    app.dependency_overrides[get_db] = lambda: pg_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_auth] = lambda: mock_user

    with (
        patch("src.common.services.jwt_service.jwt_service._redis_client", redis_session_client),
        patch("src.common.services.email_tasks.email_tasks._send_email_with_retry", new=AsyncMock(return_value=True)),
        patch("src.common.services.email_service.EmailService") as mock_email_cls,
    ):
        mock_email_cls.return_value = mock_email_service
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    # Cleanup
    app.dependency_overrides.clear()
    mock_email_service.clear()


@pytest.fixture
async def client_with_lifespan(pg_session):
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.api.main import app
    from src.db.graph import neo4j_service
    from src.db.sql import postgres_service
    from src.db.redis import redis_service
    from src.core.config import settings
    from tests.unit.test_mocks import mock_email_service

    app.dependency_overrides[get_db] = lambda: pg_session

    # 2) mock 三库连接 & 健康检查
    with (
        patch.object(postgres_service, "connect", AsyncMock(return_value=None)),
        patch.object(postgres_service, "check_connection", AsyncMock(return_value=True)),
        patch.object(postgres_service, "disconnect", AsyncMock(return_value=None)),
        patch.object(neo4j_service, "connect", AsyncMock(return_value=None)),
        patch.object(neo4j_service, "check_connection", AsyncMock(return_value=True)),
        patch.object(neo4j_service, "disconnect", AsyncMock(return_value=None)),
        patch.object(redis_service, "connect", AsyncMock(return_value=None)),
        patch.object(redis_service, "check_connection", AsyncMock(return_value=True)),
        patch.object(redis_service, "disconnect", AsyncMock(return_value=None)),
        # 3) SSEProvider stub
        patch("src.services.sse.provider.SSEProvider") as mock_sse_provider,
        # 4) Launcher 组件 stub
        patch("src.launcher.orchestrator.Orchestrator") as mock_orchestrator,
        patch("src.launcher.health.HealthMonitor") as mock_health_monitor,
        patch("src.common.services.email_service.EmailService") as mock_email_cls,
    ):
        sse_instance = MagicMock()
        sse_instance.get_redis_sse_service = AsyncMock()
        sse_instance.get_connection_manager = AsyncMock()
        sse_instance.close = AsyncMock()
        mock_sse_provider.return_value = sse_instance

        mock_orchestrator.return_value = MagicMock()
        mock_health_monitor.return_value = MagicMock()
        mock_email_cls.return_value = mock_email_service
        # 避免加载 admin 路由
        settings.launcher.admin_enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers():
    """Create authentication headers for test user."""
    from src.common.services.user.auth_service import jwt_service

    # Create token for mock user
    access_token, _, _ = jwt_service.create_access_token("999", {"email": "test@example.com", "username": "testuser"})
    return {"Authorization": f"Bearer {access_token}"}
