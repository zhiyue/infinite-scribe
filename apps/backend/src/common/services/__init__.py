"""Common services package."""

from src.external.clients import EmbeddingClient as EmbeddingService
from src.external.clients import embedding_service

from .novel_service import NovelService, novel_service
from .password_service import PasswordService
from .user_service import UserService

__all__ = [
    "EmbeddingService",
    "embedding_service",
    "NovelService",
    "novel_service",
    "PasswordService",
    "UserService",
]
