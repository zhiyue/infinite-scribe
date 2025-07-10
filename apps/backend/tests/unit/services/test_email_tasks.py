"""Unit tests for email tasks service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from src.common.services.email_tasks import EmailTasks
from tenacity import RetryError


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
    mock_email_service.send_verification_email.side_effect = RuntimeError("SMTP Error")

    # 测试重试机制
    with patch("src.common.services.email_tasks.logger") as mock_logger:
        # 由于 @retry 装饰器会在所有重试失败后抛出 RetryError
        with pytest.raises(RetryError):
            await email_tasks_service._send_email_with_retry(
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
    with patch("src.common.services.email_tasks.logger") as mock_logger:
        result = await email_tasks_service._send_email_with_retry(
            email_type="unknown_type",
            to_email="test@example.com",
        )

        assert result is False
        mock_logger.error.assert_called_with("未知的邮件类型: unknown_type")


@pytest.mark.asyncio
async def test_send_email_password_reset_success(
    email_tasks_service,
    mock_email_service,
):
    """Test successful password reset email sending."""
    result = await email_tasks_service._send_email_with_retry(
        email_type="password_reset",
        to_email="reset@example.com",
        user_name="Reset User",
        reset_url="https://example.com/reset?token=reset123",
    )

    assert result is True
    mock_email_service.send_password_reset_email.assert_called_once_with(
        "reset@example.com",
        "Reset User",
        "https://example.com/reset?token=reset123",
    )


@pytest.mark.asyncio
async def test_send_email_welcome_success(
    email_tasks_service,
    mock_email_service,
):
    """Test successful welcome email sending."""
    result = await email_tasks_service._send_email_with_retry(
        email_type="welcome",
        to_email="welcome@example.com",
        user_name="Welcome User",
    )

    assert result is True
    mock_email_service.send_welcome_email.assert_called_once_with(
        "welcome@example.com",
        "Welcome User",
    )


@pytest.mark.asyncio
async def test_email_service_returns_false(
    email_tasks_service,
    mock_email_service,
):
    """Test when email service returns False."""
    mock_email_service.send_verification_email.return_value = False

    with patch("src.common.services.email_tasks.logger") as mock_logger:
        result = await email_tasks_service._send_email_with_retry(
            email_type="verification",
            to_email="test@example.com",
            user_name="Test User",
            verification_url="https://example.com/verify?token=abc123",
        )

        assert result is False
        mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_multiple_retries_then_success(
    email_tasks_service,
    mock_email_service,
):
    """Test email sending succeeds after retries."""
    # 前两次失败，第三次成功
    mock_email_service.send_verification_email.side_effect = [
        Exception("First attempt failed"),
        Exception("Second attempt failed"),
        True,  # 第三次成功
    ]

    with patch("src.common.services.email_tasks.logger") as mock_logger:
        result = await email_tasks_service._send_email_with_retry(
            email_type="verification",
            to_email="test@example.com",
            user_name="Test User",
            verification_url="https://example.com/verify?token=abc123",
        )

        # 验证调用了3次
        assert mock_email_service.send_verification_email.call_count == 3
        # 最终返回 True
        assert result is True
        # 记录了前两次的错误
        assert mock_logger.error.call_count == 2


@pytest.mark.asyncio
async def test_logging_on_success(
    email_tasks_service,
    mock_email_service,
):
    """Test logging when email is sent successfully."""
    with patch("src.common.services.email_tasks.logger") as mock_logger:
        await email_tasks_service._send_email_with_retry(
            email_type="verification",
            to_email="test@example.com",
            user_name="Test User",
            verification_url="https://example.com/verify?token=abc123",
        )

        # 验证记录了成功日志
        mock_logger.info.assert_any_call("尝试发送 verification 邮件到 test@example.com")
        mock_logger.info.assert_any_call("成功发送 verification 邮件到 test@example.com")


@pytest.mark.asyncio
async def test_init_with_settings():
    """Test EmailTasks initialization with settings."""
    with patch("src.common.services.email_tasks.settings") as mock_settings:
        mock_settings.auth.email_max_retries = 5
        mock_settings.auth.email_retry_delay_seconds = 120

        email_tasks = EmailTasks()

        assert email_tasks.max_retries == 5
        assert email_tasks.retry_delay == 120


@pytest.mark.asyncio
async def test_init_with_default_settings():
    """Test EmailTasks initialization with default settings."""
    with patch("src.common.services.email_tasks.settings") as mock_settings:
        # 模拟没有这些设置
        delattr(mock_settings.auth, "email_max_retries")
        delattr(mock_settings.auth, "email_retry_delay_seconds")

        email_tasks = EmailTasks()

        assert email_tasks.max_retries == 3
        assert email_tasks.retry_delay == 60


@pytest.mark.asyncio
async def test_multiple_background_tasks(
    email_tasks_service,
    mock_background_tasks,
):
    """Test adding multiple email tasks to background."""
    # 发送多个邮件
    await email_tasks_service.send_verification_email_async(
        mock_background_tasks,
        "user1@example.com",
        "User 1",
        "https://example.com/verify?token=1",
    )

    await email_tasks_service.send_password_reset_email_async(
        mock_background_tasks,
        "user2@example.com",
        "User 2",
        "https://example.com/reset?token=2",
    )

    await email_tasks_service.send_welcome_email_async(
        mock_background_tasks,
        "user3@example.com",
        "User 3",
    )

    # 验证添加了3个后台任务
    assert mock_background_tasks.add_task.call_count == 3

    # 验证每个任务的参数
    calls = mock_background_tasks.add_task.call_args_list

    # 第一个任务 - 验证邮件
    assert calls[0][1]["email_type"] == "verification"
    assert calls[0][1]["to_email"] == "user1@example.com"

    # 第二个任务 - 密码重置
    assert calls[1][1]["email_type"] == "password_reset"
    assert calls[1][1]["to_email"] == "user2@example.com"

    # 第三个任务 - 欢迎邮件
    assert calls[2][1]["email_type"] == "welcome"
    assert calls[2][1]["to_email"] == "user3@example.com"
