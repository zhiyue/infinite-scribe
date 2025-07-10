"""DateTime 工具函数，处理时区相关操作。"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """获取当前 UTC 时间（时区感知）。

    返回一个带有 UTC 时区信息的 datetime 对象，
    用于兼容 PostgreSQL 的 TIMESTAMP WITH TIME ZONE (timestamptz) 字段。

    Returns:
        datetime: 带 UTC 时区信息的当前时间
    """
    return datetime.now(UTC)


def from_timestamp_utc(timestamp: float) -> datetime:
    """从时间戳创建时区感知的 UTC datetime。

    Args:
        timestamp: Unix 时间戳

    Returns:
        datetime: 带 UTC 时区信息的时间
    """
    return datetime.fromtimestamp(timestamp, tz=UTC)


def ensure_utc(dt: datetime) -> datetime:
    """确保 datetime 对象带有 UTC 时区信息。

    如果输入的 datetime 已经有时区信息，会转换到 UTC。
    如果输入的 datetime 没有时区信息，会假定它是 UTC 并添加时区信息。

    Args:
        dt: datetime 对象（可能带或不带时区）

    Returns:
        datetime: 带 UTC 时区信息的时间
    """
    if dt.tzinfo is None:
        # 假定无时区的时间是 UTC
        return dt.replace(tzinfo=UTC)
    else:
        # 转换到 UTC
        return dt.astimezone(UTC)


def to_timestamp(dt: datetime) -> float:
    """将 datetime 转换为 Unix 时间戳。

    Args:
        dt: datetime 对象（建议带时区）

    Returns:
        float: Unix 时间戳
    """
    if dt.tzinfo is None:
        # 警告：无时区的 datetime 会被假定为本地时间
        # 建议总是使用带时区的 datetime
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def parse_iso_datetime(iso_string: str) -> datetime | None:
    """解析 ISO 8601 格式的时间字符串。

    Args:
        iso_string: ISO 8601 格式的时间字符串

    Returns:
        datetime: 带时区信息的时间，解析失败返回 None
    """
    try:
        # Python 3.11+ 的 fromisoformat 支持完整的 ISO 8601
        dt = datetime.fromisoformat(iso_string)
        # 如果没有时区信息，添加 UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, AttributeError):
        return None


def format_iso_datetime(dt: datetime) -> str:
    """将 datetime 格式化为 ISO 8601 字符串。

    Args:
        dt: datetime 对象

    Returns:
        str: ISO 8601 格式的时间字符串
    """
    # 确保有时区信息
    dt = ensure_utc(dt)
    return dt.isoformat()
