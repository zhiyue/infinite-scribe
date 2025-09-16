"""Stage management endpoints for conversations (Genesis-specific)."""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation import conversation_service
from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/sessions/{session_id}/stage",
    response_model=ApiResponse[dict],
)
async def get_stage(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)

    # Verify access to session
    result = await conversation_service.get_session(db, current_user.id, session_id)
    if not result.get("success"):
        code = result.get("code", 404)
        raise HTTPException(status_code=code, detail=result.get("error", "Session not found"))

    session = result["session"]
    stage = getattr(session, "stage", None) if not isinstance(session, dict) else session.get("stage")

    set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取阶段成功（skeleton）", data={"stage": stage or "Stage_0"})


@router.put(
    "/sessions/{session_id}/stage",
    response_model=ApiResponse[dict],
    responses=COMMON_ERROR_RESPONSES,
)
async def set_stage(
    session_id: UUID,
    stage: Annotated[str, Body(embed=True)],
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)

    # Parse expected version from If-Match header
    expected_version = None
    if if_match is not None:
        try:
            expected_version = int(if_match.strip('"'))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid If-Match header")

    # Update session stage with access control
    result = await conversation_service.update_session(
        db, current_user.id, session_id, stage=stage, expected_version=expected_version
    )

    if not result.get("success"):
        code = result.get("code", 422)
        raise HTTPException(status_code=code, detail=result.get("error", "Update failed"))

    session = result.get("serialized_session") or result["session"]
    version = session.get("version", 2) if isinstance(session, dict) else getattr(session, "version", 2)

    set_common_headers(response, correlation_id=corr_id, etag=f'"{version}"')
    return ApiResponse(code=0, msg="切换阶段成功（skeleton）", data={"stage": stage, "version": version})


@router.post(
    "/sessions/{session_id}/stage/validate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
)
async def validate_stage(
    session_id: UUID,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    cmd_id = uuid4()
    set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="阶段验证已受理（skeleton）", data={"accepted": True, "command_id": str(cmd_id)})


@router.post(
    "/sessions/{session_id}/stage/lock",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ApiResponse[dict],
)
async def lock_stage(
    session_id: UUID,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    cmd_id = uuid4()
    set_common_headers(
        response,
        correlation_id=corr_id,
        location=f"/api/v1/conversations/sessions/{session_id}/commands/{cmd_id}",
    )
    return ApiResponse(code=0, msg="阶段锁定已受理（skeleton）", data={"accepted": True, "command_id": str(cmd_id)})
