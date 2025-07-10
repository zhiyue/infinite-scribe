"""Authentication endpoints for password management."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    ChangePasswordRequest,
    ErrorResponse,
    ForgotPasswordRequest,
    MessageResponse,
    PasswordStrengthResponse,
    ResetPasswordRequest,
)
from src.common.services.password_service import PasswordService
from src.common.services.user_service import UserService
from src.database import get_db
from src.middleware.auth import get_current_user
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
user_service = UserService()
password_service = PasswordService()


@router.post(
    "/forgot-password",
    response_model=MessageResponse | ErrorResponse,
    summary="Forgot password",
    description="Send password reset email to user",
)
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse | ErrorResponse:
    """Send password reset email to user.

    Args:
        request: Forgot password request with email
        background_tasks: FastAPI background tasks for async operations
        db: Database session

    Returns:
        Success or error message

    Raises:
        HTTPException: If sending reset email fails
    """
    try:
        # Request password reset with background tasks for async email sending
        result = await user_service.request_password_reset(db, request.email, background_tasks)

        return MessageResponse(success=True, message=result["message"])

    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request",
        ) from None


@router.post(
    "/reset-password",
    response_model=MessageResponse | ErrorResponse,
    summary="Reset password",
    description="Reset user password using reset token",
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse | ErrorResponse:
    """Reset user password using reset token.

    Args:
        request: Reset password request with token and new password
        db: Database session

    Returns:
        Success or error message

    Raises:
        HTTPException: If password reset fails
    """
    try:
        # Reset password using UserService
        result = await user_service.reset_password(db, request.token, request.new_password)

        if not result["success"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        return MessageResponse(success=True, message="Password has been reset successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset",
        ) from None


@router.post(
    "/change-password",
    response_model=MessageResponse | ErrorResponse,
    summary="Change password",
    description="Change user password (requires authentication)",
)
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse | ErrorResponse:
    """Change user password (authenticated users only).

    Args:
        request: Change password request
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success or error message

    Raises:
        HTTPException: If password change fails
    """
    try:
        # Validate new password strength
        validation_result = password_service.validate_password_strength(request.new_password)
        if not validation_result["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password is too weak: {', '.join(validation_result['errors'])}",
            )

        # Verify current password
        if not password_service.verify_password(request.current_password, str(current_user.password_hash)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

        # Check if new password is the same as current
        if password_service.verify_password(request.new_password, str(current_user.password_hash)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        # TODO: Implement actual password change logic
        # This requires additional methods in UserService

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Password change not yet implemented",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password change",
        ) from None


@router.post(
    "/validate-password",
    response_model=PasswordStrengthResponse,
    summary="Validate password strength",
    description="Check password strength and get suggestions",
)
async def validate_password_strength(
    password: str,
) -> PasswordStrengthResponse:
    """Validate password strength and return suggestions.

    Args:
        password: Password to validate

    Returns:
        Password strength validation result
    """
    try:
        result = password_service.validate_password_strength(password)

        return PasswordStrengthResponse(
            is_valid=result["is_valid"],
            score=result["score"],
            errors=result["errors"],
            suggestions=result["suggestions"],
        )

    except Exception as e:
        logger.error(f"Password validation error: {e}")
        # Return a safe default response
        return PasswordStrengthResponse(
            is_valid=False,
            score=0,
            errors=["Unable to validate password"],
            suggestions=["Please try again"],
        )
