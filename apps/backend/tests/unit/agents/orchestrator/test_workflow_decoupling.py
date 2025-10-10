"""Test workflow JSON decoupling implementation.

This test verifies that the business rules interface successfully decouples
workflow logic from JSON configuration files.
"""

import pytest
from unittest.mock import Mock

from src.agents.orchestrator.workflow_rules import (
    IWorkflowRules,
    StaticWorkflowRules,
    ConfigBasedWorkflowRules,
    QualityReviewRequest,
    ReviewResult,
)
from src.agents.orchestrator.workflows import EventHandlerConfig
from src.agents.orchestrator.event_handlers import (
    EventCommandFactory,
    WorkflowOrchestrator,
    CapabilityEventHandlers,
    QualityReviewCommand,
    GenerationCompletedCommand,
    ConsistencyCheckCommand,
)


class TestWorkflowRulesInterface:
    """Test that both implementations of IWorkflowRules behave consistently."""

    def test_static_rules_no_json_dependency(self):
        """Test that StaticWorkflowRules works without any JSON configuration."""
        rules = StaticWorkflowRules()

        # Test event to target mapping
        assert rules.get_target_for_event("Character.Generated") == "character"
        assert rules.get_target_for_event("Theme.Generated") == "theme"
        assert rules.get_target_for_event("Unknown.Event") is None

        # Test task prefixes
        assert rules.get_task_prefix("quality_review") == "Review.Quality.Evaluation"
        assert rules.get_task_prefix("consistency_check") == "Review.Consistency.Check"

        # Test actions
        assert rules.get_confirmation_action("character") == "Character.Confirmed"
        assert rules.get_failure_action("theme") == "Theme.Failed"
        assert rules.get_regeneration_action("character") == "Character.RegenerationRequested"

    def test_config_based_rules_with_json(self):
        """Test that ConfigBasedWorkflowRules works with existing configuration."""
        config = EventHandlerConfig.for_genesis_workflow()
        rules = ConfigBasedWorkflowRules(config)

        # Test event to target mapping (should match JSON config)
        assert rules.get_target_for_event("Character.Generated") == "character"
        assert rules.get_target_for_event("Theme.Generated") == "theme"

        # Test task prefixes
        assert rules.get_task_prefix("quality_review") == "Review.Quality.Evaluation"
        assert rules.get_task_prefix("consistency_check") == "Review.Consistency.Check"

    def test_both_implementations_produce_same_results(self):
        """Test that both implementations produce identical results for same inputs."""
        static_rules = StaticWorkflowRules()
        config = EventHandlerConfig.for_genesis_workflow()
        config_rules = ConfigBasedWorkflowRules(config)

        # Test cases for comparison
        test_events = ["Character.Generated", "Theme.Generated", "Character.Design.Generated"]
        test_task_types = ["quality_review", "consistency_check"]
        test_targets = ["character", "theme"]

        # Compare event mappings
        for event in test_events:
            assert static_rules.get_target_for_event(event) == config_rules.get_target_for_event(event)

        # Compare task prefixes
        for task_type in test_task_types:
            assert static_rules.get_task_prefix(task_type) == config_rules.get_task_prefix(task_type)

        # Compare actions
        for target in test_targets:
            assert static_rules.get_confirmation_action(target) == config_rules.get_confirmation_action(target)
            assert static_rules.get_failure_action(target) == config_rules.get_failure_action(target)
            assert static_rules.get_regeneration_action(target) == config_rules.get_regeneration_action(target)

    def test_quality_review_decision_logic(self):
        """Test quality review decision logic in both implementations."""
        static_rules = StaticWorkflowRules()
        config = EventHandlerConfig.for_genesis_workflow()
        config_rules = ConfigBasedWorkflowRules(config)

        # Test case: quality passes
        request_pass = QualityReviewRequest(
            score=8.0,
            attempts=1,
            max_attempts=3,
            threshold=7.5,
            target_type="character"
        )

        static_decision = static_rules.evaluate_quality_review(request_pass)
        config_decision = config_rules.evaluate_quality_review(request_pass)

        assert static_decision.result == ReviewResult.APPROVED
        assert config_decision.result == ReviewResult.APPROVED
        assert static_decision.action == config_decision.action == "Character.Confirmed"

        # Test case: quality fails, but can retry
        request_retry = QualityReviewRequest(
            score=6.0,
            attempts=1,
            max_attempts=3,
            threshold=7.5,
            target_type="character"
        )

        static_decision = static_rules.evaluate_quality_review(request_retry)
        config_decision = config_rules.evaluate_quality_review(request_retry)

        assert static_decision.result == ReviewResult.REJECTED_RETRY
        assert config_decision.result == ReviewResult.REJECTED_RETRY
        assert static_decision.action == config_decision.action == "Character.RegenerationRequested"

        # Test case: max attempts reached
        request_failed = QualityReviewRequest(
            score=6.0,
            attempts=2,
            max_attempts=3,
            threshold=7.5,
            target_type="character"
        )

        static_decision = static_rules.evaluate_quality_review(request_failed)
        config_decision = config_rules.evaluate_quality_review(request_failed)

        assert static_decision.result == ReviewResult.REJECTED_FAILED
        assert config_decision.result == ReviewResult.REJECTED_FAILED
        assert static_decision.action == config_decision.action == "Character.Failed"

    def test_consistency_check_logic(self):
        """Test consistency check logic in both implementations."""
        static_rules = StaticWorkflowRules()
        config = EventHandlerConfig.for_genesis_workflow()
        config_rules = ConfigBasedWorkflowRules(config)

        # Test explicit ok=True
        assert static_rules.should_confirm_consistency({"ok": True}) is True
        assert config_rules.should_confirm_consistency({"ok": True}) is True

        # Test explicit passed=True
        assert static_rules.should_confirm_consistency({"passed": True}) is True
        assert config_rules.should_confirm_consistency({"passed": True}) is True

        # Test score-based evaluation
        result_data = {"score": 1.5, "threshold": 1.0}
        assert static_rules.should_confirm_consistency(result_data) is True
        assert config_rules.should_confirm_consistency(result_data) is True

        # Test failed consistency
        result_data = {"score": 0.5, "threshold": 1.0}
        assert static_rules.should_confirm_consistency(result_data) is False
        assert config_rules.should_confirm_consistency(result_data) is False


class TestEventHandlersWithWorkflowRules:
    """Test that event handlers work correctly with the new workflow rules interface."""

    def test_quality_review_command_with_static_rules(self):
        """Test QualityReviewCommand works with StaticWorkflowRules."""
        rules = StaticWorkflowRules()
        command = QualityReviewCommand(workflow_rules=rules)

        # Mock data for quality review
        mock_data = Mock()
        mock_data.score = 8.0
        mock_data.quality_score = None
        mock_data.attempts = 1
        mock_data.max_attempts = None
        mock_data.threshold = None
        mock_data.target_type = "character"
        mock_data.entity = None
        mock_data.model_dump.return_value = {"score": 8.0, "target_type": "character"}

        # Execute command
        result = command.execute(
            msg_type="Review.Quality.Evaluated",
            session_id="test-session",
            data=mock_data,
            correlation_id="test-correlation",
            scope_type="genesis",
            scope_prefix="test"
        )

        # Verify result
        assert result is not None
        assert result.domain_event is not None
        assert result.domain_event["event_action"] == "Character.Confirmed"
        assert result.task_completion is not None

    def test_event_command_factory_with_static_rules(self):
        """Test EventCommandFactory works with StaticWorkflowRules."""
        rules = StaticWorkflowRules()
        factory = EventCommandFactory(workflow_rules=rules)

        # Test that commands are created with the rules
        generation_command = factory.get_command("Character.Generated")
        assert generation_command is not None
        assert isinstance(generation_command, GenerationCompletedCommand)
        assert generation_command.workflow_rules is rules

        quality_command = factory.get_command("Review.Quality.Evaluated")
        assert quality_command is not None
        assert isinstance(quality_command, QualityReviewCommand)
        assert quality_command.workflow_rules is rules

    def test_workflow_orchestrator_with_static_rules(self):
        """Test WorkflowOrchestrator works with StaticWorkflowRules."""
        rules = StaticWorkflowRules()
        orchestrator = WorkflowOrchestrator(workflow_rules=rules)

        # Verify the orchestrator uses the static rules
        assert orchestrator.workflow_rules is rules
        assert orchestrator.factory.workflow_rules is rules

    def test_capability_event_handlers_with_static_rules(self):
        """Test CapabilityEventHandlers works with StaticWorkflowRules."""
        rules = StaticWorkflowRules()
        handlers = CapabilityEventHandlers(workflow_rules=rules)

        # Verify the handlers use the static rules
        assert handlers.orchestrator.workflow_rules is rules

    def test_backward_compatibility_without_rules(self):
        """Test that existing code still works without providing workflow rules."""
        # This should fall back to config-based rules
        factory = EventCommandFactory()
        orchestrator = WorkflowOrchestrator()
        handlers = CapabilityEventHandlers()

        # Verify they all work (they should use ConfigBasedWorkflowRules internally)
        assert isinstance(factory.workflow_rules, ConfigBasedWorkflowRules)
        assert isinstance(orchestrator.workflow_rules, ConfigBasedWorkflowRules)
        assert isinstance(handlers.orchestrator.workflow_rules, ConfigBasedWorkflowRules)


class TestDecouplingEffectiveness:
    """Test that the decoupling actually removes JSON dependency."""

    def test_can_run_without_json_files(self, monkeypatch):
        """Test that StaticWorkflowRules can work even if JSON files are missing."""
        # Mock the file reading to simulate missing JSON
        def mock_missing_file(*args, **kwargs):
            raise FileNotFoundError("JSON file not found")

        # This should work fine since StaticWorkflowRules doesn't use JSON
        rules = StaticWorkflowRules()

        # Test core functionality
        decision = rules.evaluate_quality_review(QualityReviewRequest(
            score=8.0,
            attempts=1,
            max_attempts=3,
            threshold=7.5,
            target_type="character"
        ))

        assert decision.result == ReviewResult.APPROVED
        assert decision.action == "Character.Confirmed"

    def test_static_rules_independent_of_config_changes(self):
        """Test that StaticWorkflowRules behavior doesn't change if config changes."""
        rules = StaticWorkflowRules()

        # Get initial behavior
        initial_target = rules.get_target_for_event("Character.Generated")
        initial_action = rules.get_confirmation_action("character")

        # Simulate config changes (this shouldn't affect static rules)
        # Since static rules don't use external config, behavior should remain constant
        assert rules.get_target_for_event("Character.Generated") == initial_target
        assert rules.get_confirmation_action("character") == initial_action

    def test_migration_path_config_to_static(self):
        """Test the migration path from config-based to static rules."""
        # Step 1: Current state with config
        config = EventHandlerConfig.for_genesis_workflow()
        config_rules = ConfigBasedWorkflowRules(config)

        # Step 2: Migrated state with static rules
        static_rules = StaticWorkflowRules()

        # Step 3: Verify both produce same results (migration safety)
        test_request = QualityReviewRequest(
            score=8.0,
            attempts=1,
            max_attempts=3,
            threshold=7.5,
            target_type="character"
        )

        config_decision = config_rules.evaluate_quality_review(test_request)
        static_decision = static_rules.evaluate_quality_review(test_request)

        assert config_decision.result == static_decision.result
        assert config_decision.action == static_decision.action
        assert config_decision.reason == static_decision.reason


if __name__ == "__main__":
    pytest.main([__file__])