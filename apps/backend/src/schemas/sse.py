"""
SSE (Server-Sent Events) 事件模型定义

定义了前后端共享的 SSE 事件数据结构，确保类型安全和契约一致性。
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventScope(str, Enum):
    """事件作用域枚举"""

    USER = "user"  # 仅推送给特定用户
    SESSION = "session"  # 推送给特定会话
    NOVEL = "novel"  # 推送给订阅特定小说的用户
    GLOBAL = "global"  # 系统级广播


class ErrorLevel(str, Enum):
    """错误级别枚举"""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SSEMessage(BaseModel):
    """
    SSE 消息基类（遵循 W3C 规范）

    用于生成标准的 text/event-stream 格式消息
    """

    event: str = Field(..., description="事件类型，使用 domain.action-past 格式")
    data: dict[str, Any] = Field(..., description="事件数据")
    id: str | None = Field(None, description="事件 ID，格式：{source}:{partition}:{offset}")
    retry: int | None = Field(None, description="重连延迟（毫秒）", ge=0, le=300000)
    scope: EventScope = Field(..., description="事件作用域")
    version: str = Field("1.0", description="事件版本，用于兼容性")

    def to_sse_format(self) -> str:
        """
        转换为标准 SSE 文本格式

        格式示例：
        id: kafka:0:12345
        event: task.progress-updated
        data: {"task_id": "123", "progress": 50, "_scope": "user", "_version": "1.0"}
        retry: 5000

        """
        lines = []

        # 添加事件 ID
        if self.id:
            lines.append(f"id: {self.id}")

        # 添加事件类型
        lines.append(f"event: {self.event}")

        # 添加数据（包含元信息）
        data_with_meta = {**self.data, "_scope": self.scope.value, "_version": self.version}
        lines.append(f"data: {json.dumps(data_with_meta, ensure_ascii=False, default=str)}")

        # 添加重连延迟
        if self.retry:
            lines.append(f"retry: {self.retry}")

        # 空行结束
        lines.append("")

        return "\n".join(lines)

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)})


# ============================================================================
# 具体事件类型定义
# ============================================================================


class TaskProgressEvent(BaseModel):
    """任务进度更新事件"""

    task_id: str = Field(..., description="任务 ID")
    progress: int = Field(..., description="进度百分比", ge=0, le=100)
    message: str | None = Field(None, description="进度描述")
    estimated_remaining: int | None = Field(None, description="预计剩余时间（秒）")


class TaskStatusChangeEvent(BaseModel):
    """任务状态变更事件"""

    task_id: str = Field(..., description="任务 ID")
    old_status: str = Field(..., description="旧状态")
    new_status: str = Field(..., description="新状态")
    timestamp: datetime = Field(..., description="变更时间")
    reason: str | None = Field(None, description="状态变更原因")


class SystemNotificationEvent(BaseModel):
    """系统通知事件"""

    level: Literal["info", "warning", "error"] = Field(..., description="通知级别")
    title: str = Field(..., description="通知标题")
    message: str = Field(..., description="通知内容")
    action_required: bool = Field(False, description="是否需要用户操作")
    action_url: str | None = Field(None, description="操作链接")


class ContentUpdateEvent(BaseModel):
    """内容更新通知事件"""

    entity_type: str = Field(..., description="实体类型（novel, chapter, character 等）")
    entity_id: str = Field(..., description="实体 ID")
    action: Literal["created", "updated", "deleted"] = Field(..., description="操作类型")
    summary: str | None = Field(None, description="更新摘要")
    changed_fields: list[str] | None = Field(None, description="变更的字段列表")


class SSEErrorEvent(BaseModel):
    """SSE 错误事件"""

    level: ErrorLevel = Field(..., description="错误级别")
    code: str = Field(..., description="错误码")
    message: str = Field(..., description="用户友好的错误信息")
    correlation_id: str | None = Field(None, description="关联请求 ID")
    retry_after: int | None = Field(None, description="建议重试时间（秒）")


# ============================================================================
# 小说相关事件
# ============================================================================


class NovelCreatedEvent(BaseModel):
    """小说创建事件"""

    id: str = Field(..., description="小说 ID")
    title: str = Field(..., description="小说标题")
    theme: str | None = Field(None, description="小说主题")
    status: str = Field(..., description="小说状态")
    created_at: datetime = Field(..., description="创建时间")


class NovelStatusChangedEvent(BaseModel):
    """小说状态变更事件"""

    novel_id: str = Field(..., description="小说 ID")
    old_status: str = Field(..., description="旧状态")
    new_status: str = Field(..., description="新状态")
    changed_at: datetime = Field(..., description="变更时间")


class ChapterDraftCreatedEvent(BaseModel):
    """章节草稿创建事件"""

    chapter_id: str = Field(..., description="章节 ID")
    chapter_number: int = Field(..., description="章节序号")
    title: str | None = Field(None, description="章节标题")
    novel_id: str = Field(..., description="所属小说 ID")


class ChapterStatusChangedEvent(BaseModel):
    """章节状态变更事件"""

    chapter_id: str = Field(..., description="章节 ID")
    old_status: str = Field(..., description="旧状态")
    new_status: str = Field(..., description="新状态")
    novel_id: str = Field(..., description="所属小说 ID")


# ============================================================================
# 创世相关事件
# ============================================================================


class GenesisStepCompletedEvent(BaseModel):
    """创世步骤完成事件"""

    session_id: str = Field(..., description="创世会话 ID")
    stage: str = Field(..., description="当前阶段")
    iteration: int = Field(..., description="迭代次数")
    is_confirmed: bool = Field(..., description="是否已确认")
    summary: str | None = Field(None, description="步骤摘要")


# GenesisSessionCompletedEvent removed - replaced by GenesisFlow events


# ============================================================================
# 工作流相关事件
# ============================================================================


class WorkflowStatusChangedEvent(BaseModel):
    """工作流状态变更事件"""

    workflow_id: str = Field(..., description="工作流 ID")
    workflow_type: str = Field(..., description="工作流类型")
    old_status: str = Field(..., description="旧状态")
    new_status: str = Field(..., description="新状态")
    novel_id: str = Field(..., description="关联小说 ID")


# ============================================================================
# 事件创建辅助函数
# ============================================================================


def create_sse_message(
    event_type: str,
    data: dict[str, Any],
    scope: EventScope,
    event_id: str | None = None,
    retry: int | None = None,
    version: str = "1.0",
) -> SSEMessage:
    """
    创建 SSE 消息的辅助函数

    Args:
        event_type: 事件类型（如 "task.progress-updated"）
        data: 事件数据
        scope: 事件作用域
        event_id: 可选的事件 ID
        retry: 可选的重连延迟

    Returns:
        SSEMessage 实例
    """
    return SSEMessage(event=event_type, data=data, scope=scope, id=event_id, retry=retry, version=version)


# 导出所有事件类型
__all__ = [
    # 基础类型
    "EventScope",
    "ErrorLevel",
    "SSEMessage",
    # 通用事件
    "TaskProgressEvent",
    "TaskStatusChangeEvent",
    "SystemNotificationEvent",
    "ContentUpdateEvent",
    "SSEErrorEvent",
    # 小说相关事件
    "NovelCreatedEvent",
    "NovelStatusChangedEvent",
    "ChapterDraftCreatedEvent",
    "ChapterStatusChangedEvent",
    # 创世相关事件
    "GenesisStepCompletedEvent",
    # Note: GenesisSessionCompletedEvent removed - replaced by GenesisFlow events
    # 工作流相关事件
    "WorkflowStatusChangedEvent",
    # 辅助函数
    "create_sse_message",
]
