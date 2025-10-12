"""Common event utilities.

This module provides:
- Event configuration and topic mapping
- Event type mapping and normalization

Note: Domain event envelope classes (DomainEventEnvelope, DomainEventBuilder, SystemMetadata)
have been moved to src.common.messaging.domain_envelope for better organization.
Please import directly from there.
"""

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
    # Mapping
    "extract_strategy_key_from_event_type",
    "is_generation_completed_event",
    "normalize_task_type",
]
