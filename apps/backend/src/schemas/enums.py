"""
共享的枚举类型定义

这些枚举类型在 API 层和数据层之间共享
"""

from enum import Enum


# Agent 相关枚举
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


# 小说相关枚举
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
    FAILED = "FAILED"


# 创世流程相关枚举
class GenesisStatus(str, Enum):
    """创世会话状态枚举"""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    PAUSED = "PAUSED"


class GenesisStage(str, Enum):
    """创世业务阶段枚举"""

    CONCEPT_SELECTION = "CONCEPT_SELECTION"
    STORY_CONCEPTION = "STORY_CONCEPTION"
    WORLDVIEW = "WORLDVIEW"
    CHARACTERS = "CHARACTERS"
    PLOT_OUTLINE = "PLOT_OUTLINE"
    FINISHED = "FINISHED"


class GenesisEventType(str, Enum):
    """创世流程领域事件类型枚举"""

    # Session lifecycle events
    GENESIS_SESSION_STARTED = "GENESIS_SESSION_STARTED"
    GENESIS_SESSION_COMPLETED = "GENESIS_SESSION_COMPLETED"
    GENESIS_SESSION_ABANDONED = "GENESIS_SESSION_ABANDONED"
    GENESIS_SESSION_PAUSED = "GENESIS_SESSION_PAUSED"
    GENESIS_SESSION_RESUMED = "GENESIS_SESSION_RESUMED"

    # Stage progression events
    STAGE_ENTERED = "STAGE_ENTERED"
    STAGE_COMPLETED = "STAGE_COMPLETED"
    STAGE_CONFIRMED = "STAGE_CONFIRMED"

    # Content generation events
    INSPIRATION_REQUESTED = "INSPIRATION_REQUESTED"
    INSPIRATION_GENERATED = "INSPIRATION_GENERATED"
    CONCEPT_SELECTED = "CONCEPT_SELECTED"
    FEEDBACK_PROVIDED = "FEEDBACK_PROVIDED"

    # AI interaction events
    AI_GENERATION_STARTED = "AI_GENERATION_STARTED"
    AI_GENERATION_COMPLETED = "AI_GENERATION_COMPLETED"
    AI_GENERATION_FAILED = "AI_GENERATION_FAILED"

    # User interaction events
    USER_INPUT_REQUESTED = "USER_INPUT_REQUESTED"
    USER_INPUT_RECEIVED = "USER_INPUT_RECEIVED"
    USER_FEEDBACK_RECEIVED = "USER_FEEDBACK_RECEIVED"

    # Novel creation events
    NOVEL_CREATION_INITIATED = "NOVEL_CREATION_INITIATED"
    NOVEL_CREATED_FROM_GENESIS = "NOVEL_CREATED_FROM_GENESIS"


class GenesisCommandType(str, Enum):
    """创世流程命令类型枚举"""

    START_GENESIS = "START_GENESIS"
    SELECT_CONCEPT = "SELECT_CONCEPT"
    GENERATE_INSPIRATION = "GENERATE_INSPIRATION"
    PROVIDE_FEEDBACK = "PROVIDE_FEEDBACK"
    CONFIRM_STAGE = "CONFIRM_STAGE"
    NAVIGATE_TO_STAGE = "NAVIGATE_TO_STAGE"
    FINISH_GENESIS = "FINISH_GENESIS"
    ABANDON_GENESIS = "ABANDON_GENESIS"
    PAUSE_GENESIS = "PAUSE_GENESIS"
    RESUME_GENESIS = "RESUME_GENESIS"


# 任务和命令相关枚举
class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CommandStatus(str, Enum):
    """命令状态枚举"""

    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OutboxStatus(str, Enum):
    """事件发件箱状态枚举"""

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


# 世界观相关枚举
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
