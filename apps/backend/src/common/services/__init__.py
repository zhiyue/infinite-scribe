"""Common services package."""

from src.external.clients import EmbeddingProvider, get_embedding_service

from .novel_service import NovelService, novel_service
from .password_service import PasswordService
from .user_service import UserService

__all__ = [
    "EmbeddingProvider",
    "get_embedding_service",
    "NovelService",
    "novel_service",
    "PasswordService",
    "UserService",
]
