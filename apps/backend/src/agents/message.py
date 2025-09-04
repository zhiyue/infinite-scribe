"""Message envelope models and helpers for agents.

Provides a unified Envelope schema with encode/decode helpers so that
agents can produce/consume messages with strong typing and versioning.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Tuple

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    """Standard message envelope for inter-agent communication."""

    id: str = Field(description="Unique message identifier (UUID)")
    ts: datetime = Field(description="Event timestamp in UTC")
    type: str = Field(description="Business event type")
    version: str = Field(default="v1", description="Envelope version")
    agent: str | None = Field(default=None, description="Producing agent name")
    correlation_id: str | None = Field(default=None, description="Correlation id for tracing")
    retries: int | None = Field(default=None, description="Number of retries before success")
    status: str | None = Field(default=None, description="Business status: ok/error")
    data: dict[str, Any] = Field(default_factory=dict, description="Payload data")

    @property
    def message_id(self) -> str:
        return self.id


def encode_message(agent: str, result: dict[str, Any], *, correlation_id: str | None, retries: int) -> dict[str, Any]:
    """Encode an outgoing business result dict into an Envelope dict.

    The `result` should include at least a `type` field. Reserved routing keys
    like `_topic` and `_key` should be stripped by the caller.
    """
    from uuid import uuid4

    event_type = str(result.get("type", "unknown"))
    # Copy to avoid mutating input
    data = {k: v for k, v in result.items() if k not in {"type"}}

    env = Envelope(
        id=str(uuid4()),
        ts=datetime.now(UTC),
        type=event_type,
        version="v1",
        agent=agent,
        correlation_id=correlation_id,
        retries=retries,
        status="ok",
        data=data,
    )
    return env.model_dump()


def decode_message(value: dict[str, Any]) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Decode incoming dict into (payload, meta) tuple.

    If the dict already conforms to Envelope, returns (env.data, meta),
    otherwise treats entire dict as payload and builds minimal meta.
    """
    if {"id", "ts", "type", "data"}.issubset(value.keys()):
        env = Envelope.model_validate(value)
        payload = env.data
        meta = {
            "id": env.id,
            "message_id": env.message_id,
            "type": env.type,
            "version": env.version,
            "correlation_id": env.correlation_id,
            "agent": env.agent,
            "retries": env.retries,
            "status": env.status,
        }
        return payload, meta

    # Non-envelope payload
    payload = value if isinstance(value, dict) else {}
    meta = {
        "id": None,
        "message_id": None,
        "type": payload.get("type"),
        "version": None,
        "correlation_id": payload.get("correlation_id"),
        "agent": payload.get("agent"),
        "retries": payload.get("retries"),
        "status": payload.get("status"),
    }
    return payload, meta

