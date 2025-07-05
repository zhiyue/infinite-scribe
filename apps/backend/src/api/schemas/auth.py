"""Pydantic schemas for authentication endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Request schemas
class UserRegisterRequest(BaseModel):
    """User registration request schema."""
    
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")


class UserLoginRequest(BaseModel):
    """User login request schema."""
    
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str = Field(..., description="Refresh token")


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""
    
    email: EmailStr = Field(..., description="Email address")


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""
    
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class UpdateProfileRequest(BaseModel):
    """Update user profile request schema."""
    
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    bio: Optional[str] = Field(None, max_length=1000, description="Bio")


class ResendVerificationRequest(BaseModel):
    """Resend verification email request schema."""
    
    email: EmailStr = Field(..., description="Email address")


# Response schemas
class UserResponse(BaseModel):
    """User response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    email_verified_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    """Authentication response schema."""
    
    success: bool
    access_token: str
    refresh_token: str
    user: UserResponse
    message: Optional[str] = None


class RegisterResponse(BaseModel):
    """Registration response schema."""
    
    success: bool
    user: UserResponse
    message: str


class TokenResponse(BaseModel):
    """Token response schema."""
    
    success: bool
    access_token: str
    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response schema."""
    
    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    success: bool = False
    error: str
    details: Optional[dict] = None


class PasswordStrengthResponse(BaseModel):
    """Password strength validation response."""
    
    is_valid: bool
    score: int
    errors: list[str]
    suggestions: list[str]