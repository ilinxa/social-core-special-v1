# apps/network/selectors.py
"""
Network Selectors - Read-only queries for Follow and Connection data.

Selectors are the single source of truth for read operations.
"""

from uuid import UUID

from django.db.models import Q, QuerySet

from apps.core.exceptions import NotFound
from apps.network.models import (
    Connection,
    ConnectionStatus,
    ConnectionType,
    Follow,
    FollowStatus,
)


class FollowSelector:

    @staticmethod
    def get_by_id(*, follow_id: UUID) -> Follow:
        follow = Follow.objects.filter(id=follow_id).first()
        if not follow:
            raise NotFound(resource="Follow", resource_id=str(follow_id))
        return follow

    @staticmethod
    def is_following(
        *,
        follower_id: UUID,
        followee_type: str,
        followee_id: UUID,
    ) -> bool:
        return Follow.objects.filter(
            follower_id=follower_id,
            followee_type=followee_type,
            followee_id=followee_id,
            status=FollowStatus.ACTIVE,
        ).exists()

    @staticmethod
    def get_follow_for_user(
        *,
        follower_id: UUID,
        followee_type: str,
        followee_id: UUID,
    ) -> Follow | None:
        """Get the follow record (any status) for a user→entity pair."""
        return (
            Follow.objects.filter(
                follower_id=follower_id,
                followee_type=followee_type,
                followee_id=followee_id,
            )
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def get_followers(
        *,
        followee_type: str,
        followee_id: UUID,
    ) -> QuerySet[Follow]:
        return Follow.objects.filter(
            followee_type=followee_type,
            followee_id=followee_id,
            status=FollowStatus.ACTIVE,
        ).select_related("follower__profile")

    @staticmethod
    def get_following(
        *,
        user_id: UUID,
        followee_type: str = None,
    ) -> QuerySet[Follow]:
        qs = Follow.objects.filter(
            follower_id=user_id,
            status=FollowStatus.ACTIVE,
        )
        if followee_type:
            qs = qs.filter(followee_type=followee_type)
        return qs

    @staticmethod
    def count_followers(*, followee_type: str, followee_id: UUID) -> int:
        return Follow.objects.filter(
            followee_type=followee_type,
            followee_id=followee_id,
            status=FollowStatus.ACTIVE,
        ).count()

    @staticmethod
    def count_following(*, user_id: UUID) -> int:
        return Follow.objects.filter(
            follower_id=user_id,
            status=FollowStatus.ACTIVE,
        ).count()


class ConnectionSelector:

    @staticmethod
    def get_by_id(*, connection_id: UUID) -> Connection:
        conn = Connection.objects.filter(id=connection_id).first()
        if not conn:
            raise NotFound(resource="Connection", resource_id=str(connection_id))
        return conn

    @staticmethod
    def is_connected(*, user_a_id: UUID, user_b_id: UUID) -> bool:
        a, b = ConnectionSelector._canonical_user_pair(user_a_id, user_b_id)
        return Connection.objects.filter(
            connection_type=ConnectionType.USER_USER,
            user_a_id=a,
            user_b_id=b,
            status=ConnectionStatus.ACTIVE,
        ).exists()

    @staticmethod
    def is_connected_account(
        *,
        a_type: str,
        a_id: UUID,
        b_type: str,
        b_id: UUID,
    ) -> bool:
        ca_type, ca_id, cb_type, cb_id = ConnectionSelector._canonical_account_pair(
            a_type,
            a_id,
            b_type,
            b_id,
        )
        return Connection.objects.filter(
            connection_type=ConnectionType.ACCOUNT_ACCOUNT,
            account_a_type=ca_type,
            account_a_id=ca_id,
            account_b_type=cb_type,
            account_b_id=cb_id,
            status=ConnectionStatus.ACTIVE,
        ).exists()

    @staticmethod
    def get_user_connections(
        *,
        user_id: UUID,
        status: str = ConnectionStatus.ACTIVE,
    ) -> QuerySet[Connection]:
        return (
            Connection.objects.filter(
                connection_type=ConnectionType.USER_USER,
                status=status,
            )
            .filter(
                Q(user_a_id=user_id) | Q(user_b_id=user_id),
            )
            .select_related("user_a__profile", "user_b__profile")
        )

    @staticmethod
    def get_account_connections(
        *,
        account_type: str,
        account_id: UUID,
        status: str = ConnectionStatus.ACTIVE,
    ) -> QuerySet[Connection]:
        return Connection.objects.filter(
            connection_type=ConnectionType.ACCOUNT_ACCOUNT,
            status=status,
        ).filter(
            Q(account_a_type=account_type, account_a_id=account_id)
            | Q(account_b_type=account_type, account_b_id=account_id),
        )

    @staticmethod
    def count_user_connections(*, user_id: UUID) -> int:
        return (
            Connection.objects.filter(
                connection_type=ConnectionType.USER_USER,
                status=ConnectionStatus.ACTIVE,
            )
            .filter(
                Q(user_a_id=user_id) | Q(user_b_id=user_id),
            )
            .count()
        )

    @staticmethod
    def count_account_connections(
        *,
        account_type: str,
        account_id: UUID,
    ) -> int:
        return (
            Connection.objects.filter(
                connection_type=ConnectionType.ACCOUNT_ACCOUNT,
                status=ConnectionStatus.ACTIVE,
            )
            .filter(
                Q(account_a_type=account_type, account_a_id=account_id)
                | Q(account_b_type=account_type, account_b_id=account_id),
            )
            .count()
        )

    @staticmethod
    def get_mutual_connections(
        *,
        user_a_id: UUID,
        user_b_id: UUID,
    ) -> QuerySet:
        """Get users connected to both user_a and user_b."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        a_connections = Connection.objects.filter(
            connection_type=ConnectionType.USER_USER,
            status=ConnectionStatus.ACTIVE,
        ).filter(
            Q(user_a_id=user_a_id) | Q(user_b_id=user_a_id),
        )
        a_partner_ids = set()
        for c in a_connections:
            partner = c.user_b_id if c.user_a_id == user_a_id else c.user_a_id
            a_partner_ids.add(partner)

        b_connections = Connection.objects.filter(
            connection_type=ConnectionType.USER_USER,
            status=ConnectionStatus.ACTIVE,
        ).filter(
            Q(user_a_id=user_b_id) | Q(user_b_id=user_b_id),
        )
        b_partner_ids = set()
        for c in b_connections:
            partner = c.user_b_id if c.user_a_id == user_b_id else c.user_a_id
            b_partner_ids.add(partner)

        mutual_ids = a_partner_ids & b_partner_ids
        return User.objects.filter(id__in=mutual_ids)

    @staticmethod
    def get_connection_between_users(
        *,
        user_a_id: UUID,
        user_b_id: UUID,
    ) -> Connection | None:
        a, b = ConnectionSelector._canonical_user_pair(user_a_id, user_b_id)
        return (
            Connection.objects.filter(
                connection_type=ConnectionType.USER_USER,
                user_a_id=a,
                user_b_id=b,
            )
            .order_by("-created_at")
            .first()
        )

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
