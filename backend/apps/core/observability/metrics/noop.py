"""
NoOp Metrics Implementation
===========================
No-operation metrics implementation used when metrics collection is disabled.

All methods do nothing with zero overhead, making it safe to call
metrics methods throughout the codebase without performance impact.
"""

from typing import Dict

from apps.core.observability.metrics.interface import MetricsInterface


class NoOpMetrics(MetricsInterface):
    """
    No-operation metrics implementation.

    Used when metrics collection is disabled (default).
    All methods do nothing with minimal overhead.

    This allows the codebase to use metrics calls everywhere without
    worrying about whether metrics infrastructure is set up.

    Usage:
        # This does nothing but is safe to call
        metrics.increment("auth.login.total", tags={"method": "password"})
    """

    def increment(
        self,
        name: str,
        value: float = 1,
        tags: Dict[str, str] | None = None,
    ) -> None:
        """Do nothing."""
        pass

    def gauge(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] | None = None,
    ) -> None:
        """Do nothing."""
        pass

    def histogram(
        self,
        name: str,
        value: float,
        tags: Dict[str, str] | None = None,
    ) -> None:
        """Do nothing."""
        pass
