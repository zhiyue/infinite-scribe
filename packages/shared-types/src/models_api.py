"""
API request/response models

These models are used for API validation and documentation.
They may differ from database models to provide better API interfaces.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .models_db import (
    ChapterStatus,
    GenesisStage,
    GenesisStatus,
    NovelStatus,
    WorkflowStatus,
)


class BaseAPIModel(BaseModel):
    """API模型基类"""

    model_config = {"validate_assignment": True, "use_enum_values": True}


# ============================================================================
# 通用响应模型
# ============================================================================


class APIError(BaseAPIModel):
    """API错误响应模型"""

    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: dict[str, Any] | None = Field(None, description="错误详情")


class APISuccess(BaseAPIModel):
    """API成功响应模型"""

    success: bool = Field(True, description="操作是否成功")
    message: str | None = Field(None, description="成功消息")


# ============================================================================
# 创世流程相关模型
# ============================================================================


class StartGenesisRequest(BaseAPIModel):
    """开始创世流程请求模型 - 生成抽象立意选项供用户选择"""

    user_id: UUID | None = Field(None, description="用户ID（可选，用于追踪和个性化推荐）")

    # 立意生成偏好（可选）
    concept_preferences: dict[str, Any] | None = Field(
        None,
        description="立意生成偏好设置（可选，用于影响AI生成的立意类型）",
        examples=[
            {
                "philosophical_categories": ["存在主义", "人道主义"],
                "complexity_level": "medium",
                "thematic_focus": ["成长", "选择", "友情"],
                "cultural_context": "普世价值",
                "avoid_themes": ["暴力", "悲剧"],
            }
        ],
    )

    # 生成配置
    concept_count: int = Field(default=10, ge=5, le=20, description="生成立意的数量", examples=[10])

    # 是否使用推荐算法
    use_personalization: bool = Field(
        default=True, description="是否基于用户历史偏好进行个性化推荐"
    )

    @field_validator("concept_preferences")
    @classmethod
    def validate_concept_preferences(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """验证立意偏好设置"""
        if v is None:
            return v

        # 验证偏好设置的基本结构
        allowed_keys = {
            "philosophical_categories",  # 哲学分类偏好
            "complexity_level",  # 思辨复杂度
            "thematic_focus",  # 主题聚焦
            "cultural_context",  # 文化背景
            "avoid_themes",  # 避免的主题
            "emotional_tone",  # 情感基调
        }

        # 移除不允许的键
        filtered_prefs = {k: v for k, v in v.items() if k in allowed_keys}

        # 验证特定字段
        if "philosophical_categories" in filtered_prefs:
            if isinstance(filtered_prefs["philosophical_categories"], list):
                if len(filtered_prefs["philosophical_categories"]) > 5:
                    raise ValueError("最多选择5个哲学分类")
            else:
                raise ValueError("philosophical_categories字段必须是列表")

        if "complexity_level" in filtered_prefs:
            allowed_levels = ["simple", "medium", "complex"]
            if filtered_prefs["complexity_level"] not in allowed_levels:
                raise ValueError(f"complexity_level必须是以下之一: {', '.join(allowed_levels)}")

        if "thematic_focus" in filtered_prefs:
            if isinstance(filtered_prefs["thematic_focus"], list):
                if len(filtered_prefs["thematic_focus"]) > 8:
                    raise ValueError("主题聚焦最多选择8个")
            else:
                raise ValueError("thematic_focus字段必须是列表")

        return filtered_prefs if filtered_prefs else None


class StartGenesisResponse(BaseAPIModel):
    """开始创世流程响应模型 - 返回AI生成的立意选项供用户选择"""

    session_id: UUID = Field(..., description="创世会话ID")
    novel_id: UUID = Field(..., description="小说ID")
    status: GenesisStatus = Field(..., description="会话状态")
    current_stage: GenesisStage = Field(..., description="当前阶段，应为CONCEPT_SELECTION")

    # AI生成的立意选项列表（抽象哲学思想）
    concept_options: list[dict[str, Any]] = Field(
        ...,
        description="AI生成的10个抽象立意选项",
        examples=[
            [
                {
                    "id": 1,
                    "core_idea": "知识与无知的深刻对立",
                    "description": "探讨知识如何改变一个人的命运，以及无知所带来的悲剧与痛苦",
                    "philosophical_depth": "当个体获得超越同辈的知识时，他将面临孤独与责任的双重考验",
                    "emotional_core": "理解与被理解之间的渴望与隔阂",
                },
                {
                    "id": 2,
                    "core_idea": "个体意志与集体命运的冲突",
                    "description": "个人的选择如何影响整个群体，以及个体在集体利益面前的道德抉择",
                    "philosophical_depth": "真正的英雄主义不在于力量，而在于在关键时刻做出正确选择的勇气",
                    "emotional_core": "为了他人的幸福而牺牲自我的内心挣扎与升华",
                },
                {
                    "id": 3,
                    "core_idea": "成长中的代价与收获",
                    "description": "探讨成长过程中必须失去什么才能获得什么，以及这种交换的意义",
                    "philosophical_depth": "真正的成熟来自于接受生活中无法改变的事实，同时保持改变可以改变事物的勇气",
                    "emotional_core": "告别童真时的不舍与对未来的既期待又恐惧",
                },
            ]
        ],
    )

    # 选择指引
    selection_guidance: str = Field(
        ...,
        description="选择立意的指导说明",
        examples=[
            "请从以下10个立意中选择1-3个您感兴趣的方向，您可以直接确认，也可以提供反馈让AI进一步调整这些立意"
        ],
    )

    # 下一步操作说明
    next_action: str = Field(
        ...,
        description="下一步操作说明",
        examples=["选择喜欢的立意，可选择直接确认或提供反馈进行迭代优化"],
    )


class SelectConceptsRequest(BaseAPIModel):
    """选择立意请求模型 - 用户选择立意并可提供反馈进行迭代"""

    session_id: UUID = Field(..., description="创世会话ID")
    selected_concept_ids: list[int] = Field(
        ..., min_items=1, max_items=3, description="选中的立意ID列表（1-3个）"
    )
    user_feedback: str | None = Field(
        None, max_length=1000, description="用户对选中立意的反馈和调整建议"
    )
    action: str = Field(
        ...,
        description="用户操作类型",
        pattern="^(iterate|confirm)$",
        examples=["iterate", "confirm"],
    )

    @field_validator("user_feedback")
    @classmethod
    def validate_user_feedback(cls, v: str | None, info) -> str | None:
        """验证用户反馈"""
        # 如果是iterate操作，通常需要反馈，但不强制要求
        if info.data.get("action") == "iterate" and not v:
            # 允许无反馈的迭代，AI可以自动优化
            pass
        return v.strip() if v else None


class SelectConceptsResponse(BaseAPIModel):
    """选择立意响应模型"""

    session_id: UUID = Field(..., description="会话ID")
    current_stage: GenesisStage = Field(..., description="当前阶段")

    # 如果是iterate操作，返回调整后的立意
    refined_concepts: list[dict[str, Any]] | None = Field(
        None,
        description="根据用户反馈调整后的立意",
        examples=[
            [
                {
                    "id": 1,
                    "core_idea": "知识与无知的深刻对立",
                    "description": "探讨知识如何改变一个人的命运，以及无知所带来的悲剧与痛苦",
                    "philosophical_depth": "当个体获得超越同辈的知识时，他将面临孤独与责任的双重考验",
                    "emotional_core": "理解与被理解之间的渴望与隔阂",
                    "adjustments_made": "根据您的反馈，强化了知识带来的孤独感这一维度",
                }
            ]
        ],
    )

    # 如果是confirm操作，返回具体的故事构思
    story_concept: dict[str, Any] | None = Field(
        None,
        description="基于确认立意生成的具体故事构思",
        examples=[
            {
                "confirmed_concepts": [
                    {
                        "core_idea": "知识与无知的深刻对立",
                        "description": "探讨知识如何改变一个人的命运，以及无知所带来的悲剧与痛苦",
                        "philosophical_depth": "当个体获得超越同辈的知识时，他将面临孤独与责任的双重考验",
                        "emotional_core": "理解与被理解之间的渴望与隔阂",
                    }
                ],
                "title_suggestions": ["魔法学院的异世界学者", "穿越者的魔法修行记"],
                "core_concept": "现代高中生穿越到异世界魔法学院，利用现代知识与魔法结合，在获得力量的同时体验知识带来的孤独与责任",
                "main_themes": ["知识的力量", "文化冲突与融合", "成长与自我发现"],
                "target_audience": "青少年及奇幻爱好者",
                "estimated_length": "中长篇（30-50万字）",
                "genre_suggestions": ["奇幻", "穿越", "校园"],
                "emotional_journey": "从迷茫困顿到获得知识，再到承担责任的心路历程",
            }
        ],
    )

    # 操作结果
    is_confirmed: bool = Field(..., description="立意是否已确认")
    next_stage: GenesisStage | None = Field(
        None, description="下一阶段（确认后进入STORY_CONCEPTION）"
    )
    next_action: str = Field(
        ...,
        description="下一步操作建议",
        examples=[
            "继续提供反馈优化立意",  # iterate情况
            "立意已确认，开始世界观设计",  # confirm情况
        ],
    )


class RefineStoryConceptRequest(BaseAPIModel):
    """优化故事构思请求模型 - 在STORY_CONCEPTION阶段使用"""

    session_id: UUID = Field(..., description="创世会话ID")
    user_feedback: str = Field(..., max_length=2000, description="用户对故事构思的反馈和调整建议")
    specific_adjustments: dict[str, str] | None = Field(
        None,
        description="针对特定字段的调整",
        examples=[
            {
                "title_suggestions": "希望标题更有诗意一些",
                "target_audience": "希望面向更成熟的读者群体",
                "main_themes": "想要加入更多关于友情的主题",
            }
        ],
    )


class RefineStoryConceptResponse(BaseAPIModel):
    """优化故事构思响应模型"""

    session_id: UUID = Field(..., description="会话ID")
    current_stage: GenesisStage = Field(..., description="当前阶段，应为STORY_CONCEPTION")

    # 优化后的故事构思
    refined_story_concept: dict[str, Any] = Field(
        ...,
        description="根据反馈优化后的故事构思",
        examples=[
            {
                "confirmed_concepts": [
                    {
                        "core_idea": "知识与无知的深刻对立",
                        "description": "探讨知识如何改变一个人的命运，以及无知所带来的悲剧与痛苦",
                        "philosophical_depth": "当个体获得超越同辈的知识时，他将面临孤独与责任的双重考验",
                        "emotional_core": "理解与被理解之间的渴望与隔阂",
                    }
                ],
                "title_suggestions": ["异世界的智者之路", "穿越时空的求知者"],
                "core_concept": "现代大学生穿越到异世界魔法学院，利用现代知识与魔法结合...",
                "main_themes": ["知识的力量", "友情与理解", "成长与自我发现"],
                "target_audience": "成年奇幻爱好者",
                "estimated_length": "长篇（50-80万字）",
                "genre_suggestions": ["奇幻", "穿越", "成长"],
                "emotional_journey": "从迷茫困顿到获得知识，再到在友情中找到归属感",
                "adjustments_made": "根据您的反馈，调整了标题风格，扩大了目标读者群体，增加了友情主题",
            }
        ],
    )

    # 操作建议
    needs_further_refinement: bool = Field(..., description="是否需要进一步优化")
    next_action: str = Field(..., description="下一步操作建议")


class GenesisStepRequest(BaseAPIModel):
    """创世步骤请求模型"""

    session_id: UUID = Field(..., description="创世会话ID")
    stage: GenesisStage = Field(..., description="请求处理的阶段")
    user_input: dict[str, Any] | None = Field(None, description="用户输入数据")
    feedback: str | None = Field(None, max_length=1000, description="用户对AI建议的反馈")


class GenesisStepResponse(BaseAPIModel):
    """创世步骤响应模型"""

    step_id: UUID = Field(..., description="步骤ID")
    session_id: UUID = Field(..., description="会话ID")
    stage: GenesisStage = Field(..., description="当前阶段")
    ai_suggestions: dict[str, Any] = Field(..., description="AI生成的建议")
    options: list[dict[str, Any]] | None = Field(None, description="可选择的选项")
    requires_confirmation: bool = Field(..., description="是否需要用户确认")
    next_stage: GenesisStage | None = Field(None, description="下一阶段")


class ConfirmGenesisStepRequest(BaseAPIModel):
    """确认创世步骤请求模型"""

    step_id: UUID = Field(..., description="步骤ID")
    confirmed: bool = Field(..., description="是否确认")
    modifications: dict[str, Any] | None = Field(None, description="用户修改内容")


class ConfirmGenesisStepResponse(BaseAPIModel):
    """确认创世步骤响应模型"""

    step_id: UUID = Field(..., description="步骤ID")
    confirmed: bool = Field(..., description="确认状态")
    next_stage: GenesisStage | None = Field(None, description="下一阶段")
    is_genesis_complete: bool = Field(..., description="创世流程是否完成")


class GetGenesisStatusResponse(BaseAPIModel):
    """获取创世状态响应模型"""

    session_id: UUID = Field(..., description="会话ID")
    novel_id: UUID = Field(..., description="小说ID")
    status: GenesisStatus = Field(..., description="会话状态")
    current_stage: GenesisStage = Field(..., description="当前阶段")
    progress_percentage: int = Field(..., ge=0, le=100, description="进度百分比")
    completed_stages: list[GenesisStage] = Field(..., description="已完成的阶段")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")


# ============================================================================
# 小说管理相关模型
# ============================================================================


class CreateNovelRequest(BaseAPIModel):
    """创建小说请求模型"""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="小说标题",
        examples=["魔法学院的异世界学者"],
    )
    theme: str | None = Field(
        None, max_length=500, description="小说主题", examples=["现代人穿越到魔法世界的成长故事"]
    )
    writing_style: str | None = Field(
        None, max_length=200, description="写作风格", examples=["轻松幽默，第一人称"]
    )
    target_chapters: int = Field(default=50, ge=1, le=1000, description="目标章节数", examples=[50])

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """验证小说标题"""
        if not v or not v.strip():
            raise ValueError("小说标题不能为空")

        # 去除多余空格
        title = " ".join(v.split())

        # 检查是否只是数字或特殊字符
        if not any(c.isalpha() for c in title):
            raise ValueError("小说标题必须包含文字内容")

        # 检查长度
        if len(title) < 2:
            raise ValueError("小说标题至少需要2个字符")

        return title

    @field_validator("target_chapters")
    @classmethod
    def validate_target_chapters(cls, v: int) -> int:
        """验证目标章节数"""
        if v < 1:
            raise ValueError("目标章节数必须大于0")
        if v > 1000:
            raise ValueError("目标章节数不能超过1000章")

        # 建议合理的章节数范围
        if v < 10:
            # 这是警告，不是错误，所以只记录但不抛异常
            pass

        return v


class CreateNovelResponse(BaseAPIModel):
    """创建小说响应模型"""

    novel_id: UUID = Field(..., description="小说ID")
    title: str = Field(..., description="小说标题")
    status: NovelStatus = Field(..., description="小说状态")
    created_at: datetime = Field(..., description="创建时间")


class NovelSummary(BaseAPIModel):
    """小说摘要模型（用于列表展示）"""

    id: UUID = Field(..., description="小说ID")
    title: str = Field(..., description="小说标题")
    theme: str | None = Field(None, description="小说主题")
    status: NovelStatus = Field(..., description="小说状态")
    target_chapters: int = Field(..., description="目标章节数")
    completed_chapters: int = Field(..., description="已完成章节数")
    progress_percentage: int = Field(..., ge=0, le=100, description="完成进度百分比")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")


class GetNovelsResponse(BaseAPIModel):
    """获取小说列表响应模型"""

    novels: list[NovelSummary] = Field(..., description="小说列表")
    total: int = Field(..., ge=0, description="总数量")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, description="每页大小")


class NovelDetail(BaseAPIModel):
    """小说详情模型"""

    id: UUID = Field(..., description="小说ID")
    title: str = Field(..., description="小说标题")
    theme: str | None = Field(None, description="小说主题")
    writing_style: str | None = Field(None, description="写作风格")
    status: NovelStatus = Field(..., description="小说状态")
    target_chapters: int = Field(..., description="目标章节数")
    completed_chapters: int = Field(..., description="已完成章节数")
    progress_percentage: int = Field(..., ge=0, le=100, description="完成进度百分比")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")

    # 额外的详情信息
    character_count: int = Field(..., ge=0, description="角色数量")
    worldview_entries_count: int = Field(..., ge=0, description="世界观条目数量")
    story_arcs_count: int = Field(..., ge=0, description="故事弧线数量")
    has_active_genesis: bool = Field(..., description="是否有活跃的创世会话")


class GetNovelDetailResponse(BaseAPIModel):
    """获取小说详情响应模型"""

    novel: NovelDetail = Field(..., description="小说详情")


class UpdateNovelRequest(BaseAPIModel):
    """更新小说请求模型"""

    title: str | None = Field(None, min_length=1, max_length=255, description="小说标题")
    theme: str | None = Field(None, max_length=500, description="小说主题")
    writing_style: str | None = Field(None, max_length=200, description="写作风格")
    target_chapters: int | None = Field(None, ge=1, le=1000, description="目标章节数")
    status: NovelStatus | None = Field(None, description="小说状态")


# ============================================================================
# 角色管理相关模型
# ============================================================================


class CreateCharacterRequest(BaseAPIModel):
    """创建角色请求模型"""

    novel_id: UUID = Field(..., description="所属小说ID")
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="角色名称",
        examples=["艾莉娅·斯塔克"],
    )
    role: str | None = Field(
        None, max_length=50, description="角色定位", examples=["主角", "反派", "配角"]
    )
    description: str | None = Field(
        None,
        max_length=2000,
        description="角色外貌、性格等简述",
        examples=["年轻的魔法师，有着银色的头发和蓝色的眼睛..."],
    )
    background_story: str | None = Field(None, max_length=5000, description="角色背景故事")
    personality_traits: list[str] | None = Field(
        None, description="性格特点列表", examples=[["勇敢", "固执", "善良"]]
    )
    goals: list[str] | None = Field(
        None, description="角色的主要目标列表", examples=[["拯救王国", "找到失踪的父亲"]]
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证角色名称"""
        if not v or not v.strip():
            raise ValueError("角色名称不能为空")

        # 去除多余空格
        name = " ".join(v.split())

        # 检查长度
        if len(name) < 1:
            raise ValueError("角色名称不能为空")

        # 检查是否包含字母或中文字符
        if not any(c.isalpha() or "\u4e00" <= c <= "\u9fff" for c in name):
            raise ValueError("角色名称必须包含有效的文字字符")

        return name

    @field_validator("personality_traits")
    @classmethod
    def validate_personality_traits(cls, v: list[str] | None) -> list[str] | None:
        """验证性格特点列表"""
        if v is None:
            return v

        if len(v) > 20:
            raise ValueError("性格特点不能超过20个")

        # 清理空白和重复项
        traits = []
        for trait in v:
            if isinstance(trait, str) and trait.strip():
                cleaned_trait = trait.strip()
                if cleaned_trait not in traits:  # 去重
                    traits.append(cleaned_trait)

        return traits if traits else None

    @field_validator("goals")
    @classmethod
    def validate_goals(cls, v: list[str] | None) -> list[str] | None:
        """验证目标列表"""
        if v is None:
            return v

        if len(v) > 10:
            raise ValueError("角色目标不能超过10个")

        # 清理空白和重复项
        goals = []
        for goal in v:
            if isinstance(goal, str) and goal.strip():
                cleaned_goal = goal.strip()
                if cleaned_goal not in goals:  # 去重
                    goals.append(cleaned_goal)

        return goals if goals else None


class CreateCharacterResponse(BaseAPIModel):
    """创建角色响应模型"""

    character_id: UUID = Field(..., description="角色ID")
    name: str = Field(..., description="角色名称")
    novel_id: UUID = Field(..., description="所属小说ID")
    created_at: datetime = Field(..., description="创建时间")


class CharacterSummary(BaseAPIModel):
    """角色摘要模型（用于列表展示）"""

    id: UUID = Field(..., description="角色ID")
    name: str = Field(..., description="角色名称")
    role: str | None = Field(None, description="角色定位")
    description: str | None = Field(None, description="角色简述")
    created_at: datetime = Field(..., description="创建时间")


class GetCharactersResponse(BaseAPIModel):
    """获取角色列表响应模型"""

    characters: list[CharacterSummary] = Field(..., description="角色列表")
    novel_id: UUID = Field(..., description="所属小说ID")
    total: int = Field(..., ge=0, description="总数量")


class UpdateCharacterRequest(BaseAPIModel):
    """更新角色请求模型"""

    name: str | None = Field(None, min_length=1, max_length=255, description="角色名称")
    role: str | None = Field(None, max_length=50, description="角色定位")
    description: str | None = Field(None, max_length=2000, description="角色描述")
    background_story: str | None = Field(None, max_length=5000, description="背景故事")
    personality_traits: list[str] | None = Field(None, description="性格特点列表")
    goals: list[str] | None = Field(None, description="目标列表")


# ============================================================================
# 章节生成相关模型
# ============================================================================


class GenerateChapterRequest(BaseAPIModel):
    """生成章节请求模型"""

    novel_id: UUID = Field(..., description="小说ID")
    chapter_title: str | None = Field(
        None, max_length=255, description="章节标题（可选，AI可生成）"
    )
    plot_guidance: str | None = Field(None, max_length=2000, description="剧情指导（可选）")
    target_word_count: int | None = Field(None, ge=500, le=10000, description="目标字数（可选）")


class GenerateChapterResponse(BaseAPIModel):
    """生成章节响应模型"""

    workflow_run_id: UUID = Field(..., description="工作流运行ID")
    chapter_id: UUID = Field(..., description="章节ID")
    estimated_completion_time: int = Field(..., ge=0, description="预估完成时间（秒）")
    status: WorkflowStatus = Field(..., description="工作流状态")


class ChapterSummary(BaseAPIModel):
    """章节摘要模型"""

    id: UUID = Field(..., description="章节ID")
    novel_id: UUID = Field(..., description="所属小说ID")
    title: str = Field(..., description="章节标题")
    status: ChapterStatus = Field(..., description="章节状态")
    word_count: int = Field(..., ge=0, description="字数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")


class GetChaptersResponse(BaseAPIModel):
    """获取章节列表响应模型"""

    chapters: list[ChapterSummary] = Field(..., description="章节列表")
    novel_id: UUID = Field(..., description="所属小说ID")
    total: int = Field(..., ge=0, description="总数量")


# ============================================================================
# 工作流状态相关模型
# ============================================================================


class WorkflowStatusResponse(BaseAPIModel):
    """工作流状态响应模型"""

    workflow_run_id: UUID = Field(..., description="工作流运行ID")
    status: WorkflowStatus = Field(..., description="工作流状态")
    progress_percentage: int = Field(..., ge=0, le=100, description="进度百分比")
    current_step: str | None = Field(None, description="当前执行步骤")
    estimated_completion_time: int | None = Field(None, ge=0, description="预估剩余时间（秒）")
    error_message: str | None = Field(None, description="错误消息（如果失败）")
    result_data: dict[str, Any] | None = Field(None, description="结果数据（如果完成）")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")


# ============================================================================
# 健康检查模型
# ============================================================================


class HealthCheckResponse(BaseAPIModel):
    """健康检查响应模型"""

    status: str = Field(..., description="服务状态", examples=["healthy"])
    timestamp: datetime = Field(..., description="检查时间")
    version: str = Field(..., description="API版本", examples=["1.0.0"])
    dependencies: dict[str, str] = Field(..., description="依赖服务状态")


# ============================================================================
# 分页和查询参数模型
# ============================================================================


class PaginationParams(BaseAPIModel):
    """分页参数模型"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")


class NovelQueryParams(PaginationParams):
    """小说查询参数模型"""

    status: NovelStatus | None = Field(None, description="按状态过滤")
    search: str | None = Field(None, max_length=255, description="搜索关键词（标题或主题）")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: str | None) -> str | None:
        """验证搜索关键词"""
        if v is None:
            return v

        search_term = v.strip()
        if not search_term:
            return None

        # 搜索词太短
        if len(search_term) < 2:
            raise ValueError("搜索关键词至少需要2个字符")

        return search_term

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """验证排序字段"""
        allowed_fields = [
            "created_at",
            "updated_at",
            "title",
            "status",
            "target_chapters",
            "completed_chapters",
        ]

        if v not in allowed_fields:
            raise ValueError(f"排序字段必须是以下之一: {', '.join(allowed_fields)}")

        return v


# ============================================================================
# 自定义错误类型和异常处理
# ============================================================================


class ValidationErrorDetail(BaseAPIModel):
    """验证错误详情模型"""

    field: str = Field(..., description="出错的字段名")
    message: str = Field(..., description="错误消息")
    invalid_value: Any = Field(..., description="无效的值")


class BusinessLogicError(BaseAPIModel):
    """业务逻辑错误模型"""

    error_code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    context: dict[str, Any] | None = Field(None, description="错误上下文")


class DetailedAPIError(APIError):
    """详细的API错误响应模型"""

    validation_errors: list[ValidationErrorDetail] | None = Field(
        None, description="字段验证错误列表"
    )
    business_errors: list[BusinessLogicError] | None = Field(None, description="业务逻辑错误列表")


# ============================================================================
# 便利函数和常量
# ============================================================================


# 常见错误消息常量
class ErrorMessages:
    """错误消息常量类"""

    # 通用错误
    REQUIRED_FIELD = "此字段为必填项"
    INVALID_UUID = "无效的UUID格式"
    INVALID_EMAIL = "无效的邮箱格式"

    # 创世流程错误
    GENESIS_ALREADY_EXISTS = "该小说已有进行中的创世会话"
    GENESIS_SESSION_NOT_FOUND = "创世会话不存在"
    GENESIS_STEP_NOT_FOUND = "创世步骤不存在"
    INVALID_GENESIS_STAGE = "无效的创世阶段"

    # 小说管理错误
    NOVEL_NOT_FOUND = "小说不存在"
    NOVEL_TITLE_EXISTS = "小说标题已存在"
    INVALID_NOVEL_STATUS = "无效的小说状态"

    # 角色管理错误
    CHARACTER_NOT_FOUND = "角色不存在"
    CHARACTER_NAME_EXISTS = "该小说中已存在同名角色"
    TOO_MANY_CHARACTERS = "角色数量已达上限"

    # 章节管理错误
    CHAPTER_NOT_FOUND = "章节不存在"
    CHAPTER_GENERATION_IN_PROGRESS = "章节正在生成中，请稍后"

    # 工作流错误
    WORKFLOW_NOT_FOUND = "工作流不存在"
    WORKFLOW_ALREADY_RUNNING = "工作流正在运行中"


# 成功消息常量
class SuccessMessages:
    """成功消息常量类"""

    # 创世流程
    GENESIS_STARTED = "创世流程已开始"
    GENESIS_STEP_COMPLETED = "创世步骤已完成"
    GENESIS_COMPLETED = "创世流程已完成"

    # 小说管理
    NOVEL_CREATED = "小说创建成功"
    NOVEL_UPDATED = "小说更新成功"
    NOVEL_DELETED = "小说删除成功"

    # 角色管理
    CHARACTER_CREATED = "角色创建成功"
    CHARACTER_UPDATED = "角色更新成功"
    CHARACTER_DELETED = "角色删除成功"

    # 章节管理
    CHAPTER_GENERATION_STARTED = "章节生成已开始"
    CHAPTER_PUBLISHED = "章节发布成功"
