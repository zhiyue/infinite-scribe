"""
章节相关的 Pydantic 模型
"""

from .create import ChapterCreateRequest, ChapterVersionCreate, ReviewCreate
from .read import ChapterResponse, ChapterVersionResponse, ReviewResponse
from .update import ChapterUpdateRequest, ChapterVersionUpdate, ReviewUpdate

__all__ = [
    # 创建请求
    "ChapterCreateRequest",
    "ChapterVersionCreate",
    "ReviewCreate",
    # 更新请求
    "ChapterUpdateRequest",
    "ChapterVersionUpdate",
    "ReviewUpdate",
    # 查询响应
    "ChapterResponse",
    "ChapterVersionResponse",
    "ReviewResponse",
]
