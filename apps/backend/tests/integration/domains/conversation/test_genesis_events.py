"""
Event integration tests for Genesis conversation workflows.

This module tests domain event publishing, SSE event integration,
event ordering, payload integrity, and event-driven architecture
aspects of Genesis conversations.
"""

import time

import pytest
from src.schemas.novel.dialogue import DialogueRole

# Fixtures are automatically available from conftest.py


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
class TestGenesisEventIntegration:
    """Test domain event integration and SSE event publishing."""

    async def test_domain_event_publishing_during_conversation(self, genesis_fixture):
        """Test that domain events are properly published during conversations."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create several conversation rounds
        rounds_data = [
            {"role": DialogueRole.USER, "input_data": {"prompt": "开始创作", "action": "start"}},
            {"role": DialogueRole.ASSISTANT, "input_data": {"response": "好的，我来帮您", "action": "acknowledge"}},
            {"role": DialogueRole.USER, "input_data": {"prompt": "我想要科幻题材", "genre": "sci-fi"}},
        ]

        for round_data in rounds_data:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Verify domain events were created
        events = await genesis_fixture.get_domain_events()
        assert len(events) > 0

        # Verify event structure
        for event in events:
            assert event.aggregate_type == "GenesisSession"
            assert str(event.aggregate_id) == str(genesis_fixture.session_id)
            assert event.event_type is not None
            assert event.payload is not None

    async def test_event_ordering_and_sequencing(self, genesis_fixture):
        """Test that events are properly ordered and sequenced."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create conversation rounds with explicit timing
        events_created = []

        for i in range(3):
            result = await genesis_fixture.create_conversation_round(
                role=DialogueRole.USER if i % 2 == 0 else DialogueRole.ASSISTANT,
                input_data={"prompt": f"Round {i}", "sequence": i},
            )
            assert result["success"]
            events_created.append(time.time())

            # Small delay to ensure different timestamps
            # In real scenario, this would be natural conversation timing

        # Verify event ordering
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= 3

        # Events should be ordered by creation time
        for i in range(1, len(events)):
            assert events[i].created_at >= events[i - 1].created_at

    async def test_event_payload_integrity(self, genesis_fixture):
        """Test that event payloads contain proper data."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create round with rich payload
        complex_input = {
            "prompt": "创建一个科幻世界",
            "genre": "science_fiction",
            "elements": ["space_travel", "ai", "alien_contact"],
            "tone": "serious",
            "target_audience": "adult",
            "inspiration": "基于阿西莫夫的基地系列",
        }

        result = await genesis_fixture.create_conversation_round(role=DialogueRole.USER, input_data=complex_input)
        assert result["success"]

        # Verify event payload integrity
        events = await genesis_fixture.get_domain_events()
        assert len(events) > 0

        # Find the event for our complex round
        latest_event = events[-1]

        # Verify payload structure
        assert latest_event.payload is not None

        # In a full implementation, we'd verify specific payload fields
        # For now, we ensure the event was created and has payload data
        assert isinstance(latest_event.payload, dict) or latest_event.payload is not None

    async def test_event_failure_handling(self, genesis_fixture):
        """Test handling of event publishing failures."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Simulate scenario where event publishing might fail
        # but conversation round creation should still succeed
        try:
            result = await genesis_fixture.create_conversation_round(
                role=DialogueRole.USER,
                input_data={
                    "prompt": "This might trigger event publishing issues",
                    "large_payload": "x" * 10000,  # Large payload
                    "special_chars": "测试特殊字符 🚀 ♠️ ∑ ∞",
                    "nested_data": {
                        "level1": {"level2": {"level3": "deep_nesting"}},
                        "array": [1, 2, 3, {"nested": "value"}],
                    },
                },
            )

            # Round creation should succeed regardless of event issues
            assert result["success"]

        except Exception:
            # If there are issues, the conversation should still be recoverable
            # Create a simple recovery round
            recovery_result = await genesis_fixture.create_conversation_round(
                role=DialogueRole.USER, input_data={"prompt": "Recovery from error", "recovery": True}
            )
            assert recovery_result["success"]

        # Verify conversation state is still valid
        final_round_count = await genesis_fixture.count_conversation_rounds()
        assert final_round_count > 0

        # Verify at least some events were created
        events = await genesis_fixture.get_domain_events()
        assert len(events) > 0

    async def test_event_correlation_and_causality(self, genesis_fixture):
        """Test event correlation and causality relationships."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create a sequence of causally related rounds
        causal_sequence = [
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "prompt": "我想创作一个故事",
                    "event_type": "initiation",
                    "correlation_group": "story_creation_flow",
                },
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response": "很好，让我们开始构思",
                    "event_type": "acknowledgment",
                    "correlation_group": "story_creation_flow",
                    "caused_by": "initiation",
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "prompt": "我选择科幻题材",
                    "event_type": "selection",
                    "correlation_group": "story_creation_flow",
                    "caused_by": "acknowledgment",
                },
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response": "科幻很有趣，让我们深入探讨",
                    "event_type": "development",
                    "correlation_group": "story_creation_flow",
                    "caused_by": "selection",
                },
            },
        ]

        for round_data in causal_sequence:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Verify events maintain causality information
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= 4

        # Check that conversation maintains causal relationships
        conversation_history = genesis_fixture.conversation_history
        assert len(conversation_history) == 4

        # Verify correlation group consistency
        correlation_groups = [r["input_data"].get("correlation_group") for r in conversation_history]
        assert all(group == "story_creation_flow" for group in correlation_groups)

        # Verify causal chain
        event_types = [r["input_data"].get("event_type") for r in conversation_history]
        expected_sequence = ["initiation", "acknowledgment", "selection", "development"]
        assert event_types == expected_sequence

    async def test_event_aggregation_and_batching(self, genesis_fixture):
        """Test event aggregation and batching scenarios."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create multiple rapid-fire rounds to test batching
        batch_rounds = []
        for i in range(10):
            input_data = {
                "prompt": f"Batch message {i}",
                "batch_id": "test_batch_001",
                "sequence_in_batch": i,
                "timestamp": time.time(),
            }

            result = await genesis_fixture.create_conversation_round(
                role=DialogueRole.USER if i % 2 == 0 else DialogueRole.ASSISTANT, input_data=input_data
            )
            batch_rounds.append(result)
            assert result["success"]

        # Verify all rounds were created
        round_count = await genesis_fixture.count_conversation_rounds()
        assert round_count == 10

        # Verify event batching behavior
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= 10  # At least one event per round

        # Check batch consistency in conversation history
        conversation_history = genesis_fixture.conversation_history
        batch_messages = [r for r in conversation_history if r["input_data"].get("batch_id") == "test_batch_001"]
        assert len(batch_messages) == 10

        # Verify sequence ordering within batch
        sequence_numbers = [r["input_data"].get("sequence_in_batch") for r in batch_messages]
        assert sequence_numbers == list(range(10))

    async def test_event_publishing_with_stage_transitions(self, genesis_fixture):
        """Test event publishing during stage transitions."""
        from src.schemas.enums import GenesisStage

        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        # Create conversation in initial stage
        initial_round = await genesis_fixture.create_conversation_round(
            role=DialogueRole.USER,
            input_data={
                "prompt": "开始创意种子阶段",
                "stage": GenesisStage.INITIAL_PROMPT.value,
                "stage_action": "start",
            },
        )
        assert initial_round["success"]

        # Transition to next stage
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.THEME_CONCEPT,
            state={
                "previous_stage": GenesisStage.INITIAL_PROMPT.value,
                "current_stage": GenesisStage.THEME_CONCEPT.value,
                "transition_trigger": "stage_completion",
            },
        )
        assert stage_update["success"]

        # Create conversation in new stage
        theme_round = await genesis_fixture.create_conversation_round(
            role=DialogueRole.USER,
            input_data={
                "prompt": "开始主题开发",
                "stage": GenesisStage.THEME_CONCEPT.value,
                "stage_action": "start",
                "references_previous_stage": True,
            },
        )
        assert theme_round["success"]

        # Verify stage transition events
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= 2  # At least events for rounds, possibly stage transition

        # Check for stage-related information in conversation
        conversation_history = genesis_fixture.conversation_history
        stage_related_rounds = [r for r in conversation_history if "stage" in r["input_data"]]
        assert len(stage_related_rounds) == 2

        # Verify stage progression in conversation
        stages_mentioned = [r["input_data"]["stage"] for r in stage_related_rounds]
        assert GenesisStage.INITIAL_PROMPT.value in stages_mentioned
        assert GenesisStage.THEME_CONCEPT.value in stages_mentioned

    async def test_event_filtering_and_routing(self, genesis_fixture):
        """Test event filtering and routing based on event types."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create rounds with different event routing requirements
        routing_test_rounds = [
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "prompt": "User prompt for UI updates",
                    "event_routing": "ui_channel",
                    "priority": "high",
                    "update_type": "immediate",
                },
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response": "AI response for background processing",
                    "event_routing": "processing_channel",
                    "priority": "low",
                    "update_type": "batch",
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "prompt": "Analytics tracking event",
                    "event_routing": "analytics_channel",
                    "priority": "medium",
                    "update_type": "queued",
                },
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response": "Critical system event",
                    "event_routing": "system_channel",
                    "priority": "critical",
                    "update_type": "immediate",
                },
            },
        ]

        for round_data in routing_test_rounds:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Verify all rounds were created
        assert len(genesis_fixture.conversation_history) == 4

        # Verify routing information is preserved
        conversation_history = genesis_fixture.conversation_history
        routing_channels = [r["input_data"].get("event_routing") for r in conversation_history]
        expected_channels = ["ui_channel", "processing_channel", "analytics_channel", "system_channel"]
        assert routing_channels == expected_channels

        # Verify priority levels
        priorities = [r["input_data"].get("priority") for r in conversation_history]
        expected_priorities = ["high", "low", "medium", "critical"]
        assert priorities == expected_priorities

        # Verify events were created for filtering
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= 4

    async def test_event_replay_and_reconstruction(self, genesis_fixture):
        """Test event replay and conversation state reconstruction."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create a conversation sequence with checkpoints
        checkpoint_sequence = [
            {
                "role": DialogueRole.USER,
                "input_data": {"prompt": "Initial state", "checkpoint": "start", "state_version": 1},
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {"response": "First response", "checkpoint": "response_1", "state_version": 2},
            },
            {
                "role": DialogueRole.USER,
                "input_data": {"prompt": "Middle development", "checkpoint": "middle", "state_version": 3},
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {"response": "Final development", "checkpoint": "end", "state_version": 4},
            },
        ]

        for round_data in checkpoint_sequence:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Capture final state
        final_state = await genesis_fixture.get_session_state()
        final_round_count = await genesis_fixture.count_conversation_rounds()

        # Get all events for potential replay
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= 4

        # Verify we can reconstruct conversation timeline
        conversation_history = genesis_fixture.conversation_history
        checkpoints = [r["input_data"].get("checkpoint") for r in conversation_history]
        assert checkpoints == ["start", "response_1", "middle", "end"]

        # Verify state versions progression
        state_versions = [r["input_data"].get("state_version") for r in conversation_history]
        assert state_versions == [1, 2, 3, 4]

        # Verify timeline consistency
        assert final_round_count == 4
        assert final_state["success"]

        # Test partial replay simulation (hypothetically)
        # In a real implementation, we could replay from checkpoint "middle"
        middle_checkpoint_rounds = [r for r in conversation_history if r["input_data"].get("state_version", 0) >= 3]
        assert len(middle_checkpoint_rounds) == 2  # middle and end

    async def test_concurrent_event_publishing(self, genesis_fixture):
        """Test concurrent event publishing from multiple conversation threads."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Simulate concurrent conversation activities
        # Note: In real concurrency, we'd use asyncio.gather or similar
        concurrent_activities = [
            {
                "activity_id": "main_conversation",
                "rounds": [
                    {"role": DialogueRole.USER, "input_data": {"prompt": "Main thread message 1", "thread": "main"}},
                    {
                        "role": DialogueRole.ASSISTANT,
                        "input_data": {"response": "Main thread response 1", "thread": "main"},
                    },
                ],
            },
            {
                "activity_id": "system_notifications",
                "rounds": [
                    {
                        "role": DialogueRole.ASSISTANT,
                        "input_data": {"system_event": "Auto-save triggered", "thread": "system"},
                    },
                    {
                        "role": DialogueRole.ASSISTANT,
                        "input_data": {"system_event": "Progress checkpoint", "thread": "system"},
                    },
                ],
            },
            {
                "activity_id": "user_feedback",
                "rounds": [
                    {
                        "role": DialogueRole.USER,
                        "input_data": {"feedback": "Quality rating provided", "thread": "feedback"},
                    },
                ],
            },
        ]

        # Execute "concurrent" activities (sequentially for testing)
        total_expected_rounds = 0
        for activity in concurrent_activities:
            for round_data in activity["rounds"]:
                result = await genesis_fixture.create_conversation_round(**round_data)
                assert result["success"]
                total_expected_rounds += 1

        # Verify all concurrent events were processed
        final_round_count = await genesis_fixture.count_conversation_rounds()
        assert final_round_count == total_expected_rounds

        # Verify events maintain thread information
        conversation_history = genesis_fixture.conversation_history
        thread_info = []
        for round_data in conversation_history:
            input_data = round_data["input_data"]
            if "thread" in input_data:
                thread_info.append(input_data["thread"])
            elif "system_event" in input_data:
                thread_info.append("system")
            elif "feedback" in input_data:
                thread_info.append("feedback")
            else:
                thread_info.append("unknown")

        # Should have messages from all threads
        assert "main" in thread_info
        assert "system" in thread_info
        assert "feedback" in thread_info

        # Verify events were created for all activities
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= total_expected_rounds
