# RBAC System Implementation Plan

## Multi-Tenant Platform - System 3 of 4

**Version:** 1.2
**Date:** February 8, 2026
**Status:** Ready for Implementation

> **v1.2 Changes**: Added Platform context URL endpoints (Section 7.1). All three contexts now documented:
> Platform (`/api/v1/platform/`), Business (`/api/v1/business/{slug}/`), User (`/api/v1/me/`).
>
> **v1.1 Changes**: Fixed architectural boundary issue - ActorContext is now a pure data structure
> in `apps/core/types.py` with no RBAC imports. RBAC provides `RBACService.build_actor_context()`
> to construct instances with resolved permissions. This enables caching and keeps dependencies clean.

---

## Critical Invariants

> **These rules are non-negotiable and enforced at the database level.**

### 1. One Owner Per Account (DB-Enforced)
Each account (platform or business) has exactly **one owner**, enforced by a **unique constraint** on `(account_type, account_id, is_owner=True)`. This prevents race conditions and ensures ownership clarity.

### 2. One Membership Per User Per Account (DB-Enforced)
A user can have at most one membership per account, enforced by a **unique constraint** on `(user, account_type, account_id)`. No duplicate memberships.

### 3. is_owner Flag is Source of Truth
**Ownership is determined by `Membership.is_owner=True`, NOT by role assignment.** The Owner role grants permissions, but the `is_owner` flag determines invincibility and ownership transfer eligibility.

### 4. Level 0 Reserved for Owner Role
Role levels 0-10 where lower = higher authority. **Level 0 is reserved exclusively for Owner roles** and cannot be assigned to custom roles.

### 5. No Pending Memberships
**Membership records are created ONLY when a user becomes an active member.** Pending states are tracked in the Transaction system, not in Membership.

---

## Executive Summary

This plan outlines the implementation of the RBAC (Role-Based Access Control) System, which provides:
- **Permission**: Predefined atomic capabilities
- **Role**: Named bundles of permissions per account
- **RolePermission**: Assignment of permissions to roles with scope
- **Membership**: Connection between users and accounts with assigned roles

The system follows the established layered architecture: models → managers → selectors → services → policies → serializers → views → URLs.

---

## 1. Prerequisites

### 1.1 Required Enums (Already in `apps/core/constants.py`)

The following enums should already exist from Organization System implementation:

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

from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from django.utils import timezone


def get_client_ip(request) -> Optional[str]:
    """Extract client IP from request."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@dataclass
class ActorContext:
    """
    Captures the complete context of an actor at action time.
    Used by: Transaction system, Form Builder, Audit system

    IMPORTANT: This is a pure data structure. Do NOT add methods that
    import or depend on RBAC models. Use RBACService.build_actor_context()
    to create instances from membership records.
    """
    user_id: UUID
    account_type: Optional[str]  # AccountType value
    account_id: Optional[UUID]
    membership_id: Optional[UUID]
    role_id: Optional[UUID]
    role_name: Optional[str]
    role_level: Optional[int]
    is_owner: bool
    permissions_snapshot: List[str]  # Provided by RBAC, not resolved here
    captured_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/transmission."""
        return {
            'user_id': str(self.user_id),
            'account_type': self.account_type,
            'account_id': str(self.account_id) if self.account_id else None,
            'membership_id': str(self.membership_id) if self.membership_id else None,
            'role_id': str(self.role_id) if self.role_id else None,
            'role_name': self.role_name,
            'role_level': self.role_level,
            'is_owner': self.is_owner,
            'permissions_snapshot': self.permissions_snapshot,
            'captured_at': self.captured_at.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ActorContext':
        """Reconstruct from dictionary (for reading from storage)."""
        from datetime import datetime
        return cls(
            user_id=UUID(data['user_id']),
            account_type=data.get('account_type'),
            account_id=UUID(data['account_id']) if data.get('account_id') else None,
            membership_id=UUID(data['membership_id']) if data.get('membership_id') else None,
            role_id=UUID(data['role_id']) if data.get('role_id') else None,
            role_name=data.get('role_name'),
            role_level=data.get('role_level'),
            is_owner=data.get('is_owner', False),
            permissions_snapshot=data.get('permissions_snapshot', []),
            captured_at=datetime.fromisoformat(data['captured_at']),
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
2. Resolves permissions via `PermissionSelector.get_permissions_for_membership()` (cacheable)
3. Returns a fully-constructed `ActorContext`

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
    """Assignment of permission to role with scope."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_assignments")
    scope = models.CharField(max_length=30, choices=PermissionScope.choices, default=PermissionScope.BUSINESS)

    class Meta:
        db_table = "rbac_role_permission"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="unique_permission_per_role"),
        ]

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

## 5. Key Services

### 5.1 RBACService Key Methods

| Method | Purpose | Called By | Cache Invalidation |
|--------|---------|-----------|-------------------|
| `build_actor_context(membership, request)` | Create ActorContext with resolved permissions | Transaction, Views, Policies | Reads cache |
| `initialize_platform_account(platform_id)` | Create platform predefined roles | Organization (migration) | None |
| `initialize_business_account(business_id, owner)` | Create business roles + owner membership | Organization (create_business) | None |
| `create_membership(user, account_type, account_id, role_id)` | Create new member | Transaction (on accept) | None |
| `change_member_role(membership_id, new_role_id)` | Change member's role + invalidate cache | API | ✅ Required |
| `update_membership_status(membership_id, status)` | Suspend/ban/remove member + invalidate cache | API | ✅ Required |
| `member_leave(membership_id, user)` | Member voluntarily leaves | API | Optional |
| `transfer_ownership(account_type, account_id, new_owner)` | Transfer ownership + invalidate both memberships | Transaction (on accept) | ✅ Required |
| `create_custom_role(account_type, account_id, name, level)` | Create custom role | API | None |
| `delete_role(role_id)` | Soft-delete custom role + invalidate all members | API | ✅ Required |
| `add_permission_to_role(role_id, permission_id, scope)` | Add permission to role + invalidate all members | API | ✅ Required |
| `remove_permission_from_role(role_id, permission_id)` | Remove permission from role + invalidate all members | API | ✅ Required |

### 5.2 Service Implementation Pattern

```python
from django.db import transaction
from apps.core.observability import get_logger, AuditService, AuditLog
from apps.core.exceptions import NotFound, ConflictError, PermissionDenied

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
```

### 5.3 ActorContext Builder (Architectural Boundary)

> **Why this matters**: `ActorContext` is core infrastructure consumed by Transaction, Audit, and Form Builder.
> Permission resolution is RBAC's responsibility. This separation enables caching, keeps dependencies clean,
> and prevents other systems from coupling to RBAC internals.

```python
# In apps/rbac/services.py

from apps.core.types import ActorContext, get_client_ip
from apps.rbac.selectors import PermissionSelector

class RBACService:
    # ... other methods ...

    @staticmethod
    def build_actor_context(*, membership, request=None) -> ActorContext:
        """
        Build ActorContext from membership with resolved permissions.

        This is the ONLY method that should create ActorContext from membership.
        Other systems should call this, not construct ActorContext directly from
        RBAC models.

        Args:
            membership: Membership record (with role prefetched for efficiency)
            request: Optional HTTP request for IP/user-agent capture

        Returns:
            ActorContext with fully resolved permissions snapshot
        """
        # Permission resolution happens here - cacheable in selector
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

```python
# In apps/rbac/selectors.py

from django.core.cache import cache
from typing import List

class PermissionSelector:
    CACHE_TTL = 300  # 5 minutes

    @staticmethod
    def get_permissions_for_membership(*, membership_id: UUID) -> List[str]:
        """
        Get permission codes for a membership.

        Cacheable - permission changes should invalidate this cache.

        Returns:
            List of permission code strings (e.g., ['can_invite_member', 'can_view_members'])
        """
        cache_key = f"membership_permissions:{membership_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        membership = Membership.objects.select_related('role').get(id=membership_id)
        permissions = list(
            membership.role.role_permissions.values_list('permission__code', flat=True)
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
        memberships = Membership.objects.filter(role_id=role_id)
        for membership in memberships:
            PermissionSelector.invalidate_membership_permissions(
                membership_id=membership.id
            )
```

**Cache Invalidation Strategy:**

> **CRITICAL**: Permission caches MUST be invalidated when permissions change. Failure to invalidate
> causes subtle bugs where users retain stale permissions for up to 5 minutes (CACHE_TTL).

**Invalidation Rules** - Call `PermissionSelector.invalidate_membership_permissions()` in:

| Service Method | When | Invalidation Required |
|----------------|------|----------------------|
| `change_member_role(membership_id, new_role_id)` | After role assignment changes | Invalidate `membership_id` |
| `update_membership_status(membership_id, status)` | After suspend/ban/remove | Invalidate `membership_id` |
| `transfer_ownership(account_type, account_id, new_owner)` | After ownership transfer | Invalidate old + new owner memberships |
| `add_permission_to_role(role_id, permission_id)` | After permission added to role | Invalidate ALL memberships with `role_id` |
| `remove_permission_from_role(role_id, permission_id)` | After permission removed from role | Invalidate ALL memberships with `role_id` |
| `delete_role(role_id)` | Before soft-deleting role | Invalidate ALL memberships with `role_id` |

**Implementation Example:**

```python
# In RBACService.change_member_role()
@staticmethod
@transaction.atomic
def change_member_role(*, membership_id: UUID, new_role_id: UUID, changed_by) -> Membership:
    membership = Membership.objects.get(id=membership_id)
    old_role_id = membership.role_id

    membership.role_id = new_role_id
    membership.save()

    # CRITICAL: Invalidate cached permissions
    PermissionSelector.invalidate_membership_permissions(membership_id=membership_id)

    logger.info("rbac.membership.role_changed", membership_id=str(membership_id))
    return membership

# In RBACService.add_permission_to_role()
@staticmethod
@transaction.atomic
def add_permission_to_role(*, role_id: UUID, permission_id: UUID, scope: str) -> RolePermission:
    role_permission = RolePermission.objects.create(
        role_id=role_id,
        permission_id=permission_id,
        scope=scope
    )

    # CRITICAL: Invalidate all memberships with this role
    PermissionSelector.invalidate_role_permissions(role_id=role_id)

    logger.info("rbac.role.permission_added", role_id=str(role_id))
    return role_permission
```

**Note on Distributed Systems:**
- Current design: Single-server cache (Redis)
- Cache invalidation works correctly within single Django instance
- If scaling to multiple servers: Use Redis pub/sub or cache versioning
- Not required for initial implementation

**Usage in other systems:**

```python
# In Transaction system
from apps.rbac.services import RBACService

actor_context = RBACService.build_actor_context(
    membership=actor_membership,
    request=request
)
transaction.initiator_context = actor_context.to_dict()

# In views/middleware
actor_context = RBACService.build_actor_context(
    membership=request.membership,
    request=request
)
```

---

## 6. Policies (Authorization Logic)

### 6.1 Dominance Rule

When actor performs member-management action on target:
1. **Same account context required** (or actor has global scope permission)
2. **Actor must have required permission**
3. **Target owner is invincible** (within same authority plane)
4. **Actor.role.level < Target.role.level** (lower level = higher authority)

### 6.2 Key Policy Methods

```python
class MembershipPolicy:
    @staticmethod
    def can_act_on_member(*, actor_membership, target_membership, required_permission) -> None:
        """Raises PermissionDenied if action not allowed."""
        # Check global scope for cross-account
        # Check permission exists
        # Check owner invincibility
        # Check dominance rule

class RolePolicy:
    @staticmethod
    def can_create_role(*, actor_membership, level) -> None:
        """Cannot create level 0 or higher authority than own."""

    @staticmethod
    def can_modify_role(*, actor_membership, role) -> None:
        """System roles cannot be modified."""
```

---

## 7. URL Routing

### 7.1 Platform Context (`/api/v1/platform/`)

| Endpoint | Method | Permission |
|----------|--------|------------|
| `members/` | GET | `can_view_members` (platform scope) |
| `members/{id}/` | GET | `can_view_members` (platform scope) |
| `members/{id}/role/` | PATCH | `can_change_member_role` (global_only) |
| `members/{id}/suspend/` | POST | `can_suspend_member` (global_only) |
| `members/{id}/remove/` | POST | `can_remove_member` (global_only) |
| `members/{id}/ban/` | POST | `can_ban_member` (global_only) |
| `members/leave/` | POST | Platform member |
| `roles/` | GET | Platform member |
| `roles/` | POST | `can_create_role` (platform scope) |
| `roles/{id}/` | PATCH | `can_edit_role` (platform scope) |
| `roles/{id}/` | DELETE | `can_delete_role` (platform scope) |

### 7.2 Business Context (`/api/v1/business/{slug}/`)

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

### 7.3 User Context (`/api/v1/me/`)

| Endpoint | Method | Permission |
|----------|--------|------------|
| `memberships/` | GET | Authenticated |
| `memberships/{id}/` | GET | Authenticated |

---

## 8. Implementation Order

### Phase 1: Foundation
1. Verify enums in `apps/core/constants.py`
2. Create `apps/core/types.py` with ActorContext
3. Add AuditLog actions

### Phase 2: RBAC App
4. Create app structure
5. Create models
6. Create permission registry

### Phase 3: Data Layer
7. Create selectors
8. Create policies
9. Create services

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
19. Update BusinessAccountService.create_business() to call RBACService
20. Update platform bootstrap

### Phase 7: Testing
21. Create factories
22. Create tests
23. Run make check

---

## 9. Integration Points

### 9.1 Organization → RBAC

```python
# In BusinessAccountService.create_business()
RBACService.initialize_business_account(
    business_id=business.id,
    owner=owner,  # request.user
    request=request
)
```

### 9.2 Transaction → RBAC

```python
# In MembershipOutcomeHandler.handle_invitation_accepted()
RBACService.create_membership(
    user=actor,
    account_type=AccountType(transaction.context_type),
    account_id=transaction.context_id,
    role_id=transaction.payload.get("role_id"),
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

## 10. Verification Checklist

### Critical Invariants (DB-Level)
- [ ] Unique constraint: `(account_type, account_id)` where `is_owner=True`
- [ ] Unique constraint: `(user, account_type, account_id)` where not deleted
- [ ] Unique constraint: `(account_type, account_id, name)` for roles
- [ ] Unique constraint: `(role, permission)` for role_permissions
- [ ] MaxValueValidator(10) on Role.level

### Standard Checks
- [ ] `apps.rbac` in INSTALLED_APPS
- [ ] URLs registered
- [ ] Permissions seeded via migration
- [ ] Predefined roles created
- [ ] All services use get_logger()
- [ ] All writes use AuditService.log()
- [ ] Selectors raise NotFound
- [ ] Policies implement dominance rule
- [ ] Owner invincibility works
- [ ] Tests pass
- [ ] Coverage ≥ 80%

### Invariant Tests (Must Pass)
- [ ] Creating second owner raises IntegrityError
- [ ] Creating duplicate membership raises IntegrityError
- [ ] Owner cannot be removed/suspended
- [ ] Level 0 cannot be assigned to non-owner
- [ ] Dominance rule prevents lower-authority actions
- [ ] System roles cannot be deleted

---

## 11. Files to Create

| File | Purpose |
|------|---------|
| `backend/apps/core/types.py` | ActorContext |
| `backend/apps/rbac/__init__.py` | App init |
| `backend/apps/rbac/apps.py` | App config |
| `backend/apps/rbac/models.py` | All models |
| `backend/apps/rbac/selectors.py` | Read queries |
| `backend/apps/rbac/services.py` | RBACService |
| `backend/apps/rbac/policies.py` | Authorization |
| `backend/apps/rbac/serializers.py` | API serializers |
| `backend/apps/rbac/views.py` | API views |
| `backend/apps/rbac/urls.py` | URL routing |
| `backend/apps/rbac/admin.py` | Admin |
| `backend/apps/rbac/permissions/registry.py` | Permission definitions |
| `backend/apps/rbac/tests/factories.py` | Factories |
| `backend/apps/rbac/tests/conftest.py` | Fixtures |
| `backend/apps/rbac/tests/test_*.py` | Tests |

---

## 12. Critical Reference Files

| File | Purpose |
|------|---------|
| `backend/apps/core/constants.py` | Shared enums |
| `backend/apps/core/models/base.py` | UUIDModel, AuditModel |
| `backend/apps/core/exceptions/domain.py` | NotFound, PermissionDenied |
| `backend/apps/core/observability/audit/models.py` | AuditLog.Action |
| `.claude/system/predocs/system_1/RBAC_Permission_Role_Member_Management_Spec_v3.md` | Full spec |
| `.claude/system/predocs/system_1/Shared_System_Context.md` | Cross-system reference |

---

*End of Implementation Plan*
