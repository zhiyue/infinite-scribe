"""
Test Redis cache structure configuration for Task 1 implementation.

Tests the creation of session caching with 30-day TTL
as required by the novel genesis stage architecture.
"""

import uuid
from datetime import UTC, datetime

import pytest
from src.common.services.conversation_cache import ConversationCacheManager
from src.db.redis import redis_service


@pytest.mark.asyncio
@pytest.mark.integration
class TestRedisCacheMigration:
    """Test Redis cache migration for conversation sessions."""

    async def test_redis_connection(self):
        """Test that Redis service is available and accessible."""
        try:
            await redis_service.connect()
            is_connected = await redis_service.check_connection()
            assert is_connected, "Redis should be accessible"

            # Test basic operations
            test_key = "test:connection"
            await redis_service.set(test_key, "test_value")

            value = await redis_service.get(test_key)
            assert value == "test_value"

            await redis_service.delete(test_key)
            await redis_service.disconnect()

        except Exception as e:
            pytest.fail(f"Redis service is not available: {e}")

    async def test_conversation_cache_manager_creation(self):
        """Test creation and configuration of conversation cache manager."""
        cache_manager = ConversationCacheManager()

        # Test connection
        await cache_manager.connect()
        is_connected = await cache_manager.is_connected()
        assert is_connected, "Cache manager should connect to Redis"

        # Test TTL configuration
        assert cache_manager.default_session_ttl == 30 * 24 * 60 * 60, "Default TTL should be 30 days"

        await cache_manager.disconnect()

    async def test_conversation_session_caching(self):
        """Test caching of conversation sessions with proper TTL."""
        cache_manager = ConversationCacheManager()
        await cache_manager.connect()

        # Test session data
        session_id = str(uuid.uuid4())
        session_data = {
            "id": session_id,
            "scope_type": "GENESIS",
            "scope_id": str(uuid.uuid4()),
            "status": "ACTIVE",
            "stage": "STAGE0",
            "state": {"current_step": "character_design", "progress": 0.3},
            "version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # Test caching session
        success = await cache_manager.cache_session(session_id, session_data)
        assert success, "Session caching should succeed"

        # Test retrieving session
        cached_data = await cache_manager.get_session(session_id)
        assert cached_data is not None, "Cached session should be retrievable"
        assert cached_data["id"] == session_id
        assert cached_data["scope_type"] == "GENESIS"
        assert cached_data["state"]["current_step"] == "character_design"

        # Test TTL is set correctly
        ttl = await cache_manager.get_session_ttl(session_id)
        assert ttl > 0, "Session should have TTL set"
        assert ttl <= 30 * 24 * 60 * 60, "TTL should not exceed 30 days"
        assert ttl > (30 * 24 * 60 * 60) - 60, "TTL should be close to 30 days"  # Allow 1 minute variance

        # Test session update
        updated_data = session_data.copy()
        updated_data["state"]["progress"] = 0.7
        updated_data["version"] = 2

        success = await cache_manager.cache_session(session_id, updated_data)
        assert success, "Session update should succeed"

        cached_updated = await cache_manager.get_session(session_id)
        assert cached_updated["state"]["progress"] == 0.7
        assert cached_updated["version"] == 2

        # Clean up
        await cache_manager.delete_session(session_id)
        await cache_manager.disconnect()

    async def test_conversation_cache_key_structure(self):
        """Test that cache keys follow the expected naming convention."""
        cache_manager = ConversationCacheManager()
        await cache_manager.connect()

        session_id = str(uuid.uuid4())

        # Test key generation
        expected_key = f"conversation:session:{session_id}"
        actual_key = cache_manager.get_session_key(session_id)
        assert actual_key == expected_key, "Session key should follow naming convention"

        # Test round cache key
        round_path = "1.2.3"
        expected_round_key = f"conversation:session:{session_id}:round:{round_path}"
        actual_round_key = cache_manager.get_round_key(session_id, round_path)
        assert actual_round_key == expected_round_key, "Round key should follow naming convention"

        await cache_manager.disconnect()

    async def test_conversation_round_caching(self):
        """Test caching of individual conversation rounds."""
        cache_manager = ConversationCacheManager()
        await cache_manager.connect()

        session_id = str(uuid.uuid4())
        round_path = "1.2"
        round_data = {
            "session_id": session_id,
            "round_path": round_path,
            "role": "user",
            "input": {"content": "Tell me about the main character"},
            "output": {"content": "The main character is a brave knight..."},
            "model": "claude-3-opus",
            "tokens_in": 15,
            "tokens_out": 87,
            "latency_ms": 1250,
            "correlation_id": str(uuid.uuid4()),
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Test caching round
        success = await cache_manager.cache_round(session_id, round_path, round_data)
        assert success, "Round caching should succeed"

        # Test retrieving round
        cached_round = await cache_manager.get_round(session_id, round_path)
        assert cached_round is not None, "Cached round should be retrievable"
        assert cached_round["round_path"] == round_path
        assert cached_round["role"] == "user"
        assert cached_round["tokens_in"] == 15

        # Test round TTL (should inherit from session TTL)
        round_ttl = await cache_manager.get_round_ttl(session_id, round_path)
        assert round_ttl > 0, "Round should have TTL set"

        # Clean up
        await cache_manager.delete_round(session_id, round_path)
        await cache_manager.disconnect()

    async def test_conversation_cache_bulk_operations(self):
        """Test bulk operations on conversation cache."""
        cache_manager = ConversationCacheManager()
        await cache_manager.connect()

        session_id = str(uuid.uuid4())

        # Test bulk round retrieval
        rounds_data = []
        for i in range(5):
            round_path = str(i + 1)
            round_data = {
                "session_id": session_id,
                "round_path": round_path,
                "role": "user" if i % 2 == 0 else "assistant",
                "input": {"content": f"Round {i+1} input"},
                "output": {"content": f"Round {i+1} output"},
                "created_at": datetime.now(UTC).isoformat(),
            }
            rounds_data.append((round_path, round_data))
            await cache_manager.cache_round(session_id, round_path, round_data)

        # Test retrieving all rounds for session
        all_rounds = await cache_manager.get_session_rounds(session_id)
        assert len(all_rounds) == 5, "Should retrieve all cached rounds"

        round_paths = {round["round_path"] for round in all_rounds}
        expected_paths = {"1", "2", "3", "4", "5"}
        assert round_paths == expected_paths, "Should retrieve all round paths"

        # Test clearing session (removes session and all rounds)
        await cache_manager.clear_session(session_id)

        # Verify session and rounds are deleted
        session_data = await cache_manager.get_session(session_id)
        assert session_data is None, "Session should be deleted"

        remaining_rounds = await cache_manager.get_session_rounds(session_id)
        assert len(remaining_rounds) == 0, "All rounds should be deleted"

        await cache_manager.disconnect()

    async def test_conversation_cache_expiration_renewal(self):
        """Test TTL renewal and expiration management."""
        cache_manager = ConversationCacheManager()
        await cache_manager.connect()

        session_id = str(uuid.uuid4())
        session_data = {
            "id": session_id,
            "scope_type": "GENESIS",
            "status": "ACTIVE",
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Cache with custom TTL
        custom_ttl = 300  # 5 minutes
        success = await cache_manager.cache_session(session_id, session_data, ttl=custom_ttl)
        assert success

        # Verify custom TTL
        ttl = await cache_manager.get_session_ttl(session_id)
        assert ttl <= custom_ttl
        assert ttl > custom_ttl - 60  # Allow some variance

        # Test TTL renewal
        success = await cache_manager.renew_session_ttl(session_id)
        assert success, "TTL renewal should succeed"

        # Verify TTL was renewed to default
        renewed_ttl = await cache_manager.get_session_ttl(session_id)
        assert renewed_ttl > custom_ttl, "TTL should be renewed to default value"

        # Clean up
        await cache_manager.delete_session(session_id)
        await cache_manager.disconnect()
