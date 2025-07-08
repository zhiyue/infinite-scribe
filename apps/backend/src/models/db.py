"""
Database models for PostgreSQL tables

All models correspond to database tables and use snake_case field names
to match PostgreSQL conventions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, condecimal, model_validator


# ENUM 类型定义
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


# 核心实体表模型


class NovelModel(BaseDBModel):
    """小说表模型"""

    id: UUID
    title: str = Field(..., max_length=255, description="小说标题")
    theme: str | None = Field(None, description="小说主题")
    writing_style: str | None = Field(None, description="写作风格")
    status: NovelStatus = Field(default=NovelStatus.GENESIS, description="当前状态")
    target_chapters: int = Field(default=0, ge=0, description="目标章节数")
    completed_chapters: int = Field(default=0, ge=0, description="已完成章节数")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")

    @model_validator(mode="after")
    def validate_completed_chapters(self):
        """验证已完成章节数不能超过目标章节数"""
        if self.target_chapters is not None and self.completed_chapters > self.target_chapters:
            raise ValueError("已完成章节数不能超过目标章节数")
        return self


class ChapterModel(BaseDBModel):
    """章节表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    chapter_number: int = Field(..., ge=1, description="章节序号")
    title: str | None = Field(None, max_length=255, description="章节标题")
    status: ChapterStatus = Field(default=ChapterStatus.DRAFT, description="章节当前状态")
    published_version_id: UUID | None = Field(None, description="指向当前已发布版本的ID")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


class ChapterVersionModel(BaseDBModel):
    """章节版本表模型"""

    id: UUID
    chapter_id: UUID = Field(..., description="关联的章节ID")
    version_number: int = Field(..., ge=1, description="版本号, 从1开始递增")
    content_url: str = Field(..., description="指向Minio中该版本内容的URL")
    word_count: int | None = Field(None, ge=0, description="该版本的字数")
    created_by_agent_type: AgentType = Field(..., description="创建此版本的Agent类型")
    change_reason: str | None = Field(None, description="修改原因")
    parent_version_id: UUID | None = Field(None, description="指向上一个版本的ID")
    metadata: dict[str, Any] | None = Field(None, description="版本相关的额外元数据")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="版本创建时间")


class CharacterModel(BaseDBModel):
    """角色表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    name: str = Field(..., max_length=255, description="角色名称")
    role: str | None = Field(None, max_length=50, description="角色定位")
    description: str | None = Field(None, description="角色外貌、性格等简述")
    background_story: str | None = Field(None, description="角色背景故事")
    personality_traits: None | list[str] = Field(None, description="性格特点列表")
    goals: None | list[str] = Field(None, description="角色的主要目标列表")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


class WorldviewEntryModel(BaseDBModel):
    """世界观条目表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    entry_type: WorldviewEntryType = Field(..., description="条目类型")
    name: str = Field(..., max_length=255, description="条目名称")
    description: str | None = Field(None, description="详细描述")
    tags: None | list[str] = Field(None, description="标签, 用于分类和检索")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


class StoryArcModel(BaseDBModel):
    """故事弧表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    title: str = Field(..., max_length=255, description="故事弧标题")
    summary: str | None = Field(None, description="故事弧摘要")
    start_chapter_number: int | None = Field(None, ge=1, description="开始章节号")
    end_chapter_number: int | None = Field(None, ge=1, description="结束章节号")
    status: str = Field(default="PLANNED", max_length=50, description="状态")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")

    @model_validator(mode="after")
    def validate_chapter_numbers(self):
        """验证结束章节号不能小于开始章节号"""
        if (
            self.start_chapter_number is not None
            and self.end_chapter_number is not None
            and self.end_chapter_number < self.start_chapter_number
        ):
            raise ValueError("结束章节号不能小于开始章节号")
        return self


class ReviewModel(BaseDBModel):
    """评审记录表模型"""

    id: UUID
    chapter_id: UUID = Field(..., description="关联的章节ID")
    chapter_version_id: UUID = Field(..., description="评审针对的具体章节版本ID")
    agent_type: AgentType = Field(..., description="执行评审的Agent类型")
    review_type: str = Field(..., max_length=50, description="评审类型")
    score: Annotated[Decimal, condecimal(max_digits=3, decimal_places=1, ge=0, le=10)] | None = Field(
        None, description="评论家评分"
    )
    comment: str | None = Field(None, description="评论家评语")
    is_consistent: bool | None = Field(None, description="事实核查员判断是否一致")
    issues_found: None | list[str] = Field(None, description="事实核查员发现的问题列表")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="评审创建时间")


# 架构机制表模型


class DomainEventModel(BaseDBModel):
    """领域事件表模型"""

    id: int  # 自增序号, 保证严格的时间顺序
    event_id: UUID = Field(default_factory=lambda: __import__("uuid").uuid4(), description="事件的全局唯一标识符")
    correlation_id: UUID | None = Field(None, description="用于追踪一个完整的业务流程或请求链")
    causation_id: UUID | None = Field(None, description="指向触发此事件的上一个事件的event_id")
    event_type: str = Field(..., description="事件的唯一类型标识")
    event_version: int = Field(default=1, description="事件模型的版本号")
    aggregate_type: str = Field(..., description="聚合根类型")
    aggregate_id: str = Field(..., description="聚合根的ID")
    payload: dict[str, Any] | None = Field(None, description="事件的具体数据")
    metadata: dict[str, Any] | None = Field(None, description="附加元数据")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="事件创建时间")


class CommandInboxModel(BaseDBModel):
    """命令收件箱表模型"""

    id: UUID
    session_id: UUID = Field(..., description="关联的会话ID")
    command_type: str = Field(..., description="命令类型")
    idempotency_key: str = Field(..., description="用于防止重复的幂等键")
    payload: dict[str, Any] | None = Field(None, description="命令的参数")
    status: CommandStatus = Field(default=CommandStatus.RECEIVED, description="命令处理状态")
    error_message: str | None = Field(None, description="处理失败时的错误信息")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


class AsyncTaskModel(BaseDBModel):
    """异步任务表模型"""

    id: UUID
    task_type: str = Field(..., description="任务类型")
    triggered_by_command_id: UUID | None = Field(None, description="触发此任务的命令ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务执行状态")
    progress: Decimal = Field(default=Decimal("0.00"), description="任务进度(0.00 - 100.00)")
    input_data: dict[str, Any] | None = Field(None, description="任务的输入参数")
    result_data: dict[str, Any] | None = Field(None, description="任务成功后的结果")
    error_data: dict[str, Any] | None = Field(None, description="任务失败时的错误信息")
    execution_node: str | None = Field(None, description="执行此任务的节点或服务实例标识")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    started_at: datetime | None = Field(None, description="任务开始执行时间")
    completed_at: datetime | None = Field(None, description="任务完成时间")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


class EventOutboxModel(BaseDBModel):
    """事件发件箱表模型"""

    id: UUID
    topic: str = Field(..., description="目标Kafka主题")
    key: str | None = Field(None, description="Kafka消息的Key")
    partition_key: str | None = Field(None, description="分区键")
    payload: dict[str, Any] = Field(..., description="消息的完整内容")
    headers: dict[str, Any] | None = Field(None, description="消息头信息")
    status: OutboxStatus = Field(default=OutboxStatus.PENDING, description="消息发送状态")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    max_retries: int = Field(default=5, ge=0, description="最大重试次数")
    last_error: str | None = Field(None, description="最后一次发送失败的错误信息")
    scheduled_at: datetime | None = Field(None, description="计划发送时间")
    sent_at: datetime | None = Field(None, description="实际发送成功时间")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")


class FlowResumeHandleModel(BaseDBModel):
    """工作流恢复句柄表模型"""

    id: UUID
    correlation_id: str = Field(..., description="用于查找的关联ID")
    flow_run_id: str | None = Field(None, description="Prefect工作流运行ID")
    task_name: str | None = Field(None, description="暂停的任务名称")
    resume_handle: dict[str, Any] = Field(..., description="Prefect提供的用于恢复的完整JSON对象")
    status: HandleStatus = Field(default=HandleStatus.PENDING_PAUSE, description="回调句柄的状态")
    resume_payload: dict[str, Any] | None = Field(None, description="用于存储提前到达的恢复数据")
    timeout_seconds: int | None = Field(None, gt=0, description="句柄超时时间(秒)")
    context_data: dict[str, Any] | None = Field(None, description="额外的上下文信息")
    expires_at: datetime | None = Field(None, description="过期时间")
    resumed_at: datetime | None = Field(None, description="实际恢复时间")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


# 创世流程相关表模型


class ConceptTemplateModel(BaseDBModel):
    """立意模板表模型 - 存储抽象的哲学立意供用户选择"""

    id: UUID
    core_idea: str = Field(..., max_length=200, description="核心抽象思想,如'知识与无知的深刻对立'")
    description: str = Field(..., max_length=800, description="立意的深层含义阐述")

    # 哲学维度
    philosophical_depth: str = Field(..., max_length=1000, description="哲学思辨的深度表达")
    emotional_core: str = Field(..., max_length=500, description="情感核心与内在冲突")

    # 分类标签(抽象层面)
    philosophical_category: str | None = Field(
        None, max_length=100, description="哲学类别,如'存在主义','人道主义','理想主义'"
    )
    thematic_tags: list[str] = Field(default_factory=list, description="主题标签,如['成长','选择','牺牲','真理']")
    complexity_level: str = Field(
        default="medium", max_length=20, description="思辨复杂度,如'simple','medium','complex'"
    )

    # 适用性
    universal_appeal: bool = Field(default=True, description="是否具有普遍意义")
    cultural_specificity: str | None = Field(
        None, max_length=100, description="文化特异性,如'东方哲学','西方哲学','普世价值'"
    )

    # 元数据
    is_active: bool = Field(default=True, description="是否启用")
    created_by: str | None = Field(None, max_length=50, description="创建者,如'system','admin'")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


class GenesisSessionModel(BaseDBModel):
    """创世会话表模型"""

    id: UUID
    novel_id: UUID | None = Field(None, description="流程完成后关联的小说ID")
    user_id: UUID | None = Field(None, description="用户ID")
    status: GenesisStatus = Field(default=GenesisStatus.IN_PROGRESS, description="会话状态")
    current_stage: GenesisStage = Field(default=GenesisStage.CONCEPT_SELECTION, description="当前阶段")
    confirmed_data: dict[str, Any] | None = Field(None, description="存储每个阶段已确认的最终数据")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间")


# 导出所有模型类和枚举
__all__ = [
    # 枚举类型
    "AgentType",
    "CommandStatus",
    "TaskStatus",
    "OutboxStatus",
    "HandleStatus",
    "WorldviewEntryType",
    "NovelStatus",
    "ChapterStatus",
    "GenesisStatus",
    "GenesisStage",
    # 基础模型
    "BaseDBModel",
    # 核心实体模型
    "NovelModel",
    "ChapterModel",
    "ChapterVersionModel",
    "CharacterModel",
    "WorldviewEntryModel",
    "StoryArcModel",
    "ReviewModel",
    # 架构机制模型
    "DomainEventModel",
    "CommandInboxModel",
    "AsyncTaskModel",
    "EventOutboxModel",
    "FlowResumeHandleModel",
    # 创世流程模型
    "ConceptTemplateModel",
    "GenesisSessionModel",
    # 辅助函数
    "get_all_models",
    "get_core_entity_models",
    "get_tracking_models",
    "create_example_novel",
    "create_example_character",
    "create_example_worldview_entry",
    "create_example_concept_template",
    "create_example_genesis_session",
    "validate_model_data",
    # 常量
    "MODEL_RELATIONSHIPS",
]


# 辅助函数


def get_all_models() -> list[type[BaseDBModel]]:
    """获取所有数据库模型类列表"""
    return [
        # 核心实体模型
        NovelModel,
        ChapterModel,
        ChapterVersionModel,
        CharacterModel,
        WorldviewEntryModel,
        StoryArcModel,
        ReviewModel,
        # 架构机制模型
        DomainEventModel,
        CommandInboxModel,
        AsyncTaskModel,
        EventOutboxModel,
        FlowResumeHandleModel,
        # 创世流程模型
        ConceptTemplateModel,
        GenesisSessionModel,
    ]


def get_core_entity_models() -> list[type[BaseDBModel]]:
    """获取核心实体模型类列表(有外键约束的表)"""
    return [
        NovelModel,
        ChapterModel,
        ChapterVersionModel,
        CharacterModel,
        WorldviewEntryModel,
        StoryArcModel,
        ReviewModel,
        ConceptTemplateModel,
        GenesisSessionModel,
    ]


def get_tracking_models() -> list[type[BaseDBModel]]:
    """获取追踪模型类列表(无外键约束的表)"""
    return [
        DomainEventModel,
        CommandInboxModel,
        AsyncTaskModel,
        EventOutboxModel,
        FlowResumeHandleModel,
    ]


# 模型关系映射(用于理解表间关系)
MODEL_RELATIONSHIPS = {
    "NovelModel": {
        "children": [
            "ChapterModel",
            "CharacterModel",
            "WorldviewEntryModel",
            "StoryArcModel",
            "GenesisSessionModel",
        ],
        "foreign_keys": [],
    },
    "ChapterModel": {
        "children": ["ChapterVersionModel", "ReviewModel"],
        "foreign_keys": ["novel_id"],
    },
    "ChapterVersionModel": {
        "children": ["ReviewModel"],
        "foreign_keys": ["chapter_id", "parent_version_id"],
    },
    "CharacterModel": {
        "children": [],
        "foreign_keys": ["novel_id"],
    },
    "WorldviewEntryModel": {
        "children": [],
        "foreign_keys": ["novel_id"],
    },
    "StoryArcModel": {
        "children": [],
        "foreign_keys": ["novel_id"],
    },
    "ReviewModel": {
        "children": [],
        "foreign_keys": ["chapter_id", "chapter_version_id"],
    },
    "ConceptTemplateModel": {
        "children": [],
        "foreign_keys": [],
    },
    "GenesisSessionModel": {
        "children": [],
        "foreign_keys": ["novel_id"],
    },
    "CommandInboxModel": {
        "children": ["AsyncTaskModel"],
        "foreign_keys": ["session_id"],
    },
    "AsyncTaskModel": {
        "children": [],
        "foreign_keys": ["triggered_by_command_id"],
    },
}


# 示例用法和验证函数


def create_example_novel() -> dict:
    """创建小说模型的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "title": "无限抄写者的奇幻冒险",
        "theme": "奇幻冒险",
        "writing_style": "第三人称全知视角, 富有想象力的描述",
        "status": NovelStatus.GENESIS,
        "target_chapters": 20,
        "completed_chapters": 0,
    }


def create_example_character(novel_id: UUID | None = None) -> dict:
    """创建角色模型的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "novel_id": novel_id or uuid4(),
        "name": "艾拉·星语者",
        "role": "主角",
        "description": "拥有银色头发和蓝色眼睛的年轻法师",
        "background_story": "出生于偏远的法师村庄, 从小展现出强大的魔法天赋",
        "personality_traits": ["勇敢", "好奇", "有正义感", "有时冲动"],
        "goals": ["掌握古老的星辰魔法", "保护家乡不受邪恶势力侵害", "寻找失踪的导师"],
    }


def create_example_worldview_entry(novel_id: UUID | None = None) -> dict:
    """创建世界观条目的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "novel_id": novel_id or uuid4(),
        "entry_type": WorldviewEntryType.LOCATION,
        "name": "星辰学院",
        "description": "古老的魔法学院, 坐落在云雾缭绕的高山之上, 培养着来自各地的年轻法师",
        "tags": ["魔法学院", "教育机构", "神秘", "古老"],
    }


def create_example_concept_template() -> dict:
    """创建立意模板的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "core_idea": "知识与无知的深刻对立",
        "description": "当一个人越深入地探索真理，越发现自己的无知。真正的智慧不在于拥有答案，而在于提出正确的问题。这种认知的悖论构成了求知者永恒的困境。",
        "philosophical_depth": "基于苏格拉底的'我知道我无知'，探讨认知的边界和知识的本质。真正的智慧来自于对自己认知局限的深刻理解，以及对未知领域的敬畏与好奇。",
        "emotional_core": "求知者在追求真理的过程中体验到的挫折感、谦卑感，以及面对无限未知时的敬畏之情。智慧与愚昧的界限模糊产生的内心冲突。",
        "philosophical_category": "认知哲学",
        "thematic_tags": ["知识", "无知", "智慧", "真理", "认知", "学习", "谦卑"],
        "complexity_level": "medium",
        "universal_appeal": True,
        "cultural_specificity": "普世价值",
        "is_active": True,
        "created_by": "system",
    }


def create_example_genesis_session(novel_id: UUID | None = None) -> dict:
    """创建创世会话的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "novel_id": novel_id,
        "status": GenesisStatus.IN_PROGRESS,
        "current_stage": GenesisStage.CONCEPT_SELECTION,
        "confirmed_data": {"genre": "奇幻", "theme": "成长与冒险", "setting": "魔法世界"},
    }


def validate_model_data(model_class: type[BaseDBModel], data: dict) -> BaseDBModel:
    """验证给定数据是否符合模型要求, 返回验证后的模型实例"""
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"数据验证失败: {e}") from e
