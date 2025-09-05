"""Novel management endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import ErrorResponse, MessageResponse
from src.database import get_db
from src.middleware.auth import require_auth
from src.models.novel import Novel
from src.models.user import User
from src.schemas.novel.create import NovelCreateRequest
from src.schemas.novel.read import NovelProgress, NovelResponse, NovelSummary
from src.schemas.novel.update import NovelUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[NovelSummary] | ErrorResponse,
    summary="Get user's novels",
    description="Get a list of novels belonging to the authenticated user",
)
async def list_user_novels(
    skip: int = Query(0, ge=0, description="Number of novels to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of novels to return"),
    status_filter: str = Query(None, description="Filter by novel status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> list[NovelSummary] | ErrorResponse:
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
        # Build query with filters
        query = select(Novel).where(Novel.user_id == current_user.id)

        if status_filter:
            query = query.where(Novel.status == status_filter)

        # Add ordering and pagination
        query = query.order_by(Novel.updated_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        novels = result.scalars().all()

        return [NovelSummary.model_validate(novel) for novel in novels]

    except Exception as e:
        logger.error(f"List novels error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving novels",
        ) from e


@router.post(
    "",
    response_model=NovelResponse | ErrorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new novel",
    description="Create a new novel project",
)
async def create_novel(
    request: NovelCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> NovelResponse | ErrorResponse:
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
        # Create novel instance
        novel_data = request.model_dump(exclude_unset=True)
        novel_data["user_id"] = current_user.id

        novel = Novel(**novel_data)
        db.add(novel)
        await db.commit()
        await db.refresh(novel)

        return NovelResponse.model_validate(novel)

    except Exception as e:
        logger.error(f"Create novel error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the novel",
        ) from e


@router.get(
    "/{novel_id}",
    response_model=NovelResponse | ErrorResponse,
    summary="Get novel details",
    description="Get detailed information about a specific novel",
)
async def get_novel(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> NovelResponse | ErrorResponse:
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
        # Query novel with ownership check
        query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == current_user.id))

        result = await db.execute(query)
        novel = result.scalar_one_or_none()

        if not novel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Novel not found")

        return NovelResponse.model_validate(novel)

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
    response_model=NovelResponse | ErrorResponse,
    summary="Update novel",
    description="Update novel information",
)
async def update_novel(
    novel_id: UUID,
    request: NovelUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> NovelResponse | ErrorResponse:
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
        # Query novel with ownership check
        query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == current_user.id))

        result = await db.execute(query)
        novel = result.scalar_one_or_none()

        if not novel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Novel not found")

        # Handle optimistic locking
        if request.version and novel.version != request.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Novel has been modified by another process. Please refresh and try again.",
            )

        # Update novel fields
        update_data = request.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            if hasattr(novel, field):
                setattr(novel, field, value)

        # Increment version for optimistic locking
        novel.version += 1

        await db.commit()
        await db.refresh(novel)

        return NovelResponse.model_validate(novel)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update novel error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the novel",
        ) from e


@router.delete(
    "/{novel_id}",
    response_model=MessageResponse | ErrorResponse,
    summary="Delete novel",
    description="Delete a novel and all its associated data",
)
async def delete_novel(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> MessageResponse | ErrorResponse:
    """Delete novel by ID.

    Args:
        novel_id: Novel unique identifier
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If novel not found or access denied
    """
    try:
        # Query novel with ownership check
        query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == current_user.id))

        result = await db.execute(query)
        novel = result.scalar_one_or_none()

        if not novel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Novel not found")

        await db.delete(novel)
        await db.commit()

        return MessageResponse(success=True, message="Novel deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete novel error: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the novel",
        ) from e


@router.get(
    "/{novel_id}/chapters",
    response_model=list[dict] | ErrorResponse,
    summary="Get novel chapters",
    description="Get list of chapters for a specific novel",
)
async def get_novel_chapters(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> list[dict] | ErrorResponse:
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
        # First verify novel ownership
        novel_query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == current_user.id))
        result = await db.execute(novel_query)
        novel = result.scalar_one_or_none()

        if not novel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Novel not found")

        # Load chapters with novel
        from src.models.chapter import Chapter

        chapters_query = select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.chapter_number)

        result = await db.execute(chapters_query)
        chapters = result.scalars().all()

        return [
            {
                "id": str(chapter.id),
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "status": chapter.status,
                "created_at": chapter.created_at,
                "updated_at": chapter.updated_at,
            }
            for chapter in chapters
        ]

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
    response_model=list[dict] | ErrorResponse,
    summary="Get novel characters",
    description="Get list of characters for a specific novel",
)
async def get_novel_characters(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> list[dict] | ErrorResponse:
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
        # First verify novel ownership
        novel_query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == current_user.id))
        result = await db.execute(novel_query)
        novel = result.scalar_one_or_none()

        if not novel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Novel not found")

        # Load characters
        from src.models.character import Character

        characters_query = select(Character).where(Character.novel_id == novel_id).order_by(Character.name)

        result = await db.execute(characters_query)
        characters = result.scalars().all()

        return [
            {
                "id": str(character.id),
                "name": character.name,
                "role": character.role,
                "description": character.description,
                "personality_traits": character.personality_traits,
                "goals": character.goals,
                "created_at": character.created_at,
                "updated_at": character.updated_at,
            }
            for character in characters
        ]

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
    response_model=NovelProgress | ErrorResponse,
    summary="Get novel statistics",
    description="Get progress and statistics for a specific novel",
)
async def get_novel_stats(
    novel_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
) -> NovelProgress | ErrorResponse:
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
        # Verify novel ownership and get basic info
        novel_query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == current_user.id))
        result = await db.execute(novel_query)
        novel = result.scalar_one_or_none()

        if not novel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Novel not found")

        # Get chapter count
        from src.models.chapter import Chapter

        chapters_count_query = select(func.count(Chapter.id)).where(Chapter.novel_id == novel_id)
        result = await db.execute(chapters_count_query)
        total_chapters = result.scalar() or 0

        # Get published chapters count
        published_count_query = select(func.count(Chapter.id)).where(
            and_(Chapter.novel_id == novel_id, Chapter.status == "PUBLISHED")
        )
        result = await db.execute(published_count_query)
        published_chapters = result.scalar() or 0

        # Calculate progress percentage
        progress_percentage = 0
        if novel.target_chapters > 0:
            progress_percentage = round((published_chapters / novel.target_chapters) * 100, 2)

        return NovelProgress(
            novel_id=novel.id,
            total_chapters=total_chapters,
            published_chapters=published_chapters,
            target_chapters=novel.target_chapters,
            progress_percentage=progress_percentage,
            last_updated=novel.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get novel stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving novel statistics",
        ) from e
