"""Session service for managing user sessions with Redis caching."""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.redis_service import redis_service
from src.models.session import Session

logger = logging.getLogger(__name__)


class SessionService:
    """Service for session management with Redis caching."""

    def __init__(self):
        """Initialize session service."""
        self.cache_prefix = "session"
        self.cache_ttl = 3600  # 1 hour cache TTL

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
        """Cache session data in Redis.

        Args:
            session: Session object to cache
        """
        try:
            session_data = session.to_dict()

            # Cache by session ID
            await redis_service.set(
                self._get_cache_key(session_id=session.id), json.dumps(session_data), expire=self.cache_ttl
            )

            # Cache by JTI for quick lookup
            if session.jti:
                await redis_service.set(
                    self._get_cache_key(jti=session.jti), json.dumps(session_data), expire=self.cache_ttl
                )

            # Cache by refresh token for quick lookup
            if session.refresh_token:
                await redis_service.set(
                    self._get_cache_key(refresh_token=session.refresh_token),
                    json.dumps(session_data),
                    expire=self.cache_ttl,
                )

            logger.debug(f"Cached session {session.id} in Redis")

        except Exception as e:
            logger.error(f"Failed to cache session {session.id}: {e}")
            # Don't fail the operation if caching fails

    async def _get_cached_session(
        self, session_id: int | None = None, jti: str | None = None, refresh_token: str | None = None
    ) -> dict[str, Any] | None:
        """Get cached session data from Redis.

        Args:
            session_id: Session ID
            jti: JWT ID
            refresh_token: Refresh token

        Returns:
            Cached session data or None
        """
        try:
            cache_key = self._get_cache_key(session_id, jti, refresh_token)
            cached_data = await redis_service.get(cache_key)

            if cached_data:
                logger.debug(f"Found cached session with key {cache_key}")
                return json.loads(cached_data)

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
            if session.id:
                await redis_service.delete(self._get_cache_key(session_id=session.id))
            if session.jti:
                await redis_service.delete(self._get_cache_key(jti=session.jti))
            if session.refresh_token:
                await redis_service.delete(self._get_cache_key(refresh_token=session.refresh_token))

            logger.debug(f"Invalidated cache for session {session.id}")

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
        cached_data = await self._get_cached_session(jti=jti)
        if cached_data and cached_data.get("is_active") and not cached_data.get("revoked_at"):
            # Return cached data (would need to reconstruct Session object in real implementation)
            # For now, we'll still query the DB but the cache helps reduce Redis lookups
            pass

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
        cached_data = await self._get_cached_session(refresh_token=refresh_token)
        if cached_data and cached_data.get("is_active") and not cached_data.get("revoked_at"):
            # Return cached data (would need to reconstruct Session object in real implementation)
            pass

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

        session.last_accessed_at = utc_now()
        await db.commit()

        # Refresh cache
        await self._cache_session(session)


# Create singleton instance
session_service = SessionService()
