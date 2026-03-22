# apps/rbac/models.py
"""
RBAC Models - Permission, Role, RolePermission, Membership

Critical Invariants:
- One owner per account (DB-enforced via unique partial constraint)
- One membership per user per account (DB-enforced)
- Level 0 reserved for Owner roles only (service-enforced)
- is_owner flag is source of truth for ownership (not role)
"""

from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

from apps.core.constants import AccountType, MembershipStatus, PermissionScope
from apps.core.models import AuditModel, SoftDeleteManager, UUIDModel


class Permission(UUIDModel):
    """
    Predefined permission capability.

    Permissions are developer-defined and cannot be created by businesses.
    They represent atomic capabilities that can be bundled into roles.

    INVARIANT: Permissions are immutable after creation (seeded via migration).
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Machine-readable permission code (e.g., 'can_invite_member')",
    )
    name = models.CharField(max_length=255, help_text="Human-readable permission name")
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed description of what this permission allows",
    )
    category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Permission category (e.g., 'membership', 'content', 'settings')",
    )
    applicable_scopes = models.JSONField(
        default=list,
        help_text="List of valid PermissionScope values for this permission",
    )

    class Meta:
        db_table = "rbac_permission"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["category", "code"]

    def __str__(self):
        return f"{self.code} ({self.category})"


class Role(UUIDModel, AuditModel):
    """
    Role definition with permissions bundle.

    INVARIANT: Level 0 is reserved for Owner roles only.
    INVARIANT: System roles (is_system_role=True) cannot be modified or deleted.
    """

    name = models.CharField(max_length=100)
    # NOTE: account_id is UUIDField - any model used as an account MUST have a UUID PK.
    # Currently: BusinessAccount.id (UUID), PlatformAccount.id (UUID)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, db_index=True
    )
    account_id = models.UUIDField(db_index=True)
    level = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(10)],
        help_text="Authority level (0=owner, 10=lowest)",
    )
    is_system_role = models.BooleanField(
        default=False, help_text="System roles cannot be modified or deleted"
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "rbac_role"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["account_type", "account_id", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_role_name_per_account",
            ),
        ]
        indexes = [
            models.Index(fields=["account_type", "account_id"]),
            models.Index(fields=["account_type", "account_id", "level"]),
        ]

    def __str__(self):
        return f"{self.name} (Level {self.level})"


class RolePermission(UUIDModel):
    """
    Assignment of permission to role with scope.

    The scope determines the REACH of this permission when exercised:
    - business: Only within the business where the role is assigned
    - platform_only: Only within the platform account
    - global_only: Cross-account (e.g., platform staff acting on businesses)
    - platform_and_global: Both platform-internal and cross-account

    VALIDATION: scope must be in the Permission's applicable_scopes list.
    This is enforced in the service layer (RBACService.add_permission_to_role).
    """

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_permissions"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_assignments"
    )
    scope = models.CharField(
        max_length=30, choices=PermissionScope.choices, default=PermissionScope.BUSINESS
    )

    class Meta:
        db_table = "rbac_role_permission"
        verbose_name = "Role Permission"
        verbose_name_plural = "Role Permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="unique_permission_per_role"
            ),
        ]

    # NOTE: Scope validation (scope must be in permission.applicable_scopes) is
    # enforced in RBACService.add_permission_to_role(), NOT at the model level.
    # Django's clean() does not run on objects.create(), so model-level validation
    # would give a false sense of safety.

    def __str__(self):
        return f"{self.role.name} -> {self.permission.code} ({self.scope})"


class MembershipManager(SoftDeleteManager):
    """
    Manager for Membership with common query patterns.
    Inherits from SoftDeleteManager to automatically filter is_deleted=False.
    """

    def active(self):
        """Return only active memberships."""
        return self.get_queryset().filter(status=MembershipStatus.ACTIVE)

    def for_account(self, *, account_type: str, account_id):
        """Return active memberships for a specific account."""
        return self.active().filter(account_type=account_type, account_id=account_id)

    def for_user(self, *, user):
        """Return active memberships for a specific user."""
        return self.active().filter(user=user)


class Membership(UUIDModel, AuditModel):
    """
    Connection between User and Account with Role assignment.

    INVARIANT: Only one owner per account (is_owner=True).
    INVARIANT: Only one membership per user per account.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    # NOTE: account_id is UUIDField - see Role model note about UUID PK requirement.
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, db_index=True
    )
    account_id = models.UUIDField(db_index=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    is_owner = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this member is the account owner",
    )
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membership_status_changes",
    )
    status_reason = models.TextField(
        blank=True, default="", help_text="Reason for status change (e.g., ban reason)"
    )

    objects = MembershipManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "rbac_membership"
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"
        ordering = ["-joined_at"]
        constraints = [
            # Only one owner per account (among non-deleted memberships)
            models.UniqueConstraint(
                fields=["account_type", "account_id"],
                condition=models.Q(is_owner=True, is_deleted=False),
                name="unique_owner_per_account",
            ),
            # Only one membership per user per account (among non-deleted)
            models.UniqueConstraint(
                fields=["user", "account_type", "account_id"],
                condition=models.Q(is_deleted=False),
                name="unique_membership_per_user_account",
            ),
        ]
        indexes = [
            models.Index(fields=["account_type", "account_id", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["account_type", "account_id", "is_owner"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.role.name}"
