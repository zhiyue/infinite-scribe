# tests/fixtures/mocks.py
"""Mock fixtures for testing - email services, external APIs, etc."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest


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


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    # Set test environment
    os.environ["NODE_ENV"] = "test"

    # Set required API keys for testing (fake values)
    os.environ["SECRET_KEY"] = "test_secret_key_at_least_32_characters_long"
    os.environ["REDIS_URL"] = "redis://fake:6379/0"  # Will be mocked
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    # Some tests rely on default allowed_origins; ensure env override is absent
    os.environ.pop("ALLOWED_ORIGINS", None)

    # Email settings for testing
    os.environ["EMAIL_FROM"] = "test@example.com"
    os.environ["EMAIL_FROM_NAME"] = "Test App"
    os.environ["RESEND_API_KEY"] = "fake_resend_key"

    yield

    # Cleanup - remove test environment variables
    test_env_vars = [
        "NODE_ENV",
        "SECRET_KEY",
        "REDIS_URL",
        "FRONTEND_URL",
        "EMAIL_FROM",
        "EMAIL_FROM_NAME",
        "RESEND_API_KEY",
    ]
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]
