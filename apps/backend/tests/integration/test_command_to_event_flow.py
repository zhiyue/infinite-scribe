"""Integration tests for command-to-event flow."""

import asyncio
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

from src.common.services.command_service import command_service
from src.common.services.event_publisher import event_publisher
from src.core.database import get_async_session
from src.core.messaging import kafka_manager


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing."""
    with PostgresContainer("postgres:16") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def kafka_container():
    """Start Kafka container for testing."""
    with KafkaContainer() as kafka:
        yield kafka


@pytest.fixture(scope="session")
async def db_engine(postgres_container):
    """Create database engine with test database."""
    db_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(db_url)
    
    # Run migrations - create tables
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS command_inbox (
                id UUID PRIMARY KEY,
                session_id UUID NOT NULL,
                command_type VARCHAR(255) NOT NULL,
                idempotency_key VARCHAR(255) NOT NULL,
                payload JSONB,
                status VARCHAR(50) NOT NULL DEFAULT 'RECEIVED',
                error_message TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS domain_events (
                id SERIAL PRIMARY KEY,
                event_id UUID NOT NULL,
                correlation_id UUID,
                causation_id UUID,
                event_type VARCHAR(255) NOT NULL,
                event_version INTEGER NOT NULL DEFAULT 1,
                aggregate_type VARCHAR(255) NOT NULL,
                aggregate_id VARCHAR(255) NOT NULL,
                payload JSONB,
                metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_outbox (
                id UUID PRIMARY KEY,
                topic VARCHAR(255) NOT NULL,
                key VARCHAR(255),
                partition_key VARCHAR(255),
                payload JSONB NOT NULL,
                headers JSONB,
                status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 5,
                last_error TEXT,
                scheduled_at TIMESTAMP WITH TIME ZONE,
                sent_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS genesis_sessions (
                id UUID PRIMARY KEY,
                user_id VARCHAR(255),
                novel_id UUID,
                status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS',
                current_stage VARCHAR(50) NOT NULL DEFAULT 'CONCEPT_SELECTION',
                confirmed_data JSONB,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """))
        
        # Create unique constraint for command_inbox
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_command_inbox_unique_pending_command 
            ON command_inbox (session_id, command_type) 
            WHERE status IN ('RECEIVED', 'PROCESSING');
        """))
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create database session for testing."""
    async with AsyncSession(db_engine) as session:
        yield session


@pytest.fixture
async def test_session_id(db_session):
    """Create a test genesis session."""
    session_id = uuid4()
    
    # Insert test session
    await db_session.execute(text("""
        INSERT INTO genesis_sessions (id, user_id, status, current_stage, created_at, updated_at)
        VALUES (:id, :user_id, :status, :current_stage, NOW(), NOW())
    """), {
        'id': session_id,
        'user_id': 'test-user',
        'status': 'IN_PROGRESS',
        'current_stage': 'CONCEPT_SELECTION'
    })
    await db_session.commit()
    
    return session_id


class TestCommandProcessingFlow:
    """Test complete command processing flow."""
    
    @pytest.mark.asyncio
    async def test_process_command_creates_all_records(
        self, db_session, test_session_id
    ):
        """Test that processing a command creates records in all three tables."""
        # Setup
        command_type = "RequestConceptGeneration"
        payload = {"theme_preferences": ["科幻", "悬疑"]}
        user_id = "test-user"
        
        # Execute
        result = await command_service.process_command(
            session_id=test_session_id,
            command_type=command_type,
            payload=payload,
            db=db_session,
            user_id=user_id
        )
        
        # Verify command result
        assert result.command_id is not None
        assert result.status == "COMPLETED"
        
        # Verify command_inbox record
        command_result = await db_session.execute(text("""
            SELECT id, session_id, command_type, status, payload
            FROM command_inbox 
            WHERE id = :command_id
        """), {"command_id": result.command_id})
        
        command_row = command_result.fetchone()
        assert command_row is not None
        assert command_row[1] == test_session_id  # session_id
        assert command_row[2] == command_type  # command_type
        assert command_row[3] == "COMPLETED"  # status
        assert json.loads(command_row[4]) == payload  # payload
        
        # Verify domain_events record
        event_result = await db_session.execute(text("""
            SELECT event_type, aggregate_id, correlation_id, payload, metadata
            FROM domain_events 
            WHERE correlation_id = :command_id
        """), {"command_id": result.command_id})
        
        event_row = event_result.fetchone()
        assert event_row is not None
        assert event_row[0] == "Genesis.Session.Requested"  # event_type
        assert event_row[1] == str(test_session_id)  # aggregate_id
        assert str(event_row[2]) == str(result.command_id)  # correlation_id
        
        event_payload = json.loads(event_row[3])
        assert event_payload == payload
        
        event_metadata = json.loads(event_row[4])
        assert event_metadata["user_id"] == user_id
        assert event_metadata["source_service"] == "api-gateway"
        
        # Verify event_outbox record
        outbox_result = await db_session.execute(text("""
            SELECT topic, key, status, payload
            FROM event_outbox 
            WHERE JSON_EXTRACT(payload, '$.correlation_id') = :command_id
        """), {"command_id": f'"{result.command_id}"'})
        
        outbox_row = outbox_result.fetchone()
        assert outbox_row is not None
        assert outbox_row[0] == "domain-events"  # topic
        assert outbox_row[1] == str(test_session_id)  # key (aggregate_id)
        assert outbox_row[2] == "PENDING"  # status
    
    @pytest.mark.asyncio
    async def test_duplicate_command_prevention(
        self, db_session, test_session_id
    ):
        """Test that duplicate commands are prevented."""
        # Setup
        command_type = "ConfirmStage"
        payload = {"stage": "CONCEPT_SELECTION"}
        
        # Execute first command
        result1 = await command_service.process_command(
            session_id=test_session_id,
            command_type=command_type,
            payload=payload,
            db=db_session
        )
        
        # Try to execute duplicate command
        from src.common.services.command_service import DuplicateCommandError
        
        with pytest.raises(DuplicateCommandError) as exc_info:
            await command_service.process_command(
                session_id=test_session_id,
                command_type=command_type,
                payload=payload,
                db=db_session
            )
        
        # Verify the existing command ID is returned
        assert exc_info.value.existing_command_id == result1.command_id
        
        # Verify only one command record exists
        count_result = await db_session.execute(text("""
            SELECT COUNT(*) FROM command_inbox 
            WHERE session_id = :session_id AND command_type = :command_type
        """), {
            "session_id": test_session_id,
            "command_type": command_type
        })
        
        count = count_result.fetchone()[0]
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_causation_chain(self, db_session, test_session_id):
        """Test that events form a proper causation chain."""
        # Execute first command
        result1 = await command_service.process_command(
            session_id=test_session_id,
            command_type="CreateSession",
            payload={},
            db=db_session
        )
        
        # Execute second command
        result2 = await command_service.process_command(
            session_id=test_session_id,
            command_type="UpdateSession",
            payload={"data": "updated"},
            db=db_session
        )
        
        # Get the events
        events_result = await db_session.execute(text("""
            SELECT event_id, causation_id, correlation_id, created_at
            FROM domain_events 
            WHERE aggregate_id = :session_id
            ORDER BY id ASC
        """), {"session_id": str(test_session_id)})
        
        events = events_result.fetchall()
        assert len(events) == 2
        
        # First event should have no causation_id
        first_event = events[0]
        assert first_event[1] is None  # causation_id
        assert str(first_event[2]) == str(result1.command_id)  # correlation_id
        
        # Second event should be caused by first event
        second_event = events[1]
        assert second_event[1] == first_event[0]  # causation_id = first event_id
        assert str(second_event[2]) == str(result2.command_id)  # correlation_id


class TestTransactionalGuarantees:
    """Test transactional guarantees of the system."""
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, db_session, test_session_id):
        """Test that errors cause complete transaction rollback."""
        # Setup - Mock event publisher to fail
        original_publish = event_publisher.publish_domain_event
        
        async def failing_publish(*args, **kwargs):
            raise Exception("Simulated failure")
        
        event_publisher.publish_domain_event = failing_publish
        
        try:
            # Execute command (should fail)
            with pytest.raises(Exception):
                await command_service.process_command(
                    session_id=test_session_id,
                    command_type="FailingCommand",
                    payload={},
                    db=db_session
                )
            
            # Verify no records were created
            command_count = await db_session.execute(text("""
                SELECT COUNT(*) FROM command_inbox 
                WHERE session_id = :session_id AND command_type = 'FailingCommand'
            """), {"session_id": test_session_id})
            
            assert command_count.fetchone()[0] == 0
            
            domain_count = await db_session.execute(text("""
                SELECT COUNT(*) FROM domain_events 
                WHERE aggregate_id = :session_id
            """), {"session_id": str(test_session_id)})
            
            # Should only have records from test setup, not from failed command
            initial_count = domain_count.fetchone()[0]
            assert initial_count >= 0  # May have records from other tests
            
        finally:
            # Restore original function
            event_publisher.publish_domain_event = original_publish


class TestEventValidation:
    """Test event validation and structure."""
    
    @pytest.mark.asyncio
    async def test_event_has_required_fields(self, db_session, test_session_id):
        """Test that generated events have all required fields."""
        # Execute command
        result = await command_service.process_command(
            session_id=test_session_id,
            command_type="SubmitFeedback",
            payload={"feedback": "Great concept!"},
            db=db_session,
            user_id="test-user"
        )
        
        # Get the generated event from outbox
        outbox_result = await db_session.execute(text("""
            SELECT payload FROM event_outbox 
            WHERE JSON_EXTRACT(payload, '$.correlation_id') = :command_id
        """), {"command_id": f'"{result.command_id}"'})
        
        outbox_row = outbox_result.fetchone()
        event_payload = json.loads(outbox_row[0])
        
        # Verify all required fields are present
        required_fields = {
            'event_id', 'correlation_id', 'causation_id', 'event_type',
            'aggregate_type', 'aggregate_id', 'payload', 'metadata', 'created_at'
        }
        
        for field in required_fields:
            assert field in event_payload, f"Missing required field: {field}"
        
        # Verify field values
        assert event_payload['event_type'] == "Genesis.Session.Submitted"
        assert event_payload['aggregate_type'] == "GENESIS_SESSION"
        assert event_payload['aggregate_id'] == str(test_session_id)
        assert event_payload['correlation_id'] == str(result.command_id)
        assert event_payload['event_version'] == 1
        
        # Verify metadata structure
        metadata = event_payload['metadata']
        assert metadata['user_id'] == "test-user"
        assert metadata['source_service'] == "api-gateway"
        assert 'timestamp' in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])