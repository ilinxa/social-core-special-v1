"""
Auth Tasks
==========
Celery tasks for authentication maintenance.

Tasks:
    - cleanup_expired_tokens: Daily cleanup of expired tokens
    - cleanup_inactive_sessions: Weekly cleanup of inactive sessions

Schedule via Celery Beat in backend_core/celery.py
"""

from datetime import timedelta

from celery import shared_task
from django.db import models
from django.utils import timezone

from apps.core.observability import get_logger

logger = get_logger(__name__)


@shared_task(name="auth.cleanup_expired_tokens", soft_time_limit=240, time_limit=300)
def cleanup_expired_tokens():
    """
    Periodic cleanup of expired tokens.

    Schedule: Daily via Celery Beat (3 AM)

    Cleans up:
        - Expired refresh tokens (7+ days past expiry for audit trail)
        - Used/expired verification tokens
        - Used/expired password reset tokens

    Returns:
        Dict with deletion counts
    """
    from apps.auth.models import (
        EmailVerificationToken,
        PasswordResetToken,
        RefreshToken,
    )

    # Keep tokens for 7 days past expiry for audit trail
    cutoff = timezone.now() - timedelta(days=7)

    # Cleanup expired refresh tokens
    deleted_refresh = RefreshToken.objects.filter(expires_at__lt=cutoff).delete()[0]

    # Cleanup used/expired verification tokens
    deleted_verification = EmailVerificationToken.objects.filter(
        models.Q(expires_at__lt=cutoff) | models.Q(is_used=True, used_at__lt=cutoff)
    ).delete()[0]

    # Cleanup used/expired password reset tokens
    deleted_reset = PasswordResetToken.objects.filter(
        models.Q(expires_at__lt=cutoff) | models.Q(is_used=True, used_at__lt=cutoff)
    ).delete()[0]

    result = {
        "refresh_tokens_deleted": deleted_refresh,
        "verification_tokens_deleted": deleted_verification,
        "password_reset_tokens_deleted": deleted_reset,
    }

    logger.info("auth.cleanup.completed", **result)

    return result


@shared_task(name="auth.cleanup_inactive_sessions", soft_time_limit=240, time_limit=300)
def cleanup_inactive_sessions():
    """
    Cleanup sessions inactive for 30+ days.

    Schedule: Weekly via Celery Beat (Sunday 4 AM)

    Only cleans up sessions that are:
        - Marked as inactive (is_active=False)
        - Last activity > 30 days ago

    Active sessions are NOT deleted (users might want to see them).

    Returns:
        Dict with deletion count
    """
    from apps.auth.models import DeviceSession

    cutoff = timezone.now() - timedelta(days=30)

    deleted = DeviceSession.objects.filter(
        last_activity__lt=cutoff, is_active=False
    ).delete()[0]

    result = {"sessions_deleted": deleted}

    logger.info("auth.session_cleanup.completed", **result)

    return result


@shared_task(name="auth.revoke_user_tokens", soft_time_limit=60, time_limit=120)
def revoke_user_tokens(user_id: int, reason: str = "security"):
    """
    Async task to revoke all tokens for a user.

    Use for:
        - Security events
        - Account deactivation
        - Bulk operations

    Args:
        user_id: User's ID
        reason: Reason for revocation

    Returns:
        Dict with revocation count
    """
    from apps.auth.blacklist import JTIBlacklist
    from apps.auth.models import DeviceSession, RefreshToken

    # Blacklist all JTIs
    JTIBlacklist.blacklist_user_tokens(user_id)

    # Revoke all refresh tokens
    token_count = RefreshToken.objects.filter(user_id=user_id, is_revoked=False).update(
        is_revoked=True, revoked_at=timezone.now(), revoked_reason=reason
    )

    # Deactivate all sessions
    session_count = DeviceSession.objects.filter(
        user_id=user_id, is_active=True
    ).update(is_active=False)

    result = {
        "tokens_revoked": token_count,
        "sessions_deactivated": session_count,
    }

    logger.info("auth.revoke_user.completed", user_id=user_id, **result)

    return result
