# Backend Compatibility Review: pconsole vs gconsole

**Date:** 2026-03-09
**Scope:** Backend readiness for Platform Console (pconsole) and Global Console (gconsole)
**Reviewed Files:** ~6,000 lines across 25+ source files

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [pconsole — Platform Console](#2-pconsole--platform-console)
   - 2.1 Organization System
   - 2.2 RBAC System (Roles, Permissions, Memberships)
   - 2.3 Transaction System
   - 2.4 Form System
   - 2.5 CMS System
   - 2.6 Tier 1.5 Permission-Aware Responses
3. [gconsole — Global Console](#3-gconsole--global-console)
   - 3.1 Concept & Separation from pconsole
   - 3.2 Current Global Capabilities
   - 3.3 Missing Global Endpoints
   - 3.4 Permission Architecture for gconsole
4. [Frontend Guards & Routing](#4-frontend-guards--routing)
5. [Gap Summary](#5-gap-summary)
6. [Recommendations](#6-recommendations)
7. [File Reference](#7-file-reference)

---

## 1. Architecture Overview

The system has **three console contexts**, each with distinct authority and scope:

| Console | Audience | Account Model | Guard | URL Pattern |
|---------|----------|---------------|-------|-------------|
| **bconsole** | Business members | BusinessAccount (multi-tenant, slug-based) | BusinessGuard (membership + slug) | `/bconsole/[slug]/` |
| **pconsole** | **ALL** platform members | PlatformAccount (singleton) | PlatformGuard (membership) | `/pconsole/` |
| **gconsole** | Platform members **with global-scoped permissions** | PlatformAccount (global scope) | **NOT BUILT** | `/gconsole/` |

**Key Principle:**
- **pconsole** manages the platform's own account (members, roles, forms, transactions, CMS, profile) — same structure as bconsole but for the platform entity. ALL platform members can enter pconsole, but what they see/do is gated by their `platform_only` permissions (same as bconsole gating by business permissions).
- **gconsole** provides cross-account management (all businesses, all users, audit logs, global settings) — a completely different UI surface. Only accessible to platform members who have at least one `global_only` or `platform_and_global` scoped permission.
- A single platform member can access **both** pconsole and gconsole if their role includes permissions in both scopes.

**Authority Model (Permission Scope → Console Mapping):**
- `business` scope = actions within one business account (bconsole)
- `platform_only` scope = actions within the platform's own account (pconsole features)
- `global_only` scope = cross-account actions on all businesses/users (gconsole features)
- `platform_and_global` scope = both pconsole + gconsole features

---

## 2. pconsole — Platform Console

### 2.1 Organization System

#### Models

| Aspect | Business | Platform | Status |
|--------|----------|----------|--------|
| **Model** | `BusinessAccount` (multi-tenant, 16 fields) | `PlatformAccount` (singleton, 6 fields) | COMPATIBLE |
| **Profile** | `BusinessProfile` (19 fields: tags, website, industry, cover_image, is_public, etc.) | `PlatformProfile` (11 fields: branding colors, favicon, contact) | COMPATIBLE |
| **Slug** | `BusinessSlugHistory` for redirects | N/A (no slug concept) | N/A |
| **Creation** | Explicit via API (`POST /business/`) | Auto-via migration, configured by superuser | COMPATIBLE |
| **Singleton** | No (many instances) | Yes (`singleton_key=1` with DB constraint) | COMPATIBLE |

**Files:**
- `apps/organization/platform/models.py` (95 lines) — PlatformAccount + PlatformProfile
- `apps/organization/business/models.py` (223 lines) — BusinessAccount + BusinessProfile + SlugHistory

**Key Differences:**
- Platform has NO `status` field (no ACTIVE/SUSPENDED/ARCHIVED state machine)
- Platform has NO `verification_status` (no verification workflow)
- Platform has NO `is_public` on profile (always accessible)
- Platform has NO `tags` (not discoverable via Explore)
- Platform has `primary_color`/`secondary_color`/`favicon` (branding)

**Verdict:** READY for pconsole. Profile fields differ but that's by design.

#### Services

| Operation | Business | Platform | Status |
|-----------|----------|----------|--------|
| Create | `create_business()` | `configure()` (one-time) | COMPATIBLE |
| Update profile | `BusinessProfileService.update()` | `PlatformProfileService.update()` | COMPATIBLE |
| Update settings | `update()` | `update_settings()` | COMPATIBLE |
| Suspend/Reactivate | Yes | No | N/A (platform can't be suspended) |
| Archive/Delete | Yes | No | N/A (platform can't be deleted) |
| Update slug | Yes | No | N/A (no slug) |

**Files:**
- `apps/organization/platform/services.py` (294 lines) — PlatformAccountService + PlatformProfileService
- `apps/organization/business/services.py` (735 lines) — Full lifecycle

**Verdict:** READY for pconsole. Platform lifecycle is intentionally simpler.

#### Selectors

| Query | Business | Platform | Status |
|-------|----------|----------|--------|
| Get by ID/slug | `get_by_id()`, `get_by_slug()` | `get()` (singleton) | COMPATIBLE |
| List | `list_active()`, `list_by_owner()` | N/A (singleton) | N/A |
| Exists check | `slug_exists()` | `exists()`, `is_configured()` | COMPATIBLE |

**Files:**
- `apps/organization/platform/selectors.py` (68 lines) — 3 methods
- `apps/organization/business/selectors.py` (235 lines) — 12 methods

**Verdict:** READY for pconsole. Platform needs fewer queries (singleton).

#### API Endpoints

| Endpoint | Business | Platform | Status |
|----------|----------|----------|--------|
| Account detail (GET) | `/business/{slug}/` | `/platform/account/` | COMPATIBLE |
| Profile update (PATCH) | `/business/{slug}/profile/` | `/platform/profile/` | COMPATIBLE |
| Settings update (PATCH) | N/A | `/platform/settings/` | COMPATIBLE |
| Configure (POST) | `/business/` (create) | `/platform/account/` (configure) | COMPATIBLE |

**Files:**
- `apps/organization/platform/views.py` (332 lines) — 3 view classes
- `apps/organization/platform/urls.py` (38 lines)

**Verdict:** READY for pconsole.

---

### 2.2 RBAC System (Roles, Permissions, Memberships)

#### Platform Roles (4 system roles)

Initialized in `RBACService.initialize_platform_account()` (`apps/rbac/services.py:122-217`):

| Role | Level | System | Scope | Description |
|------|-------|--------|-------|-------------|
| **Platform Owner** | 0 | Yes | `platform_and_global` (broadest) | Full authority, all permissions |
| **Platform Admin** | 2 | No (modifiable) | `platform_only` | Platform operations (pconsole) |
| **Global Moderator** | 5 | No (modifiable) | `global_only` | Cross-account moderation (gconsole) |
| **Base Member** | 10 | Yes | None | No permissions (fallback) |

**vs Business:** Business has only 2 system roles (Owner + Base Member). Platform has 4 because it needs separate scopes for pconsole vs gconsole.

**IMPORTANT:** Platform Admin (level 2) gets `platform_only` permissions = pconsole access. Global Moderator (level 5) gets `global_only` permissions = gconsole access. Platform Owner gets BOTH.

#### Platform Permissions (53 seeded)

**Source migrations:** `apps/rbac/migrations/0002`, `0003`, `0004`, `0007`

| Category | Count | Scopes Available | pconsole? | gconsole? |
|----------|-------|------------------|-----------|-----------|
| Membership (7) | `can_invite_member`, `can_remove_member`, `can_change_member_role`, `can_suspend_member`, `can_ban_member`, `can_approve_membership_request`, `can_view_members` | business, platform_only, global_only | YES | YES |
| Roles (3) | `can_create_role`, `can_edit_role`, `can_delete_role` | business, platform_only | YES | No |
| Settings (3) | `can_edit_business`, `can_edit_profile`, `can_view_settings` | business, global_only, platform_only | YES | YES |
| Platform Admin (6) | `can_suspend_business`, `can_remove_business_owner`, `can_transfer_business_ownership`, `can_view_businesses`, `can_approve_verification_request`, `can_approve_business_creation` | global_only, platform_only | Partial | YES |
| Audit (1) | `can_view_audit_logs` | all scopes | YES | YES |
| Forms (6) | `can_create_form`, `can_edit_form`, `can_delete_form`, `can_view_responses`, `can_export_responses`, `can_process_response` | business, platform_only, global_only | YES | YES |
| Transactions (3) | `can_view_transactions`, `can_view_all_transactions`, `can_configure_transactions` | business, platform_only, global_only, platform_and_global | YES | YES |
| CMS (23) | Structural (12) + Content (8) + Media (3) | platform_only, business, global_only | YES | Partial |

**Verdict:** READY for pconsole. Permission architecture cleanly separates pconsole (`platform_only`) from gconsole (`global_only`).

#### Member Management Endpoints

All platform member endpoints exist and mirror business:

| Endpoint | Method | View | Status |
|----------|--------|------|--------|
| `/platform/members/` | GET | PlatformMemberListView | READY |
| `/platform/members/{id}/` | GET | PlatformMemberDetailView (+ `_permissions`) | READY |
| `/platform/members/{id}/role/` | PATCH | PlatformMemberRoleView | READY |
| `/platform/members/{id}/suspend/` | POST | PlatformMemberSuspendView | READY |
| `/platform/members/{id}/remove/` | POST | PlatformMemberRemoveView | READY |
| `/platform/members/{id}/ban/` | POST | PlatformMemberBanView | READY |
| `/platform/members/{id}/reactivate/` | POST | PlatformMemberReactivateView | READY |
| `/platform/members/leave/` | POST | PlatformMemberLeaveView | READY |

**Member List Features:** search, status filter, role_id filter, ordering, pagination (StandardPagination).

**Member Detail `_permissions`:** `{ can_change_role, can_suspend, can_remove, can_ban, can_reactivate }` — 5 boolean keys via `MembershipPolicy.get_viewer_permissions()`.

**Files:** `apps/rbac/views.py:854-1131`, `apps/rbac/urls.py:37-52`

**Verdict:** FULLY READY for pconsole. Complete feature parity with business.

#### Role Management Endpoints

| Endpoint | Method | View | Status |
|----------|--------|------|--------|
| `/platform/roles/` | GET | PlatformRoleListView (+ member_count) | READY |
| `/platform/roles/` | POST | PlatformRoleListView (create) | READY |
| `/platform/roles/{id}/` | GET | PlatformRoleDetailView (+ `_permissions`) | READY |
| `/platform/roles/{id}/` | PATCH | PlatformRoleDetailView (update) | READY |
| `/platform/roles/{id}/` | DELETE | PlatformRoleDetailView (delete) | READY |
| `/platform/roles/{id}/permissions/` | POST | PlatformRolePermissionView (add) | READY |
| `/platform/roles/{id}/permissions/` | DELETE | PlatformRolePermissionView (remove) | READY |

**Role Detail `_permissions`:** `{ can_edit, can_delete, can_modify_permissions }` — 3 boolean keys via `RolePolicy.get_viewer_permissions()`.

**Files:** `apps/rbac/views.py:652-847`

**Verdict:** FULLY READY for pconsole.

#### GAP: Platform Owner Membership Not Auto-Created

**Severity:** MEDIUM

`RBACService.initialize_platform_account()` creates 4 roles but does NOT create the Platform Owner membership. Compare with business: `initialize_business_account()` creates owner membership.

**Impact:** After platform configuration, no one has platform membership until manually invited. The superuser who configured it should automatically become Platform Owner.

**Fix Required:** Add owner membership creation to `PlatformAccountService.configure()`.

---

### 2.3 Transaction System

#### Platform Transaction Types (3 registered)

**File:** `apps/transaction/types.py:44-92`

| Type | Mode | Approver | Expiry | Conflict Group | Outcome |
|------|------|----------|--------|----------------|---------|
| `platform_membership_invitation` | INVITATION | TARGET_ACCEPTANCE | 14 days | `platform_membership` | `MembershipOutcomeHandler` |
| `platform_membership_request` | REQUEST | PLATFORM_AUTHORITY | 30 days | `platform_membership` | `MembershipOutcomeHandler` |
| `platform_ownership_transfer` | INVITATION | TARGET_ACCEPTANCE | 7 days | None | `OwnershipOutcomeHandler` |

**vs Business:** Business has same 3 types with identical structure (different expiry: business invitation = 7 days).

#### Transaction Endpoints

**All transaction endpoints are GENERIC** — same endpoints handle both business and platform via `context_type` parameter:

| Endpoint | Method | Platform Support |
|----------|--------|-----------------|
| `POST /transactions/invitation/` | Create invitation | YES (context_type=platform) |
| `POST /transactions/request/` | Create request | YES (context_type=platform) |
| `GET /transactions/?context_type=platform&context_id={id}` | List | YES |
| `GET /transactions/{id}/` | Detail (+ `_permissions`) | YES |
| `POST /transactions/{id}/accept/` | Accept | YES |
| `POST /transactions/{id}/deny/` | Deny | YES |
| `POST /transactions/{id}/cancel/` | Cancel | YES |
| `POST /transactions/{id}/approve/` | Approve pending review | YES |
| `GET /transactions/types/?context_type=platform` | List types | YES |

**Platform-specific guards in services:**
- `_check_member_quota()` — supports PlatformAccount.max_members (`services.py:893-901`)
- `_check_open_member_request()` — supports PlatformAccount.open_member_request (`services.py:923-930`)
- Conflict group cross-type detection — works for `platform_membership` group

**Transaction Settings (Form Mappings):**
- `GET/POST /transactions/form-mappings/?account_type=platform&account_id={id}` — SUPPORTED
- `DELETE /transactions/form-mappings/{id}/` — SUPPORTED
- Requires `can_configure_transactions` permission (platform_only scope)

**Files:** `apps/transaction/api/views.py`, `apps/transaction/services.py`, `apps/transaction/types.py`

**Verdict:** FULLY READY for pconsole. All transaction flows work identically.

---

### 2.4 Form System

#### Model Support

**File:** `apps/forms/models.py`

| Field | Values | Platform Support |
|-------|--------|-----------------|
| `FormTemplate.owner_type` | `system`, `platform`, `business` | YES |
| `FormTemplate.scope` | `platform`, `business` | YES |
| `FormResponse.context_type` | `platform`, `business` | YES |
| `TransactionFormMapping.account_type` | `platform`, `business`, `user` | YES |

**Form endpoints are GENERIC** via `account_type`/`account_id` parameters:

| Endpoint | Platform Support |
|----------|-----------------|
| `GET /{account_type}/{account_id}/forms/templates/` | YES |
| `POST /{account_type}/{account_id}/forms/templates/` | YES |
| `GET /{account_type}/{account_id}/forms/templates/{id}/` | YES (+ `_permissions`) |
| `PATCH /{account_type}/{account_id}/forms/templates/{id}/` | YES |
| `POST /{account_type}/{account_id}/forms/templates/{id}/publish/` | YES |
| `GET /{account_type}/{account_id}/forms/responses/` | YES |
| Form fields CRUD | YES |

**Files:** `apps/forms/api/views.py`, `apps/forms/models.py`

**Verdict:** FULLY READY for pconsole.

---

### 2.5 CMS System

#### Model Ownership

**File:** `apps/cms/models.py`

Site model uses `owner_type`/`owner_id` polymorphic pattern:
- `OwnerType.PLATFORM` — platform-owned sites (current default)
- `OwnerType.BUSINESS` — business-owned sites (model ready, not used)
- `OwnerType.SYSTEM` — system-wide sites

All CMS views use `PlatformContextMixin` for actor context resolution.

#### CMS Endpoints (All platform-scoped)

| Endpoint | View | Status |
|----------|------|--------|
| `GET/POST /cms/sites/` | AdminSiteListCreateView | READY |
| `GET/PATCH/DELETE /cms/sites/{id}/` | AdminSiteDetailView | READY |
| `GET/POST /cms/sites/{id}/pages/` | AdminPageListCreateView | READY |
| `GET /cms/pages/{id}/` | AdminPageDetailView | READY |
| `POST /cms/pages/{id}/publish/` | AdminPagePublishView | READY |
| `GET/POST /cms/section-templates/` | AdminSectionTemplateListCreateView | READY |
| `GET/POST /cms/block-templates/` | AdminBlockTemplateListCreateView | READY |
| `GET/PATCH /cms/block-placements/{id}/` | AdminBlockPlacementDetailView | READY |
| `GET /cms/block-placements/{id}/history/` | AdminBlockPlacementHistoryView | READY |
| `POST /cms/block-placements/{id}/rollback/` | AdminBlockPlacementRollbackView | READY |
| `GET/POST /cms/media/` | AdminMediaFileListCreateView | READY |
| `GET/PATCH/DELETE /cms/media/{id}/` | AdminMediaFileDetailView | READY |
| `GET/POST /cms/api-keys/` | AdminApiKeyListCreateView | READY |
| `DELETE /cms/api-keys/{id}/` | AdminApiKeyDetailView | READY |

**CMS Permissions:** 23 permissions seeded (12 structural + 8 content + 3 media).

**GAP:** CMS views use `IsAuthenticated` only — no RBAC permission gate enforcement. Permission codes exist in registry but are not checked in views.

**Files:** `apps/cms/api/views.py` (694 lines), `apps/cms/api/urls.py`

**Verdict:** READY for pconsole (endpoints work), but needs RBAC enforcement before production.

---

### 2.6 Tier 1.5 Permission-Aware Responses

| View | `_permissions` Keys | `_relationship` | Status |
|------|-------------------|-----------------|--------|
| PlatformAccountView | `can_view`, `can_edit_profile`, `can_edit_settings` | YES (membership + active transaction) | READY |
| PlatformProfileView | `can_view`, `can_edit_profile`, `can_edit_settings` | No | READY |
| PlatformMemberDetailView | `can_change_role`, `can_suspend`, `can_remove`, `can_ban`, `can_reactivate` | N/A | READY |
| PlatformRoleDetailView | `can_edit`, `can_delete`, `can_modify_permissions` | N/A | READY |

**Verdict:** FULLY READY for pconsole. Same Tier 1.5 pattern as business.

---

## 3. gconsole — Global Console

### 3.1 Concept & Separation from pconsole

gconsole provides **cross-account management** tools for the platform owner and members with `global_only`/`platform_and_global` scoped permissions. Unlike pconsole (which manages the platform's own account), gconsole manages ALL accounts on the platform.

| Feature | pconsole | gconsole |
|---------|----------|---------|
| **Manages** | Platform account (self) | All businesses + all users |
| **Members page** | Platform's own members | N/A (or all users) |
| **Transactions** | Platform membership invitations/requests | N/A (view all transactions) |
| **Forms** | Platform-scoped form templates | N/A (view all forms) |
| **CMS** | Platform-owned sites | Same (CMS is platform-only) |
| **Audit logs** | Platform-scoped | Global audit logs |
| **Settings** | Platform settings | Global settings |
| **Business management** | N/A | List/suspend/reactivate/verify businesses |
| **User management** | N/A | List/suspend/ban/verify users |

### 3.2 Current Global Capabilities

#### Permission Scope Architecture (READY)

**File:** `apps/core/constants.py:47-53`

```
PermissionScope:
  BUSINESS           = "business"          → bconsole
  PLATFORM_ONLY      = "platform_only"     → pconsole
  GLOBAL_ONLY        = "global_only"       → gconsole
  PLATFORM_AND_GLOBAL = "platform_and_global" → pconsole + gconsole
```

**ActorContext global permission check** (`apps/core/types.py:71-76`):

```python
def has_global_permission(self, code: str) -> bool:
    return any(
        c == code and s in ("global_only", "platform_and_global")
        for c, s in self.permissions_snapshot
    )
```

This method exists and is callable from any view. Foundation is READY.

#### Global-Scoped Permissions (Already Seeded)

| Permission | Scope | gconsole Feature |
|------------|-------|------------------|
| `can_suspend_business` | global_only | Business management |
| `can_remove_business_owner` | global_only | Business management |
| `can_transfer_business_ownership` | global_only | Business management |
| `can_view_businesses` | global_only, platform_only | Business directory |
| `can_approve_verification_request` | platform_only, global_only | Business verification |
| `can_approve_business_creation` | platform_only | Business creation approval |
| `can_view_all_transactions` | global_only, platform_and_global | Transaction oversight |
| `can_view_audit_logs` | all scopes | Audit trail |
| `can_edit_business` | global_only | Business profile editing |
| `can_edit_profile` | global_only | Profile editing |
| `can_invite_member` | global_only | Cross-account member management |
| `can_remove_member` | global_only | Cross-account member removal |
| `can_change_member_role` | global_only | Cross-account role changes |
| `can_suspend_member` | global_only | Cross-account member suspension |
| `can_ban_member` | global_only | Cross-account member banning |
| `can_view_members` | global_only | Cross-account member viewing |
| `can_assign_cms_to_business` | global_only | CMS assignment |

**17 global-scoped permissions already exist.** These permissions are assigned to:
- **Platform Owner** (level 0) — gets ALL with broadest scope
- **Global Moderator** (level 5) — gets all `global_only` permissions

#### Two-Plane Authority Model (READY)

**File:** `apps/rbac/policies.py:30-200` — `MembershipPolicy.authorize_action()`

The authorization system already supports cross-account actions:

1. **Same-Account** (pconsole/bconsole): Actor and target in same account. Dominance rule applies (actor.level < target.level).
2. **Cross-Account** (gconsole): Actor (platform member) acting on target (business member). Dominance rule SKIPPED. Only `global_only`/`platform_and_global` scoped permissions count.

**Key rule:** Platform Owner is invincible even from cross-account actions. Business Owners CAN be acted upon by platform with global permission.

**Verdict:** Authorization engine is FULLY READY for gconsole.

### 3.3 Missing Global Endpoints

#### Business Management (MISSING)

| Endpoint | Purpose | Permission Required | Status |
|----------|---------|---------------------|--------|
| `GET /admin/businesses/` | List all businesses (filters, search, pagination) | `can_view_businesses` (global) | MISSING |
| `GET /admin/businesses/{id}/` | Business detail (full data + stats) | `can_view_businesses` (global) | MISSING |
| `POST /admin/businesses/{id}/suspend/` | Suspend business | `can_suspend_business` (global) | MISSING |
| `POST /admin/businesses/{id}/reactivate/` | Reactivate suspended business | `can_suspend_business` (global) | MISSING |
| `POST /admin/businesses/{id}/verify/` | Approve/reject verification | `can_approve_verification_request` | MISSING |
| `POST /admin/businesses/{id}/transfer-ownership/` | Force ownership transfer | `can_transfer_business_ownership` | MISSING |

**Note:** Business suspend/reactivate services EXIST (`BusinessAccountService.suspend()`/`.reactivate()`), but are only accessible via Django admin (staff-only). Views need to be created with RBAC gates instead of staff checks.

#### User Management (MISSING)

| Endpoint | Purpose | Permission Required | Status |
|----------|---------|---------------------|--------|
| `GET /admin/users/` | List all users (filters, search, pagination) | New: `can_view_all_users` | MISSING |
| `GET /admin/users/{id}/` | User detail | New: `can_view_all_users` | MISSING |
| `POST /admin/users/{id}/suspend/` | Suspend user account | New: `can_suspend_user` | MISSING |
| `POST /admin/users/{id}/unsuspend/` | Unsuspend user | New: `can_suspend_user` | MISSING |
| `POST /admin/users/{id}/ban/` | Ban user | New: `can_ban_user` | MISSING |

**Note:** No user management services exist beyond the current user. Need new `UserAdminService` with suspend/ban/unsuspend operations.

#### Audit Log Endpoints (MISSING)

| Endpoint | Purpose | Permission Required | Status |
|----------|---------|---------------------|--------|
| `GET /admin/audit-logs/` | List audit logs (filters, pagination) | `can_view_audit_logs` (global) | MISSING |
| `GET /admin/audit-logs/{id}/` | Audit log entry detail | `can_view_audit_logs` (global) | MISSING |

**Note:** `AuditLog` model is fully implemented (`apps/core/observability/audit/models.py`) with 50+ action types. Data is persisted but has NO API endpoints. Only accessible via Django admin.

#### Global Statistics (MISSING)

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `GET /admin/stats/` | Platform-wide statistics (users, businesses, transactions) | MISSING |

### 3.4 Permission Architecture for gconsole

#### Access Model: pconsole vs gconsole

**Core principle:** Every platform member is a platform member first. ALL platform members can access pconsole (just like all business members can access bconsole). What they SEE and DO inside pconsole is gated by their `platform_only` permissions. gconsole is an ADDITIONAL, restricted console — only accessible to members who have at least one `global_only` or `platform_and_global` scoped permission.

```
Platform Member
  ├── pconsole (ALWAYS accessible — content gated by platform_only permissions)
  └── gconsole (ONLY if member has global-scoped permissions — content gated by global_only permissions)
```

#### Access Matrix

| Member Type | pconsole Access | pconsole Content | gconsole Access | gconsole Content |
|-------------|----------------|------------------|-----------------|------------------|
| **Platform Owner** | YES | Full (all `platform_only` + `platform_and_global` permissions) | YES | Full (all `global_only` + `platform_and_global` permissions) |
| **Member with global + platform permissions** | YES | Based on `platform_only` permissions | YES | Based on `global_only` permissions |
| **Member with global-only permissions** (e.g., Global Moderator) | YES | Base view (no `platform_only` permissions = read-only / minimal) | YES | Based on `global_only` permissions |
| **Member with platform-only permissions** (e.g., Platform Admin) | YES | Based on `platform_only` permissions | NO | No access (no global-scoped permissions) |
| **Base Member** (no permissions) | YES | Base view (read-only / minimal) | NO | No access |

#### Examples with Default Roles

| Role | Level | pconsole | gconsole | Explanation |
|------|-------|----------|---------|-------------|
| **Platform Owner** | 0 | Full access (all tools visible) | Full access (all management tools) | Has ALL permissions at broadest scope (`platform_and_global`) |
| **Platform Admin** | 2 | Full platform management (members, roles, forms, CMS, etc.) | NO ACCESS | Only has `platform_only` scoped permissions — no global scope |
| **Global Moderator** | 5 | Base view only (can see dashboard, profile — no management tools) | Cross-account management (business/user oversight) | Only has `global_only` scoped permissions — sees pconsole but can't manage platform-specific resources |
| **Base Member** | 10 | Base view only (dashboard, profile) | NO ACCESS | No permissions at all |
| **Custom role (both scopes)** | 3 | Based on assigned `platform_only` permissions | Based on assigned `global_only` permissions | Custom role can have permissions in both scopes |

#### Key Insight

pconsole and gconsole are NOT mutually exclusive. A member can have access to BOTH if their role includes permissions in both scopes. The consoles serve different purposes:

- **pconsole** = "manage the platform's own account" (members, forms, CMS, transactions, settings) — scoped by `platform_only`
- **gconsole** = "manage everything on the platform" (all businesses, all users, audit, global settings) — scoped by `global_only`

This mirrors how a single user can be a member of business A AND business B, seeing different bconsoles. Here, a platform member sees pconsole (their platform account) AND optionally gconsole (global management) depending on their permission scopes.

#### Guard Strategy

**pconsole Guard (PlatformGuard — already exists):**
1. User has an active platform membership → grant access
2. UI elements gated by `platform_only` permissions via `<Can>` component
3. Same pattern as BusinessGuard for bconsole

**gconsole Guard (NEW — GconsoleGuard):**
1. User has an active platform membership (same as pconsole)
2. **AND** user has at least one permission with `global_only` or `platform_and_global` scope
3. If no global permissions → "Access Denied" (not a global administrator)
4. UI elements inside gconsole gated by specific `global_only` permissions via `<Can>`

**Backend:** Reuse `PlatformContextMixin` for both consoles — gconsole actors ARE platform members. The difference is which permissions are checked:
- pconsole views call `actor_context.has_permission(code)` (any scope matches)
- gconsole views call `actor_context.has_global_permission(code)` (only `global_only`/`platform_and_global` match)

**Frontend:** `GconsoleGuard` needs a way to know if the user has ANY global permission. Options:
- Expose `has_global_permissions: boolean` on the membership API response
- Or check `permissions_snapshot` client-side for any `global_only`/`platform_and_global` scope
- Or add a `can_access_gconsole` computed flag to `MyMembershipOutputSerializer`

---

## 4. Frontend Guards & Routing

### Current Guards

| Guard | Checks | Context | Status |
|-------|--------|---------|--------|
| `AuthGuard` | JWT token | User | READY |
| `BusinessGuard` | Membership + slug + `active`/`pending_approval` | Business | READY |
| `PlatformGuard` | Membership + `active`/`pending_approval` | Platform | READY |
| `AdminGuard` | `is_staff` or `is_superuser` | User | READY (not for gconsole) |
| `GconsoleGuard` | Platform membership + global permissions | Platform/Global | **MISSING** |

**Files:** `frontend/src/components/guards/`

### Current Route Structure

| Context | Routes | Status |
|---------|--------|--------|
| `(app)/bconsole/[slug]/` | dashboard, profile, members, forms, content, media, transactions, audit, settings | READY |
| `(app)/pconsole/` | dashboard, profile, members, businesses, cms, forms, media, transactions, audit, settings | READY |
| `(app)/admin/` | dashboard (stub) | EXISTS |
| `(app)/gconsole/` | N/A | **MISSING** |

### Navigation Config

**File:** `frontend/src/lib/navigation-config.ts`

```typescript
type NavContextType = "personal" | "business" | "platform"
// MISSING: "global" context type
```

**Platform nav sections (pconsole):**
- OVERVIEW: Dashboard, Profile
- TEAM: Members (minMembers: 2)
- CONTENT: Forms, Templates, API Keys, Media
- OPERATIONS: Transactions, Audit, Settings

**gconsole nav sections needed:**
- OVERVIEW: Dashboard (global stats)
- MANAGEMENT: Businesses, Users
- MONITORING: Audit Logs, Transactions (global)
- SETTINGS: Platform Settings

---

## 5. Gap Summary

### pconsole Gaps (Backend)

| # | Gap | Severity | Effort | Notes |
|---|-----|----------|--------|-------|
| P-1 | Platform Owner membership not auto-created on configure | MEDIUM | 1 hour | `PlatformAccountService.configure()` needs owner membership creation |
| P-2 | CMS views lack RBAC permission enforcement | MEDIUM | 4 hours | Views use `IsAuthenticated` only, not checking CMS permission codes |
| P-3 | PlatformPolicy mixes Django staff checks with RBAC | LOW | 2 hours | `can_update_profile` checks `is_staff` instead of RBAC permission |

### pconsole Gaps (Frontend)

| # | Gap | Severity | Notes |
|---|-----|----------|-------|
| PF-1 | Platform member/role management pages | HIGH | Backend ready, need UI mirroring bconsole |
| PF-2 | Platform transaction pages | HIGH | Backend ready, need UI |
| PF-3 | Platform form builder pages | HIGH | Backend ready, need UI |
| PF-4 | Platform profile edit page | HIGH | Backend ready, need UI |
| PF-5 | Platform settings page | HIGH | Backend ready, need UI |
| PF-6 | Platform dashboard page | MEDIUM | Need content/stats |

### gconsole Gaps (Backend)

| # | Gap | Severity | Effort | Notes |
|---|-----|----------|--------|-------|
| G-1 | Business management API endpoints | HIGH | 2-3 days | Services exist, views missing. Need list/detail/suspend/reactivate/verify |
| G-2 | User management API endpoints | HIGH | 2-3 days | No services or views exist. Need full new service + views |
| G-3 | Audit log retrieval API endpoints | HIGH | 1-2 days | Model exists, selectors/views missing |
| G-4 | New permissions: `can_view_all_users`, `can_suspend_user`, `can_ban_user` | MEDIUM | 2 hours | Data migration to seed |
| G-5 | Global statistics endpoint | LOW | 1 day | Aggregate queries across models |
| G-6 | CMS permission enforcement | MEDIUM | 4 hours | Same as P-2 |

### gconsole Gaps (Frontend)

| # | Gap | Severity | Notes |
|---|-----|----------|-------|
| GF-1 | GconsoleGuard component | HIGH | Check platform membership + global permissions |
| GF-2 | gconsole route structure | HIGH | `/gconsole/` with layout + nested routes |
| GF-3 | gconsole navigation config | HIGH | New nav context with management sections |
| GF-4 | Business management pages | HIGH | List/detail/actions for all businesses |
| GF-5 | User management pages | HIGH | List/detail/actions for all users |
| GF-6 | Global audit log viewer | MEDIUM | Filterable log viewer |
| GF-7 | Global dashboard | MEDIUM | Platform-wide statistics |

---

## 6. Recommendations

### pconsole Implementation Order

1. **Fix P-1 first** (Platform Owner auto-membership) — required for any pconsole testing
2. **Frontend pages PF-1 through PF-6** — mirror bconsole components, reuse `features/members/`, `features/forms/`, `features/transactions/`
3. **Fix P-2** (CMS permission enforcement) — before going to production
4. **Fix P-3** (policy consistency) — low priority cleanup

### gconsole Implementation Order

**Phase 1: Foundation**
- Create GconsoleGuard (GF-1)
- Create gconsole route structure (GF-2, GF-3)
- Seed new permissions G-4

**Phase 2: Business Management**
- Backend: G-1 (business admin endpoints)
- Frontend: GF-4 (business management pages)

**Phase 3: User Management**
- Backend: G-2 (user admin endpoints + service)
- Frontend: GF-5 (user management pages)

**Phase 4: Monitoring**
- Backend: G-3 (audit log endpoints)
- Frontend: GF-6, GF-7 (audit viewer + dashboard)

### Key Architectural Decision

**Both pconsole and gconsole use Platform membership** (NOT separate membership systems). This means:

- **All platform members** access pconsole — UI gated by `platform_only` permissions
- **Platform members with global-scoped permissions** ALSO access gconsole — UI gated by `global_only` permissions
- A single member can access BOTH consoles if their role has permissions in both scopes
- Backend uses `PlatformContextMixin` for both — the difference is `has_permission()` (any scope, pconsole) vs `has_global_permission()` (global scope only, gconsole)
- No new `AccountType.GLOBAL` needed — global authority flows through platform membership
- GconsoleGuard checks: active platform membership + at least one `global_only`/`platform_and_global` permission

---

## 7. File Reference

### Backend — Platform Organization
| File | Lines | Purpose |
|------|-------|---------|
| `apps/organization/platform/models.py` | 95 | PlatformAccount (singleton) + PlatformProfile |
| `apps/organization/platform/services.py` | 294 | Configure + update settings/profile |
| `apps/organization/platform/selectors.py` | 68 | Get singleton + existence checks |
| `apps/organization/platform/views.py` | 332 | Account, Profile, Settings endpoints |
| `apps/organization/platform/serializers.py` | 121 | Input/output serializers |
| `apps/organization/platform/policies.py` | 107 | Platform authorization policies |
| `apps/organization/platform/urls.py` | 38 | URL routing |
| `apps/organization/platform/admin.py` | 53 | Django admin (singleton protection) |

### Backend — Platform RBAC
| File | Lines | Purpose |
|------|-------|---------|
| `apps/rbac/services.py` | 122-217 | `initialize_platform_account()` — 4 roles + permission assignment |
| `apps/rbac/views.py` | 652-847 | Platform role endpoints (7 endpoints) |
| `apps/rbac/views.py` | 854-1131 | Platform member endpoints (8 endpoints) |
| `apps/rbac/policies.py` | 30-200 | `MembershipPolicy.authorize_action()` — two-plane authority |
| `apps/rbac/policies.py` | 203-295 | `RolePolicy` — hierarchy constraints |
| `apps/rbac/migrations/0002` | — | 25 base permissions |
| `apps/rbac/migrations/0003` | — | 2 transaction permissions |
| `apps/rbac/migrations/0004` | — | 23 CMS permissions |
| `apps/rbac/migrations/0007` | — | 1 configure_transactions permission |

### Backend — Transaction System (Generic)
| File | Lines | Purpose |
|------|-------|---------|
| `apps/transaction/types.py` | 44-92 | 3 platform transaction type configs |
| `apps/transaction/services.py` | 45-350 | `create_invitation()`, `create_request()` — platform-aware |
| `apps/transaction/services.py` | 860-934 | `_check_member_quota()`, `_check_open_member_request()` — platform support |
| `apps/transaction/api/views.py` | 83-182 | Generic transaction endpoints |
| `apps/transaction/policies.py` | 71-85 | `PLATFORM_AUTHORITY` approver policy |

### Backend — Form System (Generic)
| File | Lines | Purpose |
|------|-------|---------|
| `apps/forms/models.py` | 17-54 | `owner_type` supports platform |
| `apps/forms/api/views.py` | — | Generic via `account_type`/`account_id` params |

### Backend — CMS System
| File | Lines | Purpose |
|------|-------|---------|
| `apps/cms/models.py` | 34-108 | Site model with `owner_type` polymorphism |
| `apps/cms/api/views.py` | 1-694 | 14 admin views (platform-scoped) |

### Backend — Core Authority
| File | Lines | Purpose |
|------|-------|---------|
| `apps/core/constants.py` | 47-53 | `PermissionScope` enum (4 scopes) |
| `apps/core/types.py` | 22-185 | `ActorContext` with `has_global_permission()` |
| `apps/core/views.py` | — | `PermissionInjectMixin`, `RelationshipInjectMixin` |
| `apps/rbac/views.py` | 56-135 | `AccountContextMixin`, `PlatformContextMixin` |

### Frontend — Guards & Routes
| File | Purpose |
|------|---------|
| `src/components/guards/BusinessGuard.tsx` | Membership + slug check |
| `src/components/guards/PlatformGuard.tsx` | Membership check (singleton) |
| `src/components/guards/AdminGuard.tsx` | `is_staff`/`is_superuser` check |
| `src/lib/navigation-config.ts` | Nav sections per context |
| `src/app/(app)/pconsole/` | Platform console routes |
| `src/app/(app)/bconsole/[slug]/` | Business console routes |

---

*End of review.*
