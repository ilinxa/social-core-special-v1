# apps/rbac/services.py
"""
RBAC Service - Core business logic for role-based access control.

Key methods:
- build_actor_context: Create ActorContext from membership
- initialize_platform_account: Create platform predefined roles
- initialize_business_account: Create business roles + owner membership
- create_membership: Create new member with role
- change_member_role: Change member's role
- update_membership_status: Suspend/ban/remove member
- member_leave: Member voluntarily leaves
- transfer_ownership: Transfer account ownership (stub for Transaction system)
- create_custom_role: Create custom role
- delete_role: Delete custom role
- add_permission_to_role: Add permission to role
- remove_permission_from_role: Remove permission from role
"""

from typing import Tuple
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.core.constants import AccountType, MembershipStatus, PermissionScope
from apps.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from apps.core.observability import AuditService, get_logger
from apps.core.observability.audit.models import AuditLog
from apps.core.types import ActorContext
from apps.core.utils.request import get_client_ip
from apps.rbac.models import Membership, Permission, Role, RolePermission
from apps.rbac.policies import MembershipPolicy, RolePolicy
from apps.rbac.selectors import MembershipSelector, PermissionSelector, RoleSelector

logger = get_logger(__name__)
User = get_user_model()


def _resolve_actor(actor_context: ActorContext):
    """
    Resolve User object from ActorContext for audit logging.

    Returns None if user_id is None or user not found.
    This is a lightweight helper to fix the issue of passing UUID to AuditService.log.
    """
    if not actor_context or not actor_context.user_id:
        return None
    try:
        return User.objects.get(id=actor_context.user_id)
    except User.DoesNotExist:
        return None


class RBACService:
    """
    Core RBAC service for permission, role, and membership management.
    """

    # =========================================================================
    # ACTOR CONTEXT BUILDER
    # =========================================================================

    @staticmethod
    def build_actor_context(*, membership: Membership, request=None) -> ActorContext:
        """
        Build ActorContext from membership with resolved permissions + scope.

        PRECONDITION: Membership must be ACTIVE. Raises PermissionDenied if not.

        This is the ONLY method that should create ActorContext from membership.
        Other systems should call this, not construct ActorContext directly from
        RBAC models.

        Args:
            membership: The membership to build context from
            request: Optional HTTP request for IP/user-agent

        Returns:
            ActorContext with resolved permissions

        Raises:
            PermissionDenied: If membership is not active
        """
        if membership.status != MembershipStatus.ACTIVE:
            raise PermissionDenied(
                message="Membership is not active",
                action="build_context",
            )

        # Permission resolution happens here - cacheable in selector
        # Returns List[Tuple[str, str]] = [(code, scope), ...]
        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id
        )

        return ActorContext(
            user_id=membership.user_id,
            account_type=membership.account_type,
            account_id=membership.account_id,
            membership_id=membership.id,
            role_id=membership.role_id,
            role_name=membership.role.name,
            role_level=membership.role.level,
            is_owner=membership.is_owner,
            permissions_snapshot=permissions,
            captured_at=timezone.now(),
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get("HTTP_USER_AGENT") if request else None,
        )

    # =========================================================================
    # ACCOUNT INITIALIZATION
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def initialize_platform_account(*, platform_id: UUID) -> None:
        """
        Create predefined platform roles and seed their permissions.
        Called from a data migration after platform singleton is created.

        Creates:
        - Platform Owner (level 0): All permissions (all scopes)
        - Platform Admin (level 2): Configurable platform + global permissions
        - Global Moderator (level 5): Global-scope cross-account permissions
        - Base Member (level 10): No permissions (safe fallback)
        """
        logger.info("rbac.platform.initialize.start", platform_id=str(platform_id))

        all_permissions = Permission.objects.all()

        # --- Platform Owner (level 0) ---
        owner_role = Role.objects.create(
            name="Platform Owner",
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
            level=0,
            is_system_role=True,
            description="Full platform authority with all permissions",
        )
        # Owner gets ALL permissions with their broadest applicable scope
        owner_role_perms = []
        for perm in all_permissions:
            # Prefer platform_and_global > global_only > platform_only > business
            if "platform_and_global" in perm.applicable_scopes:
                scope = PermissionScope.PLATFORM_AND_GLOBAL
            elif "global_only" in perm.applicable_scopes:
                scope = PermissionScope.GLOBAL_ONLY
            elif "platform_only" in perm.applicable_scopes:
                scope = PermissionScope.PLATFORM_ONLY
            else:
                scope = PermissionScope.BUSINESS
            owner_role_perms.append(
                RolePermission(role=owner_role, permission=perm, scope=scope)
            )
        RolePermission.objects.bulk_create(owner_role_perms)

        # --- Platform Admin (level 2) ---
        admin_role = Role.objects.create(
            name="Platform Admin",
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
            level=2,
            is_system_role=False,  # Modifiable - permissions can be adjusted
            description="Platform administrator with configurable permissions",
        )
        # Admin gets platform_only scoped permissions (no global cross-account by default)
        admin_perms = PermissionSelector.get_permissions_by_scope(scope="platform_only")
        RolePermission.objects.bulk_create(
            [
                RolePermission(
                    role=admin_role,
                    permission=perm,
                    scope=PermissionScope.PLATFORM_ONLY,
                )
                for perm in admin_perms
            ]
        )

        # --- Global Moderator (level 5) ---
        mod_role = Role.objects.create(
            name="Global Moderator",
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
            level=5,
            is_system_role=False,  # Modifiable - permissions can be adjusted
            description="Cross-account moderation capabilities",
        )
        # Moderator gets global_only scoped permissions (cross-account moderation)
        global_perms = PermissionSelector.get_permissions_by_scope(scope="global_only")
        RolePermission.objects.bulk_create(
            [
                RolePermission(
                    role=mod_role,
                    permission=perm,
                    scope=PermissionScope.GLOBAL_ONLY,
                )
                for perm in global_perms
            ]
        )

        # --- Base Member (level 10) ---
        Role.objects.create(
            name="Base Member",
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
            level=10,
            is_system_role=True,
            description="Basic member with no special permissions",
        )

        logger.info(
            "rbac.platform.initialize.complete",
            platform_id=str(platform_id),
            roles_created=4,
        )

    @staticmethod
    @transaction.atomic
    def initialize_business_account(
        *, business_id: UUID, owner, request=None
    ) -> Membership:
        """
        Create business roles and owner membership.
        Called when a new business is created.

        Creates:
        - Owner role (level 0): All business-scope permissions
        - Base Member role (level 10): No permissions

        Args:
            business_id: UUID of the new business
            owner: User who will be the owner
            request: Optional HTTP request for audit context

        Returns:
            Owner membership
        """
        logger.info("rbac.business.initialize.start", business_id=str(business_id))

        # Create Owner role (level 0)
        owner_role = Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=business_id,
            level=0,
            is_system_role=True,
            description="Business owner with full authority",
        )

        # Create Base Member role (level 10)
        Role.objects.create(
            name="Base Member",
            account_type=AccountType.BUSINESS,
            account_id=business_id,
            level=10,
            is_system_role=True,
            description="Basic member with no special permissions",
        )

        # Seed Owner role permissions (all business-scope permissions)
        business_permissions = PermissionSelector.get_permissions_by_scope(
            scope="business"
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(
                    role=owner_role,
                    permission=perm,
                    scope=PermissionScope.BUSINESS,
                )
                for perm in business_permissions
            ]
        )

        # Create owner membership
        membership = Membership.objects.create(
            user=owner,
            account_type=AccountType.BUSINESS,
            account_id=business_id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )

        logger.info(
            "rbac.owner.membership.created",
            membership_id=str(membership.id),
            business_id=str(business_id),
        )

        AuditService.log(
            action=AuditLog.Action.OWNER_MEMBERSHIP_CREATED,
            actor=owner,
            resource=membership,
            request=request,
        )

        return membership

    # =========================================================================
    # MEMBERSHIP MANAGEMENT
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def create_membership(
        *,
        user,
        account_type: str,
        account_id: UUID,
        role_id: UUID = None,
        created_by=None,
        request=None,
        status: str = None,
    ) -> Membership:
        """
        Create a membership for a user in an account.

        If role_id is None or the role no longer exists, falls back to
        the Base Member role for that account.

        Args:
            user: User to create membership for
            account_type: AccountType value
            account_id: UUID of the account
            role_id: Optional role ID (falls back to Base Member)
            created_by: Optional user who created this membership
            request: Optional HTTP request for audit context

        Returns:
            New membership

        Raises:
            ConflictError: If user is already a member
            BusinessRuleViolation: If account has reached member quota
        """
        # Quota enforcement
        active_count = MembershipSelector.count_active_members(
            account_type=account_type,
            account_id=account_id,
        )
        if account_type == AccountType.BUSINESS:
            from apps.organization.business.models import BusinessAccount

            max_members = BusinessAccount.objects.values_list(
                "max_members",
                flat=True,
            ).get(id=account_id)
        elif account_type == AccountType.PLATFORM:
            from apps.organization.platform.models import PlatformAccount

            max_members = PlatformAccount.objects.values_list(
                "max_members",
                flat=True,
            ).get(id=account_id)
        else:
            max_members = 0

        if max_members > 0 and active_count >= max_members:
            raise BusinessRuleViolation(
                message=f"Account has reached its maximum member limit ({max_members})",
                rule="member_quota_exceeded",
            )

        # Check for existing membership
        existing = MembershipSelector.get_membership_for_user_account(
            user=user,
            account_type=account_type,
            account_id=account_id,
        )
        if existing and existing.status != MembershipStatus.REMOVED:
            raise ConflictError(
                message="User is already a member of this account",
                resource="Membership",
                conflict_type="duplicate",
            )

        # Resolve role with fallback
        role = None
        if role_id:
            try:
                role = Role.objects.get(
                    id=role_id,
                    account_type=account_type,
                    account_id=account_id,
                )
            except Role.DoesNotExist:
                logger.warning(
                    "rbac.membership.role_not_found_fallback",
                    role_id=str(role_id),
                )

        if not role:
            # Fallback: Base Member role
            role = RoleSelector.get_base_member_role(
                account_type=account_type,
                account_id=account_id,
            )

        if existing and existing.status == MembershipStatus.REMOVED:
            # Reactivate removed membership with new role
            existing.status = status or MembershipStatus.ACTIVE
            existing.role = role
            existing.status_changed_at = timezone.now()
            existing.status_changed_by = created_by
            existing.status_reason = ""
            existing.save(
                update_fields=[
                    "status",
                    "role",
                    "status_changed_at",
                    "status_changed_by",
                    "status_reason",
                    "updated_at",
                ]
            )

            PermissionSelector.invalidate_membership_permissions(
                membership_id=existing.id,
            )

            logger.info(
                "rbac.membership.reactivated_from_removed",
                membership_id=str(existing.id),
                user_id=str(user.id),
                account_type=account_type,
                account_id=str(account_id),
            )

            AuditService.log(
                action=AuditLog.Action.MEMBERSHIP_REACTIVATED,
                actor=created_by or user,
                resource=existing,
                request=request,
            )

            return existing

        effective_status = status or MembershipStatus.ACTIVE
        membership = Membership.objects.create(
            user=user,
            account_type=account_type,
            account_id=account_id,
            role=role,
            is_owner=False,
            status=effective_status,
        )

        logger.info(
            "rbac.membership.created",
            membership_id=str(membership.id),
            user_id=str(user.id),
            account_type=account_type,
            account_id=str(account_id),
        )

        AuditService.log(
            action=AuditLog.Action.MEMBERSHIP_CREATED,
            actor=created_by or user,
            resource=membership,
            request=request,
        )

        return membership

    @staticmethod
    @transaction.atomic
    def change_member_role(
        *,
        membership_id: UUID,
        new_role_id: UUID,
        actor_context: ActorContext,
        request=None,
    ) -> Membership:
        """
        Change a member's role.

        Args:
            membership_id: UUID of the membership to modify
            new_role_id: UUID of the new role
            actor_context: Actor's context for authorization
            request: Optional HTTP request for audit context

        Returns:
            Updated membership

        Raises:
            NotFound: If membership or role doesn't exist
            PermissionDenied: If not authorized
        """
        membership = MembershipSelector.get_membership_by_id(
            membership_id=membership_id
        )
        new_role = RoleSelector.get_role_by_id(role_id=new_role_id)

        # Authorize the action
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=membership,
            required_permission="can_change_member_role",
        )

        # Validate role assignment
        MembershipPolicy.validate_role_assignment(
            actor_context=actor_context,
            new_role=new_role,
            target_membership=membership,
        )

        old_role = membership.role
        membership.role = new_role
        membership.save(update_fields=["role", "updated_at"])

        # Invalidate cached permissions
        PermissionSelector.invalidate_membership_permissions(
            membership_id=membership_id
        )

        logger.info(
            "rbac.membership.role_changed",
            membership_id=str(membership_id),
            old_role=old_role.name,
            new_role=new_role.name,
        )

        AuditService.log(
            action=AuditLog.Action.MEMBERSHIP_ROLE_CHANGED,
            actor=_resolve_actor(actor_context),
            resource=membership,
            request=request,
            changes={
                "old_role_id": str(old_role.id),
                "old_role_name": old_role.name,
                "new_role_id": str(new_role.id),
                "new_role_name": new_role.name,
            },
        )

        return membership

    @staticmethod
    @transaction.atomic
    def update_membership_status(
        *,
        membership_id: UUID,
        new_status: str,
        actor_context: ActorContext,
        reason: str = "",
        request=None,
    ) -> Membership:
        """
        Update a member's status (suspend/ban/remove/reactivate).

        Args:
            membership_id: UUID of the membership to modify
            new_status: New MembershipStatus value
            actor_context: Actor's context for authorization
            reason: Optional reason for status change
            request: Optional HTTP request for audit context

        Returns:
            Updated membership

        Raises:
            NotFound: If membership doesn't exist
            PermissionDenied: If not authorized
        """
        membership = MembershipSelector.get_membership_by_id(
            membership_id=membership_id
        )

        # Determine required permission based on status change
        status_permission_map = {
            MembershipStatus.SUSPENDED: "can_suspend_member",
            MembershipStatus.BANNED: "can_ban_member",
            MembershipStatus.REMOVED: "can_remove_member",
            MembershipStatus.ACTIVE: "can_suspend_member",  # Reactivation uses suspend permission
        }
        required_permission = status_permission_map.get(
            new_status, "can_suspend_member"
        )

        # Authorize the action
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=membership,
            required_permission=required_permission,
        )

        old_status = membership.status
        membership.status = new_status
        membership.status_changed_at = timezone.now()
        membership.status_changed_by_id = actor_context.user_id
        membership.status_reason = reason
        membership.save(
            update_fields=[
                "status",
                "status_changed_at",
                "status_changed_by",
                "status_reason",
                "updated_at",
            ]
        )

        # Invalidate cached permissions
        PermissionSelector.invalidate_membership_permissions(
            membership_id=membership_id
        )

        # Determine audit action based on new status
        status_action_map = {
            MembershipStatus.SUSPENDED: AuditLog.Action.MEMBERSHIP_SUSPENDED,
            MembershipStatus.BANNED: AuditLog.Action.MEMBERSHIP_BANNED,
            MembershipStatus.REMOVED: AuditLog.Action.MEMBERSHIP_REMOVED,
            MembershipStatus.ACTIVE: AuditLog.Action.MEMBERSHIP_REACTIVATED,
        }
        audit_action = status_action_map.get(
            new_status, AuditLog.Action.MEMBERSHIP_UPDATED
        )

        logger.info(
            "rbac.membership.status_changed",
            membership_id=str(membership_id),
            old_status=old_status,
            new_status=new_status,
        )

        AuditService.log(
            action=audit_action,
            actor=_resolve_actor(actor_context),
            resource=membership,
            request=request,
            details={"reason": reason} if reason else {},
            changes={
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        return membership

    @staticmethod
    @transaction.atomic
    def member_leave(*, membership_id: UUID, user, request=None) -> Membership:
        """
        Member voluntarily leaves. Owners are blocked.

        Args:
            membership_id: UUID of the membership
            user: User who is leaving (must match membership)
            request: Optional HTTP request for audit context

        Returns:
            Updated membership

        Raises:
            NotFound: If membership doesn't exist
            BusinessRuleViolation: If user is the owner
        """
        membership = MembershipSelector.get_membership_by_id(
            membership_id=membership_id
        )

        # Verify the user owns this membership
        if membership.user_id != user.id:
            raise PermissionDenied(
                message="You can only leave your own membership",
            )

        # Owner cannot leave
        if membership.is_owner:
            raise BusinessRuleViolation(
                message="You are the owner of this account. "
                "Transfer ownership first or delete the account.",
                rule="owner_cannot_leave",
            )

        membership.status = MembershipStatus.LEFT
        membership.status_changed_at = timezone.now()
        membership.status_changed_by = user
        membership.save(
            update_fields=[
                "status",
                "status_changed_at",
                "status_changed_by",
                "updated_at",
            ]
        )

        PermissionSelector.invalidate_membership_permissions(
            membership_id=membership_id
        )

        logger.info(
            "rbac.membership.left",
            membership_id=str(membership_id),
            user_id=str(user.id),
        )

        AuditService.log(
            action=AuditLog.Action.MEMBERSHIP_LEFT,
            actor=user,
            resource=membership,
            request=request,
        )

        return membership

    @staticmethod
    @transaction.atomic
    def restore_membership(
        *, membership_id: UUID, actor_context: ActorContext, request=None
    ) -> Membership:
        """
        Restore a soft-deleted or left/removed membership.

        Args:
            membership_id: UUID of the membership to restore
            actor_context: Actor's context for authorization
            request: Optional HTTP request for audit context

        Returns:
            Restored membership
        """
        # Use all_objects to get deleted memberships
        try:
            membership = Membership.all_objects.select_related("role", "user").get(
                id=membership_id
            )
        except Membership.DoesNotExist:
            raise NotFound(
                message="Membership not found",
                resource="Membership",
                resource_id=membership_id,
            )

        # Check if the membership is actually deleted
        if not membership.is_deleted:
            raise ConflictError(
                message="Membership is not deleted and cannot be restored",
                resource="Membership",
                conflict_type="invalid_state",
            )

        # Authorize the action (skip deleted check since we're restoring)
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=membership,
            required_permission="can_remove_member",  # Same permission for remove/restore
            skip_deleted_check=True,  # Allow action on deleted memberships
        )

        membership.status = MembershipStatus.ACTIVE
        membership.status_changed_at = timezone.now()
        membership.status_changed_by_id = actor_context.user_id
        membership.is_deleted = False
        membership.deleted_at = None
        membership.deleted_by = None
        membership.save()

        logger.info(
            "rbac.membership.restored",
            membership_id=str(membership_id),
        )

        AuditService.log(
            action=AuditLog.Action.MEMBERSHIP_RESTORED,
            actor=_resolve_actor(actor_context),
            resource=membership,
            request=request,
        )

        return membership

    @staticmethod
    @transaction.atomic
    def transfer_ownership(
        *,
        account_type: str,
        account_id: UUID,
        new_owner,
        transferred_by=None,
        request=None,
    ) -> Tuple[Membership, Membership]:
        """
        Transfer ownership of an account to a new owner.

        In a single atomic transaction:
        1. Get current owner membership (is_owner=True for this account)
        2. Get new owner's existing active membership (must already be a member)
        3. Demote old owner: is_owner=False, assign Base Member role
        4. Promote new owner: is_owner=True, assign Owner role (level 0)
        5. Invalidate cached permissions for BOTH memberships
        6. Audit log: OWNERSHIP_TRANSFERRED

        Args:
            account_type: AccountType value
            account_id: UUID of the account
            new_owner: User who will become the new owner
            transferred_by: User who initiated the transfer
            request: HTTP request for audit context

        Returns:
            Tuple of (old_owner_membership, new_owner_membership)
        """
        old_owner_membership = MembershipSelector.get_owner_membership(
            account_type=account_type,
            account_id=account_id,
        )
        if not old_owner_membership:
            raise NotFound(
                message="No owner found for account",
                resource="Membership",
            )

        new_owner_membership = (
            MembershipSelector.get_active_membership_for_user_account(
                user=new_owner,
                account_type=account_type,
                account_id=account_id,
            )
        )
        if not new_owner_membership:
            raise NotFound(
                message="New owner is not an active member of this account",
                resource="Membership",
            )

        owner_role = RoleSelector.get_owner_role(
            account_type=account_type,
            account_id=account_id,
        )
        base_member_role = RoleSelector.get_base_member_role(
            account_type=account_type,
            account_id=account_id,
        )

        # Demote old owner
        old_owner_membership.is_owner = False
        old_owner_membership.role = base_member_role
        old_owner_membership.save(update_fields=["is_owner", "role", "updated_at"])

        # Promote new owner
        new_owner_membership.is_owner = True
        new_owner_membership.role = owner_role
        new_owner_membership.save(update_fields=["is_owner", "role", "updated_at"])

        # Invalidate permission caches
        PermissionSelector.invalidate_membership_permissions(
            membership_id=old_owner_membership.id,
        )
        PermissionSelector.invalidate_membership_permissions(
            membership_id=new_owner_membership.id,
        )

        logger.info(
            "rbac.ownership.transferred",
            account_type=account_type,
            account_id=str(account_id),
            old_owner_id=str(old_owner_membership.user_id),
            new_owner_id=str(new_owner_membership.user_id),
        )

        AuditService.log(
            action=AuditLog.Action.OWNERSHIP_TRANSFERRED,
            actor=transferred_by or new_owner,
            resource=new_owner_membership,
            request=request,
            changes={
                "old_owner_id": str(old_owner_membership.user_id),
                "new_owner_id": str(new_owner_membership.user_id),
            },
        )

        return (old_owner_membership, new_owner_membership)

    # =========================================================================
    # ROLE MANAGEMENT
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def create_custom_role(
        *,
        account_type: str,
        account_id: UUID,
        name: str,
        level: int,
        description: str = "",
        actor_context: ActorContext,
        request=None,
    ) -> Role:
        """
        Create a custom role for an account.

        Args:
            account_type: AccountType value
            account_id: UUID of the account
            name: Role name
            level: Role level (1-10, 0 is reserved)
            description: Optional description
            actor_context: Actor's context for authorization
            request: Optional HTTP request for audit context

        Returns:
            New role

        Raises:
            PermissionDenied: If not authorized or invalid level
            ConflictError: If role name already exists
        """
        # Check permission first
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,  # No target - checking actor's permission
            required_permission="can_create_role",
        )

        # Validate level constraints
        RolePolicy.can_create_role(actor_context=actor_context, level=level)

        # Check for duplicate name
        if Role.objects.filter(
            account_type=account_type,
            account_id=account_id,
            name=name,
        ).exists():
            raise ConflictError(
                message=f"A role named '{name}' already exists",
                resource="Role",
                conflict_type="duplicate",
            )

        role = Role.objects.create(
            name=name,
            account_type=account_type,
            account_id=account_id,
            level=level,
            is_system_role=False,
            description=description,
            created_by_id=actor_context.user_id,
        )

        logger.info(
            "rbac.role.created",
            role_id=str(role.id),
            name=name,
            level=level,
        )

        AuditService.log(
            action=AuditLog.Action.ROLE_CREATED,
            actor=_resolve_actor(actor_context),
            resource=role,
            request=request,
        )

        return role

    @staticmethod
    @transaction.atomic
    def update_role(
        *,
        role_id: UUID,
        name: str = None,
        description: str = None,
        actor_context: ActorContext,
        request=None,
    ) -> Role:
        """
        Update a custom role.

        Args:
            role_id: UUID of the role to update
            name: New name (optional)
            description: New description (optional)
            actor_context: Actor's context for authorization
            request: Optional HTTP request for audit context

        Returns:
            Updated role

        Raises:
            NotFound: If role doesn't exist
            PermissionDenied: If not authorized or system role
        """
        role = RoleSelector.get_role_by_id(role_id=role_id)

        # Check permission first
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,  # No target - checking actor's permission
            required_permission="can_edit_role",
        )

        # Validate role-level constraints (system role, level check)
        RolePolicy.can_modify_role(actor_context=actor_context, role=role)

        changes = {}
        if name is not None and name != role.name:
            # Check for duplicate name
            if (
                Role.objects.filter(
                    account_type=role.account_type,
                    account_id=role.account_id,
                    name=name,
                )
                .exclude(id=role_id)
                .exists()
            ):
                raise ConflictError(
                    message=f"A role named '{name}' already exists",
                    resource="Role",
                    conflict_type="duplicate",
                )
            changes["old_name"] = role.name
            changes["new_name"] = name
            role.name = name

        if description is not None and description != role.description:
            changes["old_description"] = role.description
            changes["new_description"] = description
            role.description = description

        if changes:
            role.updated_by_id = actor_context.user_id
            # Build update_fields dynamically based on what changed
            update_fields = ["updated_by_id", "updated_at"]
            if "new_name" in changes:
                update_fields.append("name")
            if "new_description" in changes:
                update_fields.append("description")
            role.save(update_fields=update_fields)

            logger.info(
                "rbac.role.updated",
                role_id=str(role_id),
                changes=changes,
            )

            AuditService.log(
                action=AuditLog.Action.ROLE_UPDATED,
                actor=_resolve_actor(actor_context),
                resource=role,
                request=request,
                changes=changes,
            )

        return role

    @staticmethod
    @transaction.atomic
    def delete_role(
        *, role_id: UUID, actor_context: ActorContext, request=None
    ) -> None:
        """
        Delete a custom role. Blocked if role has active members.

        Args:
            role_id: UUID of the role to delete
            actor_context: Actor's context for authorization
            request: Optional HTTP request for audit context

        Raises:
            NotFound: If role doesn't exist
            PermissionDenied: If not authorized or system role
            BusinessRuleViolation: If role has active members
        """
        role = RoleSelector.get_role_by_id(role_id=role_id)

        # Check permission first
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=None,  # No target - checking actor's permission
            required_permission="can_delete_role",
        )

        # Validate role-level constraints (system role, level check)
        RolePolicy.can_delete_role(actor_context=actor_context, role=role)

        # Check for active members
        active_count = Membership.objects.active().filter(role_id=role_id).count()
        if active_count > 0:
            raise BusinessRuleViolation(
                message=f"Cannot delete role: {active_count} active member(s) assigned. "
                "Reassign members to a different role first.",
                rule="role_has_active_members",
            )

        # Pass None for user since we track the actor in audit log
        # soft_delete expects a User object, not a UUID
        role.soft_delete(user=None)

        logger.info(
            "rbac.role.deleted",
            role_id=str(role_id),
            name=role.name,
        )

        AuditService.log(
            action=AuditLog.Action.ROLE_DELETED,
            actor=_resolve_actor(actor_context),
            resource=role,
            request=request,
        )

    # =========================================================================
    # PERMISSION MANAGEMENT
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def add_permission_to_role(
        *,
        role_id: UUID,
        permission_id: UUID,
        scope: str,
        actor_context: ActorContext = None,
        request=None,
    ) -> RolePermission:
        """
        Add permission to role. Validates scope against permission's applicable_scopes.

        Args:
            role_id: UUID of the role
            permission_id: UUID of the permission
            scope: PermissionScope value
            actor_context: Optional actor context for authorization
            request: Optional HTTP request for audit context

        Returns:
            New RolePermission

        Raises:
            NotFound: If role or permission doesn't exist
            ValidationError: If scope is not valid for the permission
            ConflictError: If permission already assigned to role
        """
        RoleSelector.get_role_by_id(role_id=role_id)
        permission = PermissionSelector.get_permission_by_id(
            permission_id=permission_id
        )

        # Validate scope
        if scope not in permission.applicable_scopes:
            raise ValidationError(
                message=f"Scope '{scope}' is not valid for permission '{permission.code}'. "
                f"Valid scopes: {permission.applicable_scopes}",
                field="scope",
            )

        # Check for existing assignment
        if RolePermission.objects.filter(
            role_id=role_id, permission_id=permission_id
        ).exists():
            raise ConflictError(
                message=f"Permission '{permission.code}' is already assigned to this role",
                resource="RolePermission",
                conflict_type="duplicate",
            )

        role_permission = RolePermission.objects.create(
            role_id=role_id,
            permission_id=permission_id,
            scope=scope,
        )

        # Invalidate all memberships with this role
        PermissionSelector.invalidate_role_permissions(role_id=role_id)

        logger.info(
            "rbac.role.permission_added",
            role_id=str(role_id),
            permission_code=permission.code,
            scope=scope,
        )

        if actor_context:
            AuditService.log(
                action=AuditLog.Action.ROLE_PERMISSION_ADDED,
                actor=_resolve_actor(actor_context),
                resource=role_permission,
                request=request,
                details={
                    "permission_code": permission.code,
                    "scope": scope,
                },
            )

        return role_permission

    @staticmethod
    @transaction.atomic
    def remove_permission_from_role(
        *,
        role_id: UUID,
        permission_id: UUID,
        actor_context: ActorContext = None,
        request=None,
    ) -> None:
        """
        Remove permission from role.

        Args:
            role_id: UUID of the role
            permission_id: UUID of the permission
            actor_context: Optional actor context for authorization
            request: Optional HTTP request for audit context

        Raises:
            NotFound: If role permission assignment doesn't exist
        """
        role = RoleSelector.get_role_by_id(role_id=role_id)
        permission = PermissionSelector.get_permission_by_id(
            permission_id=permission_id
        )

        try:
            role_permission = RolePermission.objects.get(
                role_id=role_id,
                permission_id=permission_id,
            )
        except RolePermission.DoesNotExist:
            raise NotFound(
                message=f"Permission '{permission.code}' is not assigned to this role",
                resource="RolePermission",
            )

        role_permission.delete()

        # Invalidate all memberships with this role
        PermissionSelector.invalidate_role_permissions(role_id=role_id)

        logger.info(
            "rbac.role.permission_removed",
            role_id=str(role_id),
            permission_code=permission.code,
        )

        if actor_context:
            AuditService.log(
                action=AuditLog.Action.ROLE_PERMISSION_REMOVED,
                actor=_resolve_actor(actor_context),
                resource=role,
                request=request,
                details={
                    "permission_code": permission.code,
                },
            )
