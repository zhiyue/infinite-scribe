"""
角色相关的 Pydantic 模型
"""

from .create import CharacterCreateRequest
from .read import CharacterResponse
from .update import CharacterUpdateRequest

__all__ = [
    # 创建请求
    "CharacterCreateRequest",
    # 更新请求
    "CharacterUpdateRequest",
    # 查询响应
    "CharacterResponse",
]
