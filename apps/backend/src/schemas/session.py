"""Session 相关的 Pydantic 模型定义。"""

from datetime import datetime

from src.schemas.base import BaseSchema


class SessionCacheSchema(BaseSchema):
    """用于 Redis 缓存的 Session 数据模型。

    使用 Pydantic 自动处理序列化/反序列化，包括：
    - datetime 与 ISO-8601 字符串的相互转换
    - None 值的正确处理
    - 类型验证
    """

    # 核心标识
    id: int
    user_id: int
    jti: str
    refresh_token: str

    # 元数据
    user_agent: str | None = None
    ip_address: str | None = None
    device_type: str | None = None
    device_name: str | None = None

    # 生命周期 & 状态
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    last_accessed_at: datetime | None = None
    is_active: bool = True
    revoked_at: datetime | None = None
    revoke_reason: str | None = None

    # 时间戳（从 BaseSchema 继承的 created_at, updated_at 会自动处理）
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SessionResponseSchema(BaseSchema):
    """Session API 响应模型。"""

    id: int
    user_id: int
    jti: str

    # 元数据
    user_agent: str | None = None
    ip_address: str | None = None
    device_type: str | None = None
    device_name: str | None = None

    # 状态
    is_active: bool
    last_accessed_at: datetime | None = None
    created_at: datetime

    # 不暴露敏感信息如 refresh_token
