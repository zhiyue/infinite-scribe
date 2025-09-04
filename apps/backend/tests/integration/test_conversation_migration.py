"""
Test conversation database migration for Task 1 implementation.

Tests the creation of conversation_sessions and conversation_rounds tables
as required by ADR-001.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.conversation import ConversationRound, ConversationSession


@pytest.mark.asyncio
@pytest.mark.integration
class TestConversationMigration:
    """Test conversation database migration."""

    async def test_conversation_sessions_table_exists(self, postgres_test_session: AsyncSession):
        """Test that conversation_sessions table exists with correct schema."""
        # Test table existence
        result = await postgres_test_session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'conversation_sessions'
                );
            """)
        )
        assert result.scalar() is True, "conversation_sessions table should exist"

        # Test required columns exist
        result = await postgres_test_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'conversation_sessions'
                ORDER BY column_name;
            """)
        )
        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}

        # Verify required columns according to ADR-001 specification
        required_columns = {
            "id": {"type": "uuid", "nullable": "NO"},
            "scope_type": {"type": "character varying", "nullable": "NO"},
            "scope_id": {"type": "text", "nullable": "NO"},
            "status": {"type": "character varying", "nullable": "NO"},
            "stage": {"type": "character varying", "nullable": "YES"},
            "state": {"type": "jsonb", "nullable": "YES"},
            "version": {"type": "integer", "nullable": "NO"},
            "created_at": {"type": "timestamp with time zone", "nullable": "NO"},
            "updated_at": {"type": "timestamp with time zone", "nullable": "NO"},
        }

        for col_name, expected in required_columns.items():
            assert col_name in columns, f"Column {col_name} should exist"
            actual = columns[col_name]
            assert actual["nullable"] == expected["nullable"], f"Column {col_name} nullable mismatch"

    async def test_conversation_rounds_table_exists(self, postgres_test_session: AsyncSession):
        """Test that conversation_rounds table exists with correct schema."""
        # Test table existence
        result = await postgres_test_session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'conversation_rounds'
                );
            """)
        )
        assert result.scalar() is True, "conversation_rounds table should exist"

        # Test required columns exist
        result = await postgres_test_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'conversation_rounds'
                ORDER BY column_name;
            """)
        )
        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}

        # Verify required columns according to ADR-001 specification
        required_columns = {
            "session_id": {"type": "uuid", "nullable": "NO"},
            "round_path": {"type": "character varying", "nullable": "NO"},
            "role": {"type": "character varying", "nullable": "NO"},
            "input": {"type": "jsonb", "nullable": "YES"},
            "output": {"type": "jsonb", "nullable": "YES"},
            "correlation_id": {"type": "character varying", "nullable": "YES"},
            "created_at": {"type": "timestamp with time zone", "nullable": "NO"},
        }

        for col_name, expected in required_columns.items():
            assert col_name in columns, f"Column {col_name} should exist"
            actual = columns[col_name]
            assert actual["nullable"] == expected["nullable"], f"Column {col_name} nullable mismatch"

    async def test_conversation_foreign_key_constraint(self, postgres_test_session: AsyncSession):
        """Test that conversation_rounds has foreign key to conversation_sessions."""
        result = await postgres_test_session.execute(
            text("""
                SELECT tc.constraint_name, tc.table_name, kcu.column_name, 
                       ccu.table_name AS foreign_table_name,
                       ccu.column_name AS foreign_column_name 
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name = 'conversation_rounds';
            """)
        )

        foreign_keys = list(result.fetchall())
        assert len(foreign_keys) > 0, "conversation_rounds should have foreign key constraints"

        # Verify foreign key to conversation_sessions
        session_fk = next(
            (
                fk
                for fk in foreign_keys
                if fk[1] == "conversation_rounds" and fk[2] == "session_id" and fk[3] == "conversation_sessions"
            ),
            None,
        )
        assert session_fk is not None, "conversation_rounds should reference conversation_sessions.id"

    async def test_conversation_unique_constraints(self, postgres_test_session: AsyncSession):
        """Test unique constraint on conversation_rounds (session_id, round_path)."""
        result = await postgres_test_session.execute(
            text("""
                SELECT tc.constraint_name, kcu.column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE (tc.constraint_type = 'UNIQUE' OR tc.constraint_type = 'PRIMARY KEY') 
                AND tc.table_name = 'conversation_rounds'
                ORDER BY kcu.ordinal_position;
            """)
        )

        unique_constraints = list(result.fetchall())
        # The primary key constraint provides uniqueness for (session_id, round_path)
        assert (
            len(unique_constraints) >= 2
        ), "conversation_rounds should have unique constraint on (session_id, round_path) via PRIMARY KEY"
        
        # Verify the primary key covers the required columns
        pk_columns = [c[1] for c in unique_constraints if c[0] == 'pk_conversation_rounds']
        assert 'session_id' in pk_columns, "Primary key should include session_id"
        assert 'round_path' in pk_columns, "Primary key should include round_path"

    async def test_conversation_indexes_exist(self, postgres_test_session: AsyncSession):
        """Test that required indexes exist for performance."""
        result = await postgres_test_session.execute(
            text("""
                SELECT indexname, tablename, indexdef 
                FROM pg_indexes 
                WHERE tablename IN ('conversation_sessions', 'conversation_rounds')
                AND schemaname = 'public'
                ORDER BY tablename, indexname;
            """)
        )

        indexes = list(result.fetchall())
        assert len(indexes) > 0, "Conversation tables should have indexes for performance"

        # Check for expected indexes based on ADR-001
        index_names = [idx[0] for idx in indexes]

        # Primary key indexes should exist (SQLAlchemy names them pk_<table_name>)
        assert any(
            "pk_conversation_sessions" in idx for idx in index_names
        ), "Primary key index on conversation_sessions should exist"
        assert any(
            "pk_conversation_rounds" in idx for idx in index_names
        ), "Primary key index on conversation_rounds should exist"
        
        # Performance indexes should exist
        expected_indexes = [
            'idx_conversation_sessions_scope',
            'idx_conversation_sessions_status',
            'idx_conversation_sessions_updated_at',
            'idx_conversation_sessions_scope_status',
            'idx_conversation_rounds_session_id',
            'idx_conversation_rounds_correlation_id',
            'idx_conversation_rounds_created_at',
            'idx_conversation_rounds_role'
        ]
        
        for expected_idx in expected_indexes:
            assert any(expected_idx in idx for idx in index_names), f"Index {expected_idx} should exist"

    async def test_conversation_model_crud_operations(self, postgres_test_session: AsyncSession):
        """Test basic CRUD operations with conversation models."""
        from uuid import uuid4

        # Test Create
        session_id = uuid4()
        session = ConversationSession(
            id=session_id,
            scope_type="GENESIS",
            scope_id=str(uuid4()),
            status="ACTIVE",
            stage="STAGE0",
            state={"test": "data"},
            version=1,
        )
        postgres_test_session.add(session)
        await postgres_test_session.flush()

        # Test Create Round
        round_obj = ConversationRound(
            session_id=session_id,
            round_path="1",
            role="user",
            input={"content": "test input"},
            correlation_id=str(uuid4()),
        )
        postgres_test_session.add(round_obj)
        await postgres_test_session.flush()

        # Test Read
        retrieved_session = await postgres_test_session.get(ConversationSession, session_id)
        assert retrieved_session is not None
        assert retrieved_session.scope_type == "GENESIS"
        assert retrieved_session.state["test"] == "data"

        # Test relationship
        await postgres_test_session.refresh(retrieved_session, ["rounds"])
        assert len(retrieved_session.rounds) == 1
        assert retrieved_session.rounds[0].round_path == "1"

        await postgres_test_session.rollback()  # Clean up
