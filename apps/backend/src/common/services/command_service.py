"""Command service for handling transactional command processing."""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.event_publisher import event_publisher
from src.models.api import CommandResult
from src.models.db import CommandStatus

logger = logging.getLogger(__name__)


class CommandService:
    """Service for processing commands with transactional guarantees."""
    
    # Official verbs for event naming
    OFFICIAL_VERBS = {
        'Requested', 'Created', 'Proposed', 'Submitted', 'Confirmed', 
        'Updated', 'Revised', 'Completed', 'Finished', 'Failed'
    }
    
    def __init__(self):
        self.event_publisher = event_publisher
    
    async def process_command(
        self,
        session_id: UUID,
        command_type: str,
        payload: Dict[str, Any],
        db: AsyncSession,
        idempotency_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> CommandResult:
        """
        Process a command with transactional guarantees.
        
        Args:
            session_id: Genesis session ID
            command_type: Type of command to process
            payload: Command payload data
            db: Database session
            idempotency_key: Optional idempotency key for duplicate detection
            user_id: Optional user ID for metadata
            
        Returns:
            CommandResult: Result of command processing
            
        Raises:
            IntegrityError: If duplicate command detected (409 Conflict)
        """
        command_id = uuid4()
        
        # Generate idempotency key if not provided
        if idempotency_key is None:
            idempotency_key = str(command_id)
        
        try:
            # Begin transaction scope
            async with db.begin():
                # 1. Insert command into command_inbox (triggers uniqueness check)
                await self._insert_command_inbox(
                    command_id=command_id,
                    session_id=session_id,
                    command_type=command_type,
                    payload=payload,
                    idempotency_key=idempotency_key,
                    db=db,
                )
                
                # 2. Generate and insert domain event
                event_type = self._generate_event_type(command_type)
                causation_id = await self._get_last_event_id(session_id, db)
                
                await self._insert_domain_event(
                    event_type=event_type,
                    aggregate_id=str(session_id),
                    command_id=command_id,
                    payload=payload,
                    causation_id=causation_id,
                    user_id=user_id,
                    db=db,
                )
                
                # 3. Save event to outbox for Kafka publishing
                await self.event_publisher.publish_domain_event(
                    event_type=event_type,
                    aggregate_type="GENESIS_SESSION",
                    aggregate_id=str(session_id),
                    payload={
                        "session_id": str(session_id),
                        "command_type": command_type,
                        "command_payload": payload,
                    },
                    correlation_id=str(command_id),
                    causation_id=causation_id,
                    metadata={
                        "user_id": user_id,
                        "source_service": "api-gateway",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    db=db,
                )
                
                # 4. Update command status to completed
                await self._update_command_status(
                    command_id=command_id,
                    status=CommandStatus.COMPLETED,
                    db=db,
                )
                
                # Transaction commits here
                
            logger.info(f"Command processed successfully: {command_id}")
            return CommandResult(
                command_id=command_id,
                status=CommandStatus.COMPLETED.value,
                message="Command processed successfully",
            )
            
        except IntegrityError as e:
            # Handle duplicate command (unique constraint violation)
            logger.warning(f"Duplicate command detected for session {session_id}, command_type {command_type}")
            
            # Get the existing command ID for the response
            existing_command_id = await self._get_existing_command_id(
                session_id=session_id,
                command_type=command_type,
                db=db,
            )
            
            # Re-raise with the existing command ID for the API to handle
            raise DuplicateCommandError(
                f"Command already processing",
                existing_command_id=existing_command_id,
            )
            
        except Exception as e:
            logger.error(f"Error processing command {command_id}: {e}")
            
            # Try to update command status to failed
            try:
                await self._update_command_status(
                    command_id=command_id,
                    status=CommandStatus.FAILED,
                    error_message=str(e),
                    db=db,
                )
            except Exception as update_error:
                logger.error(f"Failed to update command status: {update_error}")
            
            raise
    
    async def _insert_command_inbox(
        self,
        command_id: UUID,
        session_id: UUID,
        command_type: str,
        payload: Dict[str, Any],
        idempotency_key: str,
        db: AsyncSession,
    ) -> None:
        """Insert command into command_inbox table."""
        insert_stmt = text("""
            INSERT INTO command_inbox 
            (id, session_id, command_type, idempotency_key, payload, status, created_at, updated_at)
            VALUES 
            (:id, :session_id, :command_type, :idempotency_key, :payload, :status, :created_at, :updated_at)
        """)
        
        await db.execute(insert_stmt, {
            'id': command_id,
            'session_id': session_id,
            'command_type': command_type,
            'idempotency_key': idempotency_key,
            'payload': json.dumps(payload),
            'status': CommandStatus.RECEIVED.value,
            'created_at': datetime.now(UTC),
            'updated_at': datetime.now(UTC),
        })
    
    async def _insert_domain_event(
        self,
        event_type: str,
        aggregate_id: str,
        command_id: UUID,
        payload: Dict[str, Any],
        causation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: AsyncSession = None,
    ) -> None:
        """Insert domain event into domain_events table."""
        event_id = str(uuid4())
        
        insert_stmt = text("""
            INSERT INTO domain_events 
            (event_id, correlation_id, causation_id, event_type, event_version, 
             aggregate_type, aggregate_id, payload, metadata, created_at)
            VALUES 
            (:event_id, :correlation_id, :causation_id, :event_type, :event_version,
             :aggregate_type, :aggregate_id, :payload, :metadata, :created_at)
        """)
        
        metadata = {
            "user_id": user_id,
            "source_service": "api-gateway",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        await db.execute(insert_stmt, {
            'event_id': event_id,
            'correlation_id': str(command_id),
            'causation_id': causation_id,
            'event_type': event_type,
            'event_version': 1,
            'aggregate_type': 'GENESIS_SESSION',
            'aggregate_id': aggregate_id,
            'payload': json.dumps(payload),
            'metadata': json.dumps(metadata),
            'created_at': datetime.now(UTC),
        })
    
    async def _update_command_status(
        self,
        command_id: UUID,
        status: CommandStatus,
        error_message: Optional[str] = None,
        db: AsyncSession = None,
    ) -> None:
        """Update command status in command_inbox table."""
        update_stmt = text("""
            UPDATE command_inbox 
            SET status = :status, error_message = :error_message, updated_at = :updated_at
            WHERE id = :command_id
        """)
        
        await db.execute(update_stmt, {
            'status': status.value,
            'error_message': error_message,
            'updated_at': datetime.now(UTC),
            'command_id': command_id,
        })
    
    async def _get_existing_command_id(
        self,
        session_id: UUID,
        command_type: str,
        db: AsyncSession,
    ) -> Optional[UUID]:
        """Get existing command ID for duplicate detection."""
        query = text("""
            SELECT id FROM command_inbox 
            WHERE session_id = :session_id 
            AND command_type = :command_type 
            AND status IN ('RECEIVED', 'PROCESSING')
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = await db.execute(query, {
            'session_id': session_id,
            'command_type': command_type,
        })
        
        row = result.fetchone()
        return row[0] if row else None
    
    async def _get_last_event_id(
        self,
        session_id: UUID,
        db: AsyncSession,
    ) -> Optional[str]:
        """Get the last event ID for the session (for causation_id)."""
        query = text("""
            SELECT event_id FROM domain_events 
            WHERE aggregate_id = :aggregate_id 
            AND aggregate_type = 'GENESIS_SESSION'
            ORDER BY id DESC
            LIMIT 1
        """)
        
        result = await db.execute(query, {
            'aggregate_id': str(session_id),
        })
        
        row = result.fetchone()
        return row[0] if row else None
    
    def _generate_event_type(self, command_type: str) -> str:
        """
        Generate domain event type from command type.
        
        Follows the naming convention: Genesis.Session.<ActionInPastTense>
        """
        # Map command types to past tense verbs
        command_to_verb = {
            'RequestConceptGeneration': 'Requested',
            'ConfirmStage': 'Confirmed',
            'SubmitFeedback': 'Submitted',
            'CreateSession': 'Created',
            'UpdateSession': 'Updated',
            'CompleteSession': 'Completed',
        }
        
        # Get the verb or default to 'Requested'
        verb = command_to_verb.get(command_type, 'Requested')
        
        # Validate verb is in official list
        if verb not in self.OFFICIAL_VERBS:
            logger.warning(f"Using non-official verb '{verb}' for command type '{command_type}'")
        
        return f"Genesis.Session.{verb}"


class DuplicateCommandError(Exception):
    """Exception raised when a duplicate command is detected."""
    
    def __init__(self, message: str, existing_command_id: Optional[UUID] = None):
        super().__init__(message)
        self.existing_command_id = existing_command_id


# Global command service instance
command_service = CommandService()