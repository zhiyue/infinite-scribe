"""Integration tests for Message Relay service."""

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

from src.agents.message_relay.main import MessageRelayService
from src.core.messaging import KafkaManager


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
    
    # Create event_outbox table
    async with engine.begin() as conn:
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
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create database session for testing."""
    async with AsyncSession(db_engine) as session:
        yield session


@pytest.fixture
async def kafka_manager_test(kafka_container):
    """Create Kafka manager with test configuration."""
    manager = KafkaManager()
    manager.bootstrap_servers = kafka_container.get_bootstrap_server()
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
async def relay_service_test(kafka_manager_test):
    """Create Message Relay service with test configuration."""
    service = MessageRelayService()
    service.kafka_manager = kafka_manager_test
    return service


class TestMessageRelayIntegration:
    """Test Message Relay service integration with real Kafka and PostgreSQL."""
    
    @pytest.mark.asyncio
    async def test_relay_pending_event_to_kafka(
        self, db_session, relay_service_test, kafka_container
    ):
        """Test relaying a pending event from outbox to Kafka."""
        # Setup - Insert test event into outbox
        event_id = uuid4()
        test_payload = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Created",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "aggregate_type": "GENESIS_SESSION",
            "payload": {"test": "data"},
            "metadata": {"user_id": "test-user"}
        }
        
        await db_session.execute(text("""
            INSERT INTO event_outbox 
            (id, topic, key, payload, status, created_at)
            VALUES (:id, :topic, :key, :payload, :status, :created_at)
        """), {
            "id": event_id,
            "topic": "domain-events",
            "key": "test-key",
            "payload": json.dumps(test_payload),
            "status": "PENDING",
            "created_at": datetime.now(UTC)
        })
        await db_session.commit()
        
        # Setup Kafka consumer to verify message
        consumer = AIOKafkaConsumer(
            "domain-events",
            bootstrap_servers=kafka_container.get_bootstrap_server(),
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await consumer.start()
        
        try:
            # Execute - Process pending events
            processed_count = await relay_service_test._process_pending_events()
            
            # Verify event was processed
            assert processed_count == 1
            
            # Verify event status updated in database
            status_result = await db_session.execute(text("""
                SELECT status, sent_at FROM event_outbox WHERE id = :id
            """), {"id": event_id})
            
            status_row = status_result.fetchone()
            assert status_row[0] == "SENT"
            assert status_row[1] is not None
            
            # Verify message was published to Kafka
            message = await asyncio.wait_for(consumer.getone(), timeout=10.0)
            assert message.value == test_payload
            assert message.key.decode('utf-8') == "test-key"
            
        finally:
            await consumer.stop()
    
    @pytest.mark.asyncio
    async def test_relay_retry_logic(self, db_session, kafka_container):
        """Test retry logic for failed events."""
        # Setup - Create service with broken Kafka configuration
        broken_service = MessageRelayService()
        broken_manager = KafkaManager()
        broken_manager.bootstrap_servers = "localhost:9999"  # Non-existent server
        broken_service.kafka_manager = broken_manager
        
        # Insert test event
        event_id = uuid4()
        test_payload = {
            "event_id": str(uuid4()),
            "event_type": "Test.Event",
            "aggregate_id": str(uuid4()),
        }
        
        await db_session.execute(text("""
            INSERT INTO event_outbox 
            (id, topic, key, payload, status, retry_count, max_retries, created_at)
            VALUES (:id, :topic, :key, :payload, :status, :retry_count, :max_retries, :created_at)
        """), {
            "id": event_id,
            "topic": "domain-events",
            "key": "test-key",
            "payload": json.dumps(test_payload),
            "status": "PENDING",
            "retry_count": 2,  # Start at 2 retries
            "max_retries": 3,
            "created_at": datetime.now(UTC)
        })
        await db_session.commit()
        
        # Execute - Process pending events (should fail and mark as FAILED)
        processed_count = await broken_service._process_pending_events()
        
        # Verify event was processed but failed
        assert processed_count == 0  # No successful processing
        
        # Verify event status updated to FAILED
        status_result = await db_session.execute(text("""
            SELECT status, last_error, retry_count FROM event_outbox WHERE id = :id
        """), {"id": event_id})
        
        status_row = status_result.fetchone()
        assert status_row[0] == "FAILED"
        assert status_row[1] is not None  # Error message should be present
        assert status_row[2] == 3  # Retry count should be at max
    
    @pytest.mark.asyncio
    async def test_relay_multiple_events(
        self, db_session, relay_service_test, kafka_container
    ):
        """Test relaying multiple events in batch."""
        # Setup - Insert multiple test events
        event_ids = [uuid4() for _ in range(3)]
        test_payloads = []
        
        for i, event_id in enumerate(event_ids):
            payload = {
                "event_id": str(uuid4()),
                "event_type": f"Test.Event{i}",
                "aggregate_id": str(uuid4()),
                "payload": {"test": f"data{i}"}
            }
            test_payloads.append(payload)
            
            await db_session.execute(text("""
                INSERT INTO event_outbox 
                (id, topic, key, payload, status, created_at)
                VALUES (:id, :topic, :key, :payload, :status, :created_at)
            """), {
                "id": event_id,
                "topic": "domain-events",
                "key": f"test-key-{i}",
                "payload": json.dumps(payload),
                "status": "PENDING",
                "created_at": datetime.now(UTC)
            })
        
        await db_session.commit()
        
        # Setup Kafka consumer
        consumer = AIOKafkaConsumer(
            "domain-events",
            bootstrap_servers=kafka_container.get_bootstrap_server(),
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await consumer.start()
        
        try:
            # Execute - Process pending events
            processed_count = await relay_service_test._process_pending_events()
            
            # Verify all events were processed
            assert processed_count == 3
            
            # Verify all events status updated in database
            status_result = await db_session.execute(text("""
                SELECT COUNT(*) FROM event_outbox 
                WHERE id = ANY(:ids) AND status = 'SENT'
            """), {"ids": event_ids})
            
            sent_count = status_result.fetchone()[0]
            assert sent_count == 3
            
            # Verify all messages were published to Kafka
            received_messages = []
            for _ in range(3):
                message = await asyncio.wait_for(consumer.getone(), timeout=10.0)
                received_messages.append(message.value)
            
            # Verify all payloads were received
            received_event_types = [msg["event_type"] for msg in received_messages]
            expected_event_types = [f"Test.Event{i}" for i in range(3)]
            
            assert set(received_event_types) == set(expected_event_types)
            
        finally:
            await consumer.stop()
    
    @pytest.mark.asyncio
    async def test_relay_with_headers(
        self, db_session, relay_service_test, kafka_container
    ):
        """Test relaying events with headers."""
        # Setup - Insert test event with headers
        event_id = uuid4()
        test_payload = {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Created",
            "aggregate_id": str(uuid4()),
        }
        test_headers = {
            "content-type": "application/json",
            "source": "api-gateway"
        }
        
        await db_session.execute(text("""
            INSERT INTO event_outbox 
            (id, topic, key, payload, headers, status, created_at)
            VALUES (:id, :topic, :key, :payload, :headers, :status, :created_at)
        """), {
            "id": event_id,
            "topic": "domain-events",
            "key": "test-key",
            "payload": json.dumps(test_payload),
            "headers": json.dumps(test_headers),
            "status": "PENDING",
            "created_at": datetime.now(UTC)
        })
        await db_session.commit()
        
        # Setup Kafka consumer
        consumer = AIOKafkaConsumer(
            "domain-events",
            bootstrap_servers=kafka_container.get_bootstrap_server(),
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await consumer.start()
        
        try:
            # Execute - Process pending events
            processed_count = await relay_service_test._process_pending_events()
            
            # Verify event was processed
            assert processed_count == 1
            
            # Verify message was published with headers
            message = await asyncio.wait_for(consumer.getone(), timeout=10.0)
            assert message.value == test_payload
            
            # Verify headers (Kafka headers are bytes)
            if message.headers:
                header_dict = {k: v.decode('utf-8') for k, v in message.headers}
                assert header_dict["content-type"] == "application/json"
                assert header_dict["source"] == "api-gateway"
            
        finally:
            await consumer.stop()


class TestMessageRelayErrorHandling:
    """Test error handling in Message Relay service."""
    
    @pytest.mark.asyncio
    async def test_relay_handles_invalid_json_payload(
        self, db_session, relay_service_test
    ):
        """Test that relay service handles invalid JSON gracefully."""
        # Setup - Insert event with invalid JSON payload
        event_id = uuid4()
        
        await db_session.execute(text("""
            INSERT INTO event_outbox 
            (id, topic, key, payload, status, created_at)
            VALUES (:id, :topic, :key, :payload, :status, :created_at)
        """), {
            "id": event_id,
            "topic": "domain-events",
            "key": "test-key",
            "payload": "invalid json {",  # Invalid JSON
            "status": "PENDING",
            "created_at": datetime.now(UTC)
        })
        await db_session.commit()
        
        # Execute - Process pending events (should handle error gracefully)
        processed_count = await relay_service_test._process_pending_events()
        
        # Verify event was not processed successfully
        assert processed_count == 0
        
        # Verify retry count was incremented
        retry_result = await db_session.execute(text("""
            SELECT retry_count FROM event_outbox WHERE id = :id
        """), {"id": event_id})
        
        retry_count = retry_result.fetchone()[0]
        assert retry_count == 1  # Should be incremented due to error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])