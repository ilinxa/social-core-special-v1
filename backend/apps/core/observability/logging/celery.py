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

from celery import Task
from celery.signals import task_prerun, task_postrun, task_failure

from apps.core.observability.logging.context import (
    bind_request_context,
    clear_request_context,
    generate_request_id,
)
from apps.core.observability.logging.config import get_logger


logger = get_logger(__name__)


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
    """Log task start."""
    logger.info(
        "celery.task.start",
        task_id=task_id,
        task_name=task.name,
    )


@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **_):
    """Log task completion."""
    logger.info(
        "celery.task.complete",
        task_id=task_id,
        task_name=task.name,
        state=state,
    )


@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **_):
    """Log task failure."""
    logger.error(
        "celery.task.failed",
        task_id=task_id,
        error=str(exception),
        error_type=type(exception).__name__,
    )
