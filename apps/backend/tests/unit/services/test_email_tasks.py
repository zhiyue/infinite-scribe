"""Unit tests for email tasks service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import BackgroundTasks

from src.common.services.email_tasks import EmailTasks


@pytest.fixture
def email_tasks_service():
    """Create email tasks service instance."""
    return EmailTasks()


@pytest.fixture
def mock_background_tasks():
    """Create mock background tasks."""
    return MagicMock(spec=BackgroundTasks)


@pytest.fixture
def mock_email_service():
    """Create mock email service."""
    with patch("src.common.services.email_tasks.email_service") as mock:
        mock.send_verification_email = AsyncMock(return_value=True)
        mock.send_password_reset_email = AsyncMock(return_value=True)
        mock.send_welcome_email = AsyncMock(return_value=True)
        yield mock


@pytest.mark.asyncio
async def test_send_verification_email_async(
    email_tasks_service,
    mock_background_tasks,
):
    """Test async verification email sending."""
    # 调用异步发送验证邮件
    await email_tasks_service.send_verification_email_async(
        mock_background_tasks,
        "test@example.com",
        "Test User",
        "https://example.com/verify?token=abc123",
    )

    # 验证后台任务被添加
    mock_background_tasks.add_task.assert_called_once()
    
    # 获取添加的任务参数
    call_args = mock_background_tasks.add_task.call_args
    assert call_args[0][0] == email_tasks_service._send_email_with_retry
    assert call_args[1]["email_type"] == "verification"
    assert call_args[1]["to_email"] == "test@example.com"
    assert call_args[1]["user_name"] == "Test User"
    assert call_args[1]["verification_url"] == "https://example.com/verify?token=abc123"


@pytest.mark.asyncio
async def test_send_password_reset_email_async(
    email_tasks_service,
    mock_background_tasks,
):
    """Test async password reset email sending."""
    # 调用异步发送密码重置邮件
    await email_tasks_service.send_password_reset_email_async(
        mock_background_tasks,
        "test@example.com",
        "Test User",
        "https://example.com/reset?token=xyz789",
    )

    # 验证后台任务被添加
    mock_background_tasks.add_task.assert_called_once()
    
    # 获取添加的任务参数
    call_args = mock_background_tasks.add_task.call_args
    assert call_args[0][0] == email_tasks_service._send_email_with_retry
    assert call_args[1]["email_type"] == "password_reset"
    assert call_args[1]["to_email"] == "test@example.com"
    assert call_args[1]["user_name"] == "Test User"
    assert call_args[1]["reset_url"] == "https://example.com/reset?token=xyz789"


@pytest.mark.asyncio
async def test_send_welcome_email_async(
    email_tasks_service,
    mock_background_tasks,
):
    """Test async welcome email sending."""
    # 调用异步发送欢迎邮件
    await email_tasks_service.send_welcome_email_async(
        mock_background_tasks,
        "test@example.com",
        "Test User",
    )

    # 验证后台任务被添加
    mock_background_tasks.add_task.assert_called_once()
    
    # 获取添加的任务参数
    call_args = mock_background_tasks.add_task.call_args
    assert call_args[0][0] == email_tasks_service._send_email_with_retry
    assert call_args[1]["email_type"] == "welcome"
    assert call_args[1]["to_email"] == "test@example.com"
    assert call_args[1]["user_name"] == "Test User"


@pytest.mark.asyncio
async def test_send_email_with_retry_success(
    email_tasks_service,
    mock_email_service,
):
    """Test successful email sending with retry mechanism."""
    # 测试成功发送验证邮件
    result = await email_tasks_service._send_email_with_retry(
        email_type="verification",
        to_email="test@example.com",
        user_name="Test User",
        verification_url="https://example.com/verify?token=abc123",
    )

    assert result is True
    mock_email_service.send_verification_email.assert_called_once_with(
        "test@example.com",
        "Test User",
        "https://example.com/verify?token=abc123",
    )


@pytest.mark.asyncio
async def test_send_email_with_retry_failure(
    email_tasks_service,
    mock_email_service,
):
    """Test email sending with retry on failure."""
    # 模拟邮件发送失败
    mock_email_service.send_verification_email.side_effect = Exception("SMTP Error")

    # 测试重试机制
    with patch("src.common.services.email_tasks.logger") as mock_logger:
        # 由于 @retry 装饰器的 reraise=False，异常不会被重新抛出
        result = await email_tasks_service._send_email_with_retry(
            email_type="verification",
            to_email="test@example.com",
            user_name="Test User",
            verification_url="https://example.com/verify?token=abc123",
        )

        # 验证重试了3次
        assert mock_email_service.send_verification_email.call_count == 3
        # 验证记录了错误日志
        assert mock_logger.error.called


@pytest.mark.asyncio
async def test_unknown_email_type(
    email_tasks_service,
):
    """Test handling of unknown email type."""
    result = await email_tasks_service._send_email_with_retry(
        email_type="unknown_type",
        to_email="test@example.com",
    )

    assert result is False