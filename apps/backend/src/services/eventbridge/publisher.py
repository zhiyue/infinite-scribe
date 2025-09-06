"""
Publisher for transforming domain events and publishing to SSE channels.

This module implements the Publisher component that transforms Kafka domain events
into SSE messages and routes them to users via RedisSSEService.
"""

from typing import Any

from src.core.logging import get_logger
from src.schemas.sse import EventScope, SSEMessage
from src.services.sse.redis_client import RedisSSEService

logger = get_logger(__name__)


class Publisher:
    """
    Publisher for transforming and routing domain events to SSE channels.

    Responsibilities:
    - Transform Kafka envelope to SSEMessage format
    - Extract user_id for routing
    - Create minimal data set for efficient transmission
    - Handle publishing errors gracefully
    - Preserve correlation and trace IDs for observability
    """

    def __init__(self, redis_sse_service: RedisSSEService):
        """
        Initialize Publisher with RedisSSEService dependency.

        Args:
            redis_sse_service: Service for publishing SSE messages to Redis
        """
        self.redis_sse_service = redis_sse_service

    async def publish(self, envelope: dict[str, Any]) -> str:
        """
        Transform envelope to SSEMessage and publish to user channel.

        Args:
            envelope: Domain event envelope from Kafka

        Returns:
            Stream ID from Redis publish operation

        Raises:
            ValueError: If required fields are missing
            Exception: If Redis publishing fails
        """
        try:
            # Extract user_id for routing
            user_id = self._extract_user_id(envelope)

            # Transform envelope to SSE message
            sse_message = self._transform_to_sse_message(envelope)

            # Publish to Redis SSE service
            stream_id = await self.redis_sse_service.publish_event(user_id, sse_message)

            logger.debug(f"Published event {envelope.get('event_type')} to user {user_id}, " f"stream_id: {stream_id}")

            return stream_id

        except Exception as e:
            logger.error(
                f"Failed to publish event {envelope.get('event_type', 'unknown')}: {e}",
                extra={
                    "event_id": envelope.get("event_id"),
                    "correlation_id": envelope.get("correlation_id"),
                    "user_id": envelope.get("payload", {}).get("user_id"),
                },
            )
            raise

    def _extract_user_id(self, envelope: dict[str, Any]) -> str:
        """
        Extract user_id from envelope payload for routing.

        Args:
            envelope: Domain event envelope

        Returns:
            User ID for routing

        Raises:
            ValueError: If user_id is missing
        """
        payload = envelope.get("payload", {})
        user_id = payload.get("user_id")

        if not user_id:
            raise ValueError(
                f"user_id is required in payload for event routing, " f"event_id: {envelope.get('event_id')}"
            )

        return user_id

    def _transform_to_sse_message(self, envelope: dict[str, Any]) -> SSEMessage:
        """
        Transform Kafka envelope to SSEMessage with minimal data set.

        Args:
            envelope: Domain event envelope

        Returns:
            SSEMessage formatted for SSE transmission
        """
        # Create minimal data set for efficient transmission
        minimal_data = self._create_minimal_data_set(envelope)

        return SSEMessage(
            event=envelope["event_type"],
            data=minimal_data,
            id=None,  # Will be set by Redis Streams
            scope=EventScope.USER,
            version="1.0",
        )

    def _create_minimal_data_set(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """
        Create minimal data set for SSE transmission.

        Includes only essential fields to minimize transmission size
        while preserving necessary information for UI updates.

        Args:
            envelope: Domain event envelope

        Returns:
            Minimal data dictionary
        """
        payload = envelope.get("payload", {})
        metadata = envelope.get("metadata", {})

        # Start with required fields
        minimal_data = {
            "event_id": envelope.get("event_id"),
            "event_type": envelope.get("event_type"),
            "session_id": payload.get("session_id"),
            "correlation_id": envelope.get("correlation_id"),
            "timestamp": payload.get("timestamp"),
        }

        # Add optional but recommended fields if present
        if payload.get("novel_id"):
            minimal_data["novel_id"] = payload["novel_id"]

        if metadata.get("trace_id"):
            minimal_data["trace_id"] = metadata["trace_id"]

        # Include payload content, but may be summarized in future
        if "content" in payload:
            minimal_data["payload"] = payload["content"]
        elif payload:
            # If no specific content field, include relevant payload data
            # Exclude internal fields that shouldn't be in SSE
            filtered_payload = {
                k: v
                for k, v in payload.items()
                if k not in ["user_id", "session_id", "timestamp", "novel_id"] and not k.startswith("internal_")
            }
            if filtered_payload:
                minimal_data["payload"] = filtered_payload

        return minimal_data
