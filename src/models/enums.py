"""
Database enums and constants.
"""

from enum import Enum


class AgentType(str, Enum):
    """Agent类型枚举"""
    WORLDSMITH = "worldsmith"
    PLOTMASTER = "plotmaster"
    OUTLINER = "outliner"
    DIRECTOR = "director"
    CHARACTER_EXPERT = "character_expert"
    WORLDBUILDER = "worldbuilder"
    WRITER = "writer"
    CRITIC = "critic"
    FACT_CHECKER = "fact_checker"
    REWRITER = "rewriter"


class NovelStatus(str, Enum):
    """小说状态枚举"""
    GENESIS = "GENESIS"
    GENERATING = "GENERATING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChapterStatus(str, Enum):
    """章节状态枚举"""
    DRAFT = "DRAFT"
    REVIEWING = "REVIEWING"
    REVISING = "REVISING"
    PUBLISHED = "PUBLISHED"


class GenesisStatus(str, Enum):
    """创世状态枚举"""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class GenesisStage(str, Enum):
    """创世阶段枚举"""
    CONCEPT_SELECTION = "CONCEPT_SELECTION"  # 立意选择与迭代阶段(选择抽象立意并优化)
    STORY_CONCEPTION = "STORY_CONCEPTION"  # 故事构思阶段(将立意转化为具体故事框架)
    WORLDVIEW = "WORLDVIEW"  # 世界观创建阶段
    CHARACTERS = "CHARACTERS"  # 角色设定阶段
    PLOT_OUTLINE = "PLOT_OUTLINE"  # 情节大纲阶段
    FINISHED = "FINISHED"  # 完成阶段


class CommandStatus(str, Enum):
    """命令状态枚举"""
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OutboxStatus(str, Enum):
    """发件箱状态枚举"""
    PENDING = "PENDING"
    SENT = "SENT"


class HandleStatus(str, Enum):
    """工作流恢复句柄状态枚举"""
    PENDING_PAUSE = "PENDING_PAUSE"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    EXPIRED = "EXPIRED"


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorldviewEntryType(str, Enum):
    """世界观条目类型枚举"""
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    TECHNOLOGY = "TECHNOLOGY"
    LAW = "LAW"
    CONCEPT = "CONCEPT"
    EVENT = "EVENT"
    ITEM = "ITEM"
    CULTURE = "CULTURE"
    SPECIES = "SPECIES"
    OTHER = "OTHER"