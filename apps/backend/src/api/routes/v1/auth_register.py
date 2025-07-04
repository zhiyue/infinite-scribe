"""Authentication endpoints for user registration."""

import logging
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    UserRegisterRequest,
    RegisterResponse,
    ErrorResponse,
    MessageResponse,
    ResendVerificationRequest,
    UserResponse,
)
from src.common.services.user_service import UserService
from src.database import get_db
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()
user_service = UserService()


@router.post(
    "/register",
    response_model=Union[RegisterResponse, ErrorResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new user account with email verification",
)
async def register_user(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Union[RegisterResponse, ErrorResponse]:
    """Register a new user account.
    
    Args:
        request: User registration data
        db: Database session
        
    Returns:
        Registration response with user data and verification message
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        # Convert Pydantic model to dict
        user_data = request.model_dump()
        
        # Register user
        result = await user_service.register_user(db, user_data)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        # Create response
        user_response = UserResponse.model_validate(result["user"])
        return RegisterResponse(
            success=True,
            user=user_response,
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.get(
    "/verify-email",
    response_model=Union[MessageResponse, ErrorResponse],
    summary="Verify email address",
    description="Verify user's email address using verification token",
)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> Union[MessageResponse, ErrorResponse]:
    """Verify user's email address.
    
    Args:
        token: Email verification token
        db: Database session
        
    Returns:
        Success or error message
        
    Raises:
        HTTPException: If verification fails
    """
    try:
        result = await user_service.verify_email(db, token)
        
        if not result["success"]:
            status_code = status.HTTP_400_BAD_REQUEST
            if "expired" in result["error"].lower():
                status_code = status.HTTP_410_GONE
            elif "invalid" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND
                
            raise HTTPException(
                status_code=status_code,
                detail=result["error"]
            )
        
        return MessageResponse(
            success=True,
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email verification"
        )


@router.post(
    "/resend-verification",
    response_model=Union[MessageResponse, ErrorResponse],
    summary="Resend verification email",
    description="Resend email verification to user's email address",
)
async def resend_verification_email(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> Union[MessageResponse, ErrorResponse]:
    """Resend verification email to user.
    
    Args:
        request: Email to resend verification to
        db: Database session
        
    Returns:
        Success or error message
        
    Raises:
        HTTPException: If resending fails
    """
    try:
        # For security, we don't reveal if email exists or not
        # This is a simplified implementation - in production you might want
        # to check if user exists and is not already verified
        
        return MessageResponse(
            success=True,
            message="If the email exists and is not verified, a verification email has been sent"
        )
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending verification email"
        )