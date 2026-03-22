"""
Celery Task Logging
===================
Logging integration for Celery tasks with automatic context propagation.

Usage:
    from celery import shared_task
    from apps.core.observability.logging.celery import LoggedTask

    @shared_task(base=LoggedTask)
    def my_task():
        logger.info("task.doing.something")  # Includes task context

Or connect signals in your celery.py:
    from apps.core.observability.logging.celery import connect_celery_signals
    connect_celery_signals()
"""

import time

from celery import Task
from celery.signals import task_failure, task_postrun, task_prerun

from apps.core.observability.logging.config import get_logger
from apps.core.observability.logging.context import (
    bind_request_context,
    clear_request_context,
    generate_request_id,
)
from apps.core.observability.metrics import metrics

logger = get_logger(__name__)

# Task start times for duration tracking (keyed by task_id)
_task_start_times: dict[str, float] = {}


class LoggedTask(Task):
    """
    Base task class with automatic logging context.

    Automatically binds task_id, task_name, and correlation_id
    to the logging context for all logs within the task.

    Usage:
        @shared_task(base=LoggedTask)
        def my_task():
            logger.info("task.doing.something")  # Includes task context
    """

    def __call__(self, *args, **kwargs):
        # Bind task context
        bind_request_context(
            task_id=self.request.id,
            task_name=self.name,
            correlation_id=self.request.correlation_id or generate_request_id(),
        )

        try:
            return super().__call__(*args, **kwargs)
        finally:
            clear_request_context()


def connect_celery_signals() -> None:
    """
    Connect Celery signal handlers for task logging.

    Call this in your celery.py app setup:
        from apps.core.observability.logging.celery import connect_celery_signals
        connect_celery_signals()
    """
    # Signals are connected via decorators below
    pass


@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **_):
    """Log task start and record start time for duration tracking."""
    _task_start_times[task_id] = time.perf_counter()
    logger.info(
        "celery.task.start",
        task_id=task_id,
        task_name=task.name,
    )


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **_):
    """Log task completion with duration."""
    start = _task_start_times.pop(task_id, None)
    duration_ms = round((time.perf_counter() - start) * 1000, 2) if start else None

    logger.info(
        "celery.task.complete",
        task_id=task_id,
        task_name=task.name,
        state=state,
        duration_ms=duration_ms,
    )

    tags = {"task": task.name, "outcome": state or "SUCCESS"}
    metrics.increment("celery.tasks.total", tags=tags)
    if duration_ms is not None:
        metrics.histogram(
            "celery.task.duration_ms", duration_ms, tags={"task": task.name}
        )


@task_failure.connect
def task_failure_handler(
    task_id, exception, args, kwargs, traceback, einfo, sender=None, **_
):
    """Log task failure with duration."""
    start = _task_start_times.pop(task_id, None)
    duration_ms = round((time.perf_counter() - start) * 1000, 2) if start else None
    task_name = getattr(sender, "name", "unknown")

    logger.error(
        "celery.task.failed",
        task_id=task_id,
        task_name=task_name,
        error=str(exception),
        error_type=type(exception).__name__,
        duration_ms=duration_ms,
    )

    metrics.increment(
        "celery.tasks.total", tags={"task": task_name, "outcome": "FAILURE"}
    )
    if duration_ms is not None:
        metrics.histogram(
            "celery.task.duration_ms", duration_ms, tags={"task": task_name}
        )
