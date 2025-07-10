"""Email verification model for email confirmation and password reset."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.utils.datetime_utils import utc_now
from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.user import User


class VerificationPurpose(str, Enum):
    """Purpose of the verification token."""

    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


class EmailVerification(BaseModel):
    """Email verification model for tracking verification tokens."""

    __tablename__ = "email_verifications"

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped[User] = relationship(back_populates="email_verifications")

    # Token information
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    purpose: Mapped[VerificationPurpose] = mapped_column(SQLEnum(VerificationPurpose), nullable=False)

    # Email tracking
    email: Mapped[str] = mapped_column(String(255), nullable=False)  # Store email in case user changes it

    # Token lifecycle
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Request metadata
    requested_from_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
    ) -> EmailVerification:
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
            expires_at=utc_now() + timedelta(hours=expires_in_hours),
            requested_from_ip=requested_from_ip,
            user_agent=user_agent,
        )

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return True
        return utc_now() > self.expires_at

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
        self.used_at = utc_now()

    def to_dict(self) -> dict:
        """Convert verification to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "purpose": self.purpose.value,
            "email": self.email,
            "is_valid": self.is_valid,
            "is_expired": self.is_expired,
            "is_used": self.is_used,
            "expires_at": self.expires_at.isoformat() if self.expires_at is not None else None,
            "used_at": self.used_at.isoformat() if self.used_at is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
        }
