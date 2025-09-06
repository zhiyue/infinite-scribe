# EventBridge Implementation Plan

## Overview

Implementing EventBridge service to bridge domain events from Kafka to SSE channels via Redis, following TDD approach.

## Stage 1: EventFilter Component

**Goal**: Implement event filtering and validation with white-listing support
**Success Criteria**: 
- Filter validates Genesis.Session.* event types
- White-listing works for allowed event patterns
- Required fields validation (event_id, user_id, session_id, etc.)
- Proper error messages for invalid events

**Tests**: 
- test_event_filter_validates_genesis_events()
- test_event_filter_rejects_non_genesis_events()  
- test_event_filter_validates_required_fields()
- test_event_filter_white_list_patterns()

**Status**: Complete

## Stage 2: CircuitBreaker Component

**Goal**: Implement circuit breaker for Redis failures with configurable thresholds
**Success Criteria**:
- Circuit breaker tracks failure rate in 10s windows
- States: closed/open/half_open transitions work correctly  
- Consumer pause/resume integration
- Configurable thresholds and intervals

**Tests**:
- test_circuit_breaker_closed_state()
- test_circuit_breaker_opens_on_failure_threshold()
- test_circuit_breaker_half_open_recovery()
- test_circuit_breaker_consumer_pause_resume()

**Status**: Complete

## Stage 3: Publisher Component  

**Goal**: Transform Kafka envelope to SSEMessage and publish via RedisSSEService
**Success Criteria**:
- Envelope→SSEMessage transformation with data trimming
- Integration with existing RedisSSEService.publish_event
- User-based routing (user_id extraction)
- Error handling and metrics collection

**Tests**:
- test_publisher_transforms_envelope_to_sse_message()
- test_publisher_trims_data_for_minimal_set()
- test_publisher_routes_by_user_id()
- test_publisher_handles_redis_failures()

**Status**: Complete

## Stage 4: DomainEventBridgeService Main Service

**Goal**: Implement main event bridge service with Kafka consumption loop
**Success Criteria**:
- Kafka consumer integration with existing KafkaClientManager
- Event processing pipeline: consume→filter→publish→commit
- Graceful degradation when Redis fails
- Offset management with batch commits
- Circuit breaker integration

**Tests**:
- test_event_bridge_consumes_kafka_events()
- test_event_bridge_processes_valid_events()
- test_event_bridge_degrades_gracefully_on_redis_failure()
- test_event_bridge_commits_offsets_in_batches()
- Integration test with testcontainers

**Status**: Complete

## Stage 5: Configuration and Startup

**Goal**: Add configuration, metrics, and startup scripts
**Success Criteria**:
- Configuration via environment variables
- Prometheus metrics collection
- Service startup script and health checks
- Integration with existing pnpm scripts

**Tests**:
- test_configuration_loading()
- test_metrics_collection()
- test_service_startup_and_shutdown()

**Status**: Complete

## Implementation Notes

- Follow existing codebase patterns from agents/kafka_client.py and services/sse/
- Use testcontainers for integration tests (mandatory per CLAUDE.md)
- All tests must have timeouts to prevent hanging
- Focus on reusing existing infrastructure (KafkaClientManager, RedisSSEService, etc.)
- Implement proper error handling and logging throughout