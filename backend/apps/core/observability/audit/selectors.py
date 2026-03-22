"""
Audit Log Selectors
===================
Query methods for retrieving audit logs.

Usage:
    from apps.core.observability.audit import AuditSelector, AuditLog

    logs = AuditSelector.get_by_actor(
        user.id,
        since=timezone.now() - timedelta(days=30),
        actions=[AuditLog.Action.LOGIN_SUCCESS]
    )
"""

from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from django.db.models import Count, QuerySet
from django.utils import timezone

from apps.core.observability.audit.models import AuditLog


class AuditSelector:
    """
    Selector for querying audit logs.

    All methods return QuerySets for composability.
    """

    @staticmethod
    def get_by_actor(
        actor_id: UUID,
        *,
        since: datetime | None = None,
        actions: List[str] | None = None,
    ) -> QuerySet[AuditLog]:
        """
        Get audit logs for a specific actor.

        Usage:
            logs = AuditSelector.get_by_actor(
                user.id,
                since=timezone.now() - timedelta(days=30),
                actions=[AuditLog.Action.LOGIN_SUCCESS, AuditLog.Action.LOGIN_FAILED]
            )
        """
        qs = AuditLog.objects.filter(actor_id=actor_id)

        if since:
            qs = qs.filter(timestamp__gte=since)

        if actions:
            qs = qs.filter(action__in=actions)

        return qs.order_by("-timestamp")

    @staticmethod
    def get_by_resource(
        resource_type: str,
        resource_id: UUID,
    ) -> QuerySet[AuditLog]:
        """
        Get audit trail for a specific resource.

        Usage:
            logs = AuditSelector.get_by_resource('User', user.id)
        """
        return AuditLog.objects.filter(
            resource_type=resource_type,
            resource_id=resource_id,
        ).order_by("-timestamp")

    @staticmethod
    def get_by_action(
        action: str,
        *,
        since: datetime | None = None,
        outcome: str | None = None,
    ) -> QuerySet[AuditLog]:
        """
        Get logs for a specific action type.

        Usage:
            failed_logins = AuditSelector.get_by_action(
                AuditLog.Action.LOGIN_FAILED,
                since=timezone.now() - timedelta(hours=1),
                outcome=AuditLog.Outcome.FAILURE
            )
        """
        qs = AuditLog.objects.filter(action=action)

        if since:
            qs = qs.filter(timestamp__gte=since)

        if outcome:
            qs = qs.filter(outcome=outcome)

        return qs.order_by("-timestamp")

    @staticmethod
    def get_security_events(
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> QuerySet[AuditLog]:
        """
        Get security-related events for monitoring.

        Returns events like failed logins, password changes,
        session revocations, and OAuth changes.
        """
        security_actions = [
            AuditLog.Action.LOGIN_FAILED,
            AuditLog.Action.PASSWORD_CHANGED,
            AuditLog.Action.PASSWORD_RESET_REQUESTED,
            AuditLog.Action.ALL_SESSIONS_REVOKED,
            AuditLog.Action.OAUTH_LINKED,
            AuditLog.Action.OAUTH_UNLINKED,
        ]

        qs = AuditLog.objects.filter(action__in=security_actions)

        if since:
            qs = qs.filter(timestamp__gte=since)

        return qs.order_by("-timestamp")[:limit]

    @staticmethod
    def get_failed_login_count(
        *,
        ip_address: str | None = None,
        actor_email: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """
        Count failed login attempts for rate limiting/security.

        Usage:
            count = AuditSelector.get_failed_login_count(
                ip_address="1.2.3.4",
                since=timezone.now() - timedelta(minutes=15)
            )
        """
        since = since or (timezone.now() - timedelta(minutes=15))

        qs = AuditLog.objects.filter(
            action=AuditLog.Action.LOGIN_FAILED,
            timestamp__gte=since,
        )

        if ip_address:
            qs = qs.filter(ip_address=ip_address)

        if actor_email:
            qs = qs.filter(actor_email=actor_email)

        return qs.count()

    @staticmethod
    def get_action_summary(
        *,
        since: datetime,
        until: datetime | None = None,
    ) -> List[dict]:
        """
        Get summary of actions grouped by type.

        Usage:
            summary = AuditSelector.get_action_summary(
                since=timezone.now() - timedelta(days=7)
            )
            # Returns: [{"action": "auth.login.success", "count": 150}, ...]
        """
        qs = AuditLog.objects.filter(timestamp__gte=since)

        if until:
            qs = qs.filter(timestamp__lt=until)

        return list(qs.values("action").annotate(count=Count("id")).order_by("-count"))
