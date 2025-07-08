"""Authentication endpoints for user profile management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    ErrorResponse,
    MessageResponse,
    UpdateProfileRequest,
    UserResponse,
)
from src.common.services.user_service import UserService
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
user_service = UserService()


@router.get(
    "/me",
    response_model=UserResponse | ErrorResponse,
    summary="Get current user",
    description="Get current authenticated user's profile information",
)
async def get_current_user_profile(
    current_user: User = Depends(require_auth),
) -> UserResponse | ErrorResponse:
    """Get current authenticated user's profile.

    Args:
        current_user: Current authenticated user

    Returns:
        User profile information

    Raises:
        HTTPException: If user retrieval fails
    """
    try:
        return UserResponse.model_validate(current_user)

    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving user profile",
        ) from None


@router.put(
    "/me",
    response_model=UserResponse | ErrorResponse,
    summary="Update current user profile",
    description="Update current authenticated user's profile information",
)
async def update_current_user_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> UserResponse | ErrorResponse:
    """Update current authenticated user's profile.

    Args:
        request: Profile update request
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated user profile information

    Raises:
        HTTPException: If profile update fails
    """
    try:
        # TODO: Implement actual profile update logic
        # This requires additional methods in UserService

        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Profile update not yet implemented")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating profile",
        ) from None


@router.delete(
    "/me",
    response_model=MessageResponse | ErrorResponse,
    summary="Delete current user account",
    description="Delete current authenticated user's account (soft delete)",
)
async def delete_current_user_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> MessageResponse | ErrorResponse:
    """Delete current authenticated user's account.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success or error message

    Raises:
        HTTPException: If account deletion fails
    """
    try:
        # TODO: Implement actual account deletion logic
        # This should be a soft delete (set is_active = False)

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Account deletion not yet implemented",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete account error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting account",
        ) from None
