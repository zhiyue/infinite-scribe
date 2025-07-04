"""
Base database model with common functionality.
"""

from datetime import UTC, datetime
from pydantic import BaseModel, model_validator


class BaseDBModel(BaseModel):
    """数据库模型基类"""

    model_config = {
        "from_attributes": True,
        "validate_assignment": True,
        "str_strip_whitespace": True,
        "use_enum_values": True,
    }

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
            and "updated_at" in self.model_fields
        ):
            super().__setattr__("updated_at", datetime.now(tz=UTC))