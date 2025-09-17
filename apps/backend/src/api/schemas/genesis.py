"""Genesis API模式定义

定义Genesis解耦API的请求和响应模式。
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.enums import GenesisStatus, GenesisStage, StageStatus, StageSessionStatus


# Genesis Flow 相关模式
class GenesisFlowResponse(BaseModel):
    """Genesis流程响应模式"""

    id: UUID = Field(description="流程ID")
    novel_id: UUID = Field(description="小说ID")
    status: GenesisStatus = Field(description="流程状态")
    current_stage: GenesisStage | None = Field(description="当前阶段")
    version: int = Field(description="版本号")
    state: dict[str, Any] = Field(description="流程状态数据")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    class Config:
        from_attributes = True


class GenesisFlowCreateRequest(BaseModel):
    """创建Genesis流程请求模式"""

    initial_stage: GenesisStage | None = Field(
        default=GenesisStage.INITIAL_PROMPT,
        description="初始阶段"
    )
    initial_state: dict[str, Any] | None = Field(
        default_factory=dict,
        description="初始状态数据"
    )


class GenesisFlowUpdateRequest(BaseModel):
    """更新Genesis流程请求模式"""

    status: GenesisStatus | None = Field(default=None, description="流程状态")
    current_stage: GenesisStage | None = Field(default=None, description="当前阶段")
    state: dict[str, Any] | None = Field(default=None, description="状态数据")
    expected_version: int | None = Field(default=None, description="期望版本（乐观锁）")


# Genesis Stage 相关模式
class GenesisStageResponse(BaseModel):
    """Genesis阶段响应模式"""

    id: UUID = Field(description="阶段ID")
    flow_id: UUID = Field(description="流程ID")
    stage: GenesisStage = Field(description="阶段类型")
    status: StageStatus = Field(description="阶段状态")
    config: dict[str, Any] = Field(description="阶段配置")
    result: dict[str, Any] | None = Field(description="阶段结果")
    iteration_count: int = Field(description="迭代次数")
    metrics: dict[str, Any] | None = Field(description="阶段指标")
    started_at: datetime | None = Field(description="开始时间")
    completed_at: datetime | None = Field(description="完成时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    class Config:
        from_attributes = True


class GenesisStageCreateRequest(BaseModel):
    """创建Genesis阶段请求模式"""

    config: dict[str, Any] | None = Field(
        default_factory=dict,
        description="阶段配置"
    )


class GenesisStageUpdateRequest(BaseModel):
    """更新Genesis阶段请求模式"""

    status: StageStatus | None = Field(default=None, description="阶段状态")
    config: dict[str, Any] | None = Field(default=None, description="阶段配置")
    result: dict[str, Any] | None = Field(default=None, description="阶段结果")
    metrics: dict[str, Any] | None = Field(default=None, description="阶段指标")


# Genesis Stage Session 相关模式
class GenesisStageSessionResponse(BaseModel):
    """Genesis阶段会话关联响应模式"""

    id: UUID = Field(description="关联ID")
    stage_id: UUID = Field(description="阶段ID")
    session_id: UUID = Field(description="会话ID")
    status: StageSessionStatus = Field(description="关联状态")
    is_primary: bool = Field(description="是否为主会话")
    session_kind: str | None = Field(description="会话类别")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    class Config:
        from_attributes = True


class GenesisStageSessionCreateRequest(BaseModel):
    """创建阶段会话关联请求模式"""

    session_id: UUID | None = Field(
        default=None,
        description="现有会话ID（如果为空则创建新会话）"
    )
    is_primary: bool = Field(default=False, description="是否设为主会话")
    session_kind: str | None = Field(
        default="user_interaction",
        description="会话类别"
    )


class GenesisStageSessionUpdateRequest(BaseModel):
    """更新阶段会话关联请求模式"""

    status: StageSessionStatus | None = Field(default=None, description="关联状态")
    is_primary: bool | None = Field(default=None, description="是否为主会话")
    session_kind: str | None = Field(default=None, description="会话类别")


# 复合响应模式
class GenesisFlowWithStagesResponse(BaseModel):
    """包含阶段信息的Genesis流程响应模式"""

    flow: GenesisFlowResponse = Field(description="流程信息")
    stages: list[GenesisStageResponse] = Field(description="阶段列表")


class GenesisStageWithSessionsResponse(BaseModel):
    """包含会话信息的Genesis阶段响应模式"""

    stage: GenesisStageResponse = Field(description="阶段信息")
    sessions: list[GenesisStageSessionResponse] = Field(description="会话列表")


# 错误响应模式
class GenesisErrorResponse(BaseModel):
    """Genesis API错误响应模式"""

    error: str = Field(description="错误类型")
    message: str = Field(description="错误消息")
    details: dict[str, Any] | None = Field(default=None, description="错误详情")


# 分页响应模式
class PaginatedGenesisFlowsResponse(BaseModel):
    """分页的Genesis流程列表响应模式"""

    flows: list[GenesisFlowResponse] = Field(description="流程列表")
    total: int = Field(description="总数")
    offset: int = Field(description="偏移量")
    limit: int = Field(description="限制数量")


class PaginatedGenesisStagesResponse(BaseModel):
    """分页的Genesis阶段列表响应模式"""

    stages: list[GenesisStageResponse] = Field(description="阶段列表")
    total: int = Field(description="总数")
    offset: int = Field(description="偏移量")
    limit: int = Field(description="限制数量")