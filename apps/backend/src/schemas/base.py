"""
基础 Pydantic 模型类

提供所有 DTO 的基础功能
"""

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class BaseSchema(BaseModel):
    """所有 Schema 的基类"""

    model_config = ConfigDict(
        from_attributes=True,  # 允许从 ORM 对象创建
        validate_assignment=True,  # 赋值时验证
        str_strip_whitespace=True,  # 自动去除字符串首尾空格
        use_enum_values=True,  # 使用枚举值而非枚举对象
    )


class TimestampMixin(BaseModel):
    """包含时间戳的 Mixin"""

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def set_timestamps(cls, data):
        """自动设置时间戳"""
        if isinstance(data, dict):
            now = datetime.now(tz=UTC)
            if "created_at" not in data:
                data["created_at"] = now
            if "updated_at" not in data:
                data["updated_at"] = now
        return data


class BaseDBModel(BaseModel):
    """数据库模型基类 - 用于直接映射数据库表的 Pydantic 模型"""

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    @model_validator(mode="before")
    @classmethod
    def auto_update_timestamp(cls, data):
        """自动更新 updated_at 字段"""
        if isinstance(data, dict) and "updated_at" in cls.model_fields and "updated_at" not in data:
            # 在初始化时如果没有提供 updated_at, 则设置为当前时间
            data["updated_at"] = datetime.now(tz=UTC)
        return data

    def __setattr__(self, name, value):
        """重写属性设置以自动更新 updated_at"""
        super().__setattr__(name, value)
        # 如果设置的不是 updated_at 本身, 且模型有 updated_at 字段, 则自动更新
        if (
            name != "updated_at"
            and name != "_BaseDBModel__pydantic_extra__"  # 避免内部属性
            and hasattr(self, "updated_at")
            and "updated_at" in self.__class__.model_fields
        ):
            super().__setattr__("updated_at", datetime.now(tz=UTC))


class ApiResponse(BaseSchema, Generic[T]):
    """统一API响应格式"""

    code: int = Field(..., description="响应状态码: 0=成功, 非0=错误")
    msg: str = Field(..., description="响应消息")
    data: T | None = Field(None, description="响应数据")


class PaginationInfo(BaseSchema):
    """分页信息"""

    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, le=100, description="每页大小")
    total: int = Field(..., ge=0, description="总记录数")
    total_pages: int = Field(..., ge=0, description="总页数")


class PaginatedResponse(BaseSchema, Generic[T]):
    """分页数据响应"""

    items: list[T] = Field(..., description="数据项目列表")
    pagination: PaginationInfo = Field(..., description="分页信息")


class PaginatedApiResponse(ApiResponse[PaginatedResponse[T]]):
    """统一分页API响应格式"""

    pass
