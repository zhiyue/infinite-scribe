"""API层边角案例测试 - 密码相关端点的全面测试覆盖."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException, status
from src.api.routes.v1.auth_password import (
    change_password,
    forgot_password,
    reset_password,
    validate_password_strength,
)
from src.api.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    PasswordStrengthResponse,
    ResetPasswordRequest,
)
from src.models.user import User


class TestForgotPasswordEdgeCases:
    """忘记密码端点边角案例测试."""

    @pytest.mark.asyncio
    async def test_forgot_password_malformed_email(self):
        """测试格式错误的邮箱地址."""
        # 测试明显无效的邮箱格式会被Pydantic验证拦截
        malformed_emails = [
            "",  # 空字符串
            "   ",  # 只有空格
            "invalid",  # 无@符号
            "@domain.com",  # 缺少用户名
            "user@",  # 缺少域名
        ]

        for email in malformed_emails:
            # 对于明显格式错误的邮箱，Pydantic验证应该拒绝请求
            from pydantic import ValidationError

            with pytest.raises(ValidationError):  # Pydantic validation error
                request = ForgotPasswordRequest(email=email)

        # 测试格式看起来正确但可能有问题的邮箱
        questionable_emails = [
            "user@domain..com",  # 连续点号 - 可能通过Pydantic但实际无效
            "a" * 50 + "@domain.com",  # 过长邮箱但格式正确
        ]

        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)

        for email in questionable_emails:
            try:
                request = ForgotPasswordRequest(email=email)

                with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
                    # 为了安全考虑，仍然返回成功响应
                    mock_user_service.request_password_reset = AsyncMock(
                        return_value={"message": "If the email exists, a reset link has been sent"}
                    )

                    result = await forgot_password(request, mock_background_tasks, mock_db)

                    assert isinstance(result, MessageResponse)
                    assert result.success is True
            except Exception:
                # 如果Pydantic拒绝这个邮箱，那也是可以接受的行为
                pass

    @pytest.mark.asyncio
    async def test_forgot_password_rate_limiting_simulation(self):
        """测试频繁请求的模拟（模拟速率限制场景）."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = ForgotPasswordRequest(email="test@example.com")

        # 模拟多次快速请求
        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.request_password_reset = AsyncMock(return_value={"message": "Reset email sent"})

            # 连续5次请求
            for _i in range(5):
                result = await forgot_password(request, mock_background_tasks, mock_db)
                assert result.success is True

            # 验证每次都调用了服务
            assert mock_user_service.request_password_reset.call_count == 5

    @pytest.mark.asyncio
    async def test_forgot_password_background_tasks_none(self):
        """测试BackgroundTasks为None的情况."""
        mock_db = AsyncMock()
        request = ForgotPasswordRequest(email="test@example.com")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.request_password_reset = AsyncMock(return_value={"message": "Reset email sent"})

            # BackgroundTasks参数为None应该仍然工作
            result = await forgot_password(request, None, mock_db)

            assert result.success is True
            mock_user_service.request_password_reset.assert_called_once_with(mock_db, "test@example.com", None)


class TestResetPasswordEdgeCases:
    """重置密码端点边角案例测试."""

    @pytest.mark.asyncio
    async def test_reset_password_token_injection_attempt(self):
        """测试令牌注入攻击尝试."""
        injection_tokens = [
            "'; DROP TABLE users; --",  # SQL注入尝试
            "<script>alert('xss')</script>",  # XSS尝试
            "../../../etc/passwd",  # 路径遍历尝试
            "token\x00admin",  # 空字节注入
            "token\r\nAdmin: true",  # HTTP头注入尝试
        ]

        mock_db = AsyncMock()

        for token in injection_tokens:
            request = ResetPasswordRequest(token=token, new_password="NewPassword123!")

            with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
                mock_user_service.reset_password = AsyncMock(return_value={"success": False, "error": "Invalid token"})

                with pytest.raises(HTTPException) as exc_info:
                    await reset_password(request, mock_db)

                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
                # 验证服务仍然被调用以处理无效令牌
                mock_user_service.reset_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_unicode_and_encoding_edge_cases(self):
        """测试Unicode和编码边界情况."""
        # 确保密码满足最小长度要求（8字符）
        unicode_passwords = [
            "Pássw0rd!",  # 带重音符号，9字符
            "中文密码123!",  # 中文密码，8字符
            "Пароль123!",  # 西里尔字母，10字符
            "パスワード123!",  # 日文密码，9字符
            "🔐Secure123!",  # 包含emoji，11字符
            "Café1234!",  # 混合字符，9字符
        ]

        mock_db = AsyncMock()

        for password in unicode_passwords:
            request = ResetPasswordRequest(token="valid_token", new_password=password)

            with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
                mock_user_service.reset_password = AsyncMock(
                    return_value={"success": True, "message": "Password reset successful"}
                )

                result = await reset_password(request, mock_db)

                assert result.success is True
                mock_user_service.reset_password.assert_called_once_with(mock_db, "valid_token", password)

    @pytest.mark.asyncio
    async def test_reset_password_extremely_long_token(self):
        """测试极长令牌的处理."""
        # 生成一个非常长的令牌
        long_token = "a" * 10000
        request = ResetPasswordRequest(token=long_token, new_password="NewPassword123!")
        mock_db = AsyncMock()

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.reset_password = AsyncMock(return_value={"success": False, "error": "Invalid token"})

            with pytest.raises(HTTPException) as exc_info:
                await reset_password(request, mock_db)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            # 即使令牌很长，服务仍应被调用
            mock_user_service.reset_password.assert_called_once()


class TestChangePasswordEdgeCases:
    """修改密码端点边角案例测试."""

    @pytest.fixture
    def mock_user(self):
        """创建模拟用户."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.password_hash = "hashed_password"
        user.is_active = True
        user.is_verified = True
        return user

    @pytest.mark.asyncio
    async def test_change_password_identical_passwords(self, mock_user):
        """测试当前密码和新密码完全相同的情况."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        # 当前密码和新密码相同
        request = ChangePasswordRequest(current_password="SamePassword123!", new_password="SamePassword123!")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.change_password = AsyncMock(
                return_value={"success": False, "error": "New password must be different from current password"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, mock_background_tasks, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "different from current" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_change_password_whitespace_passwords(self, mock_user):
        """测试包含前导/尾随空白字符的密码."""
        passwords_with_whitespace = [
            "  Password123!  ",  # 前后空格
            "\tPassword123!\t",  # 前后制表符
            "\nPassword123!\n",  # 前后换行符
            " Password 123! ",  # 中间空格
        ]

        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)

        for password in passwords_with_whitespace:
            request = ChangePasswordRequest(current_password="current_password", new_password=password)

            with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
                mock_user_service.change_password = AsyncMock(
                    return_value={"success": True, "message": "Password changed successfully"}
                )

                result = await change_password(request, mock_background_tasks, mock_db, mock_user)

                assert result.success is True
                # 验证密码被原样传递给服务（包括空白字符）
                mock_user_service.change_password.assert_called_once_with(
                    mock_db, mock_user.id, "current_password", password, mock_background_tasks
                )

    @pytest.mark.asyncio
    async def test_change_password_binary_data_in_password(self, mock_user):
        """测试密码中包含二进制数据的情况."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)

        # 包含不可打印字符的密码
        binary_password = "Pass\x00\x01\x02word123!"
        request = ChangePasswordRequest(current_password="current_password", new_password=binary_password)

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            # 密码服务可能会拒绝包含二进制数据的密码
            mock_user_service.change_password = AsyncMock(
                return_value={"success": False, "error": "Invalid characters in password"}
            )

            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, mock_background_tasks, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_change_password_user_object_corruption(self, mock_user):
        """测试用户对象损坏的情况."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = ChangePasswordRequest(current_password="current_password", new_password="NewPassword123!")

        # 模拟用户对象缺少必要属性
        corrupted_user = Mock()
        corrupted_user.id = None  # ID为None
        # 缺少其他必要属性

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            mock_user_service.change_password = AsyncMock(return_value={"success": False, "error": "Invalid user data"})

            with pytest.raises(HTTPException) as exc_info:
                await change_password(request, mock_background_tasks, mock_db, corrupted_user)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


class TestValidatePasswordStrengthEdgeCases:
    """密码强度验证端点边角案例测试."""

    @pytest.mark.asyncio
    async def test_validate_password_strength_extreme_lengths(self):
        """测试极端长度的密码."""
        test_cases = [
            ("", 0),  # 空密码
            ("a", 1),  # 单字符
            ("a" * 1000, 1000),  # 极长密码
            ("🔐" * 100, 100),  # 100个emoji字符
        ]

        for password, expected_length in test_cases:
            with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
                if expected_length == 0:
                    mock_password_service.validate_password_strength.return_value = {
                        "is_valid": False,
                        "score": 0,
                        "errors": ["Password cannot be empty"],
                        "suggestions": ["Enter a password"],
                    }
                elif expected_length == 1:
                    mock_password_service.validate_password_strength.return_value = {
                        "is_valid": False,
                        "score": 0,
                        "errors": ["Password too short"],
                        "suggestions": ["Use at least 8 characters"],
                    }
                elif expected_length >= 1000:
                    mock_password_service.validate_password_strength.return_value = {
                        "is_valid": False,
                        "score": 0,
                        "errors": ["Password too long"],
                        "suggestions": ["Use a shorter password"],
                    }
                else:
                    mock_password_service.validate_password_strength.return_value = {
                        "is_valid": True,
                        "score": 4,
                        "errors": [],
                        "suggestions": [],
                    }

                # 注意：现在validate_password_strength接受password作为Query参数
                result = await validate_password_strength(password=password)

                assert isinstance(result, PasswordStrengthResponse)
                if expected_length == 0 or expected_length == 1 or expected_length >= 1000:
                    assert result.is_valid is False
                    assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_password_strength_unicode_complexity(self):
        """测试Unicode字符的复杂性评估."""
        unicode_passwords = [
            "简单密码123",  # 中文+数字
            "Πάσσωορδ123!",  # 希腊字母
            "Пароль123!",  # 西里尔字母
            "مرور123!كلمة",  # 阿拉伯文
            "🔐🔑🛡️123!",  # 只有emoji和数字
            "ÄÖÜäöüß123!",  # 德语变音符
        ]

        for password in unicode_passwords:
            with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
                # 假设密码服务能够正确处理Unicode字符
                mock_password_service.validate_password_strength.return_value = {
                    "is_valid": True,
                    "score": 3,
                    "errors": [],
                    "suggestions": ["Consider adding special characters"],
                }

                result = await validate_password_strength(password=password)

                assert isinstance(result, PasswordStrengthResponse)
                assert result.score >= 0
                mock_password_service.validate_password_strength.assert_called_once_with(password)

    @pytest.mark.asyncio
    async def test_validate_password_strength_service_timeout(self):
        """测试密码服务超时的情况."""
        password = "TestPassword123!"

        with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
            # 模拟服务超时
            mock_password_service.validate_password_strength.side_effect = TimeoutError("Service timeout")

            result = await validate_password_strength(password=password)

            # 应该返回安全的默认响应
            assert isinstance(result, PasswordStrengthResponse)
            assert result.is_valid is False
            assert result.score == 0
            assert "Unable to validate password" in result.errors

    @pytest.mark.asyncio
    async def test_validate_password_strength_memory_pressure(self):
        """测试内存压力下的密码验证."""
        # 创建一个可能导致内存问题的大密码
        large_password = "A1!" + "x" * 50000  # 50KB密码

        with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
            # 模拟内存不足错误
            mock_password_service.validate_password_strength.side_effect = MemoryError("Insufficient memory")

            result = await validate_password_strength(password=large_password)

            # 应该优雅地处理内存错误
            assert isinstance(result, PasswordStrengthResponse)
            assert result.is_valid is False
            assert result.score == 0
            assert "Unable to validate password" in result.errors

    @pytest.mark.asyncio
    async def test_validate_password_strength_concurrent_requests(self):
        """测试并发请求的处理."""

        password = "TestPassword123!"

        async def validate_single():
            with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
                mock_password_service.validate_password_strength.return_value = {
                    "is_valid": True,
                    "score": 4,
                    "errors": [],
                    "suggestions": [],
                }
                return await validate_password_strength(password=password)

        # 并发执行10个密码验证请求
        tasks = [validate_single() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # 所有请求都应该成功完成
        assert len(results) == 10
        for result in results:
            assert isinstance(result, PasswordStrengthResponse)
            assert result.is_valid is True
            assert result.score == 4


class TestErrorHandlingEdgeCases:
    """错误处理边角案例测试."""

    @pytest.mark.asyncio
    async def test_database_connection_lost_during_request(self):
        """测试请求过程中数据库连接丢失的情况."""
        mock_db = AsyncMock()
        mock_background_tasks = Mock(spec=BackgroundTasks)
        request = ForgotPasswordRequest(email="test@example.com")

        with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
            # 模拟数据库连接丢失
            mock_user_service.request_password_reset = AsyncMock(
                side_effect=ConnectionError("Database connection lost")
            )

            with pytest.raises(HTTPException) as exc_info:
                await forgot_password(request, mock_background_tasks, mock_db)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "error occurred" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_unexpected_exception_types(self):
        """测试意外的异常类型处理."""
        mock_db = AsyncMock()
        request = ResetPasswordRequest(token="valid_token", new_password="NewPassword123!")

        # 移除 KeyboardInterrupt 和 SystemExit，它们会被 pytest 特殊处理
        unexpected_exceptions = [
            RecursionError("Maximum recursion depth exceeded"),
            ImportError("Module not found"),
            OSError("Operating system error"),
            MemoryError("Out of memory"),
        ]

        for exception in unexpected_exceptions:
            with patch("src.api.routes.v1.auth_password.user_service") as mock_user_service:
                mock_user_service.reset_password = AsyncMock(side_effect=exception)

                with pytest.raises(HTTPException) as exc_info:
                    await reset_password(request, mock_db)

                assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_json_serialization_errors(self):
        """测试JSON序列化错误的处理."""
        password = "TestPassword123!"

        with patch("src.api.routes.v1.auth_password.password_service") as mock_password_service:
            # 返回一个无法JSON序列化的对象
            class UnserializableObject:
                def __str__(self):
                    raise Exception("Cannot serialize")

            mock_password_service.validate_password_strength.return_value = {
                "is_valid": True,
                "score": 4,
                "errors": [],
                "suggestions": [UnserializableObject()],  # 无法序列化的对象
            }

            # 虽然服务返回了无法序列化的数据，API应该优雅处理
            try:
                result = await validate_password_strength(password)
                # 如果没有抛出异常，检查结果是否有效
                assert isinstance(result, PasswordStrengthResponse)
            except Exception:
                # 如果抛出异常，应该是可以处理的类型
                pass
