"""Unit tests for Genesis stage request schemas."""

import pytest
from pydantic import ValidationError
from src.schemas.enums import GenesisStage
from src.schemas.genesis.stage_schemas import CreateStageRequest, UpdateStageRequest


class TestCreateStageRequest:
    """Tests for CreateStageRequest validation."""

    def test_valid_config_normalized(self):
        """Valid config should be normalized via stage schema."""
        config = {
            "genre": "玄幻",
            "style": "第三人称",
            "target_word_count": 120000,
            "special_requirements": ["需要轻松氛围"],
        }

        request = CreateStageRequest(stage=GenesisStage.INITIAL_PROMPT, config=config)

        assert request.config == config

    def test_invalid_config_raises_validation_error(self):
        """Invalid config should raise ValidationError with descriptive message."""
        config = {
            "genre": "玄幻",
            "style": "第一人称",
            "target_word_count": 5000,  # below minimum
        }

        with pytest.raises(ValidationError) as exc_info:
            CreateStageRequest(stage=GenesisStage.INITIAL_PROMPT, config=config)

        assert f"Invalid config for stage {GenesisStage.INITIAL_PROMPT.name}" in str(exc_info.value)


class TestUpdateStageRequest:
    """Tests for UpdateStageRequest validation helper."""

    def test_validate_with_stage_normalizes_config(self):
        """Valid config should be normalized after validation."""
        config = {
            "genre": "科幻",
            "style": "第一人称",
            "target_word_count": 90000,
            "special_requirements": [],
        }

        request = UpdateStageRequest(config=config)
        request.validate_with_stage(GenesisStage.INITIAL_PROMPT)

        assert request.config == config

    def test_validate_with_stage_invalid_config_raises_value_error(self):
        """Invalid config should raise ValueError for easier HTTP 400 handling."""
        request = UpdateStageRequest(
            config={
                "genre": "科幻",
                "style": "第一人称",
                "target_word_count": 5000,
            }
        )

        with pytest.raises(ValueError) as exc_info:
            request.validate_with_stage(GenesisStage.INITIAL_PROMPT)

        assert f"Invalid config for stage {GenesisStage.INITIAL_PROMPT.name}" in str(exc_info.value)
