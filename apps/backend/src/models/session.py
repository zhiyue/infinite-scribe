"""Session model for JWT token management and blacklisting."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.utils.datetime_utils import utc_now
from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.user import User


class Session(BaseModel):
    """Session model for tracking user sessions and JWT tokens."""

    __tablename__ = "sessions"

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped[User] = relationship(back_populates="sessions")

    # Token information
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)  # JWT ID for blacklisting
    refresh_token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)

    # Session metadata
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)  # Support IPv6
    device_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # mobile, desktop, tablet
    device_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Token lifecycle
    access_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("idx_session_user_active", "user_id", "is_active"),
        Index("idx_session_jti_active", "jti", "is_active"),
        Index("idx_session_refresh_token_active", "refresh_token", "is_active"),
        Index("idx_session_expires", "access_token_expires_at", "refresh_token_expires_at"),
    )

    def __repr__(self) -> str:
        """String representation of the Session."""
        return f"<Session(id={self.id}, user_id={self.user_id}, jti='{self.jti[:8]}...')>"

    @property
    def is_access_token_expired(self) -> bool:
        """Check if the access token is expired."""
        return utc_now() > self.access_token_expires_at

    @property
    def is_refresh_token_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return utc_now() > self.refresh_token_expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the session is still valid."""
        return self.is_active and not self.is_refresh_token_expired and self.revoked_at is None

    def revoke(self, reason: str | None = None) -> None:
        """Revoke the session.

        Args:
            reason: Optional reason for revocation
        """
        self.is_active = False
        self.revoked_at = utc_now()
        if reason:
            self.revoke_reason = reason

    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "jti": self.jti,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "device_type": self.device_type,
            "device_name": self.device_name,
            "is_active": self.is_active,
            "is_valid": self.is_valid,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "access_token_expires_at": self.access_token_expires_at.isoformat()
            if self.access_token_expires_at
            else None,
            "refresh_token_expires_at": self.refresh_token_expires_at.isoformat()
            if self.refresh_token_expires_at
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoke_reason": self.revoke_reason,
        }
