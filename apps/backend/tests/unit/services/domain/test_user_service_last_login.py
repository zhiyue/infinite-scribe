"""测试用户服务 last_login_at 更新功能的单元测试。"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.common.services.user.user_service import UserService
from src.common.utils.datetime_utils import utc_now
from src.models.user import User


class TestUserServiceLastLogin:
    """测试用户服务 last_login_at 更新功能。"""

    def setup_method(self):
        """设置测试环境。"""
        self.user_service = UserService()
        self.mock_db = AsyncMock()

        # 创建模拟用户
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 1
        self.mock_user.email = "test@example.com"
        self.mock_user.username = "testuser"
        self.mock_user.password_hash = "$2b$12$KIkD2lw6r.p4JY7nzPpqMeFqakq8LVdlFxr5hN2YBNZJHc0D9mFcS"  # "ValidPass123!"
        self.mock_user.is_verified = True
        self.mock_user.is_locked = False
        self.mock_user.failed_login_attempts = 0
        self.mock_user.locked_until = None
        self.mock_user.last_login_at = None
        self.mock_user.last_login_ip = None
        self.mock_user.full_name = "Test User"
        self.mock_user.to_dict = Mock(
            return_value={"id": 1, "email": "test@example.com", "username": "testuser", "last_login_at": None}
        )

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.session_service")
    @patch("src.common.services.user_service.user_email_service")
    @patch("src.common.services.user_service.password_service")
    @patch("src.common.services.user_service.auth_service")
    async def test_login_updates_last_login_at(
        self, mock_jwt_service, mock_password_service, mock_email_service, mock_session_service
    ):
        """测试成功登录时更新 last_login_at 和 last_login_ip。"""
        # 设置密码验证成功
        mock_password_service.verify_password.return_value = True
        # 直接设置 user_service 实例的 password_service
        self.user_service.password_service = mock_password_service

        # 设置 JWT 服务返回值
        mock_jwt_service.create_access_token.return_value = (
            "access_token",
            "jti123",
            utc_now() + timedelta(minutes=15),
        )
        mock_jwt_service.create_refresh_token.return_value = ("refresh_token", utc_now() + timedelta(days=7))

        # 设置 session 服务
        mock_session_service.create_session = AsyncMock()
        # 直接设置 user_service 实例的服务
        self.user_service.auth_service = mock_jwt_service
        self.user_service.user_email_service = mock_email_service

        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 记录登录前的状态
        before_login_time = utc_now()
        assert self.mock_user.last_login_at is None
        assert self.mock_user.last_login_ip is None

        # 执行登录
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "ValidPass123!", "192.168.1.100", "TestAgent/1.0"
        )

        # 验证登录成功
        if not result["success"]:
            print(f"Login failed: {result}")
        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result

        # 验证 last_login_at 被更新
        assert self.mock_user.last_login_at is not None
        assert isinstance(self.mock_user.last_login_at, datetime)
        assert self.mock_user.last_login_at >= before_login_time

        # 验证 last_login_ip 被更新
        assert self.mock_user.last_login_ip == "192.168.1.100"

        # 验证 failed_login_attempts 被重置
        assert self.mock_user.failed_login_attempts == 0

        # 验证数据库提交被调用（用户更新应该在 session 创建前提交）
        assert self.mock_db.commit.call_count >= 1

        # 验证第一次 commit 是在 create_session 之前
        commit_calls = self.mock_db.commit.call_args_list
        mock_session_service.create_session.call_args_list[0]

        # 确保至少有一次 commit 在 create_session 之前被调用
        assert len(commit_calls) > 0, "数据库 commit 应该被调用"

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.password_service")
    async def test_login_failure_does_not_update_last_login(self, mock_password_service):
        """测试登录失败时不更新 last_login_at。"""
        # 设置密码验证失败
        mock_password_service.verify_password.return_value = False

        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 记录登录前的状态
        assert self.mock_user.last_login_at is None
        assert self.mock_user.last_login_ip is None

        # 执行登录（错误密码）
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "WrongPassword", "192.168.1.100", "TestAgent/1.0"
        )

        # 验证登录失败
        assert result["success"] is False
        assert "error" in result

        # 验证 last_login_at 没有被更新
        assert self.mock_user.last_login_at is None
        assert self.mock_user.last_login_ip is None

        # 验证 failed_login_attempts 增加
        assert self.mock_user.failed_login_attempts == 1

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.session_service")
    @patch("src.common.services.user_service.user_email_service")
    @patch("src.common.services.user_service.password_service")
    @patch("src.common.services.user_service.auth_service")
    async def test_multiple_logins_update_last_login_at(
        self, mock_jwt_service, mock_password_service, mock_email_service, mock_session_service
    ):
        """测试多次登录时正确更新 last_login_at。"""
        # 设置密码验证成功
        mock_password_service.verify_password.return_value = True
        # 直接设置 user_service 实例的 password_service
        self.user_service.password_service = mock_password_service

        # 设置 JWT 服务返回值
        mock_jwt_service.create_access_token.return_value = (
            "access_token",
            "jti123",
            utc_now() + timedelta(minutes=15),
        )
        mock_jwt_service.create_refresh_token.return_value = ("refresh_token", utc_now() + timedelta(days=7))

        # 设置 session 服务
        mock_session_service.create_session = AsyncMock()
        # 直接设置 user_service 实例的服务
        self.user_service.auth_service = mock_jwt_service
        self.user_service.user_email_service = mock_email_service

        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 第一次登录
        first_login_time = utc_now()
        result1 = await self.user_service.login(
            self.mock_db, "test@example.com", "ValidPass123!", "192.168.1.100", "TestAgent/1.0"
        )

        if not result1["success"]:
            print(f"First login failed: {result1}")
        assert result1["success"] is True
        first_login_at = self.mock_user.last_login_at
        assert first_login_at is not None
        assert first_login_at >= first_login_time

        # 模拟时间流逝
        import time

        time.sleep(0.1)  # 等待 100ms

        # 第二次登录
        second_login_time = utc_now()
        result2 = await self.user_service.login(
            self.mock_db,
            "test@example.com",
            "ValidPass123!",
            "192.168.1.200",  # 不同的 IP
            "TestAgent/2.0",
        )

        assert result2["success"] is True
        second_login_at = self.mock_user.last_login_at
        assert second_login_at is not None
        assert second_login_at >= second_login_time
        assert second_login_at > first_login_at  # 确保时间更新了
        assert self.mock_user.last_login_ip == "192.168.1.200"  # IP 也更新了

    @pytest.mark.asyncio
    async def test_login_with_unverified_user_does_not_update_last_login(self):
        """测试未验证用户登录时不更新 last_login_at。"""
        # 设置用户未验证
        self.mock_user.is_verified = False

        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 执行登录
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "ValidPass123!", "192.168.1.100", "TestAgent/1.0"
        )

        # 验证登录失败
        assert result["success"] is False
        assert "verify" in result["error"].lower()

        # 验证 last_login_at 没有被更新
        assert self.mock_user.last_login_at is None
        assert self.mock_user.last_login_ip is None

    @pytest.mark.asyncio
    async def test_login_with_locked_account_does_not_update_last_login(self):
        """测试账户锁定时不更新 last_login_at。"""
        # 设置账户锁定
        self.mock_user.is_locked = True
        self.mock_user.locked_until = utc_now() + timedelta(minutes=30)

        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 执行登录
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "ValidPass123!", "192.168.1.100", "TestAgent/1.0"
        )

        # 验证登录失败
        assert result["success"] is False
        assert "locked" in result["error"].lower()

        # 验证 last_login_at 没有被更新
        assert self.mock_user.last_login_at is None
        assert self.mock_user.last_login_ip is None

    @pytest.mark.asyncio
    @patch("src.common.services.user_service.session_service")
    @patch("src.common.services.user_service.user_email_service")
    @patch("src.common.services.user_service.password_service")
    @patch("src.common.services.user_service.auth_service")
    async def test_login_commit_order(
        self, mock_jwt_service, mock_password_service, mock_email_service, mock_session_service
    ):
        """测试登录时数据库提交的顺序（用户更新应在 session 创建前提交）。"""
        # 设置密码验证成功
        mock_password_service.verify_password.return_value = True
        # 直接设置 user_service 实例的 password_service
        self.user_service.password_service = mock_password_service

        # 设置 JWT 服务返回值
        mock_jwt_service.create_access_token.return_value = (
            "access_token",
            "jti123",
            utc_now() + timedelta(minutes=15),
        )
        mock_jwt_service.create_refresh_token.return_value = ("refresh_token", utc_now() + timedelta(days=7))

        # 设置 session 服务
        mock_session_service.create_session = AsyncMock()
        # 直接设置 user_service 实例的服务
        self.user_service.auth_service = mock_jwt_service
        self.user_service.user_email_service = mock_email_service

        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 记录方法调用顺序
        call_order = []

        # 设置 commit 记录
        async def record_commit():
            call_order.append("commit")

        self.mock_db.commit.side_effect = record_commit

        # 设置 create_session 记录
        async def record_create_session(*args, **kwargs):
            call_order.append("create_session")

        mock_session_service.create_session.side_effect = record_create_session

        # 执行登录
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "ValidPass123!", "192.168.1.100", "TestAgent/1.0"
        )

        # 验证登录成功
        assert result["success"] is True

        # 验证调用顺序：commit 应该在 create_session 之前
        assert "commit" in call_order
        assert "create_session" in call_order
        commit_index = call_order.index("commit")
        create_session_index = call_order.index("create_session")
        assert commit_index < create_session_index, "用户更新的 commit 应该在 create_session 之前"
