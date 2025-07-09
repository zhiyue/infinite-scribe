"""
领域事件相关的 SQLAlchemy ORM 模型
"""

from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func

from src.db.sql.base import Base


class DomainEvent(Base):
    """领域事件表 - 存储所有业务领域事件,支持事件源架构"""

    __tablename__ = "domain_events"
    __table_args__ = (
        Index("idx_domain_events_aggregate", "aggregate_type", "aggregate_id"),
        Index("idx_domain_events_event_type", "event_type"),
        Index("idx_domain_events_created_at", "created_at"),
        Index("idx_domain_events_correlation_id", "correlation_id"),
        Index("idx_domain_events_causation_id", "causation_id"),
        Index("idx_domain_events_aggregate_type_time", "aggregate_type", "created_at"),
        Index("idx_domain_events_event_type_time", "event_type", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键，用于保证事件顺序")
    event_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True, default=uuid4, comment="事件唯一标识符")
    correlation_id = Column(PGUUID(as_uuid=True), comment="关联ID，用于追踪同一业务流程中的相关事件")
    causation_id = Column(PGUUID(as_uuid=True), comment="因果链ID，表示引发此事件的上级事件")
    event_type = Column(Text, nullable=False, comment='事件类型，如"ChapterCreated"、"ReviewCompleted"')
    event_version = Column(Integer, nullable=False, default=1, comment="事件版本号，用于事件模式演化")
    aggregate_type = Column(Text, nullable=False, comment='聚合根类型，如"Novel"、"Chapter"')
    aggregate_id = Column(Text, nullable=False, comment="聚合根ID，标识具体的业务实体")
    payload = Column(JSONB, comment="事件数据载荷，包含事件的详细内容")
    event_metadata = Column("metadata", JSONB, comment="事件元数据，如用户ID、时间戳、来源等")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="事件创建时间，不可修改"
    )
