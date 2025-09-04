"""
Conversation dialogue ORM models (ADR-001)

Implements persistent dialogue storage using PostgreSQL tables:
- conversation_sessions: aggregate session state with OCC versioning
- conversation_rounds: hierarchical rounds keyed by round_path
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.sql.base import Base


class ConversationSession(Base):
    """Generic conversation session (aggregate root)."""

    __tablename__ = "conversation_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    stage: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    rounds: Mapped[list[ConversationRound]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ConversationRound(Base):
    """A single conversation round/turn within a session (supports hierarchy via round_path)."""

    __tablename__ = "conversation_rounds"
    __table_args__ = (UniqueConstraint("session_id", "round_path", name="uq_conversation_round"),)

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    round_path: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    input: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tool_calls: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(128))
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    session: Mapped[ConversationSession] = relationship(back_populates="rounds")
