"""UUID utility functions for safe UUID conversion and validation."""

from __future__ import annotations

from typing import Any
from uuid import UUID


def safe_uuid_conversion(value: str | None) -> UUID | None:
    """安全地将字符串转换为UUID，处理非法格式的情况。

    Args:
        value: 可能包含非UUID格式的字符串

    Returns:
        有效的UUID对象或None

    Examples:
        >>> safe_uuid_conversion("123e4567-e89b-12d3-a456-426614174000")
        UUID('123e4567-e89b-12d3-a456-426614174000')
        >>> safe_uuid_conversion("invalid-uuid")
        None
        >>> safe_uuid_conversion(None)
        None
    """
    if not value:
        return None

    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def is_valid_uuid(value: str | None) -> bool:
    """检查字符串是否为有效的UUID格式。

    Args:
        value: 要检查的字符串

    Returns:
        如果是有效UUID则返回True，否则返回False

    Examples:
        >>> is_valid_uuid("123e4567-e89b-12d3-a456-426614174000")
        True
        >>> is_valid_uuid("invalid-uuid")
        False
        >>> is_valid_uuid(None)
        False
    """
    return safe_uuid_conversion(value) is not None