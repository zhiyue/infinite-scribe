"""Email verification model for email confirmation and password reset."""

import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import cast

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class VerificationPurpose(str, Enum):
    """Purpose of the verification token."""

    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


class EmailVerification(BaseModel):
    """Email verification model for tracking verification tokens."""

    __tablename__ = "email_verifications"

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="email_verifications")

    # Token information
    token = Column(String(255), unique=True, nullable=False, index=True)
    purpose = Column(SQLEnum(VerificationPurpose), nullable=False)

    # Email tracking
    email = Column(String(255), nullable=False)  # Store email in case user changes it

    # Token lifecycle
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Request metadata
    requested_from_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("idx_verification_token", "token"),
        Index("idx_verification_user_purpose", "user_id", "purpose"),
        Index("idx_verification_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        """String representation of the EmailVerification."""
        return f"<EmailVerification(id={self.id}, user_id={self.user_id}, purpose='{self.purpose}')>"

    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    @classmethod
    def create_for_user(
        cls,
        user_id: int,
        email: str,
        purpose: VerificationPurpose,
        expires_in_hours: int = 24,
        requested_from_ip: str | None = None,
        user_agent: str | None = None,
    ) -> "EmailVerification":
        """Create a new verification token for a user.

        Args:
            user_id: ID of the user
            email: Email address to verify
            purpose: Purpose of the verification
            expires_in_hours: Token validity in hours
            requested_from_ip: IP address of the request
            user_agent: User agent of the request

        Returns:
            New EmailVerification instance
        """
        return cls(
            user_id=user_id,
            email=email,
            token=cls.generate_token(),
            purpose=purpose,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
            requested_from_ip=requested_from_ip,
            user_agent=user_agent,
        )

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return True
        expires_at = cast(datetime, self.expires_at)
        return datetime.now(UTC) > expires_at

    @property
    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid."""
        return not self.is_expired and not self.is_used

    def mark_as_used(self) -> None:
        """Mark the token as used."""
        self.used_at = datetime.now(UTC)

    def to_dict(self) -> dict:
        """Convert verification to dictionary."""
        expires_at: datetime | None = cast(datetime, self.expires_at) if self.expires_at is not None else None
        used_at: datetime | None = cast(datetime, self.used_at) if self.used_at is not None else None
        created_at: datetime | None = cast(datetime, self.created_at) if self.created_at is not None else None

        return {
            "id": self.id,
            "user_id": self.user_id,
            "purpose": self.purpose.value,
            "email": self.email,
            "is_valid": self.is_valid,
            "is_expired": self.is_expired,
            "is_used": self.is_used,
            "expires_at": expires_at.isoformat() if expires_at is not None else None,
            "used_at": used_at.isoformat() if used_at is not None else None,
            "created_at": created_at.isoformat() if created_at is not None else None,
        }
