# apps/network/policies.py
"""
Network Policies - Authorization logic for follow/connection operations.

Uses RBAC membership and permissions for business/platform-level actions.
"""

from uuid import UUID

from apps.core.constants import AccountType
from apps.rbac.selectors import MembershipSelector, PermissionSelector


class NetworkPolicy:

    # ------------------------------------------------------------------
    # Follow policies
    # ------------------------------------------------------------------

    @staticmethod
    def can_follow(*, user, followee_type: str, followee_id: UUID) -> bool:
        """Check if user can follow the target entity."""
        if not user.is_authenticated:
            return False

        from apps.network.selectors import FollowSelector

        return not FollowSelector.is_following(
            follower_id=user.id,
            followee_type=followee_type,
            followee_id=followee_id,
        )

    @staticmethod
    def can_unfollow(*, user, follow) -> bool:
        """Check if user can unfollow (must be the follower)."""
        if not user.is_authenticated:
            return False
        return follow.follower_id == user.id

    @staticmethod
    def can_manage_followers(
        *,
        user,
        account_type: str,
        account_id: UUID,
    ) -> bool:
        """Check if user has can_manage_followers permission for the account."""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=AccountType(account_type),
            account_id=account_id,
        )
        if not membership:
            return False

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id,
        )
        return any(code == "can_manage_followers" for code, scope in permissions)

    # ------------------------------------------------------------------
    # User connection policies
    # ------------------------------------------------------------------

    @staticmethod
    def can_connect_user(*, user, target_user_id: UUID) -> bool:
        """Check if user can send a connection request to target user."""
        if not user.is_authenticated:
            return False

        if user.id == target_user_id:
            return False

        from apps.network.selectors import ConnectionSelector

        return not ConnectionSelector.is_connected(
            user_a_id=user.id,
            user_b_id=target_user_id,
        )

    @staticmethod
    def can_disconnect_user(*, user, connection) -> bool:
        """Check if user can disconnect (must be party to the connection)."""
        if not user.is_authenticated:
            return False
        return user.id in (connection.user_a_id, connection.user_b_id)

    # ------------------------------------------------------------------
    # Account connection policies
    # ------------------------------------------------------------------

    @staticmethod
    def can_manage_connections(
        *,
        user,
        account_type: str,
        account_id: UUID,
    ) -> bool:
        """Check if user has can_manage_connections permission for the account."""
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=AccountType(account_type),
            account_id=account_id,
        )
        if not membership:
            return False

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id,
        )
        return any(code == "can_manage_connections" for code, scope in permissions)

    # ------------------------------------------------------------------
    # Tier 1.5 permission helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_follow_permissions(
        *,
        viewer,
        followee_type: str,
        followee_id: UUID,
    ) -> dict:
        """Get follow-related permissions for a viewer on a target entity."""
        if not viewer.is_authenticated:
            return {"can_follow": False, "can_unfollow": False}

        from apps.network.selectors import FollowSelector

        follow = FollowSelector.get_follow_for_user(
            follower_id=viewer.id,
            followee_type=followee_type,
            followee_id=followee_id,
        )
        is_following = follow is not None and follow.status == "active"

        return {
            "can_follow": not is_following,
            "can_unfollow": is_following,
        }

    @staticmethod
    def get_connection_permissions_for_user(
        *,
        viewer,
        target_user_id: UUID,
    ) -> dict:
        """Get connection-related permissions for a viewer on a target user."""
        if not viewer.is_authenticated:
            return {"can_connect": False, "can_disconnect": False}

        if viewer.id == target_user_id:
            return {"can_connect": False, "can_disconnect": False}

        from apps.network.selectors import ConnectionSelector

        conn = ConnectionSelector.get_connection_between_users(
            user_a_id=viewer.id,
            user_b_id=target_user_id,
        )
        is_connected = conn is not None and conn.status == "active"

        return {
            "can_connect": not is_connected,
            "can_disconnect": is_connected,
        }

    @staticmethod
    def get_business_network_permissions(*, viewer, business) -> dict:
        """Get all network permissions for a viewer on a business."""
        follow_perms = NetworkPolicy.get_follow_permissions(
            viewer=viewer,
            followee_type="business",
            followee_id=business.id,
        )
        return {
            **follow_perms,
            "can_manage_followers": NetworkPolicy.can_manage_followers(
                user=viewer,
                account_type="business",
                account_id=business.id,
            ),
            "can_manage_connections": NetworkPolicy.can_manage_connections(
                user=viewer,
                account_type="business",
                account_id=business.id,
            ),
        }
