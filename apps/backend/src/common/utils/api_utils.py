"""API 相关的通用工具函数。"""

from typing import Any
from uuid import uuid4

from fastapi import Response
from src.api.schemas import ErrorResponse


def get_or_create_correlation_id(x_corr_id: str | None) -> str:
    """获取或创建correlation ID from request header。

    Args:
        x_corr_id: 来自请求头的correlation ID

    Returns:
        str: 有效的correlation ID
    """
    try:
        if x_corr_id and len(x_corr_id) <= 64:
            # Accept UUID-like or short ASCII strings
            return x_corr_id
    except Exception:
        pass
    return str(uuid4())


def set_common_headers(
    resp: Response, correlation_id: str, etag: str | None = None, location: str | None = None
) -> None:
    """设置通用响应头。

    Args:
        resp: FastAPI Response对象
        correlation_id: 请求相关ID
        etag: ETag值
        location: Location头值
    """
    resp.headers["X-Correlation-Id"] = correlation_id
    if etag is not None:
        resp.headers["ETag"] = etag
    if location is not None:
        resp.headers["Location"] = location


# 通用API错误响应配置
COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    412: {"model": ErrorResponse, "description": "Precondition Failed"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
    429: {"model": ErrorResponse, "description": "Too Many Requests"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
}
