"""Authentication configuration."""

import os
from pydantic import Field
from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    """Authentication configuration settings."""

    # JWT Settings
    JWT_SECRET_KEY: str = Field(
        default="test_jwt_secret_key_for_development_only_32_chars" if os.getenv("NODE_ENV") == "test" else ...,
        description="Secret key for JWT signing (min 32 chars)"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm for JWT signing"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration in days"
    )

    # Email Service
    RESEND_API_KEY: str = Field(
        default="test_api_key" if os.getenv("NODE_ENV") == "test" else ...,
        description="Resend API key for sending emails"
    )
    RESEND_DOMAIN: str = Field(
        default="test.example.com" if os.getenv("NODE_ENV") == "test" else ...,
        description="Domain for sending emails"
    )
    RESEND_FROM_EMAIL: str = Field(
        default="noreply@example.com",
        description="From email address"
    )

    # Security Settings
    PASSWORD_MIN_LENGTH: int = Field(
        default=8,
        description="Minimum password length"
    )
    ACCOUNT_LOCKOUT_ATTEMPTS: int = Field(
        default=5,
        description="Failed login attempts before lockout"
    )
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = Field(
        default=30,
        description="Account lockout duration in minutes"
    )

    # Rate Limiting
    RATE_LIMIT_LOGIN_PER_MINUTE: int = Field(
        default=5,
        description="Login attempts per minute"
    )
    RATE_LIMIT_REGISTER_PER_HOUR: int = Field(
        default=10,
        description="Registration attempts per hour"
    )
    RATE_LIMIT_PASSWORD_RESET_PER_HOUR: int = Field(
        default=3,
        description="Password reset attempts per hour"
    )

    # Email Verification
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = Field(
        default=24,
        description="Email verification token expiration in hours"
    )
    PASSWORD_RESET_EXPIRE_HOURS: int = Field(
        default=1,
        description="Password reset token expiration in hours"
    )

    # Development Settings
    USE_MAILDEV: bool = Field(
        default=False,
        description="Use Maildev for local email testing"
    )
    MAILDEV_HOST: str = Field(
        default="localhost",
        description="Maildev SMTP host"
    )
    MAILDEV_PORT: int = Field(
        default=1025,
        description="Maildev SMTP port"
    )

    class Config:
        """Pydantic config."""
        env_file = ".env.test" if os.getenv("NODE_ENV") == "test" else ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Create singleton instance
auth_config = AuthConfig()