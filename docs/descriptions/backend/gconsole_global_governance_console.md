# Global Governance Console (gconsole) — Description

**Status:** Not Implemented (requirements document)
**Date:** 2026-04-06
**Workspace:** cross-cutting (backend + frontend)
**Priority:** High — security-sensitive, governance-critical

---

## 1. What Is This?

The Global Governance Console (`/gconsole`) is a **separate, security-hardened management interface** for platform staff who hold **global-scope permissions**. It provides cross-account governance capabilities: suspending businesses, moderating members across organizations, reviewing audit trails, managing business approvals, and overseeing platform-wide operations.

Today, global governance features are either **mixed into `/pconsole`** (the platform internal console) or **not built at all**. This creates two problems:

1. **Security risk** — Destructive global actions (suspend a business, ban a member across all orgs) sit alongside routine internal operations (edit platform profile, manage CMS templates) with no additional authentication barrier.
2. **Confusion** — Platform staff see governance actions they may not have permission for, and the UI doesn't clearly separate "managing our platform org" from "governing the entire system."

The gconsole fixes both problems by introducing a **physically separate route** (`/gconsole`) with **step-up authentication**, **page-level permission gates**, and **Tier 1.5 permission-aware responses** throughout.

---

## 2. Why a Separate Console?

### 2.1 pconsole vs gconsole — The Distinction

The RBAC system already defines two distinct permission scopes that map cleanly to this separation:

| Aspect | pconsole (Platform Console) | gconsole (Governance Console) |
|--------|---------------------------|-------------------------------|
| **Purpose** | Managing the platform organization itself | Governing all businesses and users across the system |
| **Permission scope** | `platform_only` | `global_only` / `platform_and_global` |
| **Who uses it** | Platform team members | Platform Owner + members with global permissions |
| **Actions** | Edit profile, manage team, create CMS templates, forms | Suspend businesses, ban members, approve creators, audit |
| **Risk level** | Moderate (internal ops) | Critical (affects external businesses and users) |
| **Auth level** | Standard JWT | Step-up authentication (re-authenticate, short-lived token) |
| **Example** | "Add Alice to our platform team" | "Suspend Acme Corp for TOS violation" |

### 2.2 What Currently Exists Where

**Correctly in pconsole (stays there):**
- Platform profile/settings management
- Platform member and role management
- CMS site/page/template creation (platform-owned)
- Forms library management
- Platform chat
- Platform network (followers, connections)

**Currently in pconsole but belongs in gconsole:**
- `/pconsole/businesses` — listing/managing all businesses (stub)
- `/pconsole/approved-creators` — managing who can create businesses
- `/pconsole/transactions` — cross-account transaction oversight
- `/pconsole/audit` — global audit log viewing (stub)

**Not built at all (new for gconsole):**
- Business suspension/reactivation/archival UI
- Cross-account member enforcement (suspend/ban/remove members in any business)
- Global moderation dashboard
- Verification request review and approval
- Ownership transfer enforcement

---

## 3. Security Model

### 3.1 Step-Up Authentication

The gconsole requires **re-authentication** before access. This is a separate, elevated session that:

- **Requires fresh credentials** — The user must re-authenticate via password re-entry OR email OTP (6-digit code, 5-min TTL), even if they have a valid standard session. User chooses method. OAuth-only users use email OTP.
- **Issues a governance-scoped token** — A short-lived access token with an elevated claim (e.g., `token_scope: "governance"` or `elevated: true`).
- **No refresh token** — The governance token cannot be refreshed. When it expires, the user must re-authenticate. This limits the blast radius of a stolen token.
- **Short TTL** — 15-30 minutes (configurable via `auth.governance.token_lifetime` in deployment config). This is deliberately aggressive.
- **Separate from standard session** — The user's normal `/pconsole` or `/bconsole` session remains unaffected. The governance token is an additional, parallel credential.

#### Token Structure (Proposed)

Standard access token payload:
```json
{
  "user_id": "uuid",
  "jti": "uuid",
  "email": "user@example.com",
  "is_verified": true,
  "token_type": "access"
}
```

Governance access token adds:
```json
{
  "user_id": "uuid",
  "jti": "uuid",
  "email": "user@example.com",
  "is_verified": true,
  "token_type": "access",
  "token_scope": "governance",
  "elevated_at": "2026-04-06T12:00:00Z"
}
```

#### Backend Enforcement

A new permission class `GovernanceTokenRequired` checks:
1. Valid JWT with `token_scope == "governance"`
2. Token not expired (short TTL)
3. User still has active platform membership with at least one `global_only` or `platform_and_global` scoped permission
4. Falls through to standard `FeatureRequired` + RBAC checks per endpoint

If the token is missing or expired, the API returns:
```json
{
  "error": {
    "code": "governance_auth_required",
    "message": "This action requires governance-level authentication.",
    "details": {
      "auth_url": "/api/v1/auth/governance/authenticate/"
    }
  }
}
```

### 3.2 Step-Up Auth Flow

```
User clicks "Governance Console" in nav
  │
  ├─ Frontend checks: does governance token exist and is it valid?
  │   ├─ YES → proceed to /gconsole
  │   └─ NO → redirect to /gconsole/authenticate
  │
  ├─ /gconsole/authenticate page:
  │   ├─ Shows: "You are about to enter the Governance Console."
  │   ├─ Shows: "This requires re-authentication for security."
  │   ├─ User chooses method:
  │   │   ├─ Password: enters password → POST /api/v1/auth/governance/authenticate/
  │   │   └─ Email OTP: clicks "Send code" → POST /api/v1/auth/governance/otp/send/
  │   │       └─ Receives 6-digit code (5-min TTL) → POST /api/v1/auth/governance/otp/verify/
  │
  ├─ Backend validates credentials:
  │   ├─ FAIL → 401 (wrong password/code, locked out, expired code, etc.)
  │   └─ OK → checks user has global permissions
  │       ├─ NO global perms → 403 "You do not have governance access"
  │       └─ YES → issues governance token
  │           ├─ Returns: { access: "<short-lived-jwt>", expires_in: 1800 }
  │           ├─ NO refresh token returned
  │           └─ Audit log: auth.governance.authenticated
  │
  ├─ Frontend stores governance token in sessionStorage (per-tab, NOT localStorage)
  │   ├─ Separate from standard auth token (which is in-memory Zustand)
  │   ├─ Used only for /api/v1/governance/* endpoints
  │   └─ Timer shows remaining session time in gconsole header
  │
  └─ On token expiry:
      ├─ API returns 401 with code "governance_token_expired"
      ├─ Frontend redirects back to /gconsole/authenticate
      └─ Audit log: auth.governance.session_expired
```

### 3.3 Session Visibility

The gconsole header should show:
- Current governance session remaining time (countdown)
- A "Lock Console" button (manually invalidate governance token)
- Visual indicator that this is an elevated session (e.g., colored banner)

---

## 4. Access Control

### 4.1 Who Can Access gconsole?

Only platform members whose role includes **at least one `global_only` or `platform_and_global` scoped permission**. By default:

| Role | Level | gconsole Access | Notes |
|------|-------|-----------------|-------|
| **Platform Owner** | 0 | Full access | Has all permissions including global |
| **Platform Admin** | 2 | No access (by default) | Has `platform_only` perms, not `global_only` |
| **Global Moderator** | 5 | Full access | Has all `global_only` permissions |
| **Base Member** | 10 | No access | No permissions |

Platform Admins can be granted gconsole access by assigning them specific `global_only` permissions via custom role configuration. Access is permission-based, not role-name-based.

### 4.2 Page-Level Permission Gates

Every gconsole page is gated by a specific permission. If the user lacks that permission, the page shows a "You don't have access" message — it does NOT hide the nav entry (Tier 1.5 pattern: show but disable, so users know the capability exists).

| Page | Required Permission | Feature Gate |
|------|-------------------|--------------|
| `/gconsole/dashboard` | Any `global_only` or `platform_and_global` permission | — |
| `/gconsole/businesses` | `can_view_businesses` | — |
| `/gconsole/businesses/[id]` | `can_view_businesses` | — |
| `/gconsole/businesses/[id]/suspend` | `can_suspend_business` | — |
| `/gconsole/businesses/[id]/transfer` | `can_transfer_business_ownership` | — |
| `/gconsole/approved-creators` | `can_approve_business_creation` | `platform.governance.approved_creators` |
| `/gconsole/verification` | `can_approve_verification_request` | `platform.governance.business_verification` |
| `/gconsole/members` | `can_view_members` (global scope) | — |
| `/gconsole/moderation` | (new permission needed) | `platform.governance.global_moderation` |
| `/gconsole/audit` | `can_view_audit_logs` (global scope) | — |
| `/gconsole/transactions` | `can_view_all_transactions` | — |

### 4.3 Tier 1.5 — Permission-Aware Responses

Every gconsole detail endpoint MUST include `_permissions` in the response:

```json
{
  "id": "uuid",
  "legal_name": "Acme Corp",
  "status": "active",
  "_permissions": {
    "can_suspend": true,
    "can_remove_owner": false,
    "can_transfer_ownership": true,
    "can_edit": true,
    "can_view_legal_info": true,
    "can_view_members": true
  }
}
```

Frontend uses the `<Can>` component to gate action buttons:
```tsx
<Can allowed={permissions.can_suspend}>
  <Button variant="destructive">Suspend Business</Button>
</Can>
```

---

## 5. Existing Infrastructure to Leverage

### 5.1 RBAC — global_only Permissions (28 Total)

These permissions already exist in the permission registry and are seeded at platform initialization:

**Business Governance (5 — exclusive to gconsole):**
| Permission | Description |
|------------|-------------|
| `can_suspend_business` | Suspend a business account |
| `can_remove_business_owner` | Remove the owner of a business account |
| `can_transfer_business_ownership` | Force transfer ownership of a business |
| `can_view_businesses` | View all business accounts on the platform |
| `can_approve_verification_request` | Approve business verification requests |

**Cross-Account Member Enforcement (6):**
| Permission | Description |
|------------|-------------|
| `can_invite_member` | Invite members (global scope: into any business) |
| `can_remove_member` | Remove members from any business |
| `can_change_member_role` | Change roles in any business |
| `can_suspend_member` | Suspend members in any business |
| `can_ban_member` | Ban members in any business |
| `can_view_members` | View members of any business |

**Cross-Account Settings (3):**
| Permission | Description |
|------------|-------------|
| `can_edit_business` | Edit any business account settings |
| `can_edit_profile` | Edit any business profile |
| `can_view_legal_info` | View legal info of any business |

**Cross-Account Oversight (2):**
| Permission | Description |
|------------|-------------|
| `can_view_all_transactions` | View transactions across all accounts |
| `can_view_audit_logs` | View audit logs across all accounts |

**Cross-Account Content (12):**
| Permission | Description |
|------------|-------------|
| `can_assign_cms_to_business` | Assign CMS sites/templates to businesses |
| `can_view_cms_content` | View CMS content in any business |
| `can_edit_cms_content` | Edit CMS content in any business |
| `can_publish_cms_content` | Publish CMS content in any business |
| `can_upload_cms_media` | Upload media in any business |
| `can_edit_cms_media` | Edit media in any business |
| `can_delete_cms_media` | Delete media in any business |
| `can_edit_form` | Edit forms in any business |
| `can_delete_form` | Delete forms in any business |
| `can_view_responses` | View form responses in any business |
| `can_export_responses` | Export form responses in any business |
| `can_process_response` | Process form responses in any business |

### 5.2 Pre-Defined Roles

| Role | Level | System? | Scope | gconsole Access |
|------|-------|---------|-------|----------------|
| Platform Owner | 0 | Yes (immutable) | All scopes (platform_and_global preferred) | Full |
| Platform Admin | 2 | No (configurable) | `platform_only` by default | None by default |
| Global Moderator | 5 | No (configurable) | `global_only` by default | Full |
| Base Member | 10 | Yes (immutable) | None | None |

### 5.3 Business Lifecycle States

| Status | Description | Governance Actions |
|--------|-------------|-------------------|
| `pending` | Awaiting platform approval | Approve or reject |
| `active` | Operational | Suspend, archive |
| `suspended` | Suspended by platform | Reactivate, archive |
| `archived` | No longer operational (terminal) | — |
| `deleted` | Soft-deleted (terminal) | — |

**Verification statuses:** `unverified` | `pending` | `verified` | `rejected` | `expired`

### 5.4 Member Enforcement States

| Status | Description | Who Can Trigger |
|--------|-------------|----------------|
| `active` | Normal member | — |
| `suspended` | Temporarily suspended | `can_suspend_member` |
| `banned` | Permanently banned | `can_ban_member` |
| `removed` | Removed from account | `can_remove_member` |
| `left` | Voluntarily left | Self only |
| `pending_approval` | Awaiting approval | System (join request) |

Enforcement data stored on Membership model:
- `status_changed_at` — When the action was taken
- `status_changed_by` — FK to the actor (User)
- `status_reason` — Free-text reason (required for governance actions)

### 5.5 Audit Log Model

The audit system is append-only and immutable. Key fields for governance:
- `actor_id` / `actor_email` / `actor_type` — Who performed the action
- `action` — 100+ action types (see Section 8)
- `resource_type` / `resource_id` — What was affected
- `outcome` — `SUCCESS` | `FAILURE` | `DENIED`
- `details` / `changes` — Structured JSON with before/after values
- `ip_address` / `user_agent` / `request_id` — Request tracing

**Query layer exists** via `AuditSelector` — 6 query methods for filtering, sorting, pagination. Protected by `can_view_audit_logs` permission. **No REST API endpoint yet** — building standalone (Decision 13).

### 5.6 Governance-Related Transaction Types

| Transaction Type | Mode | Initiator | Target | Approver | Feature Gate |
|-----------------|------|-----------|--------|----------|-------------|
| `business_creation_permission_request` | REQUEST | User | Platform | `can_approve_business_creation` | `platform.governance.business_approval` |
| `business_verification_request` | REQUEST | Business Owner | Platform | `can_approve_verification_request` | `platform.governance.business_verification` |
| `business_ownership_transfer` | INVITATION | Business Owner | User | Target acceptance | `business.transactions.ownership_transfer` |
| `platform_ownership_transfer` | INVITATION | Platform Owner | User | Target acceptance | `platform.transactions.ownership_transfer` |

### 5.7 Feature Gates

Governance feature gates in deployment_config.json:
```json
"platform": {
  "governance": {
    "business_approval": true,
    "business_verification": true,
    "approved_creators": true,
    "global_moderation": true
  }
}
```

These are already defined and tested in the conftest `_FULL_FEATURE_CONFIG`.

---

## 6. What Needs to Be Built

### 6.1 Backend — New

| Component | Description | Priority |
|-----------|-------------|----------|
| **Step-up auth endpoint (password)** | `POST /api/v1/auth/governance/authenticate/` — validates password, checks global perms, issues short-lived governance token | P0 |
| **Step-up auth endpoint (OTP send)** | `POST /api/v1/auth/governance/otp/send/` — sends 6-digit code to user's verified email (5-min TTL) | P0 |
| **Step-up auth endpoint (OTP verify)** | `POST /api/v1/auth/governance/otp/verify/` — validates code, checks global perms, issues governance token | P0 |
| **GovernanceTokenRequired** | New DRF permission class — validates `token_scope == "governance"` + middleware membership check (`global_only` or `platform_and_global`) | P0 |
| **Governance token config** | New deployment config path: `auth.governance.token_lifetime` (default: 1800s) | P0 |
| **Business suspension endpoint** | `POST /api/v1/governance/businesses/{id}/suspend/` | P1 |
| **Business reactivation endpoint** | `POST /api/v1/governance/businesses/{id}/reactivate/` | P1 |
| **Business archival endpoint** | `POST /api/v1/governance/businesses/{id}/archive/` | P1 |
| **Owner removal endpoint** | `POST /api/v1/governance/businesses/{id}/remove-owner/` | P1 |
| **Forced ownership transfer endpoint** | `POST /api/v1/governance/businesses/{id}/transfer-ownership/` | P1 |
| **Cross-account member list** | `GET /api/v1/governance/members/` — all members across all businesses | P1 |
| **Cross-account member enforcement** | `POST /api/v1/governance/members/{id}/suspend/` etc. | P1 |
| **Global audit log endpoint** | `GET /api/v1/governance/audit/` — filterable, paginated | P1 |
| **Governance URL group** | `backend_core/urls/governance.py` — registered in `GATED_GROUPS` | P0 |
| **Audit log for governance actions** | All gconsole actions must create audit entries with `actor_type=ADMIN` | P0 |

### 6.2 Backend — Fixes

| Component | Issue | Fix |
|-----------|-------|-----|
| **PlatformPolicy** (3 occurrences) | Uses `is_staff`/`is_superuser` bypass | Replace with RBAC-only checks (Decision 3) |
| **BusinessPolicy** (9 occurrences) | Uses `is_staff`/`is_superuser` — some have NO RBAC fallback at all | Replace with RBAC checks using global-scope permission resolution |
| **can_approve_business_creation** | Scoped `platform_only` only (registry.py:167) | Add `global_only` scope |
| **Business state machine** | Only `reactivate()` validates prior status | Add `VALID_TRANSITIONS` table, validate all transitions (Decision 11) |
| **Global moderation** | Feature gate exists, zero implementation | Deferred — stub page only (Decision 5) |

### 6.3 Frontend — New

| Component | Description | Priority |
|-----------|-------------|----------|
| **`/gconsole` route group** | New route group under `src/app/(app)/gconsole/` | P0 |
| **GovernanceAuthGuard** | Route guard that checks governance token validity, redirects to re-auth | P0 |
| **`/gconsole/authenticate`** | Step-up auth page (password entry, governance token issuance) | P0 |
| **Governance token store** | Separate Zustand store or auth-store extension for governance token | P0 |
| **Governance API client** | Axios instance that attaches governance token (not standard token) | P0 |
| **Session timer** | Countdown in gconsole header showing remaining session time | P1 |
| **Lock Console button** | Manual governance token invalidation | P1 |
| **`/gconsole/dashboard`** | Overview: pending approvals, active suspensions, recent audit | P1 |
| **`/gconsole/businesses`** | List all businesses with status, verification, member count | P1 |
| **`/gconsole/businesses/[id]`** | Business detail with governance actions (suspend, transfer, etc.) | P1 |
| **`/gconsole/approved-creators`** | Manage approved business creators (move from pconsole) | P1 |
| **`/gconsole/verification`** | Review and approve/reject verification requests | P1 |
| **`/gconsole/members`** | Cross-account member search and enforcement | P2 |
| **`/gconsole/audit`** | Global audit log viewer with filters | P1 |
| **`/gconsole/transactions`** | Cross-account transaction oversight (move from pconsole) | P2 |
| **`/gconsole/moderation`** | Global moderation dashboard (future — depends on moderation design) | P3 |

### 6.4 Frontend — Moves

These pages should be **removed from pconsole** and rebuilt in gconsole:

| Current Location | Status | New Location | Notes |
|-----------------|--------|-------------|-------|
| `/pconsole/businesses` (stub) | Placeholder | `/gconsole/businesses` | Rebuild with governance actions |
| `/pconsole/approved-creators` | **Real implementation** | `/gconsole/approved-creators` | Adapt existing `ApprovedCreatorsPage` feature component |
| `/pconsole/transactions` | **Real implementation** | `/gconsole/transactions` | Adapt existing `PlatformTransactionsDashboardPage` feature component |
| `/pconsole/audit` (stub) | Placeholder | `/gconsole/audit` | Rebuild with global scope (audit REST API shipping standalone — Decision 13) |

**Note (verified 2026-04-07):** `approved-creators` and `transactions` are fully functional feature modules, not stubs. Moving them requires adapting the feature components to work under gconsole guards, not building from scratch.

pconsole retains a platform-internal audit view (scoped to platform-only actions via Decision 4). The global audit view belongs in gconsole.

---

## 7. Route Structure

```
/gconsole/
  ├── authenticate              # Step-up auth page (no governance token required)
  ├── dashboard                 # Overview: pending items, active enforcements, recent audit
  │
  ├── businesses/               # Business governance
  │   ├── (list)               # All businesses with filters (status, verification, type)
  │   └── [id]/                # Business detail + governance actions
  │       ├── (detail)         # Profile, status, members summary, audit trail
  │       ├── suspend          # Suspend with reason (confirmation dialog)
  │       ├── transfer         # Force ownership transfer
  │       └── members/         # Members of this specific business
  │
  ├── approved-creators/        # Business creation approval
  │   ├── (list)               # Approved creators list
  │   └── requests/            # Pending creation requests (from transactions)
  │
  ├── verification/             # Business verification
  │   ├── (list)               # Pending verification requests
  │   └── [id]/                # Review + approve/reject
  │
  ├── members/                  # Cross-account member oversight
  │   ├── (search)             # Search members across all businesses
  │   └── [id]/                # Member detail with enforcement actions
  │
  ├── audit/                    # Global audit log
  │   └── (list)               # Filterable, paginated audit entries
  │
  ├── transactions/             # Cross-account transaction oversight
  │   ├── (list)               # All governance-related transactions
  │   └── [id]/                # Transaction detail
  │
  └── moderation/               # Global moderation (future)
      └── (dashboard)          # Content reports, user warnings, etc.
```

---

## 8. Audit Requirements

Every governance action MUST be audited. The following audit actions are relevant:

### Business Governance Actions
| Action Code | Description | When |
|-------------|-------------|------|
| `org.business.suspended` | Business suspended | Governance actor suspends a business |
| `org.business.reactivated` | Business reactivated | Governance actor lifts suspension |
| `org.business.archived` | Business archived | Governance actor archives a business |
| `org.business.deleted` | Business deleted | Governance actor deletes a business |
| `org.business.creation_permission_granted` | Business creation approved | Governance actor approves creator request |
| `org.verification.approved` | Verification approved | Governance actor approves verification |
| `org.verification.rejected` | Verification rejected | Governance actor rejects verification |

### Ownership Actions
| Action Code | Description | When |
|-------------|-------------|------|
| `org.ownership.transfer_initiated` | Ownership transfer initiated | Governance actor forces transfer |
| `rbac.ownership.transferred` | Ownership transferred | Transfer completes |
| `rbac.owner.created` | New owner created | New owner receives ownership |

### Member Enforcement Actions
| Action Code | Description | When |
|-------------|-------------|------|
| `rbac.membership.suspended` | Member suspended | Governance actor suspends a member |
| `rbac.membership.banned` | Member banned | Governance actor bans a member |
| `rbac.membership.removed` | Member removed | Governance actor removes a member |
| `rbac.membership.reactivated` | Member reactivated | Governance actor lifts suspension |
| `rbac.membership.role_changed` | Role changed | Governance actor changes a member's role |

### Auth Actions (New)
| Action Code | Description | When |
|-------------|-------------|------|
| `auth.governance.authenticated` | Governance session started | User re-authenticates for gconsole |
| `auth.governance.session_expired` | Governance session expired | Governance token TTL reached |
| `auth.governance.session_locked` | Governance session manually locked | User clicks "Lock Console" |

---

## 9. Deployment Configuration

### New Config Paths

```json
{
  "systems": {
    "governance": true
  },
  "auth": {
    "governance": {
      "token_lifetime": 1800,
      "allow_password_stepup": true,
      "allow_email_otp_stepup": true,
      "otp_code_length": 6,
      "otp_expiry_seconds": 300
    }
  },
  "platform": {
    "governance": {
      "business_approval": true,
      "business_verification": true,
      "approved_creators": true,
      "global_moderation": true
    }
  }
}
```

| Path | Type | Default | Description |
|------|------|---------|-------------|
| `systems.governance` | bool | true | Enable governance system (URL group, all governance endpoints) |
| `auth.governance.token_lifetime` | int | 1800 | Governance token TTL in seconds (30 minutes) |
| `auth.governance.allow_password_stepup` | bool | true | Allow password re-entry for step-up auth |
| `auth.governance.allow_email_otp_stepup` | bool | true | Allow email OTP (6-digit code) for step-up auth |
| `auth.governance.otp_code_length` | int | 6 | OTP code length |
| `auth.governance.otp_expiry_seconds` | int | 300 | OTP code TTL in seconds (5 minutes) |
| `platform.governance.business_approval` | bool | true | Enable business creation approval workflow |
| `platform.governance.business_verification` | bool | true | Enable business verification requests |
| `platform.governance.approved_creators` | bool | true | Restrict business creation to approved users |
| `platform.governance.global_moderation` | bool | true | Enable cross-account moderation |

---

## 10. Known Issues to Fix

### 10.1 PlatformPolicy AND BusinessPolicy Use Django Staff Flags

**Scope (verified 2026-04-07): 12 occurrences across 2 files:**

**PlatformPolicy (3 occurrences)** — `platform/policies.py`:
- `can_configure()` — `user.is_superuser` only (line 54)
- `can_update_settings()` — `user.is_superuser` bypass, then RBAC fallback (line 65)
- `can_update_profile()` — `user.is_staff or user.is_superuser` bypass, then RBAC (line 81)

**BusinessPolicy (9 occurrences)** — `business/policies.py`:
- `can_suspend()` — `is_staff or is_superuser` only, NO RBAC (line 163)
- `can_reactivate()` — `is_staff or is_superuser` only, NO RBAC (line 172)
- `can_verify()` — `is_staff or is_superuser` only, NO RBAC (line 181)
- Plus 6 more methods with staff/superuser bypass before RBAC fallback (lines 51, 64, 91, 131, 195, 240)

**Required fix (Decision 3 — DECIDED):** Remove ALL 12 `is_staff`/`is_superuser` checks. RBAC is the single source of truth for pconsole and gconsole. Superuser bypass retained only in `/admin` diagnostics panel.

### 10.2 Permission Scope Inconsistency

**`can_approve_business_creation`** is currently scoped `platform_only` but should also include `global_only`. A Global Moderator should be able to approve business creation requests, but the current scope prevents this.

### 10.3 Global Moderation — Undefined

The feature gate `platform.governance.global_moderation: true` exists and is tested, but there are **zero backend endpoints, zero services, and zero UI** for global moderation. Before implementing the gconsole moderation page, the moderation system itself needs to be designed:
- What can be moderated? (Content? Users? Businesses? Reports?)
- What actions can a moderator take? (Warn? Restrict? Remove content?)
- Is there a reporting system for users to flag content?
- How does moderation relate to existing enforcement (suspend/ban)?

This is a separate design effort and should not block gconsole implementation. The `/gconsole/moderation` page can be a stub initially.

---

## 11. Implementation Sequence

### Phase 1 — Foundation (Backend + Frontend)
1. Implement step-up auth: password endpoint (`POST /api/v1/auth/governance/authenticate/`) + email OTP endpoints (`otp/send/`, `otp/verify/`) in `apps/auth/`
2. Create `GovernanceTokenRequired` permission class with middleware membership check (`global_only` or `platform_and_global` scoped permissions)
3. Create `backend_core/urls/governance.py` URL group + register in `GATED_GROUPS`
4. Add `auth.governance.*` paths to deployment_config.json and conftest `_FULL_FEATURE_CONFIG`
5. Fix `PlatformPolicy` (3) AND `BusinessPolicy` (9) to use RBAC instead of `is_staff`/`is_superuser`
6. Fix `can_approve_business_creation` scope: add `global_only` to registry.py
7. Add business state machine `VALID_TRANSITIONS` table + validation to all service methods
8. Create `/gconsole` frontend route group with `GovernanceAuthGuard`
9. Build `/gconsole/authenticate` step-up auth page (password + email OTP chooser)
10. Build governance token store (`sessionStorage`) + governance API client (Axios with governance token header)

### Phase 2 — Business Governance
1. Build business governance endpoints (suspend, reactivate, archive, remove owner, transfer)
2. Build `/gconsole/businesses` list page with filters
3. Build `/gconsole/businesses/[id]` detail page with Tier 1.5 `_permissions`
4. Build governance action dialogs (suspend with reason, confirm transfer, etc.)
5. Move `/pconsole/approved-creators` to `/gconsole/approved-creators`
6. Build `/gconsole/verification` for business verification review

### Phase 3 — Member Governance + Audit
1. Build cross-account member search/list endpoints
2. Build `/gconsole/members` search and enforcement UI
3. Build `/gconsole/audit` with global audit log viewer
4. Move `/pconsole/transactions` (cross-account) to `/gconsole/transactions`
5. Build `/gconsole/dashboard` overview page

### Phase 4 — Polish + Tests
1. Add session timer and "Lock Console" button
2. Add gconsole navigation with permission-gated entries
3. Define governance notification types (business_suspended, member_banned, etc.) + email templates
4. Write backend tests (step-up auth with password + OTP, governance endpoints, permission checks, state machine transitions)
5. Write frontend tests (auth guard, token management, page gates)
6. Write E2E tests (step-up auth flow, permission denial, session expiry, governance actions)
7. Design appeal transaction type constants (`business_suspension_appeal`, `membership_ban_appeal`) — implementation deferred

### Phase 5 — Moderation (Future)
1. Design moderation system (separate description doc — Decision 5)
2. Implement moderation backend
3. Build `/gconsole/moderation` dashboard

---

## 12. Critical Decisions

These decisions block downstream implementation. They are grouped by urgency: **Decide Now** (blocks multiple items independently of gconsole), **Decide Before gconsole** (blocks gconsole design), and **Can Defer** (does not block initial implementation).

### Architectural Decisions (block everything downstream)

#### Decision 1: gconsole step-up auth — password-only or allow OAuth?
- **Problem:** Password-only is more secure, but users who registered via Google/Apple and have no password literally cannot access gconsole.
- **Options:**
  - (a) Password-only — require all governance users to have a password set. Force password creation before granting global permissions.
  - (b) Allow OAuth step-up — less secure (OAuth provider compromise = governance compromise), but removes the password-set requirement.
  - (c) Password-only initially, OAuth step-up as opt-in later (`allow_oauth_stepup: false` default).
- **Recommendation:** Option (c). Ship password-only. Add a "set password" requirement when granting global permissions.
- **Priority:** Decide Before gconsole

#### Decision 2: Admin console (`/admin`) — kill it or repurpose it?
- **Problem:** A stub exists at `/admin` with "System administration coming soon." gconsole now covers governance. What is `/admin` for?
- **Options:**
  - (a) Delete it entirely — gconsole replaces it.
  - (b) Repurpose as Django superuser-only system diagnostics panel (health, config, feature gate viewer, deployment info) — NOT governance.
  - (c) Merge into gconsole as a "System" tab.
- **Recommendation:** Option (b). Keep `/admin` as a lightweight system diagnostics page for Django superusers. This is the emergency escape hatch — not for daily governance, but for "the platform is broken and I need to see what's going on." gconsole handles all governance.
- **Priority:** Decide Now (affects route architecture for everything)

#### Decision 3: PlatformPolicy — RBAC-only or keep superuser escape hatch?
- **Problem:** Current code uses `is_staff`/`is_superuser` as authorization bypass. Pure RBAC means a locked-out owner with a corrupted membership record can't recover.
- **Options:**
  - (a) Remove all Django staff/superuser checks — RBAC is single source of truth. Recovery via Django shell only.
  - (b) Keep superuser as emergency-only bypass, but audit-log every use and show a warning in the UI.
  - (c) Keep superuser bypass only in `/admin` (diagnostics), remove from all `/pconsole` and `/gconsole` paths.
- **Recommendation:** Option (c). RBAC is authoritative for pconsole and gconsole. Superuser bypass is only available in the `/admin` diagnostics panel. All superuser-bypass actions are audit-logged with `actor_type=SYSTEM`.
- **Priority:** Decide Before gconsole

#### Decision 4: Audit log — one global read API or scoped per console?
- **Problem:** Three consoles need audit access with different scopes:
  - bconsole: business-scoped audit (their own actions)
  - pconsole: platform-internal audit (platform team actions)
  - gconsole: cross-account audit (all businesses, all users)
- **Options:**
  - (a) Single endpoint `GET /api/v1/audit/` with `scope` query parameter — one codebase, one selector, permission determines what you see.
  - (b) Separate endpoints: `GET /api/v1/business/{slug}/audit/` + `GET /api/v1/platform/audit/` + `GET /api/v1/governance/audit/`
  - (c) Single endpoint with implicit scope based on context header (like chat scope isolation).
- **Recommendation:** Option (b). Separate endpoints with shared selector logic. Reasons: (1) governance endpoints require governance token, (2) business endpoints require business membership, (3) URL-level system gating works per console, (4) easier to feature-gate independently.
- **Priority:** Decide Now (unblocks 4+ items across all consoles)

#### Decision 5: Global moderation — what does it actually mean?
- **Problem:** Feature gate `platform.governance.global_moderation: true` exists with zero implementation. "Global moderation" is undefined.
- **Options:**
  - (a) Moderation = business/member enforcement only (suspend, ban, remove) — already covered by existing permissions. Remove the feature gate or make it an alias.
  - (b) Moderation = content moderation (takedown CMS pages, remove form templates, flag chat messages) — requires content reporting system, moderation queue, moderator actions.
  - (c) Moderation = user reporting system (users flag content/users → moderators review → take action) — requires report model, review queue, resolution tracking.
  - (d) Full moderation suite: reporting + content takedown + user warnings + strike system.
- **Recommendation:** Defer detailed design. For gconsole v1, stub `/gconsole/moderation` and define moderation in a separate description doc. The business/member enforcement features (suspend, ban, etc.) are sufficient for launch.
- **Priority:** Can Defer

---

### Security Decisions (block gconsole)

#### Decision 6: Governance token storage on frontend
- **Problem:** Where the governance token lives determines the security/UX trade-off.
- **Options:**
  - (a) In-memory only (Zustand, no persistence) — most secure, but lost on tab refresh. Every refresh forces re-auth. Painful for 30-minute sessions.
  - (b) `sessionStorage` — survives page refresh, cleared on tab close. Moderate security: XSS can read it, but it doesn't persist.
  - (c) Short-lived httpOnly cookie — backend sets it, frontend never touches it. Most secure against XSS, but requires cookie-based API auth for governance endpoints (different from standard JWT-in-header pattern).
- **Recommendation:** Option (b) `sessionStorage`. Rationale: governance token is already short-lived (15-30 min), `sessionStorage` survives refresh but not tab close, and it keeps the JWT-in-header pattern consistent with the rest of the app. The short TTL limits XSS exposure window.
- **Priority:** Decide Before gconsole

#### Decision 7: Concurrent governance sessions
- **Problem:** Can a user hold governance tokens on multiple devices/tabs simultaneously?
- **Options:**
  - (a) Yes, each independently short-lived — simple, no server state needed.
  - (b) No, only one active governance session — requires server-side tracking and revocation of prior tokens on new step-up auth.
- **Recommendation:** Option (a). Each governance token is independently short-lived. The blast radius is already limited by the short TTL. Adding server-side session tracking adds complexity with marginal security gain.
- **Priority:** Can Defer (short TTL covers most risk)

#### Decision 8: Governance token revocation on membership change
- **Problem:** If a user's platform membership is revoked (removed, banned) while they hold an active governance token, should the token be immediately invalidated?
- **Options:**
  - (a) Rely on short TTL — token expires in 15-30 min anyway. Acceptable risk.
  - (b) Immediate JTI blacklisting — add governance token JTI to a blacklist on membership change. Check blacklist on every governance API call.
  - (c) Middleware check — every governance request re-verifies active membership (1 DB query per request).
- **Recommendation:** Option (c). One lightweight membership check per governance request is acceptable given the low traffic volume of gconsole. This avoids the complexity of a JTI blacklist while providing real-time revocation.
- **Priority:** Decide Before gconsole

#### Decision 9: Business owner notification on governance actions
- **Problem:** When a business is suspended or a member is banned by a governance actor, should the affected parties be notified automatically?
- **Options:**
  - (a) Mandatory notification with reason — every governance enforcement action sends email + in-app notification to affected owner/member.
  - (b) Optional notification — governance actor can choose to notify or not (checkbox in UI).
  - (c) Email only — governance notifications always go via email (not in-app), creating a paper trail.
- **Recommendation:** Option (a). Mandatory notification with reason. Governance actions are serious — affected parties must know what happened and why. Notifications should include: action taken, reason, who to contact for questions, and appeal process (when available). Both email and in-app.
- **Priority:** Decide Before gconsole

---

### Data Model Decisions (block implementation)

#### Decision 10: User profile T2 fields — which fields become configurable?
- **Problem:** All user profile fields are currently either T1 (always public) or T3 (members-only). Users cannot control per-field visibility. The visibility framework supports T2 (conditional, owner-configurable) but zero T2 fields are defined for users.
- **Candidates:**
  - `phone` — currently T3. Could be T2 with default `CONNECTIONS` (show to connections only).
  - `email` — currently not in registry. Could be T2 with default `CONNECTIONS`.
  - `country` / `city` — currently T1. Could be T2 with default `WORLD`.
  - `bio` — currently T1. Probably should stay T1 (it's public profile text).
  - `tags` — currently T1. Probably should stay T1 (discovery purpose).
  - `social_links` — currently not explicitly in registry. Could be T2 with default `WORLD`.
  - `timezone` — currently T3. Could be T2 with default `CONNECTIONS`.
  - `language` — currently T3. Could stay T3 (internal preference, not profile info).
- **Recommendation:** Start small. T2 fields for user profiles:
  - `phone` — default: `CONNECTIONS`
  - `email` — default: `CONNECTIONS`
  - `country` — default: `WORLD`
  - `city` — default: `WORLD`
  - `social_links` — default: `WORLD`
  - `timezone` — default: `CONNECTIONS`
  - Keep `bio`, `tags`, `first_name`, `last_name`, `avatar` as T1 (they serve discovery). Keep `language` as T3 (internal).
- **Priority:** Decide Now (standalone work, no gconsole dependency)

#### Decision 11: Business state transitions — full state machine
- **Problem:** No explicit transition constraints are enforced at the model level. Unclear who can trigger which transitions.
- **Proposed state machine:**
  ```
  PENDING ──→ ACTIVE (platform approval)
       └──→ ARCHIVED (platform rejection / owner withdrawal)

  ACTIVE ──→ SUSPENDED (governance action, requires reason)
       └──→ ARCHIVED (owner voluntary / governance action)
       └──→ DELETED (owner voluntary, soft delete)

  SUSPENDED ──→ ACTIVE (governance reactivation)
           └──→ ARCHIVED (governance decision)

  ARCHIVED ──→ (terminal, no transitions)
  DELETED  ──→ (terminal, no transitions)
  ```
- **Actor permissions (DECIDED):**
  - `PENDING → ACTIVE`: governance (`can_approve_business_creation`) or auto-approve if `business_approval` gate is off
  - `PENDING → ARCHIVED`: governance (rejection)
  - `ACTIVE → SUSPENDED`: governance only (`can_suspend_business`), mandatory reason
  - `ACTIVE → ARCHIVED`: owner (voluntary) or governance (`can_suspend_business`)
  - `ACTIVE → DELETED`: owner only (soft delete their own business)
  - `SUSPENDED → ACTIVE`: governance only (`can_suspend_business`), audit logged
  - `SUSPENDED → ARCHIVED`: governance only
  - Force-delete: superuser-only via `/admin` diagnostics (not governance)
- **Enforcement:** Service-level `VALID_TRANSITIONS` dict; PENDING only reached when `platform.governance.business_approval` gate is ON
- **Priority:** DECIDED

#### Decision 12: Appeal system — in scope or deferred?
- **Problem:** Suspended businesses and banned members currently have no recourse. An appeal would be a new transaction type.
- **Options:**
  - (a) Defer entirely — appeals are post-gconsole. Affected parties contact support via email.
  - (b) Design appeal transaction types now (`business_suspension_appeal`, `membership_ban_appeal`) but implement later.
  - (c) Implement with gconsole v1 — full appeal flow with transaction integration.
- **Recommendation:** Option (b). Design the transaction types now (so the data model doesn't need to change later), but defer implementation. Governance notification messages should include "contact support" language until appeals are built.
- **Priority:** Can Defer (but design transaction types early)

---

### Dependency Decisions (block todo items)

#### Decision 13: Audit Log read API — build now or with gconsole?
- **Problem:** The audit read API blocks 4+ items:
  - bconsole audit page
  - pconsole audit page
  - gconsole audit page
  - 1 deferred E2E workflow (`audit-trail-verification.spec.ts`)
- **Options:**
  - (a) Build now as standalone work — unblocks bconsole/pconsole audit pages immediately, gconsole audit page later inherits it.
  - (b) Bundle into gconsole Phase 3 — all audit work happens together.
- **Recommendation:** Option (a). Build the business-scoped and platform-scoped audit read API now (under existing URL groups). The governance-scoped endpoint can be added later when gconsole URL group exists. The selector logic is shared — only the view + permission layer differs.
- **Priority:** Decide Now

#### Decision 14: Notification real-time push — add WebSocket delivery?
- **Problem:** REST notification endpoints already exist (`GET /api/v1/notifications/history/`, `/scopes/`, `/types/`, `/preferences/`). What's missing is real-time push for new notifications — currently dispatch is Celery-only (email channel works, push/SMS are stubs).
- **Options:**
  - (a) REST polling only — frontend polls `history/` on interval. No new infrastructure.
  - (b) WebSocket push — build `NotificationConsumer` for real-time delivery. Reuse chat WebSocket infra (`AuthenticatedConsumer` base class).
  - (c) REST + WebSocket — REST for history/pagination (already exists), WebSocket for real-time push of new notifications.
- **Recommendation:** Option (c). REST endpoints already work. Add WebSocket `NotificationConsumer` for live push. Reuse `AuthenticatedConsumer` base class and channel layer from chat.
- **Priority:** Decide Now (blocks notification E2E tests)

#### Decision 15: Stub pages — real implementation or meaningful placeholders?
- **Problem:** 10 stub pages exist. Some need backend APIs that don't exist yet.
- **Categories:**
  - **Marketing pages** (about, contact) — static content, no backend needed. Different skill set (copywriting, design).
  - **Dashboard pages** (home, bconsole dashboard, pconsole dashboard) — need aggregation APIs (recent activity, stats, pending items).
  - **Feature pages** (bconsole audit, bconsole CMS API keys) — need backend endpoints.
- **Options:**
  - (a) Build real implementations for all — requires backend aggregation APIs first.
  - (b) Ship informative placeholders with navigation value — show what the page will contain, link to working pages.
  - (c) Mixed — build dashboards with available data, placeholder for marketing pages.
- **Recommendation:** Option (c). Build dashboards with whatever data is currently available (recent items from existing endpoints), placeholder for marketing pages (about/contact are low priority). Feature pages (audit, API keys) are blocked by backend work — build when backend is ready.
- **Priority:** Decide Now

---

### Decision Summary (Resolved 2026-04-07)

| # | Decision | Status | Outcome |
|---|----------|--------|---------|
| 1 | Step-up auth method | **DECIDED** | Password OR Email OTP (user chooses). OAuth users use email OTP — no set-password endpoint needed. 6-digit code, 5-min TTL. Extends `apps/auth/`. |
| 2 | `/admin` console fate | **DECIDED** | Repurpose as superuser-only diagnostics panel (health, config viewer, feature gate state). NOT for governance. |
| 3 | PlatformPolicy bypass | **DECIDED** | RBAC-only for pconsole/gconsole. Remove all 12 `is_staff`/`is_superuser` checks from PlatformPolicy (3) + BusinessPolicy (9). Superuser bypass only in `/admin`. |
| 4 | Audit API architecture | **DECIDED** | Separate endpoints per console: `/business/{slug}/audit/`, `/platform/audit/`, `/governance/audit/`. Shared selector logic. |
| 5 | Global moderation scope | **DEFERRED** | Stub `/gconsole/moderation`. Design moderation system in a separate description doc. |
| 6 | Governance token storage | **DECIDED** | `sessionStorage` (per-tab, survives refresh, lost on tab close). JWT-in-header pattern consistent with standard auth. |
| 7 | Concurrent governance sessions | **DEFERRED** | Allow. Each token independently short-lived. `sessionStorage` per-tab provides natural isolation. |
| 8 | Token revocation on membership change | **DECIDED** | Middleware membership check per governance request: valid JWT + active platform membership + has `global_only` or `platform_and_global` scoped permissions. |
| 9 | Owner notification on governance | **DECIDED** | Mandatory notification with reason. New types: business_suspended, business_reactivated, member_banned, etc. Email + in-app. Non-configurable. |
| 10 | User profile T2 fields | **DEFERRED** | Independent of gconsole. Keep current T1/T3 split. Revisit later. |
| 11 | Business state machine | **DECIDED** | Service-level validation with `VALID_TRANSITIONS` table. ARCHIVED/DELETED are terminal. Archive = owner AND governance. Owner can soft-delete from ACTIVE only. PENDING only reached when `platform.governance.business_approval` gate is ON. Force-delete = superuser-only via /admin. |
| 12 | Appeal system | **DEFERRED** | Design `business_suspension_appeal` and `membership_ban_appeal` transaction type constants now. Implement flow later. |
| 13 | Audit read API timing | **DECIDED** | Build business-scoped + platform-scoped audit endpoints standalone now. Governance-scoped added with gconsole URL group. |
| 14 | Notification inbox mechanism | **DECIDED** | REST history endpoint already exists. Add WebSocket `NotificationConsumer` for real-time push. Reuse chat WebSocket infra. |
| 15 | Stub pages strategy | **DEFERRED** | Stubs resolve naturally as gconsole, audit API, and other features ship. Focus on gconsole foundation first. |

---

## 13. Open Questions (Non-Blocking)

These are lower-priority questions that do not block initial implementation but should be resolved over time:

1. **IP allowlisting** — Should gconsole access be further restricted by IP range in production? (Recommendation: configurable, not enforced initially.)

2. **Governance session audit granularity** — Should every page navigation within gconsole be audit-logged, or only actions (suspend, ban, approve)? (Recommendation: actions only, plus session start/end.)

3. **Governance token scope claims** — Should the governance token embed the user's global permissions in the JWT payload (faster checks, stale risk) or always check the DB (slower, always fresh)? (Recommendation: DB check — low traffic volume makes this acceptable, and the middleware membership check from Decision 8 already covers it.)

4. **Multi-tab governance UX** — If a user has gconsole open in two tabs and the token expires in one, should both tabs redirect simultaneously? (Note: `sessionStorage` is **per-tab** (per browsing context), NOT per-origin. Each tab has its own governance token and session. Tabs expire independently.)

5. **Governance action confirmation patterns** — Should destructive actions (suspend, ban, remove owner) require a typed confirmation (e.g., "type SUSPEND to confirm") or just a dialog with confirm button? (Recommendation: typed confirmation for irreversible actions like remove-owner and ban, simple confirm for reversible actions like suspend.)

---

## 14. Infrastructure Verification (2026-04-07)

Deep code verification confirmed all decisions are dependency-safe. Issues found and resolved:

### Resolved Issues

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Business creation goes to ACTIVE directly (services.py:136), not PENDING | PENDING only when `platform.governance.business_approval` gate is ON. Otherwise ACTIVE. State machine applies from whatever state is reached. |
| 2 | `can_archive()` is owner-only (policies.py:141-154), D11 said governance-only | **Updated:** Both owner AND governance can archive. Update `can_archive()` to check: `is_owner OR has global-scoped can_suspend_business`. |
| 3 | `can_delete()` uses `is_superuser` with no RBAC replacement | Force-delete stays superuser-only, moved to `/admin` diagnostics (D2). No new permission needed. |
| 4 | `systems.governance` not in deployment_config.json | Add `"governance": true` to `systems` section in both deployment_config.json and conftest `_FULL_FEATURE_CONFIG`. |
| 5 | Global Moderator only gets `global_only` perms (not `platform_and_global`) | Correct behavior. Middleware checks "has ANY global-scoped permission." Page-level gates control what's visible. |

### Implementation Notes from Verification

- **Governance OTP:** Create a new `GovernanceOTPToken` model (don't reuse `EmailVerificationToken`) for separate TTL, constraints, and metadata.
- **Lockout:** Consider separate governance lockout counter (max 3 attempts vs 10 for login) via `auth.governance.max_attempts` config.
- **Email templates:** Must create `EmailTemplate` DB rows for all 7 governance notification types BEFORE `send()` calls.
- **Audit actions:** Add 3 new `Action` enum values (`auth.governance.authenticated`, `.session_expired`, `.session_locked`) — no migration needed (TextChoices + CharField).
- **NotificationConsumer:** Extend `AuthenticatedConsumer` base class from `apps/auth/consumers.py`. Register in `backend_core/routing.py`.
- **Token scope validation:** `GovernanceTokenRequired` must check `payload.get("token_scope") == "governance"` — standard `validate_access_token()` ignores unknown claims by design.
- **Notification category:** Use `SYSTEM` category for governance types (no GOVERNANCE category exists).

---

## 15. Key File References

| File | Relevance |
|------|-----------|
| `backend/apps/rbac/permissions/registry.py` | 28 global permissions; `get_global_permissions()` at line 493; `can_approve_business_creation` fix at line 167 |
| `backend/apps/rbac/services.py` | Role initialization, member enforcement methods |
| `backend/apps/rbac/models.py` | Membership model with enforcement fields |
| `backend/apps/auth/models.py` | RefreshToken model (token structure), EmailVerificationToken (OTP pattern to replicate, line 248-333) |
| `backend/apps/auth/services/auth_service.py` | Token issuance, rotation, reuse detection |
| `backend/apps/organization/platform/policies.py` | PlatformPolicy (3 `is_staff`/`is_superuser` to remove) |
| `backend/apps/organization/business/policies.py` | BusinessPolicy (9 `is_staff`/`is_superuser` to remove) |
| `backend/apps/organization/business/services.py` | Business lifecycle: suspend, reactivate, archive, soft_delete (add transition validation) |
| `backend/apps/organization/platform/views.py` | Current platform endpoints |
| `backend/apps/organization/business/models.py` | BusinessStatus, VerificationStatus enums |
| `backend/apps/core/observability/audit/models.py` | AuditLog model (immutable, append-only) |
| `backend/apps/transaction/constants.py` | Governance transaction types |
| `backend/apps/core/feature_config.py` | Feature gate system; `get_value()` at line 82 handles missing nested keys with defaults |
| `backend/deployment_config.json` | Governance feature gates |
| `backend/conftest.py` | `_FULL_FEATURE_CONFIG` with governance entries |
| `backend_core/urls/__init__.py` | URL group registration (`GATED_GROUPS`) |
| `frontend/src/components/guards/` | Existing auth guards (reference for GovernanceAuthGuard) |
| `frontend/src/stores/auth-store.ts` | Current auth state (extend for governance token) |
| `frontend/src/lib/api-client.ts` | Current API client (reference for governance client) |
| `backend/apps/auth/services/verification_service.py` | Verification code flow — reference for governance OTP service |
| `backend/apps/auth/consumers.py` | `AuthenticatedConsumer` base class for WebSocket consumers |
| `backend/apps/auth/blacklist.py` | JTI blacklist (Redis) — reusable for governance token revocation |
| `backend/backend_core/routing.py` | WebSocket route registration (add NotificationConsumer here) |
| `backend/apps/notifications/types.py` | Notification type registry — add governance types here |
| `backend/apps/email/models.py` | EmailTemplate model — must create rows before governance notifications |
