"""Novel management endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse
from src.common.services.novel_service import novel_service
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.user import User
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
    response_model=list[NovelSummary],
    responses={
        500: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
    summary="Get user's novels",
    description="Get a list of novels belonging to the authenticated user",
)
async def list_user_novels(
    skip: int = Query(0, ge=0, description="Number of novels to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of novels to return"),
    status_filter: NovelStatus | None = Query(None, description="Filter by novel status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> list[NovelSummary]:
    """Get paginated list of user's novels.

    Args:
        skip: Number of novels to skip for pagination
        limit: Maximum number of novels to return
        status_filter: Optional status filter
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of novel summaries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        result = await novel_service.list_user_novels(db, current_user.id, skip, limit, status_filter)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"],
            )

        return result["novels"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List novels error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving novels",
        ) from e


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=NovelResponse,
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
) -> NovelResponse:
    """Create a new novel.

    Args:
        request: Novel creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created novel details

    Raises:
        HTTPException: If creation fails
    """
    try:
        result = await novel_service.create_novel(db, current_user.id, request)

        if not result["success"]:
            # Handle different error types appropriately
            if "constraint" in result["error"].lower():
                status_code = status.HTTP_400_BAD_REQUEST
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=result["error"])

        return result["novel"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create novel error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the novel",
        ) from e


@router.get(
    "/{novel_id}",
    response_model=NovelResponse,
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
) -> NovelResponse:
    """Get novel by ID.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        Novel details

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=result["error"])

        return result["novel"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the novel",
        ) from e


@router.put(
    "/{novel_id}",
    response_model=NovelResponse,
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
) -> NovelResponse:
    """Update novel by ID.

    Args:
        novel_id: Novel unique identifier
        request: Novel update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated novel details

    Raises:
        HTTPException: If novel not found, access denied, or update fails
    """
    try:
        result = await novel_service.update_novel(db, current_user.id, novel_id, request)

        if not result["success"]:
            # Handle different error types
            if "not found" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND
            elif result.get("error_code") == "CONFLICT":
                status_code = status.HTTP_409_CONFLICT
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=result["error"])

        return result["novel"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update novel error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the novel",
        ) from e


@router.delete(
    "/{novel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
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
) -> None:
    """Delete novel by ID.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.delete_novel(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete novel error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the novel",
        ) from e


@router.get(
    "/{novel_id}/chapters",
    response_model=list[ChapterSummary],
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
) -> list[ChapterSummary]:
    """Get chapters for a novel.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of chapters

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel_chapters(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=result["error"])

        return result["chapters"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel chapters error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving chapters",
        ) from e


@router.get(
    "/{novel_id}/characters",
    response_model=list[CharacterSummary],
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
) -> list[CharacterSummary]:
    """Get characters for a novel.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of characters

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel_characters(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=result["error"])

        return result["characters"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel characters error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving characters",
        ) from e


@router.get(
    "/{novel_id}/stats",
    response_model=NovelProgress,
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
) -> NovelProgress:
    """Get statistics for a novel.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        Novel progress and statistics

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        result = await novel_service.get_novel_stats(db, current_user.id, novel_id)

        if not result["success"]:
            if "not found" in result["error"].lower():
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=result["error"])

        return result["stats"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving novel statistics",
        ) from e
