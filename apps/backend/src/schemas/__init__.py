"""
Pydantic schemas (DTOs) for API layer

按照职责单一原则组织:
- enums.py: 共享的枚举类型
- base.py: 基础模型类
- novel/: 小说相关的 Create/Update/Read DTOs
- chapter/: 章节相关的 DTOs
- character/: 角色相关的 DTOs
- worldview/: 世界观相关的 DTOs
- genesis/: 创世流程相关的 DTOs
- workflow/: 工作流相关的 DTOs
- domain_event.py: 领域事件模型
- events.py: 事件系统模型
- sse.py: SSE 推送事件模型
"""

# 基础模型和枚举类型
from .base import *  # noqa: F403

# 业务领域 schemas
from .chapter import *  # noqa: F403
from .character import *  # noqa: F403

# 领域事件
from .domain_event import *  # noqa: F403
from .enums import *  # noqa: F403
from .events import *  # noqa: F403
from .genesis import *  # noqa: F403
from .novel import *  # noqa: F403

# SSE 事件
from .sse import *  # noqa: F403
from .workflow import *  # noqa: F403
from .worldview import *  # noqa: F403
