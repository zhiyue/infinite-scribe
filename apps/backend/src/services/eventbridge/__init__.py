"""
EventBridge service package.

This package implements the EventBridge service for bridging domain events
from Kafka to SSE channels via Redis.

Architecture:
    Kafka Domain Events → EventFilter → CircuitBreaker → Publisher → Redis SSE

Components:
    - EventFilter: Validates and filters Genesis.Session.* events
    - CircuitBreaker: Handles Redis failures with consumer pause/resume
    - Publisher: Transforms events to SSE format and publishes to Redis
    - DomainEventBridgeService: Main service coordinating all components
    - Factory: Dependency injection and service creation
    - Configuration: Environment-based configuration management

Usage:
    # Create and start the service
    from src.services.eventbridge.main import main
    import asyncio

    asyncio.run(main())

    # Or using the factory directly
    from src.services.eventbridge.factory import create_event_bridge_service

    service = create_event_bridge_service()
    # ... use service
"""

from src.services.eventbridge.bridge import DomainEventBridgeService
from src.services.eventbridge.circuit_breaker import CircuitBreaker, CircuitState
from src.services.eventbridge.factory import (
    EventBridgeServiceFactory,
    create_event_bridge_service,
    get_event_bridge_factory,
)
from src.services.eventbridge.filter import EventFilter
from src.services.eventbridge.publisher import Publisher

__all__ = [
    # Main service
    "DomainEventBridgeService",

    # Components
    "EventFilter",
    "CircuitBreaker",
    "CircuitState",
    "Publisher",

    # Factory
    "EventBridgeServiceFactory",
    "create_event_bridge_service",
    "get_event_bridge_factory",
]
