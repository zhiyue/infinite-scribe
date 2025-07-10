"""测试 Session 缓存优化功能。"""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.orm import selectinload
from src.common.services.session_service import SessionService
from src.common.utils.datetime_utils import utc_now
from src.models.session import Session
from src.models.user import User


class TestSessionCacheOptimization:
    """测试 Session 缓存优化。"""

    def setup_method(self):
        """设置测试环境。"""
        self.session_service = SessionService()
        self.mock_db = AsyncMock()

    @pytest.mark.asyncio
    @patch("src.common.services.session_service.redis_service", new_callable=AsyncMock)
    async def test_get_session_by_jti_cache_hit_with_reconstruction(self, mock_redis_service):
        """测试通过 JTI 获取 session 时缓存命中并重建对象。"""
        # 模拟缓存数据
        cached_data = {
            "id": 1,
            "user_id": 10,
            "jti": "test_jti",
            "refresh_token": "test_refresh",
            "is_active": True,
            "revoked_at": None,
        }
        mock_redis_service.get.return_value = json.dumps(cached_data)

        # 模拟数据库查询（用于重建完整对象）
        mock_session = Mock(spec=Session)
        mock_session.id = 1
        mock_session.user_id = 10
        mock_session.jti = "test_jti"
        mock_session.is_active = True
        mock_session.user = Mock(spec=User, id=10, email="test@example.com")

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        self.mock_db.execute.return_value = mock_result

        # 获取 session
        result = await self.session_service.get_session_by_jti(self.mock_db, "test_jti")

        # 验证结果
        assert result is not None
        assert result.id == 1
        assert result.jti == "test_jti"

        # 验证 Redis 被查询
        mock_redis_service.get.assert_called_once_with("session:jti:test_jti")

        # 验证数据库查询被调用（用于重建完整对象）
        assert self.mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    @patch("src.common.services.session_service.redis_service", new_callable=AsyncMock)
    async def test_get_session_by_jti_cache_miss(self, mock_redis_service):
        """测试缓存未命中时的行为。"""
        # 模拟缓存未命中
        mock_redis_service.get.return_value = None

        # 模拟数据库查询
        mock_session = Mock(spec=Session)
        mock_session.id = 1
        mock_session.jti = "test_jti"
        mock_session.is_active = True
        mock_session.to_dict = Mock(return_value={"id": 1, "jti": "test_jti", "is_active": True})

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_session
        self.mock_db.execute.return_value = mock_result

        # 获取 session
        result = await self.session_service.get_session_by_jti(self.mock_db, "test_jti")

        # 验证结果
        assert result is not None
        assert result.jti == "test_jti"

        # 验证先检查了缓存
        mock_redis_service.get.assert_called_once_with("session:jti:test_jti")

        # 验证数据库被查询（因为缓存未命中）
        assert self.mock_db.execute.call_count == 1

        # 验证结果被缓存
        assert mock_redis_service.set.call_count == 3  # id, jti, refresh_token

    @pytest.mark.asyncio
    @patch("src.common.services.session_service.redis_service", new_callable=AsyncMock)
    async def test_get_session_by_jti_inactive_session_in_cache(self, mock_redis_service):
        """测试缓存中的非活跃会话被正确处理。"""
        # 模拟缓存中的非活跃会话
        cached_data = {
            "id": 1,
            "jti": "test_jti",
            "is_active": False,  # 非活跃
            "revoked_at": "2024-01-10T10:00:00Z",
        }
        mock_redis_service.get.return_value = json.dumps(cached_data)

        # 模拟数据库查询（应该查询活跃会话）
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # 没有活跃会话
        self.mock_db.execute.return_value = mock_result

        # 获取 session
        result = await self.session_service.get_session_by_jti(self.mock_db, "test_jti")

        # 验证返回 None
        assert result is None

        # 验证数据库被查询（因为缓存中的会话非活跃）
        assert self.mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    @patch("src.common.services.session_service.redis_service", new_callable=AsyncMock)
    @patch("src.common.services.session_service.logger")
    async def test_reconstruct_session_handles_errors(self, mock_logger, mock_redis_service):
        """测试重建会话时的错误处理。"""
        # 模拟缓存数据
        cached_data = {
            "id": 1,
            "jti": "test_jti",
            "is_active": True,
        }
        mock_redis_service.get.return_value = json.dumps(cached_data)

        # 第一次查询（重建时）抛出异常，第二次查询（回退查询）返回 None
        self.mock_db.execute.side_effect = [
            Exception("Database error"),  # 重建时的异常
            Mock(scalar_one_or_none=Mock(return_value=None))  # 回退查询
        ]

        # 获取 session
        result = await self.session_service.get_session_by_jti(self.mock_db, "test_jti")

        # 验证返回 None
        assert result is None

        # 验证错误被记录
        mock_logger.warning.assert_called_with("Failed to reconstruct session from cache: Database error")
        
        # 验证数据库被查询了两次（重建失败后的回退查询）
        assert self.mock_db.execute.call_count == 2