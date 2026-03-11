"""
structlog Configuration
=======================
Configure structlog for structured logging with automatic context propagation.

Usage:
    # In CoreConfig.ready()
    from apps.core.observability.logging.config import configure_logging
    configure_logging()

    # In application code
    from apps.core.observability import get_logger
    logger = get_logger(__name__)
    logger.info("user.created", user_id=123)
"""

import logging
import sys
from typing import Any, List

import structlog
from django.conf import settings


def configure_logging() -> None:
    """
    Configure structlog for the application.

    Call this in Django's AppConfig.ready() to initialize logging
    before any application code runs.

    Environment-based behavior:
        - Development: Colored console output, DEBUG level
        - Production: JSON output to stdout, INFO level
    """
    # Determine output format based on environment
    is_development = getattr(settings, "DEBUG", False)
    log_format = getattr(settings, "LOGGING_FORMAT", "json")
    log_level = getattr(settings, "LOGGING_LEVEL", "INFO")
    service_name = getattr(settings, "LOGGING_SERVICE_NAME", "django-api")

    # Import custom processors
    from apps.core.observability.logging.processors import (
        sanitize_sensitive_data,
        add_service_name,
    )

    # Common processors (run for all logs)
    # NOTE: Order matters! Sanitization MUST be early to prevent leaks
    shared_processors: List[Any] = [
        structlog.contextvars.merge_contextvars,  # Merge request context
        sanitize_sensitive_data,  # CRITICAL: Redact sensitive data early
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_service_name(service_name),
    ]

    if is_development or log_format == "console":
        # Development: Pretty console output
        shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # Production: JSON output
        shared_processors.extend([
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ])

    # Configure structlog
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Reduce noise from third-party libraries
    logging.getLogger("django").setLevel(logging.WARNING)
    logging.getLogger("django.request").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Usage:
        from apps.core.observability import get_logger

        logger = get_logger(__name__)
        logger.info("event.happened", key="value")

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog BoundLogger with automatic context propagation
    """
    return structlog.get_logger(name)
