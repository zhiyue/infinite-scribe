"""Agent 系统通用常量定义。

集中管理所有 agents 共享的常量，包括消息封装、状态码等。
遵循单一数据源原则，避免在代码中硬编码魔法值。
"""

from __future__ import annotations

from typing import Final

# ==================== 消息封装常量 ====================

# Envelope 版本配置
ENVELOPE_VERSION: Final[str] = "v1"
"""Envelope 消息格式的当前版本号"""

# 默认值
DEFAULT_EVENT_TYPE: Final[str] = "unknown"
"""当消息中未指定 type 时使用的默认事件类型"""

# 状态码
STATUS_OK: Final[str] = "ok"
"""表示操作成功的状态码"""

STATUS_ERROR: Final[str] = "error"
"""表示操作失败的状态码"""

# 保留字段名
RESERVED_FIELD_TYPE: Final[str] = "type"
"""Envelope 层级的保留字段，不应出现在业务数据中"""


# ==================== 辅助函数 ====================


def is_success_status(status: str | None) -> bool:
    """检查状态是否表示成功。

    Args:
        status: 状态字符串

    Returns:
        True 如果状态表示成功
    """
    return status == STATUS_OK


def is_error_status(status: str | None) -> bool:
    """检查状态是否表示错误。

    Args:
        status: 状态字符串

    Returns:
        True 如果状态表示错误
    """
    return status == STATUS_ERROR


__all__ = [
    "ENVELOPE_VERSION",
    "DEFAULT_EVENT_TYPE",
    "STATUS_OK",
    "STATUS_ERROR",
    "RESERVED_FIELD_TYPE",
    "is_success_status",
    "is_error_status",
]
