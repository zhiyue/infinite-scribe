"""测试并发登录和会话管理策略。"""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.common.services.user.session_service import SessionService
from src.common.services.user.user_service import UserService
from src.common.utils.datetime_utils import utc_now
from src.models.session import Session
from src.models.user import User


class TestConcurrentLogin:
    """测试并发登录处理。"""

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
        self.mock_user.failed_login_attempts = 4  # 已经有4次失败
        self.mock_user.locked_until = None
        self.mock_user.to_dict = Mock(return_value={"id": 1, "email": "test@example.com", "username": "testuser"})

    @pytest.mark.asyncio
    async def test_concurrent_failed_login_attempts(self):
        """测试并发失败登录尝试的处理（使用行锁）。"""
        # 模拟 select().where().with_for_update() 查询
        mock_query = Mock()
        mock_query.where.return_value = mock_query
        mock_query.with_for_update.return_value = mock_query

        # 模拟数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 模拟 select 函数
        with patch("src.common.services.user.user_service.select", return_value=mock_query):
            # 第5次失败尝试应该触发锁定
            result = await self.user_service.login(
                self.mock_db, "test@example.com", "WrongPassword", "127.0.0.1", "TestAgent"
            )

        # 验证使用了行锁
        mock_query.with_for_update.assert_called_once()

        # 验证账户被锁定
        assert not result["success"]
        assert "locked" in result["error"].lower()
        assert self.mock_user.failed_login_attempts == 5
        assert self.mock_user.locked_until is not None


class TestSessionManagementStrategies:
    """测试不同的会话管理策略。"""

    def setup_method(self):
        """设置测试环境。"""
        self.user_service = UserService()
        self.session_service = SessionService()
        self.mock_db = AsyncMock()

    @pytest.mark.asyncio
    @patch("src.common.services.user.user_service.settings.auth.session_strategy", "single_device")
    async def test_single_device_strategy(self):
        """测试单设备登录策略。"""
        user_id = 1

        # 模拟现有的活跃会话
        existing_sessions = [
            Mock(spec=Session, jti="old_jti_1", access_token_expires_at=utc_now() + timedelta(minutes=10)),
            Mock(spec=Session, jti="old_jti_2", access_token_expires_at=utc_now() + timedelta(minutes=10)),
        ]

        # 模拟数据库查询
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = existing_sessions
        self.mock_db.execute.return_value = mock_result

        # 模拟 session_service
        with patch("src.common.services.user.user_service.session_service") as mock_session_service:
            mock_session_service.revoke_session = AsyncMock()

            # 执行会话策略处理
            await self.user_service._handle_session_strategy(self.mock_db, user_id)

        # 验证所有旧会话都被撤销
        assert mock_session_service.revoke_session.call_count == 2

        # 验证撤销原因
        calls = mock_session_service.revoke_session.call_args_list
        for call in calls:
            assert "single device policy" in call[0][2]

    @pytest.mark.asyncio
    @patch("src.common.services.user.user_service.settings.auth.session_strategy", "max_sessions")
    @patch("src.common.services.user.user_service.settings.auth.max_sessions_per_user", 3)
    async def test_max_sessions_strategy(self):
        """测试最大会话数限制策略。"""
        user_id = 1

        # 模拟5个现有的活跃会话（超过限制）
        existing_sessions = []
        for i in range(5):
            session = Mock(spec=Session)
            session.jti = f"jti_{i}"
            session.access_token_expires_at = utc_now() + timedelta(minutes=10)
            session.created_at = utc_now() - timedelta(hours=5 - i)  # 越早创建的索引越小
            existing_sessions.append(session)

        # 模拟数据库查询
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = existing_sessions
        self.mock_db.execute.return_value = mock_result

        # 模拟 session_service
        with patch("src.common.services.user.user_service.session_service") as mock_session_service:
            mock_session_service.revoke_session = AsyncMock()

            # 执行会话策略处理
            await self.user_service._handle_session_strategy(self.mock_db, user_id)

        # 验证踢掉了3个最旧的会话（5个现有 + 1个新的 - 3个限制 = 3个要踢掉）
        assert mock_session_service.revoke_session.call_count == 3

        # 验证踢掉的是最旧的会话
        revoked_sessions = [call[0][1] for call in mock_session_service.revoke_session.call_args_list]
        revoked_jtis = [s.jti for s in revoked_sessions]
        assert set(revoked_jtis) == {"jti_0", "jti_1", "jti_2"}

    @pytest.mark.asyncio
    @patch("src.common.services.user.user_service.settings.auth.session_strategy", "multi_device")
    async def test_multi_device_strategy(self):
        """测试多设备登录策略（默认）。"""
        user_id = 1

        # 模拟 session_service
        with patch("src.common.services.user.user_service.session_service") as mock_session_service:
            mock_session_service.revoke_session = AsyncMock()

            # 执行会话策略处理
            await self.user_service._handle_session_strategy(self.mock_db, user_id)

        # 验证没有撤销任何会话
        mock_session_service.revoke_session.assert_not_called()

        # 验证也没有查询数据库（因为 multi_device 策略不需要处理）
        self.mock_db.execute.assert_not_called()


class TestLoginWithSessionManagement:
    """测试完整的登录流程与会话管理。"""

    def setup_method(self):
        """设置测试环境。"""
        self.user_service = UserService()
        self.mock_db = AsyncMock()

        # 创建模拟用户
        self.mock_user = Mock(spec=User)
        self.mock_user.id = 1
        self.mock_user.email = "test@example.com"
        self.mock_user.username = "testuser"
        self.mock_user.password_hash = "$2b$12$ValidHashForTesting"
        self.mock_user.is_verified = True
        self.mock_user.is_locked = False
        self.mock_user.failed_login_attempts = 0
        self.mock_user.locked_until = None
        self.mock_user.to_dict = Mock(return_value={"id": 1, "email": "test@example.com", "username": "testuser"})

    @pytest.mark.asyncio
    @patch("src.common.services.user.user_service.settings.auth.session_strategy", "max_sessions")
    @patch("src.common.services.user.user_service.settings.auth.max_sessions_per_user", 2)
    @patch("src.common.services.user.user_service.session_service")
    async def test_login_with_max_sessions_policy(self, mock_session_service):
        """测试带有最大会话数限制的登录。"""
        # 模拟密码验证成功
        with patch.object(self.user_service.password_service, "verify_password", return_value=True):
            # 模拟数据库查询
            mock_query = Mock()
            mock_query.where.return_value = mock_query
            mock_query.with_for_update.return_value = mock_query

            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = self.mock_user
            self.mock_db.execute.side_effect = [
                mock_result,  # 查询用户
                Mock(
                    scalars=Mock(
                        return_value=Mock(
                            all=Mock(
                                return_value=[
                                    Mock(
                                        spec=Session,
                                        jti="old_jti",
                                        access_token_expires_at=utc_now() + timedelta(minutes=10),
                                        created_at=utc_now() - timedelta(hours=1),
                                    ),
                                    Mock(
                                        spec=Session,
                                        jti="old_jti2",
                                        access_token_expires_at=utc_now() + timedelta(minutes=10),
                                        created_at=utc_now() - timedelta(minutes=30),
                                    ),
                                ]
                            )
                        )
                    )
                ),  # 查询现有会话
            ]

            # 模拟 JWT 创建
            with (
                patch.object(
                    self.user_service.auth_service,
                    "create_access_token",
                    return_value=("access_token", "new_jti", utc_now() + timedelta(minutes=15)),
                ),
                patch.object(
                    self.user_service.auth_service,
                    "create_refresh_token",
                    return_value=("refresh_token", utc_now() + timedelta(days=7)),
                ),
                patch("src.common.services.user.user_service.select", return_value=mock_query),
            ):
                # 模拟 session 创建
                mock_session_service.create_session = AsyncMock(return_value=Mock(spec=Session))
                mock_session_service.revoke_session = AsyncMock()

                # 执行登录
                result = await self.user_service.login(
                    self.mock_db, "test@example.com", "ValidPassword", "127.0.0.1", "TestAgent"
                )

        # 验证登录成功
        assert result["success"]
        assert result["access_token"] == "access_token"

        # 验证撤销了1个最旧的会话（2个现有 + 1个新的 - 2个限制 = 1个要撤销）
        assert mock_session_service.revoke_session.call_count == 1
