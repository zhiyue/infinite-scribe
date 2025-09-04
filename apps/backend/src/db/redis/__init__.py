"""
Redis database module for InfiniteScribe.

Provides Redis-based caching and session management.
"""

from .dialogue_cache import DialogueCacheManager

__all__ = [
    "DialogueCacheManager",
]