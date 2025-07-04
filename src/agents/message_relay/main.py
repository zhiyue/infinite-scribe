"""
Message Relay Service - Polls event_outbox and publishes to Kafka.
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4

from sqlalchemy import text, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session, init_db
from src.core.messaging import MessageProducer, init_messaging
from src.models.database import EventOutbox

logger = logging.getLogger(__name__)


class MessageRelayService:
    """Service for relaying events from outbox to Kafka."""
    
    def __init__(self, producer: MessageProducer, batch_size: int = 100, poll_interval: int = 1):
        self.producer = producer
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.running = False
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # seconds
    
    async def start(self):
        """Start the message relay service."""
        self.running = True
        logger.info("Message Relay Service starting...")
        
        while self.running:
            try:
                async with get_session() as session:
                    # Get pending events in batch
                    events = await self._get_pending_events(session)
                    
                    if events:
                        logger.info(f"Processing {len(events)} pending events")
                        await self._process_events_batch(events, session)
                    
                    # Cleanup old failed events (older than 24 hours)
                    await self._cleanup_old_failed_events(session)
                    
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in message relay loop: {str(e)}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Stop the message relay service."""
        self.running = False
        logger.info("Message Relay Service stopping...")
    
    async def _get_pending_events(self, session: AsyncSession) -> List[EventOutbox]:
        """Get pending events from outbox, respecting scheduled_at for retries."""
        try:
            now = datetime.utcnow()
            
            # Get events that are:
            # 1. PENDING status
            # 2. scheduled_at is null (first attempt) or scheduled_at <= now (retry time reached)
            query = select(EventOutbox).where(
                and_(
                    EventOutbox.status == "PENDING",
                    or_(
                        EventOutbox.scheduled_at.is_(None),
                        EventOutbox.scheduled_at <= now
                    )
                )
            ).order_by(EventOutbox.created_at).limit(self.batch_size)
            
            result = await session.execute(query)
            events = result.scalars().all()
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting pending events: {str(e)}")
            return []
    
    async def _process_events_batch(self, events: List[EventOutbox], session: AsyncSession) -> None:
        """Process a batch of events."""
        event_ids = [event.event_id for event in events]
        
        # Mark events as PROCESSING to prevent double processing
        await self._update_events_status_batch(event_ids, "PROCESSING", session)
        
        # Process each event
        success_ids = []
        failed_events = []
        
        for event in events:
            try:
                success = await self._publish_event_to_kafka(event)
                if success:
                    success_ids.append(event.event_id)
                else:
                    failed_events.append(event)
                    
            except Exception as e:
                logger.error(f"Error processing event {event.event_id}: {str(e)}")
                failed_events.append(event)
        
        # Batch update successful events
        if success_ids:
            await self._update_events_status_batch(success_ids, "PUBLISHED", session)
        
        # Handle failed events with retry logic
        if failed_events:
            await self._handle_failed_events(failed_events, session)
    
    async def _publish_event_to_kafka(self, event: EventOutbox) -> bool:
        """Publish single event to Kafka."""
        try:
            # Prepare message
            message_value = {
                'event_id': event.event_id,
                'event_type': event.event_type,
                'aggregate_id': event.aggregate_id,
                'event_data': event.event_data,
                'correlation_id': event.correlation_id,
                'causation_id': event.causation_id,
                'created_at': event.created_at.isoformat(),
                'version': '1.0'
            }
            
            # Prepare headers (no double encoding)
            headers = {
                'event_type': event.event_type,
                'correlation_id': event.correlation_id,
                'created_at': event.created_at.isoformat(),
                'version': '1.0'
            }
            
            # Add causation_id if present
            if event.causation_id:
                headers['causation_id'] = event.causation_id
            
            # Determine topic based on event type
            topic = self._get_topic_for_event(event.event_type)
            
            # Publish to Kafka
            await self.producer.send_message(
                topic=topic,
                key=event.aggregate_id,
                value=message_value,
                headers=headers
            )
            
            logger.debug(f"Successfully published event {event.event_id} to topic {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {str(e)}")
            return False
    
    async def _handle_failed_events(self, failed_events: List[EventOutbox], session: AsyncSession) -> None:
        """Handle failed events with retry logic."""
        for event in failed_events:
            retry_count = event.retry_count or 0
            
            if retry_count < self.max_retries:
                # Calculate next retry time with exponential backoff
                delay_seconds = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
                scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
                
                # Update for retry
                await self._update_event_for_retry(event.event_id, retry_count + 1, scheduled_at, session)
                
                logger.warning(f"Event {event.event_id} failed, scheduling retry {retry_count + 1} in {delay_seconds}s")
                
            else:
                # Max retries reached, mark as FAILED
                await self._update_events_status_batch([event.event_id], "FAILED", session)
                
                logger.error(f"Event {event.event_id} failed permanently after {self.max_retries} retries")
    
    async def _update_events_status_batch(self, event_ids: List[str], status: str, session: AsyncSession) -> None:
        """Update status for multiple events in batch."""
        if not event_ids:
            return
        
        try:
            # Use batch update for better performance
            query = text("""
                UPDATE event_outbox 
                SET status = :status, updated_at = :updated_at
                WHERE event_id = ANY(:event_ids)
            """)
            
            await session.execute(query, {
                'status': status,
                'updated_at': datetime.utcnow(),
                'event_ids': event_ids
            })
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update events status: {str(e)}")
            await session.rollback()
            raise
    
    async def _update_event_for_retry(self, event_id: str, retry_count: int, scheduled_at: datetime, session: AsyncSession) -> None:
        """Update event for retry with scheduled time."""
        try:
            query = text("""
                UPDATE event_outbox 
                SET status = 'PENDING', retry_count = :retry_count, scheduled_at = :scheduled_at, updated_at = :updated_at
                WHERE event_id = :event_id
            """)
            
            await session.execute(query, {
                'retry_count': retry_count,
                'scheduled_at': scheduled_at,
                'updated_at': datetime.utcnow(),
                'event_id': event_id
            })
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update event for retry: {str(e)}")
            await session.rollback()
            raise
    
    async def _cleanup_old_failed_events(self, session: AsyncSession) -> None:
        """Clean up old failed events (older than 24 hours)."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            query = text("""
                DELETE FROM event_outbox 
                WHERE status = 'FAILED' AND updated_at < :cutoff_time
            """)
            
            result = await session.execute(query, {'cutoff_time': cutoff_time})
            await session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Cleaned up {result.rowcount} old failed events")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old failed events: {str(e)}")
            await session.rollback()
    
    def _get_topic_for_event(self, event_type: str) -> str:
        """Determine Kafka topic based on event type."""
        # Map event types to topics
        topic_mapping = {
            'Genesis.Session.ConceptGenerationRequested': 'genesis-concept-generation',
            'Genesis.Session.StageConfirmed': 'genesis-stage-management',
            'Genesis.Session.FeedbackSubmitted': 'genesis-feedback',
        }
        
        return topic_mapping.get(event_type, 'genesis-default')
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get message relay metrics."""
        try:
            async with get_session() as session:
                # Get status counts
                query = text("""
                    SELECT status, COUNT(*) as count
                    FROM event_outbox
                    GROUP BY status
                """)
                
                result = await session.execute(query)
                status_counts = {row.status: row.count for row in result}
                
                # Get retry counts
                retry_query = text("""
                    SELECT retry_count, COUNT(*) as count
                    FROM event_outbox
                    WHERE retry_count > 0
                    GROUP BY retry_count
                """)
                
                retry_result = await session.execute(retry_query)
                retry_counts = {row.retry_count: row.count for row in retry_result}
                
                return {
                    'status_counts': status_counts,
                    'retry_counts': retry_counts,
                    'total_events': sum(status_counts.values()),
                    'service_running': self.running
                }
                
        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            return {'error': str(e)}


async def main():
    """Main function to run the message relay service."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize database
        await init_db()
        
        # Initialize messaging
        await init_messaging()
        
        # Create message producer
        from src.core.messaging import kafka_manager
        producer = MessageProducer(kafka_manager.producer)
        
        # Create and start service
        service = MessageRelayService(producer)
        
        # Handle graceful shutdown
        import signal
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            service.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start service
        await service.start()
        
    except Exception as e:
        logger.error(f"Failed to start message relay service: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())