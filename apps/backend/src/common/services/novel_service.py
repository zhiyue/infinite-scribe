"""Service for novel management operations."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.novel import Novel
from src.schemas.enums import ChapterStatus
from src.schemas.novel.create import NovelCreateRequest
from src.schemas.novel.read import NovelProgress, NovelResponse, NovelSummary
from src.schemas.novel.update import NovelUpdateRequest

logger = logging.getLogger(__name__)


class NovelService:
    """Service for novel management operations."""

    async def list_user_novels(
        self,
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        status_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get paginated list of user's novels.

        Args:
            db: Database session
            user_id: User ID for filtering
            skip: Number of records to skip
            limit: Maximum number of records to return
            status_filter: Optional status filter

        Returns:
            Result dictionary with novels list or error
        """
        try:
            # Build query with user filter
            query = select(Novel).where(Novel.user_id == user_id).order_by(Novel.updated_at.desc())

            # Add status filter if provided
            if status_filter:
                query = query.where(Novel.status == status_filter)

            # Apply pagination
            query = query.offset(skip).limit(limit)

            result = await db.execute(query)
            novels = result.scalars().all()

            # Convert to NovelSummary objects
            novel_summaries = [
                NovelSummary(
                    id=novel.id,
                    title=novel.title,
                    theme=novel.theme,
                    status=novel.status,
                    target_chapters=novel.target_chapters,
                    completed_chapters=novel.completed_chapters,
                    created_at=novel.created_at,
                    updated_at=novel.updated_at,
                )
                for novel in novels
            ]

            return {"success": True, "novels": novel_summaries}

        except Exception as e:
            logger.error(f"List user novels error: {e}")
            return {"success": False, "error": "An error occurred while retrieving novels"}

    async def create_novel(
        self,
        db: AsyncSession,
        user_id: int,
        novel_data: NovelCreateRequest,
    ) -> dict[str, Any]:
        """Create a new novel.

        Args:
            db: Database session
            user_id: Owner user ID
            novel_data: Novel creation data

        Returns:
            Result dictionary with created novel or error
        """
        try:
            # Create novel instance
            novel = Novel(
                user_id=user_id,
                title=novel_data.title,
                theme=novel_data.theme,
                writing_style=novel_data.writing_style,
                target_chapters=novel_data.target_chapters,
            )

            db.add(novel)
            await db.commit()
            await db.refresh(novel)

            # Convert to response schema
            novel_response = NovelResponse(
                id=novel.id,
                title=novel.title,
                theme=novel.theme,
                writing_style=novel.writing_style,
                status=novel.status,
                target_chapters=novel.target_chapters,
                completed_chapters=novel.completed_chapters,
                version=novel.version,
                created_at=novel.created_at,
                updated_at=novel.updated_at,
            )

            return {"success": True, "novel": novel_response}

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Novel creation integrity error: {e}")
            return {"success": False, "error": "Novel creation failed due to data constraints"}
        except Exception as e:
            await db.rollback()
            logger.error(f"Novel creation error: {e}")
            return {"success": False, "error": "An error occurred while creating the novel"}

    async def get_novel(
        self,
        db: AsyncSession,
        user_id: int,
        novel_id: UUID,
    ) -> dict[str, Any]:
        """Get a novel by ID with ownership check.

        Args:
            db: Database session
            user_id: User ID
            novel_id: Novel unique identifier

        Returns:
            Result dictionary with novel data or error
        """
        try:
            # Query with ownership check
            query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == user_id))
            result = await db.execute(query)
            novel = result.scalar_one_or_none()

            if not novel:
                return {"success": False, "error": "Novel not found"}

            # Convert to response schema
            novel_response = NovelResponse(
                id=novel.id,
                title=novel.title,
                theme=novel.theme,
                writing_style=novel.writing_style,
                status=novel.status,
                target_chapters=novel.target_chapters,
                completed_chapters=novel.completed_chapters,
                version=novel.version,
                created_at=novel.created_at,
                updated_at=novel.updated_at,
            )

            return {"success": True, "novel": novel_response}

        except Exception as e:
            logger.error(f"Get novel error: {e}")
            return {"success": False, "error": "An error occurred while retrieving the novel"}

    async def update_novel(
        self,
        db: AsyncSession,
        user_id: int,
        novel_id: UUID,
        update_data: NovelUpdateRequest,
    ) -> dict[str, Any]:
        """Update a novel with optimistic locking.

        Args:
            db: Database session
            user_id: User ID
            novel_id: Novel unique identifier
            update_data: Novel update data

        Returns:
            Result dictionary with updated novel or error
        """
        try:
            # Get novel with ownership check
            query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == user_id))
            result = await db.execute(query)
            novel = result.scalar_one_or_none()

            if not novel:
                return {"success": False, "error": "Novel not found"}

            # Check version for optimistic locking
            if novel.version != update_data.version:
                return {
                    "success": False,
                    "error": "Novel has been modified by another process. Please refresh and try again.",
                    "error_code": "CONFLICT",
                }

            # Update fields that are provided
            update_dict = update_data.model_dump(exclude_unset=True, exclude={"version"})
            for field, value in update_dict.items():
                if hasattr(novel, field):
                    setattr(novel, field, value)

            # Increment version for optimistic locking
            novel.version += 1

            await db.commit()
            await db.refresh(novel)

            # Convert to response schema
            novel_response = NovelResponse(
                id=novel.id,
                title=novel.title,
                theme=novel.theme,
                writing_style=novel.writing_style,
                status=novel.status,
                target_chapters=novel.target_chapters,
                completed_chapters=novel.completed_chapters,
                version=novel.version,
                created_at=novel.created_at,
                updated_at=novel.updated_at,
            )

            return {"success": True, "novel": novel_response}

        except Exception as e:
            await db.rollback()
            logger.error(f"Update novel error: {e}")
            return {"success": False, "error": "An error occurred while updating the novel"}

    async def delete_novel(
        self,
        db: AsyncSession,
        user_id: int,
        novel_id: UUID,
    ) -> dict[str, Any]:
        """Delete a novel with ownership check.

        Args:
            db: Database session
            user_id: User ID
            novel_id: Novel unique identifier

        Returns:
            Result dictionary with success status or error
        """
        try:
            # Get novel with ownership check
            query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == user_id))
            result = await db.execute(query)
            novel = result.scalar_one_or_none()

            if not novel:
                return {"success": False, "error": "Novel not found"}

            # Delete the novel
            await db.delete(novel)
            await db.commit()

            return {"success": True, "message": "Novel deleted successfully"}

        except Exception as e:
            await db.rollback()
            logger.error(f"Delete novel error: {e}")
            return {"success": False, "error": "An error occurred while deleting the novel"}

    async def get_novel_chapters(
        self,
        db: AsyncSession,
        user_id: int,
        novel_id: UUID,
    ) -> dict[str, Any]:
        """Get chapters for a novel with ownership check.

        Args:
            db: Database session
            user_id: User ID
            novel_id: Novel unique identifier

        Returns:
            Result dictionary with chapters list or error
        """
        try:
            # Verify novel ownership first
            novel_query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == user_id))
            result = await db.execute(novel_query)
            novel = result.scalar_one_or_none()

            if not novel:
                return {"success": False, "error": "Novel not found"}

            # Get chapters for this novel
            from src.models.chapter import Chapter

            chapters_query = select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.chapter_number)
            result = await db.execute(chapters_query)
            chapters = result.scalars().all()

            # Convert to dict format (to be replaced with ChapterSummary)
            chapters_data = []
            for chapter in chapters:
                chapter_dict = {
                    "id": chapter.id,
                    "novel_id": chapter.novel_id,
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "status": chapter.status.value if hasattr(chapter.status, "value") else chapter.status,
                    "created_at": chapter.created_at,
                    "updated_at": chapter.updated_at,
                }
                chapters_data.append(chapter_dict)

            return {"success": True, "chapters": chapters_data}

        except Exception as e:
            logger.error(f"Get novel chapters error: {e}")
            return {"success": False, "error": "An error occurred while retrieving chapters"}

    async def get_novel_characters(
        self,
        db: AsyncSession,
        user_id: int,
        novel_id: UUID,
    ) -> dict[str, Any]:
        """Get characters for a novel with ownership check.

        Args:
            db: Database session
            user_id: User ID
            novel_id: Novel unique identifier

        Returns:
            Result dictionary with characters list or error
        """
        try:
            # Verify novel ownership first
            novel_query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == user_id))
            result = await db.execute(novel_query)
            novel = result.scalar_one_or_none()

            if not novel:
                return {"success": False, "error": "Novel not found"}

            # Get characters for this novel
            from src.models.character import Character

            characters_query = select(Character).where(Character.novel_id == novel_id).order_by(Character.created_at)
            result = await db.execute(characters_query)
            characters = result.scalars().all()

            # Convert to dict format (to be replaced with CharacterSummary)
            characters_data = []
            for character in characters:
                character_dict = {
                    "id": character.id,
                    "novel_id": character.novel_id,
                    "name": character.name,
                    "role": character.role,
                    "description": character.description,
                    "personality_traits": character.personality_traits,
                    "goals": character.goals,
                    "created_at": character.created_at,
                    "updated_at": character.updated_at,
                }
                characters_data.append(character_dict)

            return {"success": True, "characters": characters_data}

        except Exception as e:
            logger.error(f"Get novel characters error: {e}")
            return {"success": False, "error": "An error occurred while retrieving characters"}

    async def get_novel_stats(
        self,
        db: AsyncSession,
        user_id: int,
        novel_id: UUID,
    ) -> dict[str, Any]:
        """Get statistics for a novel with ownership check.

        Args:
            db: Database session
            user_id: User ID
            novel_id: Novel unique identifier

        Returns:
            Result dictionary with novel statistics or error
        """
        try:
            # Verify novel ownership and get basic info
            novel_query = select(Novel).where(and_(Novel.id == novel_id, Novel.user_id == user_id))
            result = await db.execute(novel_query)
            novel = result.scalar_one_or_none()

            if not novel:
                return {"success": False, "error": "Novel not found"}

            # Get chapter count
            from src.models.chapter import Chapter

            chapters_count_query = select(func.count(Chapter.id)).where(Chapter.novel_id == novel_id)
            result = await db.execute(chapters_count_query)
            total_chapters = result.scalar() or 0

            # Get published chapters count using enum
            published_count_query = select(func.count(Chapter.id)).where(
                and_(Chapter.novel_id == novel_id, Chapter.status == ChapterStatus.PUBLISHED)
            )
            result = await db.execute(published_count_query)
            published_chapters = result.scalar() or 0

            # Calculate progress percentage
            progress_percentage = 0
            if novel.target_chapters > 0:
                progress_percentage = round((published_chapters / novel.target_chapters) * 100, 2)

            progress = NovelProgress(
                novel_id=novel.id,
                total_chapters=total_chapters,
                published_chapters=published_chapters,
                target_chapters=novel.target_chapters,
                progress_percentage=progress_percentage,
                last_updated=novel.updated_at,
            )

            return {"success": True, "stats": progress}

        except Exception as e:
            logger.error(f"Get novel stats error: {e}")
            return {"success": False, "error": "An error occurred while retrieving novel statistics"}


# Create service instance
novel_service = NovelService()
