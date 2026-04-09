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

Scoped query methods for REST API (D13):
    business = AuditSelector.list_for_business(business_id)
    platform = AuditSelector.list_for_platform()
    all_logs = AuditSelector.list_all()
"""

from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.core.observability.audit.models import AuditLog


class AuditSelector:
    """
    Selector for querying audit logs.

    All methods return QuerySets for composability.
    """

    # =========================================================================
    # EXISTING QUERY METHODS
    # =========================================================================

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

    # =========================================================================
    # SCOPED QUERY METHODS (D13 — Audit REST API)
    # =========================================================================

    @staticmethod
    def _apply_common_filters(
        qs: QuerySet,
        *,
        action: str | None = None,
        outcome: str | None = None,
        actor_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        resource_type: str | None = None,
    ) -> QuerySet:
        """Apply shared filter parameters to an audit queryset."""
        if action:
            qs = qs.filter(action=action)
        if outcome:
            qs = qs.filter(outcome=outcome)
        if actor_id:
            qs = qs.filter(actor_id=str(actor_id))
        if since:
            qs = qs.filter(timestamp__gte=since)
        if until:
            qs = qs.filter(timestamp__lt=until)
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        return qs

    @staticmethod
    def list_for_business(
        business_id: UUID,
        *,
        action: str | None = None,
        outcome: str | None = None,
        actor_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> QuerySet[AuditLog]:
        """
        Business-scoped audit: direct business resource actions.

        Filters by resource_type=BusinessAccount AND resource_id=business_id.
        Shows: created, updated, suspended, reactivated, archived,
        profile_updated, verification actions.
        """
        qs = AuditLog.objects.filter(
            resource_type="BusinessAccount",
            resource_id=str(business_id),
        )
        qs = AuditSelector._apply_common_filters(
            qs,
            action=action,
            outcome=outcome,
            actor_id=actor_id,
            since=since,
            until=until,
        )
        return qs.order_by("-timestamp")

    @staticmethod
    def list_for_platform(
        *,
        action: str | None = None,
        outcome: str | None = None,
        actor_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        resource_type: str | None = None,
    ) -> QuerySet[AuditLog]:
        """
        Platform-scoped audit: platform-related actions.

        Filters by action prefixes: org.platform.*, admin.*,
        auth.governance.*. Shows platform configuration, admin
        changes, and governance session events.
        """
        qs = AuditLog.objects.filter(
            Q(action__startswith="org.platform.")
            | Q(action__startswith="admin.")
            | Q(action__startswith="auth.governance.")
        )
        qs = AuditSelector._apply_common_filters(
            qs,
            action=action,
            outcome=outcome,
            actor_id=actor_id,
            since=since,
            until=until,
            resource_type=resource_type,
        )
        return qs.order_by("-timestamp")

    @staticmethod
    def list_all(
        *,
        action: str | None = None,
        outcome: str | None = None,
        actor_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        resource_type: str | None = None,
    ) -> QuerySet[AuditLog]:
        """
        Governance-scoped audit: all logs, no scope filter.

        Full cross-account visibility for governance actors.
        Requires GovernanceTokenRequired + can_view_audit_logs (global scope).
        """
        qs = AuditLog.objects.all()
        qs = AuditSelector._apply_common_filters(
            qs,
            action=action,
            outcome=outcome,
            actor_id=actor_id,
            since=since,
            until=until,
            resource_type=resource_type,
        )
        return qs.order_by("-timestamp")
