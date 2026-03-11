# Member Management System — Frontend High-Level Description

> **Status:** Description (pre-plan)
> **Date:** 2026-03-04
> **Scope:** Frontend implementation for member list, member detail, role management, and permission assignment
> **Depends on:** Frontend Foundation, RBAC system, Member Quota system, Transaction System Frontend (invite flow)
> **Related:** Transaction System Frontend (invite member triggers transaction), Form System Frontend (member's submitted forms)

---

## 1. Overview

The Member Management System frontend provides organization administrators with tools to
view members, manage their roles and statuses, configure custom roles with granular permissions,
and monitor member activity. It is built on top of a **complete backend** (5 membership statuses,
role hierarchy with level dominance, 10 membership permissions, 16 audit actions) and leverages
the existing **3-tier authorization** infrastructure for permission-aware UI.

### Core Principles

| Principle | Implementation |
|-----------|---------------|
| **Solo accounts excluded** | Entire Members section hidden when `max_members <= 1` via `minMembers: 2` on nav item |
| **Permission-aware everywhere** | Nav gating (Tier 1), API `_permissions` (Tier 1.5 — needs backend work), Guards (Tier 2), Backend policies (Tier 3) |
| **Consistent with app patterns** | Uses existing guards, `<Can>` component, `useFilteredNav`, membership store |
| **Dominance rule enforced** | Higher-level members (lower number) cannot be managed by lower-level members (higher number) |
| **Quota-aware** | Member count vs max shown; Invite button disabled when quota is full |
| **RolePicker reused** | Same `<RolePicker>` component from Transaction System (level-filtered, Owner excluded) |

---

## 2. Routes

All routes are within the console layout, behind `BusinessGuard` or `PlatformGuard`.

### Business Console Routes

| Route | Page | Permission Gate |
|-------|------|----------------|
| `/bconsole/[slug]/members` | Member & Role Dashboard | `can_view_members` |
| `/bconsole/[slug]/members/[id]` | Member Detail | `can_view_members` |
| `/bconsole/[slug]/members/roles/[id]` | Role Detail (permissions editor) | `can_view_members` |

### Platform Console Routes

| Route | Page | Permission Gate |
|-------|------|----------------|
| `/pconsole/members` | Member & Role Dashboard | `can_view_members` |
| `/pconsole/members/[id]` | Member Detail | `can_view_members` |
| `/pconsole/members/roles/[id]` | Role Detail (permissions editor) | `can_view_members` |

> **Note:** Platform is treated the same as business in pconsole for now. Global console
> (gconsole) for cross-account management is a future consideration.

---

## 3. Navigation Config

**Nav section:** "Members" — appears in bconsole and pconsole sidebar.

```
Members section:
  permission: "can_view_members"
  minMembers: 2
  items:
    - Members (dashboard) → /bconsole/[slug]/members
```

**Single nav item** pointing to the dashboard. Member detail and role detail are sub-routes
navigated to from the dashboard, not separate nav items.

**Visibility rules:**
- Hidden entirely when `max_members <= 1` (solo account)
- Hidden when user lacks `can_view_members` permission
- Owner always sees it (has all permissions)

---

## 4. Pages

### 4.1 Member & Role Dashboard (`/members`)

**Single dashboard page** with two main panels: Members and Roles.

#### Members Panel

**Header bar:**
- Title: "Members" with count badge (`3 / 10` — current count / max quota)
- Quota progress bar (visual indicator of capacity)
- "Invite Member" button — navigates to `/transactions/invitations` with pre-selected transaction type
  (e.g., `?type=business_membership_invitation`), or opens a dedicated invitation dialog/modal
  (design decision — see Open Design Questions)
  - **Permission gate:** `<Can allowed={permissions.can_invite_member}>`
  - **Quota gate:** Disabled with tooltip "Member limit reached (10/10)" when `current_count >= max_members` (and max_members > 0)

**Member list (table/card view):**

| Column | Source | Notes |
|--------|--------|-------|
| Avatar | User profile `avatar` | Fallback to initials |
| Name | User profile `display_name` or `full_name` | Falls back to `username` |
| Email | User `email` | Always shown |
| Role | Membership `role_name` | With level badge |
| Status | Membership `status` | Color-coded badge |
| Joined | Membership `joined_at` | Relative time |
| Actions | `_permissions` from Tier 1.5 | Edit button → member detail |

**Filters (URL-synced):**
- Status: All / Active / Suspended / Removed / Banned / Left
- Role: Dropdown of account roles
- Search: By name or email (client-side for MVP, backend search later)

**Empty states:**
- No members: "No team members yet. Invite your first member."
- No results: "No members match your filters."

#### Roles Panel

**Header bar:**
- Title: "Roles" with count
- "Create Role" button
  - **Permission gate:** `<Can allowed={permissions.can_create_role}>`

**Role list (cards or rows):**

| Column | Source | Notes |
|--------|--------|-------|
| Name | Role `name` | System roles marked with badge |
| Level | Role `level` | 0-10 with visual indicator |
| System | Role `is_system_role` | Lock icon if system |
| Description | Role `description` | Truncated |
| Actions | Level dominance + permission check | Edit (→ role detail), Delete |

**Role actions (per row):**
- **Edit** — navigates to role detail page
  - Visible when: actor has `can_edit_role` AND outranks the role AND not a system role
- **Delete** — confirmation dialog
  - Visible when: actor has `can_delete_role` AND outranks the role AND not a system role
  - Blocked if role has active members (backend returns error, UI shows message)

**System roles** (Owner, Base Member) are always shown but with no edit/delete actions.

---

### 4.2 Member Detail Page (`/members/[id]`)

**Layout:** Two-column or stacked layout with member profile and management actions.

#### Profile Section

Displays the member's **public profile data** alongside their **membership info**.

**User profile fields:**

| Field | Source | Notes |
|-------|--------|-------|
| Avatar | User profile `avatar` | Large display |
| Display Name | User profile `display_name` | Primary heading |
| Full Name | User profile `full_name` | Secondary if different |
| Email | User `email` | Always shown |
| Username | User `username` | With `@` prefix |
| Bio | User profile `bio` | If available |
| Country | User profile `country` | If available |
| City | User profile `city` | If available |

**Membership info fields:**

| Field | Source | Notes |
|-------|--------|-------|
| Role | Membership `role.name` | With level indicator |
| Status | Membership `status` | Color-coded badge |
| Joined | Membership `joined_at` | Formatted date |
| Owner | Membership `is_owner` | Crown/star badge if true |
| Status Changed | Membership `status_changed_at` | If applicable |
| Status Reason | Membership `status_reason` | If suspended/banned/removed |

#### Action Buttons (Permission-Gated)

All buttons gated by Tier 1.5 `_permissions` from member detail API response.

| Action | Visible When | Dialog | Backend Endpoint |
|--------|-------------|--------|-----------------|
| Change Role | `_permissions.can_change_role` | RolePicker dialog | `PATCH /members/{id}/role/` |
| Suspend | `_permissions.can_suspend` | Reason field (optional) | `POST /members/{id}/suspend/` |
| Reactivate | `_permissions.can_reactivate` (suspended only) | Confirmation | **No endpoint exists — backend gap** |
| Remove | `_permissions.can_remove` | Reason field (optional) | `POST /members/{id}/remove/` |
| Ban | `_permissions.can_ban` | Reason field (required) | `POST /members/{id}/ban/` |

> **Backend gap:** The suspend/remove/ban views each hardcode a single target status.
> There is no "reactivate" endpoint. The service method `update_membership_status(status=ACTIVE)`
> exists and uses `can_suspend_member` permission, but no view exposes it.
> **Required:** Add `POST /members/{id}/reactivate/` endpoint (or make suspend view bidirectional).

**Action rules (enforced by backend, reflected in `_permissions`):**
- **Dominance:** Actor can only act on members they outrank (lower level number)
- **Owner invincibility:** No actions available on the account owner
- **Self-protection:** Cannot suspend/remove/ban yourself (use "Leave" instead)
- **Status-dependent:** Reactivate only visible for suspended members

**Leave button** (separate from management actions):
- Visible to the member viewing their own membership
- Not visible to owner (owner cannot leave — must transfer ownership first)
- Confirmation dialog: "Are you sure you want to leave this organization?"

**Change Role dialog:**
- Uses `<RolePicker>` component (same as Transaction System)
- Level-filtered: only roles the actor can assign (outranks)
- Owner role (level 0) always excluded
- Current role pre-selected and shown as "Current"
- Submit: `PATCH /members/{id}/role/` with `{ role_id: "..." }`

#### Form Responses Section

**Purpose:** Show form responses submitted by this member within the organization.

**Data source:** Form responses where `submitted_by = member.user.id` AND form belongs to this account.

**Display:**
- List of form responses with template name, submission date, status
- Click to navigate to response detail (in Form System routes)
- Empty state: "This member hasn't submitted any forms yet."

> **Backend gap:** No endpoint currently filters form responses by account + user.
> Need new selector method: `list_by_account_and_submitter(account_type, account_id, user_id)`

---

### 4.3 Role Detail Page (`/members/roles/[id]`)

**Purpose:** View and edit a role's permissions.

**Permission gate:** `can_view_members` to view, `can_edit_role` to modify.

#### Role Info Header

| Field | Editable | Notes |
|-------|----------|-------|
| Name | Yes (if can edit + not system role) | Inline edit or form |
| Level | No | Displayed with badge, immutable after creation |
| Description | Yes (if can edit + not system role) | Textarea |
| System Role | No | Badge indicator |
| Member Count | No | "5 members with this role" |

#### Permissions Editor

**Layout:** Searchable checklist of all available permissions, grouped by category.

**Permission categories (from backend seeds):**

| Category | Permissions Count | Examples |
|----------|------------------|---------|
| Membership | 7 | can_invite_member, can_remove_member, can_view_members |
| Roles | 3 | can_create_role, can_edit_role, can_delete_role |
| Settings | 3 | can_edit_business, can_edit_profile, can_view_settings |
| Platform | 6 | can_suspend_business, can_view_businesses |
| Audit | 1 | can_view_audit_logs |
| Forms | 6 | can_create_form, can_view_responses |
| Transactions | 2 | can_view_transactions, can_view_all_transactions |
| CMS Structure | 12 | can_create_cms_site, can_edit_cms_page |
| CMS Content | 8 | can_edit_cms_content, can_publish_cms_content |
| CMS Media | 3 | can_upload_cms_media, can_delete_cms_media |

**Search behavior:**
- Type `"user"` → filters to permissions containing "user" in code or name
- Type `"can_invite"` → shows `can_invite_member`
- Category headers remain visible when any child matches
- Clear search to show all

**Each permission row shows:**
- Checkbox (checked if assigned to this role)
- Permission name (human readable)
- Permission code (monospace, secondary text)
- Scope selector (dropdown: business, platform_only, global_only, platform_and_global)
  - Only shows scopes valid for that permission (`applicable_scopes` from backend)
  - Auto-selects first valid scope when toggling on

**Interaction:**
- Toggle checkbox → calls add/remove permission endpoint
- Change scope → calls remove + add with new scope (atomic in UI, two calls)
- All changes are immediate (no "Save" button — each toggle is a mutation)

**System role view:** When viewing a system role (Owner, Base Member), permissions are shown
as read-only (checkboxes disabled, no scope selector). Label: "System role — permissions cannot be modified."

**Dominance guard:** If actor cannot modify this role (doesn't outrank it), all controls are disabled.
Show read-only view with message: "You don't have sufficient authority to modify this role."

**Backend endpoints used:**
- `GET /permissions/` — all 51 permissions with categories and applicable_scopes
- `GET /roles/{id}/` — role detail with current role_permissions
- `POST /roles/{id}/permissions/` — add permission (permission_id, scope)
- `DELETE /roles/{id}/permissions/` — remove permission (permission_id)

---

## 5. Member Statuses & Actions

### 5.1 Status Definitions

| Status | Color | Icon | Description |
|--------|-------|------|-------------|
| `active` | Green | CheckCircle | Member in good standing |
| `suspended` | Yellow/Amber | PauseCircle | Temporarily inactive (can be reactivated) |
| `removed` | Gray | UserMinus | Removed by administrator |
| `banned` | Red | Ban | Permanently banned |
| `left` | Gray | LogOut | Voluntarily departed |

### 5.2 Available Actions Per Status

| Current Status | Available Actions | Permission Required |
|---------------|-------------------|-------------------|
| `active` | Suspend, Remove, Ban, Change Role | Respective permission + dominance |
| `suspended` | Reactivate, Remove, Ban | `can_suspend_member` (reactivate), others as needed |
| `removed` | — (terminal) | — |
| `banned` | — (terminal) | — |
| `left` | — (terminal) | — |

> **Note:** `restore_membership` (un-soft-delete) exists in backend but is a separate
> operation from status changes. This is an edge case — document but defer UI for now.

### 5.3 Confirmation Dialogs

All destructive member actions show a confirmation dialog:

| Action | Dialog Title | Has Reason Field | Reason Required |
|--------|-------------|-----------------|-----------------|
| Suspend | "Suspend Member" | Yes | No |
| Remove | "Remove Member" | Yes | No |
| Ban | "Ban Member" | Yes | Yes |
| Reactivate | "Reactivate Member" | No | — |
| Change Role | "Change Role" | No (has RolePicker instead) | — |
| Leave | "Leave Organization" | No | — |

---

## 6. Role Management

### 6.1 Create Role Dialog

Triggered from "Create Role" button on dashboard.

**Fields:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| Name | Text | Yes | max 100 chars, unique per account |
| Level | Number (1-10) | Yes | Must be > actor's level (can't create equal or higher authority) |
| Description | Textarea | No | Free text |

**Level constraint:** The level dropdown/input only shows valid values.
- Owner (level 0) can create levels 1-10
- Level 2 member can create levels 3-10
- Level 5 member can create levels 6-10

**After creation:** Redirect to role detail page to assign permissions.

### 6.2 Role Level System

Level is **immutable** after creation. This is by design — changing authority level of an
existing role could break permission assumptions for all assigned members.

**To change a role's authority level:**
1. Create new role at desired level
2. Reassign members to new role
3. Delete old role (only after all members reassigned)

### 6.3 Delete Role Flow

1. Click "Delete" on role card → confirmation dialog
2. Backend checks: no active members assigned to this role
3. If members exist → error message: "Cannot delete: X members are assigned to this role. Reassign them first."
4. If no members → role is soft-deleted
5. UI removes role from list

---

## 7. Quota Awareness

### 7.1 Member Count Display

The dashboard header shows the current member count relative to the quota:

```
Members (3 / 10)  [████████░░] 30%
```

- `current_count`: from `MembershipSelector.count_active_members()` (or member list length)
- `max_members`: from account's `max_members` field (available in membership store as `account_max_members`)
- When `max_members = 0`: show "Members (3)" with no cap indicator (unlimited)

### 7.2 Quota-Aware Buttons

| Button | Behavior When Quota Full | Behavior When Unlimited |
|--------|-------------------------|------------------------|
| "Invite Member" | Disabled + tooltip: "Member limit reached (10/10)" | Always enabled |
| Accept Request (Transaction UI) | Disabled + tooltip: "Cannot accept — member limit reached" | Always enabled |

**Quota check source:**
- Frontend: compare `current_count >= max_members` (when `max_members > 0`)
- Backend: double-checks via `RBACService.create_membership()` quota gate

### 7.3 Quota Info Card

Optional card/banner on dashboard:

```
Team Capacity: 3 of 10 members
[Upgrade plan to add more members] (if applicable)
```

---

## 8. Permission Matrix

### 8.1 RBAC Permissions Used

| Permission Code | Used For | UI Impact |
|----------------|----------|-----------|
| `can_view_members` | View member list and details | Nav visibility, page access |
| `can_invite_member` | "Invite Member" button | Button visibility on dashboard |
| `can_remove_member` | Remove member action | Action button on member detail |
| `can_change_member_role` | Change member's role | Action button on member detail |
| `can_suspend_member` | Suspend / reactivate member | Action button on member detail |
| `can_ban_member` | Ban member permanently | Action button on member detail |
| `can_approve_membership_request` | Accept incoming requests | Used in Transaction System |
| `can_create_role` | Create custom roles | Button on roles panel |
| `can_edit_role` | Edit role name/description/permissions | Edit controls on role detail |
| `can_delete_role` | Delete custom roles | Delete button on role card |

### 8.2 Tier Usage

| Tier | Where | How |
|------|-------|-----|
| **Tier 1** (Nav gating) | `useFilteredNav` hides Members section | `permission: "can_view_members"`, `minMembers: 2` |
| **Tier 1.5** (Response permissions) | Member detail `_permissions` dict | Gates action buttons (suspend, ban, remove, role change) |
| **Tier 2** (Route guard) | BusinessGuard / PlatformGuard on routes | Ensures user is a member of the account |
| **Tier 3** (Backend enforcement) | All mutation endpoints | `MembershipPolicy.authorize_action()` with dominance rule |

### 8.3 Proposed `_permissions` for Member Detail (Tier 1.5)

```python
# MembershipPolicy.get_viewer_permissions()
{
    "can_change_role": bool,     # Can actor change this member's role
    "can_suspend": bool,         # Can actor suspend this member
    "can_remove": bool,          # Can actor remove this member
    "can_ban": bool,             # Can actor ban this member
    "can_reactivate": bool,      # Can actor reactivate (suspended only)
}
```

**Logic (backend implementation needed):**
- Each boolean runs `authorize_action()` with the respective permission
- `can_reactivate` is `True` only when target status is `suspended` AND actor has `can_suspend_member`
- All booleans are `False` when target is the owner (owner invincibility)
- All booleans are `False` when actor doesn't outrank target (dominance rule)
- All booleans are `False` when viewing own membership (can't act on self)

### 8.4 Proposed `_permissions` for Role Detail (Tier 1.5)

```python
# RolePolicy.get_viewer_permissions()
{
    "can_edit": bool,            # Can actor edit this role's name/description
    "can_delete": bool,          # Can actor delete this role
    "can_modify_permissions": bool,  # Can actor add/remove permissions on this role
}
```

**Logic:**
- All `False` for system roles (`is_system_role = True`)
- All `False` when actor doesn't outrank the role (`actor.level >= role.level`)
- `can_delete` additionally `False` when role has active members

### 8.5 Role Visibility by Actor Level

| Actor Level | Can See | Can Create | Can Edit/Delete | Can Manage Members |
|-------------|---------|-----------|-----------------|-------------------|
| 0 (Owner) | All roles | Levels 1-10 | All non-system, levels 1-10 | All non-owner members |
| 2 (Admin) | All roles | Levels 3-10 | Non-system, levels 3-10 | Members at levels 3-10 |
| 5 (Moderator) | All roles | Levels 6-10 | Non-system, levels 6-10 | Members at levels 6-10 |
| 10 (Base Member) | All roles (read-only) | None | None | None |

> **Note:** All roles are *visible* (read-only) regardless of level. The level constraint
> only applies to *actions* (create, edit, delete, manage permissions, manage members).

---

## 9. Shared Components

### 9.1 RolePicker Component

**Reused from Transaction System description.** Same component for:
- Member role change dialog (this system)
- Invitation creation (Transaction System)
- Request acceptance (Transaction System)

```
<RolePicker
  accountType="business" | "platform"
  accountId={uuid}
  actorRoleLevel={number}
  value={selectedRoleId}
  onChange={setSelectedRoleId}
  required={true}
  excludeOwner={true}
/>
```

See Transaction System Frontend description, Section 10.6 for full specification.

### 9.2 MemberStatusBadge Component

Reusable status badge with color and icon:

| Status | Color | Icon |
|--------|-------|------|
| `active` | Green | CheckCircle |
| `suspended` | Amber | PauseCircle |
| `removed` | Gray | UserMinus |
| `banned` | Red | Ban |
| `left` | Gray | LogOut |

### 9.3 ConfirmActionDialog Component

Reusable confirmation dialog for destructive member actions:

```
<ConfirmActionDialog
  title="Suspend Member"
  description="This will temporarily revoke their access."
  confirmLabel="Suspend"
  variant="warning" | "destructive"
  showReasonField={true}
  reasonRequired={false}
  onConfirm={(reason?) => ...}
  onCancel={() => ...}
/>
```

### 9.4 QuotaBar Component

Displays member quota usage:

```
<QuotaBar
  current={currentMemberCount}
  max={maxMembers}           // 0 = unlimited
  label="Team Members"
/>
```

Shows progress bar when limited, simple count when unlimited.

---

## 10. Backend API Reference

### 10.1 Member Endpoints (per account type)

**Business context:** All prefixed with `/api/v1/business/{slug}/`
**Platform context:** All prefixed with `/api/v1/platform/`

| Method | Endpoint | Description | Input | Output |
|--------|----------|-------------|-------|--------|
| `GET` | `members/` | List members | `?include_all=true` | `MembershipListOutput[]` |
| `GET` | `members/{id}/` | Member detail | — | `MembershipOutput` |
| `PATCH` | `members/{id}/role/` | Change role | `{ role_id }` | `MembershipOutput` |
| `POST` | `members/{id}/suspend/` | Suspend | `{ reason? }` | `MembershipOutput` |
| `POST` | `members/{id}/remove/` | Remove | `{ reason? }` | `MembershipOutput` |
| `POST` | `members/{id}/ban/` | Ban | `{ reason? }` | `MembershipOutput` |
| `POST` | `members/leave/` | Self-leave | — | `MembershipOutput` |

### 10.2 Role Endpoints (per account type)

| Method | Endpoint | Description | Input | Output |
|--------|----------|-------------|-------|--------|
| `GET` | `roles/` | List roles | — | `RoleOutput[]` |
| `POST` | `roles/` | Create role | `{ name, level, description? }` | `RoleDetailOutput` |
| `GET` | `roles/{id}/` | Role detail | — | `RoleDetailOutput` |
| `PATCH` | `roles/{id}/` | Update role | `{ name?, description? }` | `RoleDetailOutput` |
| `DELETE` | `roles/{id}/` | Delete role | — | 204 |
| `POST` | `roles/{id}/permissions/` | Add permission | `{ permission_id, scope }` | `RoleDetailOutput` |
| `DELETE` | `roles/{id}/permissions/` | Remove permission | `{ permission_id }` | `RoleDetailOutput` |

### 10.3 Global Endpoints

| Method | Endpoint | Description | Output |
|--------|----------|-------------|--------|
| `GET` | `/api/v1/permissions/` | All permissions | `PermissionOutput[]` |
| `GET` | `/api/v1/me/memberships/` | User's memberships | `MyMembershipOutput[]` |

### 10.4 Serializer Field Reference

**MembershipListOutputSerializer (list view — lightweight):**
- `id`, `user` (id, email, username), `role_name`, `role_level`, `is_owner`, `status`, `joined_at`

**MembershipOutputSerializer (detail view — full):**
- `id`, `user` (id, email, username), `account_type`, `account_id`, `role` (full object),
  `is_owner`, `status`, `joined_at`, `status_changed_at`, `status_reason`, `created_at`, `updated_at`

**RoleDetailOutputSerializer (role detail):**
- `id`, `name`, `account_type`, `account_id`, `level`, `is_system_role`, `description`,
  `role_permissions` (nested with permission object + scope), `permission_count`, `created_at`, `updated_at`

**PermissionOutputSerializer:**
- `id`, `code`, `name`, `description`, `category`, `applicable_scopes`

---

## 11. Backend Gaps

### 11.1 Tier 1.5 — Permission Injection Missing

| Gap | Impact | Required Change |
|-----|--------|----------------|
| **No `PermissionInjectMixin` on member detail view** | Frontend can't gate action buttons | Add mixin to `BusinessMemberDetailView` + `PlatformMemberDetailView`, implement `MembershipPolicy.get_viewer_permissions()` |
| **No `PermissionInjectMixin` on role detail view** | Frontend can't gate edit/delete/permission controls | Add mixin to `BusinessRoleDetailView` + `PlatformRoleDetailView`, implement `RolePolicy.get_viewer_permissions()` |

### 11.2 Member User Serializer Too Slim

| Gap | Impact | Required Change |
|-----|--------|----------------|
| **`MemberUserOutputSerializer` only has id, email, username** | No avatar, display_name, bio for member cards | Extend to include `display_name`, `avatar_url` (at minimum); optionally `bio`, `country`, `city` |

### 11.3 Member List Lacks Search/Filter/Pagination

| Gap | Impact | Required Change |
|-----|--------|----------------|
| **No search by name/email** | Large member lists unsearchable | Add `?search=` query param |
| **No filter by role** | Can't show "all Managers" | Add `?role_id=` query param |
| **No filter by individual status** | Binary `include_all` only | Add `?status=` query param |
| **No pagination** | All members returned at once | Add `StandardPagination` to list views |
| **No ordering** | Fixed `-joined_at` order | Add `?ordering=` param (name, role, status, joined_at) |

### 11.4 Form Responses Per Member

| Gap | Impact | Required Change |
|-----|--------|----------------|
| **No endpoint for form responses by account + user** | Can't show member's submitted forms | Add `FormResponseSelector.list_by_account_and_submitter()` + endpoint |

### 11.5 Role Management Gaps

| Gap | Impact | Required Change |
|-----|--------|----------------|
| **No member count per role in role list** | Can't show "5 members" badge on role card | Add `member_count` annotated field to `RoleOutputSerializer` or separate endpoint |
| **No atomic permission assignment on role creation** | N+1 API calls to set up role with permissions | Consider extending `RoleCreateInputSerializer` (optional enhancement) |

### 11.6 Reactivation Endpoint Missing

| Gap | Impact | Required Change |
|-----|--------|----------------|
| **No reactivate endpoint** | Suspend/remove/ban views each hardcode a single target status. No view calls `update_membership_status(status=ACTIVE)`. Service method exists, permission is `can_suspend_member`, but no view exposes it. | Add `POST /members/{id}/reactivate/` view that calls `update_membership_status(new_status=ACTIVE)` with `can_suspend_member` permission check |

### 11.7 Platform Base Member Role (Cross-System)

| Gap | Impact | Required Change |
|-----|--------|----------------|
| **Platform has no Base Member role** | Platform invitation/request acceptance crashes (`get_base_member_role()` raises NotFound). Affects RolePicker in Member Management (fewer options) and Transaction System (invitation/request workflows). | Add Base Member role (level 10) to `initialize_platform_account()` as safety net. See Transaction System Frontend description, Section 10.3-10.4 for full details. |

---

## 12. Frontend Architecture

### 12.1 Feature Folder Structure

```
frontend/src/features/members/
├── api/
│   ├── members-api.ts            # Member CRUD API functions
│   ├── roles-api.ts              # Role CRUD + permission API functions
│   └── *.test.ts
├── hooks/
│   ├── use-member-queries.ts     # TQ hooks: list, detail
│   ├── use-member-mutations.ts   # Mutation hooks: suspend, remove, ban, role change
│   ├── use-role-queries.ts       # TQ hooks: list, detail, permissions list
│   ├── use-role-mutations.ts     # Mutation hooks: create, update, delete, add/remove permission
│   └── *.test.ts
├── components/
│   ├── MemberList.tsx            # Filterable member list
│   ├── MemberCard.tsx            # Member row/card in list
│   ├── MemberProfile.tsx         # Profile section on detail page
│   ├── MemberActions.tsx         # Action buttons (permission-gated)
│   ├── MemberFormResponses.tsx   # Form responses section
│   ├── RoleList.tsx              # Role cards list
│   ├── RoleCard.tsx              # Individual role card
│   ├── CreateRoleDialog.tsx      # Role creation form
│   ├── PermissionsEditor.tsx     # Searchable permission checklist
│   ├── MemberStatusBadge.tsx     # Reusable status badge
│   ├── QuotaBar.tsx              # Member quota display
│   ├── ConfirmActionDialog.tsx   # Confirmation with optional reason
│   └── *.test.tsx
├── types/
│   └── members.ts                # TypeScript types for members + roles
├── constants/
│   └── member-statuses.ts        # Status metadata (colors, icons, labels)
└── validations/
    └── role.ts                   # Zod schemas for role creation
```

### 12.2 Type Definitions

```typescript
// Extends existing types/rbac.ts
type MembershipStatus = "active" | "suspended" | "removed" | "banned" | "left";

// Member list item (lightweight)
interface MemberListItem {
  id: string;
  user: MemberUser;
  role_name: string;
  role_level: number;
  is_owner: boolean;
  status: MembershipStatus;
  joined_at: string;
}

// Extended member user (needs backend change)
interface MemberUser {
  id: string;
  email: string;
  username: string;
  display_name?: string;   // NEW — needs backend
  avatar_url?: string;     // NEW — needs backend
}

// Member detail (full)
interface MemberDetail {
  id: string;
  user: MemberUser;
  account_type: AccountType;
  account_id: string;
  role: Role;
  is_owner: boolean;
  status: MembershipStatus;
  joined_at: string;
  status_changed_at: string | null;
  status_reason: string;
  created_at: string;
  updated_at: string;
}

// Tier 1.5 permissions for member detail
type MemberPermissions = {
  can_change_role: boolean;
  can_suspend: boolean;
  can_remove: boolean;
  can_ban: boolean;
  can_reactivate: boolean;
};

// Tier 1.5 permissions for role detail
type RolePermissions = {
  can_edit: boolean;
  can_delete: boolean;
  can_modify_permissions: boolean;
};

// Permission (from /permissions/ endpoint)
interface Permission {
  id: string;
  code: string;
  name: string;
  description: string;
  category: string;
  applicable_scopes: string[];
}

// Role permission assignment
interface RolePermissionAssignment {
  id: string;
  permission: Permission;
  scope: string;
}

// Role detail (with permissions)
interface RoleDetail extends Role {
  role_permissions: RolePermissionAssignment[];
  permission_count: number;
}
```

### 12.3 State Management

| Concern | Tool | Pattern |
|---------|------|---------|
| Member list & detail | TanStack Query | Query hooks with account context |
| Role list & detail | TanStack Query | Query hooks with account context |
| Permissions list (all 51) | TanStack Query | Cached globally (rarely changes) |
| Current user's membership | Zustand (membership-store) | Already built — provides `account_max_members`, `role_level` |
| URL state (filters, search) | URL search params | Consistent with Explore + Forms |
| Dialog state (confirm, create role) | React state | Component-local |

---

## 13. Cross-System Dependencies

### 13.1 What This System Uses (Already Built)

| System | What We Use | How |
|--------|------------|-----|
| **Auth** | `AuthGuard`, access token | Route protection, API calls |
| **RBAC** | Permission codes, membership store | Nav gating, `<Can>` component, dominance checks |
| **Organization** | Account context (slug/id) | Scopes all member/role queries |
| **Member Quota** | `minMembers` nav filter, `account_max_members` | Hide section for solo, quota-aware buttons |
| **Frontend Foundation** | Guards, nav config, API layer, error handling | All infrastructure |

### 13.2 What Uses This System

| System | What They Use | How |
|--------|-------------|-----|
| **Transaction System** | "Invite Member" triggers invitation flow | Button on dashboard links to transaction creation |
| **Transaction System** | `<RolePicker>` component | Reused from this system for role assignment |
| **Form System** | Member's form responses | Linked from member detail page |

### 13.3 Backend Work Required (Summary)

| Work Item | Type | Priority |
|-----------|------|----------|
| Add `PermissionInjectMixin` to member detail views | Backend change | **High** |
| Add `MembershipPolicy.get_viewer_permissions()` | New policy method | **High** |
| Add `PermissionInjectMixin` to role detail views | Backend change | **High** |
| Add `RolePolicy.get_viewer_permissions()` | New policy method | **High** |
| Extend `MemberUserOutputSerializer` with display_name, avatar_url | Serializer update | **High** |
| Add search/filter/pagination to member list | View update | **Medium** |
| Add `FormResponseSelector.list_by_account_and_submitter()` | New selector method | **Medium** |
| Add member form responses endpoint | New endpoint | **Medium** |
| Add `POST /members/{id}/reactivate/` endpoint | New view (service method exists, no view) | **High** |
| Add `member_count` annotation to role list serializer | Serializer update | **Low** |

---

## 14. Open Design Questions (For Planning Phase)

| Question | Options | Impact |
|----------|---------|--------|
| **Member list pagination** | (A) Backend pagination with StandardPagination, (B) Client-side pagination (fetch all), (C) Infinite scroll | UX for large member lists |
| **Member detail layout** | (A) Two-column (profile left, actions right), (B) Tabbed (profile, forms, activity), (C) Single column stacked | Page structure |
| **Role creation flow** | (A) Dialog/modal, (B) Inline form on dashboard, (C) Separate page | UX complexity |
| **Permission editor UX** | (A) Immediate save per toggle, (B) Batch changes + "Save" button | Trade-off: simplicity vs accidental changes |
| **Reactivation flow** | (A) Dedicated "Reactivate" button on suspended members (needs new endpoint), (B) Generic status change dropdown | New endpoint required — service exists, view does not |
| **Member avatar in list** | (A) Extend MemberUserOutputSerializer (1 backend change), (B) Separate user profile fetch per row (N+1) | Performance vs backend effort |
| **Invite Member flow** | (A) Navigate to `/transactions/invitations?type=...` (Transaction System owns the flow), (B) Dedicated modal on Members dashboard that creates transaction internally | Cross-system UX boundary |
| **Bulk member actions** | (A) Multi-select + bulk suspend/remove, (B) Individual actions only (MVP) | Future enhancement |
