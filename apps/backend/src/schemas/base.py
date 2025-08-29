"""
基础 Pydantic 模型类

提供所有 DTO 的基础功能
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, model_validator


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
