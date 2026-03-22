"""
Custom Log Processors
=====================
structlog processors for data sanitization, enrichment, and formatting.

Processors are functions that transform log event dictionaries.
They run in order, so sanitization should come early in the pipeline.
"""

import socket
from typing import Any, Callable, MutableMapping

# Sensitive keys to redact from logs
# These are checked case-insensitively
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "credit_card",
        "creditcard",
        "ssn",
        "access_token",
        "refresh_token",
        "cookie",
        "session_id",
        "private_key",
        "privatekey",
        "otp",
        "verification_code",
        "csrf",
    }
)


def sanitize_sensitive_data(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Remove or mask sensitive data from log events.

    This processor MUST run early in the pipeline to prevent
    accidental logging of sensitive information.

    Sensitive keys include: password, token, secret, api_key,
    authorization, credit_card, ssn, access_token, refresh_token, etc.

    Args:
        logger: The logger instance
        method_name: The log method being called
        event_dict: The event dictionary to process

    Returns:
        Sanitized event dictionary
    """

    def sanitize(obj: Any, depth: int = 0) -> Any:
        if depth > 5:  # Prevent infinite recursion
            return obj

        if isinstance(obj, dict):
            return {
                k: (
                    "[REDACTED]"
                    if k.lower() in SENSITIVE_KEYS
                    else sanitize(v, depth + 1)
                )
                for k, v in obj.items()
            }
        elif isinstance(obj, (list, tuple)):
            return [sanitize(item, depth + 1) for item in obj]
        return obj

    return sanitize(event_dict)


def add_hostname(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Add hostname to log events for distributed systems.

    Useful for identifying which server generated a log entry.

    Args:
        logger: The logger instance
        method_name: The log method being called
        event_dict: The event dictionary to process

    Returns:
        Event dictionary with hostname added
    """
    event_dict["hostname"] = socket.gethostname()
    return event_dict


def add_service_name(service_name: str) -> Callable:
    """
    Factory to create processor that adds service name.

    Usage:
        shared_processors.append(add_service_name("my-api"))

    Args:
        service_name: The service name to add to all log events

    Returns:
        Processor function
    """

    def processor(
        logger: Any,
        method_name: str,
        event_dict: MutableMapping[str, Any],
    ) -> MutableMapping[str, Any]:
        event_dict["service"] = service_name
        return event_dict

    return processor


def add_exception_context(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Add structured exception information.

    Extracts exception type, message, module, and formatted traceback
    for better error analysis in log aggregators.

    Args:
        logger: The logger instance
        method_name: The log method being called
        event_dict: The event dictionary to process

    Returns:
        Event dictionary with structured exception info
    """
    import traceback

    exc_info = event_dict.pop("exc_info", None)

    if exc_info:
        if isinstance(exc_info, tuple):
            exc_type, exc_value, exc_tb = exc_info
        else:
            import sys

            exc_type, exc_value, exc_tb = sys.exc_info()

        if exc_type:
            event_dict["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "module": exc_type.__module__,
            }
            # Include formatted stack trace for better debugging
            if exc_tb:
                event_dict["exception"]["stack"] = traceback.format_tb(exc_tb)

    return event_dict
