"""Genesis流程服务实现

管理Genesis流程的生命周期，包括创建、推进、完成等操作。
"""

from datetime import UTC, datetime

# Forward declaration to avoid circular imports
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.genesis.flow_repository import GenesisFlowRepository
from src.common.repositories.genesis.stage_repository import GenesisStageRepository
from src.models.genesis_flows import GenesisFlow
from src.schemas.enums import GenesisStage, GenesisStatus, StageStatus
from src.schemas.genesis.stage_config_schemas import (
    check_stage_config_completeness,
    is_stage_advancement,
)

if TYPE_CHECKING:
    from src.common.services.genesis.stage_session_service import GenesisStageSessionService


class GenesisFlowService:
    """Genesis流程服务，管理流程生命周期"""

    def __init__(
        self,
        flow_repository: GenesisFlowRepository,
        db_session: AsyncSession,
        stage_repository: GenesisStageRepository | None = None,
        stage_session_service: "GenesisStageSessionService | None" = None,
    ):
        self.flow_repository = flow_repository
        self.stage_repository = stage_repository
        self.db_session = db_session
        self.stage_session_service = stage_session_service

    async def ensure_flow(self, novel_id: UUID) -> GenesisFlow:
        """
        确保指定小说存在Genesis流程，如果不存在则创建。
        如果是新创建的流程，会同时创建初始阶段记录。

        Args:
            novel_id: 小说ID

        Returns:
            Genesis流程实例
        """
        # 尝试查找现有流程
        existing_flow = await self.flow_repository.find_by_novel_id(novel_id)
        if existing_flow:
            return existing_flow

        # 创建新流程
        new_flow = await self.flow_repository.create(
            novel_id=novel_id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.INITIAL_PROMPT,
            state={},
            version=1,
        )

        # 创建初始阶段记录（如果有stage_repository）
        if self.stage_repository:
            await self.stage_repository.create(
                flow_id=new_flow.id,
                stage=GenesisStage.INITIAL_PROMPT,
                status=StageStatus.RUNNING,
                config={},
                iteration_count=0,
            )

        return new_flow

    async def get_flow(self, novel_id: UUID) -> GenesisFlow | None:
        """
        获取指定小说的Genesis流程。

        Args:
            novel_id: 小说ID

        Returns:
            Genesis流程实例，如果不存在返回None
        """
        return await self.flow_repository.find_by_novel_id(novel_id)

    async def get_current_stage_id(self, flow: GenesisFlow) -> UUID | None:
        """
        获取流程当前阶段的Stage Record ID。

        Args:
            flow: Genesis流程实例

        Returns:
            当前阶段的Stage Record ID，如果不存在返回None
        """
        if not self.stage_repository or not flow.current_stage:
            return None

        # 查找当前阶段的Stage Record
        stages = await self.stage_repository.list_by_flow_id(flow_id=flow.id)

        # 找到当前阶段对应的Stage Record
        for stage_record in stages:
            if stage_record.stage == flow.current_stage:
                return stage_record.id

        return None

    async def get_all_stage_ids(self, flow: GenesisFlow) -> dict[GenesisStage, UUID]:
        """
        获取流程中所有阶段的Stage Record ID映射。

        Args:
            flow: Genesis流程实例

        Returns:
            从GenesisStage到Stage Record ID的映射字典
        """
        if not self.stage_repository:
            return {}

        # 获取流程的所有Stage Records
        stages = await self.stage_repository.list_by_flow_id(flow_id=flow.id)

        # 创建从stage类型到ID的映射
        stage_ids = {}
        for stage_record in stages:
            stage_ids[stage_record.stage] = stage_record.id

        return stage_ids

    async def get_flow_by_id(self, flow_id: UUID) -> GenesisFlow | None:
        """
        根据流程ID获取Genesis流程。

        Args:
            flow_id: 流程ID

        Returns:
            Genesis流程实例，如果不存在返回None
        """
        return await self.flow_repository.find_by_id(flow_id)

    async def advance_stage(
        self,
        flow_id: UUID,
        next_stage: GenesisStage,
        expected_version: int | None = None,
        state_updates: dict[str, Any] | None = None,
    ) -> GenesisFlow | None:
        """
        推进流程到下一个阶段。

        在向前推进阶段时，会校验当前阶段的必填字段是否已经配置完整。
        回到之前的阶段时不需要校验。

        Args:
            flow_id: 流程ID
            next_stage: 下一个阶段
            expected_version: 预期版本号（用于乐观锁）
            state_updates: 状态更新数据

        Returns:
            更新后的流程实例，如果版本冲突或不存在返回None

        Raises:
            ValueError: 当向前推进时当前阶段配置不完整
        """
        # 获取当前流程
        current_flow = await self.flow_repository.find_by_id(flow_id)
        if not current_flow:
            return None

        # 检查是否是向前推进（需要校验）还是回退（不需要校验）
        if is_stage_advancement(current_flow.current_stage, next_stage):
            # 向前推进，需要校验当前阶段配置完整性
            await self._validate_current_stage_config(flow_id, current_flow.current_stage)

        # 确保目标阶段记录和会话存在（如果不存在则创建）
        await self._ensure_stage_record_and_session(flow_id, current_flow.novel_id, next_stage)

        # 合并状态更新
        new_state = current_flow.state or {}
        if state_updates:
            new_state.update(state_updates)

        # 更新流程
        updated_flow = await self.flow_repository.update(
            flow_id=flow_id,
            current_stage=next_stage,
            state=new_state,
            expected_version=expected_version,
        )

        return updated_flow

    async def _validate_current_stage_config(self, flow_id: UUID, current_stage: GenesisStage) -> None:
        """
        校验当前阶段的配置完整性。

        Args:
            flow_id: 流程ID
            current_stage: 当前阶段

        Raises:
            ValueError: 当前阶段配置不完整时
        """
        if not self.stage_repository:
            # 没有 stage repository，跳过校验
            return

        # 获取当前阶段的记录
        current_stage_record = await self.stage_repository.find_by_flow_and_stage(flow_id, current_stage)

        if not current_stage_record:
            # 当前阶段记录不存在，可能是系统状态不一致
            # 为了避免阻塞用户操作，这里不抛出异常，只是跳过校验
            return

        # 检查配置完整性
        validation_result = check_stage_config_completeness(current_stage, current_stage_record.config)

        if not validation_result["is_complete"]:
            # 配置不完整，抛出异常
            # 优先使用中文字段名，如果没有则使用英文字段名
            missing_fields_chinese = validation_result.get("missing_fields_chinese", [])
            missing_fields = ", ".join(missing_fields_chinese) if missing_fields_chinese else ", ".join(validation_result["missing_fields"])
            raise ValueError(
                f"Cannot advance from stage {current_stage.value}: "
                f"Required fields are missing - {missing_fields}. "
                f"Please complete the current stage configuration before proceeding."
            )

    async def _ensure_stage_record_and_session(self, flow_id: UUID, novel_id: UUID, stage: GenesisStage) -> None:
        """
        确保指定阶段的记录和主要会话存在，如果不存在则创建。

        Args:
            flow_id: 流程ID
            novel_id: 小说ID
            stage: 目标阶段
        """
        # 检查是否已存在该阶段的记录
        existing_stage = await self.stage_repository.find_by_flow_and_stage(flow_id, stage)

        if not existing_stage:
            # 如果不存在，则创建新的阶段记录
            new_stage = await self.stage_repository.create(
                flow_id=flow_id,
                stage=stage,
                status=StageStatus.RUNNING,
                config={},
                result={},
                iteration_count=0,
                metrics={},
            )

            # 为新阶段创建主要会话（如果有 stage session service）
            if self.stage_session_service:
                try:
                    await self.stage_session_service.create_and_bind_session(
                        db=self.db_session,
                        stage_id=new_stage.id,
                        novel_id=novel_id,
                        is_primary=True,
                        session_kind="user_interaction",
                    )
                except Exception as e:
                    # 如果创建会话失败，记录错误但不阻止 stage 切换
                    # 用户可以在需要时手动创建会话
                    print(f"Warning: Failed to create session for stage {stage}: {e}")
        else:
            # 阶段记录存在，检查是否有主要会话，如果没有则创建
            if self.stage_session_service:
                # 这里可以检查是否有主要会话，如果没有则创建
                # 但为了简化，我们只在创建新 stage 时创建 session
                pass

    async def complete_flow(
        self,
        flow_id: UUID,
        expected_version: int | None = None,
        final_state: dict[str, Any] | None = None,
    ) -> GenesisFlow | None:
        """
        完成Genesis流程。

        Args:
            flow_id: 流程ID
            expected_version: 预期版本号（用于乐观锁）
            final_state: 最终状态数据

        Returns:
            更新后的流程实例，如果版本冲突或不存在返回None
        """
        updated_flow = await self.flow_repository.update(
            flow_id=flow_id,
            status=GenesisStatus.COMPLETED,
            current_stage=GenesisStage.FINISHED,
            state=final_state,
            expected_version=expected_version,
        )

        return updated_flow

    async def pause_flow(
        self,
        flow_id: UUID,
        expected_version: int | None = None,
        pause_reason: str | None = None,
    ) -> GenesisFlow | None:
        """
        暂停Genesis流程。

        Args:
            flow_id: 流程ID
            expected_version: 预期版本号（用于乐观锁）
            pause_reason: 暂停原因

        Returns:
            更新后的流程实例，如果版本冲突或不存在返回None
        """
        # 获取当前状态并添加暂停信息
        current_flow = await self.flow_repository.find_by_id(flow_id)
        if not current_flow:
            return None

        state_updates = current_flow.state or {}
        if pause_reason:
            state_updates["pause_reason"] = pause_reason
            state_updates["paused_at"] = datetime.now(UTC).isoformat()

        updated_flow = await self.flow_repository.update(
            flow_id=flow_id,
            status=GenesisStatus.PAUSED,
            state=state_updates,
            expected_version=expected_version,
        )

        return updated_flow

    async def abandon_flow(
        self,
        flow_id: UUID,
        expected_version: int | None = None,
        abandon_reason: str | None = None,
    ) -> GenesisFlow | None:
        """
        放弃Genesis流程。

        Args:
            flow_id: 流程ID
            expected_version: 预期版本号（用于乐观锁）
            abandon_reason: 放弃原因

        Returns:
            更新后的流程实例，如果版本冲突或不存在返回None
        """
        # 获取当前状态并添加放弃信息
        current_flow = await self.flow_repository.find_by_id(flow_id)
        if not current_flow:
            return None

        state_updates = current_flow.state or {}
        if abandon_reason:
            state_updates["abandon_reason"] = abandon_reason
            state_updates["abandoned_at"] = datetime.now(UTC).isoformat()

        updated_flow = await self.flow_repository.update(
            flow_id=flow_id,
            status=GenesisStatus.ABANDONED,
            state=state_updates,
            expected_version=expected_version,
        )

        return updated_flow

    async def list_flows_by_status(
        self,
        status: GenesisStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisFlow]:
        """
        按状态列出Genesis流程。

        Args:
            status: 流程状态
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            流程列表
        """
        return await self.flow_repository.list_by_status(
            status=status,
            limit=limit,
            offset=offset,
        )
