"""测试用户服务改进功能的单元测试。"""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.common.services.session_service import SessionService
from src.common.services.user_service import UserService
from src.common.utils.datetime_utils import utc_now
from src.core.config import settings
from src.models.session import Session
from src.models.user import User


class TestUserServiceLoginImprovements:
    """测试用户服务登录改进功能。"""

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
        self.mock_user.to_dict = Mock(return_value={"id": 1, "email": "test@example.com", "username": "testuser"})

    @pytest.mark.asyncio
    async def test_login_with_remaining_attempts_on_failure(self):
        """测试登录失败时返回剩余尝试次数。"""
        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 第一次失败尝试
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "WrongPassword", "127.0.0.1", "TestAgent"
        )

        assert not result["success"]
        assert "remaining" in result["error"]
        assert result["remaining_attempts"] == 4
        assert self.mock_user.failed_login_attempts == 1

        # 第二次失败尝试
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "WrongPassword", "127.0.0.1", "TestAgent"
        )

        assert not result["success"]
        assert result["remaining_attempts"] == 3
        assert self.mock_user.failed_login_attempts == 2

    @pytest.mark.asyncio
    async def test_account_lockout_after_max_attempts(self):
        """测试达到最大尝试次数后账户锁定。"""
        # 设置用户已经有4次失败尝试
        self.mock_user.failed_login_attempts = 4

        # 设置数据库查询返回用户
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = self.mock_user
        self.mock_db.execute.return_value = mock_result

        # 第5次失败尝试应该触发锁定
        result = await self.user_service.login(
            self.mock_db, "test@example.com", "WrongPassword", "127.0.0.1", "TestAgent"
        )

        assert not result["success"]
        assert "locked" in result["error"].lower()
        assert "locked_until" in result
        assert self.mock_user.failed_login_attempts == 5
        assert self.mock_user.locked_until is not None

        # 验证锁定时间是30分钟后
        expected_unlock_time = utc_now() + timedelta(minutes=settings.auth.account_lockout_duration_minutes)
        actual_unlock_time = self.mock_user.locked_until
        # 允许1秒的时间差
        assert abs((expected_unlock_time - actual_unlock_time).total_seconds()) < 1


class TestSessionServiceCaching:
    """测试 Session 服务缓存功能。"""

    def setup_method(self):
        """设置测试环境。"""
        self.session_service = SessionService()
        self.mock_db = AsyncMock()
        self.mock_redis = AsyncMock()

    @pytest.mark.asyncio
    @patch("src.common.services.session_service.redis_service", new_callable=AsyncMock)
    async def test_create_session_with_caching(self, mock_redis_service):
        """测试创建 session 时缓存到 Redis。"""
        # 模拟 Redis 服务
        mock_redis_service.set = AsyncMock()

        # 模拟数据库的 refresh 方法来设置 session ID 和必要字段
        async def mock_refresh(obj):
            obj.id = 1
            obj.created_at = utc_now()
            obj.updated_at = utc_now()
            # 确保所有必填字段有正确的值
            if not hasattr(obj, "last_accessed_at") or obj.last_accessed_at is None:
                obj.last_accessed_at = utc_now()
            if not hasattr(obj, "is_active") or obj.is_active is None:
                obj.is_active = True
            if not hasattr(obj, "revoked_at"):
                obj.revoked_at = None

        self.mock_db.refresh = mock_refresh

        # 创建 session
        await self.session_service.create_session(
            db=self.mock_db,
            user_id=1,
            jti="test_jti_123",
            refresh_token="test_refresh_token",
            access_token_expires_at=utc_now() + timedelta(minutes=15),
            refresh_token_expires_at=utc_now() + timedelta(days=7),
            ip_address="127.0.0.1",
            user_agent="TestAgent",
        )

        # 验证 session 被添加到数据库
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called()

        # 验证 Redis 缓存被调用（3次：by id, by jti, by refresh_token）
        assert mock_redis_service.set.call_count == 3

        # 验证缓存键的格式
        calls = mock_redis_service.set.call_args_list
        cache_keys = [call[0][0] for call in calls]
        assert any("session:id:" in key for key in cache_keys)
        assert any("session:jti:test_jti_123" in key for key in cache_keys)
        assert any("session:refresh:test_refresh_token" in key for key in cache_keys)

    @pytest.mark.asyncio
    @patch("src.common.services.session_service.redis_service", new_callable=AsyncMock)
    async def test_get_session_by_jti_with_cache_hit(self, mock_redis_service):
        """测试通过 JTI 获取 session 时命中缓存。"""
        # 模拟缓存命中
        cached_data = {"id": 1, "jti": "test_jti", "is_active": True, "revoked_at": None, "user_id": 1}
        mock_redis_service.get.return_value = json.dumps(cached_data)

        # 模拟数据库查询
        mock_session = Mock(spec=Session)
        mock_session.id = 1
        mock_session.jti = "test_jti"
        mock_session.is_active = True

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        self.mock_db.execute.return_value = mock_result

        # 获取 session
        result = await self.session_service.get_session_by_jti(self.mock_db, "test_jti")

        # 验证返回了 session
        assert result is not None

        # 验证先检查了缓存
        mock_redis_service.get.assert_called_once_with("session:jti:test_jti")

    @pytest.mark.asyncio
    @patch("src.common.services.session_service.redis_service", new_callable=AsyncMock)
    async def test_revoke_session_invalidates_cache(self, mock_redis_service):
        """测试撤销 session 时使缓存失效。"""
        # 创建模拟 session
        mock_session = Mock(spec=Session)
        mock_session.id = 1
        mock_session.jti = "test_jti"
        mock_session.refresh_token = "test_refresh"
        mock_session.revoke = Mock()

        # 模拟 Redis delete
        mock_redis_service.delete = AsyncMock()

        # 撤销 session
        await self.session_service.revoke_session(self.mock_db, mock_session, "Test reason")

        # 验证 session 被撤销
        mock_session.revoke.assert_called_once_with("Test reason")
        self.mock_db.commit.assert_called_once()

        # 验证缓存被清除（3次：by id, by jti, by refresh_token）
        assert mock_redis_service.delete.call_count == 3

        # 验证删除的缓存键
        calls = mock_redis_service.delete.call_args_list
        cache_keys = [call[0][0] for call in calls]
        assert any("session:id:1" in key for key in cache_keys)
        assert any("session:jti:test_jti" in key for key in cache_keys)
        assert any("session:refresh:test_refresh" in key for key in cache_keys)
