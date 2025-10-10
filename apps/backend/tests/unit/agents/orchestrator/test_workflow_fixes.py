"""Test fixes for workflow decoupling implementation.

This test specifically verifies that the code review issues have been fixed:
- Type conversion safety
- Thread safety
- Error handling
- Constants usage
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from src.agents.orchestrator.workflow_rules import StaticWorkflowRules, ConfigBasedWorkflowRules
from src.agents.orchestrator.workflows import EventHandlerConfig
from src.agents.orchestrator.event_handlers import QualityReviewCommand
from src.agents.orchestrator.workflow_constants import (
    WORKFLOW_DEFAULTS,
    WorkflowValidationError,
    validate_quality_threshold,
    validate_max_attempts,
    validate_consistency_threshold,
)


class TestTypeSafety:
    """Test type conversion safety fixes."""

    def test_quality_review_command_handles_invalid_types(self):
        """Test that QualityReviewCommand safely handles invalid data types."""
        rules = StaticWorkflowRules()
        command = QualityReviewCommand(workflow_rules=rules)

        # Mock data with invalid types
        mock_data = Mock()
        mock_data.score = "invalid_number"  # String that can't be converted to float
        mock_data.quality_score = None
        mock_data.attempts = "not_a_number"  # String that can't be converted to int
        mock_data.max_attempts = None
        mock_data.threshold = "bad_threshold"  # String that can't be converted to float
        mock_data.target_type = "character"
        mock_data.entity = None
        mock_data.model_dump.return_value = {"invalid": "data"}

        # This should not raise an exception, but use safe defaults
        result = command.execute(
            msg_type="Review.Quality.Evaluated",
            session_id="test-session",
            data=mock_data,
            correlation_id="test-correlation",
            scope_type="genesis",
            scope_prefix="test"
        )

        # Should complete without exceptions and use default values
        assert result is not None
        assert result.domain_event is not None

    def test_quality_review_command_handles_none_values(self):
        """Test that QualityReviewCommand safely handles None values."""
        rules = StaticWorkflowRules()
        command = QualityReviewCommand(workflow_rules=rules)

        # Mock data with None values
        mock_data = Mock()
        mock_data.score = None
        mock_data.quality_score = None
        mock_data.attempts = None
        mock_data.max_attempts = None
        mock_data.threshold = None
        mock_data.target_type = None
        mock_data.entity = None
        mock_data.model_dump.return_value = {"empty": "data"}

        # This should use safe defaults
        result = command.execute(
            msg_type="Review.Quality.Evaluated",
            session_id="test-session",
            data=mock_data,
            correlation_id="test-correlation",
            scope_type="genesis",
            scope_prefix="test"
        )

        # Should complete without exceptions
        assert result is not None
        assert result.domain_event is not None

    def test_quality_review_command_handles_missing_attributes(self):
        """Test that QualityReviewCommand safely handles missing attributes."""
        rules = StaticWorkflowRules()
        command = QualityReviewCommand(workflow_rules=rules)

        # Mock data with missing attributes (getattr will return None)
        mock_data = Mock()
        # Don't set any attributes - getattr should return None for all
        mock_data.model_dump.return_value = {"minimal": "data"}

        # This should use safe defaults for all missing attributes
        result = command.execute(
            msg_type="Review.Quality.Evaluated",
            session_id="test-session",
            data=mock_data,
            correlation_id="test-correlation",
            scope_type="genesis",
            scope_prefix="test"
        )

        # Should complete without exceptions
        assert result is not None
        assert result.domain_event is not None


class TestThreadSafety:
    """Test thread safety improvements."""

    def test_config_loading_thread_safety(self):
        """Test that config loading is thread-safe."""

        # Clear cached config to start fresh
        EventHandlerConfig._cached_default_config = None

        results = []
        errors = []

        def load_config():
            try:
                config = EventHandlerConfig.for_genesis_workflow()
                results.append(config.to_dict())
            except Exception as e:
                errors.append(e)

        # Run multiple threads simultaneously
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(load_config) for _ in range(20)]

            # Wait for all to complete
            for future in futures:
                future.result()

        # Should have no errors
        assert len(errors) == 0
        # Should have consistent results
        assert len(results) == 20

        # All results should be identical (same configuration)
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result


class TestErrorHandling:
    """Test improved error handling."""

    def test_consistency_check_with_invalid_score(self):
        """Test consistency check handles invalid score gracefully."""
        rules = StaticWorkflowRules()

        # Test with invalid score data
        result_data = {
            "ok": False,
            "passed": False,
            "score": "not_a_number",
            "threshold": 1.0
        }

        # Should not raise exception, should return False
        result = rules.should_confirm_consistency(result_data)
        assert result is False

    def test_consistency_check_with_invalid_threshold(self):
        """Test consistency check handles invalid threshold gracefully."""
        rules = StaticWorkflowRules()

        # Test with invalid threshold data
        result_data = {
            "ok": False,
            "passed": False,
            "score": 2.0,
            "threshold": "not_a_number"
        }

        # Should not raise exception, should return False
        result = rules.should_confirm_consistency(result_data)
        assert result is False

    def test_consistency_check_with_both_invalid(self):
        """Test consistency check handles both score and threshold invalid."""
        rules = StaticWorkflowRules()

        # Test with both invalid
        result_data = {
            "ok": False,
            "passed": False,
            "score": "invalid",
            "threshold": "also_invalid"
        }

        # Should not raise exception, should return False
        result = rules.should_confirm_consistency(result_data)
        assert result is False


class TestConstantsUsage:
    """Test that constants are properly used instead of hardcoded values."""

    def test_static_rules_uses_constants(self):
        """Test that StaticWorkflowRules uses WORKFLOW_DEFAULTS constants."""
        rules = StaticWorkflowRules()

        # Test event mapping uses constants
        assert rules.get_target_for_event("Character.Generated") == "character"
        assert rules.get_target_for_event("Character.Generated") in WORKFLOW_DEFAULTS.EVENT_TARGET_MAPPING.values()

        # Test action mappings use constants
        assert rules.get_confirmation_action("character") == WORKFLOW_DEFAULTS.CONFIRMATION_ACTIONS["character"]
        assert rules.get_failure_action("theme") == WORKFLOW_DEFAULTS.FAILURE_ACTIONS["theme"]
        assert rules.get_regeneration_action("character") == WORKFLOW_DEFAULTS.REGENERATION_ACTIONS["character"]

    def test_task_prefix_uses_constants(self):
        """Test that task prefixes use constants."""
        rules = StaticWorkflowRules()

        assert rules.get_task_prefix("quality_review") == WORKFLOW_DEFAULTS.QUALITY_REVIEW_PREFIX
        assert rules.get_task_prefix("consistency_check") == WORKFLOW_DEFAULTS.CONSISTENCY_CHECK_PREFIX


class TestValidationFunctions:
    """Test validation functions work correctly."""

    def test_validate_quality_threshold_valid_values(self):
        """Test quality threshold validation with valid values."""
        # Should not raise for valid values
        validate_quality_threshold(0.0)
        validate_quality_threshold(5.0)
        validate_quality_threshold(10.0)

    def test_validate_quality_threshold_invalid_values(self):
        """Test quality threshold validation with invalid values."""
        with pytest.raises(WorkflowValidationError):
            validate_quality_threshold(-1.0)

        with pytest.raises(WorkflowValidationError):
            validate_quality_threshold(11.0)

    def test_validate_max_attempts_valid_values(self):
        """Test max attempts validation with valid values."""
        validate_max_attempts(1)
        validate_max_attempts(5)
        validate_max_attempts(100)

    def test_validate_max_attempts_invalid_values(self):
        """Test max attempts validation with invalid values."""
        with pytest.raises(WorkflowValidationError):
            validate_max_attempts(0)

        with pytest.raises(WorkflowValidationError):
            validate_max_attempts(-1)

    def test_validate_consistency_threshold_valid_values(self):
        """Test consistency threshold validation with valid values."""
        validate_consistency_threshold(0.0)
        validate_consistency_threshold(1.0)
        validate_consistency_threshold(100.0)

    def test_validate_consistency_threshold_invalid_values(self):
        """Test consistency threshold validation with invalid values."""
        with pytest.raises(WorkflowValidationError):
            validate_consistency_threshold(-1.0)


class TestBackwardCompatibility:
    """Test that backward compatibility is maintained."""

    def test_both_rules_implementations_still_work(self):
        """Test that both StaticWorkflowRules and ConfigBasedWorkflowRules work."""
        # Static rules
        static_rules = StaticWorkflowRules()
        static_target = static_rules.get_target_for_event("Character.Generated")

        # Config-based rules
        config = EventHandlerConfig.for_genesis_workflow()
        config_rules = ConfigBasedWorkflowRules(config)
        config_target = config_rules.get_target_for_event("Character.Generated")

        # Both should work and return same result
        assert static_target == config_target == "character"

    def test_event_handlers_work_with_both_rules(self):
        """Test that event handlers work with both rules implementations."""
        # Test with static rules
        static_rules = StaticWorkflowRules()
        static_command = QualityReviewCommand(workflow_rules=static_rules)
        assert static_command.workflow_rules is static_rules

        # Test with config-based rules (backward compatibility)
        config = EventHandlerConfig.for_genesis_workflow()
        config_command = QualityReviewCommand(config=config)
        assert isinstance(config_command.workflow_rules, ConfigBasedWorkflowRules)


if __name__ == "__main__":
    pytest.main([__file__])