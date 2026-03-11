# apps/rbac/policies.py
"""
RBAC Policies - Authorization logic for membership and role actions.

Implements the two-plane authority model:

Business Plane - Authority within a single business account:
- Business Owner (level 0) -> custom roles (levels 1-9) -> Base Member (level 10)
- Dominance rule: actor.role.level < target.role.level
- Business Owner is invincible within this plane

Platform Plane - Authority over the entire platform:
- Platform Owner (level 0) -> Platform Admin (level 2) -> Global Moderator (level 5)
- Global-scoped permissions can act on ANY business member
- Dominance rule applies within platform, but is SKIPPED for cross-account actions
- Platform Owner is the only truly invincible entity in the system

Cross-plane rule:
When platform member acts on business member using global permission,
the business-plane dominance rule is SKIPPED. Authority comes from
the platform role and global permission, not from any business membership.
"""

from apps.core.exceptions import PermissionDenied
from apps.core.constants import AccountType, MembershipStatus
from apps.core.types import ActorContext
from apps.rbac.models import Membership, Role


class MembershipPolicy:
    """
    Authorization logic for membership actions.

    Implements the permission check algorithm from the RBAC plan v2.1.
    """

    @staticmethod
    def authorize_action(
        *,
        actor_context: ActorContext,
        target_membership: Membership = None,
        required_permission: str,
        skip_deleted_check: bool = False,
    ) -> None:
        """
        Authorize an action. Raises PermissionDenied if not allowed.

        Args:
            actor_context: The actor's context with resolved permissions
            target_membership: The membership being acted upon (optional)
            required_permission: The permission code required for the action
            skip_deleted_check: If True, skip the is_deleted check (for restore operations)

        Raises:
            PermissionDenied: If the action is not authorized

        Algorithm:
            1. Actor membership must be ACTIVE (enforced by build_actor_context)
            2. Determine if same-account or cross-account action
            3. Resolve permission with appropriate scope
            4. Target checks: owner invincibility, dominance rule
        """
        # STEP 1: Actor membership must be ACTIVE
        # (Already enforced by build_actor_context, but belt-and-suspenders)
        if actor_context.membership_id is None:
            raise PermissionDenied(message="No active membership context")

        # STEP 2: Determine context
        if target_membership is None:
            same_account = True
        else:
            same_account = (
                actor_context.account_type == target_membership.account_type
                and str(actor_context.account_id) == str(target_membership.account_id)
            )

        # STEP 3: Resolve permission with scope
        if same_account:
            # For same-account actions, accept any scope match
            has_perm = actor_context.has_permission(required_permission)
        else:
            # For cross-account actions, ONLY global scope counts
            has_perm = actor_context.has_global_permission(required_permission)

        if not has_perm:
            raise PermissionDenied(
                message=f"Missing required permission: {required_permission}",
                action=required_permission,
            )

        # STEP 4: Target checks (only if target exists)
        if target_membership is not None:
            # 4a: Target must be non-deleted membership (unless skip_deleted_check for restore)
            if not skip_deleted_check and target_membership.is_deleted:
                raise PermissionDenied(
                    message="Target membership no longer exists",
                )

            # 4b: Owner invincibility
            if target_membership.is_owner:
                if same_account:
                    # Cannot act on owner within the same account
                    raise PermissionDenied(
                        message="Cannot perform this action on the account owner",
                    )
                if target_membership.account_type == AccountType.PLATFORM:
                    # Platform owner is ALWAYS invincible
                    raise PermissionDenied(
                        message="Cannot perform this action on the platform owner",
                    )
                # Cross-account + business owner: ALLOWED
                # Platform staff CAN act on business owners via global permissions

            # 4c: Dominance rule (same-account only)
            if same_account:
                if actor_context.role_level >= target_membership.role.level:
                    raise PermissionDenied(
                        message="Insufficient authority: your role level does not "
                                "outrank the target member's role",
                    )
            # Cross-account: dominance rule SKIPPED
            # Authority comes from global permission, not relative role levels

    @staticmethod
    def validate_role_assignment(
        *,
        actor_context: ActorContext,
        new_role: Role,
        target_membership: Membership,
    ) -> None:
        """
        Additional validation for role changes.
        Called AFTER authorize_action has passed.

        Args:
            actor_context: The actor's context
            new_role: The role to be assigned
            target_membership: The membership being modified

        Raises:
            PermissionDenied: If role assignment is not allowed
        """
        # Level 0 (Owner) cannot be assigned via role change
        if new_role.level == 0:
            raise PermissionDenied(
                message="Owner role cannot be assigned directly. "
                        "Use ownership transfer instead.",
            )

        # Actor must outrank the role they're assigning
        if actor_context.role_level >= new_role.level:
            raise PermissionDenied(
                message="Cannot assign a role with equal or higher "
                        "authority than your own",
            )

        # Role must belong to the target's account
        if (new_role.account_type != target_membership.account_type
                or new_role.account_id != target_membership.account_id):
            raise PermissionDenied(
                message="Role does not belong to this account",
            )

    @staticmethod
    def get_viewer_permissions(
        *, actor_context: ActorContext, target_membership: Membership,
    ) -> dict:
        """Return permission booleans for the viewer on a membership detail."""

        def _safe_check(permission: str, **kwargs) -> bool:
            try:
                MembershipPolicy.authorize_action(
                    actor_context=actor_context,
                    target_membership=target_membership,
                    required_permission=permission,
                    **kwargs,
                )
                return True
            except PermissionDenied:
                return False

        can_change_role = _safe_check("can_change_member_role")
        can_suspend = _safe_check("can_suspend_member")
        can_remove = _safe_check("can_remove_member")
        can_ban = _safe_check("can_ban_member")

        # Reactivation is only meaningful for non-active, non-deleted members.
        # The service uses can_suspend_member for reactivation to ACTIVE.
        reactivatable = target_membership.status in (
            MembershipStatus.SUSPENDED, MembershipStatus.REMOVED,
        )
        can_reactivate = reactivatable and _safe_check("can_suspend_member")

        return {
            "can_change_role": can_change_role,
            "can_suspend": can_suspend,
            "can_remove": can_remove,
            "can_ban": can_ban,
            "can_reactivate": can_reactivate,
        }


class RolePolicy:
    """
    Authorization logic for role management actions.
    """

    @staticmethod
    def can_create_role(*, actor_context: ActorContext, level: int) -> None:
        """
        Validate role creation.

        Args:
            actor_context: The actor's context
            level: The level of the role to be created

        Raises:
            PermissionDenied: If role creation is not allowed
        """
        # Level 0 is reserved for the Owner role
        if level == 0:
            raise PermissionDenied(
                message="Level 0 is reserved for the Owner role",
            )

        # Actor must outrank the role they're creating
        if actor_context.role_level >= level:
            raise PermissionDenied(
                message="Cannot create a role with equal or higher "
                        "authority than your own",
            )

    @staticmethod
    def can_modify_role(*, actor_context: ActorContext, role: Role) -> None:
        """
        Validate role modification (edit/delete).

        Args:
            actor_context: The actor's context
            role: The role to be modified

        Raises:
            PermissionDenied: If role modification is not allowed
        """
        # System roles cannot be modified
        if role.is_system_role:
            raise PermissionDenied(
                message="System roles cannot be modified",
            )

        # Actor must outrank the role they're modifying
        if actor_context.role_level >= role.level:
            raise PermissionDenied(
                message="Cannot modify a role with equal or higher "
                        "authority than your own",
            )

    @staticmethod
    def can_delete_role(*, actor_context: ActorContext, role: Role) -> None:
        """
        Validate role deletion. Same as modification plus additional checks.

        Args:
            actor_context: The actor's context
            role: The role to be deleted

        Raises:
            PermissionDenied: If role deletion is not allowed
        """
        # Use the same checks as modification
        RolePolicy.can_modify_role(actor_context=actor_context, role=role)

    @staticmethod
    def get_viewer_permissions(
        *, actor_context: ActorContext, role: Role,
    ) -> dict:
        """Return permission booleans for the viewer on a role detail."""

        def _safe_check(fn, **kwargs) -> bool:
            try:
                fn(actor_context=actor_context, role=role, **kwargs)
                return True
            except PermissionDenied:
                return False

        has_modify_perm = actor_context.has_permission("can_create_role")
        can_edit = has_modify_perm and _safe_check(RolePolicy.can_modify_role)
        can_delete = has_modify_perm and _safe_check(RolePolicy.can_delete_role)
        can_modify_permissions = can_edit

        return {
            "can_edit": can_edit,
            "can_delete": can_delete,
            "can_modify_permissions": can_modify_permissions,
        }
