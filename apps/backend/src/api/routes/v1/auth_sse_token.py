"""SSE token authentication endpoints."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from pydantic import BaseModel

from src.core.config import settings
from src.middleware.auth import get_current_user
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


class SSETokenResponse(BaseModel):
    """SSE token response model."""

    sse_token: str
    expires_at: datetime
    token_type: str = "sse"


@router.post("/sse-token", response_model=SSETokenResponse)
async def create_sse_token(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a short-term SSE authentication token.

    Generates a specialized token for SSE connections with a short expiration time.
    This token is derived from the user's JWT session and is used specifically
    for EventSource authentication since EventSource doesn't support custom headers.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        SSETokenResponse: SSE token with expiration timestamp

    Raises:
        HTTPException: 401 if user is not authenticated
    """
    # Use single timestamp for consistency
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.auth.sse_token_expire_seconds)

    # Create SSE token payload as simple dict
    payload = {
        "user_id": current_user.id,  # Keep as integer, consistent with JWT service
        "token_type": "sse",
        "exp": expires_at,
        "iat": now,
        "jti": secrets.token_urlsafe(16),  # Add random JWT ID to ensure uniqueness
    }

    # Encode SSE token using the same secret as JWT
    sse_token = jwt.encode(
        payload,
        settings.auth.jwt_secret_key,
        algorithm=settings.auth.jwt_algorithm,
    )

    return SSETokenResponse(sse_token=sse_token, expires_at=expires_at)


def verify_sse_token(sse_token: str) -> str:
    """
    Verify SSE token and extract user ID.

    Args:
        sse_token: SSE authentication token to verify

    Returns:
        str: User ID from the token

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    logger.debug("🔍 开始验证SSE token", extra={
        "has_token": bool(sse_token),
        "token_length": len(sse_token) if sse_token else 0,
        "token_prefix": sse_token[:20] + "..." if sse_token and len(sse_token) > 20 else sse_token
    })

    # Input validation
    if not sse_token or not sse_token.strip():
        logger.warning("❌ SSE token验证失败: token为空")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is required")

    try:
        # Decode the SSE token
        payload = jwt.decode(sse_token, settings.auth.jwt_secret_key, algorithms=[settings.auth.jwt_algorithm])

        # Verify it's an SSE token and extract user ID
        if payload.get("token_type") != "sse":
            logger.warning(f"无效的token类型: {payload.get('token_type')}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("SSE token缺少user_id")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        logger.debug(f"SSE token验证成功: user_id={user_id}")

        return str(user_id)

    except ExpiredSignatureError as e:
        logger.warning("SSE token已过期")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SSE token has expired") from e
    except JWTError as e:
        logger.warning(f"SSE token无效: {type(e).__name__}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e
