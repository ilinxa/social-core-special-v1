"""
Request Logging Middleware
==========================
Django middleware for request context binding and HTTP request logging.

This middleware:
    1. Generates/extracts request IDs for correlation
    2. Binds request context to all logs in the request
    3. Logs request start/completion with timing
    4. Adds X-Request-ID header to responses

Add to MIDDLEWARE after AuthenticationMiddleware:
    'apps.core.observability.logging.middleware.RequestLoggingMiddleware',
"""

import time
from typing import FrozenSet

from django.http import HttpRequest, HttpResponse

from apps.core.observability.logging.config import get_logger
from apps.core.observability.logging.context import (
    bind_request_context,
    clear_request_context,
    generate_request_id,
)
from apps.core.observability.metrics import metrics

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware to inject request context into logs and track request timing.

    Features:
        - Generates or extracts X-Request-ID for correlation
        - Binds request_id, user_id, path, method to all logs
        - Logs request start and completion with timing
        - Skips logging for health check endpoints
        - Stores request_id on request object for other middleware

    Middleware Order:
        Must be placed AFTER AuthenticationMiddleware (needs request.user)
        but early enough to capture request timing.
    """

    # Paths to skip logging (health checks, metrics endpoints)
    # These get hit frequently by load balancers and would flood logs
    SKIP_LOGGING_PATHS: FrozenSet[str] = frozenset(
        [
            "/health",
            "/health/",
            "/healthz",
            "/healthz/",
            "/ready",
            "/ready/",
            "/metrics",
            "/metrics/",
        ]
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip logging for health check endpoints
        # These are hit constantly by load balancers/kubernetes
        if request.path in self.SKIP_LOGGING_PATHS:
            return self.get_response(request)

        # Extract or generate request ID
        request_id = request.META.get("HTTP_X_REQUEST_ID") or generate_request_id()

        # Extract user ID if authenticated
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)

        # Bind context for all logs in this request
        bind_request_context(
            request_id=request_id,
            user_id=user_id,
            path=request.path,
            method=request.method,
        )

        # Store on request object for other middleware/views
        request.request_id = request_id

        # Log request start
        start_time = time.perf_counter()

        logger.info(
            "http.request.start",
            path=request.path,
            method=request.method,
            query_string=request.META.get("QUERY_STRING", ""),
        )

        try:
            response = self.get_response(request)

            # Log request completion
            # Standardize precision to 3 decimal places across all timing logs
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            logger.info(
                "http.request.complete",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Emit metrics (NoOp backend = zero cost; pre-wired for Prometheus)
            # NOTE: 'endpoint' tag may have high cardinality from UUIDs in paths.
            # Normalize to route patterns when implementing a real metrics backend.
            metrics.increment(
                "http.requests.total",
                tags={
                    "method": request.method,
                    "status_code": str(response.status_code),
                },
            )
            metrics.histogram(
                "http.request.duration_ms",
                duration_ms,
                tags={"method": request.method, "endpoint": request.path},
            )

            # Add request ID to response headers
            response["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Log exception
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            logger.exception(
                "http.request.error",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )

            metrics.increment(
                "http.requests.total",
                tags={"method": request.method, "status_code": "500"},
            )
            metrics.histogram(
                "http.request.duration_ms",
                duration_ms,
                tags={"method": request.method, "endpoint": request.path},
            )
            raise

        finally:
            # Clear context after request
            clear_request_context()
