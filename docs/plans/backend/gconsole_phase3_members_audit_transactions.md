# gconsole Phase 3 — Member Governance, Audit, Transactions & Dashboard

**Version:** 1.0
**Date:** 2026-04-08
**Depends on:** gconsole Phase 2 (complete — 4447 tests passing, 1700 frontend tests)
**Description doc:** `docs/descriptions/backend/gconsole_global_governance_console.md`
**Scope:** Cross-account member governance, global audit viewer, global transactions, governance dashboard

---

## 1. Abstract — What We Have Done (Phase 1 + 2 Recap)

Phase 1 built the gconsole security foundation (step-up auth, GovernanceTokenRequired, RBAC-only authorization).
Phase 2 added 8 business governance endpoints + frontend pages (list, detail, suspend, reactivate, archive, transfer, verification, approved-creators).

### Already Complete
- **Step-up auth** — password re-entry OR email OTP → governance-scoped JWT (30-min TTL)
- **GovernanceTokenRequired** — validates token scope + real-time membership check on every request
- **8 business governance endpoints** — list, detail, suspend, reactivate, archive, transfer, verification, approved-creators
- **Frontend** — GovernanceGuard, governance API client, 4 governance pages, TanStack Query hooks
- **Navigation** — 6 nav items configured (dashboard, businesses, members, approved-creators, audit, transactions)
- **Audit backend** — `GovernanceAuditListView` at `/api/v1/governance/audit/` (ALREADY IMPLEMENTED)
- **Feature gates** — `systems.governance: true` in deployment config and test config

### What Phase 3 Builds
1. **Cross-account member governance** — search and enforce members across ALL business accounts
2. **Global audit log viewer** — frontend page for the already-implemented audit endpoint
3. **Global transaction viewer** — cross-account transaction listing
4. **Governance dashboard** — summary overview page with key metrics

---

## 2. Big Picture

```
┌───────────────────────────────────────────────────────────────────────┐
│                     GOVERNANCE CONSOLE                                │
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────────────────────────────┐  │
│  │ Phase 1+2 ✓      │  │ Phase 3: Members + Audit + Transactions │  │
│  │ Auth + Business   │  │                                        │  │
│  │ 8 endpoints       │  │  /gconsole/members         — search    │  │
│  │ 4 pages           │  │  /gconsole/members/[id]    — detail    │  │
│  └──────────────────┘  │  /gconsole/members/[id]/suspend         │  │
│                        │  /gconsole/members/[id]/ban             │  │
│  ┌──────────────────┐  │  /gconsole/members/[id]/remove          │  │
│  │ Audit Backend ✓  │  │  /gconsole/members/[id]/reactivate     │  │
│  │ (already built)  │  │                                        │  │
│  │ GET /governance/  │  │  /gconsole/audit            — viewer   │  │
│  │   audit/          │  │  /gconsole/transactions     — global   │  │
│  └──────────────────┘  │  /gconsole/dashboard         — summary  │  │
│                        └──────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. Dependency Analysis

### Backend — Already Exists (No Changes Needed)

| Component | File | Status |
|-----------|------|--------|
| GovernanceAuditListView | `apps/core/observability/audit/views.py:204-247` | COMPLETE — endpoint live |
| AuditSelector.list_all() | `apps/core/observability/audit/selectors.py:288-313` | COMPLETE — 6 filters |
| AuditLogOutput serializer | `apps/core/observability/audit/serializers.py:13-34` | COMPLETE — 14 fields |
| Audit URL registration | `backend_core/urls/governance.py:59-64` | COMPLETE — registered |
| `can_view_audit_logs` permission | `apps/rbac/permissions/registry.py:199-205` | COMPLETE — global scope |
| `can_view_all_transactions` permission | `apps/rbac/permissions/registry.py:189-195` | COMPLETE — global scope |
| MembershipSelector methods | `apps/rbac/selectors.py:250-498` | COMPLETE — single-account scoped |
| RBACService.update_membership_status() | `apps/rbac/services.py:574-671` | COMPLETE — suspend/ban/remove |
| MembershipPolicy.authorize_action() | `apps/rbac/policies.py:38-123` | COMPLETE — cross-account via global_only |
| MembershipPolicy.get_viewer_permissions() | `apps/rbac/policies.py:167-205` | COMPLETE — returns can_suspend/ban/remove/reactivate/change_role |
| MembershipOutputSerializer | `apps/rbac/serializers.py:132-154` | COMPLETE — 12 fields |
| MembershipListOutputSerializer | `apps/rbac/serializers.py:157-175` | COMPLETE — 7 fields |
| TransactionSelector methods | `apps/transaction/selectors.py:14-278` | COMPLETE — 17 methods |

### Backend — New Work Required

| Component | Why |
|-----------|-----|
| `MembershipSelector.list_all_members()` | No cross-account member listing exists — only per-account |
| `MembershipSelector.get_membership_by_id_global()` | No governance-scoped single membership lookup |
| GovernanceMemberListView | New endpoint: GET /api/v1/governance/members/ |
| GovernanceMemberDetailView | New endpoint: GET /api/v1/governance/members/{id}/ |
| GovernanceMemberActionView | New endpoint: POST /api/v1/governance/members/{id}/action/ |
| Governance member serializers | Need account context (business name, slug) in member list output |
| `TransactionSelector.list_all_transactions()` | No global transaction listing — only per-context or per-user |
| GovernanceTransactionListView | New endpoint: GET /api/v1/governance/transactions/ |

### Frontend — New Work Required

| Component | Why |
|-----------|-----|
| GovernanceAuditPage | Frontend page for already-complete audit endpoint |
| GovernanceMembersPage | Member search + list page |
| GovernanceMemberDetailPage | Member detail + enforcement actions |
| GovernanceTransactionsPage | Cross-account transaction list |
| GovernanceDashboardPage | Summary overview (replacing placeholder) |
| Audit types + API + hooks | Frontend integration for audit endpoint |
| Member governance types + API + hooks | Frontend integration for member endpoints |
| Transaction governance API + hooks | Governance-scoped transaction listing |

---

## 4. Implementation Steps

### Phase 3A: Backend — Cross-Account Member Governance

#### 3A-1. Extend MembershipSelector with global methods

**File:** `backend/apps/rbac/selectors.py`

Add methods after `get_users_with_permission()` (line ~498):

```python
@staticmethod
def list_all_members(
    *,
    account_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> QuerySet:
    """
    Global member listing for governance.
    Searches across ALL accounts. Filters by account_type, status, search.
    Search: email, username, first_name, last_name (case-insensitive).
    """

@staticmethod
def get_membership_by_id_global(*, membership_id: UUID) -> Membership:
    """
    Get any membership by ID (governance view, include all statuses).
    Raises NotFound if not found.
    """
```

**Pattern:** Follow `get_memberships_for_account()` (line 326) for search and ordering.
Use `Membership.all_objects` when `include_deleted=True`.
Always `select_related("user", "role")` and `order_by("-joined_at")`.

#### 3A-2. Governance member serializers

**New file:** `backend/apps/rbac/governance_serializers.py`

```python
class GovernanceMemberListOutput(BaseOutputSerializer):
    """Member listing for governance — includes account context."""
    # Fields from MembershipListOutputSerializer PLUS:
    # - account_name (annotated or from related)
    # - account_slug (for business accounts)
    # - user email, username, display_name, avatar_url
    # - status_reason
    # - status_changed_at

class GovernanceMemberDetailOutput(BaseOutputSerializer):
    """Full member detail for governance."""
    # All MembershipOutputSerializer fields PLUS:
    # - account_name, account_slug
    # - user full info (email, username, display_name)
    # - role details (name, level, permissions list)

class GovernanceMemberActionInput(BaseInputSerializer):
    """Input for governance member enforcement actions."""
    action = serializers.ChoiceField(
        choices=["suspend", "ban", "remove", "reactivate"]
    )
    reason = serializers.CharField(required=False, max_length=1000, allow_blank=True)
```

**Account context challenge:** Membership has generic `account_id` (UUID) + `account_type` (string), not a FK. The serializer must resolve account name:
- For `business` accounts: annotate with Subquery from BusinessAccount.legal_name
- For `platform` accounts: annotate with Subquery from PlatformAccount.name

#### 3A-3. Governance member permissions — USE EXISTING

**File:** `backend/apps/rbac/policies.py` — **NO CHANGES NEEDED**

The existing `MembershipPolicy.get_viewer_permissions()` (line 167-205) already returns the correct
permissions: `can_change_role`, `can_suspend`, `can_remove`, `can_ban`, `can_reactivate`.

It takes `actor_context` + `target_membership`. For governance views, build the ActorContext from
the governance user's platform membership (see D1), then pass the target membership from the URL.
The cross-account authorization in `authorize_action()` (line 81-83) correctly checks `global_only`
scope for cross-account actions — no new method needed.

#### 3A-4. Governance member views

**New file:** `backend/apps/rbac/governance_views.py`

3 endpoints — all use `[IsAuthenticated, GovernanceTokenRequired]`:

| View | Method | URL | Permission | Description |
|------|--------|-----|------------|-------------|
| `GovernanceMemberListView` | GET | `/members/` | `can_view_members` (global) | Cross-account member search |
| `GovernanceMemberDetailView` | GET | `/members/{id}/` | `can_view_members` (global) | Member detail + _permissions |
| `GovernanceMemberActionView` | POST | `/members/{id}/action/` | Per-action check | Suspend/ban/remove/reactivate |

**GovernanceMemberListView details:**
- Query params: `account_type`, `status`, `search`, `page`, `page_size`
- Uses `MembershipSelector.list_all_members(**params)`
- Annotate with account name via Subquery
- Returns `GovernanceMemberListOutput` with pagination

**GovernanceMemberDetailView details:**
- Lookup by membership UUID (not user UUID — a user may have multiple memberships)
- Manually inject `_permissions` (same approach as GovernanceBusinessDetailView)
- Returns `GovernanceMemberDetailOutput` + `_permissions`

**GovernanceMemberActionView details:**
- Accepts `action` (suspend/ban/remove/reactivate) and optional `reason`
- Permission check per action:
  - suspend → `can_suspend_member` (global scope)
  - ban → `can_ban_member` (global scope)
  - remove → `can_remove_member` (global scope)
  - reactivate → `can_suspend_member` (global scope, same as Phase 2 pattern)
- Delegates to `RBACService.update_membership_status()` which already handles:
  - Owner invincibility check
  - Audit logging (MEMBERSHIP_SUSPENDED / MEMBERSHIP_BANNED / MEMBERSHIP_REMOVED / MEMBERSHIP_REACTIVATED)
  - Permission cache invalidation

**Key:** The governance actor needs an ActorContext. Since they're a platform member with global permissions, build it from their platform membership:
```python
platform = PlatformAccount.objects.first()
actor_membership = MembershipSelector.get_active_membership_for_user_account(
    user=request.user, account_type="platform", account_id=platform.id
)
actor_context = RBACService.build_actor_context(membership=actor_membership, request=request)
```

#### 3A-5. Register member governance URLs

**File:** `backend/backend_core/urls/governance.py`

Add 3 URL patterns:
```python
path("api/v1/governance/members/", GovernanceMemberListView.as_view()),
path("api/v1/governance/members/<uuid:pk>/", GovernanceMemberDetailView.as_view()),
path("api/v1/governance/members/<uuid:pk>/action/", GovernanceMemberActionView.as_view()),
```

### Phase 3B: Backend — Global Transaction Listing

#### 3B-1. Extend TransactionSelector

**File:** `backend/apps/transaction/selectors.py`

Add method after `list_pending_for_context()` (line ~202):

```python
@staticmethod
def list_all_transactions(
    *,
    status: str | None = None,
    mode: str | None = None,
    transaction_type: str | None = None,
    context_type: str | None = None,
    include_terminal: bool = True,
) -> QuerySet:
    """Global transaction listing for governance. All accounts."""
```

**Pattern:** Follow `list_for_context()` (line 148) but without context filter.
Always `select_related("transaction_type_ref")`, ordered by `-created_at`.

#### 3B-2. Governance transaction view

**New file:** `backend/apps/transaction/governance_views.py`

1 endpoint:

| View | Method | URL | Permission |
|------|--------|-----|------------|
| `GovernanceTransactionListView` | GET | `/transactions/` | `can_view_all_transactions` (global) |

**Details:**
- Permission classes: `[IsAuthenticated, GovernanceTokenRequired]`
- Uses `TransactionSelector.list_all_transactions(**params)`
- Reuses existing `TransactionListSerializer` from `apps/transaction/api/serializers.py`
- Query params: `status`, `mode`, `transaction_type`, `context_type`, `page`, `page_size`
- `StandardPagination`

**Transaction detail:** Reuse existing `GET /api/v1/transactions/{id}/` endpoint — governance users already have `can_view_all_transactions` permission which the existing `TransactionDetailView` checks via `TransactionPolicy.can_view()`.

#### 3B-3. Register transaction governance URL

**File:** `backend/backend_core/urls/governance.py`

```python
path("api/v1/governance/transactions/", GovernanceTransactionListView.as_view()),
```

### Phase 3C: Backend — Tests

#### 3C-1. Member governance tests

**New file:** `backend/apps/rbac/tests/test_governance_views.py`

Test matrix:
- Global Moderator with governance token → 200
- Platform Admin with governance token → 403 (no global member perms)
- Regular user → 403
- Unauthenticated → 401
- Member action: suspend → verify status change + audit log
- Member action: ban → verify status change
- Member action on owner → blocked (owner invincibility)
- Search: by email, by username
- Filter: by account_type, by status

#### 3C-2. Selector tests

**File:** `backend/apps/rbac/tests/test_selectors.py`

Add tests for `list_all_members()`:
- Returns members from multiple accounts
- Filters by account_type
- Filters by status
- Search by email/username
- Excludes deleted when `include_deleted=False`

#### 3C-3. Transaction governance tests

**New file:** `backend/apps/transaction/tests/test_governance_views.py`

Test matrix:
- Global Moderator → 200
- Regular user → 403
- Unauthenticated → 401
- Filters: status, mode, transaction_type

### Phase 3D: Frontend — Audit Log Viewer

**Backend endpoint already complete.** This is frontend-only work.

#### 3D-1. Audit types

**File:** `frontend/src/types/governance.ts` (extend existing)

```typescript
export interface GovernanceAuditLog {
  id: string;
  timestamp: string;
  actor_id: string;
  actor_email: string;
  actor_type: string;   // USER | ADMIN | SYSTEM | ANONYMOUS
  action: string;
  resource_type: string;
  resource_id: string;
  resource_repr: string;
  outcome: string;      // SUCCESS | FAILURE | DENIED
  details: Record<string, unknown> | null;
  changes: Record<string, unknown> | null;
  ip_address: string | null;
  request_id: string | null;
}

export interface GovernanceAuditListParams {
  action?: string;
  outcome?: string;
  actor_id?: string;
  since?: string;       // ISO datetime
  until?: string;       // ISO datetime
  resource_type?: string;
  page?: number;
  page_size?: number;
}
```

#### 3D-2. Audit API functions

**New file:** `frontend/src/features/governance/api/governance-audit-api.ts`

```typescript
export async function listGovernanceAuditApi(
  params?: GovernanceAuditListParams,
): Promise<PaginatedResponse<GovernanceAuditLog>>
```

Uses `governanceApiClient` → GET `/audit/`

#### 3D-3. Audit query hooks

**File:** `frontend/src/features/governance/hooks/use-governance-queries.ts` (extend)

```typescript
export function useGovernanceAuditLogs(params?: GovernanceAuditListParams)
```

Add query key to `frontend/src/lib/query-keys.ts`:
```typescript
auditLogs: (params?: Record<string, unknown>) =>
  [...queryKeys.governance.all, "audit-logs", params] as const,
```

#### 3D-4. Audit log page component

**New file:** `frontend/src/features/governance/components/GovernanceAuditPage.tsx`

Features:
- Filter bar: action dropdown, outcome dropdown, actor ID input, date range (since/until), resource_type dropdown
- Paginated table with columns: timestamp, actor_email, action, resource_repr, outcome
- Expandable rows showing details/changes JSON
- Color-coded outcome badges (SUCCESS=green, FAILURE=red, DENIED=amber)
- Color-coded actor_type badges (USER=default, ADMIN=amber, SYSTEM=blue)

**Pattern:** Follow `GovernanceBusinessesPage.tsx` for filter bar + pagination.

#### 3D-5. Audit route wrapper

**New file:** `frontend/src/app/(app)/gconsole/audit/page.tsx`

```tsx
import { GovernanceAuditPage } from "@/features/governance/components/GovernanceAuditPage";
export default function Page() { return <GovernanceAuditPage />; }
```

### Phase 3E: Frontend — Member Governance Pages

#### 3E-1. Member governance types

**File:** `frontend/src/types/governance.ts` (extend)

```typescript
export interface GovernanceMember {
  id: string;                    // membership UUID
  user: { id: string; email: string; username: string; display_name: string; avatar_url: string | null; };
  account_type: string;
  account_id: string;
  account_name: string;
  account_slug: string | null;   // null for platform
  role_name: string;
  role_level: number;
  is_owner: boolean;
  status: string;
  joined_at: string;
  status_changed_at: string | null;
  status_reason: string;
}

export interface GovernanceMemberDetail extends GovernanceMember {
  created_at: string;
  updated_at: string;
}

export type GovernanceMemberPermissions = {
  can_suspend: boolean;
  can_ban: boolean;
  can_remove: boolean;
  can_reactivate: boolean;
  can_change_role: boolean;
};

export type GovernanceMemberDetailWithPerms = GovernanceMemberDetail &
  WithPermissions<GovernanceMemberPermissions>;

export interface GovernanceMemberListParams {
  account_type?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}
```

#### 3E-2. Member governance API

**New file:** `frontend/src/features/governance/api/governance-members-api.ts`

```typescript
export async function listGovernanceMembersApi(params): Promise<PaginatedResponse<GovernanceMember>>
export async function getGovernanceMemberApi(id): Promise<GovernanceMemberDetailWithPerms>
export async function governanceMemberActionApi(id, action, reason?): Promise<void>
```

Uses `governanceApiClient`.

#### 3E-3. Member query/mutation hooks

**File:** `frontend/src/features/governance/hooks/use-governance-queries.ts` (extend)

```typescript
export function useGovernanceMembers(params?: GovernanceMemberListParams)
export function useGovernanceMember(id: string)
```

**File:** `frontend/src/features/governance/hooks/use-governance-mutations.ts` (extend)

```typescript
export function useGovernanceMemberAction()
// mutationFn: ({ id, action, reason }) => governanceMemberActionApi(id, action, reason)
```

Add query keys to `frontend/src/lib/query-keys.ts`:
```typescript
members: (params?: Record<string, unknown>) =>
  [...queryKeys.governance.all, "members", params] as const,
memberDetail: (id: string) =>
  [...queryKeys.governance.all, "member", id] as const,
```

#### 3E-4. Members list page

**New file:** `frontend/src/features/governance/components/GovernanceMembersPage.tsx`

Features:
- Search bar: by email, username, name
- Filter: account_type (all/business/platform), status (all/active/suspended/banned/removed)
- Paginated list with member cards showing: avatar, name, email, account name, role, status badge
- Click → navigates to `/gconsole/members/[id]`

**Pattern:** Follow `GovernanceBusinessesPage.tsx`.

#### 3E-5. Member detail page

**New file:** `frontend/src/features/governance/components/GovernanceMemberDetailPage.tsx`

Features:
- Member info card: user details, account context, role, status, join date
- Action buttons gated by `_permissions`:
  - `<Can allowed={permissions.can_suspend && member.status === "active"}>` → Suspend
  - `<Can allowed={permissions.can_ban && member.status !== "banned"}>` → Ban
  - `<Can allowed={permissions.can_remove && member.status === "active"}>` → Remove
  - `<Can allowed={permissions.can_reactivate && (member.status === "suspended" || member.status === "removed")}>`→ Reactivate
- Action dialogs: `ConfirmActionDialog` with `showReasonField` for destructive actions

#### 3E-6. Member route wrappers

```
frontend/src/app/(app)/gconsole/members/page.tsx          → GovernanceMembersPage
frontend/src/app/(app)/gconsole/members/[id]/page.tsx     → GovernanceMemberDetailPage
```

### Phase 3F: Frontend — Global Transactions Page

#### 3F-1. Governance transaction API

**New file:** `frontend/src/features/governance/api/governance-transactions-api.ts`

```typescript
export async function listGovernanceTransactionsApi(params): Promise<PaginatedResponse<TransactionListItem>>
```

Uses `governanceApiClient` → GET `/transactions/`

**Reuse existing types:** `TransactionListItem` from `frontend/src/types/transactions.ts` — no new type needed.

#### 3F-2. Transaction query hook

**File:** `frontend/src/features/governance/hooks/use-governance-queries.ts` (extend)

```typescript
export function useGovernanceTransactions(params?: GovernanceTransactionListParams)
```

Add query key:
```typescript
transactions: (params?: Record<string, unknown>) =>
  [...queryKeys.governance.all, "transactions", params] as const,
```

#### 3F-3. Transactions page component

**New file:** `frontend/src/features/governance/components/GovernanceTransactionsPage.tsx`

Features:
- Filter bar: status, mode (invitation/request), transaction_type, context_type
- Paginated list showing: type, initiator, target, status badge, context, created date
- Click → navigates to existing `/transactions/{id}` detail (reuses existing detail page)

#### 3F-4. Transaction route wrapper

```
frontend/src/app/(app)/gconsole/transactions/page.tsx     → GovernanceTransactionsPage
```

### Phase 3G: Frontend — Dashboard

#### 3G-1. Dashboard page component

**File:** `frontend/src/features/governance/components/GovernanceDashboardPage.tsx`

Replace the current placeholder with a summary overview:

Features:
- Title: "Governance Console" with Shield icon
- Summary cards (read-only, no new endpoints needed):
  - Active Businesses count (from `/governance/businesses/?status=active&page_size=1`)
  - Suspended Businesses count (from `/governance/businesses/?status=suspended&page_size=1`)
  - Pending Verifications count (from `/governance/verification/?page_size=1`)
  - Quick links to each section

**Note:** No new backend endpoints. Uses existing list endpoints with `page_size=1` to get counts from the `count` field in paginated responses. This avoids building dedicated count endpoints.

#### 3G-2. Update dashboard route

**File:** `frontend/src/app/(app)/gconsole/dashboard/page.tsx`

Replace placeholder with:
```tsx
import { GovernanceDashboardPage } from "@/features/governance/components/GovernanceDashboardPage";
export default function Page() { return <GovernanceDashboardPage />; }
```

---

## 5. Files Summary

### New files (Backend: ~5, Frontend: ~10):

| File | Purpose |
|------|---------|
| `backend/apps/rbac/governance_serializers.py` | Member governance serializers |
| `backend/apps/rbac/governance_views.py` | 3 member governance views |
| `backend/apps/transaction/governance_views.py` | 1 transaction governance view |
| `backend/apps/rbac/tests/test_governance_views.py` | Member governance tests |
| `backend/apps/transaction/tests/test_governance_views.py` | Transaction governance tests |
| `frontend/src/features/governance/api/governance-audit-api.ts` | Audit API functions |
| `frontend/src/features/governance/api/governance-members-api.ts` | Member API functions |
| `frontend/src/features/governance/api/governance-transactions-api.ts` | Transaction API functions |
| `frontend/src/features/governance/components/GovernanceAuditPage.tsx` | Audit log viewer |
| `frontend/src/features/governance/components/GovernanceMembersPage.tsx` | Member search/list |
| `frontend/src/features/governance/components/GovernanceMemberDetailPage.tsx` | Member detail + actions |
| `frontend/src/features/governance/components/GovernanceTransactionsPage.tsx` | Global transaction list |
| `frontend/src/features/governance/components/GovernanceDashboardPage.tsx` | Dashboard overview |
| `frontend/src/app/(app)/gconsole/members/page.tsx` | Route wrapper |
| `frontend/src/app/(app)/gconsole/members/[id]/page.tsx` | Route wrapper |
| `frontend/src/app/(app)/gconsole/transactions/page.tsx` | Route wrapper |
| `frontend/src/app/(app)/gconsole/audit/page.tsx` | Route wrapper |

### Modified files:

| File | Changes |
|------|---------|
| `backend/apps/rbac/selectors.py` | Add `list_all_members()`, `get_membership_by_id_global()` |
| `backend/apps/transaction/selectors.py` | Add `list_all_transactions()` |
| `backend/backend_core/urls/governance.py` | Add 4 URL patterns (3 member + 1 transaction) |
| `frontend/src/types/governance.ts` | Add audit, member, transaction types |
| `frontend/src/lib/query-keys.ts` | Add audit, member, transaction keys |
| `frontend/src/features/governance/hooks/use-governance-queries.ts` | Add audit, member, transaction hooks |
| `frontend/src/features/governance/hooks/use-governance-mutations.ts` | Add member action mutation |
| `frontend/src/app/(app)/gconsole/dashboard/page.tsx` | Replace placeholder |

---

## 6. Implementation Order

```
3A-1  Extend MembershipSelector (list_all_members, get_membership_by_id_global)
3A-2  Governance member serializers (list output, detail output, action input)
3A-3  (no changes — existing MembershipPolicy.get_viewer_permissions() works for governance)
3A-4  Governance member views (list, detail, action)
3A-5  Register member governance URLs
  │
  ▼
3B-1  Extend TransactionSelector (list_all_transactions)
3B-2  Governance transaction view
3B-3  Register transaction governance URL
  │
  ▼
3C    Backend tests (member governance + transaction governance + selector tests)
  │
  ▼
3D-1  Frontend audit types
3D-2  Audit API functions
3D-3  Audit query hooks + query keys
3D-4  Audit log page component
3D-5  Audit route wrapper
  │
  ▼
3E-1  Frontend member types
3E-2  Member API functions
3E-3  Member query/mutation hooks + query keys
3E-4  Members list page
3E-5  Member detail page
3E-6  Member route wrappers
  │
  ▼
3F-1  Governance transaction API
3F-2  Transaction query hook + query key
3F-3  Transactions page component
3F-4  Transaction route wrapper
  │
  ▼
3G-1  Dashboard page component
3G-2  Update dashboard route
  │
  ▼
VERIFY: black + isort + flake8 + pytest (backend)
        tsc --noEmit + npm run lint + npm run test (frontend)
```

---

## 7. Key Patterns to Reuse

| Pattern | Source File | Lines |
|---------|-----------|-------|
| GovernanceTokenRequired on all views | `apps/core/permissions/governance.py` | 23-62 |
| `_has_global_permission()` pattern | `apps/organization/business/policies.py` | 48-80 |
| Manual `_permissions` injection (detail) | `apps/organization/business/governance_views.py` | 121-146 |
| Subquery for account_name annotation | `apps/organization/business/governance_views.py` | 430-461 |
| GovernanceSuspendInput (reason field) | `apps/organization/business/governance_serializers.py` | 119-121 |
| RBACService.build_actor_context() | `apps/rbac/services.py` | 74-119 |
| RBACService.update_membership_status() | `apps/rbac/services.py` | 574-671 |
| MembershipPolicy.authorize_action() | `apps/rbac/policies.py` | 38-123 |
| MembershipPolicy.get_viewer_permissions() | `apps/rbac/policies.py` | 167-205 |
| GovernanceBusinessesPage (filter+paginate) | `frontend GovernanceBusinessesPage.tsx` | — |
| GovernanceBusinessDetailPage (detail+actions) | `frontend GovernanceBusinessDetailPage.tsx` | — |
| ConfirmActionDialog (destructive actions) | `frontend/src/components/common/ConfirmActionDialog.tsx` | 1-103 |
| Can component (permission gating) | `frontend/src/components/common/Can.tsx` | 1-22 |
| governanceApiClient | `frontend/src/lib/governance-api-client.ts` | 1-65 |

---

## 8. Critical Design Decisions

### D1: Actor Context for Governance Member Actions

**Problem:** `RBACService.update_membership_status()` requires an `ActorContext`, built from the actor's membership. The governance user acts on members from ANY account. Their authority comes from their platform membership with global permissions.

**Solution:** Build ActorContext from the governance user's platform membership:
```python
platform = PlatformAccount.objects.first()
actor_membership = MembershipSelector.get_active_membership_for_user_account(
    user=request.user, account_type="platform", account_id=platform.id
)
actor_context = RBACService.build_actor_context(membership=actor_membership, request=request)
```

The existing `MembershipPolicy.authorize_action()` already handles cross-account authorization at line 83: when `same_account=False`, it only checks `global_only` scope — which the governance user has.

### D2: Account Name in Member List

**Problem:** Membership has generic `account_id` (UUID) + `account_type` (string), not a FK. The governance member list needs to show the account name.

**Solution:** Use Subquery annotation, same pattern as `_annotate_member_count()` in Phase 2:

**Important:** `PlatformAccount` does NOT have a `name` field. The name is on
`PlatformProfile` (related via OneToOneField). Use the profile relation:

```python
from apps.organization.business.models import BusinessAccount
from apps.organization.platform.models import PlatformProfile

business_name_sq = Subquery(
    BusinessAccount.all_objects.filter(id=OuterRef("account_id")).values("legal_name")[:1]
)
platform_name_sq = Subquery(
    PlatformProfile.objects.filter(platform_id=OuterRef("account_id")).values("name")[:1]
)
qs = qs.annotate(
    account_name=Case(
        When(account_type="business", then=business_name_sq),
        When(account_type="platform", then=platform_name_sq),
        default=Value("Unknown"),
        output_field=CharField(),
    ),
    account_slug=Subquery(
        BusinessAccount.all_objects.filter(id=OuterRef("account_id")).values("slug")[:1]
    ),
)
```

### D3: Transaction Detail Navigation

**Problem:** Should governance users navigate to an existing transaction detail page, or do we need a governance-specific one?

**Solution:** Reuse existing transaction detail. The `TransactionDetailView` already checks `TransactionPolicy.can_view()` which respects `can_view_all_transactions` at global scope (line 254). Governance users with this permission can view any transaction detail. Frontend links to `/transactions/{id}` (existing route).

### D4: Dashboard Counts Without New Endpoints

**Problem:** The dashboard needs summary counts (active businesses, suspended, pending verifications). Building dedicated count endpoints adds complexity.

**Solution:** Reuse existing governance list endpoints with `page_size=1`. The `count` field in paginated responses gives the total. This is a standard DRF pattern — the DB query runs with `COUNT(*)` before slicing, so `page_size=1` only fetches 1 row but returns the full count.

### D5: Member Enforcement Scope

**Problem:** When a governance user suspends a member in Business A, should the suspension cascade to Business B where the same user is also a member?

**Solution:** No cascade. Each membership is independent. Suspending membership in Business A only affects that membership. If the governance user wants to enforce across all of a user's memberships, they do it per-membership from the member list (filtered by the user's email). This matches the existing `update_membership_status()` behavior which operates on a single `membership_id`.

---

## 9. Permissions Summary

### Existing Permissions Used (no new permissions needed)

| Permission Code | Scope | Used By |
|---|---|---|
| `can_view_members` | `global_only` | GovernanceMemberListView, GovernanceMemberDetailView |
| `can_suspend_member` | `global_only` | GovernanceMemberActionView (suspend, reactivate) |
| `can_ban_member` | `global_only` | GovernanceMemberActionView (ban) |
| `can_remove_member` | `global_only` | GovernanceMemberActionView (remove) |
| `can_view_audit_logs` | `global_only` | GovernanceAuditListView (already built) |
| `can_view_all_transactions` | `global_only` | GovernanceTransactionListView |

All 6 permissions already exist in `apps/rbac/permissions/registry.py`. No new permissions needed.

---

## 10. Verification

### Backend:
```bash
cd backend
black . && isort . && flake8 .
DJANGO_SETTINGS_MODULE=backend_core.settings.local python -m pytest -v --tb=short
```

### Frontend:
```bash
cd frontend
npx tsc --noEmit
npm run lint
npm run test
```

### Manual E2E:
1. `make dev` (start server + Docker infra)
2. Login as Platform Owner or Global Moderator
3. Navigate to `/gconsole` → step-up auth
4. Authenticate → dashboard with summary cards
5. Click "Members" → cross-account member search
6. Search by email → find member across businesses
7. Click member → detail page with actions
8. Suspend member → confirm with reason → status changes
9. Reactivate → status back to active
10. Click "Audit Log" → filterable audit viewer
11. Filter by action=MEMBERSHIP_SUSPENDED → see recent suspension
12. Click "Transactions" → cross-account transaction list
13. Filter by status=pending → see pending transactions

---

## 11. Verification Corrections (2026-04-08)

Issues found during plan review and fixed:

| # | Issue | Fix |
|---|-------|-----|
| 1 | Plan referenced `TransactionListOutputSerializer` | Actual name is `TransactionListSerializer` (line 228 in `apps/transaction/api/serializers.py`). Corrected. |
| 2 | D2 Subquery referenced `PlatformAccount.name` | `PlatformAccount` has no `name` field. Name is on `PlatformProfile` (line 76 in platform/models.py). Fixed to use `PlatformProfile.objects.filter(platform_id=OuterRef("account_id"))`. |
| 3 | Plan proposed `MembershipPolicy.get_governance_viewer_permissions()` as new method | Existing `MembershipPolicy.get_viewer_permissions()` (line 167-205) already works for governance — takes `actor_context` + `target_membership`, handles cross-account via `authorize_action()`. No new method needed. Removed from plan. |
| 4 | "New Work Required" table listed `list_all_members()` and `list_filtered_global()` as separate items | These are the same method — `list_all_members()` includes filter params. Deduplicated. |
| 5 | "New Work Required" table listed `BusinessPolicy.get_governance_member_permissions()` | Unnecessary — `MembershipPolicy.get_viewer_permissions()` is the correct method. Removed. |
| 6 | `force_transfer_ownership()` line reference | Verified at line 910 in `apps/rbac/services.py` (was added in Phase 2). |

All permissions verified against `apps/rbac/permissions/registry.py`:
- `can_view_members` (line 70, scopes: business, platform_only, global_only)
- `can_suspend_member` (line 49, scopes: business, global_only)
- `can_ban_member` (line 56, scopes: business, global_only)
- `can_remove_member` (line 35, scopes: business, global_only)
- `can_view_audit_logs` (line 200, scopes: business, platform_only, global_only, platform_and_global)
- `can_view_all_transactions` (line 190, scopes: global_only, platform_and_global)

Cross-account authorization verified at `MembershipPolicy.authorize_action()`:
- Line 81-83: Cross-account actions use `global_only` scope only
- Line 114-122: Dominance rule skipped for cross-account
- Line 100-112: Owner invincibility — business owners can be acted on cross-account, platform owner is always invincible

`TransactionPolicy.can_view()` verified at line 253-255: checks `can_view_all_transactions` via `actor_context.has_global_permission()`.
