"""
Metrics System
==============
Application metrics collection with pluggable backends.

Current Implementation:
    - NoOpMetrics: Does nothing (default)

Future Backends:
    - PrometheusMetrics: Exports to Prometheus

Public API:
    - metrics: Global metrics instance

Usage:
    >>> from apps.core.observability.metrics import metrics
    >>>
    >>> metrics.increment("auth.login.total", tags={"method": "password"})
    >>> metrics.gauge("sessions.active", count)
    >>>
    >>> with metrics.timer("email.send.duration"):
    ...     send_email(...)
"""

from django.conf import settings

from apps.core.observability.metrics.interface import MetricsInterface
from apps.core.observability.metrics.noop import NoOpMetrics


def _get_metrics_backend() -> MetricsInterface:
    """
    Get the configured metrics backend.

    Returns:
        MetricsInterface implementation based on settings.
    """
    enabled = getattr(settings, "METRICS_ENABLED", False)
    backend = getattr(settings, "METRICS_BACKEND", "noop")

    if not enabled or backend == "noop":
        return NoOpMetrics()

    # Future: Prometheus backend
    # if backend == "prometheus":
    #     from apps.core.observability.metrics.prometheus import PrometheusMetrics
    #     return PrometheusMetrics()

    return NoOpMetrics()


# Global metrics instance
metrics: MetricsInterface = _get_metrics_backend()

__all__ = [
    "metrics",
    "MetricsInterface",
    "NoOpMetrics",
]
