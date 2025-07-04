"""
JWT Authentication service for Genesis API.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7'))

# Security scheme
security = HTTPBearer()


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # subject (user_id)
    exp: int  # expiration time
    iat: int  # issued at
    jti: str  # JWT ID
    token_type: str  # 'access' or 'refresh'
    user_id: str
    username: str
    permissions: list = []


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthService:
    """JWT Authentication service."""
    
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.access_token_expire_minutes = JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = JWT_REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(self, user_id: str, username: str, permissions: list = None) -> str:
        """Create JWT access token."""
        if permissions is None:
            permissions = []
        
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            'sub': user_id,
            'exp': int(expires_at.timestamp()),
            'iat': int(now.timestamp()),
            'jti': str(uuid4()),
            'token_type': 'access',
            'user_id': user_id,
            'username': username,
            'permissions': permissions
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str, username: str) -> str:
        """Create JWT refresh token."""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            'sub': user_id,
            'exp': int(expires_at.timestamp()),
            'iat': int(now.timestamp()),
            'jti': str(uuid4()),
            'token_type': 'refresh',
            'user_id': user_id,
            'username': username
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(**payload)
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def create_token_pair(self, user_id: str, username: str, permissions: list = None) -> TokenResponse:
        """Create access and refresh token pair."""
        if permissions is None:
            permissions = []
        
        access_token = self.create_access_token(user_id, username, permissions)
        refresh_token = self.create_refresh_token(user_id, username)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60
        )
    
    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify it's a refresh token
            if payload.get('token_type') != 'refresh':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Create new token pair
            return self.create_token_pair(
                user_id=payload['user_id'],
                username=payload['username'],
                permissions=[]  # Could fetch from database
            )
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )


# Global auth service instance
auth_service = AuthService()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenPayload:
    """FastAPI dependency to get current authenticated user."""
    try:
        token = credentials.credentials
        token_payload = auth_service.verify_token(token)
        
        # Verify it's an access token
        if token_payload.token_type != 'access':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return token_payload
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_permissions(required_permissions: list):
    """Decorator to require specific permissions."""
    def permission_checker(current_user: TokenPayload = Depends(get_current_user)):
        user_permissions = set(current_user.permissions)
        required_permissions_set = set(required_permissions)
        
        if not required_permissions_set.issubset(user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return permission_checker


# Demo/Development Helper Functions
def create_demo_token() -> str:
    """Create a demo token for development/testing."""
    return auth_service.create_access_token(
        user_id="demo_user",
        username="demo@example.com",
        permissions=["genesis:command:create", "genesis:event:read"]
    )


def validate_demo_environment():
    """Validate that JWT is properly configured for production."""
    if JWT_SECRET_KEY == 'your-secret-key-change-in-production':
        if os.getenv('ENVIRONMENT', 'development') == 'production':
            raise RuntimeError(
                "JWT_SECRET_KEY must be set to a secure random value in production"
            )
        else:
            logger.warning(
                "Using default JWT_SECRET_KEY. This is fine for development but "
                "must be changed in production."
            )


# Initialize validation
validate_demo_environment()


# Export commonly used functions
__all__ = [
    'auth_service',
    'get_current_user',
    'require_permissions',
    'TokenPayload',
    'TokenResponse',
    'create_demo_token'
]