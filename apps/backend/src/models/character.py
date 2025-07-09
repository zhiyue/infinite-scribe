"""
角色相关的 SQLAlchemy ORM 模型
"""

from uuid import uuid4

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.sql.base import Base


class Character(Base):
    """角色表 - 存储小说中所有角色的详细设定信息"""

    __tablename__ = "characters"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="角色唯一标识符，对应Neo4j中的app_id")
    novel_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表",
    )
    name = Column(String(255), nullable=False, comment="角色姓名，必填")
    role = Column(String(50), comment='角色定位，如"主角"、"反派"、"配角"等')
    description = Column(Text, comment="角色外观、特征等描述信息")
    background_story = Column(Text, comment="角色背景故事，包括身世、经历等")
    personality_traits = Column(ARRAY(Text), comment='性格特征数组，如["勇敢", "正直", "幽默"]')
    goals = Column(ARRAY(Text), comment='角色目标数组，如["寻找失散的妹妹", "成为最强剑士"]')
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="角色创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="角色信息最后更新时间",
    )

    # 关系
    novel = relationship("Novel", back_populates="characters")
