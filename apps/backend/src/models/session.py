"""Session model for JWT token management and blacklisting."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class Session(BaseModel):
    """Session model for tracking user sessions and JWT tokens."""

    __tablename__ = "sessions"

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="sessions")

    # Token information
    jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID for blacklisting
    refresh_token = Column(String(500), unique=True, nullable=False, index=True)

    # Session metadata
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True, index=True)  # Support IPv6
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    device_name = Column(String(100), nullable=True)

    # Token lifecycle
    access_token_expires_at = Column(DateTime, nullable=False)
    refresh_token_expires_at = Column(DateTime, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String(255), nullable=True)

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
        return datetime.utcnow() > self.access_token_expires_at

    @property
    def is_refresh_token_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.utcnow() > self.refresh_token_expires_at

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
        self.revoked_at = datetime.utcnow()
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
