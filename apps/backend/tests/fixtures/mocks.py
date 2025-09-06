# tests/fixtures/mocks.py
"""Mock fixtures for testing - email services, external APIs, etc."""

from __future__ import annotations
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