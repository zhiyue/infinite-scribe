"""
Dialogue schemas按CQRS模式组织

基于ADR-001的对话状态管理架构，
支持会话(Session)和轮次(Round)的完整生命周期管理。
"""

from .create import (
    CommandRequest,
    ContentSearchRequest,
    ConversationRoundCreate,
    ConversationSessionCreate,
    CreateSessionRequest,
    RoundCreateRequest,
    VersionCreateRequest,
    VersionMergeRequest,
)
from .enums import DialogueRole, ScopeType, SessionStatus
from .read import (
    CommandStatusResponse,
    ConversationRoundResponse,
    ConversationSessionResponse,
    DialogueCache,
    DialogueHistory,
    RoundResponse,
    SessionResponse,
)
from .update import (
    ConversationRoundUpdate,
    ConversationSessionUpdate,
    UpdateSessionRequest,
)


# ---------- 公共导出 ----------

__all__ = [
    # 枚举
    "ScopeType",
    "SessionStatus",
    "DialogueRole",
    # Create models (from create.py)
    "ConversationSessionCreate",
    "ConversationRoundCreate",
    "CreateSessionRequest",
    "RoundCreateRequest",
    "CommandRequest",
    "ContentSearchRequest",
    "VersionCreateRequest",
    "VersionMergeRequest",
    # Read models (from read.py)
    "ConversationSessionResponse",
    "ConversationRoundResponse",
    "DialogueHistory",
    "DialogueCache",
    "SessionResponse",
    "RoundResponse",
    "CommandStatusResponse",
    # Update models (from update.py)
    "ConversationSessionUpdate",
    "ConversationRoundUpdate",
    "UpdateSessionRequest",
]
