"""Genesis API routes for command-based operations."""

import logging
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.command_service import command_service, DuplicateCommandError
from src.core.database import get_db_session
from src.models.api import CommandRequest, CommandResponse, ErrorResponse

logger = logging.getLogger(__name__)

# Create router for Genesis endpoints
router = APIRouter(prefix="/genesis", tags=["genesis"])

# Security dependency for JWT authentication
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Extract user ID from JWT token.
    
    For now, this is a placeholder. In production, you would:
    1. Verify JWT token signature
    2. Extract user ID from token payload
    3. Validate token expiration
    """
    # TODO: Implement proper JWT verification
    # For now, return a placeholder user ID
    return "user-placeholder"


@router.post(
    "/sessions/{session_id}/commands",
    response_model=CommandResponse,
    responses={
        200: {"description": "Command processed successfully"},
        202: {"description": "Command accepted for processing"},
        409: {"description": "Duplicate command", "model": ErrorResponse},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def process_command(
    session_id: UUID,
    command_request: CommandRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> CommandResponse:
    """
    Process a command for a Genesis session.
    
    This endpoint handles all command types for Genesis sessions and routes them
    to the appropriate processing logic. Commands are processed transactionally
    to ensure consistency between command_inbox, domain_events, and event_outbox.
    """
    try:
        # Route command based on command_type
        if command_request.command_type in ["RequestConceptGeneration", "ConfirmStage", "SubmitFeedback"]:
            # Process the command
            result = await command_service.process_command(
                session_id=session_id,
                command_type=command_request.command_type,
                payload=command_request.payload or {},
                db=db,
                user_id=current_user,
            )
            
            # Return appropriate response based on command type
            if command_request.command_type in ["RequestConceptGeneration"]:
                # Async commands return 202 Accepted
                return CommandResponse(
                    command_id=result.command_id,
                    status=result.status,
                    message="Command accepted for processing",
                )
            else:
                # Sync commands return 200 OK
                return CommandResponse(
                    command_id=result.command_id,
                    status=result.status,
                    message=result.message,
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported command type: {command_request.command_type}",
            )
            
    except DuplicateCommandError as e:
        # Handle duplicate command with 409 Conflict
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "DUPLICATE_COMMAND",
                "message": "Command already processing",
                "duplicate_command_id": str(e.existing_command_id) if e.existing_command_id else None,
            },
        )
    
    except Exception as e:
        logger.error(f"Error processing command for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get(
    "/sessions/{session_id}/status",
    response_model=Dict[str, Any],
)
async def get_session_status(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the current status of a Genesis session.
    
    This endpoint returns the current state of the session including:
    - Current stage
    - Status
    - Confirmed data
    """
    try:
        # Query session from database
        from sqlalchemy import text
        
        query = text("""
            SELECT id, status, current_stage, confirmed_data, created_at, updated_at
            FROM genesis_sessions
            WHERE id = :session_id
        """)
        
        result = await db.execute(query, {"session_id": session_id})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        
        return {
            "session_id": str(row[0]),
            "status": row[1],
            "current_stage": row[2],
            "confirmed_data": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status for {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post(
    "/sessions",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Create a new Genesis session.
    
    This creates a new session for the Genesis workflow and returns the session ID.
    """
    try:
        from datetime import UTC, datetime
        from uuid import uuid4
        from sqlalchemy import text
        
        session_id = uuid4()
        
        # Insert new session
        insert_stmt = text("""
            INSERT INTO genesis_sessions 
            (id, user_id, status, current_stage, created_at, updated_at)
            VALUES 
            (:id, :user_id, :status, :current_stage, :created_at, :updated_at)
        """)
        
        await db.execute(insert_stmt, {
            "id": session_id,
            "user_id": current_user,
            "status": "IN_PROGRESS",
            "current_stage": "CONCEPT_SELECTION",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        })
        
        await db.commit()
        
        return {
            "session_id": str(session_id),
            "status": "IN_PROGRESS",
            "current_stage": "CONCEPT_SELECTION",
            "message": "Genesis session created successfully",
        }
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )