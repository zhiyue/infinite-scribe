"""Message Relay Service - Publishes events from outbox to Kafka."""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_async_session
from src.core.messaging import kafka_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format=settings.LOG_FORMAT,
)
logger = logging.getLogger(__name__)

# Service configuration
RELAY_POLL_INTERVAL = int(os.getenv("RELAY_POLL_INTERVAL", "5"))  # seconds
RELAY_BATCH_SIZE = int(os.getenv("RELAY_BATCH_SIZE", "100"))  # records per batch


class MessageRelayService:
    """Service for relaying events from outbox to Kafka."""
    
    def __init__(self):
        self.running = False
        self.kafka_manager = kafka_manager
        
    async def start(self):
        """Start the message relay service."""
        logger.info("Starting Message Relay Service...")
        
        try:
            # Start Kafka producer
            await self.kafka_manager.start()
            
            self.running = True
            logger.info("Message Relay Service started successfully")
            
            # Start polling loop
            await self._polling_loop()
            
        except Exception as e:
            logger.error(f"Failed to start Message Relay Service: {e}")
            raise
    
    async def stop(self):
        """Stop the message relay service gracefully."""
        logger.info("Stopping Message Relay Service...")
        
        self.running = False
        
        # Stop Kafka producer
        await self.kafka_manager.stop()
        
        logger.info("Message Relay Service stopped")
    
    async def _polling_loop(self):
        """Main polling loop for processing outbox events."""
        while self.running:
            try:
                # Process a batch of pending events
                processed_count = await self._process_pending_events()
                
                if processed_count > 0:
                    logger.info(f"Processed {processed_count} events")
                
                # Wait before next poll
                await asyncio.sleep(RELAY_POLL_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(RELAY_POLL_INTERVAL)
    
    async def _process_pending_events(self) -> int:
        """Process pending events from the outbox."""
        async with get_async_session() as db:
            # Get pending events
            pending_events = await self._get_pending_events(db)
            
            if not pending_events:
                return 0
            
            processed_count = 0
            
            for event in pending_events:
                try:
                    success = await self._publish_event(event, db)
                    if success:
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing event {event['id']}: {e}")
                    
            return processed_count
    
    async def _get_pending_events(self, db: AsyncSession) -> List[dict]:
        """Get pending events from the outbox table."""
        query = text("""
            SELECT id, topic, key, payload, headers, retry_count, max_retries
            FROM event_outbox
            WHERE status = 'PENDING'
            AND (scheduled_at IS NULL OR scheduled_at <= :now)
            ORDER BY created_at ASC
            LIMIT :batch_size
        """)
        
        result = await db.execute(query, {
            "now": datetime.now(UTC),
            "batch_size": RELAY_BATCH_SIZE,
        })
        
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def _publish_event(self, event: dict, db: AsyncSession) -> bool:
        """Publish a single event to Kafka with retry logic."""
        event_id = event['id']
        
        try:
            # Parse payload if it's a string
            payload = event['payload']
            if isinstance(payload, str):
                payload = json.loads(payload)
            
            # Parse headers if they exist
            headers = None
            if event['headers']:
                if isinstance(event['headers'], str):
                    headers = json.loads(event['headers'])
                else:
                    headers = event['headers']
            
            # Convert headers to the format expected by Kafka
            kafka_headers = {}
            if headers:
                for k, v in headers.items():
                    if isinstance(v, str):
                        kafka_headers[k] = v.encode('utf-8')
                    elif isinstance(v, bytes):
                        kafka_headers[k] = v
                    else:
                        kafka_headers[k] = str(v).encode('utf-8')
            
            # Publish to Kafka
            success = await self.kafka_manager.send_message(
                topic=event['topic'],
                key=event['key'],
                value=json.dumps(payload),
                headers=kafka_headers,
            )
            
            if success:
                # Mark as sent
                await self._mark_event_sent(event_id, db)
                logger.debug(f"Event {event_id} published successfully")
                return True
            else:
                # Handle failure with retry logic
                await self._handle_publish_failure(event, db)
                return False
                
        except Exception as e:
            logger.error(f"Error publishing event {event_id}: {e}")
            await self._handle_publish_failure(event, db)
            return False
    
    async def _mark_event_sent(self, event_id: str, db: AsyncSession):
        """Mark an event as successfully sent."""
        update_stmt = text("""
            UPDATE event_outbox
            SET status = 'SENT', sent_at = :sent_at
            WHERE id = :event_id
        """)
        
        await db.execute(update_stmt, {
            "sent_at": datetime.now(UTC),
            "event_id": event_id,
        })
        await db.commit()
    
    async def _handle_publish_failure(self, event: dict, db: AsyncSession):
        """Handle failed event publishing with exponential backoff retry."""
        event_id = event['id']
        retry_count = event['retry_count']
        max_retries = event['max_retries']
        
        if retry_count < max_retries:
            # Increment retry count and schedule next attempt
            next_retry_count = retry_count + 1
            
            # Exponential backoff: 1s, 2s, 4s
            backoff_seconds = 2 ** (next_retry_count - 1)
            scheduled_at = datetime.now(UTC).timestamp() + backoff_seconds
            scheduled_at = datetime.fromtimestamp(scheduled_at, UTC)
            
            update_stmt = text("""
                UPDATE event_outbox
                SET retry_count = :retry_count, scheduled_at = :scheduled_at
                WHERE id = :event_id
            """)
            
            await db.execute(update_stmt, {
                "retry_count": next_retry_count,
                "scheduled_at": scheduled_at,
                "event_id": event_id,
            })
            
            logger.warning(f"Event {event_id} failed, scheduling retry {next_retry_count}/{max_retries} in {backoff_seconds}s")
            
        else:
            # Mark as failed after max retries
            update_stmt = text("""
                UPDATE event_outbox
                SET status = 'FAILED', last_error = :error
                WHERE id = :event_id
            """)
            
            await db.execute(update_stmt, {
                "error": f"Failed after {max_retries} retry attempts",
                "event_id": event_id,
            })
            
            logger.error(f"Event {event_id} marked as FAILED after {max_retries} retry attempts")
        
        await db.commit()


# Global service instance
relay_service = MessageRelayService()


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(relay_service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for the Message Relay Service."""
    # Check service type environment variable
    service_type = os.getenv("SERVICE_TYPE", "")
    if service_type != "message-relay":
        logger.error("SERVICE_TYPE must be set to 'message-relay' to run this service")
        sys.exit(1)
    
    logger.info("Starting Message Relay Service...")
    logger.info(f"Configuration: Poll interval={RELAY_POLL_INTERVAL}s, Batch size={RELAY_BATCH_SIZE}")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    try:
        await relay_service.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)
    finally:
        await relay_service.stop()


if __name__ == "__main__":
    asyncio.run(main())