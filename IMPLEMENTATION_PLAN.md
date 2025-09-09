## Stage 1: Baseline Review & Goals

Goal: Understand current conversation services and align with Novel Genesis stage docs. Success Criteria: Identify API surface gaps vs tests and .tasks/novel-genesis-stage design; list minimal compatibility shims. Tests: Dry-run unit suite on conversation services to observe failures and categorize (contract vs logic). Status: Complete

## Stage 2: Event Handler Compatibility

Goal: Restore high-level helpers on `ConversationEventHandler` while keeping newer low-level API. Success Criteria: Provide `create_round_events`, `ensure_command_events`, `create_command_events`, and `_compute_next_round_path` without breaking existing internal usage. Tests: Unit tests expecting these methods can be adapted to new semantics. Status: In Progress

## Stage 3: Round Service Utilities

Goal: Add back-compat utility functions on `ConversationRoundService` (`_compute_next_round_path`, `_parse_correlation_uuid`). Success Criteria: Helpers exist and behave as expected; no behavior change to public API. Tests: Direct unit tests on utilities. Status: Complete

## Stage 4: Access Control Flexibility

Goal: Make `verify_session_access` accept both session id and session object to support older call sites/tests. Success Criteria: Method handles `UUID | ConversationSession`. Tests: Unit tests stubbing verify calls with session instances. Status: Complete

## Stage 5: Command Service Integration

Goal: Prefer `ConversationEventHandler` to create/ensure command artifacts (outbox + domain events), with fallback to atomic helper preserved. Success Criteria: `ConversationCommandService` accepts `event_handler` and uses it by default via facade. Tests: Conversation command unit tests aligned. Status: In Progress

## Notes

- The repository’s existing unit tests for conversation services are partially out of sync with the current refactor (facade + specialized services). This plan introduces compatibility helpers to ease migration and reduce churn.
- Follow-up: Update unit tests to remove direct assertions on internal collaborators not injected (e.g., event handler mocks) and target the public behavior via the facade and service boundaries.

