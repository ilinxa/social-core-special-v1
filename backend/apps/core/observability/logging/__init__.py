"""
Structured Logging
==================
structlog-based logging with automatic context propagation.

Public API:
    - get_logger(name): Get a structured logger
    - configure_logging(): Initialize structlog configuration

Components:
    - config: structlog configuration and logger factory
    - processors: Custom log processors (redaction, etc.)
    - context: Context variable management
    - middleware: RequestLoggingMiddleware for HTTP request logging
"""

from apps.core.observability.logging.config import configure_logging, get_logger

__all__ = [
    "get_logger",
    "configure_logging",
]
