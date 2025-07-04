"""
Genesis API routes with command-based endpoints.
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.auth import get_current_user, TokenPayload, require_permissions
from src.models.api import (
    CommandRequest,
    CommandResponse,
    ErrorResponse,
    GenesisHealthResponse
)
from src.common.services.command_service import CommandService
from src.common.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/genesis", tags=["genesis"])

# Initialize services
event_publisher = EventPublisher()
command_service = CommandService(event_publisher)


@router.get("/health", response_model=GenesisHealthResponse)
async def health_check():
    """Health check endpoint."""
    return GenesisHealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp="2024-01-01T00:00:00Z"
    )


@router.post("/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:command:create"]))
):
    """
    Execute a command based on command_type.
    Supports: RequestConceptGeneration, ConfirmStage, SubmitFeedback
    """
    try:
        logger.info(f"Processing command {request.command_type} for session {request.session_id} by user {current_user.username}")
        
        # Validate command type
        supported_commands = ["RequestConceptGeneration", "ConfirmStage", "SubmitFeedback"]
        if request.command_type not in supported_commands:
            return CommandResponse(
                success=False,
                error=ErrorResponse(
                    code="UNSUPPORTED_COMMAND",
                    message=f"Command type {request.command_type} is not supported",
                    details={"supported_commands": supported_commands}
                )
            )
        
        # Process command
        response = await command_service.process_command(request, session)
        
        if response.success:
            logger.info(f"Command {request.command_type} processed successfully with correlation_id {response.correlation_id}")
        else:
            logger.warning(f"Command {request.command_type} failed: {response.error.message if response.error else 'Unknown error'}")
        
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error processing command: {str(e)}", exc_info=True)
        
        return CommandResponse(
            success=False,
            error=ErrorResponse(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"error": str(e)}
            )
        )


@router.get("/command/{command_id}/status")
async def get_command_status(
    command_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:command:read"]))
):
    """Get status of a specific command."""
    try:
        status_info = await command_service.get_command_status(command_id, session)
        
        if status_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Command {command_id} not found"
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting command status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get command status"
        )


@router.get("/commands/failed")
async def get_failed_commands(
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:admin:read"]))
):
    """Get list of failed commands for monitoring."""
    try:
        failed_commands = await command_service.get_failed_commands(session, limit)
        
        return {
            "failed_commands": failed_commands,
            "count": len(failed_commands),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error getting failed commands: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get failed commands"
        )


@router.post("/request-concept-generation", response_model=CommandResponse)
async def request_concept_generation(
    request: CommandRequest,
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:concept:create"]))
):
    """
    Convenience endpoint for RequestConceptGeneration command.
    """
    if request.command_type != "RequestConceptGeneration":
        request.command_type = "RequestConceptGeneration"
    
    return await execute_command(request, session, current_user)


@router.post("/confirm-stage", response_model=CommandResponse)
async def confirm_stage(
    request: CommandRequest,
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:stage:confirm"]))
):
    """
    Convenience endpoint for ConfirmStage command.
    """
    if request.command_type != "ConfirmStage":
        request.command_type = "ConfirmStage"
    
    return await execute_command(request, session, current_user)


@router.post("/submit-feedback", response_model=CommandResponse)
async def submit_feedback(
    request: CommandRequest,
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:feedback:create"]))
):
    """
    Convenience endpoint for SubmitFeedback command.
    """
    if request.command_type != "SubmitFeedback":
        request.command_type = "SubmitFeedback"
    
    return await execute_command(request, session, current_user)


@router.get("/sessions/{session_id}/events")
async def get_session_events(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:event:read"]))
):
    """Get events for a specific session."""
    try:
        from sqlalchemy import select
        from src.models.database import DomainEvent
        
        query = select(DomainEvent).where(
            DomainEvent.aggregate_id == session_id
        ).order_by(DomainEvent.created_at)
        
        result = await session.execute(query)
        events = result.scalars().all()
        
        return {
            "session_id": session_id,
            "events": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "event_data": event.event_data,
                    "correlation_id": event.correlation_id,
                    "causation_id": event.causation_id,
                    "created_at": event.created_at.isoformat()
                }
                for event in events
            ],
            "count": len(events)
        }
        
    except Exception as e:
        logger.error(f"Error getting session events: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session events"
        )


@router.get("/metrics")
async def get_metrics(
    session: AsyncSession = Depends(get_session),
    current_user: TokenPayload = Depends(require_permissions(["genesis:admin:read"]))
):
    """Get system metrics."""
    try:
        from sqlalchemy import text
        
        # Get command status counts
        command_query = text("""
            SELECT status, COUNT(*) as count
            FROM command_inbox
            GROUP BY status
        """)
        
        command_result = await session.execute(command_query)
        command_stats = {row.status: row.count for row in command_result}
        
        # Get event outbox status counts
        outbox_query = text("""
            SELECT status, COUNT(*) as count
            FROM event_outbox
            GROUP BY status
        """)
        
        outbox_result = await session.execute(outbox_query)
        outbox_stats = {row.status: row.count for row in outbox_result}
        
        # Get recent activity (last 24 hours)
        recent_query = text("""
            SELECT COUNT(*) as count
            FROM command_inbox
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        
        recent_result = await session.execute(recent_query)
        recent_commands = recent_result.scalar()
        
        return {
            "command_stats": command_stats,
            "outbox_stats": outbox_stats,
            "recent_commands_24h": recent_commands,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        )


# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {}
            }
        }
    )


@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {}
            }
        }
    )