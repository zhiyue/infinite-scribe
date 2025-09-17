"""Rounds management endpoints for conversations."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.conversation.conversation_service import conversation_service
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.common.utils.datetime_utils import format_iso_datetime, utc_now
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse, PaginatedApiResponse, PaginatedResponse, PaginationInfo
from src.schemas.novel.dialogue import DialogueRole, RoundResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/sessions/{session_id}/rounds",
    response_model=PaginatedApiResponse[RoundResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def list_rounds(
    session_id: UUID,
    response: Response,
    after: str | None = Query(None, description="Cursor (round_path)"),
    limit: int = Query(50, ge=1, le=200),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    role: DialogueRole | None = Query(None),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> PaginatedApiResponse[RoundResponse]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    set_common_headers(response, correlation_id=corr_id)
    result = await conversation_service.list_rounds(
        db,
        current_user.id,
        session_id,
        after=after,
        limit=limit,
        order=order,
        role=role,
    )
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to list rounds"))
    rounds = result.get("rounds", [])
    items = [
        RoundResponse(
            session_id=r.session_id if hasattr(r, "session_id") else UUID(r["session_id"]),
            round_path=r.round_path if hasattr(r, "round_path") else r["round_path"],
            role=DialogueRole(r.role if hasattr(r, "role") else r["role"]),
            input=r.input if hasattr(r, "input") else r.get("input", {}),
            output=r.output if hasattr(r, "output") else r.get("output"),
            model=r.model if hasattr(r, "model") else r.get("model"),
            correlation_id=r.correlation_id if hasattr(r, "correlation_id") else r.get("correlation_id"),
            created_at=(
                r.created_at.isoformat()
                if hasattr(r, "created_at")
                else r.get("created_at") or format_iso_datetime(utc_now())
            ),
        )
        for r in rounds
    ]
    pagination = PaginationInfo(page=1, page_size=limit, total=len(items), total_pages=1)
    return PaginatedApiResponse(code=0, msg="获取轮次成功", data=PaginatedResponse(items=items, pagination=pagination))



@router.get(
    "/sessions/{session_id}/rounds/{round_id}",
    response_model=ApiResponse[RoundResponse],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_round(
    session_id: UUID,
    response: Response,
    round_id: str = Path(..., description="Round path, e.g., 1 or 2.1"),
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RoundResponse]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    set_common_headers(response, correlation_id=corr_id)
    result = await conversation_service.get_round(db, current_user.id, session_id, round_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Round not found"))
    r = result["round"]
    data = RoundResponse(
        session_id=r["session_id"] if isinstance(r, dict) else r.session_id,
        round_path=r["round_path"] if isinstance(r, dict) else r.round_path,
        role=DialogueRole(r["role"] if isinstance(r, dict) else r.role),
        input=r.get("input", {}) if isinstance(r, dict) else r.input or {},
        output=r.get("output") if isinstance(r, dict) else r.output,
        model=r.get("model") if isinstance(r, dict) else r.model,
        correlation_id=r.get("correlation_id") if isinstance(r, dict) else r.correlation_id,
        created_at=(
            r.get("created_at") or format_iso_datetime(utc_now())
            if isinstance(r, dict)
            else (r.created_at.isoformat() if getattr(r, "created_at", None) else format_iso_datetime(utc_now()))
        ),
    )
    return ApiResponse(code=0, msg="获取轮次成功", data=data)
