"""
Notification Policies
=====================
Authorization logic for notification operations.
"""

from uuid import UUID


class NotificationPolicy:
    """
    Authorization for notification operations.

    Follows the project's policy pattern (see ChatPolicy, BusinessPolicy).
    """

    @staticmethod
    def can_view_scoped_notifications(*, user, scope_type: str, scope_id: UUID) -> bool:
        """
        User can view notifications for a scope if:
        - scope is 'user' (always visible to the user themselves)
        - scope is 'business'/'platform' and user is an active member
        """
        if scope_type == "user":
            return True

        from apps.rbac.selectors import MembershipSelector

        return MembershipSelector.is_user_member_of_account(
            user=user, account_type=scope_type, account_id=scope_id
        )

    @staticmethod
    def can_manage_notifications(*, user, scope_type: str, scope_id: UUID) -> bool:
        """
        User can manage org notification settings if they have
        the 'can_manage_notifications' RBAC permission.
        """
        if scope_type == "user":
            return True

        from apps.rbac.selectors import MembershipSelector, PermissionSelector

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user, account_type=scope_type, account_id=scope_id
        )
        if not membership:
            return False

        perms = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id
        )
        return any(code == "can_manage_notifications" for code, _ in perms)

    @staticmethod
    def get_viewer_permissions(*, user, scope_type: str, scope_id: UUID | None) -> dict:
        """
        Tier 1.5: permissions for notification views.

        Returns dict of booleans for frontend UI gating.
        """
        if scope_type == "user" or scope_id is None:
            return {
                "can_view_notifications": True,
                "can_manage_preferences": True,
                "can_manage_org_notifications": False,
            }

        is_member = NotificationPolicy.can_view_scoped_notifications(
            user=user, scope_type=scope_type, scope_id=scope_id
        )
        can_manage = (
            NotificationPolicy.can_manage_notifications(
                user=user, scope_type=scope_type, scope_id=scope_id
            )
            if is_member
            else False
        )

        return {
            "can_view_notifications": is_member,
            "can_manage_preferences": is_member,
            "can_manage_org_notifications": can_manage,
        }
