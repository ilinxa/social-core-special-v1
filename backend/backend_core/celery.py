"""
Celery Configuration
====================
Celery task queue setup for Django.

Usage:
    # Start worker:
    celery -A backend_core worker -l info

    # Start beat scheduler:
    celery -A backend_core beat -l info

    # Combined (development only):
    celery -A backend_core worker -B -l info
"""

import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_core.settings.local')

# Create Celery app
app = Celery('backend_core')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat schedule
from celery.schedules import crontab

app.conf.beat_schedule = {
    # Transaction
    "expire-transactions": {
        "task": "apps.transaction.tasks.expire_transactions_task",
        "schedule": crontab(minute=0),  # Every hour
    },
    "transaction-expiration-reminders": {
        "task": "apps.transaction.tasks.send_expiration_reminder_task",
        "schedule": crontab(hour=9, minute=0),  # Daily 9 AM
    },
    "cleanup-transaction-logs": {
        "task": "apps.transaction.tasks.cleanup_old_transaction_logs_task",
        "schedule": crontab(hour=3, minute=0),  # Daily 3 AM
    },
    # Auth
    "cleanup-expired-tokens": {
        "task": "auth.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),  # Daily 2 AM
    },
    "cleanup-inactive-sessions": {
        "task": "auth.cleanup_inactive_sessions",
        "schedule": crontab(hour=2, minute=30),  # Daily 2:30 AM
    },
    # Email
    "retry-failed-emails": {
        "task": "apps.email.tasks.retry_failed_emails_task",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "cleanup-old-email-logs": {
        "task": "apps.email.tasks.cleanup_old_email_logs",
        "schedule": crontab(hour=4, minute=0),  # Daily 4 AM
    },
    # Notifications
    "cleanup-old-notification-logs": {
        "task": "apps.notifications.tasks.cleanup_old_notification_logs",
        "schedule": crontab(hour=4, minute=30),  # Daily 4:30 AM
    },
    # CMS
    "cleanup-tombstoned-media": {
        "task": "cms.cleanup_tombstoned_media",
        "schedule": crontab(hour=5, minute=0),  # Daily 5 AM
    },
    "prune-content-versions": {
        "task": "cms.prune_content_versions",
        "schedule": crontab(hour=5, minute=30, day_of_week=0),  # Weekly Sunday 5:30 AM
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
