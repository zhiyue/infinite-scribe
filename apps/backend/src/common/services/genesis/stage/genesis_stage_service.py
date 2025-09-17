"""Genesis阶段服务实现

管理Genesis阶段的创建、完成、会话绑定等操作。
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation.session_repository import ConversationSessionRepository
from src.common.repositories.genesis.flow_repository import GenesisFlowRepository
from src.common.repositories.genesis.stage_repository import GenesisStageRepository
from src.common.repositories.genesis.stage_session_repository import GenesisStageSessionRepository
from src.models.genesis_flows import GenesisStageRecord, GenesisStageSession
from src.schemas.enums import GenesisStage, GenesisStatus, StageSessionStatus, StageStatus


class GenesisStageService:
    """Genesis阶段服务，管理阶段生命周期和会话绑定"""

    def __init__(
        self,
        flow_repository: GenesisFlowRepository,
        stage_repository: GenesisStageRepository,
        stage_session_repository: GenesisStageSessionRepository,
        conversation_session_repository: ConversationSessionRepository,
        db_session: AsyncSession,
    ):
        self.flow_repository = flow_repository
        self.stage_repository = stage_repository
        self.stage_session_repository = stage_session_repository
        self.conversation_session_repository = conversation_session_repository
        self.db_session = db_session

    async def create_stage(
        self,
        flow_id: UUID,
        stage: GenesisStage,
        config: dict[str, Any] | None = None,
    ) -> GenesisStageRecord:
        """
        创建新的阶段记录。

        Args:
            flow_id: 流程ID
            stage: 阶段类型
            config: 阶段配置

        Returns:
            创建的阶段记录

        Raises:
            ValueError: 如果流程不存在
        """
        # 验证流程存在
        flow = await self.flow_repository.find_by_id(flow_id)
        if not flow:
            raise ValueError(f"Genesis flow with ID {flow_id} not found")

        # 创建阶段记录
        stage_record = await self.stage_repository.create(
            flow_id=flow_id,
            stage=stage,
            status=StageStatus.RUNNING,
            config=config or {},
            iteration_count=0,
        )

        # 更新阶段记录的开始时间
        await self.stage_repository.update(
            stage_id=stage_record.id,
            # 在实际实现中，这里应该直接设置started_at字段
            # 目前先通过config记录
            config={**(config or {}), "started_at": datetime.now(UTC).isoformat()},
        )

        await self.db_session.commit()
        return stage_record

    async def complete_stage(
        self,
        stage_id: UUID,
        result: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> GenesisStageRecord | None:
        """
        完成阶段并记录结果。

        Args:
            stage_id: 阶段ID
            result: 阶段产出结果
            metrics: 阶段指标数据

        Returns:
            更新后的阶段记录，如果不存在返回None
        """
        updated_stage = await self.stage_repository.update(
            stage_id=stage_id,
            status=StageStatus.COMPLETED,
            result=result or {},
            metrics=metrics or {},
        )

        if updated_stage:
            # 将关联的会话状态设置为归档
            sessions = await self.stage_session_repository.list_by_stage_id(
                stage_id=stage_id,
                status=StageSessionStatus.ACTIVE,
            )

            for session in sessions:
                await self.stage_session_repository.update(
                    association_id=session.id,
                    status=StageSessionStatus.ARCHIVED,
                )

            # 自动推进流程到下一个阶段
            await self._auto_advance_flow_if_needed(updated_stage)

            await self.db_session.commit()

        return updated_stage

    async def add_stage_session(
        self,
        stage_id: UUID,
        session_id: UUID,
        is_primary: bool = False,
        session_kind: str | None = None,
    ) -> GenesisStageSession:
        """
        将现有会话绑定到阶段。

        Args:
            stage_id: 阶段ID
            session_id: 会话ID
            is_primary: 是否为主会话
            session_kind: 会话类别

        Returns:
            创建的关联记录

        Raises:
            ValueError: 如果阶段不存在或绑定校验失败
        """
        # 验证阶段存在
        stage_record = await self.stage_repository.find_by_id(stage_id)
        if not stage_record:
            raise ValueError(f"Stage with ID {stage_id} not found")

        # 验证会话存在并获取其scope信息用于绑定校验
        session = await self.conversation_session_repository.find_by_id(session_id)
        if not session:
            raise ValueError(f"Conversation session with ID {session_id} not found")

        # 绑定校验：验证scope_type和scope_id
        flow = await self.flow_repository.find_by_id(stage_record.flow_id)
        if not flow:
            raise ValueError(f"Flow with ID {stage_record.flow_id} not found")

        await self._validate_session_binding(session, flow.novel_id)

        # 如果设置为主会话，先清除其他主会话标记
        if is_primary:
            await self._clear_primary_sessions(stage_id)

        # 创建关联
        association = await self.stage_session_repository.create(
            stage_id=stage_id,
            session_id=session_id,
            status=StageSessionStatus.ACTIVE,
            is_primary=is_primary,
            session_kind=session_kind,
        )

        await self.db_session.commit()
        return association

    async def create_and_bind_session(
        self,
        stage_id: UUID,
        novel_id: UUID,
        is_primary: bool = False,
        session_kind: str | None = None,
    ) -> UUID:
        """
        创建新的对话会话并绑定到阶段。

        Args:
            stage_id: 阶段ID
            novel_id: 小说ID
            is_primary: 是否为主会话
            session_kind: 会话类别

        Returns:
            创建的会话ID

        Raises:
            ValueError: 如果阶段不存在
        """
        # 验证阶段存在
        stage_record = await self.stage_repository.find_by_id(stage_id)
        if not stage_record:
            raise ValueError(f"Stage with ID {stage_id} not found")

        # 创建新的对话会话
        session = await self.conversation_session_repository.create(
            scope_type="GENESIS",
            scope_id=str(novel_id),
            status="ACTIVE",
        )

        # 绑定到阶段
        await self.add_stage_session(
            stage_id=stage_id,
            session_id=session.id,
            is_primary=is_primary,
            session_kind=session_kind,
        )

        return session.id

    async def list_stage_sessions(
        self,
        stage_id: UUID,
        status: StageSessionStatus | None = None,
    ) -> list[GenesisStageSession]:
        """
        列出阶段的所有会话。

        Args:
            stage_id: 阶段ID
            status: 可选的状态过滤

        Returns:
            会话关联列表
        """
        return await self.stage_session_repository.list_by_stage_id(
            stage_id=stage_id,
            status=status,
        )

    async def get_primary_session(self, stage_id: UUID) -> GenesisStageSession | None:
        """
        获取阶段的主会话。

        Args:
            stage_id: 阶段ID

        Returns:
            主会话关联，如果没有返回None
        """
        return await self.stage_session_repository.find_primary_session_for_stage(stage_id)

    async def set_primary_session(
        self,
        stage_id: UUID,
        session_id: UUID,
    ) -> GenesisStageSession | None:
        """
        设置主会话。

        Args:
            stage_id: 阶段ID
            session_id: 会话ID

        Returns:
            更新后的主会话关联，如果不存在返回None
        """
        result = await self.stage_session_repository.set_primary_session(
            stage_id=stage_id,
            session_id=session_id,
        )

        if result:
            await self.db_session.commit()

        return result

    async def get_stage_by_id(self, stage_id: UUID) -> GenesisStageRecord | None:
        """
        根据ID获取阶段记录。

        Args:
            stage_id: 阶段ID

        Returns:
            阶段记录，如果不存在返回None
        """
        return await self.stage_repository.find_by_id(stage_id)

    async def list_stages_by_flow(
        self,
        flow_id: UUID,
        status: StageStatus | None = None,
    ) -> list[GenesisStageRecord]:
        """
        按流程ID列出阶段。

        Args:
            flow_id: 流程ID
            status: 可选的状态过滤

        Returns:
            阶段记录列表
        """
        return await self.stage_repository.list_by_flow_id(
            flow_id=flow_id,
            status=status,
        )

    async def _validate_session_binding(self, session, novel_id: UUID) -> None:
        """
        验证会话绑定的合法性。

        Args:
            session: 会话实例
            novel_id: 小说ID

        Raises:
            ValueError: 如果绑定校验失败
        """
        # 验证scope_type必须为GENESIS
        if session.scope_type != "GENESIS":
            raise ValueError(
                f"Cannot bind session with scope_type '{session.scope_type}' to Genesis stage. "
                "Only GENESIS sessions can be bound."
            )

        # 验证scope_id必须等于novel_id
        if session.scope_id != str(novel_id):
            raise ValueError(
                f"Cannot bind session with scope_id '{session.scope_id}' to novel {novel_id}. "
                "Session scope_id must match the novel_id."
            )

    async def _clear_primary_sessions(self, stage_id: UUID) -> None:
        """
        清除阶段的其他主会话标记。

        Args:
            stage_id: 阶段ID
        """
        # 获取当前的主会话
        current_primary = await self.stage_session_repository.find_primary_session_for_stage(stage_id)
        if current_primary:
            await self.stage_session_repository.update(
                association_id=current_primary.id,
                is_primary=False,
            )

    async def _auto_advance_flow_if_needed(self, completed_stage: GenesisStageRecord) -> None:
        """
        自动推进流程到下一个阶段（如果需要）。

        Args:
            completed_stage: 已完成的阶段记录
        """
        # 获取流程信息
        flow = await self.flow_repository.find_by_id(completed_stage.flow_id)
        if not flow:
            return

        # 确定下一个阶段
        next_stage = self._get_next_stage(completed_stage.stage)
        if not next_stage:
            # 如果没有下一个阶段，标记流程为完成
            await self.flow_repository.update(
                flow_id=flow.id,
                status=GenesisStatus.COMPLETED,
                current_stage=GenesisStage.FINISHED,
            )
            return

        # 检查是否应该自动推进
        if self._should_auto_advance(completed_stage.stage):
            await self.flow_repository.update(
                flow_id=flow.id,
                current_stage=next_stage,
            )

    def _get_next_stage(self, current_stage: GenesisStage) -> GenesisStage | None:
        """
        获取指定阶段的下一个阶段。

        Args:
            current_stage: 当前阶段

        Returns:
            下一个阶段，如果已是最后阶段则返回None
        """
        stage_progression = [
            GenesisStage.INITIAL_PROMPT,
            GenesisStage.WORLDVIEW,
            GenesisStage.CHARACTERS,
            GenesisStage.PLOT_OUTLINE,
            GenesisStage.FINISHED,
        ]

        try:
            current_index = stage_progression.index(current_stage)
            if current_index < len(stage_progression) - 1:
                return stage_progression[current_index + 1]
        except ValueError:
            pass

        return None

    def _should_auto_advance(self, completed_stage: GenesisStage) -> bool:
        """
        判断是否应该自动推进到下一个阶段。

        Args:
            completed_stage: 已完成的阶段

        Returns:
            是否应该自动推进
        """
        # 默认情况下，所有阶段完成后都自动推进
        # 在实际实现中，可能需要根据业务规则调整
        return completed_stage != GenesisStage.FINISHED
