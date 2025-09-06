"""Stage management endpoints for conversations (Genesis-specific)."""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response, status

from src.common.utils.api_utils import COMMON_ERROR_RESPONSES, get_or_create_correlation_id, set_common_headers
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
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取阶段成功（skeleton）", data={"stage": "Stage_0"})


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
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    if if_match is not None and if_match.strip('"') != "1":
        raise HTTPException(status_code=412, detail="Version mismatch (skeleton)")
    set_common_headers(response, correlation_id=corr_id, etag='"2"')
    return ApiResponse(code=0, msg="切换阶段成功（skeleton）", data={"stage": stage, "version": 2})


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
