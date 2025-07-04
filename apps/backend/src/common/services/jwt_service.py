"""JWT service for token management."""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from redis import Redis

from src.core.auth_config import auth_config
from src.core.config import settings


class JWTService:
    """Service for JWT token management and password hashing."""

    def __init__(self):
        """Initialize JWT service."""
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = auth_config.JWT_SECRET_KEY
        self.algorithm = auth_config.JWT_ALGORITHM
        self.access_token_expire_minutes = auth_config.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = auth_config.REFRESH_TOKEN_EXPIRE_DAYS
        
        # Redis client for blacklist
        self._redis_client: Optional[Redis] = None

    @property
    def redis_client(self) -> Redis:
        """Get Redis client for blacklist management."""
        if self._redis_client is None:
            self._redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
        return self._redis_client

    # Password hashing methods
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    # JWT token methods
    def create_access_token(
        self, 
        subject: str, 
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, datetime]:
        """Create an access token.
        
        Args:
            subject: Subject of the token (usually user ID)
            additional_claims: Additional claims to include in the token
            
        Returns:
            Tuple of (token, jti, expires_at)
        """
        jti = secrets.token_urlsafe(16)
        expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": str(subject),
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "jti": jti,
            "token_type": "access",
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt, jti, expires_at

    def create_refresh_token(
        self, 
        subject: str, 
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, datetime]:
        """Create a refresh token.
        
        Args:
            subject: Subject of the token (usually user ID)
            additional_claims: Additional claims to include in the token
            
        Returns:
            Tuple of (token, expires_at)
        """
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode = {
            "sub": str(subject),
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "token_type": "refresh",
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt, expires_at

    def verify_token(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
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
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            self.redis_client.setex(
                f"blacklist:{jti}",
                ttl,
                "1"
            )

    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted.
        
        Args:
            jti: JWT ID to check
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        if not jti:
            return False
            
        return bool(self.redis_client.get(f"blacklist:{jti}"))

    def extract_token_from_header(self, authorization: str) -> Optional[str]:
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


# Create singleton instance
jwt_service = JWTService()