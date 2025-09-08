"""Common services package - organized by business domains."""

from src.external.clients import EmbeddingProvider, get_embedding_service

# System-level services
from .audit_service import AuditService, audit_service
from .content import (
    NovelService,
    novel_service,
)
from .conversation import (
    ConversationCacheManager,
    ConversationService,
    conversation_service,
)
from .rate_limit_service import RateLimitService, rate_limit_service

# Domain services
from .user import (
    AuthService,
    PasswordService,
    SessionService,
    UserEmailService,
    UserEmailTasks,
    UserService,
    auth_service,
    session_service,
    user_email_service,
    user_email_tasks,
)
from .workflow import (
    TaskService,
    task_service,
)

__all__ = [
    # External clients
    "EmbeddingProvider",
    "get_embedding_service",

    # User domain
    "AuthService", "auth_service",
    "PasswordService",
    "SessionService", "session_service",
    "UserService",
    "UserEmailService", "UserEmailTasks", "user_email_service", "user_email_tasks",

    # Conversation domain
    "ConversationCacheManager",
    "ConversationService", "conversation_service",

    # Content domain
    "NovelService", "novel_service",

    # Workflow domain
    "TaskService", "task_service",

    # System-level services
    "AuditService", "audit_service",
    "RateLimitService", "rate_limit_service",
]
