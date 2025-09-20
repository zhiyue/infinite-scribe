"""Outbox Relay Service (DB -> Kafka)

Placement rationale:
- This is not an Agent; it polls the database (event_outbox) and publishes to Kafka.
- Lives under services/outbox to follow ADR guidance.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from aiokafka import AIOKafkaProducer
from aiokafka.errors import UnknownTopicOrPartitionError
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from src.core.config import get_settings
from src.core.logging.config import configure_logging, get_logger
from src.db.sql.session import create_sql_session
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus

log = get_logger("outbox.relay")


class OutboxRelayService:
    """Relay service that publishes outbox events to Kafka."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._stop_event = asyncio.Event()
        self._producer: AIOKafkaProducer | None = None
        self._validate_settings()

    async def start(self) -> None:
        """Initialize resources (logging, Kafka producer)."""
        configure_logging(environment=self.settings.environment, level=self.settings.log_level)
        log.info(
            "relay_starting",
            kafka_bootstrap=self.settings.kafka_bootstrap_servers,
            poll_interval_s=self.settings.relay.poll_interval_seconds,
            batch_size=self.settings.relay.batch_size,
        )

        # Initialize database engine connection early to establish async context
        try:
            log.info("relay_initializing_database_context")

            # Force SQLAlchemy async greenlet context establishment
            from sqlalchemy import text

            # Force greenlet context by creating and using a connection in the current async context
            from src.db.sql.engine import get_engine

            engine = get_engine()

            # Establish greenlet context with a direct connection
            async with engine.begin() as conn:
                # Execute a simple query to establish greenlet context
                result = await conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                log.info("relay_greenlet_context_established", test_result=test_value)

            # Now test session-based operations
            async with create_sql_session() as test_session:
                # Use a simple query to test session connectivity
                result = await test_session.execute(text("SELECT 1 as session_test"))
                session_test = result.scalar()
                log.info("relay_database_context_ready", session_test=session_test)

        except Exception as e:
            log.error("relay_database_init_failed", error=str(e), error_type=type(e).__name__)
            raise

        # Initialize Kafka producer (we pre-encode bytes to avoid double serialization)
        log.info("relay_connecting_to_kafka", bootstrap_servers=self.settings.kafka_bootstrap_servers)
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            linger_ms=5,
        )
        await self._producer.start()
        log.info("relay_producer_ready", kafka_connected=True, producer_config={"acks": "all", "idempotent": True})

        # Ensure common topics exist to prevent immediate failures
        await self._ensure_common_topics_exist()

    async def stop(self) -> None:
        """Stop background tasks and close resources."""
        self._stop_event.set()
        if self._producer:
            try:
                await self._producer.stop()
            except Exception:
                log.warning("relay_producer_stop_failed", exc_info=True)
            self._producer = None
        log.info("relay_stopped")

    async def run_forever(self) -> None:
        """Main loop: poll -> publish -> sleep until stopped."""
        await self.start()
        cycle_count = 0
        heartbeat_interval = 12  # Log heartbeat every ~60s (12 cycles * 5s default interval)

        try:
            log.info("relay_main_loop_started", poll_interval_s=self.settings.relay.poll_interval_seconds)
            while not self._stop_event.is_set():
                try:
                    cycle_count += 1
                    processed = await self._drain_once()

                    # Log periodic heartbeat to show service is alive
                    if cycle_count % heartbeat_interval == 0:
                        log.info("relay_heartbeat", cycle=cycle_count, last_processed=processed)

                    if processed == 0:
                        # Log idle polling occasionally (every 6 cycles when idle)
                        if cycle_count % 6 == 0:
                            log.debug("relay_idle_poll", cycle=cycle_count)
                        # No work found; sleep full interval
                        await asyncio.wait_for(
                            self._stop_event.wait(), timeout=float(self.settings.relay.poll_interval_seconds)
                        )
                    else:
                        # Log when we processed events
                        log.info("relay_batch_processed", processed_count=processed, cycle=cycle_count)
                        # When we had work, yield briefly to next cycle
                        await asyncio.sleep(self.settings.relay.yield_sleep_ms / 1000.0)
                except TimeoutError:
                    # Normal wakeup
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.error("relay_loop_error", cycle=cycle_count, exc_info=True)
                    # Small backoff on unexpected loop errors
                    await asyncio.sleep(self.settings.relay.loop_error_backoff_ms / 1000.0)
        finally:
            log.info("relay_main_loop_stopping", total_cycles=cycle_count)
            await self.stop()

    async def _drain_once(self) -> int:
        """Fetch candidate IDs and process rows in separate transactions."""
        candidate_ids: list[str] = []

        # Phase 1: read candidate IDs (no row locks kept)
        try:
            async with create_sql_session() as session:
                stmt = self._build_select_for_ids()
                res = await session.execute(stmt)
                candidate_ids = list(res.scalars().all())
                # Commit read-only tx (no-op) and close session
        except Exception as e:
            log.error("relay_select_candidates_failed", error=str(e), error_type=type(e).__name__)
            return 0

        if not candidate_ids:
            return 0

        # Phase 2: process each row in its own transaction with row-level lock
        processed = 0
        for oid in candidate_ids:
            try:
                async with create_sql_session() as session:
                    row = await self._lock_row(session, oid)
                    if row is None:
                        # Another worker may have taken it
                        continue
                    ok = await self._process_row(session, row)
                    # Commit per row regardless of ok to persist state transitions
                    log.info(
                        "relay_pre_commit",
                        row_id=str(getattr(row, "id", oid)),
                    )
                    await session.commit()
                    log.info(
                        "relay_post_commit",
                        row_id=str(getattr(row, "id", oid)),
                        committed=True,
                    )
                    processed += 1 if ok else 0
            except Exception as e:
                log.error("relay_process_row_failed", row_id=str(oid), error=str(e), error_type=type(e).__name__)
                # Continue with next row
                continue
        return processed

    async def _ensure_common_topics_exist(self) -> None:
        """Ensure common topics exist by triggering auto-creation.

        除固定的领域事件主题外，动态收集已配置 agents 的 consume/produce 主题，
        以及 EventBridge 配置的领域主题，尽量一次性触发 auto-creation，
        降低首次投递 UnknownTopicOrPartitionError 的概率。
        """
        common_topics: list[str] = [
            "genesis.session.events",
        ]

        # Merge in EventBridge configured domain topics
        try:
            eb_topics = list(self.settings.eventbridge.domain_topics or [])
            for t in eb_topics:
                if isinstance(t, str) and t:
                    common_topics.append(t)
        except Exception:
            pass

        # Merge in all agent consume/produce topics from centralized config
        try:
            from src.agents.agent_config import AGENT_TOPICS

            for cfg in (AGENT_TOPICS or {}).values():
                for t in (cfg.get("consume") or []):
                    if isinstance(t, str) and t:
                        common_topics.append(t)
                for t in (cfg.get("produce") or []):
                    if isinstance(t, str) and t:
                        common_topics.append(t)
        except Exception:
            # 兜底：如果配置导入失败，不影响主流程
            pass

        # De-duplicate
        topics = sorted({t for t in common_topics if isinstance(t, str) and t})

        if not self._producer:
            log.warning("relay_topic_check_skipped", reason="no_producer")
            return

        for topic in topics:
            try:
                # Request metadata for the topic - this will trigger auto-creation if enabled
                metadata = await self._producer.client.fetch_all_metadata()
                # Use partitions_for_topic to check if topic exists (recommended approach)
                if metadata.partitions_for_topic(topic) is not None:
                    log.info("relay_topic_ensured", topic=topic)
                else:
                    log.info("relay_topic_will_autocreate", topic=topic)
            except Exception as e:
                log.warning("relay_topic_check_failed", topic=topic, error=str(e))

    async def _send_with_topic_retry(
        self,
        producer: AIOKafkaProducer,
        topic: str,
        value: bytes,
        key: bytes | None,
        headers: list[tuple[str, bytes]] | None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Send message with retry logic for topic auto-creation.

        Args:
            producer: Kafka producer instance
            topic: Topic name
            value: Message value (encoded)
            key: Message key (encoded)
            headers: Message headers
            max_retries: Maximum retry attempts for topic not found errors
            retry_delay: Delay between retries in seconds
        """
        for attempt in range(max_retries + 1):
            try:
                await producer.send_and_wait(topic, value=value, key=key, headers=headers)
                return
            except UnknownTopicOrPartitionError:
                if attempt < max_retries:
                    log.info(
                        "relay_send_topic_not_found_retrying",
                        topic=topic,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    # Try to trigger topic creation by fetching metadata
                    try:
                        await producer.client.fetch_all_metadata()
                    except Exception:
                        pass  # Ignore metadata fetch errors
                    await asyncio.sleep(retry_delay)
                else:
                    log.error(
                        "relay_send_topic_not_found_final",
                        topic=topic,
                        max_retries=max_retries,
                    )
                    raise
            except Exception:
                # For other errors, don't retry - let the outer error handling deal with it
                raise

    def _build_select_for_ids(self) -> Select:
        now = func.now()
        stmt = (
            select(EventOutbox.id)
            .where(
                and_(
                    EventOutbox.status == OutboxStatus.PENDING,
                    or_(EventOutbox.scheduled_at.is_(None), EventOutbox.scheduled_at <= now),
                )
            )
            .order_by(EventOutbox.created_at.asc())
            .limit(self.settings.relay.batch_size)
        )
        return stmt

    async def _lock_row(self, session: AsyncSession, oid: Any) -> EventOutbox | None:
        """Lock a single row by id with SKIP LOCKED and revalidate eligibility."""
        now = func.now()
        stmt = (
            select(EventOutbox)
            .where(
                and_(
                    EventOutbox.id == oid,
                    EventOutbox.status == OutboxStatus.PENDING,
                    or_(EventOutbox.scheduled_at.is_(None), EventOutbox.scheduled_at <= now),
                )
            )
            .with_for_update(skip_locked=True)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def _process_row(self, session: AsyncSession, row: EventOutbox) -> bool:
        """Attempt to publish row to Kafka and update row state."""
        topic = row.topic

        # Prevent work during shutdown
        if self._stop_event.is_set():
            # Reset to PENDING so it can be retried when service restarts
            row.status = OutboxStatus.PENDING
            session.add(row)
            return False

        # Producer may become unavailable during shutdown; snapshot local reference
        producer = self._producer
        if not producer:
            log.warning("relay_producer_unavailable", topic=topic)
            return False
        payload = row.payload
        key_value = row.key or row.partition_key

        headers_list: list[tuple[str, bytes]] | None = None
        if row.headers and isinstance(row.headers, dict):
            try:
                headers_list = [(str(k), str(v).encode("utf-8")) for k, v in row.headers.items()]
            except Exception as ex:
                log.warning("relay_header_encode_failed", error=str(ex))
                headers_list = None

        key_bytes: bytes | None = key_value.encode("utf-8") if isinstance(key_value, str) else None

        try:
            # Encode payload once; producer sends bytes
            encoded_value = json.dumps(payload).encode("utf-8")
            # Send and wait to ensure delivery before updating DB
            await self._send_with_topic_retry(producer, topic, encoded_value, key_bytes, headers_list)

            # Update status to SENT (DB-level update to ensure persistence)
            row.status = OutboxStatus.SENT
            row.sent_at = cast(Any, datetime.now(UTC))
            row.last_error = None
            session.add(row)
            row_id = str(getattr(row, "id", ""))
            await session.execute(
                update(EventOutbox)
                .where(EventOutbox.id == row.id)
                .values(status=OutboxStatus.SENT, sent_at=row.sent_at, last_error=None)
            )
            await session.flush()
            log.info(
                "relay_sent",
                topic=topic,
                key=key_value,
                new_status=OutboxStatus.SENT.value,
                row_id=row_id,
            )
            return True
        except Exception as e:
            # Schedule retry with exponential backoff
            row.retry_count = int(row.retry_count or 0) + 1
            row.last_error = str(e)

            base_ms = int(self.settings.relay.retry_backoff_ms)
            max_backoff = int(self.settings.relay.max_backoff_ms)
            attempt = max(1, int(row.retry_count))
            # Exponential backoff with cap and overflow guard
            try:
                exp = 2 ** max(0, attempt - 1)
            except OverflowError:
                exp = 2**16  # clamp exponent
            raw_delay = base_ms * exp
            delay_ms = raw_delay if raw_delay <= max_backoff else max_backoff
            # Honor per-row max_retries if set; otherwise fallback to default
            max_retries = int(row.max_retries or self.settings.relay.max_retries_default)

            if attempt >= max_retries:
                # Mark permanently failed
                row.status = OutboxStatus.FAILED
                row.scheduled_at = None
                # Add to session to track changes for commit
                session.add(row)
                log.error(
                    "relay_retry_exhausted",
                    topic=topic,
                    key=key_value,
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(e),
                )
                return False
            else:
                # Reschedule with backoff
                scheduled_delay = delay_ms / 1000.0
                row.scheduled_at = cast(Any, datetime.now(UTC) + timedelta(seconds=scheduled_delay))
                # Add to session to track changes for commit
                session.add(row)
                log.warning(
                    "relay_send_failed",
                    topic=topic,
                    key=key_value,
                    attempt=attempt,
                    next_retry_in_s=scheduled_delay,
                    error=str(e),
                )
                return False

    def _validate_settings(self) -> None:
        r = self.settings.relay
        # Basic bounds and positivity checks
        if r.batch_size <= 0:
            raise ValueError("relay.batch_size must be > 0")
        if r.poll_interval_seconds <= 0:
            raise ValueError("relay.poll_interval_seconds must be > 0")
        if r.retry_backoff_ms <= 0:
            raise ValueError("relay.retry_backoff_ms must be > 0")
        if r.max_retries_default < 0:
            raise ValueError("relay.max_retries_default must be >= 0")
        if r.yield_sleep_ms < 0 or r.loop_error_backoff_ms < 0:
            raise ValueError("relay sleep/backoff ms must be >= 0")
        if r.max_backoff_ms <= 0:
            raise ValueError("relay.max_backoff_ms must be > 0")
        if r.max_backoff_ms < r.retry_backoff_ms:
            log.warning("relay_max_backoff_lt_base", max_backoff_ms=r.max_backoff_ms, base_ms=r.retry_backoff_ms)


async def main() -> None:
    service = OutboxRelayService()
    try:
        await service.run_forever()
    except KeyboardInterrupt:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
