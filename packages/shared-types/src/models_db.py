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


class ActivityStatus(str, Enum):
    """活动状态枚举"""

    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class EventStatus(str, Enum):
    """事件状态枚举"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


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

    CONCEPT_SELECTION = "CONCEPT_SELECTION"      # 立意选择与迭代阶段（选择抽象立意并优化）
    STORY_CONCEPTION = "STORY_CONCEPTION"        # 故事构思阶段（将立意转化为具体故事框架）
    WORLDVIEW = "WORLDVIEW"                      # 世界观创建阶段
    CHARACTERS = "CHARACTERS"                    # 角色设定阶段
    PLOT_OUTLINE = "PLOT_OUTLINE"               # 情节大纲阶段
    FINISHED = "FINISHED"                        # 完成阶段


class OperationType(str, Enum):
    """操作类型枚举"""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


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
            # 在初始化时如果没有提供 updated_at，则设置为当前时间
            data["updated_at"] = datetime.now(tz=UTC)
        return data

    def __setattr__(self, name, value):
        """重写属性设置以自动更新 updated_at"""
        super().__setattr__(name, value)
        # 如果设置的不是 updated_at 本身，且模型有 updated_at 字段，则自动更新
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
    created_by_agent_type: AgentType | None = Field(None, description="创建此记录的Agent类型")
    updated_by_agent_type: AgentType | None = Field(None, description="最后更新此记录的Agent类型")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )

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
    created_by_agent_type: AgentType | None = Field(None, description="创建此记录的Agent类型")
    updated_by_agent_type: AgentType | None = Field(None, description="最后更新此记录的Agent类型")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


class ChapterVersionModel(BaseDBModel):
    """章节版本表模型"""

    id: UUID
    chapter_id: UUID = Field(..., description="关联的章节ID")
    version_number: int = Field(..., ge=1, description="版本号，从1开始递增")
    content_url: str = Field(..., description="指向Minio中该版本内容的URL")
    word_count: int | None = Field(None, ge=0, description="该版本的字数")
    created_by_agent_type: AgentType = Field(..., description="创建此版本的Agent类型")
    change_reason: str | None = Field(None, description="修改原因")
    parent_version_id: UUID | None = Field(None, description="指向上一个版本的ID")
    metadata: dict[str, Any] | None = Field(None, description="版本相关的额外元数据")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="版本创建时间"
    )


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
    created_by_agent_type: AgentType | None = Field(None, description="创建此记录的Agent类型")
    updated_by_agent_type: AgentType | None = Field(None, description="最后更新此记录的Agent类型")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


class WorldviewEntryModel(BaseDBModel):
    """世界观条目表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说的ID")
    entry_type: str = Field(..., max_length=50, description="条目类型")
    name: str = Field(..., max_length=255, description="条目名称")
    description: str | None = Field(None, description="详细描述")
    tags: None | list[str] = Field(None, description="标签，用于分类和检索")
    version: int = Field(default=1, ge=1, description="乐观锁版本号")
    created_by_agent_type: AgentType | None = Field(None, description="创建此记录的Agent类型")
    updated_by_agent_type: AgentType | None = Field(None, description="最后更新此记录的Agent类型")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


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
    created_by_agent_type: AgentType | None = Field(None, description="创建此记录的Agent类型")
    updated_by_agent_type: AgentType | None = Field(None, description="最后更新此记录的Agent类型")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )

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
    workflow_run_id: UUID | None = Field(None, description="关联的工作流运行ID")
    agent_type: AgentType = Field(..., description="执行评审的Agent类型")
    review_type: str = Field(..., max_length=50, description="评审类型")
    score: Annotated[Decimal, condecimal(max_digits=3, decimal_places=1, ge=0, le=10)] | None = (
        Field(None, description="评论家评分")
    )
    comment: str | None = Field(None, description="评论家评语")
    is_consistent: bool | None = Field(None, description="事实核查员判断是否一致")
    issues_found: None | list[str] = Field(None, description="事实核查员发现的问题列表")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="评审创建时间"
    )


# 中间产物表模型


class OutlineModel(BaseDBModel):
    """大纲表模型"""

    id: UUID
    chapter_id: UUID = Field(..., description="关联的章节ID")
    created_by_agent_type: AgentType | None = Field(None, description="创建此大纲的Agent类型")
    version: int = Field(default=1, ge=1, description="大纲版本号")
    content: str = Field(..., description="大纲文本内容")
    content_url: str | None = Field(None, description="指向Minio中存储的大纲文件URL")
    metadata: dict[str, Any] | None = Field(None, description="额外的结构化元数据")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )


class SceneCardModel(BaseDBModel):
    """场景卡表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说ID")
    chapter_id: UUID = Field(..., description="所属章节ID")
    outline_id: UUID = Field(..., description="关联的大纲ID")
    created_by_agent_type: AgentType | None = Field(None, description="创建此场景卡的Agent类型")
    scene_number: int = Field(..., ge=1, description="场景在章节内的序号")
    pov_character_id: UUID | None = Field(None, description="视角角色ID")
    content: dict[str, Any] = Field(..., description="场景的详细设计")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )


class CharacterInteractionModel(BaseDBModel):
    """角色互动表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="所属小说ID")
    chapter_id: UUID = Field(..., description="所属章节ID")
    scene_card_id: UUID = Field(..., description="关联的场景卡ID")
    created_by_agent_type: AgentType | None = Field(None, description="创建此互动的Agent类型")
    interaction_type: str | None = Field(None, max_length=50, description="互动类型")
    content: dict[str, Any] = Field(..., description="互动的详细内容")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )


# 追踪与配置表模型 (无外键)


class WorkflowRunModel(BaseDBModel):
    """工作流运行表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="关联的小说ID")
    workflow_type: str = Field(..., max_length=100, description="工作流类型")
    status: WorkflowStatus = Field(..., description="工作流当前状态")
    parameters: dict[str, Any] | None = Field(None, description="启动工作流时传入的参数")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="开始时间"
    )
    completed_at: datetime | None = Field(None, description="完成时间")
    error_details: dict[str, Any] | None = Field(None, description="错误详情")


class AgentActivityModel(BaseDBModel):
    """Agent活动表模型（分区表）"""

    id: UUID
    workflow_run_id: UUID | None = Field(None, description="关联的工作流运行ID")
    novel_id: UUID = Field(..., description="关联的小说ID")
    target_entity_id: UUID | None = Field(None, description="活动操作的目标实体ID")
    target_entity_type: str | None = Field(None, max_length=50, description="目标实体类型")
    agent_type: AgentType | None = Field(None, description="执行活动的Agent类型")
    activity_type: str = Field(..., max_length=100, description="活动类型")
    status: ActivityStatus = Field(..., description="活动状态")
    input_data: dict[str, Any] | None = Field(None, description="活动的输入数据摘要")
    output_data: dict[str, Any] | None = Field(None, description="活动的输出数据摘要")
    error_details: dict[str, Any] | None = Field(None, description="错误详情")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="开始时间"
    )
    completed_at: datetime | None = Field(None, description="完成时间")
    # duration_seconds: 计算字段，由数据库生成
    llm_tokens_used: int | None = Field(None, ge=0, description="调用LLM消耗的Token数")
    llm_cost_estimate: (
        Annotated[Decimal, condecimal(max_digits=10, decimal_places=6, ge=0)] | None
    ) = Field(None, description="调用LLM的估算成本")
    retry_count: int = Field(default=0, ge=0, description="重试次数")


class EventModel(BaseDBModel):
    """事件表模型"""

    id: UUID
    event_type: str = Field(..., max_length=100, description="事件类型")
    novel_id: UUID | None = Field(None, description="关联的小说ID")
    workflow_run_id: UUID | None = Field(None, description="关联的工作流运行ID")
    payload: dict[str, Any] = Field(..., description="事件的完整载荷")
    status: EventStatus = Field(default=EventStatus.PENDING, description="事件处理状态")
    processed_by_agent_type: AgentType | None = Field(None, description="处理此事件的Agent类型")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="事件创建时间"
    )
    processed_at: datetime | None = Field(None, description="事件处理完成时间")
    error_details: dict[str, Any] | None = Field(None, description="错误详情")


class AgentConfigurationModel(BaseDBModel):
    """Agent配置表模型"""

    id: UUID
    novel_id: UUID | None = Field(None, description="关联的小说ID，NULL表示全局配置")
    agent_type: AgentType | None = Field(None, description="配置作用的Agent类型")
    config_key: str = Field(..., max_length=255, description="配置项名称")
    config_value: dict[str, Any] | str | int | float = Field(..., description="配置项的值")
    is_active: bool = Field(default=True, description="是否启用此配置")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


# 创世流程相关表模型


class ConceptTemplateModel(BaseDBModel):
    """立意模板表模型 - 存储抽象的哲学立意供用户选择"""

    id: UUID
    core_idea: str = Field(..., max_length=200, description="核心抽象思想，如'知识与无知的深刻对立'")
    description: str = Field(..., max_length=800, description="立意的深层含义阐述")
    
    # 哲学维度
    philosophical_depth: str = Field(..., max_length=1000, description="哲学思辨的深度表达")
    emotional_core: str = Field(..., max_length=500, description="情感核心与内在冲突")
    
    # 分类标签（抽象层面）
    philosophical_category: str | None = Field(None, max_length=100, description="哲学类别，如'存在主义','人道主义','理想主义'")
    thematic_tags: list[str] = Field(default_factory=list, description="主题标签，如['成长','选择','牺牲','真理']")
    complexity_level: str = Field(default="medium", max_length=20, description="思辨复杂度，如'simple','medium','complex'")
    
    # 适用性
    universal_appeal: bool = Field(default=True, description="是否具有普遍意义")
    cultural_specificity: str | None = Field(None, max_length=100, description="文化特异性，如'东方哲学','西方哲学','普世价值'")
    
    # 使用统计
    usage_count: int = Field(default=0, ge=0, description="被选择使用的次数")
    rating_sum: int = Field(default=0, ge=0, description="用户评分总和")
    rating_count: int = Field(default=0, ge=0, description="评分人数")
    
    # 元数据
    is_active: bool = Field(default=True, description="是否启用")
    created_by: str | None = Field(None, max_length=50, description="创建者，如'system','admin'")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )

    @property
    def average_rating(self) -> float | None:
        """计算平均评分"""
        if self.rating_count == 0:
            return None
        return self.rating_sum / self.rating_count


class GenesisSessionModel(BaseDBModel):
    """创世会话表模型"""

    id: UUID
    novel_id: UUID = Field(..., description="关联的小说ID")
    user_id: UUID | None = Field(None, description="用户ID")
    status: GenesisStatus = Field(default=GenesisStatus.IN_PROGRESS, description="会话状态")
    current_stage: GenesisStage = Field(default=GenesisStage.CONCEPT_SELECTION, description="当前阶段")
    initial_user_input: dict[str, Any] | None = Field(None, description="初始用户输入")
    final_settings: dict[str, Any] | None = Field(None, description="最终设置")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="最后更新时间"
    )


class GenesisStepModel(BaseDBModel):
    """创世步骤表模型"""

    id: UUID
    session_id: UUID = Field(..., description="所属会话ID")
    stage: GenesisStage = Field(..., description="所属阶段")
    iteration_count: int = Field(..., ge=1, description="迭代次数")
    ai_prompt: str | None = Field(None, description="AI提示词")
    ai_output: dict[str, Any] = Field(..., description="AI输出")
    user_feedback: str | None = Field(None, description="用户反馈")
    is_confirmed: bool = Field(default=False, description="是否已确认")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="创建时间"
    )


# 审计日志表模型（可选）


class AuditLogModel(BaseDBModel):
    """审计日志表模型"""

    id: UUID
    table_name: str = Field(..., max_length=63, description="发生变更的表名")
    record_id: UUID = Field(..., description="发生变更的记录ID")
    operation: OperationType = Field(..., description="操作类型")
    changed_by_agent_type: AgentType | None = Field(None, description="执行变更的Agent类型")
    changed_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), description="变更发生时间"
    )
    old_values: dict[str, Any] | None = Field(None, description="旧值")
    new_values: dict[str, Any] | None = Field(None, description="新值")


# 导出所有模型类和枚举
__all__ = [
    # 枚举类型
    "AgentType",
    "ActivityStatus",
    "WorkflowStatus",
    "EventStatus",
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
    # 中间产物模型
    "OutlineModel",
    "SceneCardModel",
    "CharacterInteractionModel",
    # 追踪与配置模型
    "WorkflowRunModel",
    "AgentActivityModel",
    "EventModel",
    "AgentConfigurationModel",
    # 创世流程模型
    "GenesisSessionModel",
    "GenesisStepModel",
    # 审计日志模型
    "AuditLogModel",
    # 辅助函数
    "get_all_models",
    "get_core_entity_models",
    "get_tracking_models",
    "create_example_novel",
    "create_example_character",
    "create_example_worldview_entry",
    "create_example_genesis_session",
    "validate_model_data",
    # 常量
    "MODEL_RELATIONSHIPS",
]


# 辅助函数


def get_all_models() -> list[type[BaseDBModel]]:
    """获取所有数据库模型类列表"""
    return [
        NovelModel,
        ChapterModel,
        ChapterVersionModel,
        CharacterModel,
        WorldviewEntryModel,
        StoryArcModel,
        ReviewModel,
        OutlineModel,
        SceneCardModel,
        CharacterInteractionModel,
        WorkflowRunModel,
        AgentActivityModel,
        EventModel,
        AgentConfigurationModel,
        GenesisSessionModel,
        GenesisStepModel,
        AuditLogModel,
    ]


def get_core_entity_models() -> list[type[BaseDBModel]]:
    """获取核心实体模型类列表（有外键约束的表）"""
    return [
        NovelModel,
        ChapterModel,
        ChapterVersionModel,
        CharacterModel,
        WorldviewEntryModel,
        StoryArcModel,
        ReviewModel,
        OutlineModel,
        SceneCardModel,
        CharacterInteractionModel,
        GenesisSessionModel,
        GenesisStepModel,
    ]


def get_tracking_models() -> list[type[BaseDBModel]]:
    """获取追踪模型类列表（无外键约束的表）"""
    return [
        WorkflowRunModel,
        AgentActivityModel,
        EventModel,
        AgentConfigurationModel,
        AuditLogModel,
    ]


# 模型关系映射（用于理解表间关系）
MODEL_RELATIONSHIPS = {
    "NovelModel": {
        "children": [
            "ChapterModel",
            "CharacterModel",
            "WorldviewEntryModel",
            "StoryArcModel",
            "GenesisSessionModel",
            "SceneCardModel",
            "CharacterInteractionModel",
        ],
        "foreign_keys": [],
    },
    "ChapterModel": {
        "children": ["ChapterVersionModel", "OutlineModel", "SceneCardModel"],
        "foreign_keys": ["novel_id"],
    },
    "ChapterVersionModel": {
        "children": ["ReviewModel"],
        "foreign_keys": ["chapter_id", "parent_version_id"],
    },
    "GenesisSessionModel": {"children": ["GenesisStepModel"], "foreign_keys": ["novel_id"]},
    "GenesisStepModel": {"children": [], "foreign_keys": ["session_id"]},
    "OutlineModel": {"children": ["SceneCardModel"], "foreign_keys": ["chapter_id"]},
    "SceneCardModel": {
        "children": ["CharacterInteractionModel"],
        "foreign_keys": ["novel_id", "chapter_id", "outline_id", "pov_character_id"],
    },
    "CharacterInteractionModel": {
        "children": [],
        "foreign_keys": ["novel_id", "chapter_id", "scene_card_id"],
    },
    "ReviewModel": {"children": [], "foreign_keys": ["chapter_id", "chapter_version_id"]},
}


# 示例用法和验证函数


def create_example_novel() -> dict:
    """创建小说模型的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "title": "无限抄写者的奇幻冒险",
        "theme": "奇幻冒险",
        "writing_style": "第三人称全知视角，富有想象力的描述",  # noqa: RUF001
        "status": NovelStatus.GENESIS,
        "target_chapters": 20,
        "completed_chapters": 0,
        "created_by_agent_type": AgentType.WORLDSMITH,
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
        "background_story": "出生于偏远的法师村庄，从小展现出强大的魔法天赋",
        "personality_traits": ["勇敢", "好奇", "有正义感", "有时冲动"],
        "goals": ["掌握古老的星辰魔法", "保护家乡不受邪恶势力侵害", "寻找失踪的导师"],
        "created_by_agent_type": AgentType.CHARACTER_EXPERT,
    }


def create_example_worldview_entry(novel_id: UUID | None = None) -> dict:
    """创建世界观条目的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "novel_id": novel_id or uuid4(),
        "entry_type": "LOCATION",
        "name": "星辰学院",
        "description": "古老的魔法学院，坐落在云雾缭绕的高山之上，培养着来自各地的年轻法师",
        "tags": ["魔法学院", "教育机构", "神秘", "古老"],
        "created_by_agent_type": AgentType.WORLDBUILDER,
    }


def create_example_genesis_session(novel_id: UUID | None = None) -> dict:
    """创建创世会话的示例数据"""
    from uuid import uuid4

    return {
        "id": uuid4(),
        "novel_id": novel_id or uuid4(),
        "status": GenesisStatus.IN_PROGRESS,
        "current_stage": GenesisStage.CONCEPT_SELECTION,
        "initial_user_input": {"genre": "奇幻", "theme": "成长与冒险", "setting": "魔法世界"},
    }


def validate_model_data(model_class: type[BaseDBModel], data: dict) -> BaseDBModel:
    """验证给定数据是否符合模型要求，返回验证后的模型实例"""
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"数据验证失败: {e}") from e
