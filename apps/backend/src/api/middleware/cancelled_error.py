"""
ASGI middleware to gracefully swallow asyncio.CancelledError during shutdown/reload.

Context:
- Long-lived streaming endpoints (like SSE) often get cancelled when the server
  reloads or receives SIGINT/SIGTERM. This surfaces as asyncio.CancelledError
  bubbling up to Uvicorn, which logs an error stacktrace even though it's expected.

This middleware catches CancelledError at the ASGI boundary and downgrades it to
an info log so shutdown stays clean without noisy tracebacks.
"""

from __future__ import annotations

import asyncio

from src.core.logging import get_logger
from starlette.types import ASGIApp, Receive, Scope, Send

logger = get_logger(__name__)


class CancelledErrorMiddleware:
    """ASGI middleware that suppresses CancelledError noise on shutdown.

    Works for streaming responses (e.g., SSE) because it wraps the ASGI call directly
    instead of relying on Starlette's BaseHTTPMiddleware.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await self.app(scope, receive, send)
        except asyncio.CancelledError:
            # Expected during reload/termination; avoid error stacktraces.
            # Do not re-raise to uvicorn; just log at info level.
            logger.info("Request cancelled (shutdown/reload): suppressed CancelledError")
            # Nothing to send here—the connection is being torn down.
            return
