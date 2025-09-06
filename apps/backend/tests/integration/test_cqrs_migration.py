"""Integration tests for PostgreSQL CQRS tables schema.

Covers existence and key constraints/indexes for:
- command_inbox
- domain_events
- event_outbox
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
@pytest.mark.integration
class TestCQRSPostgresSchema:
    async def test_command_inbox_table_exists_and_constraints(self, postgres_test_session: AsyncSession):
        # Table exists
        result = await postgres_test_session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'command_inbox'
                );
                """
            )
        )
        assert result.scalar() is True, "command_inbox table should exist"

        # Columns + nullability (types vary: focus on presence/nullability)
        result = await postgres_test_session.execute(
            text(
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'command_inbox'
                """
            )
        )
        cols = {row[0]: row[1] for row in result.fetchall()}

        required_not_null = {
            "id",
            "session_id",
            "command_type",
            "idempotency_key",
            "status",
            "retry_count",
            "created_at",
            "updated_at",
        }
        for c in required_not_null:
            assert c in cols, f"command_inbox column missing: {c}"
            assert cols[c] == "NO", f"{c} should be NOT NULL"

        # Optional columns that can be NULL
        for c in ["payload", "error_message"]:
            assert c in cols, f"command_inbox column missing: {c}"
            assert cols[c] == "YES", f"{c} should be NULLABLE"

        # Unique idempotency_key
        result = await postgres_test_session.execute(
            text(
                """
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'command_inbox'
                  AND tc.constraint_type = 'UNIQUE'
                  AND kcu.column_name = 'idempotency_key';
                """
            )
        )
        assert result.fetchone() is not None, "idempotency_key should have UNIQUE constraint"

    async def test_domain_events_table_exists_and_constraints(self, postgres_test_session: AsyncSession):
        # Table exists
        result = await postgres_test_session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'domain_events'
                );
                """
            )
        )
        assert result.scalar() is True, "domain_events table should exist"

        # Columns + nullability
        result = await postgres_test_session.execute(
            text(
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'domain_events'
                """
            )
        )
        cols = {row[0]: row[1] for row in result.fetchall()}

        required_not_null = {
            "id",
            "event_id",
            "event_type",
            "event_version",
            "aggregate_type",
            "aggregate_id",
            "created_at",
        }
        for c in required_not_null:
            assert c in cols, f"domain_events column missing: {c}"
            assert cols[c] == "NO", f"{c} should be NOT NULL"

        # Optional columns
        for c in ["correlation_id", "causation_id", "payload", "metadata"]:
            assert c in cols, f"domain_events column missing: {c}"
            assert cols[c] == "YES", f"{c} should be NULLABLE"

        # Unique on event_id
        result = await postgres_test_session.execute(
            text(
                """
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = 'domain_events'
                  AND tc.constraint_type = 'UNIQUE'
                  AND kcu.column_name = 'event_id';
                """
            )
        )
        assert result.fetchone() is not None, "event_id should have UNIQUE constraint"

        # Expected indexes presence (names may vary by alembic; check a subset)
        result = await postgres_test_session.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = 'domain_events';
                """
            )
        )
        index_names = {row[0] for row in result.fetchall()}
        expected_any = {
            "idx_domain_events_aggregate",
            "idx_domain_events_event_type",
            "idx_domain_events_created_at",
        }
        assert expected_any & index_names, "domain_events should have expected indexes"

    async def test_event_outbox_table_exists_and_indexes(self, postgres_test_session: AsyncSession):
        # Table exists
        result = await postgres_test_session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'event_outbox'
                );
                """
            )
        )
        assert result.scalar() is True, "event_outbox table should exist"

        # Columns + nullability
        result = await postgres_test_session.execute(
            text(
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'event_outbox'
                """
            )
        )
        cols = {row[0]: row[1] for row in result.fetchall()}

        required_not_null = {
            "id",
            "topic",
            "payload",
            "status",
            "retry_count",
            "max_retries",
            "created_at",
        }
        for c in required_not_null:
            assert c in cols, f"event_outbox column missing: {c}"
            assert cols[c] == "NO", f"{c} should be NOT NULL"

        # Expected indexes presence (subset)
        result = await postgres_test_session.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = 'event_outbox';
                """
            )
        )
        index_names = {row[0] for row in result.fetchall()}
        expected = {
            "idx_event_outbox_status",
            "idx_event_outbox_topic",
            "idx_event_outbox_created_at",
        }
        assert expected.issubset(index_names), "event_outbox should have core indexes"
