"""
后端模型定义包
从 packages/shared-types 迁移而来
"""

# 导入所有模型以便于使用
from .db import *
from .api import *
from .events import *
from .sse import *

# Auth models
from src.models.base import Base as AuthBase, BaseModel as AuthBaseModel
from src.models.user import User
from src.models.session import Session
from src.models.email_verification import EmailVerification, VerificationPurpose

__all__ = [
    # 从 db 模块导出
    'BaseDBModel',
    'init_db',
    'get_db',
    'AsyncSessionLocal',
    'Base',
    'create_database_tables',
    'drop_database_tables',
    'recreate_database',
    'check_database_connection',
    'shutdown_database',
    'NovelModel',
    'ChapterModel',
    'ChapterVersionModel',
    'CharacterModel',
    'WorldviewEntryModel',
    'StoryArcModel',
    'ReviewModel',
    'OutlineModel',
    'SceneCardModel',
    'CharacterInteractionModel',
    'WorkflowRunModel',
    'AgentActivityModel',
    'EventModel',
    'AgentConfigurationModel',
    'GenesisSessionModel',
    'GenesisStepModel',
    'AuditLogModel',
    
    # 从 api 模块导出
    'BaseAPIModel',
    'NovelCreateRequest',
    'NovelUpdateRequest',
    'ChapterCreateRequest',
    'ChapterUpdateRequest',
    'CharacterCreateRequest',
    'CharacterUpdateRequest',
    'WorldviewEntryCreateRequest',
    'WorldviewEntryUpdateRequest',
    'GenesisStartRequest',
    'GenesisFeedbackRequest',
    'WorkflowStartRequest',
    
    # 从 events 模块导出
    'BaseEvent',
    'NovelCreatedEvent',
    'ChapterUpdatedEvent',
    'WorkflowStartedEvent',
    'WorkflowCompletedEvent',
    'AgentActivityEvent',
    'GenesisProgressEvent',
    'ChapterCompletedEvent',
    'ChapterRevisedEvent',
    'ReviewCreatedEvent',
    'GenesisSessionStartedEvent',
    'GenesisSessionCompletedEvent',
    'GenesisStageCompletedEvent',
    'ConceptIterationApprovedEvent',
    'ConceptIterationRejectedEvent',
    'StoryFrameworkGeneratedEvent',
    'WorldviewGeneratedEvent',
    'CharactersGeneratedEvent',
    'OutlineGeneratedEvent',
    
    # 从 sse 模块导出
    'SSEEvent',
    'SSEEventType',
    'SSEMessage',
    'NovelProgressSSE',
    'ChapterProgressSSE',
    'AgentStatusSSE',
    'ErrorSSE',
    # Auth models
    "AuthBase",
    "AuthBaseModel",
    "User",
    "Session",
    "EmailVerification",
    "VerificationPurpose",
]