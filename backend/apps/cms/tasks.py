# apps/cms/tasks.py
"""
CMS Celery Tasks
=================
Background tasks using shared_task.
"""

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from apps.core.observability import get_logger

logger = get_logger(__name__)


@shared_task(name="cms.cleanup_tombstoned_media", soft_time_limit=240, time_limit=300)
def cleanup_tombstoned_media():
    """
    Periodic task: Remove tombstoned media files with zero published references.
    Schedule: Daily or as configured in CELERY_BEAT_SCHEDULE.
    """
    from apps.cms.services import CMSMediaService

    cleaned = CMSMediaService.cleanup_tombstoned()
    logger.info("cms.task.cleanup_tombstoned.complete", cleaned_count=cleaned)
    return cleaned


@shared_task(name="cms.prune_content_versions", soft_time_limit=300, time_limit=600)
def prune_content_versions():
    """
    Periodic task: Prune content versions beyond retention limit.
    Schedule: Weekly.
    """
    from apps.cms.models import SectionBlockPlacement
    from apps.cms.services import _prune_old_versions

    placements = SectionBlockPlacement.objects.all()
    pruned_total = 0
    try:
        for placement in placements.iterator():
            _prune_old_versions(block_placement_id=placement.id)
            pruned_total += 1
    except SoftTimeLimitExceeded:
        logger.warning(
            "cms.task.prune_versions.time_limit",
            placements_checked=pruned_total,
        )

    logger.info("cms.task.prune_versions.complete", placements_checked=pruned_total)
