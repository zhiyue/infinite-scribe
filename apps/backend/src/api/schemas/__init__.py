"""API schemas for request/response validation."""

from .auth import (
    AuthResponse,
    ChangePasswordRequest,
    ErrorResponse,
    ForgotPasswordRequest,
    MessageResponse,
    PasswordStrengthResponse,
    RefreshTokenRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

__all__ = [
    # Request schemas
    "UserRegisterRequest",
    "UserLoginRequest",
    "RefreshTokenRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "ChangePasswordRequest",
    "UpdateProfileRequest",
    "ResendVerificationRequest",
    # Response schemas
    "UserResponse",
    "AuthResponse",
    "RegisterResponse",
    "TokenResponse",
    "MessageResponse",
    "ErrorResponse",
    "PasswordStrengthResponse",
]
