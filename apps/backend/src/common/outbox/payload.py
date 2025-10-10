"""Utilities for constructing Outbox payload envelopes with a consistent schema."""

from __future__ import annotations

import contextlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.event import DomainEvent


class SystemMetadata(BaseModel):
    """Canonical system-level metadata stored alongside each Outbox payload."""

    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None
    created_at: str | None = None
    event_version: int | None = None

    model_config = ConfigDict(extra="forbid")


class OutboxPayloadEnvelope(BaseModel):
    """Structured Outbox payload envelope."""

    system: SystemMetadata
    data: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "v1"

    model_config = ConfigDict(extra="forbid")


class OutboxPayloadBuilder:
    """Builder that enforces separation between system metadata and business payload."""

    RESERVED_TOP_LEVEL_FIELDS = {"system", "data", "schema_version"}

    def __init__(self) -> None:
        self._system_metadata: dict[str, Any] = {}
        self._business_data: dict[str, Any] = {}
        self._schema_version: str = "v1"

    def with_domain_event(self, event: DomainEvent) -> OutboxPayloadBuilder:
        """Populate system metadata from a SQLAlchemy DomainEvent instance."""
        raw_metadata = event.event_metadata or {}
        if isinstance(raw_metadata, dict):
            cleaned_metadata = {k: v for k, v in raw_metadata.items() if v is not None}
        else:
            cleaned_metadata = {}

        nested = cleaned_metadata.get("metadata")
        if isinstance(nested, dict) and not nested:
            cleaned_metadata.pop("metadata")

        self._system_metadata = {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "metadata": cleaned_metadata,
        }

        if getattr(event, "correlation_id", None):
            self._system_metadata["correlation_id"] = str(event.correlation_id)
        if getattr(event, "causation_id", None):
            self._system_metadata["causation_id"] = str(event.causation_id)
        if getattr(event, "created_at", None):
            with contextlib.suppress(Exception):
                self._system_metadata["created_at"] = event.created_at.isoformat()  # type: ignore[attr-defined]
        if getattr(event, "event_version", None) is not None:
            self._system_metadata["event_version"] = event.event_version

        return self

    def with_business_data(self, data: dict[str, Any]) -> OutboxPayloadBuilder:
        """Attach business payload data after validating reserved keys."""
        if not data:
            return self

        conflicts = set(data.keys()) & self.RESERVED_TOP_LEVEL_FIELDS
        if conflicts:
            raise ValueError(
                f"Business data contains reserved top-level fields: {conflicts}. "
                "These fields conflict with the envelope structure."
            )

        self._business_data = data
        return self

    def with_schema_version(self, version: str) -> OutboxPayloadBuilder:
        """Override schema version for gradual migrations."""
        self._schema_version = version
        return self

    def build(self) -> OutboxPayloadEnvelope:
        """Create the final OutboxPayloadEnvelope instance."""
        required_fields = ["event_id", "event_type", "aggregate_type", "aggregate_id"]
        missing = [field for field in required_fields if field not in self._system_metadata]
        if missing:
            raise ValueError(f"Missing required system metadata fields: {missing}")

        return OutboxPayloadEnvelope(
            system=SystemMetadata(**self._system_metadata),
            data=self._business_data,
            schema_version=self._schema_version,
        )

    @classmethod
    def from_domain_event(cls, domain_event: DomainEvent) -> OutboxPayloadBuilder:
        """Convenience constructor that seeds builder from a domain event."""
        return cls().with_domain_event(domain_event).with_business_data(domain_event.payload or {})
