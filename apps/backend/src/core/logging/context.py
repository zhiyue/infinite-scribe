"""Context binding functionality for structured logging"""

import contextvars
from typing import Any

import structlog

# Configuration constants
MAX_CONTEXT_SIZE = 50  # Maximum number of context entries to prevent memory leaks
PROTECTED_KEYS = {"request_id", "user_id", "trace_id", "service", "component"}  # Always keep these keys

# Context variable storage
_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("logging_context", default={})


def bind_request_context(request_id: str, user_id: str | None = None, trace_id: str | None = None, **kwargs) -> None:
    """Bind request context to current execution context"""
    context_data = {"request_id": request_id, "user_id": user_id, "trace_id": trace_id or request_id, **kwargs}
    _bind_context(context_data)


def bind_service_context(service: str, component: str, version: str | None = None, **kwargs) -> None:
    """Bind service context"""
    context_data = {"service": service, "component": component, "version": version, **kwargs}
    _bind_context(context_data)


def _bind_context(context_data: dict[str, Any]) -> None:
    """Common context binding logic with size limits to prevent memory leaks"""
    context = _context.get().copy()
    context.update(context_data)

    # Prevent unbounded context growth
    if len(context) > MAX_CONTEXT_SIZE:
        # Preserve protected keys and keep most recent entries
        protected_items = {k: v for k, v in context.items() if k in PROTECTED_KEYS}
        other_items = {k: v for k, v in context.items() if k not in PROTECTED_KEYS}

        # Calculate how many non-protected items we can keep
        remaining_slots = MAX_CONTEXT_SIZE - len(protected_items)
        if remaining_slots > 0:
            # Keep the most recent entries (dict maintains insertion order in Python 3.7+)
            recent_items = dict(list(other_items.items())[-remaining_slots:])
            context = {**protected_items, **recent_items}
        else:
            # If protected items alone exceed the limit, keep only protected items
            context = protected_items

    _context.set(context)

    # Use structlog's contextvars binding
    structlog.contextvars.bind_contextvars(**{k: v for k, v in context.items() if v is not None})


def get_current_context() -> dict[str, Any]:
    """Get current context"""
    return _context.get().copy()


def clear_context() -> None:
    """Clear current context"""
    _context.set({})
    structlog.contextvars.clear_contextvars()
