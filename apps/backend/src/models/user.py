from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.common.utils.datetime_utils import utc_now
from src.models.base import BaseModel  # 假设你有一个 BaseModel

if TYPE_CHECKING:
    from src.models.email_verification import EmailVerification
    from src.models.session import Session


class User(BaseModel):
    """User model for authentication and user management."""

    __tablename__ = "users"

    # Basic information
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # Profile information
    first_name: Mapped[str | None] = mapped_column(String(100), default=None)
    last_name: Mapped[str | None] = mapped_column(String(100), default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(500), default=None)
    bio: Mapped[str | None] = mapped_column(String(1000), default=None)

    # Account status
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    # Security
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), default=None)  # Support IPv6

    # Timestamps
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    sessions: Mapped[list[Session]] = relationship(back_populates="user", cascade="all, delete-orphan")
    email_verifications: Mapped[list[EmailVerification]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_username_active", "username", "is_active"),
        Index("idx_user_locked_until", "locked_until"),
    )

    def __repr__(self) -> str:
        """String representation of the User."""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.username

    @property
    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if not self.locked_until:
            return False
        return utc_now() < self.locked_until

    @property
    def is_email_verified(self) -> bool:
        """检查邮箱是否已验证"""
        return self.email_verified_at is not None

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary.

        Args:
            include_sensitive: Whether to include sensitive information

        Returns:
            Dictionary representation of the user
        """
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_superuser": self.is_superuser,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
            "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
        }

        if include_sensitive:
            data.update(
                {
                    "failed_login_attempts": self.failed_login_attempts,
                    "is_locked": self.is_locked,
                    "locked_until": self.locked_until.isoformat() if self.locked_until else None,
                    "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
                    "last_login_ip": self.last_login_ip,
                    "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
                }
            )

        return data
