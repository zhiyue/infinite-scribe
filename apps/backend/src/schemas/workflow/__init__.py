"""
工作流相关的 Pydantic 模型
"""

from .create import AsyncTaskCreate, CommandInboxCreate, EventOutboxCreate, FlowResumeHandleCreate
from .read import AsyncTaskResponse, CommandInboxResponse, EventOutboxResponse, FlowResumeHandleResponse
from .update import AsyncTaskUpdate, CommandInboxUpdate, EventOutboxUpdate, FlowResumeHandleUpdate

__all__ = [
    # 创建请求
    "CommandInboxCreate",
    "AsyncTaskCreate",
    "EventOutboxCreate",
    "FlowResumeHandleCreate",
    # 更新请求
    "CommandInboxUpdate",
    "AsyncTaskUpdate",
    "EventOutboxUpdate",
    "FlowResumeHandleUpdate",
    # 查询响应
    "CommandInboxResponse",
    "AsyncTaskResponse",
    "EventOutboxResponse",
    "FlowResumeHandleResponse",
]
