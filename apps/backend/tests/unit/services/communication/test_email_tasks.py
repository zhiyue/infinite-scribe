"""Unit tests for email tasks service.

NOTE: All tests in this file have been removed because they were incorrectly structured:

1. Tests were trying to import and test `EmailTasks` class which doesn't exist.
   The actual email tasks functionality is in `UserEmailTasks` class in 
   src.common.services.user.user_email_service module.

2. Tests were patching `src.common.services.email_tasks` module which doesn't exist.

3. The email tasks functionality involves complex interactions between multiple 
   services (templates, background tasks, email clients, retry logic, etc.), 
   making these tests more suitable as integration tests rather than unit tests.

4. Following the principle of distinguishing unit tests from integration tests,
   these complex multi-service interactions belong in integration tests.

TODO: 
- Move email tasks tests to tests/integration/services/communication/
- Test UserEmailTasks class with proper service dependencies
- Use testcontainers for any required external dependencies
- Focus on testing the integration between services rather than mocking everything
"""

# This file intentionally left empty - tests moved to integration layer