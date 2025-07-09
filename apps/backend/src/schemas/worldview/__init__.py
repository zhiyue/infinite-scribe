"""
世界观相关的 Pydantic 模型
"""

from .create import StoryArcCreateRequest, WorldviewEntryCreateRequest
from .read import StoryArcResponse, WorldviewEntryResponse
from .update import StoryArcUpdateRequest, WorldviewEntryUpdateRequest

__all__ = [
    # 创建请求
    "WorldviewEntryCreateRequest",
    "StoryArcCreateRequest",
    # 更新请求
    "WorldviewEntryUpdateRequest",
    "StoryArcUpdateRequest",
    # 查询响应
    "WorldviewEntryResponse",
    "StoryArcResponse",
]
