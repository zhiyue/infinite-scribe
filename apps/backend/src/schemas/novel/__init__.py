"""
小说相关的 Pydantic schemas

按照用例分离:
- create.py: 创建小说的请求 DTO
- update.py: 更新小说的请求 DTO
- read.py: 查询小说的响应 DTO
"""

from .create import *  # noqa: F403
from .read import *  # noqa: F403
from .update import *  # noqa: F403
