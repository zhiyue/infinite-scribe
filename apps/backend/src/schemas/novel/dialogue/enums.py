"""对话相关的枚举定义"""

from enum import Enum


class ScopeType(str, Enum):
    """对话范围类型"""

    GENESIS = "GENESIS"  # 小说创作阶段
    CHAPTER = "CHAPTER"  # 章节写作阶段
    REVIEW = "REVIEW"  # 审查和修订阶段
    PLANNING = "PLANNING"  # 规划和大纲阶段
    WORLDBUILDING = "WORLDBUILDING"  # 世界构建阶段


class SessionStatus(str, Enum):
    """会话生命周期状态"""

    ACTIVE = "ACTIVE"  # 会话当前活跃
    COMPLETED = "COMPLETED"  # 会话成功完成
    ABANDONED = "ABANDONED"  # 会话被放弃
    PAUSED = "PAUSED"  # 会话已暂停


class DialogueRole(str, Enum):
    """对话参与者角色"""

    USER = "user"  # 用户
    ASSISTANT = "assistant"  # AI助手
    SYSTEM = "system"  # 系统
    TOOL = "tool"  # 工具