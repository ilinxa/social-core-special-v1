# apps/rbac/selectors.py
"""
RBAC Selectors - Read-only queries for RBAC data.

Selectors are the single source of truth for read operations.
They handle caching where appropriate and return domain objects.
"""

from typing import List, Tuple
from uuid import UUID

from django.core.cache import cache
from django.db.models import QuerySet

from apps.core.constants import MembershipStatus
from apps.core.exceptions import NotFound
from apps.rbac.models import Membership, Permission, Role, RolePermission


class PermissionSelector:
    """
    Selectors for Permission queries with caching for membership permissions.
    """

    CACHE_TTL = 300  # 5 minutes

    @staticmethod
    def get_all_permissions() -> QuerySet[Permission]:
        """Get all permissions ordered by category and code."""
        return Permission.objects.all().order_by("category", "code")

    @staticmethod
    def get_permission_by_id(*, permission_id: UUID) -> Permission:
        """
        Get a permission by ID.

        Raises:
            NotFound: If permission doesn't exist
        """
        try:
            return Permission.objects.get(id=permission_id)
        except Permission.DoesNotExist:
            raise NotFound(
                message="Permission not found",
                resource="Permission",
                resource_id=permission_id,
            )

    @staticmethod
    def get_permission_by_code(*, code: str) -> Permission:
        """
        Get a permission by code.

        Raises:
            NotFound: If permission doesn't exist
        """
        try:
            return Permission.objects.get(code=code)
        except Permission.DoesNotExist:
            raise NotFound(
                message="Permission not found", resource="Permission", resource_id=code
            )

    @staticmethod
    def get_permissions_by_category(*, category: str) -> QuerySet[Permission]:
        """Get all permissions in a category."""
        return Permission.objects.filter(category=category)

    @staticmethod
    def get_permissions_by_scope(*, scope: str) -> List[Permission]:
        """
        Get all permissions that include the given scope in applicable_scopes.

        Uses Python filtering to work across all database backends (SQLite, PostgreSQL).

        Args:
            scope: The scope to filter by (e.g., "business", "platform_only", "global_only")

        Returns:
            List of Permission objects that have this scope in their applicable_scopes.
        """
        all_permissions = Permission.objects.all()
        return [
            perm for perm in all_permissions if scope in (perm.applicable_scopes or [])
        ]

    @staticmethod
    def get_permissions_for_membership(*, membership_id: UUID) -> List[Tuple[str, str]]:
        """
        Get permission (code, scope) tuples for a membership.

        Uses caching for performance. Returns empty list if membership
        is not active or role is soft-deleted.

        Returns:
            List of (permission_code, scope) tuples.
            e.g. [("can_view_members", "business"), ("can_remove_member", "global_only")]
        """
        cache_key = f"membership_permissions:{membership_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Verify membership is active and role is not soft-deleted
        # If membership is not active (suspended/banned/left/removed),
        # return empty permissions - this is the correct semantic.
        try:
            membership = Membership.objects.select_related("role").get(
                id=membership_id,
                status=MembershipStatus.ACTIVE,
            )
        except Membership.DoesNotExist:
            return []

        if membership.role.is_deleted:
            # Role was soft-deleted but member wasn't reassigned (shouldn't happen
            # because delete_role blocks when members exist, but defensive check)
            return []

        permissions = list(
            membership.role.role_permissions.select_related("permission").values_list(
                "permission__code", "scope"
            )
        )

        cache.set(cache_key, permissions, PermissionSelector.CACHE_TTL)
        return permissions

    @staticmethod
    def invalidate_membership_permissions(*, membership_id: UUID) -> None:
        """Invalidate cached permissions for a specific membership."""
        cache_key = f"membership_permissions:{membership_id}"
        cache.delete(cache_key)

    @staticmethod
    def invalidate_role_permissions(*, role_id: UUID) -> None:
        """Invalidate cached permissions for all memberships with this role."""
        membership_ids = list(
            Membership.objects.filter(role_id=role_id).values_list("id", flat=True)
        )
        if membership_ids:
            cache.delete_many(
                [f"membership_permissions:{mid}" for mid in membership_ids]
            )


class RoleSelector:
    """
    Selectors for Role queries.
    """

    @staticmethod
    def get_role_by_id(*, role_id: UUID) -> Role:
        """
        Get a role by ID.

        Raises:
            NotFound: If role doesn't exist or is soft-deleted
        """
        try:
            return Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            raise NotFound(
                message="Role not found", resource="Role", resource_id=role_id
            )

    @staticmethod
    def get_roles_for_account(
        *, account_type: str, account_id: UUID, include_system: bool = True
    ) -> QuerySet[Role]:
        """
        Get all roles for an account.

        Args:
            account_type: AccountType value
            account_id: UUID of the account
            include_system: Whether to include system roles (default True)

        Returns:
            QuerySet of roles ordered by level
        """
        from django.db.models import Count, Q

        qs = Role.objects.filter(
            account_type=account_type,
            account_id=account_id,
        ).annotate(
            member_count=Count(
                "memberships",
                filter=Q(
                    memberships__is_deleted=False,
                    memberships__status="active",
                ),
            ),
        )
        if not include_system:
            qs = qs.filter(is_system_role=False)
        return qs.order_by("level")

    @staticmethod
    def get_owner_role(*, account_type: str, account_id: UUID) -> Role:
        """
        Get the owner role (level 0) for an account.

        Raises:
            NotFound: If owner role doesn't exist
        """
        try:
            return Role.objects.get(
                account_type=account_type,
                account_id=account_id,
                level=0,
                is_system_role=True,
            )
        except Role.DoesNotExist:
            raise NotFound(
                message="Owner role not found for account",
                resource="Role",
            )

    @staticmethod
    def get_base_member_role(*, account_type: str, account_id: UUID) -> Role:
        """
        Get the base member role (level 10) for an account.

        Raises:
            NotFound: If base member role doesn't exist
        """
        try:
            return Role.objects.get(
                account_type=account_type,
                account_id=account_id,
                name="Base Member",
                is_system_role=True,
            )
        except Role.DoesNotExist:
            raise NotFound(
                message="Base Member role not found for account",
                resource="Role",
            )

    @staticmethod
    def get_role_permissions(*, role_id: UUID) -> QuerySet[RolePermission]:
        """Get all permission assignments for a role."""
        return RolePermission.objects.filter(role_id=role_id).select_related(
            "permission"
        )


class MembershipSelector:
    """
    Selectors for Membership queries.
    """

    @staticmethod
    def get_membership_by_id(*, membership_id: UUID) -> Membership:
        """
        Get a membership by ID.

        Raises:
            NotFound: If membership doesn't exist or is soft-deleted
        """
        try:
            return Membership.objects.select_related("role", "user").get(
                id=membership_id
            )
        except Membership.DoesNotExist:
            raise NotFound(
                message="Membership not found",
                resource="Membership",
                resource_id=membership_id,
            )

    @staticmethod
    def get_membership_for_user_account(
        *, user, account_type: str, account_id: UUID
    ) -> Membership | None:
        """
        Get a user's membership in a specific account.

        Returns:
            Membership or None if not a member
        """
        return (
            Membership.objects.filter(
                user=user,
                account_type=account_type,
                account_id=account_id,
            )
            .select_related("role")
            .first()
        )

    @staticmethod
    def get_active_membership_for_user_account(
        *, user, account_type: str, account_id: UUID
    ) -> Membership | None:
        """
        Get a user's active membership in a specific account.

        Returns:
            Membership or None if not an active member
        """
        return (
            Membership.objects.active()
            .filter(
                user=user,
                account_type=account_type,
                account_id=account_id,
            )
            .select_related("role")
            .first()
        )

    @staticmethod
    def count_active_members(*, account_type: str, account_id: UUID) -> int:
        """Count active and pending-approval (non-deleted) members in an account."""
        return Membership.objects.filter(
            account_type=account_type,
            account_id=account_id,
            status__in=[MembershipStatus.ACTIVE, MembershipStatus.PENDING_APPROVAL],
            is_deleted=False,
        ).count()

    @staticmethod
    def get_memberships_for_account(
        *,
        account_type: str,
        account_id: UUID,
        status: str | None = None,
        include_all_statuses: bool = False,
        search: str | None = None,
        role_id: UUID | None = None,
        ordering: str | None = None,
    ) -> QuerySet[Membership]:
        """
        Get all memberships for an account.

        Args:
            account_type: AccountType value
            account_id: UUID of the account
            status: Filter by specific status (optional)
            include_all_statuses: If True, include non-active statuses
            search: Search by user email, username, or profile name
            role_id: Filter by role ID
            ordering: Order by field (joined_at, -joined_at, status, role_level)

        Returns:
            QuerySet of memberships
        """
        if include_all_statuses:
            qs = Membership.objects.filter(
                account_type=account_type,
                account_id=account_id,
            )
        else:
            qs = Membership.objects.active().filter(
                account_type=account_type,
                account_id=account_id,
            )

        if status:
            qs = qs.filter(status=status)

        if role_id:
            qs = qs.filter(role_id=role_id)

        if search:
            from django.db.models import Q

            qs = qs.filter(
                Q(user__email__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__profile__first_name__icontains=search)
                | Q(user__profile__last_name__icontains=search)
            )

        order_map = {
            "joined_at": "joined_at",
            "-joined_at": "-joined_at",
            "status": "status",
            "role_level": "role__level",
        }
        order_field = order_map.get(ordering, "-joined_at")

        return qs.select_related("role", "user").order_by(order_field)

    @staticmethod
    def get_memberships_for_user(
        *,
        user,
        status: str | None = None,
        include_all_statuses: bool = False,
        include_pending_approval: bool = False,
    ) -> QuerySet[Membership]:
        """
        Get all memberships for a user.

        Args:
            user: User object
            status: Filter by specific status (optional)
            include_all_statuses: If True, include non-active statuses
            include_pending_approval: If True, also include pending_approval
                alongside active memberships (used by my-memberships API so
                the frontend can show a "Pending Review" guard).

        Returns:
            QuerySet of memberships
        """
        if include_all_statuses:
            qs = Membership.objects.filter(user=user)
        elif include_pending_approval:
            from apps.core.constants import MembershipStatus

            qs = Membership.objects.filter(
                user=user,
                is_deleted=False,
                status__in=[MembershipStatus.ACTIVE, MembershipStatus.PENDING_APPROVAL],
            )
        else:
            qs = Membership.objects.active().filter(user=user)

        if status:
            qs = qs.filter(status=status)

        return qs.select_related("role").order_by("-joined_at")

    @staticmethod
    def get_owner_membership(
        *, account_type: str, account_id: UUID
    ) -> Membership | None:
        """
        Get the owner membership for an account.

        Returns:
            Owner membership or None if no owner exists
        """
        return (
            Membership.objects.filter(
                account_type=account_type,
                account_id=account_id,
                is_owner=True,
            )
            .select_related("role", "user")
            .first()
        )

    @staticmethod
    def is_user_member_of_account(*, user, account_type: str, account_id: UUID) -> bool:
        """Check if user is an active member of an account."""
        return (
            Membership.objects.active()
            .filter(
                user=user,
                account_type=account_type,
                account_id=account_id,
            )
            .exists()
        )

    @staticmethod
    def is_user_owner_of_account(*, user, account_type: str, account_id: UUID) -> bool:
        """Check if user is the owner of an account."""
        return Membership.objects.filter(
            user=user,
            account_type=account_type,
            account_id=account_id,
            is_owner=True,
        ).exists()

    @staticmethod
    def get_users_with_permission(
        *,
        account_type: str,
        account_id: UUID,
        permission_code: str,
    ) -> list:
        """
        Get all active users who have a specific permission in an account.

        Uses ORM join: Membership -> Role -> RolePermission -> Permission.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        user_ids = (
            Membership.objects.active()
            .filter(
                account_type=account_type,
                account_id=account_id,
                role__role_permissions__permission__code=permission_code,
            )
            .values_list("user_id", flat=True)
            .distinct()
        )

        return list(User.objects.filter(id__in=user_ids, is_active=True))

    @staticmethod
    def list_all_members(
        *,
        account_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> QuerySet[Membership]:
        """
        Global member listing for governance.
        Searches across ALL accounts. Filters by account_type, status, search.
        Search: email, username, first_name, last_name (case-insensitive).
        """
        from django.db.models import Q

        if include_deleted:
            qs = Membership.all_objects.all()
        else:
            qs = Membership.objects.all()

        if account_type:
            qs = qs.filter(account_type=account_type)

        if status:
            qs = qs.filter(status=status)

        if search:
            qs = qs.filter(
                Q(user__email__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__profile__first_name__icontains=search)
                | Q(user__profile__last_name__icontains=search)
            )

        return qs.select_related("role", "user").order_by("-joined_at")

    @staticmethod
    def get_membership_by_id_global(*, membership_id: UUID) -> Membership:
        """
        Get any membership by ID (governance view, include all statuses).
        Uses all_objects to include soft-deleted memberships.

        Raises:
            NotFound: If membership doesn't exist
        """
        try:
            return Membership.all_objects.select_related("role", "user").get(
                id=membership_id
            )
        except Membership.DoesNotExist:
            raise NotFound(
                message="Membership not found",
                resource="Membership",
                resource_id=membership_id,
            )
