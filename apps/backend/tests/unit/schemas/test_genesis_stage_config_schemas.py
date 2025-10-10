"""Unit tests for Genesis stage configuration schemas."""

import pytest
from pydantic import ValidationError
from src.schemas.enums import GenesisStage
from src.schemas.genesis.stage_config_schemas import (
    CharactersConfig,
    InitialPromptConfig,
    PlotOutlineConfig,
    WorldviewConfig,
    check_stage_config_completeness,
    get_all_stage_config_schemas,
    get_stage_config_example,
    get_stage_config_schema,
    get_stage_order,
    is_stage_advancement,
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


class TestStageConfigTemplates:
    """Test helpers providing example configuration data."""

    def test_example_returns_expected_initial_prompt_template(self):
        """Initial prompt stage template should match schema example values."""
        example = get_stage_config_example(GenesisStage.INITIAL_PROMPT)

        assert example["genre"] == "玄幻"
        assert example["style"] == "第三人称"
        assert example["target_word_count"] == 100000
        assert example["special_requirements"] == [
            "融入中国传统文化元素",
            "避免过于血腥的情节",
            "加入轻松幽默的元素",
        ]

    def test_example_returns_default_for_optional_fields(self):
        """Worldview template should include optional field defaults when provided."""
        example = get_stage_config_example(GenesisStage.WORLDVIEW)

        assert example["time_period"] == "古代"
        assert example["geography_type"] == "大陆"
        assert example["tech_magic_level"] == "高魔法"
        assert example["social_structure"] == "封建制"
        assert example["power_system"] == "修真等级"


class TestGetStageOrder:
    """Test get_stage_order function."""

    def test_returns_correct_order(self):
        """Test that stage order is correct."""
        order = get_stage_order()

        expected_order = [
            GenesisStage.INITIAL_PROMPT,
            GenesisStage.WORLDVIEW,
            GenesisStage.CHARACTERS,
            GenesisStage.PLOT_OUTLINE,
            GenesisStage.FINISHED,
        ]

        assert order == expected_order

    def test_returns_all_stages(self):
        """Test that all stages are included."""
        order = get_stage_order()

        assert len(order) == 5
        assert GenesisStage.INITIAL_PROMPT in order
        assert GenesisStage.WORLDVIEW in order
        assert GenesisStage.CHARACTERS in order
        assert GenesisStage.PLOT_OUTLINE in order
        assert GenesisStage.FINISHED in order


class TestIsStageAdvancement:
    """Test is_stage_advancement function."""

    def test_forward_progression(self):
        """Test forward stage progression detection."""
        # Test each progression step
        assert is_stage_advancement(GenesisStage.INITIAL_PROMPT, GenesisStage.WORLDVIEW) is True
        assert is_stage_advancement(GenesisStage.WORLDVIEW, GenesisStage.CHARACTERS) is True
        assert is_stage_advancement(GenesisStage.CHARACTERS, GenesisStage.PLOT_OUTLINE) is True
        assert is_stage_advancement(GenesisStage.PLOT_OUTLINE, GenesisStage.FINISHED) is True

    def test_backward_progression(self):
        """Test backward stage progression detection."""
        # Test each regression step
        assert is_stage_advancement(GenesisStage.WORLDVIEW, GenesisStage.INITIAL_PROMPT) is False
        assert is_stage_advancement(GenesisStage.CHARACTERS, GenesisStage.WORLDVIEW) is False
        assert is_stage_advancement(GenesisStage.PLOT_OUTLINE, GenesisStage.CHARACTERS) is False
        assert is_stage_advancement(GenesisStage.FINISHED, GenesisStage.PLOT_OUTLINE) is False

    def test_same_stage(self):
        """Test same stage detection."""
        assert is_stage_advancement(GenesisStage.INITIAL_PROMPT, GenesisStage.INITIAL_PROMPT) is False
        assert is_stage_advancement(GenesisStage.WORLDVIEW, GenesisStage.WORLDVIEW) is False
        assert is_stage_advancement(GenesisStage.CHARACTERS, GenesisStage.CHARACTERS) is False
        assert is_stage_advancement(GenesisStage.PLOT_OUTLINE, GenesisStage.PLOT_OUTLINE) is False
        assert is_stage_advancement(GenesisStage.FINISHED, GenesisStage.FINISHED) is False

    def test_skip_stages(self):
        """Test skipping stages."""
        # Forward skipping should be detected as advancement
        assert is_stage_advancement(GenesisStage.INITIAL_PROMPT, GenesisStage.CHARACTERS) is True
        assert is_stage_advancement(GenesisStage.WORLDVIEW, GenesisStage.FINISHED) is True

        # Backward skipping should be detected as regression
        assert is_stage_advancement(GenesisStage.CHARACTERS, GenesisStage.INITIAL_PROMPT) is False
        assert is_stage_advancement(GenesisStage.FINISHED, GenesisStage.WORLDVIEW) is False


class TestCheckStageConfigCompleteness:
    """Test check_stage_config_completeness function."""

    def test_complete_initial_prompt_config(self):
        """Test complete initial prompt configuration."""
        config = {
            "genre": "科幻",
            "style": "第一人称",
            "target_word_count": 80000,
            "special_requirements": ["硬科幻"]
        }

        result = check_stage_config_completeness(GenesisStage.INITIAL_PROMPT, config)

        assert result["is_complete"] is True
        assert result["missing_fields"] == []
        assert "complete" in result["message"]

    def test_incomplete_initial_prompt_config(self):
        """Test incomplete initial prompt configuration."""
        config = {
            "genre": "科幻",
            # missing style and target_word_count
        }

        result = check_stage_config_completeness(GenesisStage.INITIAL_PROMPT, config)

        assert result["is_complete"] is False
        assert "style" in result["missing_fields"]
        assert "target_word_count" in result["missing_fields"]
        assert "incomplete" in result["message"]

    def test_complete_worldview_config(self):
        """Test complete worldview configuration."""
        config = {
            "time_period": "未来",
            "geography_type": "太空",
            "tech_magic_level": "高科技",
            "social_structure": "联邦制",
            "power_system": "无"  # optional but present
        }

        result = check_stage_config_completeness(GenesisStage.WORLDVIEW, config)

        assert result["is_complete"] is True
        assert result["missing_fields"] == []

    def test_incomplete_worldview_config(self):
        """Test incomplete worldview configuration."""
        config = {
            "time_period": "未来",
            "geography_type": "太空",
            # missing tech_magic_level and social_structure
        }

        result = check_stage_config_completeness(GenesisStage.WORLDVIEW, config)

        assert result["is_complete"] is False
        assert "tech_magic_level" in result["missing_fields"]
        assert "social_structure" in result["missing_fields"]

    def test_complete_characters_config(self):
        """Test complete characters configuration."""
        config = {
            "protagonist_count": 2,
            "relationship_complexity": "复杂",
            "personality_preferences": ["勇敢", "聪明"],
            "include_villains": True  # optional but present
        }

        result = check_stage_config_completeness(GenesisStage.CHARACTERS, config)

        assert result["is_complete"] is True
        assert result["missing_fields"] == []

    def test_incomplete_characters_config(self):
        """Test incomplete characters configuration."""
        config = {
            "protagonist_count": 1,
            # missing relationship_complexity and personality_preferences
        }

        result = check_stage_config_completeness(GenesisStage.CHARACTERS, config)

        assert result["is_complete"] is False
        assert "relationship_complexity" in result["missing_fields"]
        assert "personality_preferences" in result["missing_fields"]

    def test_complete_plot_outline_config(self):
        """Test complete plot outline configuration."""
        config = {
            "chapter_count_preference": 30,
            "plot_complexity": "复杂",
            "conflict_types": ["内心冲突", "外部冲突"],
            "pacing_preference": "中等"  # optional but present
        }

        result = check_stage_config_completeness(GenesisStage.PLOT_OUTLINE, config)

        assert result["is_complete"] is True
        assert result["missing_fields"] == []

    def test_incomplete_plot_outline_config(self):
        """Test incomplete plot outline configuration."""
        config = {
            "chapter_count_preference": 25,
            # missing plot_complexity and conflict_types
        }

        result = check_stage_config_completeness(GenesisStage.PLOT_OUTLINE, config)

        assert result["is_complete"] is False
        assert "plot_complexity" in result["missing_fields"]
        assert "conflict_types" in result["missing_fields"]

    def test_empty_config(self):
        """Test empty configuration."""
        result = check_stage_config_completeness(GenesisStage.INITIAL_PROMPT, {})

        assert result["is_complete"] is False
        assert "genre" in result["missing_fields"]
        assert "style" in result["missing_fields"]
        assert "target_word_count" in result["missing_fields"]

    def test_none_config(self):
        """Test None configuration."""
        result = check_stage_config_completeness(GenesisStage.INITIAL_PROMPT, None)

        assert result["is_complete"] is False
        assert "genre" in result["missing_fields"]
        assert "style" in result["missing_fields"]
        assert "target_word_count" in result["missing_fields"]

    def test_empty_string_values(self):
        """Test empty string values are treated as missing."""
        config = {
            "genre": "",  # empty string
            "style": "第一人称",
            "target_word_count": 80000,
        }

        result = check_stage_config_completeness(GenesisStage.INITIAL_PROMPT, config)

        assert result["is_complete"] is False
        assert "genre" in result["missing_fields"]

    def test_empty_list_values(self):
        """Test empty list values are treated as missing."""
        config = {
            "protagonist_count": 1,
            "relationship_complexity": "简单",
            "personality_preferences": [],  # empty list
        }

        result = check_stage_config_completeness(GenesisStage.CHARACTERS, config)

        assert result["is_complete"] is False
        assert "personality_preferences" in result["missing_fields"]

    def test_finished_stage(self):
        """Test FINISHED stage always returns complete."""
        result = check_stage_config_completeness(GenesisStage.FINISHED, None)

        assert result["is_complete"] is True
        assert result["missing_fields"] == []
        assert "FINISHED stage does not require configuration" in result["message"]

    def test_unsupported_stage_raises_error(self):
        """Test that unsupported stage raises ValueError."""
        # This would test if we add a new stage that's not in the required_fields_map
        # For now, all valid stages are supported, so we can't test this scenario
        pass
