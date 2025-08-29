"""Authentication endpoints for user registration."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    ErrorResponse,
    MessageResponse,
    RegisterResponse,
    ResendVerificationRequest,
    UserRegisterRequest,
    UserResponse,
)
from src.common.services.user_service import UserService
from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()
user_service = UserService()


@router.post(
    "/register",
    response_model=RegisterResponse | ErrorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new user account with email verification",
)
async def register_user(
    request: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse | ErrorResponse:
    """Register a new user account.

    Args:
        request: User registration data
        background_tasks: FastAPI background tasks for async operations
        db: Database session

    Returns:
        Registration response with user data and verification message

    Raises:
        HTTPException: If registration fails
    """
    try:
        # Convert Pydantic model to dict
        user_data = request.model_dump()

        # Register user with background tasks for async email sending
        result = await user_service.register_user(db, user_data, background_tasks)

        if not result["success"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        # Create response
        user_response = UserResponse.model_validate(result["user"])
        return RegisterResponse(success=True, user=user_response, message=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        ) from None


@router.get(
    "/verify-email",
    response_model=MessageResponse | ErrorResponse,
    summary="Verify email address",
    description="Verify user's email address using verification token",
)
async def verify_email(
    token: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse | ErrorResponse:
    """Verify user's email address.

    Args:
        token: Email verification token
        background_tasks: FastAPI background tasks for async operations
        db: Database session

    Returns:
        Success or error message

    Raises:
        HTTPException: If verification fails
    """
    try:
        result = await user_service.verify_email(db, token, background_tasks)

        if not result["success"]:
            status_code = status.HTTP_400_BAD_REQUEST
            if "expired" in result["error"].lower():
                status_code = status.HTTP_410_GONE
            elif "invalid" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND

            raise HTTPException(status_code=status_code, detail=result["error"])

        return MessageResponse(success=True, message=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email verification",
        ) from None


@router.post(
    "/resend-verification",
    response_model=MessageResponse | ErrorResponse,
    summary="Resend verification email",
    description="Resend email verification to user's email address",
)
async def resend_verification_email(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse | ErrorResponse:
    """Resend verification email to user.

    Args:
        request: Email to resend verification to
        background_tasks: FastAPI background tasks for async operations
        db: Database session

    Returns:
        Success or error message

    Raises:
        HTTPException: If resending fails
    """
    try:
        # 调用用户服务的重发验证邮件方法
        await user_service.resend_verification_email(
            db,
            request.email,
            background_tasks
        )

        # For security, always return the same message regardless of whether
        # the email exists or not
        return MessageResponse(
            success=True,
            message="If the email exists and is not verified, a verification email has been sent",
        )

    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending verification email",
        ) from None
