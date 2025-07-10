"""Base model for authentication-related database models."""

from sqlalchemy import Column, DateTime, Integer

from src.common.utils.datetime_utils import utc_now
from src.db.sql.base import Base


class BaseModel(Base):
    """Base model for all authentication database models."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
