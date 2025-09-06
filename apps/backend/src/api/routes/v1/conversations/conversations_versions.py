"""Versioning endpoints for conversations."""

import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Response, status

from src.common.utils.api_utils import get_or_create_correlation_id, set_common_headers
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse
from src.schemas.novel.dialogue import VersionCreateRequest, VersionMergeRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/sessions/{session_id}/versions",
    response_model=ApiResponse[list[dict]],
)
async def list_versions(
    session_id: UUID,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[list[dict]]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="获取版本列表（skeleton）", data=[])


@router.post(
    "/sessions/{session_id}/versions",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[dict],
)
async def create_version_branch(
    session_id: UUID,
    request: VersionCreateRequest,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    branch_id = f"v{request.base_version}-branch-{uuid4().hex[:8]}"
    set_common_headers(
        response, correlation_id=corr_id, location=f"/api/v1/conversations/sessions/{session_id}/versions"
    )
    return ApiResponse(code=0, msg="创建分支成功（skeleton）", data={"branch": branch_id, "label": request.label})


@router.put(
    "/sessions/{session_id}/versions/merge",
    response_model=ApiResponse[dict],
)
async def merge_versions(
    session_id: UUID,
    request: VersionMergeRequest,
    response: Response,
    x_correlation_id: Annotated[str | None, Header(alias="X-Correlation-Id")] = None,
    current_user: User = Depends(require_auth),
) -> ApiResponse[dict]:
    corr_id = get_or_create_correlation_id(x_correlation_id)
    # For long-running merges, it could be 202. Here 200 to keep simple.
    set_common_headers(response, correlation_id=corr_id)
    return ApiResponse(code=0, msg="合并完成（skeleton）", data={"target": request.target, "merged": True})
