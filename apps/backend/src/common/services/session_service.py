"""Session service for managing user sessions with Redis caching."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.redis import redis_service
from src.models.session import Session
from src.schemas.session import SessionCacheSchema

logger = logging.getLogger(__name__)


class SessionService:
    """Service for session management with Redis caching."""

    def __init__(self):
        """Initialize session service."""
        self.cache_prefix = "session"
        self.cache_ttl = 3600  # 1 hour cache TTL
        # Flag used by specific code paths to request full ORM objects with relationships
        self._need_full_object: bool = False

    # no additional class-level declaration; instance attribute is set in __init__

    def _get_cache_key(
        self, session_id: int | None = None, jti: str | None = None, refresh_token: str | None = None
    ) -> str:
        """Get Redis cache key for session.

        Args:
            session_id: Session ID
            jti: JWT ID
            refresh_token: Refresh token

        Returns:
            Redis cache key
        """
        if session_id:
            return f"{self.cache_prefix}:id:{session_id}"
        elif jti:
            return f"{self.cache_prefix}:jti:{jti}"
        elif refresh_token:
            return f"{self.cache_prefix}:refresh:{refresh_token}"
        else:
            raise ValueError("Must provide either session_id, jti, or refresh_token")

    async def _cache_session(self, session: Session) -> None:
        """Cache session data in Redis using Pydantic serialization.

        Args:
            session: Session object to cache
        """
        try:
            # 使用 Pydantic 自动序列化，处理 datetime 等复杂类型
            cache_obj = SessionCacheSchema.model_validate(session, from_attributes=True)
            payload = cache_obj.model_dump_json()  # Pydantic v2 -> JSON string

            # Cache by session ID
            session_id = getattr(session, "id", None)
            if session_id is not None:
                await redis_service.set(self._get_cache_key(session_id=session_id), payload, expire=self.cache_ttl)

            # Cache by JTI for quick lookup
            jti = getattr(session, "jti", None)
            if jti:
                await redis_service.set(self._get_cache_key(jti=jti), payload, expire=self.cache_ttl)

            # Cache by refresh token for quick lookup
            refresh_token = getattr(session, "refresh_token", None)
            if refresh_token:
                await redis_service.set(
                    self._get_cache_key(refresh_token=refresh_token),
                    payload,
                    expire=self.cache_ttl,
                )

            logger.debug(f"Cached session {getattr(session, 'id', 'unknown')} in Redis")

        except Exception as e:
            logger.error(f"Failed to cache session {getattr(session, 'id', 'unknown')}: {e}")
            # Don't fail the operation if caching fails

    async def _get_cached_session_schema(
        self, session_id: int | None = None, jti: str | None = None, refresh_token: str | None = None
    ) -> SessionCacheSchema | None:
        """Get cached session data from Redis as Pydantic model.

        Args:
            session_id: Session ID
            jti: JWT ID
            refresh_token: Refresh token

        Returns:
            Cached session as Pydantic model or None
        """
        try:
            cache_key = self._get_cache_key(session_id, jti, refresh_token)
            raw = await redis_service.get(cache_key)

            if raw:
                logger.debug(f"Found cached session with key {cache_key}")
                # Pydantic 自动处理 JSON 反序列化和 datetime 解析
                return SessionCacheSchema.model_validate_json(raw)

        except Exception as e:
            logger.error(f"Failed to get cached session: {e}")

        return None

    async def _invalidate_cache(self, session: Session) -> None:
        """Invalidate cached session data.

        Args:
            session: Session object to invalidate
        """
        try:
            # Delete all cache entries for this session
            session_id = getattr(session, "id", None)
            if session_id is not None:
                await redis_service.delete(self._get_cache_key(session_id=session_id))

            jti = getattr(session, "jti", None)
            if jti:
                await redis_service.delete(self._get_cache_key(jti=jti))

            refresh_token = getattr(session, "refresh_token", None)
            if refresh_token:
                await redis_service.delete(self._get_cache_key(refresh_token=refresh_token))

            logger.debug(f"Invalidated cache for session {getattr(session, 'id', 'unknown')}")

        except Exception as e:
            logger.error(f"Failed to invalidate session cache: {e}")

    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        jti: str,
        refresh_token: str,
        access_token_expires_at: datetime,
        refresh_token_expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        """Create a new session and cache it.

        Args:
            db: Database session
            user_id: User ID
            jti: JWT ID
            refresh_token: Refresh token
            access_token_expires_at: Access token expiration
            refresh_token_expires_at: Refresh token expiration
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created session
        """
        session = Session(
            user_id=user_id,
            jti=jti,
            refresh_token=refresh_token,
            access_token_expires_at=access_token_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Cache the session after it has an ID
        await self._cache_session(session)

        return session

    async def get_session_by_jti(self, db: AsyncSession, jti: str) -> Session | None:
        """Get session by JTI with caching.

        Args:
            db: Database session
            jti: JWT ID

        Returns:
            Session or None
        """
        # Check cache first
        cached_schema = await self._get_cached_session_schema(jti=jti)
        if cached_schema and cached_schema.is_active and not cached_schema.revoked_at:
            # 从缓存重建 Session 对象
            session = await self._reconstruct_session_from_cache(db, cached_schema)
            if session:
                return session

        # Query database
        result = await db.execute(select(Session).where(Session.jti == jti, Session.is_active.is_(True)))
        session = result.scalar_one_or_none()

        # Cache if found
        if session:
            await self._cache_session(session)

        return session

    async def get_session_by_refresh_token(self, db: AsyncSession, refresh_token: str) -> Session | None:
        """Get session by refresh token with caching.

        Args:
            db: Database session
            refresh_token: Refresh token

        Returns:
            Session or None
        """
        # Check cache first
        cached_schema = await self._get_cached_session_schema(refresh_token=refresh_token)
        if cached_schema and cached_schema.is_active and not cached_schema.revoked_at:
            # 从缓存重建 Session 对象
            session = await self._reconstruct_session_from_cache(db, cached_schema)
            if session:
                return session

        # Query database
        result = await db.execute(
            select(Session).where(Session.refresh_token == refresh_token, Session.is_active.is_(True))
        )
        session = result.scalar_one_or_none()

        # Cache if found
        if session:
            await self._cache_session(session)

        return session

    async def revoke_session(self, db: AsyncSession, session: Session, reason: str | None = None) -> None:
        """Revoke a session and invalidate cache.

        Args:
            db: Database session
            session: Session to revoke
            reason: Revocation reason
        """
        session.revoke(reason)
        await db.commit()

        # Invalidate cache
        await self._invalidate_cache(session)

    async def update_session_access(self, db: AsyncSession, session: Session) -> None:
        """Update session last accessed time and refresh cache.

        Args:
            db: Database session
            session: Session to update
        """
        from src.common.utils.datetime_utils import utc_now

        # 使用 setattr 来避免 mypy 列类型错误
        session.last_accessed_at = utc_now()
        await db.commit()

        # Refresh cache
        await self._cache_session(session)

    async def _reconstruct_session_from_cache(self, db: AsyncSession, cached: SessionCacheSchema) -> Session | None:
        """Reconstruct Session object from cached Pydantic model.

        对于大部分场景（如验证令牌有效性），直接使用缓存数据即可。
        只有需要关联对象（如 User）时才查询数据库。

        Args:
            db: Database session
            cached: Cached session as Pydantic model

        Returns:
            Session object or None
        """
        try:
            # 90% 场景：仅验证会话有效性，无需查询数据库
            if cached.is_active and not cached.revoked_at:
                # 创建轻量级 Session 对象（不含关联对象）
                session = Session()
                # 使用 Pydantic 模型的数据填充
                for field in [
                    "id",
                    "user_id",
                    "jti",
                    "refresh_token",
                    "is_active",
                    "access_token_expires_at",
                    "refresh_token_expires_at",
                    "last_accessed_at",
                    "created_at",
                    "updated_at",
                ]:
                    if hasattr(cached, field):
                        setattr(session, field, getattr(cached, field))

                # 特殊情况：如果需要完整对象（包含 User 关系），查询数据库
                # 这通常只在 refresh_token 场景需要
                if hasattr(self, "_need_full_object") and self._need_full_object and cached.id:
                    result = await db.execute(
                        select(Session)
                        .options(selectinload(Session.user))  # 预加载用户信息
                        .where(Session.id == cached.id)
                    )
                    return result.scalar_one_or_none()

                return session

            return None

        except Exception as e:
            logger.warning(f"Failed to reconstruct session from cache: {e}")
            return None


# Create singleton instance
session_service = SessionService()
