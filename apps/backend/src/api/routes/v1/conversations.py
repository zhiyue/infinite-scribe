"""Conversation (Genesis) endpoints."""

from fastapi import APIRouter

from .conversations import (
    conversations_commands,
    conversations_content,
    conversations_quality,
    conversations_rounds,
    conversations_sessions,
    conversations_stages,
    conversations_versions,
)

router = APIRouter()

# Include all conversation-related routes
router.include_router(conversations_sessions.router, tags=["conversations", "sessions"])
router.include_router(conversations_rounds.router, tags=["conversations", "rounds"])
router.include_router(conversations_stages.router, tags=["conversations", "stages"])
router.include_router(conversations_commands.router, tags=["conversations", "commands"])
router.include_router(conversations_content.router, tags=["conversations", "content"])
router.include_router(conversations_quality.router, tags=["conversations", "quality"])
router.include_router(conversations_versions.router, tags=["conversations", "versions"])