"""Genesis流程服务实现

管理Genesis流程的生命周期，包括创建、推进、完成等操作。
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.genesis.flow_repository import GenesisFlowRepository
from src.models.genesis_flows import GenesisFlow
from src.schemas.enums import GenesisStage, GenesisStatus


class GenesisFlowService:
    """Genesis流程服务，管理流程生命周期"""

    def __init__(
        self,
        flow_repository: GenesisFlowRepository,
        db_session: AsyncSession,
    ):
        self.flow_repository = flow_repository
        self.db_session = db_session

    async def ensure_flow(self, novel_id: UUID) -> GenesisFlow:
        """
        确保指定小说存在Genesis流程，如果不存在则创建。

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

        Args:
            flow_id: 流程ID
            next_stage: 下一个阶段
            expected_version: 预期版本号（用于乐观锁）
            state_updates: 状态更新数据

        Returns:
            更新后的流程实例，如果版本冲突或不存在返回None
        """
        # 获取当前流程
        current_flow = await self.flow_repository.find_by_id(flow_id)
        if not current_flow:
            return None

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
