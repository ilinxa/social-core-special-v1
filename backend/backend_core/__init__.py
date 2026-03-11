"""
Backend Core Package
====================
Main Django project configuration.
"""

# This will make sure the Celery app is always imported when
# Django starts so that shared_task will use this app.
from backend_core.celery import app as celery_app

# Import schema extensions so they auto-register with drf_spectacular
try:
    from backend_core import schema  # noqa: F401
except ImportError:
    pass

__all__ = ('celery_app',)
