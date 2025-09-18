"""Unit tests for Genesis stage configuration schemas."""

import pytest
from pydantic import ValidationError
from src.schemas.enums import GenesisStage
from src.schemas.genesis.stage_config_schemas import (
    CharactersConfig,
    InitialPromptConfig,
    PlotOutlineConfig,
    WorldviewConfig,
    get_all_stage_config_schemas,
    get_stage_config_schema,
    validate_stage_config,
)


class TestInitialPromptConfig:
    """Test InitialPromptConfig schema."""

    def test_valid_config(self):
        """Test valid initial prompt configuration."""
        config_data = {
            "genre": "玄幻",
            "style": "第三人称",
            "target_word_count": 100000,
            "special_requirements": ["融入中国传统文化元素", "加入幽默元素"],
        }

        config = InitialPromptConfig(**config_data)

        assert config.genre == "玄幻"
        assert config.style == "第三人称"
        assert config.target_word_count == 100000
        assert config.special_requirements == ["融入中国传统文化元素", "加入幽默元素"]

    def test_default_special_requirements(self):
        """Test default special_requirements is empty list."""
        config_data = {"genre": "科幻", "style": "第一人称", "target_word_count": 50000}

        config = InitialPromptConfig(**config_data)

        assert config.special_requirements == []

    def test_word_count_validation(self):
        """Test word count validation boundaries."""
        # Test minimum boundary
        config_data = {
            "genre": "言情",
            "style": "第三人称",
            "target_word_count": 10000,  # minimum
            "special_requirements": [],
        }
        config = InitialPromptConfig(**config_data)
        assert config.target_word_count == 10000

        # Test maximum boundary
        config_data["target_word_count"] = 1000000  # maximum
        config = InitialPromptConfig(**config_data)
        assert config.target_word_count == 1000000

        # Test below minimum should fail
        with pytest.raises(ValidationError):
            config_data["target_word_count"] = 9999
            InitialPromptConfig(**config_data)

        # Test above maximum should fail
        with pytest.raises(ValidationError):
            config_data["target_word_count"] = 1000001
            InitialPromptConfig(**config_data)

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            InitialPromptConfig(genre="玄幻", style="第三人称")  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            InitialPromptConfig(genre="玄幻", target_word_count=100000)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            InitialPromptConfig(style="第三人称", target_word_count=100000)  # type: ignore[call-arg]


class TestWorldviewConfig:
    """Test WorldviewConfig schema."""

    def test_valid_config(self):
        """Test valid worldview configuration."""
        config_data = {
            "time_period": "古代",
            "geography_type": "大陆",
            "tech_magic_level": "高魔法",
            "social_structure": "封建制",
            "power_system": "修真等级",
        }

        config = WorldviewConfig(**config_data)

        assert config.time_period == "古代"
        assert config.geography_type == "大陆"
        assert config.tech_magic_level == "高魔法"
        assert config.social_structure == "封建制"
        assert config.power_system == "修真等级"

    def test_optional_power_system(self):
        """Test power_system is optional."""
        config_data = {
            "time_period": "现代",
            "geography_type": "城市",
            "tech_magic_level": "低魔法",
            "social_structure": "民主制",
        }

        config = WorldviewConfig(**config_data)
        assert config.power_system is None

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            WorldviewConfig(  # type: ignore[call-arg]
                geography_type="大陆", tech_magic_level="高魔法", social_structure="封建制"
            )  # missing time_period


class TestCharactersConfig:
    """Test CharactersConfig schema."""

    def test_valid_config(self):
        """Test valid characters configuration."""
        config_data = {
            "protagonist_count": 2,
            "relationship_complexity": "复杂",
            "personality_preferences": ["坚韧", "聪明", "善良"],
            "include_villains": True,
        }

        config = CharactersConfig(**config_data)

        assert config.protagonist_count == 2
        assert config.relationship_complexity == "复杂"
        assert config.personality_preferences == ["坚韧", "聪明", "善良"]
        assert config.include_villains is True

    def test_protagonist_count_validation(self):
        """Test protagonist count validation boundaries."""
        config_data = {
            "protagonist_count": 1,  # minimum
            "relationship_complexity": "简单",
            "personality_preferences": ["勇敢"],
            "include_villains": False,
        }
        config = CharactersConfig(**config_data)
        assert config.protagonist_count == 1

        config_data["protagonist_count"] = 5  # maximum
        config = CharactersConfig(**config_data)
        assert config.protagonist_count == 5

        # Test below minimum should fail
        with pytest.raises(ValidationError):
            config_data["protagonist_count"] = 0
            CharactersConfig(**config_data)

        # Test above maximum should fail
        with pytest.raises(ValidationError):
            config_data["protagonist_count"] = 6
            CharactersConfig(**config_data)

    def test_default_include_villains(self):
        """Test default include_villains is True."""
        config_data = {"protagonist_count": 1, "relationship_complexity": "简单", "personality_preferences": ["勇敢"]}

        config = CharactersConfig(**config_data)
        assert config.include_villains is True


class TestPlotOutlineConfig:
    """Test PlotOutlineConfig schema."""

    def test_valid_config(self):
        """Test valid plot outline configuration."""
        config_data = {
            "chapter_count_preference": 25,
            "plot_complexity": "中等",
            "conflict_types": ["内心冲突", "人际冲突"],
            "pacing_preference": "快节奏",
        }

        config = PlotOutlineConfig(**config_data)

        assert config.chapter_count_preference == 25
        assert config.plot_complexity == "中等"
        assert config.conflict_types == ["内心冲突", "人际冲突"]
        assert config.pacing_preference == "快节奏"

    def test_chapter_count_validation(self):
        """Test chapter count validation boundaries."""
        config_data = {
            "chapter_count_preference": 5,  # minimum
            "plot_complexity": "简单",
            "conflict_types": ["外部冲突"],
            "pacing_preference": "慢节奏",
        }
        config = PlotOutlineConfig(**config_data)
        assert config.chapter_count_preference == 5

        config_data["chapter_count_preference"] = 100  # maximum
        config = PlotOutlineConfig(**config_data)
        assert config.chapter_count_preference == 100

        # Test below minimum should fail
        with pytest.raises(ValidationError):
            config_data["chapter_count_preference"] = 4
            PlotOutlineConfig(**config_data)

        # Test above maximum should fail
        with pytest.raises(ValidationError):
            config_data["chapter_count_preference"] = 101
            PlotOutlineConfig(**config_data)

    def test_default_pacing_preference(self):
        """Test default pacing_preference is '中等'."""
        config_data = {"chapter_count_preference": 20, "plot_complexity": "中等", "conflict_types": ["社会冲突"]}

        config = PlotOutlineConfig(**config_data)
        assert config.pacing_preference == "中等"


class TestGetStageConfigSchema:
    """Test get_stage_config_schema function."""

    def test_initial_prompt_stage(self):
        """Test getting schema for INITIAL_PROMPT stage."""
        schema_class = get_stage_config_schema(GenesisStage.INITIAL_PROMPT)
        assert schema_class == InitialPromptConfig

    def test_worldview_stage(self):
        """Test getting schema for WORLDVIEW stage."""
        schema_class = get_stage_config_schema(GenesisStage.WORLDVIEW)
        assert schema_class == WorldviewConfig

    def test_characters_stage(self):
        """Test getting schema for CHARACTERS stage."""
        schema_class = get_stage_config_schema(GenesisStage.CHARACTERS)
        assert schema_class == CharactersConfig

    def test_plot_outline_stage(self):
        """Test getting schema for PLOT_OUTLINE stage."""
        schema_class = get_stage_config_schema(GenesisStage.PLOT_OUTLINE)
        assert schema_class == PlotOutlineConfig

    def test_unsupported_stage(self):
        """Test error for unsupported stage."""
        with pytest.raises(ValueError, match="Unsupported stage type"):
            get_stage_config_schema(GenesisStage.FINISHED)


class TestValidateStageConfig:
    """Test validate_stage_config function."""

    def test_valid_initial_prompt_config(self):
        """Test validation of valid initial prompt config."""
        config_data = {
            "genre": "科幻",
            "style": "第一人称",
            "target_word_count": 80000,
            "special_requirements": ["硬科幻元素"],
        }

        result = validate_stage_config(GenesisStage.INITIAL_PROMPT, config_data)

        assert isinstance(result, InitialPromptConfig)
        assert result.genre == "科幻"
        assert result.target_word_count == 80000

    def test_valid_worldview_config(self):
        """Test validation of valid worldview config."""
        config_data = {
            "time_period": "未来",
            "geography_type": "太空",
            "tech_magic_level": "高科技",
            "social_structure": "联邦制",
        }

        result = validate_stage_config(GenesisStage.WORLDVIEW, config_data)

        assert isinstance(result, WorldviewConfig)
        assert result.time_period == "未来"
        assert result.geography_type == "太空"

    def test_invalid_config_data(self):
        """Test validation error for invalid config data."""
        invalid_config = {
            "genre": "玄幻",
            "style": "第三人称",
            "target_word_count": 5000,  # below minimum
        }

        with pytest.raises(ValidationError):
            validate_stage_config(GenesisStage.INITIAL_PROMPT, invalid_config)

    def test_unsupported_stage_validation(self):
        """Test error for unsupported stage in validation."""
        config_data = {"some": "data"}

        with pytest.raises(ValueError, match="Unsupported stage type"):
            validate_stage_config(GenesisStage.FINISHED, config_data)


class TestGetAllStageConfigSchemas:
    """Test get_all_stage_config_schemas function."""

    def test_returns_all_supported_stages(self):
        """Test that all supported stages are returned."""
        schemas = get_all_stage_config_schemas()

        expected_stages = {
            GenesisStage.INITIAL_PROMPT.value,
            GenesisStage.WORLDVIEW.value,
            GenesisStage.CHARACTERS.value,
            GenesisStage.PLOT_OUTLINE.value,
        }

        assert set(schemas.keys()) == expected_stages

    def test_excludes_finished_stage(self):
        """Test that FINISHED stage is excluded."""
        schemas = get_all_stage_config_schemas()

        assert GenesisStage.FINISHED.value not in schemas

    def test_schemas_are_json_schema_format(self):
        """Test that returned schemas are in JSON Schema format."""
        schemas = get_all_stage_config_schemas()

        for _, schema in schemas.items():
            assert isinstance(schema, dict)
            assert "type" in schema
            assert "properties" in schema
            assert schema["type"] == "object"

    def test_initial_prompt_schema_structure(self):
        """Test the structure of initial prompt schema."""
        schemas = get_all_stage_config_schemas()
        initial_prompt_schema = schemas[GenesisStage.INITIAL_PROMPT.value]

        expected_properties = {"genre", "style", "target_word_count", "special_requirements"}
        assert set(initial_prompt_schema["properties"].keys()) == expected_properties

        # Check required fields
        assert "required" in initial_prompt_schema
        expected_required = {"genre", "style", "target_word_count"}
        assert set(initial_prompt_schema["required"]) == expected_required
