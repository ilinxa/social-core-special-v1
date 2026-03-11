"""
Metrics Interface
=================
Abstract interface for metrics collection.

Implementations:
    - NoOpMetrics: Does nothing (default, zero overhead)
    - PrometheusMetrics: Exports to Prometheus (future)

Metric Types:
    - Counter: Monotonically increasing (requests, errors)
    - Gauge: Point-in-time value (active sessions, queue size)
    - Histogram: Distribution of values (response times, sizes)
"""

import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Dict, Generator, Optional


class MetricsInterface(ABC):
    """
    Abstract interface for metrics collection.

    Usage:
        from apps.core.observability.metrics import metrics

        metrics.increment("auth.login.total", tags={"method": "password"})
        metrics.gauge("sessions.active", count)

        with metrics.timer("email.send.duration_ms"):
            send_email(...)
    """

    @staticmethod
    def _normalize_tags(tags: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """
        Normalize tag values to strings.

        Prevents type bugs when values are accidentally passed as non-strings.
        """
        if not tags:
            return None
        return {k: str(v) for k, v in tags.items()}

    @abstractmethod
    def increment(
        self,
        name: str,
        value: float = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Increment a counter metric.

        Counters are monotonically increasing values that only go up.
        Use for: total requests, total errors, total logins, etc.

        Usage:
            metrics.increment("auth.login.total", tags={"method": "password"})
            metrics.increment("email.sent.total", tags={"template": "welcome"})

        Args:
            name: Metric name (dot-separated)
            value: Amount to increment (default 1)
            tags: Dimension tags for filtering (bounded cardinality only!)
        """
        pass

    @abstractmethod
    def gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Set a gauge metric to a specific value.

        Gauges are point-in-time values that can go up or down.
        Use for: active sessions, queue size, memory usage, etc.

        Usage:
            metrics.gauge("sessions.active", count)
            metrics.gauge("queue.size", len(queue), tags={"queue": "email"})

        Args:
            name: Metric name
            value: Current value
            tags: Dimension tags (bounded cardinality only!)
        """
        pass

    @abstractmethod
    def histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a value in a histogram (distribution).

        Histograms track the distribution of values (p50, p90, p99, etc.).
        Use for: request durations, response sizes, etc.

        Usage:
            metrics.histogram("http.request.duration_ms", duration)
            metrics.histogram("email.size_bytes", len(body))

        Args:
            name: Metric name
            value: Observed value
            tags: Dimension tags (bounded cardinality only!)
        """
        pass

    @contextmanager
    def timer(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> Generator[None, None, None]:
        """
        Context manager to time an operation.

        Automatically records the duration as a histogram when the
        context exits (on success or failure).

        Usage:
            with metrics.timer("email.send.duration_ms"):
                send_email(...)

            with metrics.timer("db.query.duration_ms", tags={"query": "user_list"}):
                User.objects.all()

        Args:
            name: Metric name for the histogram
            tags: Dimension tags (bounded cardinality only!)

        Yields:
            None (just measures time)
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.histogram(name, duration_ms, tags)
