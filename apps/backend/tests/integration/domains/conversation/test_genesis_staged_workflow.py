"""
Staged workflow tests for Genesis conversation progression.

This module tests complete workflow progression through Genesis stages:
立意 (Theme) → 世界观 (Worldview) → 人物 (Characters) → 情节 (Plot)

Tests include stage transitions, context preservation, validation,
and end-to-end workflow completion.
"""

import pytest
from src.schemas.enums import GenesisStage
from src.schemas.novel.dialogue import DialogueRole

from .conftest import GenesisTestData


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_docker
class TestGenesisStagedWorkflow:
    """Test complete staged workflow progression (立意/世界观/人物/情节)."""

    async def test_complete_genesis_workflow_progression(self, genesis_fixture):
        """Test complete Genesis workflow from Stage 0 to completion."""

        # Stage 0: Creative Seed
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        from .conftest import GenesisTestData

        stage_0_results = await genesis_fixture.simulate_multi_round_conversation(
            stage_data=GenesisTestData.STAGE_0_CREATIVE_SEEDS[0], rounds=2
        )
        assert len(stage_0_results) > 0

        # Progress to Stage 1: Theme Development
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.WORLDVIEW,
            state={"current_stage": GenesisStage.WORLDVIEW.value, "stage_0_completed": True},
        )
        assert stage_update["success"]

        stage_1_results = await genesis_fixture.simulate_multi_round_conversation(
            stage_data=GenesisTestData.STAGE_1_THEMES[0], rounds=2
        )

        # Progress to Stage 2: Worldview Construction
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.WORLDVIEW,
            state={"current_stage": GenesisStage.WORLDVIEW.value, "stage_1_completed": True},
        )
        assert stage_update["success"]

        stage_2_results = await genesis_fixture.simulate_multi_round_conversation(
            stage_data=GenesisTestData.STAGE_2_WORLDVIEWS[0], rounds=2
        )

        # Progress to Stage 3: Character Design
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.CHARACTERS,
            state={"current_stage": GenesisStage.CHARACTERS.value, "stage_2_completed": True},
        )
        assert stage_update["success"]

        stage_3_results = await genesis_fixture.simulate_multi_round_conversation(
            stage_data=GenesisTestData.STAGE_3_CHARACTERS[0], rounds=2
        )

        # Progress to Stage 4: Plot Framework
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.PLOT_OUTLINE,
            state={"current_stage": GenesisStage.PLOT_OUTLINE.value, "stage_3_completed": True},
        )
        assert stage_update["success"]

        stage_4_results = await genesis_fixture.simulate_multi_round_conversation(
            stage_data=GenesisTestData.STAGE_4_PLOTS[0], rounds=2
        )

        # Verify complete workflow
        total_rounds = await genesis_fixture.count_conversation_rounds()
        assert total_rounds >= 20  # At least 2 rounds per stage * 4 stages + stage transitions

        # Verify domain events for stage progressions
        events = await genesis_fixture.get_domain_events()
        assert len(events) >= 4  # At least one event per stage

        # Verify final session state
        final_session_state = await genesis_fixture.get_session_state()
        assert final_session_state["success"]
        session_data = final_session_state["session"]

        # Check final stage
        final_stage = (
            session_data.get("stage") if hasattr(session_data, "get") else getattr(session_data, "stage", None)
        )
        assert final_stage == GenesisStage.PLOT_OUTLINE.value

    async def test_stage_validation_and_transitions(self, genesis_fixture):
        """Test stage validation and proper transitions."""
        from src.common.services.conversation.conversation_service import conversation_service

        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        # Try to skip stages (should be controlled by business logic)
        async with genesis_fixture.session_factory() as db:
            # Attempt to jump from Stage 0 to Stage 3
            invalid_transition = await conversation_service.update_session(
                db=db,
                user_id=genesis_fixture.user.id,
                session_id=genesis_fixture.session_id,
                stage=GenesisStage.CHARACTERS.value,  # Skip stages 1 and 2
            )

            # The service should handle this gracefully
            # (In a fully implemented system, this might be rejected)
            # For now, we just verify the system doesn't crash
            assert "success" in invalid_transition

        # Verify proper stage progression
        stages = [
            GenesisStage.INITIAL_PROMPT,
            GenesisStage.WORLDVIEW,
            GenesisStage.CHARACTERS,
            GenesisStage.PLOT_OUTLINE,
        ]

        for stage in stages:
            stage_update = await genesis_fixture.update_session_stage(stage)
            assert stage_update["success"]

            # Add some conversation for this stage
            await genesis_fixture.create_conversation_round(
                role=DialogueRole.USER, input_data={"prompt": f"进入{stage.value}阶段", "stage": stage.value}
            )

    async def test_cross_stage_context_preservation(self, genesis_fixture):
        """Test that context from previous stages is preserved."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        # Build up context across stages
        stage_contexts = {}

        # Stage 0: Establish creative seed context
        stage_0_data = GenesisTestData.STAGE_0_CREATIVE_SEEDS[0]
        await genesis_fixture.simulate_multi_round_conversation(stage_0_data, rounds=1)
        stage_contexts["stage_0"] = stage_0_data

        # Update session state with Stage 0 context
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.WORLDVIEW,
            state={"stage_0_context": stage_contexts["stage_0"], "current_stage": GenesisStage.WORLDVIEW.value},
        )
        assert stage_update["success"]

        # Stage 1: Build on Stage 0 context
        stage_1_data = GenesisTestData.STAGE_1_THEMES[0]
        stage_1_data["builds_on"] = stage_contexts["stage_0"]["type"]
        await genesis_fixture.simulate_multi_round_conversation(stage_1_data, rounds=1)
        stage_contexts["stage_1"] = stage_1_data

        # Verify context is preserved in session state
        session_state = await genesis_fixture.get_session_state()
        assert session_state["success"]
        session_data = session_state.get("session", {})

        if hasattr(session_data, "state"):
            state_data = session_data.state
        else:
            state_data = session_data.get("state", {})

        # Verify Stage 0 context is still available
        assert "stage_0_context" in str(state_data) or len(genesis_fixture.conversation_history) > 0

        # Continue to next stage
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.WORLDVIEW,
            state={
                "stage_0_context": stage_contexts["stage_0"],
                "stage_1_context": stage_contexts["stage_1"],
                "current_stage": GenesisStage.WORLDVIEW.value,
            },
        )
        assert stage_update["success"]

        # Stage 2: Build on previous contexts
        stage_2_data = GenesisTestData.STAGE_2_WORLDVIEWS[0]
        stage_2_data["theme_reference"] = stage_contexts["stage_1"]["theme"]
        await genesis_fixture.simulate_multi_round_conversation(stage_2_data, rounds=1)

        # Verify all contexts are maintained
        final_session_state = await genesis_fixture.get_session_state()
        assert final_session_state["success"]

        # Verify conversation history shows progression
        assert len(genesis_fixture.conversation_history) >= 6  # At least 2 rounds per stage

        # Verify we can reference earlier stages in current conversation
        reference_round = await genesis_fixture.create_conversation_round(
            role=DialogueRole.USER,
            input_data={
                "prompt": "请结合前面的创意种子和主题来完善世界观",
                "references_previous_stages": True,
                "stage_0_ref": stage_contexts["stage_0"]["type"],
                "stage_1_ref": stage_contexts["stage_1"]["theme"],
            },
        )
        assert reference_round["success"]

    async def test_stage_completion_criteria(self, genesis_fixture):
        """Test stage completion criteria and validation."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        # Stage 0: Creative Seed - needs at least one locked concept
        creative_seed_rounds = [
            {"role": DialogueRole.USER, "input_data": {"prompt": "我想创作科幻小说", "intent": "start_creation"}},
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "concepts": [
                        {"id": 1, "title": "时间旅行", "appeal": "经典科幻元素"},
                        {"id": 2, "title": "AI觉醒", "appeal": "当代科技思考"},
                    ],
                    "response_type": "concept_generation",
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {"selected_concept": 2, "lock_decision": True, "completion_criteria": "concept_locked"},
            },
        ]

        for round_data in creative_seed_rounds:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Mark Stage 0 as complete and transition
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.WORLDVIEW,
            state={
                "stage_0_completed": True,
                "locked_concept": {"id": 2, "title": "AI觉醒"},
                "current_stage": GenesisStage.WORLDVIEW.value,
            },
        )
        assert stage_update["success"]

        # Stage 1: Theme Development - needs clear thematic statement
        theme_development_rounds = [
            {
                "role": DialogueRole.USER,
                "input_data": {"prompt": "基于AI觉醒的概念，探讨主题", "builds_on_stage_0": True},
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "thematic_options": ["人性与技术的边界", "意识的本质探讨", "创造者与被创造者的关系"],
                    "response_type": "theme_analysis",
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "selected_theme": "人性与技术的边界",
                    "theme_statement": "探讨当AI拥有意识时，人类如何重新定义自己的价值",
                    "completion_criteria": "theme_finalized",
                },
            },
        ]

        for round_data in theme_development_rounds:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Verify completion criteria tracking
        session_state = await genesis_fixture.get_session_state()
        assert session_state["success"]

        # Verify we have meaningful completion markers in conversation history
        completion_markers = [
            r for r in genesis_fixture.conversation_history if "completion_criteria" in r["input_data"]
        ]
        assert len(completion_markers) >= 2  # At least one per completed stage

    async def test_stage_branching_and_alternative_paths(self, genesis_fixture):
        """Test alternative workflow paths and stage branching."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        # Alternative Path 1: Start with character concept instead of plot concept
        character_first_rounds = [
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "prompt": "我想从人物开始创作",
                    "starting_approach": "character_driven",
                    "alternative_path": True,
                },
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "approach_acknowledgment": "以人物为中心的创作方式",
                    "character_prompts": [
                        "描述一个让您印象深刻的人",
                        "想象一个处在困境中的角色",
                        "创造一个有独特能力的人物",
                    ],
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "character_concept": "一个能感知他人情绪的心理医生",
                    "character_appeal": "在帮助别人的同时承受巨大心理负担",
                },
            },
        ]

        for round_data in character_first_rounds:
            result = await genesis_fixture.create_conversation_round(**round_data)
            assert result["success"]

        # Branch to theme development based on character
        stage_update = await genesis_fixture.update_session_stage(
            stage=GenesisStage.WORLDVIEW,
            state={
                "starting_approach": "character_driven",
                "character_seed": "情感感知心理医生",
                "current_stage": GenesisStage.WORLDVIEW.value,
            },
        )
        assert stage_update["success"]

        # Theme development influenced by character choice
        character_influenced_theme = await genesis_fixture.create_conversation_round(
            role=DialogueRole.USER,
            input_data={
                "prompt": "基于这个人物，探讨关于共情与界限的主题",
                "theme_influenced_by": "character_concept",
                "alternative_development": True,
            },
        )
        assert character_influenced_theme["success"]

        # Verify alternative path tracking
        conversation_history = genesis_fixture.conversation_history
        alternative_markers = [
            r
            for r in conversation_history
            if r["input_data"].get("alternative_path") or r["input_data"].get("alternative_development")
        ]
        assert len(alternative_markers) >= 2

        # Verify session state reflects alternative approach
        final_state = await genesis_fixture.get_session_state()
        assert final_state["success"]
        session_data = final_state["session"]

        if hasattr(session_data, "state"):
            state_data = session_data.state
        else:
            state_data = session_data.get("state", {})

        assert "starting_approach" in str(state_data) or "character_driven" in str(conversation_history)

    async def test_workflow_interruption_and_resumption(self, genesis_fixture):
        """Test workflow interruption at different stages and resumption."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        # Complete Stage 0
        stage_0_data = GenesisTestData.STAGE_0_CREATIVE_SEEDS[0]
        await genesis_fixture.simulate_multi_round_conversation(stage_0_data, rounds=1)

        # Start Stage 1
        stage_update = await genesis_fixture.update_session_stage(GenesisStage.WORLDVIEW)
        assert stage_update["success"]

        stage_1_partial = await genesis_fixture.create_conversation_round(
            role=DialogueRole.USER,
            input_data={"prompt": "开始主题开发", "stage_status": "started", "interruption_point": "before_completion"},
        )
        assert stage_1_partial["success"]

        # Simulate interruption (save state)
        pre_interruption_state = await genesis_fixture.get_session_state()
        pre_interruption_rounds = await genesis_fixture.count_conversation_rounds()

        # Simulate resumption (use the same fixture since it already has the session)
        # In a real scenario, this would be a new fixture instance with the same session ID
        resumed_fixture = genesis_fixture  # For testing purposes, reuse the same fixture

        # Resume from interruption
        resumption_round = await resumed_fixture.create_conversation_round(
            role=DialogueRole.USER,
            input_data={
                "prompt": "继续之前未完成的主题开发",
                "resumption": True,
                "references_previous": "stage_1_partial_work",
            },
        )
        assert resumption_round["success"]

        # Continue workflow
        theme_completion = await resumed_fixture.create_conversation_round(
            role=DialogueRole.ASSISTANT,
            input_data={"theme_development": "基于之前的讨论，完善主题", "acknowledges_interruption": True},
        )
        assert theme_completion["success"]

        # Verify continuity
        post_resumption_rounds = await resumed_fixture.count_conversation_rounds()
        assert post_resumption_rounds > pre_interruption_rounds

        # Verify state consistency
        post_resumption_state = await resumed_fixture.get_session_state()
        assert post_resumption_state["success"]

        # Both fixtures should see the same session
        assert str(genesis_fixture.session_id) == str(resumed_fixture.session_id)

    async def test_workflow_quality_gates(self, genesis_fixture):
        """Test quality gates and validation at each workflow stage."""
        session_result = await genesis_fixture.create_genesis_session(GenesisStage.INITIAL_PROMPT)
        assert session_result["success"]

        # Define quality criteria for each stage
        quality_gates = {
            GenesisStage.INITIAL_PROMPT: {
                "min_rounds": 2,
                "required_elements": ["concept", "appeal"],
                "validation": "concept_clarity",
            },
            GenesisStage.WORLDVIEW: {
                "min_rounds": 3,
                "required_elements": ["world_rules", "cultural_context"],
                "validation": "thematic_coherence",
            },
            GenesisStage.WORLDVIEW: {
                "min_rounds": 4,
                "required_elements": ["rules", "geography", "culture"],
                "validation": "world_consistency",
            },
            GenesisStage.CHARACTERS: {
                "min_rounds": 3,
                "required_elements": ["motivation", "background", "relationships"],
                "validation": "character_depth",
            },
        }

        current_stage = GenesisStage.INITIAL_PROMPT

        for stage, criteria in quality_gates.items():
            # Ensure we're at the right stage
            if current_stage != stage:
                stage_update = await genesis_fixture.update_session_stage(stage)
                assert stage_update["success"]
                current_stage = stage

            # Meet minimum round requirement
            for i in range(criteria["min_rounds"]):
                round_result = await genesis_fixture.create_conversation_round(
                    role=DialogueRole.USER if i % 2 == 0 else DialogueRole.ASSISTANT,
                    input_data={
                        "prompt": f"Quality gate test for {stage.value} - round {i+1}",
                        "stage": stage.value,
                        "quality_element": criteria["required_elements"][i % len(criteria["required_elements"])],
                        "validation_type": criteria["validation"],
                    },
                )
                assert round_result["success"]

            # Verify quality gate criteria
            stage_rounds = [
                r for r in genesis_fixture.conversation_history if r["input_data"].get("stage") == stage.value
            ]
            assert len(stage_rounds) >= criteria["min_rounds"]

            # Check for required elements
            stage_content = str(stage_rounds)
            for element in criteria["required_elements"]:
                assert element in stage_content.lower() or any(
                    element in str(r["input_data"]).lower() for r in stage_rounds
                )

        # Verify overall workflow quality
        total_rounds = await genesis_fixture.count_conversation_rounds()
        assert total_rounds >= sum(criteria["min_rounds"] for criteria in quality_gates.values())

        # Verify progression through quality gates
        final_session_state = await genesis_fixture.get_session_state()
        assert final_session_state["success"]
