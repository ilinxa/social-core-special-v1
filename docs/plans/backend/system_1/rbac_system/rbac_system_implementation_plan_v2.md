# RBAC System Implementation Plan (Revised)

## Multi-Tenant Platform - System 3 of 4

**Version:** 2.0
**Date:** February 10, 2026
**Status:** Ready for Implementation

> **v2.0 Changes (comprehensive revision):**
> - Fixed: Permission snapshot now carries scope (was flat list of codes, cross-account checks were broken)
> - Fixed: Explicit two-plane authority model (platform plane vs business plane) with defined cross-plane rules
> - Fixed: Owner invincibility scoped correctly (business owners invincible within business, not against platform)
> - Fixed: Owner cannot leave without transferring ownership
> - Fixed: Membership status checked as precondition before permission resolution
> - Fixed: Role deletion blocked when role has active members (no zombie permissions)
> - Fixed: Role-level validation on assignment (prevents privilege escalation)
> - Fixed: ActorContext.user_id type corrected to match UUID PK
> - Fixed: get_client_ip imported from existing utility instead of duplicated
> - Retained: All model definitions, DB constraints, app structure, URL routing, integration points from v1.2

---

## Critical Invariants

> **These rules are non-negotiable and enforced at the database level.**

### 1. One Owner Per Account (DB-Enforced)
Each account (platform or business) has exactly **one owner**, enforced by a **unique partial constraint** on `(account_type, account_id)` where `is_owner=True AND is_deleted=False`. This prevents race conditions and ensures ownership clarity.

### 2. One Membership Per User Per Account (DB-Enforced)
A user can have at most one membership per account, enforced by a **unique partial constraint** on `(user, account_type, account_id)` where `is_deleted=False`. No duplicate memberships.

### 3. is_owner Flag is Source of Truth
**Ownership is determined by `Membership.is_owner=True`, NOT by role assignment.** The Owner role grants permissions, but the `is_owner` flag determines invincibility and ownership transfer eligibility.

### 4. Level 0 Reserved for Owner Role
Role levels 0-10 where lower = higher authority. **Level 0 is reserved exclusively for Owner roles** and cannot be assigned to custom roles.

### 5. No Pending Memberships
**Membership records are created ONLY when a user becomes an active member.** Pending states are tracked in the Transaction system, not in Membership.

### 6. Account ID Constraint
**Any model that serves as an "account" MUST use a UUID primary key.** `Membership.account_id` and `Role.account_id` are `UUIDField`. Currently `BusinessAccount.id` and `PlatformAccount.id` are both UUID ✓. Adding a new account type with an integer PK will break these fields on PostgreSQL.

---

## Executive Summary

This plan outlines the implementation of the RBAC (Role-Based Access Control) System, which provides:
- **Permission**: Predefined atomic capabilities
- **Role**: Named bundles of permissions per account, with scope per assignment
- **RolePermission**: Assignment of permissions to roles **with scope** (business, platform_only, global_only, platform_and_global)
- **Membership**: Connection between users and accounts with assigned roles

The system follows the established layered architecture: models → managers → selectors → services → policies → serializers → views → URLs.

---

## 1. Prerequisites

### 1.1 Required Enums (Already in `apps/core/constants.py`)

The following enums already exist from Organization System implementation:

```python
# backend/apps/core/constants.py

class AccountType(models.TextChoices):
    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"

class PermissionScope(models.TextChoices):
    BUSINESS = "business", "Business Only"
    PLATFORM_ONLY = "platform_only", "Platform Only"
    GLOBAL_ONLY = "global_only", "Global Only"
    PLATFORM_AND_GLOBAL = "platform_and_global", "Platform and Global"

class MembershipStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    LEFT = "left", "Left"
    REMOVED = "removed", "Removed"
    BANNED = "banned", "Banned"
    # NOTE: No 'pending' - pending state is in Transaction system
```

### 1.2 New AuditLog Actions

Add to `apps/core/observability/audit/models.py` - `AuditLog.Action` enum:

```python
# RBAC - Roles
ROLE_CREATED = "rbac.role.created", "Role Created"
ROLE_UPDATED = "rbac.role.updated", "Role Updated"
ROLE_DELETED = "rbac.role.deleted", "Role Deleted"
ROLE_PERMISSION_ADDED = "rbac.role.permission_added", "Permission Added to Role"
ROLE_PERMISSION_REMOVED = "rbac.role.permission_removed", "Permission Removed from Role"

# RBAC - Membership
MEMBERSHIP_CREATED = "rbac.membership.created", "Membership Created"
MEMBERSHIP_UPDATED = "rbac.membership.updated", "Membership Updated"
MEMBERSHIP_ROLE_CHANGED = "rbac.membership.role_changed", "Member Role Changed"
MEMBERSHIP_SUSPENDED = "rbac.membership.suspended", "Member Suspended"
MEMBERSHIP_REACTIVATED = "rbac.membership.reactivated", "Member Reactivated"
MEMBERSHIP_REMOVED = "rbac.membership.removed", "Member Removed"
MEMBERSHIP_BANNED = "rbac.membership.banned", "Member Banned"
MEMBERSHIP_LEFT = "rbac.membership.left", "Member Left"
MEMBERSHIP_RESTORED = "rbac.membership.restored", "Member Restored"

# RBAC - Ownership
OWNERSHIP_TRANSFERRED = "rbac.ownership.transferred", "Ownership Transferred"
OWNER_MEMBERSHIP_CREATED = "rbac.owner.created", "Owner Membership Created"
```

### 1.3 ActorContext Structure (Create `apps/core/types.py`)

> **ARCHITECTURAL BOUNDARY**: `ActorContext` is a **pure data structure** in core infrastructure.
> It does NOT import or depend on RBAC models. RBAC is responsible for *constructing* ActorContext
> instances via `RBACService.build_actor_context()`. This separation enables:
> - Permission resolution caching in RBAC layer
> - Clean dependency direction (RBAC → Core, never Core → RBAC)
> - Transaction/Audit systems consume ActorContext without RBAC coupling

```python
# backend/apps/core/types.py

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from django.utils import timezone

# Import from existing utility - DO NOT duplicate
from apps.core.utils.request import get_client_ip


@dataclass
class ActorContext:
    """
    Captures the complete context of an actor at action time.
    Used by: Transaction system, Form Builder, Audit system

    IMPORTANT: This is a pure data structure. Do NOT add methods that
    import or depend on RBAC models. Use RBACService.build_actor_context()
    to create instances from membership records.
    """
    # NOTE: user_id is UUID because User.id is UUIDField (migrated in 0005/0006)
    user_id: Optional[UUID]
    account_type: Optional[str]  # AccountType value
    account_id: Optional[UUID]
    membership_id: Optional[UUID]
    role_id: Optional[UUID]
    role_name: Optional[str]
    role_level: Optional[int]
    is_owner: bool
    # v2.0: Permissions carry scope as (code, scope) tuples
    # e.g. [("can_view_members", "business"), ("can_remove_member", "global_only")]
    permissions_snapshot: List[Tuple[str, str]] = field(default_factory=list)
    captured_at: datetime = field(default_factory=timezone.now)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # --- Convenience permission checks (no RBAC imports needed) ---

    def has_permission(self, code: str) -> bool:
        """Check if actor has a permission (any scope)."""
        return any(c == code for c, _ in self.permissions_snapshot)

    def has_permission_with_scope(self, code: str, scope: str) -> bool:
        """Check if actor has a specific permission with a specific scope."""
        return (code, scope) in self.permissions_snapshot

    def has_global_permission(self, code: str) -> bool:
        """Check if actor has a permission with global or platform_and_global scope."""
        return any(
            c == code and s in ("global_only", "platform_and_global")
            for c, s in self.permissions_snapshot
        )

    def permission_codes(self) -> List[str]:
        """Return flat list of permission codes (for backward compatibility)."""
        return list(set(c for c, _ in self.permissions_snapshot))

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/transmission."""
        return {
            'user_id': str(self.user_id) if self.user_id else None,
            'account_type': self.account_type,
            'account_id': str(self.account_id) if self.account_id else None,
            'membership_id': str(self.membership_id) if self.membership_id else None,
            'role_id': str(self.role_id) if self.role_id else None,
            'role_name': self.role_name,
            'role_level': self.role_level,
            'is_owner': self.is_owner,
            # Store as list of [code, scope] pairs
            'permissions_snapshot': [[c, s] for c, s in self.permissions_snapshot],
            'captured_at': self.captured_at.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ActorContext':
        """Reconstruct from dictionary (for reading from storage)."""
        from datetime import datetime as dt
        perms = data.get('permissions_snapshot', [])
        # Handle both old format (flat list) and new format (list of pairs)
        if perms and isinstance(perms[0], str):
            # Legacy: flat list of codes -> treat as business scope
            parsed_perms = [(code, "business") for code in perms]
        else:
            parsed_perms = [(p[0], p[1]) for p in perms]

        return cls(
            user_id=UUID(data['user_id']) if data.get('user_id') else None,
            account_type=data.get('account_type'),
            account_id=UUID(data['account_id']) if data.get('account_id') else None,
            membership_id=UUID(data['membership_id']) if data.get('membership_id') else None,
            role_id=UUID(data['role_id']) if data.get('role_id') else None,
            role_name=data.get('role_name'),
            role_level=data.get('role_level'),
            is_owner=data.get('is_owner', False),
            permissions_snapshot=parsed_perms,
            captured_at=dt.fromisoformat(data['captured_at']),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent'),
        )

    @classmethod
    def for_user_context(cls, user, request=None) -> 'ActorContext':
        """
        Create ActorContext for user-level actions (no account context).
        Use this for actions that don't require account membership.
        """
        return cls(
            user_id=user.id,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
            captured_at=timezone.now(),
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT') if request else None,
        )

    @classmethod
    def for_anonymous(cls, request=None) -> 'ActorContext':
        """Create ActorContext for anonymous/unauthenticated actions."""
        return cls(
            user_id=None,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
            captured_at=timezone.now(),
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT') if request else None,
        )

    @classmethod
    def for_system(cls) -> 'ActorContext':
        """Create ActorContext for system-initiated actions (Celery tasks, etc.)."""
        return cls(
            user_id=None,
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name='SYSTEM',
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
            captured_at=timezone.now(),
            ip_address=None,
            user_agent=None,
        )
```

### 1.4 ActorContext Builder in RBAC (See Section 5.3)

The RBAC layer provides `RBACService.build_actor_context()` which:
1. Takes a membership record
2. Verifies membership is ACTIVE (precondition)
3. Resolves permissions **with scope** via `PermissionSelector.get_permissions_for_membership()` (cacheable)
4. Returns a fully-constructed `ActorContext`

This keeps permission resolution logic in RBAC where it belongs.

---

## 2. App Structure

```
backend/apps/rbac/
    __init__.py
    apps.py
    models.py               # Permission, Role, RolePermission, Membership
    managers.py             # MembershipManager
    selectors.py            # PermissionSelector, RoleSelector, MembershipSelector
    services.py             # RBACService (core initialization and operations)
    policies.py             # RolePolicy, MembershipPolicy (authorization checks)
    serializers.py          # Input/Output serializers
    views.py                # Role and Membership API views
    urls.py                 # URL routing
    admin.py                # Django Admin configuration

    permissions/
        __init__.py
        registry.py         # Permission registry and data migration helper

    tests/
        __init__.py
        conftest.py         # Shared test fixtures
        factories.py        # Factory-boy factories
        test_models.py
        test_selectors.py
        test_services.py
        test_policies.py
        test_views.py
```

---

## 3. Model Definitions

### 3.1 Permission Model (`apps/rbac/models.py`)

```python
"""
RBAC Models - Permission, Role, RolePermission, Membership
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator
from apps.core.models import UUIDModel, AuditModel
from apps.core.constants import AccountType, PermissionScope, MembershipStatus


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
        help_text="Machine-readable permission code (e.g., 'can_invite_member')"
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable permission name"
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed description of what this permission allows"
    )
    category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Permission category (e.g., 'membership', 'content', 'settings')"
    )
    applicable_scopes = models.JSONField(
        default=list,
        help_text="List of valid PermissionScope values for this permission"
    )

    class Meta:
        db_table = "rbac_permission"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["category", "code"]

    def __str__(self):
        return f"{self.code} ({self.category})"
```

### 3.2 Role Model

```python
class Role(UUIDModel, AuditModel):
    """
    Role definition with permissions bundle.

    INVARIANT: Level 0 is reserved for Owner roles only.
    INVARIANT: System roles (is_system_role=True) cannot be modified or deleted.
    """
    name = models.CharField(max_length=100)
    # NOTE: account_id is UUIDField - any model used as an account MUST have a UUID PK.
    # Currently: BusinessAccount.id (UUID) ✓, PlatformAccount.id (UUID) ✓
    account_type = models.CharField(max_length=20, choices=AccountType.choices, db_index=True)
    account_id = models.UUIDField(db_index=True)
    level = models.PositiveSmallIntegerField(validators=[MaxValueValidator(10)])
    is_system_role = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "rbac_role"
        constraints = [
            models.UniqueConstraint(
                fields=["account_type", "account_id", "name"],
                name="unique_role_name_per_account"
            ),
        ]
        indexes = [
            models.Index(fields=["account_type", "account_id"]),
            models.Index(fields=["account_type", "account_id", "level"]),
        ]

    def __str__(self):
        return f"{self.name} (Level {self.level})"
```

### 3.3 RolePermission Model

```python
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
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_assignments")
    scope = models.CharField(max_length=30, choices=PermissionScope.choices, default=PermissionScope.BUSINESS)

    class Meta:
        db_table = "rbac_role_permission"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="unique_permission_per_role"),
        ]

    def clean(self):
        """Validate scope is in the permission's applicable_scopes."""
        from django.core.exceptions import ValidationError
        if self.permission_id and self.scope not in self.permission.applicable_scopes:
            raise ValidationError(
                f"Scope '{self.scope}' is not valid for permission '{self.permission.code}'. "
                f"Valid scopes: {self.permission.applicable_scopes}"
            )

    def __str__(self):
        return f"{self.role.name} -> {self.permission.code} ({self.scope})"
```

### 3.4 Membership Model

```python
class MembershipManager(models.Manager):
    """Manager for Membership with soft-delete filtering."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def active(self):
        return self.get_queryset().filter(status=MembershipStatus.ACTIVE)

    def for_account(self, *, account_type: str, account_id):
        return self.active().filter(account_type=account_type, account_id=account_id)

    def for_user(self, *, user):
        return self.active().filter(user=user)


class Membership(UUIDModel, AuditModel):
    """
    Connection between User and Account with Role assignment.

    INVARIANT: Only one owner per account (is_owner=True).
    INVARIANT: Only one membership per user per account.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    # NOTE: account_id is UUIDField - see Role model note about UUID PK requirement.
    account_type = models.CharField(max_length=20, choices=AccountType.choices, db_index=True)
    account_id = models.UUIDField(db_index=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    is_owner = models.BooleanField(default=False, db_index=True)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="membership_status_changes")
    status_reason = models.TextField(blank=True, default="")

    objects = MembershipManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "rbac_membership"
        ordering = ["-joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["account_type", "account_id"],
                condition=models.Q(is_owner=True, is_deleted=False),
                name="unique_owner_per_account"
            ),
            models.UniqueConstraint(
                fields=["user", "account_type", "account_id"],
                condition=models.Q(is_deleted=False),
                name="unique_membership_per_user_account"
            ),
        ]
        indexes = [
            models.Index(fields=["account_type", "account_id", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["account_type", "account_id", "is_owner"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.role.name}"
```

---

## 4. Permission Registry

### 4.1 Permission Registry (`apps/rbac/permissions/registry.py`)

Complete list of permissions to seed via data migration:

| Code | Category | Applicable Scopes |
|------|----------|-------------------|
| `can_invite_member` | membership | business, platform_only, global_only |
| `can_remove_member` | membership | business, global_only |
| `can_change_member_role` | membership | business, global_only |
| `can_suspend_member` | membership | business, global_only |
| `can_ban_member` | membership | business, global_only |
| `can_approve_membership_request` | membership | business, platform_only |
| `can_view_members` | membership | business, platform_only, global_only |
| `can_create_role` | roles | business, platform_only |
| `can_edit_role` | roles | business, platform_only |
| `can_delete_role` | roles | business, platform_only |
| `can_edit_business` | settings | business, global_only |
| `can_edit_profile` | settings | business, global_only |
| `can_view_settings` | settings | business, platform_only |
| `can_suspend_business` | platform | global_only |
| `can_remove_business_owner` | platform | global_only |
| `can_transfer_business_ownership` | platform | global_only |
| `can_view_businesses` | platform | global_only, platform_only |
| `can_approve_verification_request` | platform | platform_only, global_only |
| `can_approve_business_creation` | platform | platform_only |
| `can_view_audit_logs` | audit | business, platform_only, global_only, platform_and_global |
| `can_create_form` | forms | business, platform_only |
| `can_edit_form` | forms | business, platform_only, global_only |
| `can_delete_form` | forms | business, platform_only, global_only |
| `can_view_responses` | forms | business, platform_only, global_only |
| `can_export_responses` | forms | business, platform_only, global_only |
| `can_process_response` | forms | business, platform_only, global_only |

### 4.2 Predefined Roles

| Account Type | Role | Level | Permissions | Modifiable |
|--------------|------|-------|-------------|------------|
| Business | Owner | 0 | All business-scope | No |
| Business | Base Member | 10 | None | No |
| Platform | Platform Owner | 0 | All + platform_and_global | No |
| Platform | Platform Admin | 2 | Configurable | Yes |
| Platform | Global Moderator | 5 | Global scope | Yes |

---

## 5. Authority Model and Permission Checking

> **This is the core logic of the RBAC system. Every permission check flows through this model.**

### 5.1 Two Authority Planes

The system operates on two distinct authority planes:

**Business Plane** — Authority within a single business account.
- Business Owner (level 0) → custom roles (levels 1-9) → Base Member (level 10)
- The dominance rule applies: actor.role.level < target.role.level
- Business Owner is invincible within this plane (no business member can act on the owner)

**Platform Plane** — Authority over the entire platform, including cross-account actions.
- Platform Owner (level 0) → Platform Admin (level 2) → Global Moderator (level 5)
- Platform staff with `global_only` or `platform_and_global` scoped permissions can act on ANY business member
- The dominance rule applies within this plane (Platform Admin cannot act on Platform Owner)
- Platform Owner is the only truly invincible entity in the system (invincible in all planes)

**Cross-plane rule:** When a platform member acts on a business member using a global-scoped permission, the business-plane dominance rule is SKIPPED. The platform member's authority comes from their platform role and global permission, not from any business membership.

### 5.2 The Permission Check Algorithm

Every action goes through this exact sequence. The policy layer implements this as `MembershipPolicy.authorize_action()`.

```
AUTHORIZE_ACTION(actor_membership, target_membership_or_none, required_permission):

  ┌─────────────────────────────────────────────────────────────┐
  │ STEP 1: PRECONDITION — Actor membership must be ACTIVE      │
  │                                                             │
  │ if actor_membership.status != ACTIVE:                       │
  │     raise PermissionDenied("Your membership is not active") │
  └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ STEP 2: DETERMINE CONTEXT — Same account or cross-account?  │
  │                                                             │
  │ same_account = (target is None) OR (                        │
  │     actor.account_type == target.account_type AND           │
  │     actor.account_id == target.account_id                   │
  │ )                                                           │
  └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ STEP 3: RESOLVE PERMISSION WITH SCOPE                       │
  │                                                             │
  │ if same_account:                                            │
  │     # For same-account actions, accept any scope match      │
  │     actor must have (required_permission, ANY scope)         │
  │     in their permissions_snapshot                            │
  │                                                             │
  │ if cross_account:                                           │
  │     # For cross-account actions, ONLY global scope counts   │
  │     actor must have (required_permission, global_only)       │
  │     OR (required_permission, platform_and_global)            │
  │     in their permissions_snapshot                            │
  │                                                             │
  │ if no matching permission found:                            │
  │     raise PermissionDenied("Missing required permission")   │
  └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ STEP 4: TARGET CHECKS (only if target_membership exists)    │
  │                                                             │
  │ 4a. Target must be non-deleted membership                   │
  │                                                             │
  │ 4b. OWNER INVINCIBILITY:                                    │
  │     if target.is_owner:                                     │
  │         if same_account:                                    │
  │             raise PermissionDenied("Cannot act on owner")   │
  │         if cross_account AND target.account_type==PLATFORM: │
  │             raise PermissionDenied("Cannot act on           │
  │                                    platform owner")         │
  │         # cross_account + target is business owner:         │
  │         # ALLOWED — platform staff CAN act on business      │
  │         # owners via global permissions                     │
  │         # (e.g., can_remove_business_owner)                 │
  │                                                             │
  │ 4c. DOMINANCE RULE (same-account only):                     │
  │     if same_account:                                        │
  │         if actor.role.level >= target.role.level:            │
  │             raise PermissionDenied("Insufficient authority") │
  │     # cross-account: dominance rule SKIPPED                 │
  │     # (platform authority comes from global permission,     │
  │     #  not from relative role levels)                        │
  └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        ACTION ALLOWED
```

### 5.3 Permission Check Examples (Walkthrough)

**Example 1: Business Admin (level 2) removes a Business Member (level 10)**
- Step 1: Admin membership is ACTIVE ✓
- Step 2: Same account (both in business X) → `same_account = True`
- Step 3: Admin has `(can_remove_member, business)` → found ✓
- Step 4b: Target is not owner ✓
- Step 4c: Admin level 2 < Member level 10 → dominance ✓
- **Result: ALLOWED**

**Example 2: Business Member (level 10) tries to remove Business Admin (level 2)**
- Step 1: Member is ACTIVE ✓
- Step 2: Same account → `same_account = True`
- Step 3: Member has no `can_remove_member` permission → **DENIED at Step 3**

**Example 3: Platform Global Moderator (level 5) suspends a Business Owner (level 0)**
- Step 1: Moderator membership is ACTIVE ✓
- Step 2: Different accounts (platform vs business X) → `same_account = False`
- Step 3: Cross-account → needs global scope. Moderator has `(can_suspend_member, global_only)` → found ✓
- Step 4b: Target is owner, but `cross_account AND target.account_type == BUSINESS` → platform can act on business owner → ALLOWED ✓
- Step 4c: Cross-account → dominance rule SKIPPED ✓
- **Result: ALLOWED**

**Example 4: Platform Admin (level 2) tries to suspend Platform Owner (level 0)**
- Step 1: Admin is ACTIVE ✓
- Step 2: Same account (both platform) → `same_account = True`
- Step 3: Admin has `(can_suspend_member, platform_only)` → found ✓
- Step 4b: Target is owner AND same_account → **DENIED at Step 4b** ("Cannot act on owner")

**Example 5: Business Admin from Business A tries to remove member from Business B**
- Step 1: Admin is ACTIVE ✓
- Step 2: Different accounts (business A vs business B) → `same_account = False`
- Step 3: Cross-account → needs global scope. Admin has `(can_remove_member, business)` but NOT `global_only` → **DENIED at Step 3**

**Example 6: Suspended member tries to act**
- Step 1: Membership status is SUSPENDED → **DENIED at Step 1**

**Example 7: Platform Global Moderator tries to act on Platform Owner**
- Step 1: Moderator is ACTIVE ✓
- Step 2: Same account (both platform) → `same_account = True`
- Step 3: Moderator has required permission ✓
- Step 4b: Target is owner AND same_account → **DENIED at Step 4b**

### 5.4 Role Assignment Validation

When changing a member's role (`change_member_role`), an additional check applies **after** the standard permission check:

```
VALIDATE_ROLE_ASSIGNMENT(actor_membership, new_role):

  # Actor cannot assign a role with equal or higher authority than their own
  if actor_membership.role.level >= new_role.level:
      raise PermissionDenied(
          "Cannot assign a role with equal or higher authority than your own"
      )

  # Level 0 can never be assigned through role change
  # (ownership is transferred, not assigned)
  if new_role.level == 0:
      raise PermissionDenied("Owner role cannot be assigned directly")

  # New role must belong to the same account as the target membership
  if new_role.account_type != target_membership.account_type
     or new_role.account_id != target_membership.account_id:
      raise PermissionDenied("Role does not belong to this account")
```

### 5.5 Owner Leave Prevention

Owners cannot leave their account. They must either transfer ownership or delete the account:

```python
# In RBACService.member_leave()
if membership.is_owner:
    raise BusinessRuleViolation(
        message="You are the owner of this account. "
                "Transfer ownership first or delete the account.",
        rule="owner_cannot_leave"
    )
```

### 5.6 Role Deletion Guard

Roles cannot be deleted if they have active members:

```python
# In RBACService.delete_role()
active_count = Membership.objects.active().filter(role_id=role_id).count()
if active_count > 0:
    raise BusinessRuleViolation(
        message=f"Cannot delete role: {active_count} active member(s) assigned. "
                "Reassign members to a different role first.",
        rule="role_has_active_members"
    )
```

---

## 6. Key Services

### 6.1 RBACService Key Methods

| Method | Purpose | Called By | Cache Invalidation |
|--------|---------|-----------|-------------------|
| `build_actor_context(membership, request)` | Create ActorContext with resolved permissions + scope | Transaction, Views, Policies | Reads cache |
| `initialize_platform_account(platform_id)` | Create platform predefined roles | Organization (migration) | None |
| `initialize_business_account(business_id, owner)` | Create business roles + owner membership | Organization (create_business) | None |
| `create_membership(user, account_type, account_id, role_id)` | Create new member (with default role fallback) | Transaction (on accept) | None |
| `change_member_role(membership_id, new_role_id, actor_membership)` | Change member's role + invalidate cache | API | ✅ Required |
| `update_membership_status(membership_id, status, actor_membership)` | Suspend/ban/remove member + invalidate cache | API | ✅ Required |
| `member_leave(membership_id, user)` | Member voluntarily leaves (owner blocked) | API | Optional |
| `transfer_ownership(account_type, account_id, new_owner)` | Transfer ownership + invalidate both memberships | Transaction (on accept) | ✅ Required |
| `create_custom_role(account_type, account_id, name, level, actor_membership)` | Create custom role (level > actor's level) | API | None |
| `delete_role(role_id, actor_membership)` | Delete role (blocked if has active members) | API | None |
| `add_permission_to_role(role_id, permission_id, scope)` | Add permission to role + validate scope + invalidate | API | ✅ Required |
| `remove_permission_from_role(role_id, permission_id)` | Remove permission from role + invalidate | API | ✅ Required |

### 6.2 Service Implementation Pattern

```python
from django.db import transaction
from apps.core.observability import get_logger, AuditService, AuditLog
from apps.core.exceptions import NotFound, ConflictError, PermissionDenied, BusinessRuleViolation

logger = get_logger(__name__)

class RBACService:
    @staticmethod
    @transaction.atomic
    def initialize_business_account(*, business_id: UUID, owner, request=None) -> Membership:
        logger.info("rbac.business.initialize.start", business_id=str(business_id))

        # Create Owner role (level 0)
        owner_role = Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=business_id,
            level=0,
            is_system_role=True,
        )

        # Create Base Member role (level 10)
        Role.objects.create(
            name="Base Member",
            account_type=AccountType.BUSINESS,
            account_id=business_id,
            level=10,
            is_system_role=True,
        )

        # Seed Owner role permissions (all business-scope permissions)
        # ... (assign all permissions with applicable scope "business" to owner_role)

        # Create owner membership
        membership = Membership.objects.create(
            user=owner,
            account_type=AccountType.BUSINESS,
            account_id=business_id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )

        logger.info("rbac.owner.membership.created", membership_id=str(membership.id))

        AuditService.log(
            action=AuditLog.Action.OWNER_MEMBERSHIP_CREATED,
            actor=owner,
            resource=membership,
            request=request,
        )

        return membership

    @staticmethod
    @transaction.atomic
    def create_membership(
        *, user, account_type: str, account_id: UUID,
        role_id: UUID = None, created_by=None, request=None
    ) -> Membership:
        """
        Create a membership for a user in an account.

        If role_id is None or the role no longer exists, falls back to
        the Base Member role for that account.
        """
        # Resolve role with fallback
        role = None
        if role_id:
            try:
                role = Role.objects.get(
                    id=role_id,
                    account_type=account_type,
                    account_id=account_id,
                    is_deleted=False,
                )
            except Role.DoesNotExist:
                logger.warning(
                    "rbac.membership.role_not_found_fallback",
                    role_id=str(role_id),
                )

        if not role:
            # Fallback: Base Member role
            role = Role.objects.get(
                account_type=account_type,
                account_id=account_id,
                name="Base Member",
                is_system_role=True,
            )

        membership = Membership.objects.create(
            user=user,
            account_type=account_type,
            account_id=account_id,
            role=role,
            is_owner=False,
            status=MembershipStatus.ACTIVE,
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
    def member_leave(*, membership_id: UUID, user) -> Membership:
        """Member voluntarily leaves. Owners are blocked."""
        membership = Membership.objects.get(id=membership_id, user=user)

        if membership.is_owner:
            raise BusinessRuleViolation(
                message="You are the owner of this account. "
                        "Transfer ownership first or delete the account.",
                rule="owner_cannot_leave"
            )

        membership.status = MembershipStatus.LEFT
        membership.status_changed_at = timezone.now()
        membership.status_changed_by = user
        membership.save(update_fields=["status", "status_changed_at", "status_changed_by", "updated_at"])

        PermissionSelector.invalidate_membership_permissions(membership_id=membership_id)

        AuditService.log(
            action=AuditLog.Action.MEMBERSHIP_LEFT,
            actor=user,
            resource=membership,
        )

        return membership

    @staticmethod
    @transaction.atomic
    def delete_role(*, role_id: UUID, actor_membership) -> None:
        """Delete a custom role. Blocked if role has active members."""
        role = Role.objects.get(id=role_id)

        if role.is_system_role:
            raise BusinessRuleViolation(
                message="System roles cannot be deleted.",
                rule="system_role_immutable"
            )

        active_count = Membership.objects.active().filter(role_id=role_id).count()
        if active_count > 0:
            raise BusinessRuleViolation(
                message=f"Cannot delete role: {active_count} active member(s) assigned. "
                        "Reassign members to a different role first.",
                rule="role_has_active_members"
            )

        role.soft_delete(user=actor_membership.user)

        AuditService.log(
            action=AuditLog.Action.ROLE_DELETED,
            actor=actor_membership.user,
            resource=role,
        )

    @staticmethod
    @transaction.atomic
    def add_permission_to_role(*, role_id: UUID, permission_id: UUID, scope: str) -> 'RolePermission':
        """Add permission to role. Validates scope against permission's applicable_scopes."""
        permission = Permission.objects.get(id=permission_id)

        if scope not in permission.applicable_scopes:
            raise ValidationError(
                message=f"Scope '{scope}' is not valid for permission '{permission.code}'. "
                        f"Valid scopes: {permission.applicable_scopes}",
                field="scope",
            )

        role_permission = RolePermission.objects.create(
            role_id=role_id,
            permission_id=permission_id,
            scope=scope,
        )

        # Invalidate all memberships with this role
        PermissionSelector.invalidate_role_permissions(role_id=role_id)

        return role_permission
```

### 6.3 ActorContext Builder (Architectural Boundary)

> **Why this matters**: `ActorContext` is core infrastructure consumed by Transaction, Audit, and Form Builder.
> Permission resolution is RBAC's responsibility. This separation enables caching, keeps dependencies clean,
> and prevents other systems from coupling to RBAC internals.

```python
# In apps/rbac/services.py

from apps.core.types import ActorContext
from apps.core.utils.request import get_client_ip
from apps.rbac.selectors import PermissionSelector

class RBACService:
    # ... other methods ...

    @staticmethod
    def build_actor_context(*, membership, request=None) -> ActorContext:
        """
        Build ActorContext from membership with resolved permissions + scope.

        PRECONDITION: Membership must be ACTIVE. Raises PermissionDenied if not.

        This is the ONLY method that should create ActorContext from membership.
        Other systems should call this, not construct ActorContext directly from
        RBAC models.
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
            user_agent=request.META.get('HTTP_USER_AGENT') if request else None,
        )
```

### 6.4 Permission Selector (with Scope)

```python
# In apps/rbac/selectors.py

from django.core.cache import cache
from typing import List, Tuple

class PermissionSelector:
    CACHE_TTL = 300  # 5 minutes

    @staticmethod
    def get_permissions_for_membership(*, membership_id: UUID) -> List[Tuple[str, str]]:
        """
        Get permission (code, scope) tuples for a membership.

        Returns:
            List of (permission_code, scope) tuples.
            e.g. [("can_view_members", "business"), ("can_remove_member", "global_only")]
        """
        cache_key = f"membership_permissions:{membership_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Verify membership is active and role is not soft-deleted
        membership = Membership.objects.select_related('role').get(
            id=membership_id,
            status=MembershipStatus.ACTIVE,
        )

        if membership.role.is_deleted:
            # Role was soft-deleted but member wasn't reassigned (shouldn't happen
            # because delete_role blocks when members exist, but defensive check)
            return []

        permissions = list(
            membership.role.role_permissions
            .select_related('permission')
            .values_list('permission__code', 'scope')
        )

        cache.set(cache_key, permissions, PermissionSelector.CACHE_TTL)
        return permissions

    @staticmethod
    def invalidate_membership_permissions(*, membership_id: UUID) -> None:
        """Invalidate cached permissions when role or permissions change."""
        cache_key = f"membership_permissions:{membership_id}"
        cache.delete(cache_key)

    @staticmethod
    def invalidate_role_permissions(*, role_id: UUID) -> None:
        """Invalidate cached permissions for all memberships with this role."""
        membership_ids = list(
            Membership.objects.filter(role_id=role_id).values_list('id', flat=True)
        )
        if membership_ids:
            cache.delete_many([
                f"membership_permissions:{mid}" for mid in membership_ids
            ])
```

**Cache Invalidation Rules:**

| Service Method | Invalidation Required |
|----------------|----------------------|
| `change_member_role(membership_id, ...)` | Invalidate `membership_id` |
| `update_membership_status(membership_id, ...)` | Invalidate `membership_id` |
| `transfer_ownership(...)` | Invalidate old + new owner memberships |
| `add_permission_to_role(role_id, ...)` | Invalidate ALL memberships with `role_id` |
| `remove_permission_from_role(role_id, ...)` | Invalidate ALL memberships with `role_id` |
| `member_leave(membership_id, ...)` | Invalidate `membership_id` |

Note: `invalidate_role_permissions` uses `cache.delete_many()` for batch efficiency instead of looping individual deletes.

---

## 7. Policies (Authorization Logic)

### 7.1 MembershipPolicy

```python
# apps/rbac/policies.py

from apps.core.exceptions import PermissionDenied
from apps.core.constants import AccountType, MembershipStatus

class MembershipPolicy:
    """
    Authorization logic for membership actions.

    Implements the two-plane authority model:
    - Business plane: dominance rule applies (level comparison)
    - Platform plane: global-scoped permissions skip business dominance
    """

    @staticmethod
    def authorize_action(
        *,
        actor_context: 'ActorContext',
        target_membership: 'Membership' = None,
        required_permission: str,
    ) -> None:
        """
        Authorize an action. Raises PermissionDenied if not allowed.

        Implements the full check algorithm from Section 5.2.
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
            has_perm = actor_context.has_permission(required_permission)
        else:
            has_perm = actor_context.has_global_permission(required_permission)

        if not has_perm:
            raise PermissionDenied(
                message=f"Missing required permission: {required_permission}",
                action=required_permission,
            )

        # STEP 4: Target checks (only if target exists)
        if target_membership is not None:
            # 4b: Owner invincibility
            if target_membership.is_owner:
                if same_account:
                    raise PermissionDenied(
                        message="Cannot perform this action on the account owner",
                    )
                if target_membership.account_type == AccountType.PLATFORM:
                    raise PermissionDenied(
                        message="Cannot perform this action on the platform owner",
                    )
                # cross_account + business owner: ALLOWED (platform staff can act)

            # 4c: Dominance rule (same-account only)
            if same_account:
                if actor_context.role_level >= target_membership.role.level:
                    raise PermissionDenied(
                        message="Insufficient authority: your role level does not "
                                "outrank the target member's role",
                    )
            # cross-account: dominance rule skipped

    @staticmethod
    def validate_role_assignment(
        *,
        actor_context: 'ActorContext',
        new_role: 'Role',
        target_membership: 'Membership',
    ) -> None:
        """
        Additional validation for role changes.
        Called AFTER authorize_action has passed.
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


class RolePolicy:
    """Authorization logic for role management actions."""

    @staticmethod
    def can_create_role(*, actor_context: 'ActorContext', level: int) -> None:
        """Validate role creation. Level 0 is reserved, must outrank."""
        if level == 0:
            raise PermissionDenied(
                message="Level 0 is reserved for the Owner role",
            )
        if actor_context.role_level >= level:
            raise PermissionDenied(
                message="Cannot create a role with equal or higher "
                        "authority than your own",
            )

    @staticmethod
    def can_modify_role(*, actor_context: 'ActorContext', role: 'Role') -> None:
        """Validate role modification. System roles are immutable."""
        if role.is_system_role:
            raise PermissionDenied(
                message="System roles cannot be modified",
            )
        if actor_context.role_level >= role.level:
            raise PermissionDenied(
                message="Cannot modify a role with equal or higher "
                        "authority than your own",
            )
```

---

## 8. URL Routing

### 8.1 Platform Context (`/api/v1/platform/`)

| Endpoint | Method | Permission |
|----------|--------|------------|
| `members/` | GET | `can_view_members` (platform scope) |
| `members/{id}/` | GET | `can_view_members` (platform scope) |
| `members/{id}/role/` | PATCH | `can_change_member_role` (platform scope) |
| `members/{id}/suspend/` | POST | `can_suspend_member` (platform scope) |
| `members/{id}/remove/` | POST | `can_remove_member` (platform scope) |
| `members/{id}/ban/` | POST | `can_ban_member` (platform scope) |
| `members/leave/` | POST | Platform member |
| `roles/` | GET | Platform member |
| `roles/` | POST | `can_create_role` (platform scope) |
| `roles/{id}/` | PATCH | `can_edit_role` (platform scope) |
| `roles/{id}/` | DELETE | `can_delete_role` (platform scope) |

### 8.2 Business Context (`/api/v1/business/{slug}/`)

| Endpoint | Method | Permission |
|----------|--------|------------|
| `members/` | GET | `can_view_members` |
| `members/{id}/` | GET | `can_view_members` |
| `members/{id}/role/` | PATCH | `can_change_member_role` |
| `members/{id}/suspend/` | POST | `can_suspend_member` |
| `members/{id}/remove/` | POST | `can_remove_member` |
| `members/{id}/ban/` | POST | `can_ban_member` |
| `members/leave/` | POST | Authenticated |
| `roles/` | GET | Authenticated |
| `roles/` | POST | `can_create_role` |
| `roles/{id}/` | PATCH | `can_edit_role` |
| `roles/{id}/` | DELETE | `can_delete_role` |

### 8.3 User Context (`/api/v1/me/`)

| Endpoint | Method | Permission |
|----------|--------|------------|
| `memberships/` | GET | Authenticated |
| `memberships/{id}/` | GET | Authenticated |

---

## 9. Implementation Order

### Phase 1: Foundation
1. Verify enums in `apps/core/constants.py`
2. Create `apps/core/types.py` with ActorContext (v2.0 with scope tuples)
3. Add AuditLog actions

### Phase 2: RBAC App
4. Create app structure
5. Create models (Permission, Role, RolePermission, Membership)
6. Create permission registry

### Phase 3: Data Layer
7. Create selectors (with scope-aware permission resolution)
8. Create policies (two-plane authority model)
9. Create services (with all guards: owner leave prevention, role deletion guard, role assignment validation)

### Phase 4: API Layer
10. Create serializers
11. Create views
12. Create URLs
13. Create admin

### Phase 5: Integration
14. Add to INSTALLED_APPS
15. Register URLs
16. Run makemigrations
17. Create data migration for permissions
18. Run migrate

### Phase 6: Connect Organization
19. Update `BusinessAccountService.create_business()` to call `RBACService.initialize_business_account()`
20. Update platform bootstrap

### Phase 7: Testing
21. Create factories
22. Create tests
23. Run `make check`

---

## 10. Integration Points

### 10.1 Organization → RBAC

```python
# In BusinessAccountService.create_business()
from apps.rbac.services import RBACService

RBACService.initialize_business_account(
    business_id=business.id,
    owner=owner,  # request.user
    request=request
)
```

### 10.2 Transaction → RBAC

```python
# In MembershipOutcomeHandler.handle_invitation_accepted()
RBACService.create_membership(
    user=actor,
    account_type=AccountType(transaction.context_type),
    account_id=transaction.context_id,
    role_id=transaction.payload.get("role_id"),  # Falls back to Base Member if None/invalid
    created_by=actor,
)

# In OwnershipTransferOutcomeHandler.handle_accepted()
RBACService.transfer_ownership(
    account_type=AccountType(transaction.context_type),
    account_id=transaction.context_id,
    new_owner=actor,
    transferred_by=actor,
)
```

---

## 11. Verification Checklist

### Critical Invariants (DB-Level)
- [ ] Unique constraint: `(account_type, account_id)` where `is_owner=True AND is_deleted=False`
- [ ] Unique constraint: `(user, account_type, account_id)` where `is_deleted=False`
- [ ] Unique constraint: `(account_type, account_id, name)` for roles
- [ ] Unique constraint: `(role, permission)` for role_permissions
- [ ] MaxValueValidator(10) on Role.level

### Permission Check Logic
- [ ] Scope is carried in permissions_snapshot as (code, scope) tuples
- [ ] Same-account: any scope match accepted
- [ ] Cross-account: only global_only or platform_and_global accepted
- [ ] Membership status checked BEFORE permission resolution
- [ ] Business owner invincible within business (same-account)
- [ ] Platform owner invincible everywhere
- [ ] Business owner NOT invincible against platform global-scope actions
- [ ] Dominance rule applied for same-account actions only
- [ ] Dominance rule skipped for cross-account (platform → business) actions
- [ ] Role assignment validates actor outranks target role level
- [ ] Level 0 cannot be assigned via role change (ownership transfer only)
- [ ] Owner cannot leave (must transfer or delete)
- [ ] Role deletion blocked when active members exist
- [ ] Scope validated against permission's applicable_scopes on assignment

### Invariant Tests (Must Pass)
- [ ] Creating second owner raises IntegrityError
- [ ] Creating duplicate membership raises IntegrityError
- [ ] Owner cannot be removed/suspended by same-account member
- [ ] Platform owner cannot be removed/suspended by anyone
- [ ] Business owner CAN be suspended by platform staff with global permission
- [ ] Level 0 cannot be assigned to non-owner
- [ ] Dominance rule prevents lower-authority same-account actions
- [ ] Cross-account action without global scope is denied
- [ ] Cross-account action with global scope bypasses dominance rule
- [ ] System roles cannot be deleted
- [ ] Role with active members cannot be deleted
- [ ] Suspended member cannot perform actions
- [ ] Role assignment respects actor level (no privilege escalation)
- [ ] Owner leave attempt raises BusinessRuleViolation
- [ ] Invalid scope on RolePermission is rejected
- [ ] Soft-deleted role returns empty permissions

### Standard Checks
- [ ] `apps.rbac` in INSTALLED_APPS
- [ ] URLs registered
- [ ] Permissions seeded via migration
- [ ] Predefined roles created
- [ ] All services use `get_logger()`
- [ ] All writes use `AuditService.log()`
- [ ] Selectors raise `NotFound`
- [ ] Tests pass
- [ ] Coverage ≥ 80%

---

## 12. Files to Create

| File | Purpose |
|------|---------|
| `backend/apps/core/types.py` | ActorContext (v2.0 with scope tuples) |
| `backend/apps/rbac/__init__.py` | App init |
| `backend/apps/rbac/apps.py` | App config |
| `backend/apps/rbac/models.py` | All models |
| `backend/apps/rbac/selectors.py` | Read queries (scope-aware) |
| `backend/apps/rbac/services.py` | RBACService (with all guards) |
| `backend/apps/rbac/policies.py` | Authorization (two-plane model) |
| `backend/apps/rbac/serializers.py` | API serializers |
| `backend/apps/rbac/views.py` | API views |
| `backend/apps/rbac/urls.py` | URL routing |
| `backend/apps/rbac/admin.py` | Admin |
| `backend/apps/rbac/permissions/registry.py` | Permission definitions |
| `backend/apps/rbac/tests/factories.py` | Factories |
| `backend/apps/rbac/tests/conftest.py` | Fixtures |
| `backend/apps/rbac/tests/test_*.py` | Tests |

---

## 13. Critical Reference Files

| File | Purpose |
|------|---------|
| `backend/apps/core/constants.py` | Shared enums (AccountType, PermissionScope, MembershipStatus) |
| `backend/apps/core/models/base.py` | UUIDModel, AuditModel, SoftDeleteModel |
| `backend/apps/core/exceptions/domain.py` | NotFound, PermissionDenied, BusinessRuleViolation |
| `backend/apps/core/observability/audit/models.py` | AuditLog.Action |
| `backend/apps/core/observability/audit/service.py` | AuditService |
| `backend/apps/core/utils/request.py` | get_client_ip (existing utility) |
| `backend/apps/users/models.py` | User model (UUID PK) |
| `backend/apps/organization/business/models.py` | BusinessAccount (UUID PK) |
| `backend/apps/organization/business/services.py` | BusinessAccountService (RBAC integration stub) |
| `backend/apps/organization/platform/models.py` | PlatformAccount (UUID PK, singleton) |

---

*End of Implementation Plan v2.0*
