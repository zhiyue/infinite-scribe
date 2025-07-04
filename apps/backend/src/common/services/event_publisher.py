"""Event publisher service for transactional outbox pattern."""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db import EventOutboxModel, OutboxStatus

logger = logging.getLogger(__name__)


class EventPublisherService:
    """Service for publishing events to the outbox table."""
    
    REQUIRED_EVENT_FIELDS = {"event_id", "correlation_id", "causation_id", "event_type", "aggregate_type", "aggregate_id"}
    
    def __init__(self):
        self.topic_name = "domain-events"
    
    async def save_to_outbox(
        self,
        topic: str,
        key: str,
        payload: Dict[str, Any],
        db: AsyncSession,
        headers: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Save an event to the outbox table for reliable delivery.
        
        Args:
            topic: Kafka topic name
            key: Message key (typically aggregate_id)
            payload: Event payload containing domain event data
            db: Database session
            headers: Optional message headers
            
        Returns:
            UUID: The outbox record ID
            
        Raises:
            ValueError: If the event payload is missing required fields
        """
        # Validate event payload
        self._validate_event_payload(payload)
        
        # Create outbox record
        outbox_id = uuid4()
        outbox_record = EventOutboxModel(
            id=outbox_id,
            topic=topic,
            key=key,
            payload=payload,
            headers=headers,
            status=OutboxStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        
        # Insert into database using raw SQL to avoid ORM issues
        insert_stmt = text("""
            INSERT INTO event_outbox 
            (id, topic, key, partition_key, payload, headers, status, retry_count, max_retries, created_at)
            VALUES 
            (:id, :topic, :key, :partition_key, :payload, :headers, :status, :retry_count, :max_retries, :created_at)
        """)
        
        await db.execute(insert_stmt, {
            'id': outbox_id,
            'topic': topic,
            'key': key,
            'partition_key': key,  # Use key as partition key for consistent partitioning
            'payload': json.dumps(payload),
            'headers': json.dumps(headers) if headers else None,
            'status': OutboxStatus.PENDING.value,
            'retry_count': 0,
            'max_retries': 5,
            'created_at': datetime.now(UTC),
        })
        
        logger.info(f"Event saved to outbox: {outbox_id}, topic: {topic}, key: {key}")
        return outbox_id
    
    def _validate_event_payload(self, payload: Dict[str, Any]) -> None:
        """
        Validate that the event payload contains all required fields.
        
        Args:
            payload: Event payload to validate
            
        Raises:
            ValueError: If required fields are missing
        """
        if not isinstance(payload, dict):
            raise ValueError("Event payload must be a dictionary")
        
        missing_fields = self.REQUIRED_EVENT_FIELDS - set(payload.keys())
        if missing_fields:
            raise ValueError(f"Event payload missing required fields: {missing_fields}")
        
        # Validate specific field types
        if not isinstance(payload.get('event_id'), str):
            raise ValueError("event_id must be a string")
        
        if payload.get('correlation_id') is not None and not isinstance(payload.get('correlation_id'), str):
            raise ValueError("correlation_id must be a string or None")
        
        if payload.get('causation_id') is not None and not isinstance(payload.get('causation_id'), str):
            raise ValueError("causation_id must be a string or None")
        
        if not isinstance(payload.get('event_type'), str):
            raise ValueError("event_type must be a string")
        
        if not isinstance(payload.get('aggregate_type'), str):
            raise ValueError("aggregate_type must be a string")
        
        if not isinstance(payload.get('aggregate_id'), str):
            raise ValueError("aggregate_id must be a string")
    
    async def publish_domain_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: AsyncSession = None,
    ) -> UUID:
        """
        Publish a domain event to the outbox.
        
        Args:
            event_type: Type of domain event
            aggregate_type: Type of aggregate
            aggregate_id: ID of the aggregate
            payload: Event payload data
            correlation_id: Correlation ID for tracking
            causation_id: ID of the event that caused this event
            metadata: Additional metadata
            db: Database session
            
        Returns:
            UUID: The outbox record ID
        """
        event_id = str(uuid4())
        
        # Construct complete event payload
        event_payload = {
            'event_id': event_id,
            'correlation_id': correlation_id,
            'causation_id': causation_id,
            'event_type': event_type,
            'event_version': 1,
            'aggregate_type': aggregate_type,
            'aggregate_id': aggregate_id,
            'payload': payload,
            'metadata': metadata or {},
            'created_at': datetime.now(UTC).isoformat(),
        }
        
        # Save to outbox
        return await self.save_to_outbox(
            topic=self.topic_name,
            key=aggregate_id,
            payload=event_payload,
            db=db,
            headers={'content-type': 'application/json'},
        )


# Global event publisher instance
event_publisher = EventPublisherService()