# Transaction System — Frontend High-Level Description

> **Status:** Description (pre-plan)
> **Date:** 2026-03-04
> **Scope:** Frontend implementation for transaction management, form-transaction assignment, and request/invitation workflows
> **Depends on:** Frontend Foundation, RBAC system, Member Quota system, Form System Frontend
> **Related:** Form System Frontend (form builder reused in Fill/View mode)

---

## 1. Overview

The Transaction System frontend provides organization members with tools to manage
transactional workflows — invitations, requests, approvals, and their associated forms.
It is built on top of a **complete backend** (10 transaction types, 9 statuses, state machine,
outcome handlers, form integration) and introduces **per-organization form-transaction
assignment** as a new capability.

### Core Principles

| Principle | Implementation |
|-----------|---------------|
| **Solo accounts excluded** | Entire Transactions section hidden when `max_members <= 1` via `minMembers: 2` on nav item |
| **Permission-aware everywhere** | Nav gating (Tier 1), API `_permissions` (Tier 1.5 — needs backend work), Guards (Tier 2), Backend policies (Tier 3) |
| **Consistent with app patterns** | Uses existing guards, `<Can>` component, `useFilteredNav`, membership store |
| **Category-based grouping** | Transaction types grouped by category for organized UI (membership, verification, etc.) |
| **System forms locked** | System-required forms (superuser-assigned) cannot be removed; orgs can add custom forms in addition |

---

## 2. Routes

All routes exist in two contexts — business console and platform console:

| Route | Business Console | Platform Console |
|-------|-----------------|-----------------|
| Dashboard | `/bconsole/[slug]/transactions/` | `/pconsole/transactions/` |
| Settings | `/bconsole/[slug]/transactions/settings` | `/pconsole/transactions/settings` |
| Requests | `/bconsole/[slug]/transactions/requests` | `/pconsole/transactions/requests` |
| Request detail | `/bconsole/[slug]/transactions/requests/[id]` | `/pconsole/transactions/requests/[id]` |
| Invitations | `/bconsole/[slug]/transactions/invitations` | `/pconsole/transactions/invitations` |
| Invitation detail | `/bconsole/[slug]/transactions/invitations/[id]` | `/pconsole/transactions/invitations/[id]` |

### Route Protection

| Layer | Mechanism | Already Built |
|-------|-----------|--------------|
| Authentication | `AuthGuard` wraps all `(app)` routes | Yes |
| Account membership | `BusinessGuard` / `PlatformGuard` with retry-on-miss | Yes |
| Member quota | `minMembers: 2` on nav config hides section for solo accounts | Yes |
| Permission | `permission` field on nav items filters by RBAC codes | Yes |

---

## 3. Navigation Configuration

### Nav Item (in `navigation-config.ts`)

The Transactions section is a **new nav section** with sub-items:

```
Section: "Transactions"
  minMembers: 2
  permission: (any transaction permission — see dashboard visibility logic)

  Items:
    - Requests      → /transactions/requests      permission: can_view_transactions
    - Invitations   → /transactions/invitations    permission: can_invite_member
    - Settings      → /transactions/settings       permission: can_configure_transactions
```

**Note:** The nav section should be visible if the user has **any** transaction-related
permission. Individual items are filtered by their specific permission gates.

---

## 4. Transaction Type Categories

### New Backend Field: `category` on `TransactionTypeConfig`

A `category` field is added to the `TransactionTypeConfig` dataclass to enable frontend
grouping. Categories must be chosen carefully to support future expansion (events, etc.).

### Proposed Categories

| Category | Transaction Types | Notes |
|----------|------------------|-------|
| `membership` | `platform_membership_invitation`, `platform_membership_request`, `business_membership_invitation`, `business_membership_request` | Core membership workflows |
| `ownership` | `platform_ownership_transfer`, `business_ownership_transfer` | Ownership transfer — separate from membership because it's a structural change |
| `verification` | `business_verification_request` | Business verification workflow |
| `permission` | `business_creation_permission_request` | Permission grants |
| `social` | `business_follow_request`, `user_connection_request` | Future social features (stubs) |

> **Future categories:** `events`, `commerce`, `moderation`, etc. can be added later
> without changing the existing structure.

### Category Metadata (Frontend)

Each category has display metadata:

```
membership:    { label: "Membership",    icon: Users,        description: "Member invitations and requests" }
ownership:     { label: "Ownership",     icon: Crown,        description: "Account ownership transfers" }
verification:  { label: "Verification",  icon: ShieldCheck,  description: "Business verification" }
permission:    { label: "Permissions",   icon: Key,          description: "Permission grants" }
social:        { label: "Social",        icon: Heart,        description: "Follows and connections" }
```

---

## 5. Pages

### 5.1 Transactions Dashboard (`/transactions/`)

**Purpose:** Landing page with bento grid / card panel summarizing each sub-section.

**Visibility rule:** Each card is visible only if the user has the relevant permission.
Hidden cards are removed from the layout (not disabled), consistent with the rest of the app.

| Card | Visible When | Navigates To | Summary Content |
|------|-------------|--------------|-----------------|
| **Requests** | `can_view_transactions` OR `can_approve_membership_request` | `/transactions/requests` | Pending request count, recent activity |
| **Invitations** | `can_invite_member` | `/transactions/invitations` | Active invitation count, sent/accepted/expired stats |
| **Settings** | `can_configure_transactions` | `/transactions/settings` | "Configure transaction forms" |

**Data source:** Lightweight API calls (transaction counts by mode/status) or a dedicated
dashboard summary endpoint.

### 5.2 Requests Page (`/transactions/requests`)

**Purpose:** View incoming requests that need review/approval. These are transactions where
the organization is the target (someone is requesting something FROM the org).

**Permission gate:** `can_view_transactions` OR `can_approve_membership_request`

**Layout:**

**Filters (combinable):**

| Filter | Type | Options |
|--------|------|---------|
| Category | Select | membership, ownership, verification, permission, social |
| Transaction type | Select | Filtered by selected category |
| Status | Multi-select | All 9 statuses (default: show non-terminal) |
| Date range | Date picker | created_at range |
| Submitter | Search/autocomplete | User who initiated the request |

**List columns:**

| Column | Source | Notes |
|--------|--------|-------|
| Type | `transaction_type` | Human-readable name from category metadata |
| Category | Derived from type | Badge/chip |
| Requester | `initiator_id` → user name/email | Needs denormalized field (see backend gaps) |
| Status | `status` | Color-coded badge |
| Has Form | `form_response_id` | Icon indicator if form is linked |
| Created | `created_at` | Relative or absolute date |
| Expires | `expires_at` | Countdown or date |

**Row click** → navigates to `/transactions/requests/[id]`

**Relevant transaction types for requests:**
- `platform_membership_request` (Platform console)
- `business_membership_request` (Business console)
- `business_verification_request` (Platform console)
- `business_creation_permission_request` (Platform console)
- `business_follow_request` (Business console — auto-approved, may not appear)
- `user_connection_request` (User-to-user — may not appear in org console)

### 5.3 Request Detail (`/transactions/requests/[id]`)

**Purpose:** View a single request — details, form response, action buttons.

**Backend endpoint:** `GET /api/v1/transactions/<id>/`

**Layout sections:**

**Header:**
- Transaction type name + category badge
- Status badge (color-coded)
- Created date, expires date

**Requester info:**
- User name, email, avatar
- `initiator_context` details (role, account if applicable)

**Form response section** (if form is linked):
- Rendered using the Form Builder component in **View** mode
- Shows all submitted field values with proper labels
- If INFO_REQUESTED: shows revision history, highlighted requested fields
- Backend endpoint: `GET /api/v1/transactions/<id>/form-response/`

**Transaction log:**
- Timeline of all status changes (from `logs` array in detail response)
- Each log entry: timestamp, event_type, previous_status → new_status, actor info

**Action buttons** (permission-gated, status-dependent):

| Action | Visible When | Status Required | Backend Endpoint |
|--------|-------------|----------------|-----------------|
| Accept | User can approve (Tier 1.5 `_permissions.can_accept`) | PENDING | `POST /transactions/<id>/accept/` |
| Deny | User can approve (same as accept) | PENDING | `POST /transactions/<id>/deny/` |
| Dismiss | User can approve (REQUEST mode only) | PENDING | `POST /transactions/<id>/dismiss/` |
| Request Info | User can approve + form is linked | PENDING | `POST /transactions/<id>/request-info/` |
| Cancel | User is initiator | PENDING | `POST /transactions/<id>/cancel/` |

**Quota awareness for Accept (membership transactions only):**
When the transaction is a membership request/invitation, the "Accept" button must also check
member quota. If `current_count >= max_members` (and `max_members > 0`), disable the button
with tooltip: "Cannot accept — member limit reached". Data source: `account_max_members` from
membership store + member count from account context.

**Deny action:** Shows a modal/dialog with optional `reason` text field.
**Request Info action:** Shows a modal with required `message` field and optional
`requested_fields` checkboxes (populated from linked form's field list).

### 5.4 Invitations Page (`/transactions/invitations`)

**Purpose:** View outgoing invitations sent by org members. These are transactions where
an org member invites someone TO the org.

**Permission gate:** `can_invite_member`

**Layout:**

**Filters (combinable):**

| Filter | Type | Options |
|--------|------|---------|
| Category | Select | membership, ownership |
| Transaction type | Select | Filtered by selected category |
| Status | Multi-select | All statuses (default: non-terminal) |
| Date range | Date picker | created_at range |
| Invitee | Search/autocomplete | Target user |

**List columns:**

| Column | Source | Notes |
|--------|--------|-------|
| Type | `transaction_type` | Human-readable name |
| Invitee | `target_id` → user name/email | Needs denormalized field |
| Invited by | `initiator_id` → user name/email | Who sent it |
| Status | `status` | Color-coded badge |
| Role | `payload.role_id` → role name | For membership invitations |
| Sent | `created_at` | Date |
| Expires | `expires_at` | Countdown |

**Row click** → navigates to `/transactions/invitations/[id]`

**"New Invitation" button** (visible if `can_invite_member`):
- Opens invitation creation flow
- Select transaction type (filtered to INVITATION mode types for this context)
- Select target user (search/autocomplete)
- Fill payload fields (role, message — varies by type)
- If form is configured for this type: show form builder in **Fill** mode
- Submit creates transaction via `POST /api/v1/transactions/invitation/`

**Relevant transaction types for invitations:**
- `platform_membership_invitation` (Platform console)
- `business_membership_invitation` (Business console)
- `platform_ownership_transfer` (Platform console — owner only)
- `business_ownership_transfer` (Business console — owner only)

### 5.5 Invitation Detail (`/transactions/invitations/[id]`)

**Purpose:** View a single invitation — details, status, linked form.

**Layout:** Similar to Request Detail but from the sender's perspective.

**Header:** Type, category, status, dates
**Target info:** Invitee name, email
**Payload info:** Role assigned, message sent
**Form response** (if linked): Form Builder in **View** mode
**Transaction log:** Timeline of status changes

**Action buttons:**

| Action | Visible When | Status Required | Backend Endpoint |
|--------|-------------|----------------|-----------------|
| Cancel | User is initiator | PENDING | `POST /transactions/<id>/cancel/` |

### 5.6 Settings Page (`/transactions/settings`)

**Purpose:** Configure which custom forms are required for each transaction type.

**Permission gate:** `can_configure_transactions` (new permission)

**Layout:**

Grouped by **category**. Each category is a collapsible section.

For each transaction type within a category:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Business Membership Invitation                          [membership]│
│                                                                     │
│ System Form: None                                                   │
│ Custom Form: [ Select a form...          ▼ ]  [Save] [Remove]      │
│                                                                     │
│ Status: No form configured                                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Business Verification Request                        [verification] │
│                                                                     │
│ System Form: system-business-verification  🔒 (locked)              │
│ Custom Form: [ Select a form...          ▼ ]  [Save] [Remove]      │
│                                                                     │
│ Status: System form required + no custom form                       │
└─────────────────────────────────────────────────────────────────────┘
```

**For each transaction type card:**

| Element | Behavior |
|---------|----------|
| **System Form** (read-only) | Shows system form name with lock icon if `required_form_template_slug` is set in config. Cannot be removed or changed. |
| **Custom Form** (editable) | Dropdown of org's ACTIVE form templates. Can be set, changed, or removed. |
| **Save button** | Saves the custom form mapping via `TransactionFormMapping` API |
| **Remove button** | Removes the custom form mapping (system form remains if present) |

**Filtering which transaction types appear:**
- Only show types relevant to the current context (business vs platform)
- Only show types where `user_configurable: true`
- Only show types where `enabled: true`
- Group by category

**Transaction types visible per context:**

| Context | Visible Transaction Types |
|---------|--------------------------|
| Business Console | `business_membership_invitation`, `business_membership_request`, `business_ownership_transfer`, `business_follow_request` |
| Platform Console | `platform_membership_invitation`, `platform_membership_request`, `platform_ownership_transfer`, `business_verification_request`, `business_creation_permission_request` |

---

## 6. Transaction Statuses & Lifecycle

### 6.1 State Machine

```
  ┌─────────┐     (auto)      ┌─────────┐
  │ CREATED │ ───────────────► │ PENDING │
  └─────────┘                  └─────────┘
                                  │ │ │ │ │ │
                    ┌─────────────┘ │ │ │ │ └──────────────┐
                    │     ┌────────┘ │ │ └────────┐        │
                    ▼     ▼          ▼ ▼          ▼        ▼
              ┌──────┐ ┌──────┐ ┌────────┐ ┌─────────┐ ┌──────────────┐
              │ACCEPT│ │DENIED│ │CANCELL.│ │DISMISSD.│ │INFO_REQUESTED│
              └──────┘ └──────┘ └────────┘ └─────────┘ └──────────────┘
                                                              │
                                                              ▼
                                                         ┌─────────┐
                                                         │ PENDING │ (loop)
                                                         └─────────┘

  Any non-terminal status ──(expiry)──► EXPIRED
  Any non-terminal status ──(system)──► INVALIDATED
```

### 6.2 Status Display

| Status | Color | Icon | Description |
|--------|-------|------|-------------|
| `created` | Gray | Clock | Just created (auto-transitions to pending) |
| `pending` | Yellow/Amber | HourglassIcon | Awaiting action |
| `accepted` | Green | CheckCircle | Approved and outcome executed |
| `denied` | Red | XCircle | Rejected (with reason) |
| `cancelled` | Gray | Ban | Cancelled by initiator |
| `expired` | Orange | TimerOff | Expired (past expires_at) |
| `dismissed` | Gray | EyeOff | Soft-closed by authority without explicit deny (REQUEST mode only) |
| `invalidated` | Red/Dark | AlertTriangle | System-invalidated (permissions changed) |
| `info_requested` | Blue | MessageSquare | Waiting for more info from initiator |

### 6.3 Available Actions Per Status

| Status | Initiator Can | Approver Can |
|--------|--------------|--------------|
| `pending` | Cancel | Accept, Deny, Dismiss (REQUEST only), Request Info |
| `info_requested` | Resubmit (update form + resubmit) | — |
| `accepted` | — | — |
| `denied` | — | — |
| `cancelled` | — | — |
| `expired` | — | — |
| `invalidated` | — | — |
| `dismissed` | — | — |

---

## 7. Form-Transaction Assignment System

### 7.1 Concept

Organizations can **optionally** attach custom forms to transaction types. When a form is
configured for a transaction type:
- **Invitations:** The inviter fills out the form during invitation creation
- **Requests:** The requester fills out the form during request submission
- The filled form is linked to the transaction and visible to approvers

### 7.2 Two Layers of Forms

| Layer | Source | Locked? | Example |
|-------|--------|---------|---------|
| **System Form** | `TransactionTypeConfig.required_form_template_slug` (hard-coded) | Yes — superuser-assigned, cannot be removed or modified by org | `system-business-verification` |
| **Custom Form** | `TransactionFormMapping` model (per-account, database) | No — org admin can set, change, or remove | Any org ACTIVE form template |

**Both can coexist.** If a transaction type has both a system form AND a custom form,
the submitter fills out **both** forms during the transaction flow.

### 7.3 New Backend: `TransactionFormMapping` Model

**Purpose:** Per-account configuration of which custom form is used for which transaction type.

```python
class TransactionFormMapping(AuditModel):
    account_type = CharField(max_length=20)           # "business" or "platform"
    account_id = UUIDField()                           # Account UUID
    transaction_type = CharField(max_length=100)       # e.g., "business_membership_invitation"
    form_template = ForeignKey(FormTemplate)            # Must be ACTIVE, owned by this account
    is_required = BooleanField(default=False)           # Must fill vs optional

    class Meta:
        unique_together = ("account_type", "account_id", "transaction_type")
```

**Constraints:**
- One custom form per (account, transaction_type) — unique together
- Form template must be ACTIVE and owned by the same account
- Form template scope must match transaction context_type
- Cannot override system forms — system forms are always required in addition

### 7.4 New Backend: API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/transactions/form-mappings/<account_type>/<account_id>/` | List all mappings for account |
| `POST` | `/api/v1/transactions/form-mappings/<account_type>/<account_id>/` | Create/update mapping |
| `DELETE` | `/api/v1/transactions/form-mappings/<account_type>/<account_id>/<transaction_type>/` | Remove mapping |
| `GET` | `/api/v1/transactions/types/` | List available transaction types with categories (new) |

### 7.5 New Backend: Permission

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_configure_transactions` | Configure Transactions | transaction | business, platform_only |

### 7.6 Updated Transaction Creation Flow

When creating a transaction (invitation or request), the flow becomes:

```
1. Get TransactionTypeConfig for type
2. Check system form requirement (from config.required_form_template_slug)
3. Check custom form mapping (from TransactionFormMapping for this account + type)
4. If system form required → submitter fills system form (Form Builder, Fill mode)
5. If custom form mapped → submitter fills custom form (Form Builder, Fill mode)
6. Submit form response(s)
7. Create transaction with form_response_id(s)
8. Bidirectional linking
```

---

## 8. Permission Matrix

### 8.1 RBAC Permissions Used by Transactions

**Existing permissions:**

| Code | Name | Category | Used For |
|------|------|----------|----------|
| `can_view_transactions` | View Transactions | transaction | View requests/invitations list in account |
| `can_view_all_transactions` | View All Transactions | transaction | Platform-wide view (global) |
| `can_invite_member` | Invite Member | membership | Create invitations |
| `can_approve_membership_request` | Approve Membership Request | membership | Accept/deny membership requests |
| `can_approve_verification_request` | Approve Verification | platform | Accept/deny business verification |
| `can_approve_business_creation` | Approve Business Creation | platform | Accept/deny business creation requests |

**New permission (requires backend migration):**

| Code | Name | Category | Scopes |
|------|------|----------|--------|
| `can_configure_transactions` | Configure Transactions | transaction | business, platform_only |

### 8.2 Frontend Permission Usage

| Feature | Tier | Mechanism | Permission(s) |
|---------|------|-----------|---------------|
| Transactions nav section visible | Tier 1 | `useFilteredNav` + `minMembers: 2` | Any transaction permission |
| Requests nav item visible | Tier 1 | `useFilteredNav` permission gate | `can_view_transactions` |
| Invitations nav item visible | Tier 1 | `useFilteredNav` permission gate | `can_invite_member` |
| Settings nav item visible | Tier 1 | `useFilteredNav` permission gate | `can_configure_transactions` |
| Dashboard card visibility | Tier 1 | `<Can>` or conditional render | Same as respective nav items |
| Accept/Deny/Dismiss buttons | Tier 1.5 | `<Can allowed={_permissions.can_accept}>` | Via `_permissions` from API (needs backend work) |
| Cancel button | Tier 1.5 | `<Can allowed={_permissions.can_cancel}>` | Initiator-only check |
| Request Info button | Tier 1.5 | `<Can allowed={_permissions.can_request_info}>` | Approver + form linked |
| New Invitation button | Tier 1 | Permission check | `can_invite_member` |
| Form assignment config | Tier 1 | Permission check | `can_configure_transactions` |
| Route access | Tier 2 | BusinessGuard / PlatformGuard | Membership required |
| All write operations | Tier 3 | Backend policy enforcement | RBAC permission checks |

### 8.3 Tier 1.5: Permission-Aware Responses (Needs Backend Work)

Currently, transaction views do **NOT** use `PermissionInjectMixin`. This must be added.

**Proposed `TransactionPolicy.get_viewer_permissions()`:**

```python
@staticmethod
def get_viewer_permissions(*, transaction, actor_context, config) -> dict:
    return {
        "can_accept": _safe_check(TransactionPolicy.can_accept, transaction, actor_context, config),
        "can_deny": _safe_check(TransactionPolicy.can_deny, transaction, actor_context, config),
        "can_cancel": _safe_check(TransactionPolicy.is_initiator, transaction, actor_context),
        "can_dismiss": transaction.mode == "request" and _safe_check(TransactionPolicy.can_deny, ...),
        "can_request_info": _safe_check(TransactionPolicy.can_accept, ...) and transaction.form_response_id,
        "can_resubmit": transaction.status == "info_requested" and _is_initiator,
        "can_view_form": transaction.form_response_id is not None,
    }
```

**Frontend type:**

```typescript
type TransactionPermissions = {
  can_accept: boolean;
  can_deny: boolean;
  can_cancel: boolean;
  can_dismiss: boolean;
  can_request_info: boolean;
  can_resubmit: boolean;
  can_view_form: boolean;
};
```

### 8.4 Visibility Summary by Role

| Feature | Owner | Admin (transaction perms) | Member (invite perm only) | Member (view only) | Member (no perms) |
|---------|-------|--------------------------|--------------------------|-------------------|-------------------|
| Transactions nav section | Visible | Visible | Visible | Visible | Hidden |
| Dashboard | Visible | Visible | Visible (1-2 cards) | Visible (1 card) | Hidden |
| Requests card | Visible | Visible | Hidden | Visible | Hidden |
| Invitations card | Visible | Visible | Visible | Hidden | Hidden |
| Settings card | Visible | Visible | Hidden | Hidden | Hidden |
| Accept/Deny request | Yes | Yes (if has approval perm) | No | No | No |
| Create invitation | Yes | Yes (if has invite perm) | Yes | No | No |
| Cancel own invitation | Yes | Yes | Yes | No | No |
| Configure form mapping | Yes | Yes (if has config perm) | No | No | No |
| View transaction detail | Yes | Yes | Yes (own) | Yes | No |

---

## 9. Backend API Reference

### 9.1 Existing Endpoints (12 total)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/transactions/` | List transactions (role filter: all/initiator/target) |
| `POST` | `/api/v1/transactions/invitation/` | Create invitation |
| `POST` | `/api/v1/transactions/request/` | Create request |
| `GET` | `/api/v1/transactions/types/<type>/form/` | Get form schema for transaction type |
| `GET` | `/api/v1/transactions/<id>/` | Transaction detail (with logs) |
| `POST` | `/api/v1/transactions/<id>/accept/` | Accept transaction |
| `POST` | `/api/v1/transactions/<id>/deny/` | Deny transaction (with reason) |
| `POST` | `/api/v1/transactions/<id>/cancel/` | Cancel transaction (initiator only) |
| `POST` | `/api/v1/transactions/<id>/dismiss/` | Dismiss terminal transaction |
| `POST` | `/api/v1/transactions/<id>/request-info/` | Request more info |
| `POST` | `/api/v1/transactions/<id>/resubmit/` | Resubmit after info request |
| `GET/PATCH` | `/api/v1/transactions/<id>/form-response/` | View/update linked form response |

### 9.2 Existing Serializer Fields

**TransactionListSerializer (6 fields — very slim):**
- `id`, `transaction_type`, `mode`, `status`, `expires_at`, `created_at`

**TransactionOutputSerializer (22+ fields):**
- `id`, `transaction_type`, `mode`, `initiator_type`, `initiator_id`, `initiator_context`,
  `target_type`, `target_id`, `context_type`, `context_id`, `status`, `payload`,
  `form_response_id`, `info_requested_at`, `info_requested_message`, `info_requested_fields`,
  `expires_at`, `resolved_at`, `resolution_reason`, `created_at`, `updated_at`,
  `logs` (nested), `form_response` (embedded)

### 9.3 Backend Gaps (Needs Work)

| Gap | Impact | Suggested Resolution |
|-----|--------|---------------------|
| **No `TransactionFormMapping` model** | Can't configure per-org custom forms for transaction types | New model + migration + service + selector + API endpoints |
| **No `can_configure_transactions` permission** | Can't gate settings page | New permission seed migration |
| **No `category` on TransactionTypeConfig** | Can't group types in UI | Add field to dataclass + set on all 10 types |
| **No PermissionInjectMixin on transactions** | Can't gate action buttons via Tier 1.5 | Add `get_viewer_permissions()` to TransactionPolicy, add mixin to TransactionDetailView |
| **TransactionListSerializer too slim** | Can't display meaningful list (no names/emails) | Add denormalized fields: initiator_name, initiator_email, target_name, target_email, category |
| **No transaction type list endpoint** | Settings page can't discover available types | Add `GET /transactions/types/` returning types with categories |
| **No context-filtered transaction list** | Can't list transactions for specific account | Add `context_type` + `context_id` query params on list endpoint |
| **No `form_mappings` CRUD endpoints** | Settings page can't read/write form mappings | New API endpoints (see Section 7.4) |
| **Transaction list not filtered by mode** | Can't separate requests from invitations in list | Add `mode` query param filter |
| **No transaction count/summary endpoint** | Dashboard cards need counts | Add lightweight summary endpoint |
| **Platform invitation missing `role_id` in payload** | Platform invitation acceptance crashes — no Base Member role exists for platform | Add `role_id` to `platform_membership_invitation` payload_schema (required) |
| **Platform has no Base Member role** | `get_base_member_role()` raises `NotFound` for platform accounts | Either add Base Member role to `initialize_platform_account()` OR require explicit `role_id` on all platform membership transactions |
| **Accept endpoint takes no request body** | Approver cannot assign role when accepting membership requests | Add `AcceptTransactionInputSerializer` with optional `role_id` field; pass to outcome handler |
| **Request approval always defaults to Base Member** | No role picker at approval time; `handle_request_approved()` falls back silently | Update handler to read `role_id` from acceptance payload (new), fall back to Base Member only if not provided |

---

## 10. Role Assignment in Membership Transactions

### 10.1 Requirement

> Membership transactions must have an assigned role:
> - **Before invitation send** — inviter picks the role for the invitee
> - **Before request accept** — approver picks the role for the requester
> - **Owner role is NEVER assignable** — ownership is only transferred via ownership transfer transaction
> - **Level constraint** — a member can only assign roles with lower authority than their own (higher level number)

### 10.2 RBAC Role Level System (Existing)

Authority is **inverse**: level 0 = highest authority (Owner), level 10 = lowest (Base Member).

**Business account roles:**

| Role | Level | System Role | Notes |
|------|-------|-------------|-------|
| Owner | 0 | Yes | Only via ownership transfer, never assignable |
| *(custom roles)* | 1-9 | No | Created by members with lower level |
| Base Member | 10 | Yes | Default fallback, no permissions |

**Platform account roles:**

| Role | Level | System Role | Notes |
|------|-------|-------------|-------|
| Platform Owner | 0 | Yes | Only via ownership transfer, never assignable |
| Platform Admin | 2 | No | Platform-only scoped permissions |
| Global Moderator | 5 | No | Global-scope cross-account permissions |
| *(no Base Member)* | — | — | **Missing — needs to be added** |

**Dominance rule (existing in `MembershipPolicy.validate_role_assignment()`):**
- Owner role (level 0) can **never** be assigned — raises `PermissionDenied`
- Actor's role level must be **strictly lower** than the assigned role's level
- Example: Level 2 member can assign levels 3-10 only. Cannot assign level 0, 1, or 2.
- The assigned role must belong to the same account

### 10.3 Current Backend State

| Transaction | Role at Creation | Role at Acceptance | Level Check | Status |
|-------------|-----------------|-------------------|-------------|--------|
| Business invitation | `role_id` REQUIRED in payload | Uses payload role | **None** (gap) | Works but no level validation |
| Platform invitation | No `role_id` in payload | Falls back to Base Member (CRASHES) | **None** | **Bug** |
| Business request | No `role_id` in payload | Falls back to Base Member | **None** | Works but no approver choice |
| Platform request | No `role_id` in payload | Falls back to Base Member (CRASHES) | **None** | **Bug** |

**Critical backend gap:** `create_membership()` (called by outcome handlers) does **NOT**
enforce the level constraint. The level check only exists in `change_member_role()` via
`validate_role_assignment()`. This means a level 5 member with `can_invite_member` could
assign a level 2 role in the invitation payload without being blocked.

### 10.4 Required Backend Changes

**For invitations (role set by inviter at creation):**
1. Add `role_id` to `platform_membership_invitation` payload_schema (required, same as business)
2. **Add level validation in `create_invitation()`** — check that inviter's role level < assigned role's level
3. `handle_invitation_accepted()` already reads `payload.get("role_id")` — no handler change needed
4. Frontend: invitation creation form includes role picker

**For requests (role set by approver at acceptance):**
1. Create `AcceptTransactionInputSerializer` with optional `role_id` field
2. Update `AcceptTransactionView` to accept request body
3. Update `TransactionService.accept()` to pass acceptance payload to outcome handler
4. **Add level validation in `accept()`** — check that approver's role level < assigned role's level
5. Update `handle_request_approved()` to prefer acceptance-time `role_id` over payload `role_id`
6. Frontend: acceptance dialog includes role picker

**Level enforcement (new — applies to both flows):**
- Reuse `MembershipPolicy.validate_role_assignment()` logic in transaction creation and acceptance
- Block if `actor_context.role_level >= new_role.level`
- Block if `new_role.level == 0` (Owner role)

**Platform Base Member role decision (one of):**
- **(A)** Add Base Member role (level 10) to `initialize_platform_account()` as a safe fallback
- **(B)** Make `role_id` required on ALL membership transactions (no fallback needed)
- Recommendation: **(A)** — add Base Member as safety net, but UI always shows role picker

### 10.5 Frontend UI Impact

**Invitation creation form** (`/transactions/invitations` → "New Invitation"):
- Role picker is a **required field** for membership invitations
- Dropdown populated from account's available roles, **filtered by actor's level**
- Only shows roles where `role.level > actor.role_level` (actor can't assign equal or higher authority)
- Owner role (level 0) is **always excluded**
- API: `GET /api/v1/business/{slug}/roles/` or `GET /api/v1/platform/roles/`

**Request acceptance dialog** (`/transactions/requests/[id]` → "Accept" button):
- Clicking "Accept" opens a dialog with role picker
- Same filtering: only roles where `role.level > approver.role_level`
- Owner role (level 0) is **always excluded**
- "Accept" button in dialog submits with selected `role_id`
- API: `POST /api/v1/transactions/<id>/accept/` with `{ "role_id": "..." }`

### 10.6 Role Picker Component

Reusable across **3 systems**:
1. **Transaction System** — invitation creation (role for invitee)
2. **Transaction System** — request acceptance dialog (role for requester)
3. **Member Management System** — member role change dialog (see Role/Member Management Frontend doc)

```
<RolePicker
  accountType="business" | "platform"
  accountId={uuid}
  actorRoleLevel={number}          // Current user's role level (for filtering)
  value={selectedRoleId}
  onChange={setSelectedRoleId}
  required={true}
  excludeOwner={true}              // Always true — Owner is never assignable
/>
```

**Filtering logic:**
1. Fetch all roles via `GET /api/v1/business/{slug}/roles/` or `GET /api/v1/platform/roles/`
2. Exclude Owner role (level 0)
3. Exclude roles where `role.level <= actorRoleLevel` (can't assign equal or higher authority)
4. Sort remaining roles by level (ascending — highest authority first)
5. Display as select dropdown with role name and level indicator

**Example — Level 2 actor (Platform Admin) sees:**
- Global Moderator (level 5) ✓
- Base Member (level 10) ✓
- ~~Platform Admin (level 2)~~ — excluded (same level)
- ~~Platform Owner (level 0)~~ — excluded (Owner)

### 10.7 Owner-Specific Permissions in This Plan

Owner permissions are consistent across the system:

| Feature | Owner Behavior | Enforced By |
|---------|---------------|-------------|
| **Forms section** | Full access (all 6 form permissions) | RBAC role permissions |
| **Transactions section** | Full access (all transaction permissions) | RBAC role permissions |
| **Create invitation** | Can create + assign any role (level 1-10) | Level constraint (0 < all) |
| **Accept request** | Can accept + assign any role (level 1-10) | Level constraint (0 < all) |
| **Ownership transfer** | Only owner can initiate (`owner_only: true` on config) | TransactionPolicy.can_create_invitation() |
| **Role management** | Can create/modify/delete roles at any level (1-10) | MembershipPolicy.can_create_role() |
| **Delete account** | Owner-only action | BusinessPolicy / PlatformPolicy |
| **Nav visibility** | Sees all nav items (no permission gaps) | useFilteredNav (owner has all permissions) |
| **`_permissions` in API** | All booleans true | Backend policy evaluation |

---

## 11. Frontend Architecture

### 11.1 Feature Folder Structure (Proposed)

```
frontend/src/features/transactions/
├── api/
│   ├── transactions-api.ts          # API functions (typed wrappers)
│   └── transactions-api.test.ts
├── hooks/
│   ├── use-transaction-queries.ts   # TanStack Query hooks (list, detail, types)
│   ├── use-transaction-mutations.ts # Mutation hooks (accept, deny, cancel, etc.)
│   └── *.test.ts
├── components/
│   ├── TransactionCard.tsx          # Row/card for transaction list
│   ├── TransactionFilters.tsx       # Combinable filter panel
│   ├── TransactionTimeline.tsx      # Status change log timeline
│   ├── TransactionStatusBadge.tsx   # Color-coded status badge
│   ├── CategoryBadge.tsx            # Category chip/badge
│   ├── ActionButtons.tsx            # Accept/Deny/Cancel/etc. button group
│   ├── DenyDialog.tsx               # Deny confirmation with reason
│   ├── RequestInfoDialog.tsx        # Request info with message + field selection
│   ├── InvitationCreateForm.tsx     # New invitation creation flow
│   ├── FormMappingCard.tsx          # Settings page: per-type form config card
│   ├── FormMappingList.tsx          # Settings page: grouped by category
│   └── DashboardCard.tsx            # Bento grid card
├── types/
│   └── transactions.ts             # TypeScript types matching backend serializers
├── constants/
│   └── transaction-categories.ts   # Category metadata (labels, icons, descriptions)
└── validations/
    └── transaction.ts              # Zod schemas for invitation creation
```

### 11.2 Type Definitions (Matching Backend)

```typescript
// Transaction statuses
type TransactionStatus =
  | "created" | "pending" | "accepted" | "denied"
  | "cancelled" | "expired" | "dismissed"
  | "invalidated" | "info_requested";

type TransactionMode = "invitation" | "request";
type PartyType = "user" | "account" | "membership_actor" | "system";
type ContextType = "platform" | "business" | "user";
type ApproverPolicy = "target_acceptance" | "account_authority" | "platform_authority" | "auto_approval";

// Category (new)
type TransactionCategory = "membership" | "ownership" | "verification" | "permission" | "social";

// Transaction type config (from new /types/ endpoint)
type TransactionTypeInfo = {
  id: string;
  name: string;
  mode: TransactionMode;
  category: TransactionCategory;
  context_type: ContextType;
  user_configurable: boolean;
  requires_form: boolean;
  has_optional_form: boolean;
  system_form_slug: string | null;
};

// Form mapping (from new model)
type TransactionFormMapping = {
  id: string;
  transaction_type: string;
  form_template_id: string;
  form_template_name: string;
  is_required: boolean;
};

// Permission type for Tier 1.5
type TransactionPermissions = {
  can_accept: boolean;
  can_deny: boolean;
  can_cancel: boolean;
  can_dismiss: boolean;
  can_request_info: boolean;
  can_resubmit: boolean;
  can_view_form: boolean;
};
```

### 11.3 State Management Pattern

| Concern | Tool | Pattern |
|---------|------|---------|
| Server data (transactions, mappings) | TanStack Query | Query + mutation hooks |
| Current membership / permissions | Zustand (membership-store) | Already built |
| Form builder state (during invitation creation) | React state | Component-local |
| URL state (filters, tabs) | URL search params | Consistent with Explore + Forms |

---

## 12. Interaction with Form System

### 12.1 Where Form Builder Is Reused

| Context | Form Builder Mode | Trigger |
|---------|------------------|---------|
| **Invitation creation** | **Fill** mode | When creating invitation and form is configured for the transaction type |
| **Request submission** | **Fill** mode | When submitting request and form is configured for the transaction type |
| **Request detail (approver view)** | **View** mode | Viewing submitted form data in request detail |
| **Invitation detail** | **View** mode | Viewing submitted form data in invitation detail |
| **Info request resubmission** | **Fill** mode (partial) | Updating specific fields after info requested |

### 12.2 Form Resolution Logic (Frontend)

When creating a transaction, the frontend must determine which form(s) to show:

```
1. Fetch TransactionTypeConfig → check system_form_slug
2. Fetch TransactionFormMapping for (account, transaction_type) → check custom form
3. If system_form_slug exists:
   → Fetch system form template
   → Render Form Builder (Fill mode) — REQUIRED, cannot skip
4. If custom form mapping exists:
   → Fetch custom form template
   → Render Form Builder (Fill mode) — required or optional per mapping.is_required
5. Submit form response(s)
6. Create transaction with form_response_id(s)
```

### 12.3 Multiple Forms Consideration

When both system form AND custom form are configured, the UI shows them sequentially
(wizard-style steps) or as separate sections on the same page. The transaction is linked
to the primary (system) form response, and the custom form response can be linked via
a secondary reference.

> **Note:** The current backend only supports ONE `form_response_id` per transaction.
> Supporting both system + custom forms simultaneously may require adding a
> `custom_form_response_id` field to the Transaction model, or using a junction table.
> This should be resolved during the planning phase.

---

## 13. Cross-System Dependencies

### 13.1 What This System Uses (Already Built)

| System | What We Use | How |
|--------|------------|-----|
| **Auth** | `AuthGuard`, access token | Route protection, API calls |
| **RBAC** | Permission codes, membership store | Nav gating, `<Can>` component, action buttons |
| **Organization** | Account context (business/platform) | Scope for transaction context |
| **Member Quota** | `minMembers` nav filter | Hide entire Transactions section for solo accounts |
| **Form System** | Form Builder component (Fill + View modes) | Form filling during transaction creation, form viewing in detail |
| **Frontend Foundation** | Guards, nav config, API layer, error handling | All infrastructure |

### 13.2 What Uses This System (Future)

| System | What They Use | How |
|--------|-------------|-----|
| **Member Management UI** | Invitation creation flow | "Invite Member" button triggers transaction |
| **Business Verification UI** | Verification request flow | Dedicated page for verification workflow |
| **Notification System** | Transaction events | Notifications when transactions change status |

### 13.3 Backend Work Required (Summary)

| Work Item | Type | Priority |
|-----------|------|----------|
| Add `category` field to `TransactionTypeConfig` | Backend change (dataclass) | High |
| Create `TransactionFormMapping` model | New model + migration | High |
| Seed `can_configure_transactions` permission | Migration | High |
| Add `TransactionFormMapping` service + selector | New service layer | High |
| Add form-mapping CRUD API endpoints | New views + URLs | High |
| Add `get_viewer_permissions()` to TransactionPolicy | Backend change | High |
| Add `PermissionInjectMixin` to TransactionDetailView | Backend change | High |
| Expand TransactionListSerializer (denormalized names) | Serializer update | High |
| Add `mode`, `context_type`, `context_id` query params on list | View update | Medium |
| Add transaction types list endpoint with categories | New endpoint | Medium |
| Add transaction count/summary endpoint | New endpoint | Medium |
| Handle dual form (system + custom) on same transaction | Model/design decision | Medium |
| **Add `role_id` to platform invitation payload_schema** | Platform invitations crash without it (no Base Member role) | **Critical** |
| **Add Base Member role to platform initialization** | Fallback for any case where role_id is missing | **Critical** |
| **Accept endpoint must accept `role_id` body** | Approver can't assign role when accepting requests | **Critical** |
| **Update `handle_request_approved()` to use acceptance-time role** | Currently ignores approver intent, always uses Base Member | **Critical** |
| Add roles list endpoint per account (if not exists) | Role picker component needs to fetch available roles | Already exists (`/business/{slug}/roles/`, `/platform/roles/`) |
| **Add role level validation to `create_invitation()`** | Level 5 member can currently assign level 2 role — no level check in invitation flow | **Critical** |
| **Add role level validation to `accept()` for requests** | Approver could assign a role above their authority | **Critical** |

---

## 14. Open Design Questions (For Planning Phase)

| Question | Options | Impact |
|----------|---------|--------|
| **Dual forms per transaction** | (A) Add `custom_form_response_id` field, (B) Use junction table, (C) Merge into single response | Affects model, API, and form rendering flow |
| **Category source of truth** | (A) Hard-coded in frontend constants matching backend, (B) Served from backend types endpoint | Affects sync burden |
| **Invitation creation flow** | (A) Modal/dialog, (B) Dedicated page, (C) Multi-step wizard | UX complexity |
| **Request submission from outside** | How does a non-member submit a membership request with form? They may not have console access | May need public-facing request page |
| **Transaction expiry UI** | Show countdown timer? Auto-refresh? Visual warning? | UX detail |
| **Dismissed vs hidden** | Should dismissed transactions be hidden or shown with muted style? | List filtering UX |
| **Platform Base Member role** | Decided: **(A)** Add Base Member role to platform init as safety net, but UI always shows role picker | Resolved — add to platform initialization |
