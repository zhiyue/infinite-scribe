"""Conversations API routes."""

from fastapi import APIRouter

from . import (
    conversations_commands,
    conversations_content,
    conversations_quality,
    conversations_rounds,
    conversations_sessions,
    # conversations_stages,  # DEPRECATED: Moved to Genesis API
    conversations_versions,
)

# 创建主路由器
router = APIRouter()

# 会话管理路由
router.include_router(conversations_sessions.router, tags=["conversations-sessions"])

# 轮次管理路由
router.include_router(conversations_rounds.router, tags=["conversations-rounds"])

# 阶段管理路由 - DEPRECATED: Moved to Genesis API
# router.include_router(conversations_stages.router, tags=["conversations-stages"])

# 消息和命令路由
router.include_router(conversations_commands.router, tags=["conversations-commands"])

# 内容管理路由
router.include_router(conversations_content.router, tags=["conversations-content"])

# 质量和一致性路由
router.include_router(conversations_quality.router, tags=["conversations-quality"])

# 版本控制路由
router.include_router(conversations_versions.router, tags=["conversations-versions"])
