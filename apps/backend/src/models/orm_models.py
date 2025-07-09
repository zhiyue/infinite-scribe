"""
SQLAlchemy ORM 模型定义

这些模型对应 PostgreSQL 数据库中的表结构
"""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base

# 导入枚举类型
from .db import (
    AgentType,
    ChapterStatus,
    CommandStatus,
    GenesisStage,
    GenesisStatus,
    HandleStatus,
    NovelStatus,
    OutboxStatus,
    TaskStatus,
    WorldviewEntryType,
)


# 核心实体表模型
class Novel(Base):
    """小说表 - 存储每个独立小说项目的核心元数据"""

    __tablename__ = "novels"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="小说唯一标识符，自动生成的UUID")
    title = Column(String(255), nullable=False, comment="小说标题，必填，最长255个字符")
    theme = Column(Text, comment='小说主题描述，如"科幻冒险"、"都市言情"等')
    writing_style = Column(Text, comment='写作风格描述，如"幽默诙谐"、"严肃写实"等')
    status = Column(
        Enum(NovelStatus), nullable=False, default=NovelStatus.GENESIS, comment="小说生成状态，使用novel_status枚举"
    )
    target_chapters = Column(Integer, nullable=False, default=0, comment="目标章节数，用户设定的计划章节总数")
    completed_chapters = Column(Integer, nullable=False, default=0, comment="已完成章节数，系统自动统计")
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间，带时区的时间戳"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最后更新时间，通过触发器自动维护",
    )

    # 关系
    chapters = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="novel", cascade="all, delete-orphan")
    worldview_entries = relationship("WorldviewEntry", back_populates="novel", cascade="all, delete-orphan")
    story_arcs = relationship("StoryArc", back_populates="novel", cascade="all, delete-orphan")
    genesis_sessions = relationship("GenesisSession", back_populates="novel")


class Chapter(Base):
    """章节元数据表 - 存储章节的元数据,与具体的版本内容分离"""

    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("novel_id", "chapter_number"),)

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="章节唯一标识符，自动生成的UUID")
    novel_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表，级联删除",
    )
    chapter_number = Column(Integer, nullable=False, comment="章节序号，从1开始递增，同一小说内唯一")
    title = Column(String(255), comment="章节标题，可选字段")
    status = Column(
        Enum(ChapterStatus), nullable=False, default=ChapterStatus.DRAFT, comment="章节当前状态，使用chapter_status枚举"
    )
    published_version_id = Column(
        PGUUID(as_uuid=True), comment="指向当前已发布版本的ID，外键将在chapter_versions表创建后添加"
    )
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="章节创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="章节最后更新时间",
    )

    # 关系
    novel = relationship("Novel", back_populates="chapters")
    versions = relationship("ChapterVersion", back_populates="chapter", foreign_keys="ChapterVersion.chapter_id")
    published_version = relationship("ChapterVersion", foreign_keys=[published_version_id], post_update=True)
    reviews = relationship("Review", back_populates="chapter", cascade="all, delete-orphan")


class ChapterVersion(Base):
    """章节版本表 - 存储一个章节的每一次具体内容的迭代版本,实现版本控制"""

    __tablename__ = "chapter_versions"
    __table_args__ = (UniqueConstraint("chapter_id", "version_number"),)

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="章节版本的唯一标识符")
    chapter_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的章节ID，外键关联chapters表",
    )
    version_number = Column(Integer, nullable=False, comment="版本号，从1开始递增，同一章节内唯一")
    content_url = Column(Text, nullable=False, comment="指向MinIO中该版本内容的URL")
    word_count = Column(Integer, comment="该版本的字数统计")
    created_by_agent_type = Column(Enum(AgentType), nullable=False, comment="创建此版本的AI智能体类型")
    change_reason = Column(Text, comment='修改原因说明，如"根据评论家意见修改"')
    parent_version_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("chapter_versions.id", ondelete="SET NULL"),
        comment="指向上一个版本的ID，形成版本链",
    )
    version_metadata = Column("metadata", JSONB, comment="存储与此版本相关的额外元数据，JSONB格式")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="版本创建时间")

    # 关系
    chapter = relationship("Chapter", back_populates="versions", foreign_keys=[chapter_id])
    parent_version = relationship("ChapterVersion", remote_side=[id])
    reviews = relationship("Review", back_populates="chapter_version", cascade="all, delete-orphan")


class Character(Base):
    """角色表 - 存储小说中所有角色的详细设定信息"""

    __tablename__ = "characters"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="角色唯一标识符，对应Neo4j中的app_id")
    novel_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表",
    )
    name = Column(String(255), nullable=False, comment="角色姓名，必填")
    role = Column(String(50), comment='角色定位，如"主角"、"反派"、"配角"等')
    description = Column(Text, comment="角色外观、特征等描述信息")
    background_story = Column(Text, comment="角色背景故事，包括身世、经历等")
    personality_traits = Column(ARRAY(Text), comment='性格特征数组，如["勇敢", "正直", "幽默"]')
    goals = Column(ARRAY(Text), comment='角色目标数组，如["寻找失散的妹妹", "成为最强剑士"]')
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="角色创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="角色信息最后更新时间",
    )

    # 关系
    novel = relationship("Novel", back_populates="characters")


class WorldviewEntry(Base):
    """世界观条目表 - 存储世界观中的所有设定条目,如地点、组织、物品等"""

    __tablename__ = "worldview_entries"
    __table_args__ = (UniqueConstraint("novel_id", "name", "entry_type"),)

    id = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="条目唯一标识符，与Neo4j图数据库中节点的app_id属性对应",
    )
    novel_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表",
    )
    entry_type = Column(Enum(WorldviewEntryType), nullable=False, comment="条目类型，使用worldview_entry_type枚举")
    name = Column(String(255), nullable=False, comment='条目名称，如"魔法学院"、"时空传送门"等，同一小说内按类型唯一')
    description = Column(Text, comment="条目详细描述，包含其特征、作用、历史等信息")
    tags = Column(ARRAY(Text), comment='标签数组，用于分类和快速检索，如["魔法", "禁地", "古代遗迹"]')
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="条目创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="条目最后更新时间",
    )

    # 关系
    novel = relationship("Novel", back_populates="worldview_entries")


class StoryArc(Base):
    """故事弧表 - 存储主要的情节线或故事阶段的规划"""

    __tablename__ = "story_arcs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="故事弧唯一标识符")
    novel_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属小说ID，外键关联novels表",
    )
    title = Column(String(255), nullable=False, comment='故事弧标题，如"主角觉醒篇"、"魔王讨伐篇"')
    summary = Column(Text, comment="故事弧概要，描述这条线索的主要内容和发展")
    start_chapter_number = Column(Integer, comment="故事弧开始的章节号")
    end_chapter_number = Column(Integer, comment="故事弧结束的章节号")
    status = Column(
        String(50), default="PLANNED", comment="故事弧状态，如PLANNED(已规划)、ACTIVE(进行中)、COMPLETED(已完成)"
    )
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="故事弧创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="故事弧最后更新时间",
    )

    # 关系
    novel = relationship("Novel", back_populates="story_arcs")


class Review(Base):
    """评审记录表 - 记录每一次对章节草稿的评审结果"""

    __tablename__ = "reviews"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="评审记录唯一标识符")
    chapter_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
        comment="被评审的章节ID，外键关联chapters表",
    )
    chapter_version_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("chapter_versions.id", ondelete="CASCADE"),
        nullable=False,
        comment="评审针对的具体章节版本ID，外键关联chapter_versions表",
    )
    agent_type = Column(Enum(AgentType), nullable=False, comment="执行评审的AI智能体类型")
    review_type = Column(String(50), nullable=False, comment="评审类型，如CRITIC(评论家审查)、FACT_CHECK(事实核查)")
    score = Column(Numeric(3, 1), comment="评分，范围0.0-10.0，保留一位小数")
    comment = Column(Text, comment="评审意见和建议的详细文本")
    is_consistent = Column(Boolean, comment="是否与小说设定一致，用于事实核查")
    issues_found = Column(ARRAY(Text), comment='发现的问题列表，如["时间线冲突", "角色性格不一致"]')
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="评审创建时间，不会更新"
    )

    # 关系
    chapter = relationship("Chapter", back_populates="reviews")
    chapter_version = relationship("ChapterVersion", back_populates="reviews")


# 创世流程相关表
class GenesisSession(Base):
    """创世会话表 - 作为创世流程的"状态快照",用于高效查询当前流程的状态"""

    __tablename__ = "genesis_sessions"
    __table_args__ = (
        CheckConstraint(
            """
            (current_stage = 'CONCEPT_SELECTION' AND status = 'IN_PROGRESS') OR
            (current_stage = 'STORY_CONCEPTION' AND status = 'IN_PROGRESS') OR
            (current_stage = 'WORLDVIEW' AND status = 'IN_PROGRESS') OR
            (current_stage = 'CHARACTERS' AND status = 'IN_PROGRESS') OR
            (current_stage = 'PLOT_OUTLINE' AND status = 'IN_PROGRESS') OR
            (current_stage = 'FINISHED' AND status IN ('COMPLETED', 'ABANDONED'))
            """,
            name="check_genesis_stage_progression",
        ),
        CheckConstraint(
            "(status != 'COMPLETED') OR (status = 'COMPLETED' AND novel_id IS NOT NULL)",
            name="check_completed_has_novel",
        ),
        Index("idx_genesis_sessions_user_id", "user_id"),
        Index("idx_genesis_sessions_status", "status"),
        Index("idx_genesis_sessions_current_stage", "current_stage"),
        Index("idx_genesis_sessions_novel_id", "novel_id"),
        Index("idx_genesis_sessions_user_status", "user_id", "status"),
        Index("idx_genesis_sessions_status_stage", "status", "current_stage"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="创世会话的唯一标识符")
    novel_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("novels.id", ondelete="SET NULL"),
        comment="流程完成后关联的小说ID，允许为空（流程未完成时）",
    )
    user_id = Column(PGUUID(as_uuid=True), comment="发起创世流程的用户ID，用于权限控制和用户关联")
    status = Column(
        Enum(GenesisStatus),
        nullable=False,
        default=GenesisStatus.IN_PROGRESS,
        comment="整个创世会话的状态，使用genesis_status枚举",
    )
    current_stage = Column(
        Enum(GenesisStage),
        nullable=False,
        default=GenesisStage.CONCEPT_SELECTION,
        comment="当前所处的业务阶段，使用genesis_stage枚举",
    )
    confirmed_data = Column(JSONB, comment="存储每个阶段已确认的最终数据，JSONB格式，包含各阶段的输出结果")
    version = Column(Integer, nullable=False, default=1, comment="乐观锁版本号，用于并发控制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创世会话创建时间")
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="创世会话最后更新时间",
    )

    # 关系
    novel = relationship("Novel", back_populates="genesis_sessions")


class ConceptTemplate(Base):
    """立意模板表 - 存储抽象的哲学立意供用户选择"""

    __tablename__ = "concept_templates"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="立意模板的唯一标识符")
    core_idea = Column(String(200), nullable=False, comment='核心抽象思想，如"知识与无知的深刻对立"')
    description = Column(String(800), nullable=False, comment="立意的深层含义阐述，不超过800字符")
    philosophical_depth = Column(String(1000), nullable=False, comment="哲学思辨的深度表达，探讨存在、认知、道德等层面")
    emotional_core = Column(String(500), nullable=False, comment="情感核心与内在冲突，描述人物可能面临的情感挑战")
    philosophical_category = Column(String(100), comment='哲学类别，如"存在主义"、"人道主义"、"理想主义"')
    thematic_tags = Column(
        JSONB, nullable=False, default=list, comment='主题标签，如["成长","选择","牺牲","真理"]，JSON数组格式'
    )
    complexity_level = Column(
        String(20), nullable=False, default="medium", comment="思辨复杂度：simple, medium, complex"
    )
    universal_appeal = Column(Boolean, nullable=False, default=True, comment="是否具有普遍意义，跨文化的普适性")
    cultural_specificity = Column(String(100), comment='文化特异性，如"东方哲学"、"西方哲学"、"普世价值"')
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用，用于管理可用的立意模板")
    created_by = Column(String(50), server_default="system", comment='创建者，如"system"、"admin"或具体用户')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


# 领域事件和架构机制表
class DomainEvent(Base):
    """领域事件表 - 存储所有业务领域事件,支持事件源架构"""

    __tablename__ = "domain_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键，用于保证事件顺序")
    event_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True, default=uuid4, comment="事件唯一标识符")
    correlation_id = Column(PGUUID(as_uuid=True), comment="关联ID，用于追踪同一业务流程中的相关事件")
    causation_id = Column(PGUUID(as_uuid=True), comment="因果链ID，表示引发此事件的上级事件")
    event_type = Column(Text, nullable=False, comment='事件类型，如"ChapterCreated"、"ReviewCompleted"')
    event_version = Column(Integer, nullable=False, default=1, comment="事件版本号，用于事件模式演化")
    aggregate_type = Column(Text, nullable=False, comment='聚合根类型，如"Novel"、"Chapter"')
    aggregate_id = Column(Text, nullable=False, comment="聚合根ID，标识具体的业务实体")
    payload = Column(JSONB, comment="事件数据载荷，包含事件的详细内容")
    event_metadata = Column("metadata", JSONB, comment="事件元数据，如用户ID、时间戳、来源等")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="事件创建时间，不可修改"
    )

    # 索引
    __table_args__ = (
        Index("idx_domain_events_aggregate", "aggregate_type", "aggregate_id"),
        Index("idx_domain_events_event_type", "event_type"),
        Index("idx_domain_events_created_at", "created_at"),
        Index("idx_domain_events_correlation_id", "correlation_id"),
        Index("idx_domain_events_causation_id", "causation_id"),
        Index("idx_domain_events_aggregate_type_time", "aggregate_type", "created_at"),
        Index("idx_domain_events_event_type_time", "event_type", "created_at"),
    )


class CommandInbox(Base):
    """命令收件箱表 - 接收和存储待处理的命令,用于CQRS架构的命令侧"""

    __tablename__ = "command_inbox"
    __table_args__ = (
        Index("idx_command_inbox_unique_pending_command", "session_id", "command_type", unique=True),
        UniqueConstraint("idempotency_key"),
        CheckConstraint("retry_count >= 0", name="check_retry_count_non_negative"),
        CheckConstraint(
            "(status != 'FAILED') OR (status = 'FAILED' AND error_message IS NOT NULL)",
            name="check_failed_has_error_message",
        ),
        Index("idx_command_inbox_session_id", "session_id"),
        Index("idx_command_inbox_status", "status"),
        Index("idx_command_inbox_command_type", "command_type"),
        Index("idx_command_inbox_created_at", "created_at"),
        Index("idx_command_inbox_session_status", "session_id", "status"),
        Index("idx_command_inbox_status_created", "status", "created_at"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="命令唯一标识符")
    session_id = Column(PGUUID(as_uuid=True), nullable=False, comment="会话ID，关联到genesis_sessions或其他业务会话")
    command_type = Column(Text, nullable=False, comment='命令类型，如"ConfirmStoryConception"、"GenerateWorldview"')
    idempotency_key = Column(Text, nullable=False, unique=True, comment="幂等键，确保同一命令不会被重复处理")
    payload = Column(JSONB, comment="命令载荷，包含命令执行所需的所有数据")
    status = Column(
        Enum(CommandStatus), nullable=False, default=CommandStatus.RECEIVED, comment="命令状态，使用command_status枚举"
    )
    error_message = Column(Text, comment="错误信息，当状态为FAILED时必填")
    retry_count = Column(Integer, nullable=False, default=0, comment="重试次数，用于失败重试机制")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="命令接收时间")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="最后更新时间"
    )

    # 关系
    async_tasks = relationship("AsyncTask", back_populates="command")


class AsyncTask(Base):
    """异步任务表 - 跟踪和管理系统中的所有异步任务执行"""

    __tablename__ = "async_tasks"
    __table_args__ = (
        CheckConstraint("progress >= 0.0 AND progress <= 100.0", name="check_progress_range"),
        CheckConstraint("retry_count >= 0 AND retry_count <= max_retries", name="check_retry_count_valid"),
        CheckConstraint("max_retries >= 0", name="check_max_retries_non_negative"),
        CheckConstraint(
            "(status NOT IN ('COMPLETED', 'FAILED')) OR (status IN ('COMPLETED', 'FAILED') AND completed_at IS NOT NULL)",
            name="check_completed_has_timestamp",
        ),
        CheckConstraint(
            "(status != 'RUNNING') OR (status = 'RUNNING' AND started_at IS NOT NULL)",
            name="check_running_has_started",
        ),
        CheckConstraint(
            "(status != 'FAILED') OR (status = 'FAILED' AND error_data IS NOT NULL)", name="check_failed_has_error"
        ),
        CheckConstraint(
            "(status != 'COMPLETED') OR (status = 'COMPLETED' AND result_data IS NOT NULL)",
            name="check_completed_has_result",
        ),
        Index("idx_async_tasks_status", "status"),
        Index("idx_async_tasks_task_type", "task_type"),
        Index("idx_async_tasks_created_at", "created_at"),
        Index("idx_async_tasks_command_id", "triggered_by_command_id"),
        Index("idx_async_tasks_status_type", "status", "task_type"),
        Index("idx_async_tasks_status_created", "status", "created_at"),
        Index("idx_async_tasks_type_created", "task_type", "created_at"),
        Index("idx_async_tasks_execution_node", "execution_node"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="任务唯一标识符")
    task_type = Column(Text, nullable=False, comment='任务类型，如"GenerateChapter"、"AnalyzeWorldview"')
    triggered_by_command_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("command_inbox.id", ondelete="SET NULL"),
        comment="触发此任务的命令ID，外键关联command_inbox表",
    )
    status = Column(
        Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING, comment="任务状态，使用task_status枚举"
    )
    progress = Column(Numeric(5, 2), nullable=False, default=Decimal("0.00"), comment="任务进度百分比，0.00-100.00")
    input_data = Column(JSONB, comment="任务输入数据，JSON格式")
    result_data = Column(JSONB, comment="任务执行结果，完成时必填")
    error_data = Column(JSONB, comment="错误信息详情，失败时必填")
    execution_node = Column(Text, comment="执行任务的节点标识，用于分布式任务调度")
    retry_count = Column(Integer, nullable=False, default=0, comment="当前重试次数")
    max_retries = Column(Integer, nullable=False, default=3, comment="最大重试次数，默认3次")
    started_at = Column(DateTime(timezone=True), comment="任务开始执行时间，状态为RUNNING时必填")
    completed_at = Column(DateTime(timezone=True), comment="任务完成时间，状态为COMPLETED或FAILED时必填")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="任务创建时间")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="最后更新时间"
    )

    # 关系
    command = relationship("CommandInbox", back_populates="async_tasks")


class EventOutbox(Base):
    """事件发件箱表 - 确保事件可靠发布到消息队列的事务性发件箱模式实现"""

    __tablename__ = "event_outbox"
    __table_args__ = (
        CheckConstraint("retry_count >= 0 AND retry_count <= max_retries", name="check_retry_count_valid"),
        CheckConstraint("max_retries >= 0", name="check_max_retries_non_negative"),
        CheckConstraint(
            "(status != 'SENT') OR (status = 'SENT' AND sent_at IS NOT NULL)", name="check_sent_has_timestamp"
        ),
        CheckConstraint("scheduled_at IS NULL OR scheduled_at >= created_at", name="check_scheduled_at_future"),
        Index("idx_event_outbox_status", "status"),
        Index("idx_event_outbox_topic", "topic"),
        Index("idx_event_outbox_created_at", "created_at"),
        Index("idx_event_outbox_pending_scheduled", "status", "scheduled_at"),
        Index("idx_event_outbox_retry_count", "retry_count"),
        Index("idx_event_outbox_topic_status", "topic", "status"),
        Index("idx_event_outbox_status_created", "status", "created_at"),
        Index("idx_event_outbox_key", "key"),
        Index("idx_event_outbox_partition_key", "partition_key"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="消息唯一标识符")
    topic = Column(Text, nullable=False, comment='消息主题/队列名称，如"novel.events"、"chapter.updates"')
    key = Column(Text, comment="消息键，用于消息分区和顺序保证")
    partition_key = Column(Text, comment="分区键，用于Kafka等消息系统的分区路由")
    payload = Column(JSONB, nullable=False, comment="消息载荷，包含事件的完整数据")
    headers = Column(JSONB, comment="消息头，包含元数据如事件类型、版本、追踪ID等")
    status = Column(
        Enum(OutboxStatus), nullable=False, default=OutboxStatus.PENDING, comment="消息状态，使用outbox_status枚举"
    )
    retry_count = Column(Integer, nullable=False, default=0, comment="当前重试次数")
    max_retries = Column(Integer, nullable=False, default=5, comment="最大重试次数，默认5次")
    last_error = Column(Text, comment="最后一次发送失败的错误信息")
    scheduled_at = Column(DateTime(timezone=True), comment="计划发送时间，用于延迟消息")
    sent_at = Column(DateTime(timezone=True), comment="实际发送成功时间，状态为SENT时必填")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="消息创建时间")


class FlowResumeHandle(Base):
    """工作流恢复句柄表 - 支持长时间运行的工作流暂停和恢复机制"""

    __tablename__ = "flow_resume_handles"
    __table_args__ = (
        Index("idx_flow_resume_handles_unique_correlation", "correlation_id", unique=True),
        CheckConstraint("timeout_seconds IS NULL OR timeout_seconds > 0", name="check_timeout_positive"),
        CheckConstraint("expires_at IS NULL OR expires_at > created_at", name="check_expires_after_created"),
        CheckConstraint(
            "(status != 'RESUMED') OR (status = 'RESUMED' AND resumed_at IS NOT NULL)",
            name="check_resumed_has_timestamp",
        ),
        CheckConstraint(
            "(status NOT IN ('PAUSED', 'RESUMED')) OR (status IN ('PAUSED', 'RESUMED') AND resume_handle IS NOT NULL)",
            name="check_paused_has_handle",
        ),
        Index("idx_flow_resume_handles_correlation_id", "correlation_id"),
        Index("idx_flow_resume_handles_status", "status"),
        Index("idx_flow_resume_handles_flow_run_id", "flow_run_id"),
        Index("idx_flow_resume_handles_expires_at", "expires_at"),
        Index("idx_flow_resume_handles_status_expires", "status", "expires_at"),
        Index("idx_flow_resume_handles_correlation_status", "correlation_id", "status"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4, comment="句柄唯一标识符")
    correlation_id = Column(Text, nullable=False, comment="关联ID，唯一标识一个可恢复的工作流实例")
    flow_run_id = Column(Text, comment="工作流运行ID，关联到具体的工作流执行实例")
    task_name = Column(Text, comment='暂停的任务名称，如"WaitForUserConfirmation"')
    resume_handle = Column(JSONB, nullable=False, comment="恢复句柄数据，包含恢复工作流所需的状态信息")
    status = Column(
        Enum(HandleStatus),
        nullable=False,
        default=HandleStatus.PENDING_PAUSE,
        comment="句柄状态，使用handle_status枚举",
    )
    resume_payload = Column(JSONB, comment="恢复时的载荷数据，包含用户输入或外部事件数据")
    timeout_seconds = Column(Integer, comment="超时时间（秒），超时后工作流将自动恢复或失败")
    context_data = Column(JSONB, comment="上下文数据，存储工作流暂停时的业务上下文")
    expires_at = Column(DateTime(timezone=True), comment="句柄过期时间，过期后不能再恢复")
    resumed_at = Column(DateTime(timezone=True), comment="实际恢复时间，状态为RESUMED时必填")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="句柄创建时间")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="最后更新时间"
    )
