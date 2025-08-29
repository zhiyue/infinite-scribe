"""SSE token authentication endpoints."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
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


class SSETokenPayload(BaseModel):
    """SSE token payload for JWT encoding."""

    user_id: str
    session_id: str
    token_type: str = "sse"
    exp: datetime
    iat: datetime


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
    try:
        # Token expires in 60 seconds (short-lived for security)
        expires_delta = timedelta(seconds=60)
        expires_at = datetime.now(UTC) + expires_delta

        # Create SSE token payload
        sse_payload = SSETokenPayload(
            user_id=str(current_user.id),
            session_id="sse_session",  # TODO: Get actual session ID if needed
            exp=expires_at,
            iat=datetime.now(UTC),
        )

        # Encode SSE token using the same secret as JWT
        sse_token = jwt.encode(
            sse_payload.model_dump(),
            settings.auth.jwt_secret_key,
            algorithm=settings.auth.jwt_algorithm,
        )

        logger.info(f"Generated SSE token for user {current_user.id}")

        return SSETokenResponse(sse_token=sse_token, expires_at=expires_at)

    except Exception as e:
        logger.error(f"Failed to create SSE token for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create SSE token"
        ) from e


async def verify_sse_token(sse_token: str) -> str:
    """
    Verify SSE token and extract user ID.

    Args:
        sse_token: SSE authentication token to verify

    Returns:
        str: User ID from the token

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    try:
        # Decode the SSE token
        payload = jwt.decode(sse_token, settings.auth.jwt_secret_key, algorithms=[settings.auth.jwt_algorithm])

        # Verify it's an SSE token
        if payload.get("token_type") != "sse":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        # Extract user ID
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        return user_id

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SSE token has expired"
        ) from e
    except jwt.JWTError as e:
        logger.warning(f"Invalid SSE token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        ) from e
