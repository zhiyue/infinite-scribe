"""Validation functions for Genesis stage endpoints."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.content.novel_service import NovelService
from src.common.services.genesis.stage.genesis_stage_service import GenesisStageService
from src.models.genesis_flows import GenesisFlow, GenesisStageRecord
from src.models.novel import Novel
from src.models.user import User


async def validate_novel_ownership(
    novel_id: UUID,
    user: User,
    novel_service: NovelService,
    db: AsyncSession,
) -> None:
    """Validate that the user owns the specified novel."""
    result = await novel_service.get_novel(db, user.id, novel_id)
    if not result["success"]:
        if result["error"] == "Novel not found":
            raise HTTPException(status_code=404, detail="Novel not found or you don't have permission to access it")
        else:
            raise HTTPException(status_code=500, detail="Failed to validate novel ownership")


async def validate_stage_ownership(
    stage_id: UUID,
    user: User,
    stage_service: GenesisStageService,
    novel_service: NovelService,
) -> UUID:
    """Validate stage ownership and return the backing novel ID."""
    stage = await stage_service.get_stage_by_id(stage_id)
    if not stage:
        raise HTTPException(status_code=404, detail="Genesis stage not found")

    ownership_query = (
        select(GenesisFlow.novel_id)
        .select_from(GenesisStageRecord)
        .join(GenesisFlow, GenesisStageRecord.flow_id == GenesisFlow.id)
        .join(Novel, Novel.id == GenesisFlow.novel_id)
        .where(GenesisStageRecord.id == stage_id, Novel.user_id == user.id)
    )

    result = await stage_service.db_session.execute(ownership_query)
    novel_id = result.scalar_one_or_none()

    if novel_id is None:
        raise HTTPException(status_code=404, detail="Novel not found or you don't have permission to access it")

    # Additional validation through service layer (ensures consistent error contracts)
    await validate_novel_ownership(novel_id, user, novel_service, stage_service.db_session)

    return novel_id
