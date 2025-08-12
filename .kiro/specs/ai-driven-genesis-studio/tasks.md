# Implementation Plan

- [x] 1. Set up database schema and types foundation
  - Create database migration scripts for all six core tables with proper constraints and indexes
  - Implement Pydantic models in backend/src/models corresponding to all table structures
  - Write database migration verification scripts to ensure schema correctness
  - using alembic
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [-] 2. Implement core data models and domain events
- [x] 2.1 Create enhanced domain event models and enums
  - Extend existing event.py model to support new event types for genesis workflow
  - Create comprehensive enums for GenesisStage, GenesisStatus, CommandStatus in shared types
  - Implement event serialization and deserialization utilities
  - _Requirements: 1.1, 1.4_

- [ ] 2.2 Implement command inbox and outbox models
  - Create CommandInbox SQLAlchemy model with unique constraints for idempotency
  - Create EventOutbox SQLAlchemy model for transactional event publishing
  - Implement FlowResumeHandle model for Prefect pause/resume functionality
  - _Requirements: 1.1, 1.2, 2.2_

- [ ] 2.3 Create async tasks tracking model
  - Implement AsyncTask SQLAlchemy model for background task management
  - Add task status tracking and retry logic support
  - Create task result storage and error handling mechanisms
  - _Requirements: 1.1, 3.1_

- [ ] 3. Build command processing infrastructure
- [ ] 3.1 Implement command handler base classes and interfaces
  - Create abstract CommandHandler base class with validation and processing methods
  - Implement CommandRouter for routing commands based on command_type
  - Create command validation framework with proper error handling
  - _Requirements: 2.1, 2.2_

- [ ] 3.2 Create transactional command processing service
  - Implement service that handles command_inbox, domain_events, and event_outbox in single transaction
  - Add idempotency checking using command_inbox unique constraints
  - Implement proper error handling and rollback mechanisms
  - _Requirements: 2.2, 2.3_

- [ ] 3.3 Implement specific genesis command handlers
  - Create StartGenesisCommandHandler for initializing new genesis sessions
  - Implement SelectConceptCommandHandler for concept selection processing
  - Create GenerateInspirationCommandHandler for AI content generation
  - Implement ConfirmStageCommandHandler for stage progression
  - _Requirements: 2.1, 4.1, 5.1, 5.4_

- [ ] 4. Create message relay service for event publishing
- [ ] 4.1 Implement event outbox polling service
  - Create MessageRelayService that polls event_outbox table for PENDING events
  - Implement Kafka publishing logic with proper error handling
  - Add retry mechanism with exponential backoff for failed publications
  - _Requirements: 2.4_

- [ ] 4.2 Add event outbox status management
  - Implement status updates from PENDING to SENT after successful Kafka publishing
  - Create dead letter queue handling for events that exceed max retries
  - Add monitoring and alerting for failed event publications
  - _Requirements: 2.4_

- [ ] 5. Build Prefect workflow integration
- [ ] 5.1 Create core genesis workflow structure
  - Implement main genesis_workflow Prefect flow with guided and free-form modes
  - Create individual stage tasks for concept, theme, character, world, and plot development
  - Implement workflow state management and progression logic
  - _Requirements: 3.1, 5.2, 5.3_

- [ ] 5.2 Implement pause/resume mechanism
  - Create wait_for_user_input task that creates flow_resume_handles records
  - Implement Prefect API integration for requesting task pause status
  - Create status hooks to update flow_resume_handles when pause is confirmed
  - _Requirements: 3.2, 3.3, 3.4_

- [ ] 5.3 Build Prefect callback service
  - Implement PrefectCallbackService for handling user response events
  - Create correlation_id lookup logic for finding resume handles
  - Implement Prefect API calls to resume paused tasks with result data injection
  - Add race condition handling for resume signals arriving before pause signals
  - _Requirements: 3.5, 3.6, 3.7_

- [ ] 6. Create API endpoints for command and query operations
- [ ] 6.1 Implement unified command API endpoint
  - Create POST /genesis/commands endpoint with command routing logic
  - Implement request validation and command_type-based handler dispatch
  - Add proper HTTP status code handling including 409 Conflict for duplicate commands
  - _Requirements: 2.1, 2.3_

- [ ] 6.2 Build genesis state query API
  - Create GET /genesis/{session_id}/state endpoint for current state retrieval
  - Implement state reconstruction from genesis_sessions and domain_events
  - Add current_stage and is_pending flag calculation logic
  - _Requirements: 4.2, 6.3_

- [ ] 6.3 Create Server-Sent Events streaming endpoint
  - Implement GET /genesis/{session_id}/events/stream SSE endpoint
  - Create real-time event filtering and streaming logic
  - Add connection management and graceful disconnection handling
  - _Requirements: 4.3, 4.4_

- [ ] 7. Build frontend UI components and integration
- [ ] 7.1 Create genesis studio main interface
  - Implement React components for guided and free-form creation modes
  - Create stage navigation and progress tracking UI elements
  - Add AI content display and user feedback collection interfaces
  - _Requirements: 4.1, 5.1, 5.2_

- [ ] 7.2 Implement real-time UI updates via SSE
  - Create SSE client connection management in React
  - Implement real-time progress bar and status badge updates
  - Add dynamic content updates without manual refresh requirements
  - _Requirements: 4.3, 4.4_

- [ ] 7.3 Add session state restoration functionality
  - Implement page refresh handling with state API calls
  - Create UI state reconstruction based on current_stage and is_pending flags
  - Add proper interactive element enabling/disabling based on session state
  - _Requirements: 4.2, 6.3_

- [ ] 8. Implement session management and persistence
- [ ] 8.1 Create genesis session lifecycle management
  - Implement session creation with unique identifier generation
  - Add session data persistence across all workflow stages
  - Create session expiration and cleanup mechanisms
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 8.2 Build session interruption and recovery handling
  - Implement graceful session state preservation during interruptions
  - Create session restoration logic for returning users
  - Add concurrent access handling with optimistic locking using version field
  - _Requirements: 6.3, 6.5_

- [ ] 9. Add comprehensive error handling and monitoring
- [ ] 9.1 Implement command processing error handling
  - Create validation error responses with detailed error messages
  - Add workflow error capture in async_tasks table with retry logic
  - Implement timeout handling with user notifications
  - _Requirements: 2.3, 3.1, 3.7_

- [ ] 9.2 Create event processing error management
  - Implement exponential backoff retry for outbox publishing failures
  - Add dead letter queue for events exceeding max retries
  - Create callback timeout cleanup for stale resume handles
  - _Requirements: 2.4, 3.5, 3.7_

- [ ] 10. Build testing infrastructure and test suites
- [ ] 10.1 Create unit tests for core components
  - Write comprehensive tests for all command handlers with various input scenarios
  - Implement event handler tests verifying processing and side effects
  - Create Prefect task tests in isolation with mocked dependencies
  - _Requirements: All requirements - validation_

- [ ] 10.2 Implement integration tests for system interactions
  - Create database transaction tests verifying ACID properties across tables
  - Implement event publishing tests for outbox pattern reliability
  - Add Prefect integration tests for pause/resume mechanisms
  - Write API endpoint tests for complete request/response cycles
  - _Requirements: All requirements - integration validation_

- [ ] 11. Complete system integration and finalization
- [ ] 11.1 Implement end-to-end workflow testing
  - Create complete guided mode genesis workflow tests
  - Implement free-form mode creation process tests
  - Add interruption recovery tests for session restoration
  - Test real-time SSE event streaming functionality
  - _Requirements: All requirements - end-to-end validation_

- [ ] 11.2 Finalize novel creation and navigation
  - Implement FINISH_GENESIS command handler for novel creation
  - Create automatic navigation to project details page after completion
  - Add proper cleanup of completed genesis sessions
  - Implement novel-genesis session relationship management
  - _Requirements: 4.5, 6.1_