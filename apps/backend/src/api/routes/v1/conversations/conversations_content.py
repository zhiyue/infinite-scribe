"""Content management endpoints for conversations."""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_service import conversation_service
from src.common.utils.api_utils import get_or_create_correlation_id, set_common_headers
from src.common.utils.datetime_utils import format_iso_datetime, utc_now
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse, PaginatedApiResponse, PaginatedResponse, PaginationInfo
from src.schemas.novel.dialogue import ContentSearchRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/sessions/{session_id}/content",
    response_model=ApiResponse[dict],
)
async def get_content(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.get_session(db, current_user.id, session_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Session not found"))
    s = result["session"]
    state = s.get("state", {}) if isinstance(s, dict) else getattr(s, "state", {}) or {}
    set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(
        code=0, msg="获取内容聚合成功", data={"state": state, "meta": {"updated_at": format_iso_datetime(utc_now())}}
    )


@router.post(
    "/sessions/{session_id}/content/export",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
)
async def export_content(
    session_id: UUID,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    result = await conversation_service.enqueue_command(
        db,
        current_user.id,
        session_id,
        command_type="CONTENT_EXPORT",
        payload={},
        idempotency_key=idempotency_key,
    )
    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to enqueue export"))
    cmd = result["command"]
    cmd_id = getattr(cmd, "id", uuid4())
    set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="导出任务已受理", data={"accepted": True, "command_id": str(cmd_id)})


@router.post(
    "/sessions/{session_id}/content/search",
    response_model=PaginatedApiResponse[dict],
)
async def search_content(
    session_id: UUID,
    request: ContentSearchRequest,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> PaginatedApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    set_common_headers(response, correlation_id=corr_id)
    pagination = PaginationInfo(page=1, page_size=request.limit, total=0, total_pages=0)
    return PaginatedApiResponse(
        code=0, msg="搜索完成（skeleton）", data=PaginatedResponse(items=[], pagination=pagination)
    )
