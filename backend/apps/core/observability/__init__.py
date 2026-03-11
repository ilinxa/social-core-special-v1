"""
Observability System
====================
Cross-cutting observability infrastructure for the application.

This module provides:
    - Structured logging with automatic context propagation
    - Audit logging for compliance and security tracking
    - Metrics interface (NoOp by default, extensible to Prometheus)

Public API:
    Logging:
        - get_logger(name): Get a structured logger
        - configure_logging(): Initialize structlog (called in CoreConfig.ready())

    Audit:
        - AuditLog: Model for audit entries
        - AuditService: Service for creating audit logs
        - AuditSelector: Query methods for audit logs
        - audited: Decorator for automatic audit logging

    Metrics:
        - metrics: Global metrics instance (NoOp by default)

Usage:
    >>> from apps.core.observability import get_logger, AuditService, AuditLog
    >>>
    >>> logger = get_logger(__name__)
    >>> logger.info("user.updated", user_id=123)
    >>>
    >>> AuditService.log(
    ...     action=AuditLog.Action.USER_UPDATED,
    ...     actor=user,
    ...     resource=target_user,
    ...     request=request
    ... )
"""

# Logging - imported lazily to avoid circular imports during Django startup
# These will be available after configure_logging() is called in CoreConfig.ready()


def get_logger(name: str):
    """
    Get a structured logger for the given name.

    Args:
        name: Logger name, typically __name__

    Returns:
        A structlog BoundLogger with automatic context propagation

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user.login", user_id=123)
    """
    from apps.core.observability.logging.config import get_logger as _get_logger
    return _get_logger(name)


def configure_logging():
    """
    Initialize structlog configuration.

    Should be called once during Django startup, typically in CoreConfig.ready().
    """
    from apps.core.observability.logging.config import configure_logging as _configure
    _configure()


# Audit - lazy imports to avoid circular dependencies
def _get_audit_log():
    from apps.core.observability.audit.models import AuditLog
    return AuditLog


def _get_audit_service():
    from apps.core.observability.audit.service import AuditService
    return AuditService


def _get_audit_selector():
    from apps.core.observability.audit.selectors import AuditSelector
    return AuditSelector


def _get_audited():
    from apps.core.observability.audit.decorators import audited
    return audited


# Metrics
def _get_metrics():
    from apps.core.observability.metrics import metrics
    return metrics


# Module-level lazy access (for backwards compatibility with direct imports)
# The actual imports happen in __getattr__ to avoid import-time issues

def __getattr__(name: str):
    """Lazy attribute access for observability components."""
    if name == "AuditLog":
        return _get_audit_log()
    elif name == "AuditService":
        return _get_audit_service()
    elif name == "AuditSelector":
        return _get_audit_selector()
    elif name == "audited":
        return _get_audited()
    elif name == "metrics":
        return _get_metrics()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Logging
    "get_logger",
    "configure_logging",
    # Audit
    "AuditLog",
    "AuditService",
    "AuditSelector",
    "audited",
    # Metrics
    "metrics",
]
