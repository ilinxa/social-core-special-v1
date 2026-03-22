# apps/organization/business/policies.py
"""
Business Policies - Authorization logic for business operations.

Policies determine whether an actor can perform specific actions.
They are called by views/services to enforce business rules.

Uses RBAC membership and permissions for authorization:
- Owner checks: MembershipSelector.is_user_owner_of_account()
- Permission checks: _has_business_permission() helper
- Membership checks: MembershipSelector.is_user_member_of_account()
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
    def can_create(*, user) -> bool:
        """
        Check if user can create a business.

        Requires platform approval (can_create_business flag) unless staff/superuser.
        """
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return user.can_create_business

    @staticmethod
    def can_view(*, user, business) -> bool:
        """
        Check if user can view a business.

        Staff/superuser can view all businesses including suspended.
        Authenticated users can view any active business.
        Anonymous users can view active businesses with public profiles.
        """
        if user.is_authenticated and (user.is_staff or user.is_superuser):
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
        - User is staff/superuser, OR
        - User is an active member with 'can_edit_business' permission
        """
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
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
        Platform staff cannot change slugs (business identity decision).
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

        User can delete if:
        - User is superuser, OR
        - User is the business owner

        Note: Regular staff cannot delete businesses.
        """
        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return MembershipSelector.is_user_owner_of_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )

    @staticmethod
    def can_archive(*, user, business) -> bool:
        """
        Check if user can archive a business.

        Only the business owner can archive their business.
        """
        if not user.is_authenticated:
            return False

        return MembershipSelector.is_user_owner_of_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )

    @staticmethod
    def can_suspend(*, user, business) -> bool:
        """
        Check if user can suspend a business.

        Only platform staff/superuser can suspend businesses.
        """
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    @staticmethod
    def can_reactivate(*, user, business) -> bool:
        """
        Check if user can reactivate a suspended business.

        Only platform staff/superuser can reactivate businesses.
        """
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    @staticmethod
    def can_verify(*, user, business) -> bool:
        """
        Check if user can verify a business.

        Only platform staff/superuser can verify businesses.
        """
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    @staticmethod
    def can_update_profile(*, user, business) -> bool:
        """
        Check if user can update business profile.

        User can update profile if:
        - User is staff/superuser, OR
        - User is an active member with 'can_edit_profile' permission
        """
        if not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
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
    def can_view_profile(*, user, business, profile) -> bool:
        """
        Check if user can view business profile.

        Public profiles are viewable by anyone (including anonymous).
        Private profiles require membership, follower status, or staff.
        """
        if user.is_authenticated and (user.is_staff or user.is_superuser):
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
