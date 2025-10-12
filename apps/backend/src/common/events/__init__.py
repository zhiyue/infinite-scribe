"""Common event utilities and domain event envelope.

This module provides:
- Event configuration and topic mapping
- Domain event envelope for Event Sourcing and CQRS
- Event builders for constructing standardized event messages

Note: Domain event envelope classes have been moved to src.common.messaging.domain_envelope
for better organization alongside capability event envelopes.
"""

# Re-export from new location for backward compatibility
from src.common.messaging.domain_envelope import DomainEventBuilder, DomainEventEnvelope, SystemMetadata

from .config import (
    build_event_type,
    get_aggregate_type,
    get_domain_topic,
    infer_scope_from_topic,
)
from .mapping import (
    extract_strategy_key_from_event_type,
    is_generation_completed_event,
    normalize_task_type,
)

__all__ = [
    # Configuration
    "build_event_type",
    "get_aggregate_type",
    "get_domain_topic",
    "infer_scope_from_topic",
    # Domain Event Envelope
    "DomainEventBuilder",
    "DomainEventEnvelope",
    "SystemMetadata",
    # Mapping
    "extract_strategy_key_from_event_type",
    "is_generation_completed_event",
    "normalize_task_type",
]
