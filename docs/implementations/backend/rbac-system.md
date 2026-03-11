# RBAC System — Implementation Reference

**Version:** v1
**Last Updated:** 2026-02-24
**Status:** Implemented

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  API Layer (views.py)                                            │
│  21 views: Permissions, Roles (CRUD + Permissions),              │
│  Members (List, Detail, Leave, Role, Suspend, Remove, Ban)       │
│  AccountContextMixin → resolves ActorContext per account type     │
├──────────────────────────────────────────────────────────────────┤
│  Serializers (serializers.py)                                    │
│  6 input + 8 output serializers                                  │
├──────────────────────────────────────────────────────────────────┤
│  Service Layer (services.py)                                     │
│  RBACService: initialize_platform_account, initialize_business,  │
│    create_membership, change_member_role, update_membership_status│
│    member_leave, restore_membership, transfer_ownership,         │
│    create_custom_role, update_role, delete_role,                 │
│    add/remove_permission_to_role, build_actor_context             │
├─────────────────────┬────────────────────────────────────────────┤
│  Policies            │  Selectors                                 │
│  (policies.py)       │  (selectors.py)                            │
│  MembershipPolicy:   │  PermissionSelector (8 methods)            │
│    authorize_action,  │  RoleSelector (5 methods)                  │
│    validate_role_     │  MembershipSelector (9 methods)            │
│    assignment         │  + Permission caching (TTL=300s)           │
│  RolePolicy:         │                                            │
│    can_create_role,   │                                            │
│    can_modify_role,   │                                            │
│    can_delete_role    │                                            │
├─────────────────────┴────────────────────────────────────────────┤
│  Data Layer (models.py)                                          │
│  Permission (immutable, 28 entries, 7 categories)                │
│  Role (per-account, system + custom, soft-delete)                │
│  RolePermission (assignment with scope)                          │
│  Membership (user-account link, soft-delete, ownership)          │
├──────────────────────────────────────────────────────────────────┤
│  Constants & Types                                               │
│  AccountType, PermissionScope, MembershipStatus                  │
│  ActorContext (apps/core/types.py) — pure dataclass              │
├──────────────────────────────────────────────────────────────────┤
│  Permissions Registry (permissions/registry.py)                  │
│  28 permissions across 7 categories, seeded via data migrations  │
└──────────────────────────────────────────────────────────────────┘

External dependencies:
  → apps.core (AuditModel, UUIDModel, SoftDeleteManager, ActorContext, AuditService, exceptions)
  → apps.organization (BusinessAccount, PlatformAccount — URL resolution in views)
  → apps.users (User model)
```

---

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Two-plane authority model | Business Plane + Platform Plane | Business staff control their own account; platform staff exercise global authority over all businesses |
| Level-based dominance | Numeric role levels (0=owner, 10=lowest) | Simple, deterministic authorization: actor must outrank target (lower number wins) |
| Owner invincibility | Owner (level 0) cannot be acted upon by same-account members | Prevents accidental/malicious owner demotion within their own account |
| `is_owner` as source of truth | Dedicated boolean on Membership, not derived from role | Ownership is a first-class concept separate from role level; avoids ambiguity with custom level-0 roles |
| Immutable permissions | Seeded via data migration only | Permission registry is a controlled vocabulary; prevents runtime drift between environments |
| Scoped permission model | 4 scopes (BUSINESS, PLATFORM_ONLY, GLOBAL_ONLY, PLATFORM_AND_GLOBAL) | Enables fine-grained cross-account authorization without duplicating permission entries |
| Permission caching | Cache permission tuples per membership (TTL=300s) | Avoids repeated multi-join queries during request authorization; invalidated on role/permission changes |
| Soft-delete on Membership | `is_deleted`, `deleted_at`, `deleted_by` fields with filtered manager | Preserves audit trail for removed/left members; `objects` manager auto-filters deleted records |

---

## 3. Data Layer

### 3.1 Permission

Location: `apps/rbac/models.py`

Inherits: `UUIDModel` (UUID pk)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField(pk) | Auto-generated |
| `code` | CharField(100, unique, db_index) | Machine-readable identifier, e.g., `can_invite_member` |
| `name` | CharField(255) | Human-readable display name |
| `description` | TextField(blank) | Optional explanation |
| `category` | CharField(50, db_index) | Grouping: membership, roles, settings, platform, transaction, audit, forms |
| `applicable_scopes` | JSONField(default=list) | List of valid `PermissionScope` values for this permission |

**Immutability:** Permissions are seeded exclusively via data migrations. No runtime creation/modification.

**Ordering:** `["category", "code"]`

### 3.2 Role

Location: `apps/rbac/models.py`

Inherits: `AuditModel` (UUIDModel + created_at, updated_at, created_by, updated_by, is_deleted, deleted_at, deleted_by)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField(pk) | Auto-generated |
| `name` | CharField(100) | Display name |
| `account_type` | CharField(20, choices=AccountType) | `platform` or `business` |
| `account_id` | UUIDField | UUID of the owning account |
| `level` | PositiveSmallIntegerField(max=10) | Authority level: 0=owner (highest), 10=lowest |
| `is_system_role` | BooleanField(default=False) | System roles are immutable (cannot edit/delete) |
| `description` | TextField(blank) | Optional role description |

**Constraints:**
- UniqueConstraint: `(account_type, account_id, name)` — no duplicate role names per account

**Indexes:**
- `(account_type, account_id)`
- `(account_type, account_id, level)`

### 3.3 RolePermission

Location: `apps/rbac/models.py`

Inherits: `UUIDModel` (UUID pk)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField(pk) | Auto-generated |
| `role` | FK→Role(CASCADE) | related_name="role_permissions" |
| `permission` | FK→Permission(CASCADE) | related_name="role_assignments" |
| `scope` | CharField(30, choices=PermissionScope, default=BUSINESS) | Scope at which this permission is granted |

**Constraints:**
- UniqueConstraint: `(role, permission)` — each permission assigned at most once per role

### 3.4 Membership

Location: `apps/rbac/models.py`

Inherits from `UUIDModel` and `AuditModel` (provides soft-delete fields, created_by, updated_by, timestamps).

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUIDField(pk) | Auto-generated |
| `user` | FK→User(CASCADE) | related_name="memberships" |
| `account_type` | CharField(20, choices=AccountType) | `platform` or `business` |
| `account_id` | UUIDField | UUID of the account |
| `role` | FK→Role(PROTECT) | related_name="memberships"; PROTECT prevents role deletion while assigned |
| `is_owner` | BooleanField(default=False) | SOURCE OF TRUTH for ownership |
| `status` | CharField(20, choices=MembershipStatus, default=ACTIVE) | Current membership state |
| `joined_at` | DateTimeField(auto_now_add) | When the membership was created |
| `status_changed_at` | DateTimeField(null) | When status last changed |
| `status_changed_by` | FK→User(SET_NULL, null) | Who changed the status |
| `status_reason` | TextField(blank) | Reason for status change (e.g., ban reason) |
| `is_deleted` | BooleanField(default=False) | Soft-delete flag |
| `deleted_at` | DateTimeField(null) | When soft-deleted |
| `deleted_by` | FK→User(SET_NULL, null) | Who soft-deleted |
| `created_at` | DateTimeField(auto_now_add) | Record creation timestamp |
| `updated_at` | DateTimeField(auto_now) | Last modification timestamp |

**Constraints:**
- UniqueConstraint: `(account_type, account_id)` WHERE `is_owner=True AND is_deleted=False` — one owner per account
- UniqueConstraint: `(user, account_type, account_id)` WHERE `is_deleted=False` — one membership per user per account

**Indexes:**
- `(account_type, account_id, status)`
- `(user, status)`
- `(account_type, account_id, is_owner)`

**Manager:** `objects = MembershipManager()` — auto-filters `is_deleted=False`; methods: `active()`, `for_account()`, `for_user()`

### 3.5 ActorContext

Location: `apps/core/types.py`

Pure dataclass (not a Django model) capturing the identity and authority of an actor at action time.

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | Optional[UUID] | Authenticated user |
| `account_type` | Optional[str] | Account type in context |
| `account_id` | Optional[UUID] | Account UUID in context |
| `membership_id` | Optional[UUID] | Active membership UUID |
| `role_id` | Optional[UUID] | Role UUID |
| `role_name` | Optional[str] | Role display name |
| `role_level` | Optional[int] | Role authority level |
| `is_owner` | bool | Whether user is owner in this context |
| `permissions_snapshot` | List[Tuple[str, str]] | `(code, scope)` tuples captured at context build time |
| `captured_at` | datetime | When context was built |
| `ip_address` | Optional[str] | From request |
| `user_agent` | Optional[str] | From request |

**Key Methods:**
- `has_permission(code)` → bool — checks any scope
- `has_permission_with_scope(code, scope)` → bool — checks specific scope
- `has_global_permission(code)` → bool — checks `global_only` or `platform_and_global` scope
- `permission_codes()` → List[str]
- `to_dict()` / `from_dict(data)` — serialization for audit logs and transaction snapshots
- `for_user_context(user, request=None)` — no account context (e.g., personal actions)
- `for_anonymous(request=None)` — unauthenticated actor
- `for_system()` — Celery tasks and system operations

### Migrations

- `0001_initial` — Creates Permission, Role, RolePermission, Membership tables with all indexes and constraints
- `0002_seed_permissions` — Seeds 26 predefined permissions across 5 categories (reversible)
- `0003_seed_transaction_permissions` — Seeds 2 transaction permissions (added during Transaction system implementation)

---

## 4. Service Layer

### 4.1 RBACService

Location: `apps/rbac/services.py`

**Context Building:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `build_actor_context` | membership, request? | ActorContext | Precondition: membership must be ACTIVE. Loads permission snapshot from cache/DB |

**Account Initialization:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `initialize_platform_account` | platform_id | None | Creates 3 system roles: Platform Owner (level 0), Platform Admin (level 2), Global Moderator (level 5) |
| `initialize_business_account` | business_id, owner, request? | Membership | Creates 2 system roles: Owner (level 0), Base Member (level 10). Returns owner membership. Audits: `OWNER_MEMBERSHIP_CREATED` |

**Membership Management:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_membership` | user, account_type, account_id, role_id?, created_by?, request? | Membership | Defaults to Base Member role if `role_id` not provided. Audits: `MEMBERSHIP_CREATED` |
| `change_member_role` | membership_id, new_role_id, actor_context, request? | Membership | Policy: `MembershipPolicy.authorize_action` + `validate_role_assignment`. Invalidates permission cache. Audits: `MEMBERSHIP_ROLE_CHANGED` |
| `update_membership_status` | membership_id, new_status, actor_context, reason?, request? | Membership | Permission map: SUSPENDED→`can_suspend_member`, BANNED→`can_ban_member`, REMOVED→`can_remove_member`, ACTIVE→`can_suspend_member` (reactivation). Audits: `MEMBERSHIP_SUSPENDED/BANNED/REMOVED/REACTIVATED` |
| `member_leave` | membership_id, user, request? | Membership | Owner cannot leave (raises `BusinessRuleViolation`). Audits: `MEMBERSHIP_LEFT` |
| `restore_membership` | membership_id, actor_context, request? | Membership | Restores soft-deleted or left/removed membership. Audits: `MEMBERSHIP_RESTORED` |
| `transfer_ownership` | account_type, account_id, new_owner, transferred_by?, request? | Tuple[Membership, Membership] | Single atomic transaction: demote old owner + promote new owner. Audits: `OWNERSHIP_TRANSFERRED` |

**Role Management:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `create_custom_role` | account_type, account_id, name, level, description?, actor_context, request? | Role | Policy: `MembershipPolicy.authorize_action` + `RolePolicy.can_create_role`. Audits: `ROLE_CREATED` |
| `update_role` | role_id, name?, description?, actor_context, request? | Role | Policy: `MembershipPolicy.authorize_action` + `RolePolicy.can_modify_role`. Audits: `ROLE_UPDATED` |
| `delete_role` | role_id, actor_context, request? | None | Precondition: no active members assigned to role. Audits: `ROLE_DELETED` |

**Permission Management:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `add_permission_to_role` | role_id, permission_id, scope, actor_context?, request? | RolePermission | Validates scope is in `permission.applicable_scopes`. Invalidates role permission cache. Audits: `ROLE_PERMISSION_ADDED` |
| `remove_permission_from_role` | role_id, permission_id, actor_context?, request? | None | Invalidates role permission cache. Audits: `ROLE_PERMISSION_REMOVED` |

### 4.2 Selectors

Location: `apps/rbac/selectors.py`

**PermissionSelector:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_all_permissions` | — | QuerySet | All permissions |
| `get_permission_by_id` | permission_id | Permission | Raises `NotFound` |
| `get_permission_by_code` | code | Permission | Raises `NotFound` |
| `get_permissions_by_category` | category | QuerySet | Filtered by category |
| `get_permissions_by_scope` | scope | List[Permission] | Permissions where scope is in `applicable_scopes` |
| `get_permissions_for_membership` | membership_id | List[Tuple[str, str]] | CACHED (TTL=300s). Returns `(code, scope)` tuples |
| `invalidate_membership_permissions` | membership_id | None | Clears cache for single membership |
| `invalidate_role_permissions` | role_id | None | Batch invalidates all membership caches for members of this role |

**RoleSelector:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_role_by_id` | role_id | Role | Raises `NotFound` |
| `get_roles_for_account` | account_type, account_id, include_system? | QuerySet | Optionally includes system roles |
| `get_owner_role` | account_type, account_id | Role | Level 0 role for account |
| `get_base_member_role` | account_type, account_id | Role | Highest level role for account (default assignment) |
| `get_role_permissions` | role_id | QuerySet[RolePermission] | All permission assignments for role |

**MembershipSelector:**

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `get_membership_by_id` | membership_id | Membership | Raises `NotFound` |
| `get_membership_for_user_account` | user, account_type, account_id | Optional[Membership] | Any status |
| `get_active_membership_for_user_account` | user, account_type, account_id | Optional[Membership] | ACTIVE only |
| `get_memberships_for_account` | account_type, account_id, status?, include_all_statuses? | QuerySet | List members of account |
| `get_memberships_for_user` | user, status?, include_all_statuses? | QuerySet | List user's memberships |
| `get_owner_membership` | account_type, account_id | Optional[Membership] | Owner of account |
| `count_active_members` | account_type, account_id | int | Active member count |
| `is_user_member_of_account` | user, account_type, account_id | bool | Active membership check |
| `is_user_owner_of_account` | user, account_type, account_id | bool | Ownership check |

### 4.3 Policies

Location: `apps/rbac/policies.py`

**MembershipPolicy:**

| Method | Args | Behavior |
|--------|------|----------|
| `authorize_action` | actor_context, target_membership?, required_permission, skip_deleted_check? | Two-plane authorization algorithm (see Key Flows). Raises `PermissionDenied` |
| `validate_role_assignment` | actor_context, new_role, target_membership | Cannot assign Owner role (level 0) directly. Actor must outrank role: `actor.role.level < new_role.level`. Role must belong to target's account |

**Two-Plane Authorization Algorithm (`authorize_action`):**
1. Actor must be ACTIVE
2. Determine same-account vs cross-account
3. **Same-account:** Accept any scope match for the required permission
4. **Cross-account:** ONLY global scope counts (`global_only` or `platform_and_global`)
5. **Owner invincibility:** Cannot act on owner within same account
6. **Platform owner** always invincible (cannot be targeted cross-account either)
7. **Dominance rule (same-account only):** `actor.role.level < target.role.level` required
8. **Cross-account:** Dominance rule SKIPPED (platform staff act regardless of target's level)

**RolePolicy:**

| Method | Args | Behavior |
|--------|------|----------|
| `can_create_role` | actor_context, level | Level 0 reserved for Owner. Actor must outrank: `actor.role.level < level` |
| `can_modify_role` | actor_context, role | System roles immutable. Actor must outrank: `actor.role.level < role.level` |
| `can_delete_role` | actor_context, role | Same checks as `can_modify_role` |

---

## 5. API Layer

### 5.1 Endpoints

**Permissions** (base: `/api/v1/rbac/`)

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/permissions/` | GET | PermissionListView | IsAuthenticated | List all permissions |

**Business Roles** (base: `/api/v1/business/<slug>/`)

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/roles/` | GET | BusinessRoleListView | IsAuthenticated + Membership | List roles for business |
| `/roles/` | POST | BusinessRoleListView | IsAuthenticated + `can_create_role` | Create custom role |
| `/roles/<role_id>/` | GET | BusinessRoleDetailView | IsAuthenticated + Membership | Get role details with permissions |
| `/roles/<role_id>/` | PATCH | BusinessRoleDetailView | IsAuthenticated + `can_edit_role` | Update role name/description |
| `/roles/<role_id>/` | DELETE | BusinessRoleDetailView | IsAuthenticated + `can_delete_role` | Delete role (no active members) |
| `/roles/<role_id>/permissions/` | POST | BusinessRolePermissionView | IsAuthenticated + `can_edit_role` | Add permission to role |
| `/roles/<role_id>/permissions/` | DELETE | BusinessRolePermissionView | IsAuthenticated + `can_edit_role` | Remove permission from role |

**Business Members** (base: `/api/v1/business/<slug>/`)

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/members/` | GET | BusinessMemberListView | IsAuthenticated + `can_view_members` | List business members |
| `/members/leave/` | POST | BusinessMemberLeaveView | IsAuthenticated + Membership | Leave business |
| `/members/<membership_id>/` | GET | BusinessMemberDetailView | IsAuthenticated + `can_view_members` | Member details |
| `/members/<membership_id>/role/` | PATCH | BusinessMemberRoleView | IsAuthenticated + `can_change_member_role` | Change member's role |
| `/members/<membership_id>/suspend/` | POST | BusinessMemberSuspendView | IsAuthenticated + `can_suspend_member` | Suspend member |
| `/members/<membership_id>/remove/` | POST | BusinessMemberRemoveView | IsAuthenticated + `can_remove_member` | Remove member |
| `/members/<membership_id>/ban/` | POST | BusinessMemberBanView | IsAuthenticated + `can_ban_member` | Ban member |

**Platform Roles** (base: `/api/v1/platform/`): Same structure as Business Roles.

**Platform Members** (base: `/api/v1/platform/`): Same structure as Business Members.

**User Context** (base: `/api/v1/users/me/`)

| Endpoint | Method | View | Permission | Description |
|----------|--------|------|------------|-------------|
| `/memberships/` | GET | MyMembershipsListView | IsAuthenticated | List user's own memberships |
| `/memberships/<membership_id>/` | GET | MyMembershipDetailView | IsAuthenticated | Membership details with permissions |

### 5.2 View Mixins

| Mixin | Purpose |
|-------|---------|
| `AccountContextMixin` | Abstract base. Provides `get_actor_context()` which resolves membership and builds ActorContext via `RBACService.build_actor_context()` |
| `BusinessContextMixin` | Resolves business account from URL slug. `get_account_type()` returns `BUSINESS` |
| `PlatformContextMixin` | Gets platform singleton. `get_account_type()` returns `PLATFORM` |

### 5.3 Serializers

Location: `apps/rbac/serializers.py`

**Input Serializers (6):**

| Serializer | Key Fields | Notes |
|------------|------------|-------|
| RoleCreateInput | name, level, description? | Validates level range |
| RoleUpdateInput | name?, description? | Partial update |
| RolePermissionAddInput | permission_id, scope | Validates scope against permission's applicable_scopes |
| RolePermissionRemoveInput | permission_id | Identifies permission to remove |
| MembershipRoleChangeInput | role_id | New role UUID |
| MembershipStatusChangeInput | status, reason? | Validates status transition |

**Output Serializers (8):**

| Serializer | Purpose | Notes |
|------------|---------|-------|
| PermissionOutput | Permission details | code, name, description, category, applicable_scopes |
| RolePermissionOutput | Permission assignment | Nested permission details + scope |
| RoleOutput | Role summary | name, level, is_system_role, account info |
| RoleDetailOutput | Role with permissions | Extends RoleOutput with permissions list + member count |
| MemberUserOutput | User info within membership | Nested user details |
| MembershipOutput | Full membership details | User, role, status, ownership, timestamps |
| MembershipListOutput | Lightweight membership | Compact for list views |
| MyMembershipOutput | User's own membership | Includes permissions list for the authenticated user |

---

## 6. Types & Constants

### Enums

| Enum | Values | Location |
|------|--------|----------|
| `AccountType` | PLATFORM, BUSINESS | Constants |
| `PermissionScope` | BUSINESS, PLATFORM_ONLY, GLOBAL_ONLY, PLATFORM_AND_GLOBAL | Constants |
| `MembershipStatus` | ACTIVE, SUSPENDED, LEFT, REMOVED, BANNED | Constants |

### Permission Scopes Explained

| Scope | Meaning |
|-------|---------|
| `BUSINESS` | Authority within the business account the role belongs to |
| `PLATFORM_ONLY` | Authority within the platform account only |
| `GLOBAL_ONLY` | Authority across all accounts (cross-account enforcement) |
| `PLATFORM_AND_GLOBAL` | Both platform-local and cross-account authority |

### Permission Registry (28 permissions, 7 categories)

| Category | Permissions |
|----------|-------------|
| Membership (7) | `can_invite_member`, `can_remove_member`, `can_change_member_role`, `can_suspend_member`, `can_ban_member`, `can_approve_membership_request`, `can_view_members` |
| Roles (3) | `can_create_role`, `can_edit_role`, `can_delete_role` |
| Settings (3) | `can_edit_business`, `can_edit_profile`, `can_view_settings` |
| Platform (6) | `can_suspend_business`, `can_remove_business_owner`, `can_transfer_business_ownership`, `can_view_businesses`, `can_approve_verification_request`, `can_approve_business_creation` |
| Transaction (2) | `can_view_transactions`, `can_view_all_transactions` |
| Audit (1) | `can_view_audit_logs` |
| Forms (6) | `can_create_form`, `can_edit_form`, `can_delete_form`, `can_view_responses`, `can_export_responses`, `can_process_response` |

---

## 7. Key Flows

### Flow 1: Business Account Initialization

1. `BusinessAccountService` creates a new business account
2. Calls `RBACService.initialize_business_account(business_id, owner)`
3. Service creates Owner role (level 0, `is_system_role=True`)
4. Service creates Base Member role (level 10, `is_system_role=True`)
5. Service creates Membership for owner: `role=Owner, is_owner=True, status=ACTIVE`
6. Audits `OWNER_MEMBERSHIP_CREATED`
7. Returns the owner Membership

### Flow 2: Build Actor Context

1. View receives authenticated request with account context (e.g., business slug)
2. `AccountContextMixin.get_actor_context()` resolves the user's active membership for the account
3. Calls `RBACService.build_actor_context(membership, request)`
4. Service loads permissions via `PermissionSelector.get_permissions_for_membership()` (cache hit or DB query + cache write, TTL=300s)
5. Constructs `ActorContext` dataclass with user info, role info, `permissions_snapshot`, IP, user agent
6. Returns `ActorContext` — passed to all policy checks during the request

### Flow 3: Same-Account Action Authorization

1. Admin (level 2) wants to suspend a Manager (level 5) in the same business
2. View calls policy: `MembershipPolicy.authorize_action(actor_context, target_membership, required_permission="can_suspend_member")`
3. Policy checks:
   - Actor status is ACTIVE
   - Same account detected (`actor.account_id == target.account_id`)
   - Actor has `can_suspend_member` with any scope — found with `BUSINESS` scope
   - Target is NOT owner — passes
   - Dominance check: `actor.role.level (2) < target.role.level (5)` — passes
4. Authorization granted. Service proceeds with suspension

### Flow 4: Cross-Account Action Authorization (Platform Staff -> Business)

1. Platform Admin wants to suspend a Business Owner
2. View builds actor context from platform membership
3. `MembershipPolicy.authorize_action(actor_context, target_membership, required_permission="can_suspend_business")`
4. Policy checks:
   - Actor status is ACTIVE
   - Cross-account detected (platform account != business account)
   - Actor has `can_suspend_business` with `GLOBAL_ONLY` or `PLATFORM_AND_GLOBAL` scope — required for cross-account
   - Target is business owner — but cross-account, so owner invincibility within same account does NOT apply
   - Dominance rule SKIPPED for cross-account actions
5. Authorization granted. Platform staff can act on any business member regardless of their level

### Flow 5: Ownership Transfer

1. Current owner initiates transfer (via Transaction system acceptance, or direct service call)
2. `RBACService.transfer_ownership(account_type, account_id, new_owner, transferred_by)`:
   - Runs inside `@transaction.atomic`
   - Finds current owner membership (`is_owner=True`)
   - Demotes current owner: `is_owner=False`, assigns Base Member role
   - Promotes new owner: `is_owner=True`, assigns Owner role (level 0)
   - Audits `OWNERSHIP_TRANSFERRED`
3. Returns tuple: `(old_owner_membership, new_owner_membership)`

### Flow 6: Permission Cache Invalidation

1. Admin adds a permission to the "Editor" role via `add_permission_to_role()`
2. Service calls `PermissionSelector.invalidate_role_permissions(role_id)`
3. Selector queries all active memberships assigned to this role
4. For each membership, clears the cached permission tuple list
5. Next request from any member with this role triggers a fresh DB query and cache write

---

## 8. Permissions & Authorization

### RBAC Permissions (seeded)

| Permission | Category | Applicable Scopes | Used By |
|------------|----------|-------------------|---------|
| `can_invite_member` | membership | business, platform_only | `MembershipPolicy.authorize_action` |
| `can_remove_member` | membership | business, platform_only | `RBACService.update_membership_status` |
| `can_change_member_role` | membership | business, platform_only | `RBACService.change_member_role` |
| `can_suspend_member` | membership | business, platform_only | `RBACService.update_membership_status` |
| `can_ban_member` | membership | business, platform_only | `RBACService.update_membership_status` |
| `can_approve_membership_request` | membership | business, platform_only | Transaction policies |
| `can_view_members` | membership | business, platform_only | Member list/detail views |
| `can_create_role` | roles | business, platform_only | `RBACService.create_custom_role` |
| `can_edit_role` | roles | business, platform_only | `RBACService.update_role` |
| `can_delete_role` | roles | business, platform_only | `RBACService.delete_role` |
| `can_suspend_business` | platform | global_only, platform_and_global | Cross-account platform enforcement |
| `can_remove_business_owner` | platform | global_only, platform_and_global | Cross-account platform enforcement |
| `can_transfer_business_ownership` | platform | global_only, platform_and_global | Cross-account ownership transfer |
| `can_view_businesses` | platform | platform_only, platform_and_global | Platform admin views |
| `can_approve_verification_request` | platform | platform_only, platform_and_global | Transaction policies |
| `can_approve_business_creation` | platform | platform_only, platform_and_global | Transaction policies |
| `can_view_transactions` | transaction | business, platform_only | Transaction list views |
| `can_view_all_transactions` | transaction | global_only, platform_and_global | Platform-wide transaction access |
| `can_view_audit_logs` | audit | business, platform_only, platform_and_global | Audit log views |
| `can_create_form` | forms | business | Form builder |
| `can_edit_form` | forms | business | Form builder |
| `can_delete_form` | forms | business | Form builder |
| `can_view_responses` | forms | business | Form response views |
| `can_export_responses` | forms | business | Form response export |
| `can_process_response` | forms | business | Form response processing |
| `can_edit_business` | settings | business | Business settings |
| `can_edit_profile` | settings | business, platform_only | Profile settings |
| `can_view_settings` | settings | business, platform_only | Settings views |

### Audit Actions (16)

| Action | Constant | Triggered By |
|--------|----------|--------------|
| Role Created | `rbac.role.created` | `create_custom_role` |
| Role Updated | `rbac.role.updated` | `update_role` |
| Role Deleted | `rbac.role.deleted` | `delete_role` |
| Role Permission Added | `rbac.role.permission_added` | `add_permission_to_role` |
| Role Permission Removed | `rbac.role.permission_removed` | `remove_permission_from_role` |
| Membership Created | `rbac.membership.created` | `create_membership` |
| Membership Updated | `rbac.membership.updated` | General membership update |
| Membership Role Changed | `rbac.membership.role_changed` | `change_member_role` |
| Membership Suspended | `rbac.membership.suspended` | `update_membership_status` (SUSPENDED) |
| Membership Reactivated | `rbac.membership.reactivated` | `update_membership_status` (ACTIVE) |
| Membership Removed | `rbac.membership.removed` | `update_membership_status` (REMOVED) |
| Membership Banned | `rbac.membership.banned` | `update_membership_status` (BANNED) |
| Membership Left | `rbac.membership.left` | `member_leave` |
| Membership Restored | `rbac.membership.restored` | `restore_membership` |
| Ownership Transferred | `rbac.ownership.transferred` | `transfer_ownership` |
| Owner Membership Created | `rbac.owner.created` | `initialize_business_account` |

---

## 9. Configuration & Gotchas

### Permission Cache

| Parameter | Value | Notes |
|-----------|-------|-------|
| Cache key | `rbac:membership:{membership_id}:permissions` | Per-membership |
| TTL | 300 seconds (5 minutes) | Fixed, not configurable |
| Invalidation | On role change, permission add/remove | Batch invalidation for all members of a role |
| Backend | Requires real cache (LocMemCache or Redis) | DummyCache in test settings makes caching a no-op |

### System Roles (created during account initialization)

**Platform Account:**
- Platform Owner (level 0, system)
- Platform Admin (level 2, system)
- Global Moderator (level 5, system)

**Business Account:**
- Owner (level 0, system)
- Base Member (level 10, system)

### Gotchas

- **`is_owner` vs role level**: `is_owner=True` on Membership is the source of truth for ownership. Role level 0 indicates the Owner role but is not sufficient alone — always check `is_owner` for ownership logic.
- **Owner cannot leave**: `member_leave()` raises `BusinessRuleViolation` if the membership has `is_owner=True`. Must transfer ownership first.
- **PROTECT on role FK**: Membership has `FK→Role(PROTECT)`, so `delete_role()` must verify no active members are assigned before deletion. Attempting to delete a role with assigned members raises `IntegrityError`.
- **System role immutability**: `is_system_role=True` roles cannot be edited or deleted. `RolePolicy.can_modify_role()` rejects these attempts.
- **MembershipStatus.LEFT only via `member_leave()`**: The `update_membership_status()` method does not support setting status to LEFT directly — only SUSPENDED, BANNED, REMOVED, and ACTIVE (reactivation).
- **Permission scope validation**: `add_permission_to_role()` validates that the requested scope is in the permission's `applicable_scopes` list. Attempting to assign a `business` scope to a `global_only` permission will fail.
- **DummyCache in tests**: Permission caching is a no-op under DummyCache. Tests that verify cache behavior must use a LocMemCache fixture override.
- **auto_now_add on joined_at/created_at**: Cannot set at creation time. Use `Membership.objects.filter(id=obj.id).update(joined_at=...)` after factory creation.
- **UUID serialization**: Always `str(uuid)` when storing UUIDs in JSONField (e.g., ActorContext `to_dict()`) or passing to JWT/JSON serializers.
- **Soft-delete manager**: `Membership.objects` auto-filters `is_deleted=False`. To query deleted memberships, use `Membership.all_objects` or explicit filter.
- **Lazy imports in functions**: Mock at source (`apps.rbac.services.RBACService.method`), not the consumer module that lazy-imports it.

---

## 10. Local Development

### Setup

```bash
# Already included in INSTALLED_APPS
# Run migrations
cd backend
python manage.py migrate

# Verify models
python manage.py shell -c "from apps.rbac.models import Permission, Role, RolePermission, Membership; print('OK')"

# Verify permission seed
python manage.py shell -c "from apps.rbac.models import Permission; print(f'{Permission.objects.count()} permissions seeded')"
```

### Test Data

- `RoleFactory` — configurable factory for roles (account_type, level, is_system_role)
- `MembershipFactory` — creates memberships with linked users and roles
- `PermissionFactory` — creates test permissions (for unit tests; production uses seeded data)
- `RolePermissionFactory` — links roles to permissions with scope
- Fixtures in `apps/rbac/tests/conftest.py`: users, accounts, roles, memberships, permissions, actor contexts
- Canonical `UserFactory` at `apps/users/tests/factories.py`

### Useful URLs

| URL | Method | Purpose |
|-----|--------|---------|
| `/api/v1/rbac/permissions/` | GET | List all permissions |
| `/api/v1/business/<slug>/roles/` | GET | List business roles |
| `/api/v1/business/<slug>/members/` | GET | List business members |
| `/api/v1/users/me/memberships/` | GET | List user's own memberships |

---

## 11. Deployment

| Aspect | Local (SQLite) | Production (PostgreSQL + Redis) |
|--------|----------------|-------------------------------|
| Database | SQLite | PostgreSQL |
| Cache | DummyCache (permission cache no-op) | Redis (permission cache enforced, TTL=300s) |
| Permission seed | `0002_seed_permissions` + `0003_seed_transaction_permissions` | Same migrations |
| Account init | Manual via service call or shell | Triggered by account creation flow |

### Pre-Deploy Checklist

- [ ] Run migrations: `python manage.py migrate`
- [ ] Verify permission seed: `python manage.py shell -c "from apps.rbac.models import Permission; print(Permission.objects.count())"` (should be 28)
- [ ] Verify Redis is available for permission caching
- [ ] Verify platform account is initialized with system roles
- [ ] Verify ActorContext serialization works with production UUID format

---

## 12. Testing

| Module | Tests | Status |
|--------|-------|--------|
| test_actor_scenarios.py | 66 | Pass |
| test_models.py | 25 | Pass |
| test_policies.py | 24 | Pass |
| test_selectors.py | 38 | Pass |
| test_services.py | 38 | Pass |
| test_views.py | 32 | Pass |
| **Total** | **223** | **Pass** |

**Test infrastructure:**
- `apps/rbac/tests/factories.py` — RoleFactory, MembershipFactory, PermissionFactory, RolePermissionFactory
- `apps/rbac/tests/conftest.py` — Fixtures for users, accounts, roles, memberships, permissions, actor contexts
- All tests use `@pytest.mark.django_db`, AAA pattern, factory-boy
- `test_actor_scenarios.py` — 66 comprehensive scenarios covering both planes: same-account authorization, cross-account platform enforcement, owner invincibility, dominance rules, scope-based permission matching

---

## 13. File Summary

### New Files

| File | Description |
|------|-------------|
| `apps/rbac/__init__.py` | Package init |
| `apps/rbac/apps.py` | Django app config |
| `apps/rbac/admin.py` | Admin registration |
| `apps/rbac/models.py` | Permission, Role, RolePermission, Membership models |
| `apps/rbac/selectors.py` | PermissionSelector (8 methods), RoleSelector (5 methods), MembershipSelector (9 methods) |
| `apps/rbac/services.py` | RBACService (12 public methods) |
| `apps/rbac/policies.py` | MembershipPolicy (2 methods), RolePolicy (3 methods) |
| `apps/rbac/serializers.py` | 6 input + 8 output serializers |
| `apps/rbac/views.py` | 21 views + AccountContextMixin, BusinessContextMixin, PlatformContextMixin |
| `apps/rbac/urls.py` | URL patterns for permissions, roles, members |
| `apps/rbac/permissions/__init__.py` | Permissions package init |
| `apps/rbac/permissions/registry.py` | 28 permission definitions across 7 categories |
| `apps/rbac/migrations/0001_initial.py` | Schema migration: Permission, Role, RolePermission, Membership tables |
| `apps/rbac/migrations/0002_seed_permissions.py` | Data migration: seeds 26 permissions (reversible) |
| `apps/rbac/migrations/0003_seed_transaction_permissions.py` | Data migration: seeds 2 transaction permissions |
| `apps/rbac/tests/__init__.py` | Test package init |
| `apps/rbac/tests/conftest.py` | Test fixtures |
| `apps/rbac/tests/factories.py` | Test factories |
| `apps/rbac/tests/test_actor_scenarios.py` | 66 actor scenario tests |
| `apps/rbac/tests/test_models.py` | 25 model tests |
| `apps/rbac/tests/test_policies.py` | 24 policy tests |
| `apps/rbac/tests/test_selectors.py` | 38 selector tests |
| `apps/rbac/tests/test_services.py` | 38 service tests |
| `apps/rbac/tests/test_views.py` | 32 view tests |

---

## 14. Known Limitations

1. **Permission cache TTL is fixed at 300s**: Not configurable via settings; hardcoded in selector
2. **No bulk permission assignment**: Permissions must be added to roles one at a time via `add_permission_to_role()`
3. **No permission inheritance between roles**: Each role's permissions are independent; no parent-child role hierarchy
4. **MembershipStatus.LEFT cannot be set via `update_membership_status()`**: Only available through `member_leave()` service method
5. **No audit log for read-only operations**: Permission, role, and membership queries are not audited
6. **No role templates/groups**: Custom roles must be built from scratch; no pre-configured permission bundles

---

## 15. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| Configurable cache TTL via settings | Currently hardcoded 300s in selector | P2 |
| Bulk permission assignment API | Allow assigning multiple permissions to a role in one call | P1 |
| Permission groups/templates for quick role setup | Pre-configured bundles like "Content Manager", "Moderator" | P2 |
| Integration with Organization policies (replace STUB checks) | Some organization-level checks are currently stubbed | P0 |
| Role inheritance/hierarchy | Child roles inherit parent permissions | P3 |
| Membership invitation/request flow integration | Currently handled by Transaction system | Implemented |

---

## 16. Changelog

### v1 (2026-02-24)
- Initial implementation: 4 models, two-plane authority model, 28 seeded permissions across 7 categories
- 223 tests across 6 test modules (models, policies, selectors, services, views, actor scenarios)
- ActorContext dataclass for immutable authority snapshots
- Permission caching with per-membership TTL (300s) and role-level batch invalidation
- 16 audit actions covering all RBAC mutations
- Full API layer with business, platform, and user-context endpoints
