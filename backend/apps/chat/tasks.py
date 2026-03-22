"""
Chat Tasks
==========
Celery tasks for chat system maintenance.
"""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.core.observability import get_logger

logger = get_logger(__name__)


@shared_task(soft_time_limit=120, time_limit=180)
def expire_stale_chat_requests():
    """
    Reset chat requests pending longer than CHAT_REQUEST_EXPIRY_DAYS to NONE.

    Runs periodically via Celery beat. Stale requests are auto-expired so
    conversations can be re-initiated.
    """
    from apps.chat.constants import CHAT_REQUEST_EXPIRY_DAYS, RequestStatus
    from apps.chat.models import ConversationParticipant

    cutoff = timezone.now() - timedelta(days=CHAT_REQUEST_EXPIRY_DAYS)
    count = ConversationParticipant.objects.filter(
        request_status=RequestStatus.PENDING,
        created_at__lt=cutoff,
    ).update(request_status=RequestStatus.NONE)

    logger.info("chat.requests.expired", count=count)
    return count


@shared_task(soft_time_limit=120, time_limit=180)
def cleanup_orphan_attachments():
    """
    Delete attachment files that were uploaded but never linked to a message.

    Orphan attachments older than CHAT_ATTACHMENT_ORPHAN_TTL_HOURS are cleaned up.
    Storage deletion is best-effort — the DB record is deleted regardless.
    """
    from apps.chat.constants import CHAT_ATTACHMENT_ORPHAN_TTL_HOURS
    from apps.chat.models import MessageAttachment

    from django.core.files.storage import default_storage

    cutoff = timezone.now() - timedelta(hours=CHAT_ATTACHMENT_ORPHAN_TTL_HOURS)
    orphans = MessageAttachment.objects.filter(
        message__isnull=True,
        created_at__lt=cutoff,
    )
    count = 0
    for orphan in orphans:
        try:
            default_storage.delete(orphan.storage_key)
        except Exception:
            pass  # Storage deletion is best-effort
        orphan.delete()
        count += 1

    logger.info("chat.attachments.orphans_cleaned", count=count)
    return count
