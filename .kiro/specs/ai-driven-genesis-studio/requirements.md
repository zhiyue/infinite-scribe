# Requirements Document

## Introduction

The AI-Driven Genesis Studio is a comprehensive system that enables users to create novel initial settings through an AI-supervised, iterative feedback process. The system must implement a dual-entry mode supporting both command-driven and event-driven architectures, utilizing Prefect's pause/resume mechanisms for non-blocking workflow management. This feature represents a complete end-to-end solution from database design to user interface, ensuring reliable, scalable, and user-friendly novel creation workflows.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want a robust data foundation with event sourcing capabilities, so that the system can maintain data consistency, support idempotency, and provide reliable event publishing.

#### Acceptance Criteria

1. WHEN database migration scripts are executed THEN PostgreSQL database SHALL successfully create six core tables: `domain_events`, `command_inbox`, `async_tasks`, `event_outbox`, `flow_resume_handles`, and `genesis_sessions`
2. WHEN the `command_inbox` table is created THEN it SHALL include a unique constraint index on `(session_id, command_type)` where `status IN ('RECEIVED', 'PROCESSING')`
3. WHEN the `flow_resume_handles` table is created THEN it SHALL include a unique constraint index on `correlation_id` where `status = 'WAITING'`
4. WHEN a shared types package is created at `packages/shared-types` THEN it SHALL contain Pydantic models corresponding to all table structures with correct type annotations

### Requirement 2

**User Story:** As a frontend developer, I want command-based API endpoints with atomic event publishing, so that I can interact with the backend reliably using a unified approach.

#### Acceptance Criteria

1. WHEN the API gateway receives a `POST /.../commands` request THEN it SHALL route to different processing logic based on the `command_type` in the request body
2. WHEN the API processes a command THEN write operations to `command_inbox`, `domain_events`, and `event_outbox` tables SHALL be completed within a single database transaction
3. WHEN a duplicate, incomplete command is submitted THEN the API SHALL utilize the `command_inbox` unique constraint and return a `409 Conflict` status code
4. WHEN a separate `Message Relay` service detects `PENDING` status records in `event_outbox` THEN it SHALL poll the records, publish them to Kafka, and update the record status to `SENT` upon success

### Requirement 3

**User Story:** As a system, I want Prefect workflows to pause when waiting for external events and resume upon receiving callbacks, so that I can implement non-blocking, event-driven complex business processes with efficient resource utilization.

#### Acceptance Criteria

1. WHEN a Prefect Flow reaches a `wait_for_user_input` task THEN it SHALL successfully create a persistent callback record in the `flow_resume_handles` table with status `PENDING_PAUSE`
2. WHEN the wait task executes THEN it SHALL successfully request Prefect API to set its status to `PAUSED`
3. WHEN Prefect confirms the task is paused THEN a status hook SHALL be triggered to update the corresponding record in `flow_resume_handles` table to status `PAUSED`
4. WHEN an independent `PrefectCallbackService` listens to a result event containing `correlation_id` THEN it SHALL find the corresponding callback handle from `flow_resume_handles` table or Redis cache using the `correlation_id`
5. WHEN the callback service finds the handle THEN it SHALL successfully call Prefect API to resume the paused task and inject result data
6. WHEN a race condition occurs (resume signal arrives before pause signal) THEN the system SHALL correctly handle this situation through the status and `resume_payload` fields in `flow_resume_handles` table, ensuring the workflow is eventually resumed successfully

### Requirement 4

**User Story:** As a supervisor, I want a UI interface that seamlessly collaborates with the command and event-based backend, so that I can experience a smooth, real-time genesis process where state is never lost.

#### Acceptance Criteria

1. WHEN a user performs any action in the UI that triggers backend operations (such as "Give me inspiration!") THEN the frontend SHALL send a command with correct `command_type` and `payload` to the `POST /.../commands` endpoint
2. WHEN a user refreshes the Genesis Studio page THEN the UI SHALL call the `GET /.../state` interface and accurately restore to the interface state before the user left (including disabling interactive elements) based on the returned `current_stage` and `is_pending` flags
3. WHEN the UI is loaded THEN it SHALL establish a persistent SSE connection with the backend's `/events/stream` endpoint
4. WHEN the backend has any progress or status updates THEN the UI SHALL receive them in real-time through SSE and update progress bars, status badges, or display new content accordingly, without requiring manual user refresh
5. WHEN a user completes all stages from "concept selection" to "plot outline" and finally clicks "Complete Genesis" THEN the UI SHALL correctly handle the synchronous success response of the `FINISH_GENESIS` command and automatically navigate to the project details page of the newly created novel

### Requirement 5

**User Story:** As a user, I want to experience different genesis creation modes, so that I can choose the approach that best fits my creative process.

#### Acceptance Criteria

1. WHEN a user accesses the Genesis Studio THEN the system SHALL provide dual-entry modes: guided step-by-step creation and free-form creation
2. WHEN a user selects guided mode THEN the system SHALL present sequential stages: concept inspiration, theme selection, character development, world building, and plot outline
3. WHEN a user selects free-form mode THEN the system SHALL allow jumping between different creation aspects without enforcing a specific order
4. WHEN AI generates content in any mode THEN the user SHALL be able to provide feedback, request modifications, or accept the generated content
5. WHEN a user provides feedback THEN the system SHALL use that feedback to refine subsequent AI generations within the same session

### Requirement 6

**User Story:** As a system, I want to maintain session state and handle interruptions gracefully, so that users can resume their creative process from where they left off.

#### Acceptance Criteria

1. WHEN a user starts a genesis session THEN the system SHALL create a unique session identifier and persist all session data
2. WHEN a user's session is interrupted (browser close, network issues) THEN the system SHALL maintain the session state in the database
3. WHEN a user returns to continue their session THEN the system SHALL restore the exact state including current stage, generated content, and user feedback history
4. WHEN a session exceeds the maximum allowed duration THEN the system SHALL provide warnings and allow session extension or graceful completion
5. WHEN multiple users attempt to access the same session THEN the system SHALL handle concurrent access appropriately with proper locking mechanisms