"""
API request/response models

These models are used for API validation and documentation.
They may differ from database models to provide better API interfaces.
"""

from pydantic import BaseModel

# TODO: Task 5 - 在此文件中定义API专用的Pydantic模型
# 将实现创世流程相关的请求/响应模型


class BaseAPIModel(BaseModel):
    """API模型基类"""

    model_config = {"validate_assignment": True}


# API模型将在 Task 5 中实现
# - CreateNovelRequest
# - CreateNovelResponse
# - GenesisStepRequest
# - GenesisStepResponse
# - UpdateCharacterRequest
# - UpdateCharacterResponse
