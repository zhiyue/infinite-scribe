"""
后端模型定义包
从 packages/shared-types 迁移而来
"""

# 导入所有模型以便于使用
from .db import *
from .api import *
from .events import *
from .sse import *

__all__ = [
    # 从 db 模块导出
    'BaseDBModel',
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
    
    # 从 sse 模块导出
    'SSEEvent',
    'SSEEventType',
    'NovelProgressSSE',
    'ChapterProgressSSE',
    'AgentStatusSSE',
    'ErrorSSE',
]