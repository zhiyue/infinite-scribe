"""
Shared fixtures and test data for Genesis conversation integration tests.

This module provides common test infrastructure used across all Genesis
conversation test modules to ensure consistency and reduce duplication.
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from src.common.services.conversation.conversation_service import conversation_service
from src.models.conversation import ConversationRound
from src.models.event import DomainEvent
from src.models.novel import Novel
from src.models.user import User
from src.schemas.enums import GenesisStage, GenesisStatus
from src.schemas.novel.dialogue import DialogueRole, ScopeType


class GenesisTestData:
    """Test data templates for different Genesis stages."""

    STAGE_0_CREATIVE_SEEDS = [
        {"type": "concept_collision", "prompt": "修仙 + 克苏鲁神话的世界设定", "elements": ["修仙", "克苏鲁"]},
        {"type": "what_if", "prompt": "假如人的寿命可以当作货币交易", "core_assumption": "寿命交易机制"},
        {"type": "unique_system", "prompt": "每个人都能看到他人的好感度数值", "system_rules": "好感度可视化系统"},
    ]

    STAGE_1_THEMES = [
        {"theme": "自我与命运的抗争", "core_emotion": "不甘与坚韧", "value_tension": "个人意志 vs 天命既定"},
        {"theme": "记忆与身份的本质", "core_emotion": "迷茫与寻找", "value_tension": "过去的自己 vs 现在的认知"},
    ]

    STAGE_2_WORLDVIEWS = [
        {
            "world_name": "灵气复苏后的现代都市",
            "rules": ["灵气浓度影响科技运作", "修炼者与普通人的社会分层"],
            "geography": "现代城市框架，但有灵脉、禁区等特殊地点",
            "culture": "传统修炼文化与现代文明的融合冲突",
        }
    ]

    STAGE_3_CHARACTERS = [
        {
            "name": "李志明",
            "role": "主角",
            "motivation": "寻找失踪的妹妹",
            "background": "普通上班族，意外获得修炼天赋",
            "relationships": {"妹妹": "失踪的血亲", "师父": "神秘引路人"},
        }
    ]

    STAGE_4_PLOTS = [
        {
            "structure": "三幕式",
            "act1": "日常生活被打破，踏入修炼世界",
            "act2": "在修炼中寻找妹妹线索，遇到更大阴谋",
            "act3": "揭开真相，拯救妹妹和世界",
        }
    ]


class GenesisConversationTestFixture:
    """Test fixture for Genesis conversation testing."""

    def __init__(self, session_factory, user: User, novel: Novel):
        self.session_factory = session_factory
        self.user = user
        self.novel = novel
        self.session_id: UUID | None = None
        self.conversation_history: list[dict[str, Any]] = []

    async def create_genesis_session(self, stage: GenesisStage = GenesisStage.INITIAL_PROMPT) -> dict[str, Any]:
        """Create a new Genesis conversation session."""
        async with self.session_factory() as db:
            result = await conversation_service.create_session(
                db=db,
                user_id=self.user.id,
                scope_type=ScopeType.GENESIS,
                scope_id=str(self.novel.id),
                stage=stage.value,
                initial_state={"current_stage": stage.value, "status": GenesisStatus.IN_PROGRESS.value},
            )

            if result["success"]:
                session = result["session"]
                self.session_id = session.id if hasattr(session, "id") else session["id"]

            return result

    async def create_conversation_round(
        self,
        role: DialogueRole,
        input_data: dict[str, Any],
        model: str | None = "test-model",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a conversation round and track it."""
        if not self.session_id:
            raise ValueError("Session not created yet")

        async with self.session_factory() as db:
            result = await conversation_service.create_round(
                db=db,
                user_id=self.user.id,
                session_id=self.session_id,
                role=role,
                input_data=input_data,
                model=model,
                correlation_id=correlation_id or str(uuid4()),
            )

            if result["success"]:
                self.conversation_history.append(
                    {
                        "role": role,
                        "input_data": input_data,
                        "result": result,
                        "timestamp": result.get("round", {}).get("created_at"),
                    }
                )

            return result

    async def simulate_multi_round_conversation(
        self, stage_data: dict[str, Any], rounds: int = 3
    ) -> list[dict[str, Any]]:
        """Simulate a multi-round conversation for a Genesis stage."""
        results = []

        # Initial user prompt
        user_prompt = {"prompt": f"我想要基于以下内容进行创作: {stage_data}", "stage_context": stage_data}
        result = await self.create_conversation_round(role=DialogueRole.USER, input_data=user_prompt)
        results.append(result)

        # Simulate AI responses and user feedback rounds
        for round_num in range(1, rounds + 1):
            # AI response
            ai_response = {
                "generated_content": f"基于您的需求，我为您生成了 {round_num} 个方案...",
                "options": [f"方案{i}" for i in range(1, 4)],
                "round_number": round_num,
            }
            result = await self.create_conversation_round(role=DialogueRole.ASSISTANT, input_data=ai_response)
            results.append(result)

            # User feedback (except for the last round)
            if round_num < rounds:
                feedback = {
                    "selected_option": 1,
                    "feedback": f"第{round_num}轮的反馈：请在方案1的基础上增加更多细节",
                    "refinement_request": True,
                }
                result = await self.create_conversation_round(role=DialogueRole.USER, input_data=feedback)
                results.append(result)

        return results

    async def get_session_state(self) -> dict[str, Any]:
        """Get current session state."""
        if not self.session_id:
            return {}

        async with self.session_factory() as db:
            return await conversation_service.get_session(db, self.user.id, self.session_id)

    async def get_domain_events(self) -> list[DomainEvent]:
        """Get all domain events for this session."""
        if not self.session_id:
            return []

        async with self.session_factory() as db:
            result = await db.execute(
                select(DomainEvent)
                .where(DomainEvent.aggregate_id == str(self.session_id))
                .order_by(DomainEvent.created_at)
            )
            return list(result.scalars().all())

    async def count_conversation_rounds(self) -> int:
        """Count total conversation rounds."""
        if not self.session_id:
            return 0

        async with self.session_factory() as db:
            result = await db.scalar(
                select(func.count())
                .select_from(ConversationRound)
                .where(ConversationRound.session_id == self.session_id)
            )
            return result or 0

    async def update_session_stage(self, stage: GenesisStage, state: dict[str, Any] = None) -> dict[str, Any]:
        """Update session stage with optional state."""
        if not self.session_id:
            raise ValueError("Session not created yet")

        async with self.session_factory() as db:
            return await conversation_service.update_session(
                db=db,
                user_id=self.user.id,
                session_id=self.session_id,
                stage=stage.value,
                state=state or {"current_stage": stage.value},
            )


class DetailedConversationPatterns:
    """Realistic conversation patterns for Genesis creative workflows."""

    @staticmethod
    def creative_seed_conversation_pattern() -> list[dict[str, Any]]:
        """Simulate realistic creative seed development conversation."""
        return [
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "prompt": "我想写一个科幻小说，但是没有具体的想法",
                    "context": "beginner_user",
                    "request_type": "inspiration",
                },
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response_type": "multiple_options",
                    "options": [
                        {
                            "id": 1,
                            "title": "时间悖论",
                            "description": "主角发现可以向过去发送信息，但每次改变都带来意想不到的后果",
                            "genre_tags": ["time_travel", "paradox", "butterfly_effect"],
                            "appeal": "探索因果关系和选择的重量",
                        },
                        {
                            "id": 2,
                            "title": "意识上传",
                            "description": "人类可以将意识上传到数字世界，但身份和真实性成为问题",
                            "genre_tags": ["cyberpunk", "identity", "virtual_reality"],
                            "appeal": "讨论什么定义了真正的自我",
                        },
                    ],
                    "guidance": "您可以选择一个感兴趣的方向，或告诉我您更偏好什么类型的科幻元素？",
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "selected_option": 2,
                    "feedback": "意识上传的概念很有趣，但我希望故事更加人性化一些",
                    "additional_preferences": {"tone": "emotional", "focus": "human_relationships"},
                },
            },
        ]

    @staticmethod
    def theme_development_conversation_pattern() -> list[dict[str, Any]]:
        """Simulate theme development conversation."""
        return [
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "prompt": "基于刚才的创意种子，我想深入探讨主题",
                    "previous_context": "意识上传、数字复活的故事概念",
                    "goal": "确立清晰的主题思想",
                },
            },
            {
                "role": DialogueRole.ASSISTANT,
                "input_data": {
                    "response_type": "theme_analysis",
                    "potential_themes": [
                        {
                            "theme": "真爱超越生死边界",
                            "core_message": "真正的爱情不受物理形式限制",
                            "emotional_arc": "从痛苦→接受→重新定义爱情",
                        },
                        {
                            "theme": "放手是最深的爱",
                            "core_message": "真正的爱包含让所爱之人安息的勇气",
                            "emotional_arc": "执着→挣扎→释然→成长",
                        },
                    ],
                },
            },
            {
                "role": DialogueRole.USER,
                "input_data": {
                    "theme_preference": "mixed_approach",
                    "feedback": "我希望结合这两个主题，既有爱情的坚持，也有放手的智慧",
                },
            },
        ]


# Test quality metrics
class ConversationQualityMetrics:
    """Utilities for measuring conversation quality."""

    @staticmethod
    def calculate_engagement_score(conversation_history: list[dict]) -> float:
        """Calculate engagement score based on conversation patterns."""
        if not conversation_history:
            return 0.0

        total_score = 0
        for round_data in conversation_history:
            input_data = round_data["input_data"]

            # Length and detail bonus
            content_length = len(str(input_data))
            length_score = min(content_length / 1000, 1.0)

            # Specificity bonus
            specificity_indicators = ["reasoning", "feedback", "additional", "specific", "detail"]
            specificity_score = sum(0.2 for indicator in specificity_indicators if indicator in str(input_data).lower())

            # Interactivity bonus
            interactive_elements = ["question", "choice", "option", "prefer", "want"]
            interactivity_score = sum(0.1 for element in interactive_elements if element in str(input_data).lower())

            round_score = length_score + min(specificity_score, 1.0) + min(interactivity_score, 0.5)
            total_score += round_score

        return total_score / len(conversation_history)

    @staticmethod
    def analyze_conversation_flow(conversation_history: list[dict]) -> dict[str, Any]:
        """Analyze conversation flow patterns."""
        if len(conversation_history) < 2:
            return {"flow_quality": "insufficient_data"}

        # Check role alternation
        roles = [r["role"] for r in conversation_history]
        alternation_breaks = sum(1 for i in range(1, len(roles)) if roles[i] == roles[i - 1])
        alternation_score = 1.0 - (alternation_breaks / len(roles))

        # Check progression (increasing detail/specificity)
        content_lengths = [len(str(r["input_data"])) for r in conversation_history]
        progression_score = 1.0 if content_lengths[-1] > content_lengths[0] else 0.5

        return {
            "alternation_score": alternation_score,
            "progression_score": progression_score,
            "total_rounds": len(conversation_history),
            "flow_quality": "good" if alternation_score > 0.8 and progression_score > 0.5 else "needs_improvement",
        }


# Pytest fixtures
@pytest.fixture
async def test_user_and_novel(pg_session):
    """Create test user and novel for conversation tests."""
    user = User(
        username=f"genesis_test_user_{uuid4().hex[:8]}",
        email=f"genesis_test_{uuid4().hex[:8]}@example.com",
        password_hash="test_hash",
    )
    pg_session.add(user)
    await pg_session.flush()

    novel = Novel(user_id=user.id, title=f"Genesis Test Novel {uuid4().hex[:8]}", theme="Test Theme")
    pg_session.add(novel)
    await pg_session.commit()

    return user, novel


@pytest.fixture
async def genesis_fixture(pg_session, test_user_and_novel):
    """Create Genesis conversation test fixture."""
    user, novel = test_user_and_novel
    
    # Create a session factory-like wrapper for the existing session
    class SessionWrapper:
        def __init__(self, session):
            self.session = session
            
        def __call__(self):
            return self.session_context()
            
        async def __aenter__(self):
            return self.session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
        def session_context(self):
            return self
    
    session_factory = SessionWrapper(pg_session)
    return GenesisConversationTestFixture(session_factory, user, novel)
