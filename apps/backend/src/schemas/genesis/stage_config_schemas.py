"""Genesis stage configuration schemas and utilities."""

from typing import Any

from pydantic import BaseModel, Field

from ..enums import GenesisStage


class InitialPromptConfig(BaseModel):
    """初始提示阶段配置"""

    genre: str = Field(..., title="小说类型", description="选择小说的基本类型，如玄幻、都市、武侠等")
    style: str = Field(..., title="写作风格", description="选择叙述视角和写作风格，如第一人称、第三人称等")
    target_word_count: int = Field(..., title="目标字数", description="预期完成的小说总字数", ge=10000, le=1000000)
    special_requirements: list[str] = Field(default_factory=list, title="特殊要求", description="对创作的特殊要求或限制条件")

    class Config:
        json_schema_extra = {
            "title": "初始灵感配置",
            "description": "设定小说的基本信息和创作方向",
            "example": {
                "genre": "玄幻",
                "style": "第三人称",
                "target_word_count": 100000,
                "special_requirements": ["融入中国传统文化元素", "避免过于血腥的情节", "加入轻松幽默的元素"],
            }
        }


class WorldviewConfig(BaseModel):
    """世界观阶段配置"""

    time_period: str = Field(..., title="时代背景", description="故事发生的时代，如古代、现代、未来等")
    geography_type: str = Field(..., title="地理环境", description="故事世界的地理特征，如大陆、星球、岛屿等")
    tech_magic_level: str = Field(..., title="科技魔法水平", description="世界的科技发展水平或魔法系统强度")
    social_structure: str = Field(..., title="社会结构", description="社会制度和政治体系，如封建制、共和制等")
    power_system: str | None = Field(None, title="力量体系", description="世界中的特殊力量系统，如修真、魔法、异能等")

    class Config:
        json_schema_extra = {
            "title": "世界观配置",
            "description": "构建故事世界的背景设定和基本规则",
            "example": {
                "time_period": "古代",
                "geography_type": "大陆",
                "tech_magic_level": "高魔法",
                "social_structure": "封建制",
                "power_system": "修真等级",
            }
        }


class CharactersConfig(BaseModel):
    """角色阶段配置"""

    protagonist_count: int = Field(..., title="主角数量", description="故事的主角人数，建议1-3人", ge=1, le=5)
    relationship_complexity: str = Field(..., title="角色关系复杂度", description="角色间关系的复杂程度，如简单、中等、复杂")
    personality_preferences: list[str] = Field(..., title="性格偏好", description="希望角色具备的性格特征")
    include_villains: bool = Field(True, title="包含反派", description="是否在故事中设置反派角色")

    class Config:
        json_schema_extra = {
            "title": "角色配置",
            "description": "定义主要角色的特征和关系设定",
            "example": {
                "protagonist_count": 1,
                "relationship_complexity": "中等",
                "personality_preferences": ["坚韧", "聪明", "善良"],
                "include_villains": True,
            }
        }


class PlotOutlineConfig(BaseModel):
    """情节大纲阶段配置"""

    chapter_count_preference: int = Field(..., title="章节数量", description="预期的章节总数，建议20-50章", ge=5, le=100)
    plot_complexity: str = Field(..., title="情节复杂度", description="故事情节的复杂程度，如简单、中等、复杂")
    conflict_types: list[str] = Field(..., title="冲突类型", description="故事中包含的主要冲突类型")
    pacing_preference: str = Field("中等", title="节奏偏好", description="故事发展的节奏快慢，如缓慢、中等、快速")

    class Config:
        json_schema_extra = {
            "title": "剧情大纲配置",
            "description": "规划整体故事结构和发展脉络",
            "example": {
                "chapter_count_preference": 30,
                "plot_complexity": "中等",
                "conflict_types": ["内心冲突", "人际冲突", "社会冲突"],
                "pacing_preference": "中等",
            }
        }


# 联合类型定义
StageConfigUnion = InitialPromptConfig | WorldviewConfig | CharactersConfig | PlotOutlineConfig


def get_stage_config_schema(
    stage: GenesisStage,
) -> type[InitialPromptConfig | WorldviewConfig | CharactersConfig | PlotOutlineConfig]:
    """根据阶段类型返回对应的配置Schema

    Args:
        stage: Genesis阶段类型

    Returns:
        对应的配置Schema类

    Raises:
        ValueError: 当阶段类型不支持时
    """
    mapping = {
        GenesisStage.INITIAL_PROMPT: InitialPromptConfig,
        GenesisStage.WORLDVIEW: WorldviewConfig,
        GenesisStage.CHARACTERS: CharactersConfig,
        GenesisStage.PLOT_OUTLINE: PlotOutlineConfig,
    }

    if stage not in mapping:
        raise ValueError(f"Unsupported stage type: {stage}")

    return mapping[stage]  # type: ignore[return-value]


def validate_stage_config(stage: GenesisStage, config: dict[str, Any]) -> BaseModel:
    """验证阶段配置

    Args:
        stage: Genesis阶段类型
        config: 配置字典

    Returns:
        验证后的配置对象

    Raises:
        ValidationError: 当配置不符合Schema要求时
        ValueError: 当阶段类型不支持时
    """
    schema_class = get_stage_config_schema(stage)
    return schema_class(**config)


def get_stage_config_example(stage: GenesisStage) -> dict[str, Any]:
    """获取指定阶段的示例配置字典。

    优先返回 JSON Schema 中配置的示例，若未提供则回退到模型默认值。
    """

    schema_class = get_stage_config_schema(stage)
    schema_dict = schema_class.model_json_schema()

    example = schema_dict.get("example")
    if isinstance(example, dict):
        return example

    examples = schema_dict.get("examples")
    if isinstance(examples, list):
        for item in examples:
            if isinstance(item, dict):
                return item

    return schema_class.model_construct().model_dump()


def get_all_stage_config_schemas() -> dict[str, dict]:
    """获取所有阶段的配置Schema

    Returns:
        包含所有阶段Schema的字典，key为阶段名称，value为JSON Schema
    """
    schemas = {}
    for stage in GenesisStage:
        if stage != GenesisStage.FINISHED:  # FINISHED阶段不需要配置
            try:
                schema_class = get_stage_config_schema(stage)
                schemas[stage.value] = schema_class.model_json_schema()
            except ValueError:
                # 跳过不支持的阶段类型
                continue
    return schemas


def get_stage_order() -> list[GenesisStage]:
    """获取阶段顺序列表

    Returns:
        按顺序排列的阶段列表
    """
    return [
        GenesisStage.INITIAL_PROMPT,
        GenesisStage.WORLDVIEW,
        GenesisStage.CHARACTERS,
        GenesisStage.PLOT_OUTLINE,
        GenesisStage.FINISHED,
    ]


def is_stage_advancement(current_stage: GenesisStage, target_stage: GenesisStage) -> bool:
    """判断是否为阶段推进（向前）

    Args:
        current_stage: 当前阶段
        target_stage: 目标阶段

    Returns:
        True 如果是向前推进，False 如果是回退或同级
    """
    stage_order = get_stage_order()

    try:
        current_index = stage_order.index(current_stage)
        target_index = stage_order.index(target_stage)
        return target_index > current_index
    except ValueError:
        # 如果阶段不在列表中，认为不是推进
        return False


def check_stage_config_completeness(stage: GenesisStage, config: dict[str, Any] | None) -> dict[str, Any]:
    """检查阶段配置的完整性

    Args:
        stage: 阶段类型
        config: 配置数据

    Returns:
        包含校验结果的字典，格式：
        {
            "is_complete": bool,
            "missing_fields": list[str],
            "missing_fields_chinese": list[str],  # 新增：中文字段名
            "message": str
        }

    Raises:
        ValueError: 当阶段类型不支持时
    """
    if stage == GenesisStage.FINISHED:
        # FINISHED阶段不需要配置
        return {
            "is_complete": True,
            "missing_fields": [],
            "missing_fields_chinese": [],
            "message": "FINISHED stage does not require configuration"
        }

    if not config:
        config = {}

    # 获取阶段的必填字段
    required_fields_map = {
        GenesisStage.INITIAL_PROMPT: ["genre", "style", "target_word_count"],
        GenesisStage.WORLDVIEW: ["time_period", "geography_type", "tech_magic_level", "social_structure"],
        GenesisStage.CHARACTERS: ["protagonist_count", "relationship_complexity", "personality_preferences"],
        GenesisStage.PLOT_OUTLINE: ["chapter_count_preference", "plot_complexity", "conflict_types"],
    }

    if stage not in required_fields_map:
        raise ValueError(f"Unsupported stage type for validation: {stage}")

    required_fields = required_fields_map[stage]
    missing_fields = []

    for field in required_fields:
        if field not in config or config[field] is None:
            missing_fields.append(field)
        elif isinstance(config[field], str | list) and not config[field]:
            # 空字符串或空列表也视为缺失
            missing_fields.append(field)

    # 获取缺失字段的中文名称
    missing_fields_chinese = []
    if missing_fields:
        try:
            schema_class = get_stage_config_schema(stage)
            json_schema = schema_class.model_json_schema()
            properties = json_schema.get("properties", {})

            for field in missing_fields:
                field_info = properties.get(field, {})
                chinese_name = field_info.get("title", field)  # 使用title作为中文名称，如果没有则使用英文名
                missing_fields_chinese.append(chinese_name)
        except Exception:
            # 如果获取中文名称失败，使用英文名称作为后备
            missing_fields_chinese = missing_fields

    is_complete = len(missing_fields) == 0

    if is_complete:
        message = f"Stage {stage.value} configuration is complete"
    else:
        # 使用中文字段名生成消息
        chinese_fields = ", ".join(missing_fields_chinese) if missing_fields_chinese else ", ".join(missing_fields)
        message = f"Stage {stage.value} configuration is incomplete. Missing fields: {chinese_fields}"

    return {
        "is_complete": is_complete,
        "missing_fields": missing_fields,
        "missing_fields_chinese": missing_fields_chinese,
        "message": message
    }
