"""
Basic multi-round conversation tests for Genesis stages.

This module tests fundamental multi-round conversation functionality
for each Genesis stage, ensuring proper conversation flow, state tracking,
and round alternation patterns.
"""

import pytest
from src.schemas.enums import GenesisStage
from src.schemas.novel.dialogue import DialogueRole



@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
class TestGenesisMultiRoundConversations:
    """Test multi-round conversations for each Genesis stage."""

    async def test_stage_0_creative_seed_multi_round(self, genesis_fixture):
        """Test multi-round conversation for Stage 0 (Creative Seed)."""
        # Create Genesis session
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"], f"Failed to create session: {session_result}"

        # Simulate multi-round conversation with creative seed data
        stage_data = GenesisTestData.STAGE_0_CREATIVE_SEEDS[0]
        conversation_results = await genesis_fixture.simulate_multi_round_conversation(stage_data=stage_data, rounds=3)

        # Verify conversation rounds
        assert len(conversation_results) == 5  # 1 initial + 3*(AI + user feedback) - 1 (no final feedback)

        # Verify round count in database
        round_count = await genesis_fixture.count_conversation_rounds()
        assert round_count == 5

        # Verify domain events were created
        events = await genesis_fixture.get_domain_events()
        assert len(events) > 0

        # Verify conversation history tracking
        assert len(genesis_fixture.conversation_history) == 5

        # Verify first round is user input
        first_round = genesis_fixture.conversation_history[0]
        assert first_round["role"] == DialogueRole.USER
        assert "prompt" in first_round["input_data"]

        # Verify alternating pattern
        for i, round_data in enumerate(genesis_fixture.conversation_history):
            if i % 2 == 0:  # Even indices should be user
                expected_role = DialogueRole.USER
            else:  # Odd indices should be assistant
                expected_role = DialogueRole.ASSISTANT
            assert round_data["role"] == expected_role

    async def test_stage_1_theme_development_multi_round(self, genesis_fixture):
        """Test multi-round conversation for Stage 1 (Theme Development)."""
        # Create Genesis session at Stage 1
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.THEME_CONCEPT)
        assert session_result["success"]

        # Simulate theme development conversation
        stage_data = GenesisTestData.STAGE_1_THEMES[0]
        conversation_results = await genesis_fixture.simulate_multi_round_conversation(
            stage_data=stage_data,
            rounds=4,  # More rounds for theme development
        )

        # Verify conversation structure
        assert len(conversation_results) == 7  # 1 initial + 4*(AI + user) - 1

        # Verify session state progression
        session_state = await genesis_fixture.get_session_state()
        assert session_state["success"]

        # Verify theme-specific content
        theme_rounds = [r for r in genesis_fixture.conversation_history if "theme" in str(r["input_data"]).lower()]
        assert len(theme_rounds) > 0

    async def test_stage_2_worldview_construction_multi_round(self, genesis_fixture):
        """Test multi-round conversation for Stage 2 (Worldview Construction)."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.WORLDVIEW)
        assert session_result["success"]

        stage_data = GenesisTestData.STAGE_2_WORLDVIEWS[0]
        conversation_results = await genesis_fixture.simulate_multi_round_conversation(
            stage_data=stage_data,
            rounds=5,  # Complex worldbuilding needs more rounds
        )

        # Verify extensive conversation
        assert len(conversation_results) == 9  # 1 initial + 5*(AI + user) - 1

        # Verify worldview complexity tracking
        worldview_rounds = [
            r
            for r in genesis_fixture.conversation_history
            if any(key in str(r["input_data"]).lower() for key in ["world", "rules", "geography", "culture"])
        ]
        assert len(worldview_rounds) > 0

    async def test_stage_3_character_design_multi_round(self, genesis_fixture):
        """Test multi-round conversation for Stage 3 (Character Design)."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.CHARACTER)
        assert session_result["success"]

        stage_data = GenesisTestData.STAGE_3_CHARACTERS[0]
        conversation_results = await genesis_fixture.simulate_multi_round_conversation(stage_data=stage_data, rounds=4)

        assert len(conversation_results) == 7

        # Verify character-specific content
        character_rounds = [
            r
            for r in genesis_fixture.conversation_history
            if any(
                key in str(r["input_data"]).lower() for key in ["character", "protagonist", "motivation", "background"]
            )
        ]
        assert len(character_rounds) > 0

    async def test_stage_4_plot_framework_multi_round(self, genesis_fixture):
        """Test multi-round conversation for Stage 4 (Plot Framework)."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.PLOT)
        assert session_result["success"]

        stage_data = GenesisTestData.STAGE_4_PLOTS[0]
        conversation_results = await genesis_fixture.simulate_multi_round_conversation(stage_data=stage_data, rounds=3)

        assert len(conversation_results) == 5

        # Verify plot-specific content
        plot_rounds = [
            r
            for r in genesis_fixture.conversation_history
            if any(key in str(r["input_data"]).lower() for key in ["plot", "structure", "conflict", "climax"])
        ]
        assert len(plot_rounds) > 0

    async def test_conversation_round_structure_validation(self, genesis_fixture):
        """Test that conversation rounds maintain proper structure."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Test various input data structures
        test_rounds = [
            {"role": DialogueRole.USER, "input_data": {"prompt": "Simple text prompt", "metadata": {"type": "simple"}}},
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response": "AI response with structured data",
                    "options": ["option1", "option2", "option3"],
                    "confidence": 0.85,
                    "metadata": {"type": "structured"},
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "selected_option": "option1",
                    "feedback": "User feedback",
                    "additional_notes": "Some notes",
                    "metadata": {"type": "feedback"},
                },
            },
        ]

        for round_data in test_rounds:
            result = await genesis_fixture.create_conversation_round(
                role=round_data["role"], input_data=round_data["input_data"]
            )
            assert result["success"]

            # Verify structure preservation
            last_history = genesis_fixture.conversation_history[-1]
            assert last_history["role"] == round_data["role"]
            assert "metadata" in last_history["input_data"]

        # Verify total rounds
        assert len(genesis_fixture.conversation_history) == 3
        assert await genesis_fixture.count_conversation_rounds() == 3

    async def test_multi_round_conversation_flow_quality(self, genesis_fixture):
        """Test conversation flow quality metrics."""
        assert session_result["success"]

        # Create conversation with increasing complexity
        progressive_rounds = [
            {
                "role": DialogueRole.USER,
                "input_data": {"prompt": "Start"},  # Simple
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response": "Here are some options for your consideration",
                    "options": ["A", "B", "C"],
                },  # More complex
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "choice": "B",
                    "reasoning": "I choose B because it aligns with my vision",
                    "additional_preferences": ["detail1", "detail2"],
                    "feedback": "Please add more specific examples",
                },  # Most complex
            },
        ]

        for round_data in progressive_rounds:
            result = await genesis_fixture.create_conversation_round(
                role=round_data["role"], input_data=round_data["input_data"]
            )
            assert result["success"]

        # Analyze conversation quality
        engagement_score = ConversationQualityMetrics.calculate_engagement_score(genesis_fixture.conversation_history)
        flow_analysis = ConversationQualityMetrics.analyze_conversation_flow(genesis_fixture.conversation_history)

        # Verify quality metrics
        assert engagement_score > 0.3  # Should have decent engagement
        assert flow_analysis["alternation_score"] == 1.0  # Perfect alternation
        assert flow_analysis["progression_score"] == 1.0  # Content complexity increased
        assert flow_analysis["flow_quality"] == "good"

    async def test_conversation_round_timestamps_ordering(self, genesis_fixture):
        """Test that conversation rounds maintain proper timestamp ordering."""
        session_result = await genesis_fixture.create_genesis_session()
        assert session_result["success"]

        # Create multiple rounds with time tracking
        rounds = [
            {"role": DialogueRole.USER, "input_data": {"prompt": "Round 1"}},
            {"role": DialogueRole.ASSISTANT, "input_data": {"response": "Response 1"}},
            {"role": DialogueRole.USER, "input_data": {"prompt": "Round 2"}},
            {"role": DialogueRole.ASSISTANT, "input_data": {"response": "Response 2"}},
        ]

        for round_data in rounds:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Verify timestamp ordering
        conversation_history = genesis_fixture.conversation_history
        assert len(conversation_history) == 4

        # Check that timestamps exist and are in order (if available)
        timestamps = [r.get("timestamp") for r in conversation_history]
        non_none_timestamps = [ts for ts in timestamps if ts is not None]

        if len(non_none_timestamps) > 1:
            # Verify chronological order
            for i in range(1, len(non_none_timestamps)):
                assert non_none_timestamps[i] >= non_none_timestamps[i - 1]

    async def test_conversation_session_state_tracking(self, genesis_fixture):
        """Test session state tracking during multi-round conversations."""
        # Start with initial stage
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        initial_state = await genesis_fixture.get_session_state()
        assert initial_state["success"]

        # Create conversation rounds
        stage_data = GenesisTestData.STAGE_0_CREATIVE_SEEDS[0]
        conversation_results = await genesis_fixture.simulate_multi_round_conversation(stage_data=stage_data, rounds=2)

        # Check state after conversation
        post_conversation_state = await genesis_fixture.get_session_state()
        assert post_conversation_state["success"]

        # Verify state can be retrieved consistently
        another_state_check = await genesis_fixture.get_session_state()
        assert another_state_check["success"]

        # Session should still be the same
        session_data = post_conversation_state["session"]
        session_id_from_state = (
            session_data.get("id") if hasattr(session_data, "get") else getattr(session_data, "id", None)
        )
        assert str(session_id_from_state) == str(genesis_fixture.session_id)
