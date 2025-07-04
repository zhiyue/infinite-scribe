"""
Command processing service with transactional guarantees.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy import text, select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import CommandInbox, DomainEvent, EventOutbox
from src.models.api import (
    CommandRequest,
    CommandResponse,
    ErrorResponse,
    RequestConceptGenerationCommand,
    ConfirmStageCommand,
    SubmitFeedbackCommand
)
from src.common.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class CommandService:
    """Service for processing commands with transactional guarantees."""
    
    def __init__(self, event_publisher: EventPublisher):
        self.event_publisher = event_publisher
        self.command_processors = {
            'RequestConceptGeneration': self._process_request_concept_generation,
            'ConfirmStage': self._process_confirm_stage,
            'SubmitFeedback': self._process_submit_feedback,
        }
    
    async def process_command(self, command: CommandRequest, session: AsyncSession) -> CommandResponse:
        """Process a command with full transactional guarantees."""
        correlation_id = str(uuid4())
        
        try:
            # Start transaction
            await session.begin()
            
            # Check for duplicate commands
            if await self._is_duplicate_command(command, session):
                await session.rollback()
                return CommandResponse(
                    success=False,
                    correlation_id=correlation_id,
                    error=ErrorResponse(
                        code="DUPLICATE_COMMAND",
                        message=f"Command {command.command_type} already processed for session {command.session_id}",
                        details={"session_id": command.session_id, "command_type": command.command_type}
                    )
                )
            
            # Store command in inbox
            command_id = await self._store_command_inbox(command, correlation_id, session)
            
            # Process command based on type
            processor = self.command_processors.get(command.command_type)
            if not processor:
                await session.rollback()
                return CommandResponse(
                    success=False,
                    correlation_id=correlation_id,
                    error=ErrorResponse(
                        code="UNKNOWN_COMMAND",
                        message=f"Unknown command type: {command.command_type}",
                        details={"command_type": command.command_type}
                    )
                )
            
            try:
                # Execute command processor
                events = await processor(command, correlation_id, session)
                
                # Store domain events
                await self._store_domain_events(events, correlation_id, session)
                
                # Publish events to outbox
                await self._publish_events_to_outbox(events, correlation_id, session)
                
                # Update command status to COMPLETED
                await self._update_command_status(command_id, "COMPLETED", session)
                
                # Commit transaction
                await session.commit()
                
                return CommandResponse(
                    success=True,
                    correlation_id=correlation_id,
                    data={"command_id": command_id, "events_count": len(events)}
                )
                
            except Exception as e:
                logger.error(f"Command processing failed: {str(e)}", exc_info=True)
                # Update command status to FAILED within transaction
                await self._update_command_status(command_id, "FAILED", session)
                await session.rollback()
                
                return CommandResponse(
                    success=False,
                    correlation_id=correlation_id,
                    error=ErrorResponse(
                        code="COMMAND_PROCESSING_ERROR",
                        message=f"Failed to process command: {str(e)}",
                        details={"command_id": command_id}
                    )
                )
                
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}", exc_info=True)
            await session.rollback()
            
            return CommandResponse(
                success=False,
                correlation_id=correlation_id,
                error=ErrorResponse(
                    code="TRANSACTION_ERROR",
                    message=f"Transaction failed: {str(e)}",
                    details={}
                )
            )
    
    async def _is_duplicate_command(self, command: CommandRequest, session: AsyncSession) -> bool:
        """Check if command is a duplicate using unique constraint."""
        try:
            # Use PostgreSQL JSON operator syntax
            query = select(CommandInbox).where(
                and_(
                    CommandInbox.session_id == command.session_id,
                    CommandInbox.command_type == command.command_type,
                    CommandInbox.status.in_(["PENDING", "PROCESSING", "COMPLETED"])
                )
            )
            
            result = await session.execute(query)
            existing_command = result.scalars().first()
            
            return existing_command is not None
            
        except Exception as e:
            logger.error(f"Error checking duplicate command: {str(e)}")
            return False
    
    async def _store_command_inbox(self, command: CommandRequest, correlation_id: str, session: AsyncSession) -> str:
        """Store command in command_inbox table."""
        command_id = str(uuid4())
        
        command_inbox = CommandInbox(
            command_id=command_id,
            session_id=command.session_id,
            command_type=command.command_type,
            payload=command.payload,
            correlation_id=correlation_id,
            status="PROCESSING",
            created_at=datetime.utcnow()
        )
        
        session.add(command_inbox)
        await session.flush()  # Flush to get the ID
        
        return command_id
    
    async def _store_domain_events(self, events: List[Dict[str, Any]], correlation_id: str, session: AsyncSession) -> None:
        """Store domain events in database."""
        for event_data in events:
            domain_event = DomainEvent(
                event_id=str(uuid4()),
                event_type=event_data['event_type'],
                aggregate_id=event_data['aggregate_id'],
                event_data=event_data['event_data'],
                correlation_id=correlation_id,
                causation_id=event_data.get('causation_id'),
                created_at=datetime.utcnow()
            )
            
            session.add(domain_event)
        
        if events:
            await session.flush()
    
    async def _publish_events_to_outbox(self, events: List[Dict[str, Any]], correlation_id: str, session: AsyncSession) -> None:
        """Publish events to event_outbox table."""
        for event_data in events:
            await self.event_publisher.publish_event(
                event_type=event_data['event_type'],
                event_data=event_data['event_data'],
                correlation_id=correlation_id,
                causation_id=event_data.get('causation_id'),
                session=session
            )
    
    async def _update_command_status(self, command_id: str, status: str, session: AsyncSession) -> None:
        """Update command status in database."""
        try:
            query = text("""
                UPDATE command_inbox 
                SET status = :status, updated_at = :updated_at
                WHERE command_id = :command_id
            """)
            
            await session.execute(query, {
                'status': status,
                'updated_at': datetime.utcnow(),
                'command_id': command_id
            })
            
        except Exception as e:
            logger.error(f"Failed to update command status: {str(e)}")
            raise
    
    async def _process_request_concept_generation(
        self, 
        command: CommandRequest, 
        correlation_id: str,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Process RequestConceptGeneration command."""
        try:
            # Validate payload
            concept_command = RequestConceptGenerationCommand(**command.payload)
            
            # Generate events
            events = [
                {
                    'event_type': 'Genesis.Session.ConceptGenerationRequested',
                    'aggregate_id': command.session_id,
                    'event_data': {
                        'session_id': command.session_id,
                        'topic': concept_command.topic,
                        'requirements': concept_command.requirements,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    'causation_id': correlation_id
                }
            ]
            
            return events
            
        except Exception as e:
            logger.error(f"Error processing RequestConceptGeneration: {str(e)}")
            raise
    
    async def _process_confirm_stage(
        self, 
        command: CommandRequest, 
        correlation_id: str,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Process ConfirmStage command."""
        try:
            # Validate payload
            confirm_command = ConfirmStageCommand(**command.payload)
            
            # Generate events
            events = [
                {
                    'event_type': 'Genesis.Session.StageConfirmed',
                    'aggregate_id': command.session_id,
                    'event_data': {
                        'session_id': command.session_id,
                        'stage_name': confirm_command.stage_name,
                        'confirmation_data': confirm_command.confirmation_data,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    'causation_id': correlation_id
                }
            ]
            
            return events
            
        except Exception as e:
            logger.error(f"Error processing ConfirmStage: {str(e)}")
            raise
    
    async def _process_submit_feedback(
        self, 
        command: CommandRequest, 
        correlation_id: str,
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Process SubmitFeedback command."""
        try:
            # Validate payload
            feedback_command = SubmitFeedbackCommand(**command.payload)
            
            # Generate events
            events = [
                {
                    'event_type': 'Genesis.Session.FeedbackSubmitted',
                    'aggregate_id': command.session_id,
                    'event_data': {
                        'session_id': command.session_id,
                        'feedback_type': feedback_command.feedback_type,
                        'feedback_data': feedback_command.feedback_data,
                        'rating': feedback_command.rating,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    'causation_id': correlation_id
                }
            ]
            
            return events
            
        except Exception as e:
            logger.error(f"Error processing SubmitFeedback: {str(e)}")
            raise
    
    async def get_command_status(self, command_id: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
        """Get command status by ID."""
        try:
            query = select(CommandInbox).where(CommandInbox.command_id == command_id)
            result = await session.execute(query)
            command = result.scalars().first()
            
            if command:
                return {
                    'command_id': command.command_id,
                    'session_id': command.session_id,
                    'command_type': command.command_type,
                    'status': command.status,
                    'created_at': command.created_at.isoformat(),
                    'updated_at': command.updated_at.isoformat() if command.updated_at else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting command status: {str(e)}")
            return None
    
    async def get_failed_commands(self, session: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
        """Get failed commands for monitoring."""
        try:
            query = select(CommandInbox).where(
                CommandInbox.status == "FAILED"
            ).order_by(CommandInbox.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            commands = result.scalars().all()
            
            return [
                {
                    'command_id': cmd.command_id,
                    'session_id': cmd.session_id,
                    'command_type': cmd.command_type,
                    'status': cmd.status,
                    'created_at': cmd.created_at.isoformat(),
                    'updated_at': cmd.updated_at.isoformat() if cmd.updated_at else None
                }
                for cmd in commands
            ]
            
        except Exception as e:
            logger.error(f"Error getting failed commands: {str(e)}")
            return []