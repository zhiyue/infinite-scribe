"""Tests for unified event mapping configuration."""

import pytest
from src.common.events.mapping import (
    normalize_task_type,
    get_event_payload_class,
    get_event_by_command,
    get_event_category,
    list_events_by_category,
    validate_event_mappings,
    get_mapping_statistics,
    TASK_TYPE_SUFFIX_MAPPING,
)
from src.schemas.enums import GenesisEventType
from src.schemas.genesis_events import (
    GenesisEventPayload,
    StageEnteredPayload,
    StageCompletedPayload,
    ConceptSelectedPayload,
    AIGenerationStartedPayload,
)


class TestTaskTypeNormalization:
    """Test task type suffix normalization."""

    @pytest.mark.parametrize("input_type,expected", [
        ("Character.Design.GenerationRequested", "Character.Design.Generation"),
        ("Character.Design.Generated", "Character.Design.Generation"),
        ("Outliner.Theme.Generated", "Outliner.Theme.Generation"),
        ("Review.Quality.EvaluationRequested", "Review.Quality.Evaluation"),
        ("Review.Consistency.CheckRequested", "Review.Consistency.Check"),
        ("Simple.Requested", "Simple.Request"),
        ("NoSuffix", "NoSuffix"),
        ("", ""),
        ("Single", "Single"),
    ])
    def test_normalize_task_type(self, input_type, expected):
        """Test task type normalization with various inputs."""
        result = normalize_task_type(input_type)
        assert result == expected

    def test_normalize_task_type_preserves_unknown_suffixes(self):
        """Test that unknown suffixes are preserved."""
        result = normalize_task_type("Test.CustomSuffix")
        assert result == "Test.CustomSuffix"

    def test_suffix_mapping_completeness(self):
        """Test that all expected suffix mappings are defined."""
        expected_suffixes = {
            "GenerationRequested", "Generated", "EvaluationRequested", "Evaluated",
            "CheckRequested", "Checked", "AnalysisRequested", "Analyzed",
            "ValidationRequested", "Validated", "RevisionRequested", "Revised",
            "Requested", "Started", "Completed", "Result"
        }

        actual_suffixes = set(TASK_TYPE_SUFFIX_MAPPING.keys())
        assert actual_suffixes == expected_suffixes


class TestEventPayloadMapping:
    """Test event to payload class mapping."""

    @pytest.mark.parametrize("event_type,expected_class", [
        (GenesisEventType.STAGE_ENTERED, StageEnteredPayload),
        (GenesisEventType.STAGE_COMPLETED, StageCompletedPayload),
        (GenesisEventType.CONCEPT_SELECTED, ConceptSelectedPayload),
        (GenesisEventType.AI_GENERATION_STARTED, AIGenerationStartedPayload),
        # Test unmapped events fall back to generic payload
        (GenesisEventType.AI_GENERATION_FAILED, GenesisEventPayload),
        (GenesisEventType.USER_INPUT_REQUESTED, GenesisEventPayload),
        ("UNKNOWN_EVENT", GenesisEventPayload),
    ])
    def test_get_event_payload_class(self, event_type, expected_class):
        """Test payload class retrieval for various event types."""
        result = get_event_payload_class(event_type)
        assert result == expected_class

    def test_high_frequency_events_have_specific_payloads(self):
        """Test that high-frequency events have dedicated payload classes."""
        high_freq_events = [
            "STAGE_ENTERED", "STAGE_COMPLETED", "AI_GENERATION_STARTED",
            "AI_GENERATION_COMPLETED", "CONCEPT_SELECTED"
        ]

        for event in high_freq_events:
            payload_class = get_event_payload_class(event)
            assert payload_class != GenesisEventPayload, f"High-frequency event {event} should have specific payload class"


class TestCommandEventMapping:
    """Test command to event mapping."""

    @pytest.mark.parametrize("command,expected_event", [
        ("Character.Request", "Character.Requested"),
        ("Character.Requested", "Character.Requested"),
        ("CHARACTER_REQUEST", "Character.Requested"),
        ("Theme.Request", "Theme.Requested"),
        ("THEME_REQUEST", "Theme.Requested"),
        ("Stage.Validate", "Stage.ValidationRequested"),
        ("Stage.Lock", "Stage.LockRequested"),
    ])
    def test_get_event_by_command(self, command, expected_event):
        """Test command to event mapping."""
        result = get_event_by_command(command)
        assert result == expected_event

    def test_unmapped_command_returns_none(self):
        """Test that unmapped commands return None."""
        result = get_event_by_command("UnknownCommand")
        assert result is None


class TestEventCategorization:
    """Test event categorization functionality."""

    @pytest.mark.parametrize("event_type,expected_category", [
        (GenesisEventType.STAGE_ENTERED, "stage_lifecycle"),
        (GenesisEventType.STAGE_COMPLETED, "stage_lifecycle"),
        (GenesisEventType.CONCEPT_SELECTED, "content_generation"),
        (GenesisEventType.AI_GENERATION_STARTED, "ai_interaction"),
        (GenesisEventType.NOVEL_CREATED_FROM_GENESIS, "novel_creation"),
        ("UNKNOWN_EVENT", "general"),
    ])
    def test_get_event_category(self, event_type, expected_category):
        """Test event category retrieval."""
        result = get_event_category(event_type)
        assert result == expected_category

    def test_list_events_by_category(self):
        """Test listing events by category."""
        stage_events = list_events_by_category("stage_lifecycle")
        assert "STAGE_ENTERED" in stage_events
        assert "STAGE_COMPLETED" in stage_events

        ai_events = list_events_by_category("ai_interaction")
        assert "AI_GENERATION_STARTED" in ai_events
        assert "AI_GENERATION_COMPLETED" in ai_events

    def test_list_events_by_unknown_category(self):
        """Test listing events for unknown category returns empty list."""
        result = list_events_by_category("unknown_category")
        assert result == []


class TestMappingValidation:
    """Test mapping validation utilities."""

    def test_validate_event_mappings(self):
        """Test mapping validation identifies issues correctly."""
        issues = validate_event_mappings()

        # Should not have orphaned payload mappings (all mapped events should exist in enum)
        assert not issues.get("orphaned_payload_mappings", [])

        # May have missing high-frequency mappings (this is allowed but logged)
        # May have missing category mappings (events without categories default to "general")

    def test_mapping_statistics(self):
        """Test mapping statistics provide expected counts."""
        stats = get_mapping_statistics()

        assert stats["total_task_type_mappings"] > 0
        assert stats["total_event_payload_mappings"] > 0
        assert stats["total_command_event_mappings"] > 0
        assert stats["total_event_categories"] > 0
        assert stats["total_genesis_event_types"] > 0

    def test_validate_no_critical_issues(self):
        """Test that validation finds no critical issues."""
        issues = validate_event_mappings()

        # Critical issues that should not exist
        critical_issues = ["orphaned_payload_mappings"]

        for issue_type in critical_issues:
            assert not issues.get(issue_type, []), f"Critical issue found: {issue_type} = {issues.get(issue_type)}"


class TestIntegration:
    """Integration tests for unified mapping."""

    def test_task_type_normalization_idempotent(self):
        """Test that normalizing already normalized task types is idempotent."""
        test_cases = [
            "Character.Design.Generation",
            "Review.Quality.Evaluation",
            "Review.Consistency.Check",
        ]

        for task_type in test_cases:
            # Normalizing should not change already normalized types
            result = normalize_task_type(task_type)
            assert result == task_type

    def test_end_to_end_mapping_consistency(self):
        """Test consistency across all mapping functions."""
        # Test a complete flow
        command = "Character.Request"

        # Command should map to an event
        event_action = get_event_by_command(command)
        assert event_action is not None

        # Can get category for events
        # Note: command events are domain events, not genesis events
        # So they may not have direct category mapping, which is fine

        # Task type normalization should work with capability events
        capability_event = "Character.Design.GenerationRequested"
        normalized = normalize_task_type(capability_event)
        assert normalized == "Character.Design.Generation"