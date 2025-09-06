"""Agents test configuration - override event loop to be function scoped."""

import asyncio

import pytest


@pytest.fixture(scope="function")
def event_loop():
    """Create a fresh event loop for each agent test function.

    This overrides the session-scoped event_loop fixture to ensure
    that each async test in the agents module gets a clean event loop,
    preventing event loop contamination between tests.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        try:
            # Cancel any remaining tasks
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                # Wait for all tasks to be cancelled
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()
