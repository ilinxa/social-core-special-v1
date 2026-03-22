"""
Context Variable Management
===========================
Request-scoped context variables for structured logging.

These variables are automatically included in all log events
within the same request/task context.

Usage:
    from apps.core.observability.logging.context import bind_request_context

    # In middleware or task setup
    bind_request_context(
        request_id="abc-123",
        user_id="456",
    )

    # All subsequent logs in this request will include these values
"""

import uuid
from contextvars import ContextVar
from typing import Any, Dict

import structlog

# Context variables for request-scoped data
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def bind_request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    correlation_id: str | None = None,
    **extra,
) -> None:
    """
    Bind context variables for the current request.

    All subsequent log calls in this request will include these values.

    Args:
        request_id: Unique request identifier
        user_id: Authenticated user ID
        correlation_id: Cross-service correlation ID
        **extra: Additional context to bind

    Usage:
        bind_request_context(
            request_id="abc-123",
            user_id="user-456",
            custom_field="value"
        )
    """
    if request_id:
        _request_id.set(request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)

    if user_id:
        _user_id.set(user_id)
        structlog.contextvars.bind_contextvars(user_id=user_id)

    if correlation_id:
        _correlation_id.set(correlation_id)
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    if extra:
        structlog.contextvars.bind_contextvars(**extra)


def clear_request_context() -> None:
    """
    Clear all request-scoped context variables.

    Call this at the end of request processing to prevent
    context leakage between requests.
    """
    _request_id.set(None)
    _user_id.set(None)
    _correlation_id.set(None)
    structlog.contextvars.clear_contextvars()


def get_request_id() -> str | None:
    """Get the current request ID."""
    return _request_id.get()


def get_user_id() -> str | None:
    """Get the current user ID."""
    return _user_id.get()


def get_correlation_id() -> str | None:
    """Get the current correlation ID."""
    return _correlation_id.get()


def get_current_context() -> Dict[str, Any]:
    """
    Get all current context variables.

    Returns:
        Dict with request_id, user_id, and correlation_id
    """
    return {
        "request_id": _request_id.get(),
        "user_id": _user_id.get(),
        "correlation_id": _correlation_id.get(),
    }


def generate_request_id() -> str:
    """
    Generate a new request ID.

    Returns:
        UUID4 string
    """
    return str(uuid.uuid4())
