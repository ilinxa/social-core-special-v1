# RBAC System — Complete Technical Reference

**App:** `apps.rbac`
**Version:** 2.1 (Two-Plane Authority Model)
**Last Updated:** February 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture & Dependencies](#2-architecture--dependencies)
3. [Data Model](#3-data-model)
4. [Permission Registry](#4-permission-registry)
5. [Two-Plane Authority Model](#5-two-plane-authority-model)
6. [Authorization Algorithm](#6-authorization-algorithm)
7. [Service Layer](#7-service-layer)
8. [Selector Layer](#8-selector-layer)
9. [Policy Layer](#9-policy-layer)
10. [API Layer](#10-api-layer)
11. [Account Initialization](#11-account-initialization)
12. [ActorContext](#12-actorcontext)
13. [Caching Strategy](#13-caching-strategy)
14. [Audit Trail](#14-audit-trail)
15. [Test Architecture](#15-test-architecture)
16. [Critical Invariants](#16-critical-invariants)
17. [Integration Points](#17-integration-points)
18. [File Reference](#18-file-reference)

---

## 1. System Overview

The RBAC system provides role-based access control for a multi-tenant platform where two types of accounts coexist: a single **Platform account** (the operator) and multiple **Business accounts** (tenants). It implements a two-plane authority model where platform staff can moderate businesses through cross-account global permissions, while business members operate within their own isolated context.

**Core Concepts:**

The system is built around four entities. **Permissions** are developer-defined atomic capabilities seeded via database migration — businesses cannot create new permissions. **Roles** are named bundles of permissions scoped to a specific account, where each role has an authority level (0 = owner, 10 = lowest). **RolePermissions** bind a permission to a role with a specific scope that determines the permission's reach. **Memberships** connect a user to an account with an assigned role, carrying status (active, suspended, banned, removed, left) and ownership flags.

**Design Principles:**

The system follows a layered architecture with strict separation of concerns: models handle data and constraints, selectors handle reads and caching, services handle writes and business logic, policies handle authorization decisions, and views handle HTTP serialization. All write operations go through `RBACService` static methods wrapped in `@transaction.atomic`. All read operations go through selector classes. Authorization checks happen in the policy layer, never in views or services directly.

---

## 2. Architecture & Dependencies

### Layer Diagram

```
┌─────────────────────────────────────────────┐
│                  Views (API)                 │
│  BusinessRoleListView, PlatformMemberList..  │
├─────────────────────────────────────────────┤
│               Serializers                    │
│  Input validation + Output formatting        │
├──────────────────┬──────────────────────────┤
│   Services       │      Selectors           │
│   (writes)       │      (reads + cache)     │
├──────────────────┴──────────────────────────┤
│                 Policies                     │
│  MembershipPolicy, RolePolicy               │
├─────────────────────────────────────────────┤
│                  Models                      │
│  Permission, Role, RolePermission, Membership│
├─────────────────────────────────────────────┤
│              Core (shared)                   │
│  ActorContext, Constants, Exceptions, Audit  │
└─────────────────────────────────────────────┘
```

### External Dependencies

| Module | Import Path | What RBAC Uses |
|--------|-------------|---------------|
| Core Types | `apps.core.types.ActorContext` | Immutable snapshot of actor identity + permissions |
| Core Constants | `apps.core.constants` | `AccountType`, `PermissionScope`, `MembershipStatus` enums |
| Core Exceptions | `apps.core.exceptions` | `NotFound`, `ConflictError`, `PermissionDenied`, `BusinessRuleViolation`, `ValidationError` |
| Core Models | `apps.core.models` | `UUIDModel` (UUID pk), `AuditModel` (created/updated tracking), `SoftDeleteManager` |
| Observability | `apps.core.observability` | `get_logger` (structured logging), `AuditService.log()` |
| Organization | `apps.organization.business.models` | `BusinessAccount` (resolved in views via slug) |
| Organization | `apps.organization.platform.models` | `PlatformAccount` (singleton, resolved in views) |

### Enum Values

**AccountType:** `platform`, `business`

**PermissionScope:** `business` (within assigned business), `platform_only` (within platform account), `global_only` (cross-account, platform → business), `platform_and_global` (both platform-internal and cross-account)

**MembershipStatus:** `active`, `suspended`, `left`, `removed`, `banned`

---

## 3. Data Model

### Entity Relationship

```
Permission (immutable, seeded)
    │
    ├──< RolePermission >──┐
    │    (scope)            │
    │                       │
    │                     Role (per-account)
    │                       │
    │                       ├── account_type + account_id
    │                       ├── level (0-10)
    │                       ├── is_system_role
    │                       │
    │                     Membership
    │                       ├── user (FK → AUTH_USER)
    │                       ├── account_type + account_id
    │                       ├── role (FK → Role, PROTECT)
    │                       ├── is_owner
    │                       ├── status
    │                       └── soft-delete fields
```

### Permission

Predefined atomic capability. Immutable after creation (seeded via `0002_seed_permissions` migration).

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key (from `UUIDModel`) |
| `code` | CharField(100) | Unique, indexed. Machine-readable (e.g., `can_suspend_member`) |
| `name` | CharField(255) | Human-readable display name |
| `description` | TextField | Detailed description |
| `category` | CharField(50) | Indexed. Groups: `membership`, `roles`, `settings`, `platform`, `audit`, `forms` |
| `applicable_scopes` | JSONField | List of valid `PermissionScope` values for this permission |

**Table:** `rbac_permission`
**Ordering:** `["category", "code"]`

### Role

Named bundle of permissions scoped to a specific account.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `name` | CharField(100) | Unique per account (via constraint) |
| `account_type` | CharField(20) | `AccountType` choices |
| `account_id` | UUIDField | References `BusinessAccount.id` or `PlatformAccount.id` |
| `level` | PositiveSmallIntegerField | 0-10. 0 = owner (reserved), 10 = lowest. Validates `MaxValueValidator(10)` |
| `is_system_role` | BooleanField | System roles cannot be modified or deleted |
| `description` | TextField | Optional |
| `created_by` | FK → User | From `AuditModel` |
| `updated_by` | FK → User | From `AuditModel` |
| `created_at` / `updated_at` | DateTimeField | From `AuditModel` |

**Table:** `rbac_role`
**Constraints:** `unique_role_name_per_account` on `(account_type, account_id, name)`
**Indexes:** `(account_type, account_id)`, `(account_type, account_id, level)`

### RolePermission

Assignment of a permission to a role with a specific scope.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `role` | FK → Role | CASCADE |
| `permission` | FK → Permission | CASCADE |
| `scope` | CharField(30) | `PermissionScope` choices. Default: `business` |

**Table:** `rbac_role_permission`
**Constraints:** `unique_permission_per_role` on `(role, permission)`

**Important:** Scope validation (scope must be in `permission.applicable_scopes`) is enforced in `RBACService.add_permission_to_role()`, not at the model level. Django's `clean()` does not run on `objects.create()`, so model-level validation would give a false sense of safety.

### Membership

Connection between a user and an account with a role assignment.

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `user` | FK → User | CASCADE |
| `account_type` | CharField(20) | `AccountType` choices |
| `account_id` | UUIDField | References business or platform |
| `role` | FK → Role | **PROTECT** (prevents deleting roles with members) |
| `is_owner` | BooleanField | Source of truth for ownership (not the role) |
| `status` | CharField(20) | `MembershipStatus` choices |
| `joined_at` | DateTimeField | auto_now_add |
| `status_changed_at` | DateTimeField | Nullable |
| `status_changed_by` | FK → User | SET_NULL |
| `status_reason` | TextField | Reason for status change |

**Table:** `rbac_membership`
**Ordering:** `["-joined_at"]`
**Managers:** `objects` = `MembershipManager` (excludes soft-deleted), `all_objects` = default (includes everything)

**DB-Enforced Constraints:**

| Constraint | Condition | Purpose |
|-----------|-----------|---------|
| `unique_owner_per_account` | `is_owner=True, is_deleted=False` | One owner per account |
| `unique_membership_per_user_account` | `is_deleted=False` | One membership per user per account |

Both constraints use partial unique indexes that ignore soft-deleted records, allowing membership restoration and ownership transfer.

**MembershipManager** extends `SoftDeleteManager` with convenience methods: `active()` filters by `status=ACTIVE`, `for_account(account_type, account_id)` chains active + account filter, `for_user(user)` chains active + user filter.

---

## 4. Permission Registry

All 25 permissions are defined in `apps/rbac/permissions/registry.py` and seeded via `0002_seed_permissions` migration. The registry is the single source of truth.

### Membership Permissions (7)

| Code | Applicable Scopes | Purpose |
|------|-------------------|---------|
| `can_invite_member` | business, platform_only, global_only | Invite new members |
| `can_remove_member` | business, global_only | Remove members |
| `can_change_member_role` | business, global_only | Change role assignment |
| `can_suspend_member` | business, global_only | Temporarily suspend access |
| `can_ban_member` | business, global_only | Permanently ban member |
| `can_approve_membership_request` | business, platform_only | Approve pending requests |
| `can_view_members` | business, platform_only, global_only | View member list |

### Role Permissions (3)

| Code | Applicable Scopes | Purpose |
|------|-------------------|---------|
| `can_create_role` | business, platform_only | Create custom roles |
| `can_edit_role` | business, platform_only | Modify custom roles |
| `can_delete_role` | business, platform_only | Delete custom roles |

Note: Role management permissions have **no global scope**. Platform staff cannot create/edit/delete roles inside a business remotely — only moderate members.

### Settings Permissions (3)

| Code | Applicable Scopes | Purpose |
|------|-------------------|---------|
| `can_edit_business` | business, global_only | Edit account settings |
| `can_edit_profile` | business, global_only | Edit public profile |
| `can_view_settings` | business, platform_only | View account settings |

### Platform Permissions (5)

| Code | Applicable Scopes | Purpose |
|------|-------------------|---------|
| `can_suspend_business` | global_only | Suspend entire business account |
| `can_remove_business_owner` | global_only | Remove a business owner |
| `can_transfer_business_ownership` | global_only | Force ownership transfer |
| `can_view_businesses` | global_only, platform_only | View all businesses |
| `can_approve_verification_request` | platform_only, global_only | Approve verification |
| `can_approve_business_creation` | platform_only | Approve new businesses |

### Audit Permissions (1)

| Code | Applicable Scopes | Purpose |
|------|-------------------|---------|
| `can_view_audit_logs` | business, platform_only, global_only, platform_and_global | View audit logs (broadest scope) |

### Forms Permissions (6)

| Code | Applicable Scopes | Purpose |
|------|-------------------|---------|
| `can_create_form` | business, platform_only | Create forms |
| `can_edit_form` | business, platform_only, global_only | Edit forms |
| `can_delete_form` | business, platform_only, global_only | Delete forms |
| `can_view_responses` | business, platform_only, global_only | View form responses |
| `can_export_responses` | business, platform_only, global_only | Export responses |
| `can_process_response` | business, platform_only, global_only | Process/handle responses |

### Scope Semantics

The scope on a `RolePermission` determines **where the permission can reach** when exercised:

| Scope | Meaning | Example |
|-------|---------|---------|
| `business` | Only within the business where the role is assigned | Business Admin suspends a member in their own business |
| `platform_only` | Only within the platform account itself | Platform Admin creates a role for the platform |
| `global_only` | Cross-account: platform member acting on a business | Global Moderator suspends a business member remotely |
| `platform_and_global` | Both platform-internal and cross-account | Platform Owner viewing audit logs anywhere |

---

## 5. Two-Plane Authority Model

The system operates on two authority planes with distinct rules for each.

### Business Plane

Authority within a single business account. The hierarchy is:

```
Business Owner (level 0)     ← Invincible within this plane
    │
    ├── Custom Admin (level 1-2)
    ├── Custom Editor (level 3-5)
    ├── Custom Viewer (level 6-9)
    │
    └── Base Member (level 10)  ← No permissions
```

**Rules:**
- Dominance rule applies: `actor.role.level < target.role.level` (lower number = higher authority)
- Business Owner (`is_owner=True`) is invincible — no same-account member can act on them
- Members can only create/assign roles with strictly lower authority than their own
- Equal-level members cannot act on each other

### Platform Plane

Authority over the entire platform. Predefined roles:

```
Platform Owner (level 0)      ← Truly invincible (no one can act on them)
    │
    ├── Platform Admin (level 2)   ← platform_only scope (internal management)
    │
    └── Global Moderator (level 5) ← global_only scope (cross-account moderation)
```

**Rules:**
- Dominance rule applies within the platform (Platform Owner > Admin > Moderator)
- Platform Owner is the **only truly invincible entity** in the entire system
- Dominance rule is **SKIPPED** for cross-account actions — authority comes from the global permission, not relative role levels

### Cross-Plane Interaction

When a platform member acts on a business member using a global-scoped permission:

1. The business-plane dominance rule does not apply
2. Business Owner invincibility is **overridden** — platform staff with global permissions CAN act on business owners
3. Platform Owner invincibility is **never overridden** — they remain untouchable
4. The actor does not need a membership in the target business

This is the key design choice: platform staff moderate businesses through the scope system, not by being members of those businesses.

### Cross-Plane Authority Matrix

| Actor | Target | Requires | Dominance | Owner Invincible? |
|-------|--------|----------|-----------|-------------------|
| Business member | Same business member | `business` scope | Yes | Business Owner: Yes |
| Platform member | Same platform member | `platform_only` scope | Yes | Platform Owner: Yes |
| Platform member | Business member | `global_only` or `platform_and_global` scope | **Skipped** | Business Owner: **No** |
| Platform member | Platform Owner | Any scope | N/A | **Always Yes** |
| Business member | Other business member | Not possible | N/A | N/A |

---

## 6. Authorization Algorithm

The 4-step algorithm is implemented in `MembershipPolicy.authorize_action()`.

### Step 1: Actor Validation

Actor must have an active membership context (`membership_id is not None`). This is already enforced by `build_actor_context()` which raises `PermissionDenied` for non-active memberships, but the policy double-checks.

### Step 2: Context Determination

Determine if the action is same-account or cross-account by comparing `actor_context.account_type + account_id` with `target_membership.account_type + account_id`. If there is no target (e.g., creating a role), it's treated as same-account.

### Step 3: Permission Resolution

| Context | Check Method | What Passes |
|---------|-------------|-------------|
| Same-account | `actor_context.has_permission(code)` | Any scope match for that code |
| Cross-account | `actor_context.has_global_permission(code)` | Only `global_only` or `platform_and_global` scope |

If no matching permission is found, raises `PermissionDenied`.

### Step 4: Target Checks

Only applies when a target membership exists:

**4a — Deleted check:** Target must not be soft-deleted (skippable via `skip_deleted_check=True` for restore operations).

**4b — Owner invincibility:**
- Same-account + target is owner → **DENIED** (always)
- Cross-account + target is platform owner → **DENIED** (always)
- Cross-account + target is business owner → **ALLOWED** (platform staff can act on business owners)

**4c — Dominance rule (same-account only):**
- `actor.role_level >= target.role.level` → **DENIED**
- Cross-account → **SKIPPED** entirely

### Role Assignment Validation

`MembershipPolicy.validate_role_assignment()` runs after `authorize_action` for role changes:

1. Cannot assign level 0 (Owner) role — must use ownership transfer
2. Actor must outrank the role being assigned: `actor.role_level < new_role.level`
3. Role must belong to the target's account (account_type + account_id match)

### Role Policy Checks

`RolePolicy` validates role management operations:

- **can_create_role:** Level 0 is forbidden, actor must outrank the level being created
- **can_modify_role:** System roles are forbidden, actor must outrank the role
- **can_delete_role:** Delegates to `can_modify_role` (same checks)

---

## 7. Service Layer

All write operations go through `RBACService` static methods. Every mutation is wrapped in `@transaction.atomic` and produces both a structured log entry and an `AuditService.log()` call.

### Method Reference

| Method | Purpose | Auth Required | Audit Action |
|--------|---------|--------------|--------------|
| `build_actor_context` | Create ActorContext from membership | Membership must be ACTIVE | — |
| `initialize_platform_account` | Seed platform roles + permissions | None (migration) | — |
| `initialize_business_account` | Create business roles + owner membership | None (business creation flow) | `OWNER_MEMBERSHIP_CREATED` |
| `create_membership` | Add member with role (fallback to Base Member) | None (called by invitation system) | `MEMBERSHIP_CREATED` |
| `change_member_role` | Change member's role | `can_change_member_role` + dominance + role validation | `MEMBERSHIP_ROLE_CHANGED` |
| `update_membership_status` | Suspend/ban/remove/reactivate | Status-dependent permission | Status-dependent action |
| `member_leave` | Member voluntarily leaves | Must be own membership, not owner | `MEMBERSHIP_LEFT` |
| `restore_membership` | Restore soft-deleted membership | `can_remove_member` (skip_deleted_check) | `MEMBERSHIP_RESTORED` |
| `transfer_ownership` | Transfer account ownership | **STUB** — deferred to Transaction system | `OWNERSHIP_TRANSFERRED` |
| `create_custom_role` | Create a custom role | `can_create_role` + level validation | `ROLE_CREATED` |
| `update_role` | Update role name/description | `can_edit_role` + system role check | `ROLE_UPDATED` |
| `delete_role` | Soft-delete a custom role | `can_delete_role` + no active members | `ROLE_DELETED` |
| `add_permission_to_role` | Add permission with scope validation | Optional actor_context | `ROLE_PERMISSION_ADDED` |
| `remove_permission_from_role` | Remove permission from role | Optional actor_context | `ROLE_PERMISSION_REMOVED` |

### Status Change Permission Mapping

`update_membership_status` maps the target status to the required permission:

| New Status | Required Permission | Audit Action |
|-----------|-------------------|--------------|
| `suspended` | `can_suspend_member` | `MEMBERSHIP_SUSPENDED` |
| `banned` | `can_ban_member` | `MEMBERSHIP_BANNED` |
| `removed` | `can_remove_member` | `MEMBERSHIP_REMOVED` |
| `active` (reactivation) | `can_suspend_member` | `MEMBERSHIP_REACTIVATED` |

### Membership Creation Fallback

`create_membership` implements a defensive fallback for role resolution:

1. If `role_id` is provided, attempt to find a matching role in the target account
2. If the role doesn't exist or `role_id` is None, fall back to the account's Base Member role
3. This prevents orphaned memberships when a role is deleted between invitation and acceptance

### Actor Resolution

The helper `_resolve_actor(actor_context)` converts `ActorContext.user_id` (UUID) to a `User` object for `AuditService.log()`. Returns `None` if user_id is None or user doesn't exist. This exists because `AuditService.log` expects a User object, not a UUID.

---

## 8. Selector Layer

All read operations go through selector classes. `PermissionSelector` handles caching.

### PermissionSelector

| Method | Returns | Cached |
|--------|---------|--------|
| `get_all_permissions()` | QuerySet ordered by category, code | No |
| `get_permission_by_id(permission_id)` | Permission or raises `NotFound` | No |
| `get_permission_by_code(code)` | Permission or raises `NotFound` | No |
| `get_permissions_by_category(category)` | QuerySet filtered by category | No |
| `get_permissions_by_scope(scope)` | List[Permission] — Python-filtered (SQLite-compatible) | No |
| `get_permissions_for_membership(membership_id)` | List[Tuple[str, str]] — (code, scope) pairs | **Yes** (5 min TTL) |
| `invalidate_membership_permissions(membership_id)` | None — deletes cache key | — |
| `invalidate_role_permissions(role_id)` | None — deletes cache for all memberships with role | — |

**Note on `get_permissions_by_scope`:** This method uses Python-level filtering (`if scope in perm.applicable_scopes`) instead of a database JSONField contains lookup to support both SQLite and PostgreSQL backends.

### RoleSelector

| Method | Returns |
|--------|---------|
| `get_role_by_id(role_id)` | Role or raises `NotFound` |
| `get_roles_for_account(account_type, account_id, include_system)` | QuerySet ordered by level |
| `get_owner_role(account_type, account_id)` | Role (level=0, is_system_role=True) or raises `NotFound` |
| `get_base_member_role(account_type, account_id)` | Role (name="Base Member", is_system_role=True) or raises `NotFound` |
| `get_role_permissions(role_id)` | QuerySet[RolePermission] with select_related permission |

### MembershipSelector

| Method | Returns |
|--------|---------|
| `get_membership_by_id(membership_id)` | Membership (select_related role, user) or raises `NotFound` |
| `get_membership_for_user_account(user, account_type, account_id)` | Membership or None |
| `get_active_membership_for_user_account(...)` | Active Membership or None |
| `get_memberships_for_account(account_type, account_id, status, include_all_statuses)` | QuerySet |
| `get_memberships_for_user(user, status, include_all_statuses)` | QuerySet |
| `get_owner_membership(account_type, account_id)` | Membership (is_owner=True) or None |
| `count_active_members(account_type, account_id)` | int |
| `is_user_member_of_account(user, account_type, account_id)` | bool |
| `is_user_owner_of_account(user, account_type, account_id)` | bool |

---

## 9. Policy Layer

Two policy classes handle authorization decisions. They are pure logic — no database writes, no side effects. They raise `PermissionDenied` on failure and return `None` on success.

### MembershipPolicy

- **`authorize_action(actor_context, target_membership, required_permission, skip_deleted_check)`** — the core 4-step algorithm (see §6)
- **`validate_role_assignment(actor_context, new_role, target_membership)`** — additional checks for role changes (see §6)

### RolePolicy

- **`can_create_role(actor_context, level)`** — level 0 forbidden, actor must outrank
- **`can_modify_role(actor_context, role)`** — system roles forbidden, actor must outrank
- **`can_delete_role(actor_context, role)`** — delegates to `can_modify_role`

---

## 10. API Layer

### URL Structure

Three URL groups mounted at different prefixes:

| Context | Prefix | URL Set |
|---------|--------|---------|
| Business | `/api/v1/business/<slug>/` | `business_urlpatterns` |
| Platform | `/api/v1/platform/` | `platform_urlpatterns` |
| User | `/api/v1/me/` | `user_urlpatterns` |
| Shared | `/api/v1/` | `shared_urlpatterns` (permissions list) |

### Business Endpoints

| Method | Path | View | Purpose |
|--------|------|------|---------|
| GET | `roles/` | BusinessRoleListView | List roles |
| POST | `roles/` | BusinessRoleListView | Create custom role |
| GET | `roles/<role_id>/` | BusinessRoleDetailView | Role details |
| PATCH | `roles/<role_id>/` | BusinessRoleDetailView | Update role |
| DELETE | `roles/<role_id>/` | BusinessRoleDetailView | Delete role |
| POST | `roles/<role_id>/permissions/` | BusinessRolePermissionView | Add permission to role |
| DELETE | `roles/<role_id>/permissions/` | BusinessRolePermissionView | Remove permission from role |
| GET | `members/` | BusinessMemberListView | List members |
| POST | `members/leave/` | BusinessMemberLeaveView | Leave business |
| GET | `members/<id>/` | BusinessMemberDetailView | Member details |
| PATCH | `members/<id>/role/` | BusinessMemberRoleView | Change role |
| POST | `members/<id>/suspend/` | BusinessMemberSuspendView | Suspend member |
| POST | `members/<id>/remove/` | BusinessMemberRemoveView | Remove member |
| POST | `members/<id>/ban/` | BusinessMemberBanView | Ban member |

### Platform Endpoints

Mirror structure of business endpoints at `/api/v1/platform/`. Identical verb/path patterns for roles and members.

### User Endpoints

| Method | Path | View | Purpose |
|--------|------|------|---------|
| GET | `memberships/` | MyMembershipsListView | List own memberships |
| GET | `memberships/<id>/` | MyMembershipDetailView | Own membership details (with permissions) |

### View Mixins

**`AccountContextMixin`** is the base that resolves account context and builds `ActorContext`. It defines `get_account_type()`, `get_account_id()`, and `get_actor_context()`. The `get_actor_context()` method looks up the current user's active membership for the account, then calls `RBACService.build_actor_context()`.

**`BusinessContextMixin`** resolves the business from the URL `business_slug` parameter via `BusinessAccount.objects.get(slug=slug)`.

**`PlatformContextMixin`** resolves the platform singleton via `PlatformAccount.objects.first()`.

### Serializers

**Output serializers:** `PermissionOutputSerializer`, `RoleOutputSerializer`, `RoleDetailOutputSerializer` (includes nested permissions + count), `MembershipOutputSerializer` (full detail with nested user + role), `MembershipListOutputSerializer` (lightweight for lists), `MyMembershipOutputSerializer` (includes resolved permissions list).

**Input serializers:** `RoleCreateInputSerializer` (name + level 1-10 + description), `RoleUpdateInputSerializer` (optional name + description), `RolePermissionAddInputSerializer` (permission_id + scope), `RolePermissionRemoveInputSerializer` (permission_id), `MembershipRoleChangeInputSerializer` (role_id), `MembershipStatusChangeInputSerializer` (status + optional reason).

---

## 11. Account Initialization

### Business Initialization

`RBACService.initialize_business_account(business_id, owner, request)` is called when a new business is created. It performs these operations atomically:

1. Creates **Owner** role (level 0, system, "Full authority")
2. Creates **Base Member** role (level 10, system, "No permissions")
3. Seeds Owner role with all permissions that have `business` in their `applicable_scopes` — all scoped as `business`
4. Creates owner membership (`is_owner=True`, `status=ACTIVE`)
5. Logs `OWNER_MEMBERSHIP_CREATED` audit event

After initialization, the business has 2 system roles and 1 membership. The owner has all business-scope permissions. Base Member has zero permissions.

### Platform Initialization

`RBACService.initialize_platform_account(platform_id)` is called from a data migration after the platform singleton is created. It creates three roles:

**Platform Owner (level 0, system):**
Gets **all** permissions with their broadest applicable scope. The scope priority is: `platform_and_global` > `global_only` > `platform_only` > `business`.

**Platform Admin (level 2, non-system):**
Gets all permissions that include `platform_only` in their `applicable_scopes`, all scoped as `platform_only`. This means Platform Admin has no cross-account reach by default — they manage the platform internally.

**Global Moderator (level 5, non-system):**
Gets all permissions that include `global_only` in their `applicable_scopes`, all scoped as `global_only`. This gives Global Moderator cross-account reach but no platform-internal management.

Note: Platform Admin and Global Moderator are `is_system_role=False`, meaning their permissions can be adjusted after creation.

---

## 12. ActorContext

`ActorContext` is a pure Python dataclass defined in `apps.core.types`. It captures a complete snapshot of an actor's identity and permissions at the moment of an action. It has no imports from RBAC models, avoiding circular dependencies.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | Optional[UUID] | Acting user's ID (None for anonymous/system) |
| `account_type` | Optional[str] | `AccountType` value |
| `account_id` | Optional[UUID] | Account context UUID |
| `membership_id` | Optional[UUID] | Membership record UUID |
| `role_id` | Optional[UUID] | Assigned role UUID |
| `role_name` | Optional[str] | Human-readable role name |
| `role_level` | Optional[int] | Authority level (0=owner, 10=lowest) |
| `is_owner` | bool | Whether actor is account owner |
| `permissions_snapshot` | List[Tuple[str, str]] | List of `(code, scope)` tuples |
| `captured_at` | datetime | When context was captured |
| `ip_address` | Optional[str] | Client IP |
| `user_agent` | Optional[str] | Client user agent |

### Permission Check Methods

- **`has_permission(code)`** — returns True if any (code, *) exists in snapshot (any scope)
- **`has_permission_with_scope(code, scope)`** — exact (code, scope) match
- **`has_global_permission(code)`** — True if code exists with `global_only` or `platform_and_global` scope
- **`permission_codes()`** — flat deduplicated list of permission codes (backward compat)

### Factory Methods

- **`for_user_context(user, request)`** — user-level actions with no account context
- **`for_anonymous(request)`** — unauthenticated actions
- **`for_system()`** — system-initiated actions (Celery tasks, etc.)

### Serialization

`to_dict()` / `from_dict()` for storage and transmission. `from_dict` handles backward compatibility with legacy flat permission lists by converting `["code1", "code2"]` to `[("code1", "business"), ("code2", "business")]`.

---

## 13. Caching Strategy

Only `PermissionSelector.get_permissions_for_membership()` is cached.

**Cache key:** `membership_permissions:{membership_id}`
**TTL:** 300 seconds (5 minutes)
**Backend:** Uses Django's default cache (supports Redis, Memcached, LocMemCache)

### Invalidation Points

Every service method that changes permissions triggers cache invalidation:

| Service Method | Invalidation |
|---------------|-------------|
| `change_member_role` | `invalidate_membership_permissions(membership_id)` |
| `update_membership_status` | `invalidate_membership_permissions(membership_id)` |
| `member_leave` | `invalidate_membership_permissions(membership_id)` |
| `add_permission_to_role` | `invalidate_role_permissions(role_id)` — invalidates ALL memberships with that role |
| `remove_permission_from_role` | `invalidate_role_permissions(role_id)` — invalidates ALL memberships with that role |

### Defensive Checks in Cache Lookup

`get_permissions_for_membership` includes defensive logic: if the membership is not active or the role is soft-deleted, it returns an empty list (without caching the empty result). This prevents stale permissions from being served after a status change that happened outside normal service flows.

---

## 14. Audit Trail

Every mutation in the service layer produces an `AuditService.log()` call with a specific action constant from `AuditLog.Action`.

### Audit Actions

| Action Constant | Triggered By |
|----------------|-------------|
| `OWNER_MEMBERSHIP_CREATED` | `initialize_business_account` |
| `MEMBERSHIP_CREATED` | `create_membership` |
| `MEMBERSHIP_ROLE_CHANGED` | `change_member_role` |
| `MEMBERSHIP_SUSPENDED` | `update_membership_status` (→ suspended) |
| `MEMBERSHIP_BANNED` | `update_membership_status` (→ banned) |
| `MEMBERSHIP_REMOVED` | `update_membership_status` (→ removed) |
| `MEMBERSHIP_REACTIVATED` | `update_membership_status` (→ active) |
| `MEMBERSHIP_LEFT` | `member_leave` |
| `MEMBERSHIP_RESTORED` | `restore_membership` |
| `ROLE_CREATED` | `create_custom_role` |
| `ROLE_UPDATED` | `update_role` |
| `ROLE_DELETED` | `delete_role` |
| `ROLE_PERMISSION_ADDED` | `add_permission_to_role` |
| `ROLE_PERMISSION_REMOVED` | `remove_permission_from_role` |

### Audit Payload

Each audit call includes: `action` (the action constant), `actor` (User object via `_resolve_actor()`), `resource` (the affected model instance), `request` (optional HTTP request for IP/user-agent), `changes` (dict of old/new values where applicable), `details` (additional context like reason).

---

## 15. Test Architecture

220 tests across 6 test files (197 passed, 3 skipped for cache backend).

### Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `test_models.py` | 25 | DB constraints, managers, audit fields, status transitions |
| `test_policies.py` | 24 | Core 4-step algorithm, owner invincibility, dominance, role validation |
| `test_selectors.py` | 38 | All query patterns, caching, cache invalidation |
| `test_services.py` | 47 | Service mutations, authorization integration, error paths |
| `test_views.py` | 37 | API endpoints, serialization, HTTP status codes |
| `test_actor_scenarios.py` | 66 | Real-world actor-perspective integration tests, audit verification |

### Test Infrastructure

**Factories** (`tests/factories.py`): Factory-boy factories for all models. Key composites: `BusinessWithOwnerFactory` creates a business + owner role + base member role + owner membership in one call. Specialized variants: `SuspendedMembershipFactory`, `BannedMembershipFactory`, `GlobalRolePermissionFactory`.

**Conftest** (`tests/conftest.py`): Skip markers for SQLite (`skip_if_sqlite`) and LocMemCache (`skip_if_locmem_cache`) environments. API client fixtures.

### Actor Scenario Categories

| Category | Tests | Covers |
|----------|-------|--------|
| Business Owner | 5 | Suspend/ban any member, create admin role, owner invincibility, cannot leave |
| Business Admin | 4 | Suspend lower level, cannot suspend equal, cannot create equal role, assign lower role |
| Business Member | 3 | Cannot suspend, can leave, cannot create roles |
| Platform Admin Cross-Business | 3 | Global scope can suspend, platform_only cannot, global can ban business owner |
| Platform Admin Internal | 4 | Can suspend Global Mod, cannot suspend Platform Owner, equal-level checks |
| Platform Owner | 2 | Complete invincibility, can suspend Platform Admin |
| Platform Owner Cross-Account | 4 | Can suspend business owner/admin, can ban business member, cannot act on self |
| Global Moderator Cross-Account | 8 | Suspend business owner/admin/member, remove, ban, cannot create business roles, cannot act on Platform Owner/Admin |
| Platform Only Scope Limitations | 2 | Verifies `platform_only` scope cannot cross into business context |
| Cross-Account Edge Cases | 5 | Business owner cannot act in other business, separate contexts, remove/role change blocked |
| Role Management | 5 | Owner edit/delete, cannot delete with members, system role protection, admin create lower |
| Permission Assignment | 2 | Valid business scope, invalid scope rejected |
| Membership Status Transitions | 2 | Suspend→reactivate, ban→reactivate |
| Audit Trail Verification | 13 | Mock `AuditService.log()` and assert call_args for 13 audit actions |
| Suspended/Banned Behavior | 2 | Cannot build ActorContext |
| Dominance Rule Edge Cases | 2 | Level 3 > Level 5, Level 5 < Level 3 |

---

## 16. Critical Invariants

These are the system's hard rules that must never be violated:

1. **One owner per account** — DB-enforced via partial unique constraint on `(account_type, account_id)` where `is_owner=True, is_deleted=False`

2. **One membership per user per account** — DB-enforced via partial unique constraint on `(user, account_type, account_id)` where `is_deleted=False`

3. **Level 0 reserved for Owner** — Service-enforced: `RolePolicy.can_create_role()` blocks level 0, `MembershipPolicy.validate_role_assignment()` blocks assigning level 0 roles

4. **`is_owner` is the source of truth** — Ownership is determined by the `is_owner` flag on Membership, not by having a level-0 role. This allows ownership transfer without role confusion

5. **System roles are immutable** — `RolePolicy.can_modify_role()` and `can_delete_role()` block operations on `is_system_role=True` roles

6. **Permissions are immutable** — Seeded via migration, no API endpoint for creation. Only role↔permission bindings change

7. **Scope must be in applicable_scopes** — `RBACService.add_permission_to_role()` validates that the scope is in the permission's `applicable_scopes` list

8. **Platform Owner is universally invincible** — The policy algorithm has no bypass for acting on a Platform Owner. This is the system's root of trust

9. **Business Owner is conditionally invincible** — Invincible within the business plane, but platform staff with global scope can override

10. **Cross-account requires global scope** — `MembershipPolicy.authorize_action()` calls `has_global_permission()` for cross-account actions, which only matches `global_only` or `platform_and_global` scopes

11. **Dominance skipped cross-account** — When platform acts on business via global permission, role levels are not compared

12. **Ownership transfer is a stub** — `transfer_ownership()` raises `NotImplementedError` until the Transaction system is implemented

---

## 17. Integration Points

### Systems That Call RBAC

| System | How It Uses RBAC |
|--------|-----------------|
| Organization (Business creation) | Calls `initialize_business_account()` when a new business is created |
| Organization (Platform setup) | Calls `initialize_platform_account()` from data migration |
| Invitation/Request system | Calls `create_membership()` when an invitation is accepted |
| Transaction system (future) | Will call `transfer_ownership()` via `OwnershipTransferOutcomeHandler` |
| Any view layer | Calls `build_actor_context()` to get authorization context for the current request |

### Systems That Consume ActorContext

| System | How It Uses ActorContext |
|--------|------------------------|
| RBAC Policies | Reads `permissions_snapshot`, `role_level`, `is_owner` for authorization |
| Transaction System | Stores actor context for audit trail and outcome handling |
| Form Builder | Checks permissions for form CRUD operations |
| Audit System | Extracts `user_id`, `ip_address`, `user_agent` for log entries |

### How Other Views Integrate

Any view that needs authorization should follow this pattern:

```python
# In a view method:
membership = MembershipSelector.get_active_membership_for_user_account(
    user=request.user,
    account_type=AccountType.BUSINESS,
    account_id=business.id,
)
if not membership:
    raise PermissionDenied(message="Not a member")

actor_context = RBACService.build_actor_context(
    membership=membership,
    request=request,
)

# Pass actor_context to service methods that need authorization
RBACService.some_action(actor_context=actor_context, ...)
```

The `AccountContextMixin` and its subclasses (`BusinessContextMixin`, `PlatformContextMixin`) encapsulate this pattern for RBAC's own views.

---

## 18. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `models.py` | 256 | Permission, Role, RolePermission, Membership + MembershipManager |
| `services.py` | 1077 | RBACService with all write operations |
| `selectors.py` | 427 | PermissionSelector, RoleSelector, MembershipSelector |
| `policies.py` | 234 | MembershipPolicy, RolePolicy |
| `views.py` | 793 | All API views + mixins |
| `serializers.py` | 236 | Input/output serializers |
| `urls.py` | 65 | URL configuration (business, platform, user, shared) |
| `admin.py` | 116 | Django admin configuration |
| `permissions/registry.py` | 295 | Permission definitions + helper functions |
| `migrations/0001_initial.py` | ~300 | Schema creation |
| `migrations/0002_seed_permissions.py` | 85 | Permission data seeding |
| `tests/factories.py` | 322 | Factory-boy test factories |
| `tests/conftest.py` | 594 | Pytest fixtures + skip markers |
| `tests/test_models.py` | ~500 | 25 model tests |
| `tests/test_policies.py` | ~800 | 24 policy tests |
| `tests/test_selectors.py` | ~600 | 38 selector tests |
| `tests/test_services.py` | ~1000 | 47 service tests |
| `tests/test_views.py` | ~800 | 37 view tests |
| `tests/test_actor_scenarios.py` | ~2500 | 66 actor scenario tests |

---

*End of RBAC System Technical Reference*
