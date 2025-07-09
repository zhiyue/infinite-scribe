"""
后端模型定义包
从 packages/shared-types 迁移而来
"""

# 导入所有模型以便于使用
# Auth models
from src.models.base import Base as AuthBase
from src.models.base import BaseModel as AuthBaseModel
from src.models.email_verification import EmailVerification, VerificationPurpose
from src.models.session import Session
from src.models.user import User

# 暂时保留 star imports 以避免破坏现有代码
# TODO: 后续需要改为显式导入
from .api import *  # noqa: F403
from .db import *  # noqa: F403
from .events import *  # noqa: F403

# 导入 ORM 模型
from .orm_models import (
    AsyncTask,
    Chapter,
    ChapterVersion,
    Character,
    CommandInbox,
    ConceptTemplate,
    DomainEvent,
    EventOutbox,
    FlowResumeHandle,
    GenesisSession,
    Novel,
    Review,
    StoryArc,
    WorldviewEntry,
)
from .sse import *  # noqa: F403

__all__ = [  # noqa: F405
    # 从 db 模块导出
    "BaseDBModel",
    "init_db",
    "get_db",
    "AsyncSessionLocal",
    "Base",
    "create_database_tables",
    "drop_database_tables",
    "recreate_database",
    "check_database_connection",
    "shutdown_database",
    "NovelModel",
    "ChapterModel",
    "ChapterVersionModel",
    "CharacterModel",
    "WorldviewEntryModel",
    "StoryArcModel",
    "ReviewModel",
    "OutlineModel",
    "SceneCardModel",
    "CharacterInteractionModel",
    "WorkflowRunModel",
    "AgentActivityModel",
    "EventModel",
    "AgentConfigurationModel",
    "GenesisSessionModel",
    "GenesisStepModel",
    "AuditLogModel",
    # 从 api 模块导出
    "BaseAPIModel",
    "NovelCreateRequest",
    "NovelUpdateRequest",
    "ChapterCreateRequest",
    "ChapterUpdateRequest",
    "CharacterCreateRequest",
    "CharacterUpdateRequest",
    "WorldviewEntryCreateRequest",
    "WorldviewEntryUpdateRequest",
    "GenesisStartRequest",
    "GenesisFeedbackRequest",
    "WorkflowStartRequest",
    # 从 events 模块导出
    "BaseEvent",
    "NovelCreatedEvent",
    "ChapterUpdatedEvent",
    "WorkflowStartedEvent",
    "WorkflowCompletedEvent",
    "AgentActivityEvent",
    "GenesisProgressEvent",
    "ChapterCompletedEvent",
    "ChapterRevisedEvent",
    "ReviewCreatedEvent",
    "GenesisSessionStartedEvent",
    "GenesisSessionCompletedEvent",
    "GenesisStageCompletedEvent",
    "ConceptIterationApprovedEvent",
    "ConceptIterationRejectedEvent",
    "StoryFrameworkGeneratedEvent",
    "WorldviewGeneratedEvent",
    "CharactersGeneratedEvent",
    "OutlineGeneratedEvent",
    # 从 sse 模块导出
    "SSEEvent",
    "SSEEventType",
    "SSEMessage",
    "NovelProgressSSE",
    "ChapterProgressSSE",
    "AgentStatusSSE",
    "ErrorSSE",
    # Auth models
    "AuthBase",
    "AuthBaseModel",
    "User",
    "Session",
    "EmailVerification",
    "VerificationPurpose",
    # ORM models
    "Novel",
    "Chapter",
    "ChapterVersion",
    "Character",
    "WorldviewEntry",
    "StoryArc",
    "Review",
    "GenesisSession",
    "ConceptTemplate",
    "DomainEvent",
    "CommandInbox",
    "AsyncTask",
    "EventOutbox",
    "FlowResumeHandle",
]
