"""测试 Session 缓存优化功能。"""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.common.services.user.session_service import SessionService
from src.common.utils.datetime_utils import utc_now
from src.models.session import Session
from src.schemas.session import SessionCacheSchema


class TestSessionCacheOptimization:
    """测试 Session 缓存优化。"""

    def setup_method(self):
        """设置测试环境。"""
        self.session_service = SessionService()
        self.mock_db = AsyncMock()

    @pytest.mark.asyncio
    @patch("src.common.services.user.session_service.redis_service", new_callable=AsyncMock)
    async def test_get_session_by_jti_cache_hit_with_reconstruction(self, mock_redis_service):
        """测试通过 JTI 获取 session 时缓存命中并重建对象。"""
        # 模拟缓存数据（使用 Pydantic 序列化）
        cached_schema = SessionCacheSchema(
            id=1,
            user_id=10,
            jti="test_jti",
            refresh_token="test_refresh",
            is_active=True,
            revoked_at=None,
            access_token_expires_at=utc_now() + timedelta(minutes=15),
            refresh_token_expires_at=utc_now() + timedelta(days=7),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        mock_redis_service.get.return_value = cached_schema.model_dump_json()

        # 获取 session
        result = await self.session_service.get_session_by_jti(self.mock_db, "test_jti")

        # 验证结果（从缓存重建的轻量级对象）
        assert result is not None
        assert result.id == 1
        assert result.jti == "test_jti"
        assert result.user_id == 10
        assert result.is_active is True

        # 验证 Redis 被查询
        mock_redis_service.get.assert_called_once_with("session:jti:test_jti")

        # 验证没有查询数据库（因为使用缓存数据）
        assert self.mock_db.execute.call_count == 0

    @pytest.mark.asyncio
    @patch("src.common.services.user.session_service.redis_service", new_callable=AsyncMock)
    async def test_get_session_by_jti_cache_miss(self, mock_redis_service):
        """测试缓存未命中时的行为。"""
        # 模拟缓存未命中
        mock_redis_service.get.return_value = None

        # 模拟数据库查询
        mock_session = Mock(spec=Session)
        mock_session.id = 1
        mock_session.user_id = 10
        mock_session.jti = "test_jti"
        mock_session.refresh_token = "test_refresh"
        mock_session.is_active = True
        mock_session.access_token_expires_at = utc_now() + timedelta(minutes=15)
        mock_session.refresh_token_expires_at = utc_now() + timedelta(days=7)
        mock_session.created_at = utc_now()
        mock_session.updated_at = utc_now()
        mock_session.revoked_at = None
        # 添加 Pydantic 验证需要的字段
        mock_session.user_agent = None
        mock_session.ip_address = None
        mock_session.device_type = None
        mock_session.device_name = None
        mock_session.last_accessed_at = None
        mock_session.revoke_reason = None

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
    @patch("src.common.services.user.session_service.redis_service", new_callable=AsyncMock)
    async def test_get_session_by_jti_inactive_session_in_cache(self, mock_redis_service):
        """测试缓存中的非活跃会话被正确处理。"""
        # 模拟缓存中的非活跃会话（使用 Pydantic）
        cached_schema = SessionCacheSchema(
            id=1,
            user_id=10,
            jti="test_jti",
            refresh_token="test_refresh",
            is_active=False,  # 非活跃
            revoked_at=utc_now() - timedelta(hours=1),
            access_token_expires_at=utc_now() + timedelta(minutes=15),
            refresh_token_expires_at=utc_now() + timedelta(days=7),
            created_at=utc_now() - timedelta(days=1),
            updated_at=utc_now() - timedelta(hours=1),
        )
        mock_redis_service.get.return_value = cached_schema.model_dump_json()

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
    @patch("src.common.services.user.session_service.redis_service", new_callable=AsyncMock)
    async def test_reconstruct_session_handles_errors(self, mock_redis_service):
        """测试 Pydantic 反序列化错误处理。"""
        # 模拟无效的缓存数据（缺少必需字段）
        invalid_json = '{"id": 1, "jti": "test_jti"}'  # 缺少必需的 user_id 等字段
        mock_redis_service.get.return_value = invalid_json

        # 模拟数据库查询（回退查询）
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_db.execute.return_value = mock_result

        # 获取 session（应该优雅地处理错误并回退到数据库查询）
        result = await self.session_service.get_session_by_jti(self.mock_db, "test_jti")

        # 验证返回 None
        assert result is None

        # 验证尝试了缓存查询
        mock_redis_service.get.assert_called_once_with("session:jti:test_jti")

        # 验证回退到数据库查询
        assert self.mock_db.execute.call_count == 1
