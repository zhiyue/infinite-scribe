"""JWT service for token management."""

import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from redis import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError

from src.common.utils.datetime_utils import from_timestamp_utc, utc_now
from src.core.config import settings


class JWTService:
    """Service for JWT token management."""

    def __init__(self):
        """Initialize JWT service."""
        self.secret_key = settings.auth.jwt_secret_key
        self.algorithm = settings.auth.jwt_algorithm
        self.access_token_expire_minutes = settings.auth.access_token_expire_minutes
        self.refresh_token_expire_days = settings.auth.refresh_token_expire_days

        # Redis connection pool for better connection management
        self._redis_pool: ConnectionPool | None = None
        self._redis_client: Redis | None = None

    @property
    def redis_client(self) -> Redis:
        """Get Redis client for blacklist management."""
        if self._redis_pool is None:
            self._redis_pool = ConnectionPool(
                host=settings.database.redis_host,
                port=settings.database.redis_port,
                password=settings.database.redis_password,
                decode_responses=True,
                max_connections=10,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

        if self._redis_client is None:
            self._redis_client = Redis(connection_pool=self._redis_pool)

        return self._redis_client

    def create_access_token(
        self, subject: str, additional_claims: dict[str, Any] | None = None
    ) -> tuple[str, str, datetime]:
        """Create an access token.

        Args:
            subject: Subject of the token (usually user ID)
            additional_claims: Additional claims to include in the token

        Returns:
            Tuple of (token, jti, expires_at)
        """
        jti = secrets.token_urlsafe(16)
        expires_at = utc_now() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode = {
            "sub": str(subject),
            "exp": expires_at,
            "iat": utc_now(),
            "jti": jti,
            "token_type": "access",
        }

        if additional_claims:
            to_encode.update(additional_claims)

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt, jti, expires_at

    def create_refresh_token(
        self, subject: str, additional_claims: dict[str, Any] | None = None
    ) -> tuple[str, datetime]:
        """Create a refresh token.

        Args:
            subject: Subject of the token (usually user ID)
            additional_claims: Additional claims to include in the token

        Returns:
            Tuple of (token, expires_at)
        """
        expires_at = utc_now() + timedelta(days=self.refresh_token_expire_days)

        to_encode = {
            "sub": str(subject),
            "exp": expires_at,
            "iat": utc_now(),
            "jti": secrets.token_urlsafe(16),  # Add JTI for uniqueness
            "token_type": "refresh",
        }

        if additional_claims:
            to_encode.update(additional_claims)

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt, expires_at

    def verify_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify
            expected_type: Expected token type (access or refresh)

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            if payload.get("token_type") != expected_type:
                raise JWTError(f"Invalid token type. Expected {expected_type}")

            # Check if token is blacklisted (only for access tokens)
            if expected_type == "access" and self.is_token_blacklisted(payload.get("jti")):
                raise JWTError("Token has been revoked")

            return payload

        except JWTError:
            raise

    def blacklist_token(self, jti: str, expires_at: datetime) -> None:
        """Add a token to the blacklist.

        Args:
            jti: JWT ID to blacklist
            expires_at: Token expiration time
        """
        if not jti:
            return

        # Calculate TTL for Redis
        ttl = int((expires_at - utc_now()).total_seconds())
        if ttl > 0:
            try:
                self.redis_client.setex(f"blacklist:{jti}", ttl, "1")
            except (ConnectionError, TimeoutError) as e:
                # Log error but don't fail - let the request continue
                # In production, you might want to use proper logging
                print(f"Redis error while blacklisting token: {e}")

    def is_token_blacklisted(self, jti: str | None) -> bool:
        """Check if a token is blacklisted.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        if not jti:
            return False

        try:
            return bool(self.redis_client.get(f"blacklist:{jti}"))
        except (ConnectionError, TimeoutError) as e:
            # If Redis is unavailable, assume token is not blacklisted
            # This allows the service to continue functioning
            print(f"Redis error while checking blacklist: {e}")
            return False

    def extract_token_from_header(self, authorization: str) -> str | None:
        """Extract token from Authorization header.

        Args:
            authorization: Authorization header value

        Returns:
            Token string or None if invalid format
        """
        if not authorization:
            return None

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    async def refresh_access_token(
        self, db: Any, refresh_token: str, old_access_token: str | None = None
    ) -> dict[str, Any]:
        """Refresh access token using refresh token.

        Args:
            db: Database session
            refresh_token: Valid refresh token
            old_access_token: Optional old access token to blacklist

        Returns:
            Dictionary with success status and new tokens or error message
        """
        try:
            # Import here to avoid circular dependency
            from src.common.services.session_service import session_service

            # Verify refresh token
            payload = self.verify_token(refresh_token, "refresh")
            user_id = payload.get("sub")

            if not user_id:
                return {"success": False, "error": "Invalid refresh token: missing subject"}

            # Find session by refresh token
            session = await session_service.get_session_by_refresh_token(db, refresh_token)
            if not session or not session.is_valid:
                return {"success": False, "error": "Invalid or expired session"}

            # Create new access token
            new_access_token, new_jti, access_expires_at = self.create_access_token(
                user_id,
                {
                    "email": session.user.email if session.user else None,
                    "username": session.user.username if session.user else None,
                },
            )

            # Create new refresh token (token rotation for security)
            new_refresh_token, refresh_expires_at = self.create_refresh_token(user_id)

            # Blacklist old access token if provided
            if old_access_token:
                try:
                    old_payload = self.verify_token(old_access_token, "access")
                    old_jti = old_payload.get("jti")
                    if old_jti:
                        # Calculate expiration from old token
                        old_exp = from_timestamp_utc(old_payload.get("exp", 0))
                        self.blacklist_token(old_jti, old_exp)
                except JWTError:
                    # Old token is already invalid, ignore
                    pass

            # Update session with new tokens
            session.jti = new_jti
            session.refresh_token = new_refresh_token
            session.access_token_expires_at = access_expires_at
            session.refresh_token_expires_at = refresh_expires_at
            await db.commit()

            # Update cache
            await session_service._cache_session(session)

            return {
                "success": True,
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "expires_at": access_expires_at.isoformat(),
            }

        except JWTError as e:
            error_msg = str(e).lower()
            if "expired" in error_msg:
                return {"success": False, "error": "Refresh token has expired"}
            elif "token type" in error_msg:
                return {"success": False, "error": "Invalid token type. Expected refresh token"}
            else:
                return {"success": False, "error": "Invalid refresh token"}
        except Exception as e:
            return {"success": False, "error": f"Token refresh failed: {e!s}"}


# Create singleton instance
jwt_service = JWTService()
