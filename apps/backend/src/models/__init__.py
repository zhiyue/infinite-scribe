"""
SQLAlchemy ORM 模型定义包
"""

# 基础模型
from src.db.sql.base import Base
from src.db.sql.base import Base as AuthBase  # 兼容旧名称
from src.models.base import BaseModel as AuthBaseModel
from src.models.chapter import Chapter, ChapterVersion, Review
from src.models.character import Character
from src.models.conversation import ConversationRound, ConversationSession

# 认证相关模型
from src.models.email_verification import EmailVerification, VerificationPurpose
from src.models.event import DomainEvent
from src.models.genesis import ConceptTemplate

# 业务领域模型
from src.models.novel import Novel
from src.models.session import Session
from src.models.user import User
from src.models.workflow import (
    AsyncTask,
    CommandInbox,
    EventOutbox,
    FlowResumeHandle,
)
from src.models.worldview import StoryArc, WorldviewEntry

# Pydantic 模型已迁移到 schemas 模块
# 使用 from src.schemas import * 导入

__all__ = [
    # 基础模型
    "AuthBase",
    "AuthBaseModel",
    "Base",
    # 认证模型
    "User",
    "Session",
    "EmailVerification",
    "VerificationPurpose",
    # 业务领域模型
    "Novel",
    "Chapter",
    "ChapterVersion",
    "Review",
    "Character",
    "ConversationSession",
    "ConversationRound",
    "WorldviewEntry",
    "StoryArc",
    "ConceptTemplate",
    "DomainEvent",
    "CommandInbox",
    "AsyncTask",
    "EventOutbox",
    "FlowResumeHandle",
]
