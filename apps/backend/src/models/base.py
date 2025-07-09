"""Base model for authentication-related database models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer

from src.db.sql.base import Base


class BaseModel(Base):
    """Base model for all authentication database models."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
