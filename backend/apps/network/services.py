# apps/network/services.py
"""
Network Services - Write operations for Follow and Connection.

All write methods are @staticmethod, @transaction.atomic, keyword-only args.
"""

from uuid import UUID

from django.db import transaction as db_transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleViolation, ConflictError, PermissionDenied
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditService
from apps.core.observability.audit.models import AuditLog
from apps.network.models import (
    Connection,
    ConnectionStatus,
    ConnectionType,
    Follow,
    FollowStatus,
)

logger = get_logger(__name__)


class FollowService:

    @staticmethod
    @db_transaction.atomic
    def create_follow(
        *,
        follower,
        followee_type: str,
        followee_id: UUID,
        transaction_id: UUID = None,
        request=None,
    ) -> Follow:
        """
        Create a follow relationship. Reactivates if previously removed.
        """
        existing = Follow.objects.filter(
            follower=follower,
            followee_type=followee_type,
            followee_id=followee_id,
        ).first()

        if existing:
            if existing.status == FollowStatus.ACTIVE:
                raise ConflictError(
                    message="Already following this account",
                    resource="Follow",
                    conflict_type="duplicate",
                )
            # Reactivate previously removed follow
            existing.status = FollowStatus.ACTIVE
            existing.removed_at = None
            existing.removed_by = None
            existing.save(
                update_fields=["status", "removed_at", "removed_by", "updated_at"]
            )
            follow = existing
        else:
            follow = Follow.objects.create(
                follower=follower,
                followee_type=followee_type,
                followee_id=followee_id,
                status=FollowStatus.ACTIVE,
            )

        AuditService.log(
            action=AuditLog.Action.FOLLOW_CREATED,
            actor=follower,
            resource=follow,
            request=request,
            details={
                "followee_type": followee_type,
                "followee_id": str(followee_id),
                "transaction_id": str(transaction_id) if transaction_id else None,
            },
        )
        logger.info(
            "network.follow.created",
            follow_id=str(follow.id),
            follower_id=str(follower.id),
            followee_type=followee_type,
            followee_id=str(followee_id),
        )
        return follow

    @staticmethod
    @db_transaction.atomic
    def unfollow(*, follow_id: UUID, user, request=None) -> Follow:
        """User unfollows — must be the follower."""
        from apps.network.selectors import FollowSelector

        follow = FollowSelector.get_by_id(follow_id=follow_id)

        if follow.follower_id != user.id:
            raise PermissionDenied(
                message="Only the follower can unfollow",
                action="unfollow",
                resource="Follow",
            )

        if follow.status != FollowStatus.ACTIVE:
            raise BusinessRuleViolation(
                message="Follow is not active",
                rule="follow_not_active",
            )

        now = timezone.now()
        follow.status = FollowStatus.REMOVED
        follow.removed_at = now
        follow.removed_by = user
        follow.save(update_fields=["status", "removed_at", "removed_by", "updated_at"])

        AuditService.log(
            action=AuditLog.Action.FOLLOW_REMOVED,
            actor=user,
            resource=follow,
            request=request,
            details={
                "followee_type": follow.followee_type,
                "followee_id": str(follow.followee_id),
            },
        )
        logger.info("network.follow.removed", follow_id=str(follow.id))
        return follow

    @staticmethod
    @db_transaction.atomic
    def remove_follower(
        *,
        follow_id: UUID,
        actor,
        actor_context,
        request=None,
    ) -> Follow:
        """Account manager removes a follower. Requires can_manage_followers."""
        from apps.network.policies import NetworkPolicy
        from apps.network.selectors import FollowSelector

        follow = FollowSelector.get_by_id(follow_id=follow_id)

        if follow.status != FollowStatus.ACTIVE:
            raise BusinessRuleViolation(
                message="Follow is not active",
                rule="follow_not_active",
            )

        if not NetworkPolicy.can_manage_followers(
            user=actor,
            account_type=follow.followee_type,
            account_id=follow.followee_id,
        ):
            raise PermissionDenied(
                message="You do not have permission to manage followers",
                action="remove_follower",
                resource="Follow",
            )

        now = timezone.now()
        follow.status = FollowStatus.REMOVED
        follow.removed_at = now
        follow.removed_by = actor
        follow.save(update_fields=["status", "removed_at", "removed_by", "updated_at"])

        AuditService.log(
            action=AuditLog.Action.FOLLOWER_REMOVED,
            actor=actor,
            resource=follow,
            request=request,
            details={
                "follower_id": str(follow.follower_id),
                "followee_type": follow.followee_type,
                "followee_id": str(follow.followee_id),
            },
        )
        logger.info(
            "network.follower.removed",
            follow_id=str(follow.id),
            removed_by=str(actor.id),
        )

        # Notify the removed follower (deferred until transaction commits)
        _follow = follow

        def _send_removal_notification():
            try:
                from apps.notifications.services import NotificationService

                NotificationService.send(
                    user=_follow.follower,
                    notification_type="new_follower",
                    context={
                        "follower_id": str(_follow.follower_id),
                        "followee_type": _follow.followee_type,
                        "followee_id": str(_follow.followee_id),
                        "action": "removed",
                    },
                )
            except Exception:
                logger.warning(
                    "network.follower.removed.notification_failed",
                    follow_id=str(_follow.id),
                )

        db_transaction.on_commit(_send_removal_notification)

        return follow


class ConnectionService:

    @staticmethod
    def _canonical_user_pair(user_a_id: UUID, user_b_id: UUID):
        if str(user_a_id) <= str(user_b_id):
            return user_a_id, user_b_id
        return user_b_id, user_a_id

    @staticmethod
    def _canonical_account_pair(a_type, a_id, b_type, b_id):
        if (a_type, str(a_id)) <= (b_type, str(b_id)):
            return a_type, a_id, b_type, b_id
        return b_type, b_id, a_type, a_id

    @staticmethod
    @db_transaction.atomic
    def create_user_connection(
        *,
        user_a_id: UUID,
        user_b_id: UUID,
        note: str = "",
        initiated_by_id: UUID = None,
        transaction_id: UUID = None,
        request=None,
    ) -> Connection:
        """Create a user↔user connection. Reactivates if disconnected."""
        ca, cb = ConnectionService._canonical_user_pair(user_a_id, user_b_id)

        existing = Connection.objects.filter(
            connection_type=ConnectionType.USER_USER,
            user_a_id=ca,
            user_b_id=cb,
        ).first()

        now = timezone.now()
        if existing:
            if existing.status == ConnectionStatus.ACTIVE:
                raise ConflictError(
                    message="Users are already connected",
                    resource="Connection",
                    conflict_type="duplicate",
                )
            # Reactivate
            existing.status = ConnectionStatus.ACTIVE
            existing.note = note
            existing.connected_at = now
            existing.disconnected_at = None
            existing.disconnected_by = None
            existing.initiated_by_id = initiated_by_id
            existing.save(
                update_fields=[
                    "status",
                    "note",
                    "connected_at",
                    "disconnected_at",
                    "disconnected_by",
                    "initiated_by_id",
                    "updated_at",
                ]
            )
            connection = existing
        else:
            connection = Connection.objects.create(
                connection_type=ConnectionType.USER_USER,
                user_a_id=ca,
                user_b_id=cb,
                status=ConnectionStatus.ACTIVE,
                note=note,
                initiated_by_id=initiated_by_id,
                connected_at=now,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        actor = (
            User.objects.filter(id=initiated_by_id).first() if initiated_by_id else None
        )

        AuditService.log(
            action=AuditLog.Action.CONNECTION_CREATED,
            actor=actor,
            resource=connection,
            request=request,
            details={
                "user_a_id": str(ca),
                "user_b_id": str(cb),
                "transaction_id": str(transaction_id) if transaction_id else None,
            },
        )
        logger.info(
            "network.connection.created",
            connection_id=str(connection.id),
            user_a=str(ca),
            user_b=str(cb),
        )
        return connection

    @staticmethod
    @db_transaction.atomic
    def create_account_connection(
        *,
        a_type: str,
        a_id: UUID,
        b_type: str,
        b_id: UUID,
        initiated_by_id: UUID = None,
        note: str = "",
        transaction_id: UUID = None,
        request=None,
    ) -> Connection:
        """Create an account↔account connection. Reactivates if disconnected."""
        ca_type, ca_id, cb_type, cb_id = ConnectionService._canonical_account_pair(
            a_type,
            a_id,
            b_type,
            b_id,
        )

        existing = Connection.objects.filter(
            connection_type=ConnectionType.ACCOUNT_ACCOUNT,
            account_a_type=ca_type,
            account_a_id=ca_id,
            account_b_type=cb_type,
            account_b_id=cb_id,
        ).first()

        now = timezone.now()
        if existing:
            if existing.status == ConnectionStatus.ACTIVE:
                raise ConflictError(
                    message="Accounts are already connected",
                    resource="Connection",
                    conflict_type="duplicate",
                )
            existing.status = ConnectionStatus.ACTIVE
            existing.note = note
            existing.connected_at = now
            existing.disconnected_at = None
            existing.disconnected_by = None
            existing.initiated_by_id = initiated_by_id
            existing.save(
                update_fields=[
                    "status",
                    "note",
                    "connected_at",
                    "disconnected_at",
                    "disconnected_by",
                    "initiated_by_id",
                    "updated_at",
                ]
            )
            connection = existing
        else:
            connection = Connection.objects.create(
                connection_type=ConnectionType.ACCOUNT_ACCOUNT,
                account_a_type=ca_type,
                account_a_id=ca_id,
                account_b_type=cb_type,
                account_b_id=cb_id,
                status=ConnectionStatus.ACTIVE,
                note=note,
                initiated_by_id=initiated_by_id,
                connected_at=now,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        actor = (
            User.objects.filter(id=initiated_by_id).first() if initiated_by_id else None
        )

        AuditService.log(
            action=AuditLog.Action.CONNECTION_CREATED,
            actor=actor,
            resource=connection,
            request=request,
            details={
                "account_a": f"{ca_type}:{ca_id}",
                "account_b": f"{cb_type}:{cb_id}",
                "transaction_id": str(transaction_id) if transaction_id else None,
            },
        )
        logger.info(
            "network.connection.created",
            connection_id=str(connection.id),
            account_a=f"{ca_type}:{ca_id}",
            account_b=f"{cb_type}:{cb_id}",
        )
        return connection

    @staticmethod
    @db_transaction.atomic
    def disconnect_user_connection(
        *,
        connection_id: UUID,
        user,
        request=None,
    ) -> Connection:
        """User disconnects from another user."""
        from apps.network.selectors import ConnectionSelector

        connection = ConnectionSelector.get_by_id(connection_id=connection_id)

        if connection.connection_type != ConnectionType.USER_USER:
            raise BusinessRuleViolation(
                message="Not a user connection",
                rule="wrong_connection_type",
            )

        if user.id not in (connection.user_a_id, connection.user_b_id):
            raise PermissionDenied(
                message="You are not a party to this connection",
                action="disconnect",
                resource="Connection",
            )

        if connection.status != ConnectionStatus.ACTIVE:
            raise BusinessRuleViolation(
                message="Connection is not active",
                rule="connection_not_active",
            )

        now = timezone.now()
        connection.status = ConnectionStatus.DISCONNECTED
        connection.disconnected_at = now
        connection.disconnected_by = user
        connection.save(
            update_fields=[
                "status",
                "disconnected_at",
                "disconnected_by",
                "updated_at",
            ]
        )

        AuditService.log(
            action=AuditLog.Action.CONNECTION_DISCONNECTED,
            actor=user,
            resource=connection,
            request=request,
            details={
                "user_a_id": str(connection.user_a_id),
                "user_b_id": str(connection.user_b_id),
            },
        )
        logger.info(
            "network.connection.disconnected",
            connection_id=str(connection.id),
            disconnected_by=str(user.id),
        )
        return connection

    @staticmethod
    @db_transaction.atomic
    def disconnect_account_connection(
        *,
        connection_id: UUID,
        actor,
        actor_context,
        request=None,
    ) -> Connection:
        """Account manager disconnects an account connection."""
        from apps.network.policies import NetworkPolicy
        from apps.network.selectors import ConnectionSelector

        connection = ConnectionSelector.get_by_id(connection_id=connection_id)

        if connection.connection_type != ConnectionType.ACCOUNT_ACCOUNT:
            raise BusinessRuleViolation(
                message="Not an account connection",
                rule="wrong_connection_type",
            )

        if connection.status != ConnectionStatus.ACTIVE:
            raise BusinessRuleViolation(
                message="Connection is not active",
                rule="connection_not_active",
            )

        # Check permission on at least one side
        has_perm = False
        for acct_type, acct_id in [
            (connection.account_a_type, connection.account_a_id),
            (connection.account_b_type, connection.account_b_id),
        ]:
            if NetworkPolicy.can_manage_connections(
                user=actor,
                account_type=acct_type,
                account_id=acct_id,
            ):
                has_perm = True
                break

        if not has_perm:
            raise PermissionDenied(
                message="You do not have permission to manage connections",
                action="disconnect_account_connection",
                resource="Connection",
            )

        now = timezone.now()
        connection.status = ConnectionStatus.DISCONNECTED
        connection.disconnected_at = now
        connection.disconnected_by = actor
        connection.save(
            update_fields=[
                "status",
                "disconnected_at",
                "disconnected_by",
                "updated_at",
            ]
        )

        AuditService.log(
            action=AuditLog.Action.CONNECTION_DISCONNECTED,
            actor=actor,
            resource=connection,
            request=request,
            details={
                "account_a": f"{connection.account_a_type}:{connection.account_a_id}",
                "account_b": f"{connection.account_b_type}:{connection.account_b_id}",
            },
        )
        logger.info(
            "network.connection.disconnected",
            connection_id=str(connection.id),
            disconnected_by=str(actor.id),
        )
        return connection
