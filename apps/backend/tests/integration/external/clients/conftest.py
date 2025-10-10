"""Conftest for external client integration tests.

This conftest disables problematic autouse fixtures from the parent integration
test configuration that are not relevant for external client testing.
"""

import pytest


# Disable the autouse email service mocking fixture for external client tests
@pytest.fixture(autouse=True, scope="function")
def _mock_email_service_instance_methods():
    """Override the problematic email service fixture to be a no-op."""
    # This is a no-op fixture that overrides the autouse fixture from
    # tests/integration/fixtures/mocks.py to prevent it from interfering
    # with our external client tests
    yield


# Disable other potentially problematic fixtures
@pytest.fixture(autouse=True, scope="function")
def _mock_email_tasks_send_with_retry():
    """Override the email tasks fixture to be a no-op."""
    yield


@pytest.fixture(autouse=True, scope="function")
def _patch_outbox_relay_database_session():
    """Override the outbox relay fixture to be a no-op."""
    yield
