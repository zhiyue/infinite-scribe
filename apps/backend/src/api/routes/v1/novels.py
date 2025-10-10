"""Novel management endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.content.novel_service import novel_service
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
from src.schemas.base import ApiResponse, PaginatedApiResponse, PaginatedResponse, PaginationInfo
from src.schemas.chapter.read import ChapterSummary
from src.schemas.character.read import CharacterSummary
from src.schemas.enums import NovelStatus
from src.schemas.novel.create import NovelCreateRequest
from src.schemas.novel.read import NovelProgress, NovelResponse, NovelSummary
from src.schemas.novel.update import NovelUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedApiResponse[NovelSummary],
    responses={
        500: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Get user's novels",
    description="Get a paginated list of novels belonging to the authenticated user",
)
async def list_user_novels(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="Number of novels per page"),
    status_filter: NovelStatus | None = Query(None, alias="status", description="Filter by novel status"),
    search: str | None = Query(None, description="Search in title and theme"),
    sort_by: str = Query("updated_at", alias="sortBy", description="Sort field"),
    sort_order: str = Query("desc", alias="sortOrder", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> PaginatedApiResponse[NovelSummary]:
    """Get paginated list of user's novels.

    Args:
        page: Page number (starts from 1)
        page_size: Number of novels per page
        status_filter: Optional status filter
        search: Optional search term for title and theme
        sort_by: Sort field
        sort_order: Sort order (asc or desc)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated response with novel summaries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Convert page-based pagination to offset-based
        skip = (page - 1) * page_size

        # Call service with extended parameters
        result = await novel_service.list_user_novels(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=page_size,
            status_filter=status_filter,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        if not result["success"]:
            return PaginatedApiResponse(code=500, msg=result["error"], data=None)

        # Calculate pagination info
        total = result.get("total", 0)
        total_pages = (total + page_size - 1) // page_size

        pagination_info = PaginationInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

        paginated_data = PaginatedResponse(
            items=result["novels"],
            pagination=pagination_info,
        )

        return PaginatedApiResponse(code=0, msg="获取小说列表成功", data=paginated_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List novels error: {e}")
        return PaginatedApiResponse(code=500, msg="获取小说列表时发生错误", data=None)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[NovelResponse],
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Create new novel",
    description="Create a new novel project",
)
async def create_novel(
    request: NovelCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ApiResponse[NovelResponse]:
    """Create a new novel.

    Args:
        request: Novel creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created novel details in unified response format

    Raises:
        HTTPException: If creation fails
    """
    try:
        result = await novel_service.create_novel(db, current_user.id, request)

        if not result["success"]:
            # Handle different error types appropriately
            if "constraint" in result["error"].lower():
                return ApiResponse(code=400, msg=result["error"], data=None)
            else:
                return ApiResponse(code=500, msg=result["error"], data=None)

        return ApiResponse(code=0, msg="创建小说成功", data=result["novel"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create novel error: {e}")
        return ApiResponse(code=500, msg="创建小说时发生错误", data=None)


@router.get(
    "/{novel_id}",
    response_model=ApiResponse[NovelResponse],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Get novel details",
    description="Get detailed information about a specific novel",
)
async def get_novel(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ApiResponse[NovelResponse]:
    """Get novel by ID.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        Novel details in unified response format

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                return ApiResponse(code=404, msg=result["error"], data=None)
            else:
                return ApiResponse(code=500, msg=result["error"], data=None)

        return ApiResponse(code=0, msg="获取小说详情成功", data=result["novel"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel error: {e}")
        return ApiResponse(code=500, msg="获取小说详情时发生错误", data=None)


@router.put(
    "/{novel_id}",
    response_model=ApiResponse[NovelResponse],
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Update novel",
    description="Update novel information",
)
async def update_novel(
    novel_id: UUID,
    request: NovelUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ApiResponse[NovelResponse]:
    """Update novel by ID.

    Args:
        novel_id: Novel unique identifier
        request: Novel update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated novel details in unified response format

    Raises:
        HTTPException: If novel not found, access denied, or update fails
    """
    try:
        result = await novel_service.update_novel(db, current_user.id, novel_id, request)

        if not result["success"]:
            # Handle different error types
            if "not found" in result["error"].lower():
                return ApiResponse(code=404, msg=result["error"], data=None)
            elif result.get("error_code") == "CONFLICT":
                return ApiResponse(code=409, msg=result["error"], data=None)
            else:
                return ApiResponse(code=500, msg=result["error"], data=None)

        return ApiResponse(code=0, msg="更新小说成功", data=result["novel"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update novel error: {e}")
        return ApiResponse(code=500, msg="更新小说时发生错误", data=None)


@router.delete(
    "/{novel_id}",
    response_model=ApiResponse[None],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Delete novel",
    description="Delete a novel and all its associated data",
)
async def delete_novel(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ApiResponse[None]:
    """Delete novel by ID.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        Unified response format

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.delete_novel(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                return ApiResponse(code=404, msg=result["error"], data=None)
            else:
                return ApiResponse(code=500, msg=result["error"], data=None)

        return ApiResponse(code=0, msg="删除小说成功", data=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete novel error: {e}")
        return ApiResponse(code=500, msg="删除小说时发生错误", data=None)


@router.get(
    "/{novel_id}/chapters",
    response_model=ApiResponse[list[ChapterSummary]],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Get novel chapters",
    description="Get list of chapters for a specific novel",
)
async def get_novel_chapters(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ApiResponse[list[ChapterSummary]]:
    """Get chapters for a novel.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of chapters in unified response format

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel_chapters(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                return ApiResponse(code=404, msg=result["error"], data=None)
            else:
                return ApiResponse(code=500, msg=result["error"], data=None)

        return ApiResponse(code=0, msg="获取章节列表成功", data=result["chapters"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel chapters error: {e}")
        return ApiResponse(code=500, msg="获取章节列表时发生错误", data=None)


@router.get(
    "/{novel_id}/characters",
    response_model=ApiResponse[list[CharacterSummary]],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Get novel characters",
    description="Get list of characters for a specific novel",
)
async def get_novel_characters(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ApiResponse[list[CharacterSummary]]:
    """Get characters for a novel.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of characters in unified response format

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel_characters(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                return ApiResponse(code=404, msg=result["error"], data=None)
            else:
                return ApiResponse(code=500, msg=result["error"], data=None)

        return ApiResponse(code=0, msg="获取角色列表成功", data=result["characters"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel characters error: {e}")
        return ApiResponse(code=500, msg="获取角色列表时发生错误", data=None)


@router.get(
    "/{novel_id}/stats",
    response_model=ApiResponse[NovelProgress],
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Get novel statistics",
    description="Get progress and statistics for a specific novel",
)
async def get_novel_stats(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> ApiResponse[NovelProgress]:
    """Get statistics for a novel.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        Novel progress and statistics in unified response format

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel_stats(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                return ApiResponse(code=404, msg=result["error"], data=None)
            else:
                return ApiResponse(code=500, msg=result["error"], data=None)

        return ApiResponse(code=0, msg="获取统计信息成功", data=result["stats"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel stats error: {e}")
        return ApiResponse(code=500, msg="获取统计信息时发生错误", data=None)
