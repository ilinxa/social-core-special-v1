"""
Health & Readiness Probes
=========================
Kubernetes-style liveness and readiness probes.

- /health/ — Liveness: is the process alive? Returns 200 unconditionally.
  Should NOT check dependencies (a DB outage shouldn't trigger pod restarts).

- /ready/ — Readiness: can the process serve traffic? Checks DB, cache,
  and Celery broker connectivity. Returns 200 or 503.
"""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """
    Liveness probe — always returns 200 if the process is running.

    Kubernetes liveness probes should not check external dependencies;
    a database outage should not cause pod restarts.
    """
    return JsonResponse({"status": "ok"})


def readiness_check(request):
    """
    Readiness probe — checks DB, cache, and Celery broker connectivity.

    Returns 200 if all dependencies are reachable, 503 otherwise.
    """
    checks = {"status": "ok"}

    # Database
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        checks["status"] = "error"

    # Cache (Redis)
    try:
        cache.set("_ready", "1", 10)
        checks["cache"] = "ok" if cache.get("_ready") == "1" else "error"
    except Exception:
        checks["cache"] = "error"
        checks["status"] = "error"

    # Celery broker
    try:
        from backend_core.celery import app as celery_app

        result = celery_app.control.inspect(timeout=2).ping()
        checks["celery_broker"] = "ok"
        checks["celery_workers"] = "ok" if result else "none"
    except Exception:
        checks["celery_broker"] = "error"
        checks["celery_workers"] = "unknown"
        checks["status"] = "error"

    status_code = 200 if checks["status"] == "ok" else 503
    return JsonResponse(checks, status=status_code)
