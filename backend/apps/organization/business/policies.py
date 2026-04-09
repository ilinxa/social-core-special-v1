# apps/organization/business/policies.py
"""
Business Policies - Authorization logic for business operations.

Policies determine whether an actor can perform specific actions.
They are called by views/services to enforce business rules.

Uses RBAC membership and permissions for authorization:
- Owner checks: MembershipSelector.is_user_owner_of_account()
- Business-scope permission checks: _has_business_permission() helper
- Global-scope permission checks: _has_global_permission() helper
- Membership checks: MembershipSelector.is_user_member_of_account()

Note: is_staff/is_superuser are NOT used for authorization.
All access control is RBAC-based (Decision 3 — gconsole Phase 1).
Superuser bypass is only available in /admin diagnostics panel.
"""

from apps.core.constants import AccountType
from apps.rbac.selectors import MembershipSelector, PermissionSelector


class BusinessPolicy:
    """Authorization policies for business operations."""

    @staticmethod
    def _has_business_permission(*, user, business, permission_code: str) -> bool:
        """
        Check if user has a specific permission for a business.

        Returns True if user has an active membership with a role
        that grants the specified permission.
        """
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        if not membership:
            return False

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id,
        )
        return any(code == permission_code for code, scope in permissions)

    @staticmethod
    def _has_global_permission(*, user, permission_code: str) -> bool:
        """
        Check if user has a global-scoped permission via platform membership.

        Used for governance actions that cross account boundaries
        (e.g., suspend any business, view all businesses).

        Returns True if user has an active platform membership with a role
        that grants the specified permission at global_only or
        platform_and_global scope.
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
        return any(
            code == permission_code and scope in ("global_only", "platform_and_global")
            for code, scope in permissions
        )

    @staticmethod
    def can_create(*, user) -> bool:
        """
        Check if user can create a business.

        Requires the can_create_business flag on the user record,
        OR the user has the global can_approve_business_creation permission
        (governance actors can always create businesses).
        """
        if not user.is_authenticated:
            return False
        if BusinessPolicy._has_global_permission(
            user=user, permission_code="can_approve_business_creation"
        ):
            return True
        return user.can_create_business

    @staticmethod
    def can_view(*, user, business) -> bool:
        """
        Check if user can view a business.

        Governance actors (can_view_businesses) can view all businesses
        including suspended/archived.
        Authenticated users can view any active business.
        Anonymous users can view active businesses with public profiles.
        """
        if user.is_authenticated and BusinessPolicy._has_global_permission(
            user=user, permission_code="can_view_businesses"
        ):
            return True

        if business.status != "active" or business.is_deleted:
            return False

        if user.is_authenticated:
            return True

        # Anonymous: only if profile is public
        try:
            return business.profile.is_public
        except Exception:
            return False

    @staticmethod
    def can_update(*, user, business) -> bool:
        """
        Check if user can update a business.

        User can update if:
        - User has global can_edit_business permission (governance), OR
        - User is an active member with 'can_edit_business' permission
        """
        if not user.is_authenticated:
            return False

        if BusinessPolicy._has_global_permission(
            user=user, permission_code="can_edit_business"
        ):
            return True

        return BusinessPolicy._has_business_permission(
            user=user,
            business=business,
            permission_code="can_edit_business",
        )

    @staticmethod
    def can_update_slug(*, user, business) -> bool:
        """
        Check if user can change business slug.

        Only the business owner can change the slug.
        """
        if not user.is_authenticated:
            return False

        return MembershipSelector.is_user_owner_of_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )

    @staticmethod
    def can_delete(*, user, business) -> bool:
        """
        Check if user can soft delete a business.

        Only the business owner can delete their own business.
        Force-delete is superuser-only via /admin diagnostics.
        """
        if not user.is_authenticated:
            return False

        return MembershipSelector.is_user_owner_of_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )

    @staticmethod
    def can_archive(*, user, business) -> bool:
        """
        Check if user can archive a business.

        Owner can self-archive (voluntary closure).
        Governance actors with can_suspend_business can also archive.
        """
        if not user.is_authenticated:
            return False

        if MembershipSelector.is_user_owner_of_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        ):
            return True

        return BusinessPolicy._has_global_permission(
            user=user, permission_code="can_suspend_business"
        )

    @staticmethod
    def can_suspend(*, user, business) -> bool:
        """
        Check if user can suspend a business.

        Requires global can_suspend_business permission (governance only).
        """
        if not user.is_authenticated:
            return False
        return BusinessPolicy._has_global_permission(
            user=user, permission_code="can_suspend_business"
        )

    @staticmethod
    def can_reactivate(*, user, business) -> bool:
        """
        Check if user can reactivate a suspended business.

        Requires global can_suspend_business permission (governance only).
        """
        if not user.is_authenticated:
            return False
        return BusinessPolicy._has_global_permission(
            user=user, permission_code="can_suspend_business"
        )

    @staticmethod
    def can_verify(*, user, business) -> bool:
        """
        Check if user can verify a business.

        Requires global can_approve_verification_request permission.
        """
        if not user.is_authenticated:
            return False
        return BusinessPolicy._has_global_permission(
            user=user, permission_code="can_approve_verification_request"
        )

    @staticmethod
    def can_update_profile(*, user, business) -> bool:
        """
        Check if user can update business profile.

        User can update profile if:
        - User has global can_edit_profile permission (governance), OR
        - User is an active member with 'can_edit_profile' permission
        """
        if not user.is_authenticated:
            return False

        if BusinessPolicy._has_global_permission(
            user=user, permission_code="can_edit_profile"
        ):
            return True

        return BusinessPolicy._has_business_permission(
            user=user,
            business=business,
            permission_code="can_edit_profile",
        )

    @staticmethod
    def get_viewer_permissions(*, user, business) -> dict:
        """
        Get evaluated permissions for the requesting user on this business.

        Returns a dict of boolean permission flags for frontend UI gating.
        """
        from apps.network.policies import NetworkPolicy

        perms = {
            "can_view": BusinessPolicy.can_view(user=user, business=business),
            "can_edit": BusinessPolicy.can_update(user=user, business=business),
            "can_edit_profile": BusinessPolicy.can_update_profile(
                user=user, business=business
            ),
            "can_delete": BusinessPolicy.can_delete(user=user, business=business),
            "can_change_slug": BusinessPolicy.can_update_slug(
                user=user, business=business
            ),
            "can_archive": BusinessPolicy.can_archive(user=user, business=business),
        }
        perms.update(
            NetworkPolicy.get_business_network_permissions(
                viewer=user, business=business
            )
        )
        return perms

    @staticmethod
    def get_governance_viewer_permissions(*, user) -> dict:
        """Get governance action permissions for the user (not business-specific)."""
        return {
            "can_suspend": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_suspend_business"
            ),
            "can_view_businesses": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_view_businesses"
            ),
            "can_edit": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_edit_business"
            ),
            "can_verify": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_approve_verification_request"
            ),
            "can_remove_owner": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_remove_business_owner"
            ),
            "can_transfer_ownership": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_transfer_business_ownership"
            ),
            "can_view_legal_info": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_view_legal_info"
            ),
            "can_archive": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_suspend_business"
            ),
            "can_approve_creation": BusinessPolicy._has_global_permission(
                user=user, permission_code="can_approve_business_creation"
            ),
        }

    @staticmethod
    def can_view_profile(*, user, business, profile) -> bool:
        """
        Check if user can view business profile.

        Public profiles are viewable by anyone (including anonymous).
        Private profiles require membership, follower status, or
        global can_view_businesses permission.
        """
        if user.is_authenticated and BusinessPolicy._has_global_permission(
            user=user, permission_code="can_view_businesses"
        ):
            return True

        if profile.is_public:
            return True

        if not user.is_authenticated:
            return False

        if MembershipSelector.is_user_member_of_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        ):
            return True

        # Followers can view private profiles
        from apps.network.selectors import FollowSelector

        return FollowSelector.is_following(
            follower_id=user.id,
            followee_type="business",
            followee_id=business.id,
        )
