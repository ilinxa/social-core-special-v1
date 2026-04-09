# apps/organization/platform/policies.py
"""
Platform Policies - Authorization logic for platform operations.

Policies determine whether an actor can perform specific actions.
They are called by views/services to enforce business rules.

Uses RBAC membership and permissions for console authorization:
- Permission checks: _has_platform_permission() helper
- can_configure: superuser-only (platform bootstrap, not RBAC)
- All other methods: RBAC-only (Decision 3 — gconsole Phase 1)
"""

from apps.core.constants import AccountType
from apps.rbac.selectors import MembershipSelector, PermissionSelector


class PlatformPolicy:
    """Authorization policies for platform operations."""

    @staticmethod
    def _has_platform_permission(*, user, permission_code: str) -> bool:
        """
        Check if user has a specific permission in their platform membership.

        Returns True if user has an active platform membership with a role
        that grants the specified permission.
        """
        from apps.organization.platform.models import PlatformAccount

        platform = PlatformAccount.objects.first()
        if not platform:
            return False

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        if not membership:
            return False

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id,
        )
        return any(code == permission_code for code, scope in permissions)

    @staticmethod
    def can_configure(*, user) -> bool:
        """
        Check if user can configure the platform.

        Only superusers can perform initial platform configuration.
        """
        return user.is_authenticated and user.is_superuser

    @staticmethod
    def can_update_settings(*, user) -> bool:
        """
        Check if user can update platform settings.

        RBAC members with can_edit_business permission.
        """
        if not user.is_authenticated:
            return False
        return PlatformPolicy._has_platform_permission(
            user=user,
            permission_code="can_edit_business",
        )

    @staticmethod
    def can_update_profile(*, user) -> bool:
        """
        Check if user can update platform profile.

        RBAC members with can_edit_profile permission.
        """
        if not user.is_authenticated:
            return False
        return PlatformPolicy._has_platform_permission(
            user=user,
            permission_code="can_edit_profile",
        )

    @staticmethod
    def can_view(*, user) -> bool:
        """
        Check if user can view platform information.

        Platform info is publicly viewable by anyone.
        """
        return True

    @staticmethod
    def get_viewer_permissions(*, user) -> dict:
        """
        Get evaluated permissions for the requesting user.

        Returns a dict of boolean permission flags for frontend UI gating.
        """
        return {
            "can_view": PlatformPolicy.can_view(user=user),
            "can_edit_profile": PlatformPolicy.can_update_profile(user=user),
            "can_edit_settings": PlatformPolicy.can_update_settings(user=user),
        }
