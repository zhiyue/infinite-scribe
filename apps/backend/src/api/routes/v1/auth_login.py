"""Authentication endpoints for user login/logout."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    AuthResponse,
    ErrorResponse,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserResponse,
)
from src.common.services.user.user_service import UserService
from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
user_service = UserService()


@router.post(
    "/login",
    response_model=AuthResponse | ErrorResponse,
    summary="User login",
    description="Authenticate user and return access/refresh tokens",
)
async def login_user(
    request: UserLoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse | ErrorResponse:
    """Authenticate user and return tokens.

    Args:
        request: User login credentials
        req: FastAPI request object (for IP and user agent)
        db: Database session

    Returns:
        Authentication response with tokens and user data

    Raises:
        HTTPException: If login fails
    """
    # 登录
    try:
        # Get client info
        ip_address = req.client.host if req.client else None
        user_agent = req.headers.get("user-agent")

        # Attempt login
        result = await user_service.login(db, request.email, request.password, ip_address, user_agent)

        if not result["success"]:
            # Determine appropriate status code
            status_code = status.HTTP_401_UNAUTHORIZED
            if "locked" in result["error"].lower():
                status_code = status.HTTP_423_LOCKED
            elif "verify" in result["error"].lower():
                status_code = status.HTTP_403_FORBIDDEN

            # 构建错误响应，包含额外信息
            error_detail = {
                "message": result["error"],
                "error": result["error"],  # 保持向后兼容
            }

            # 添加额外的错误信息
            if "remaining_attempts" in result:
                error_detail["remaining_attempts"] = result["remaining_attempts"]
            if "locked_until" in result:
                error_detail["locked_until"] = result["locked_until"]

            raise HTTPException(status_code=status_code, detail=error_detail)

        # Create response
        user_response = UserResponse.model_validate(result["user"])
        return AuthResponse(
            success=True,
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user=user_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        ) from e


@router.post(
    "/logout",
    response_model=MessageResponse | ErrorResponse,
    summary="User logout",
    description="Logout user and invalidate current session",
)
async def logout_user(
    req: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse | ErrorResponse:
    """Logout user and invalidate session.

    Args:
        req: FastAPI request object (contains JWT info in state)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success or error message

    Raises:
        HTTPException: If logout fails
    """
    try:
        # Get JTI from request state (set by auth middleware)
        jti = getattr(req.state, "jti", None)

        if not jti:
            logger.warning("No JTI found in request state during logout")
            # Still return success for security
            return MessageResponse(success=True, message="Logged out successfully")

        # Logout user
        result = await user_service.logout(db, jti)

        if not result["success"]:
            logger.error(f"Logout failed: {result['error']}")
            # Still return success for security

        return MessageResponse(success=True, message="Logged out successfully")

    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Return success for security - don't reveal internal errors
        return MessageResponse(success=True, message="Logged out successfully")


@router.post(
    "/refresh",
    response_model=TokenResponse | ErrorResponse,
    summary="Refresh access token",
    description="Refresh access token using refresh token",
)
async def refresh_access_token(
    request: RefreshTokenRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse | ErrorResponse:
    """Refresh access token using refresh token.

    Args:
        request: Refresh token request
        req: FastAPI request object (for extracting old access token)
        db: Database session

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh fails
    """
    try:
        # Extract old access token from header if present
        authorization = req.headers.get("Authorization")
        old_access_token = None
        if authorization:
            from src.common.services.user.auth_service import auth_service

            old_access_token = auth_service.extract_token_from_header(authorization)

        # Refresh the token
        from src.common.services.user.auth_service import auth_service

        result = await auth_service.refresh_access_token(db, request.refresh_token, old_access_token)

        if not result["success"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result["error"])

        return TokenResponse(success=True, access_token=result["access_token"], refresh_token=result["refresh_token"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh",
        ) from e
