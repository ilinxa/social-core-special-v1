# gconsole Phase 2 — Business Governance Implementation Plan

**Version:** 1.0
**Date:** 2026-04-07
**Depends on:** gconsole Phase 1 (complete — 4393 tests passing)
**Description doc:** `docs/descriptions/backend/gconsole_global_governance_console.md`
**Scope:** Backend governance endpoints + frontend governance pages

---

## 1. Abstract — What We Have Done (Phase 1 Recap)

Phase 1 built the gconsole foundation across 23 files:

### Backend Foundation (4393 tests, 0 failures)
- **Step-up auth system** — `GovernanceAuthService` in `apps/auth/services/governance_service.py`: password re-entry OR email OTP (6-digit, 5-min TTL). Issues short-lived governance JWT with `token_scope: "governance"`.
- **GovernanceOTPToken model** — `apps/auth/models.py`: separate from EmailVerificationToken, with attempt tracking and per-token brute-force protection.
- **GovernanceTokenRequired permission** — `apps/core/permissions/governance.py`: validates `token_scope == "governance"` + real-time membership check (global_only or platform_and_global permissions). Runs on every governance request.
- **3 auth endpoints** — `POST /api/v1/auth/governance/authenticate/`, `otp/send/`, `otp/verify/`. All require standard IsAuthenticated. Return `{access, expires_in}` with no refresh token.
- **Governance URL group** — `backend_core/urls/governance.py` (empty shell) + registered in GATED_GROUPS with `systems.governance` gate.
- **RBAC-only authorization** — Removed all 12 `is_staff`/`is_superuser` checks from BusinessPolicy (9) and PlatformPolicy (2). All authorization is now RBAC-based. Superuser bypass only in `/admin` diagnostics.
- **Business state machine** — `VALID_TRANSITIONS` table in `apps/organization/business/transitions.py`. All 4 service methods (suspend, reactivate, archive, soft_delete) now validate transitions.
- **Config** — `systems.governance: true` + `auth.governance.*` paths in deployment_config.json, conftest.py, and full example doc.
- **Audit actions** — 3 new: `auth.governance.authenticated`, `session_expired`, `session_locked`.
- **Permission scope fix** — `can_approve_business_creation` now includes `global_only` (was `platform_only` only). Data migration applied.

### Frontend Foundation (0 TypeScript errors, 0 ESLint errors)
- **Governance token manager** — `lib/governance-token.ts`: sessionStorage-based (per-tab, survives refresh).
- **Governance API client** — `lib/governance-api-client.ts`: Axios instance attaching governance token as Authorization: Bearer. Redirects to authenticate on 401/403.
- **GovernanceGuard** — `components/guards/GovernanceGuard.tsx`: checks governance token validity, exempts /gconsole/authenticate, periodic 30s re-check.
- **Step-up auth page** — `/gconsole/authenticate`: password tab + OTP tab with proper error handling.
- **Dashboard placeholder** — `/gconsole/dashboard`.
- **Navigation** — governance context type + nav config with 6 items (dashboard, businesses, members, approved-creators, audit, transactions).

---

## 2. Big Picture — What Phase 2 Builds

Phase 2 adds the actual governance business operations:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     GOVERNANCE CONSOLE                              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────────────────────────────────┐ │
│  │ Step-up Auth  │  │ Phase 2: Business Governance                │ │
│  │ (Phase 1) ✓   │  │                                            │ │
│  │ Password/OTP  │  │  /gconsole/businesses          — list all  │ │
│  │ → Gov Token   │  │  /gconsole/businesses/[id]     — detail    │ │
│  └──────┬───────┘  │  /gconsole/businesses/[id]/suspend          │ │
│         │          │  /gconsole/businesses/[id]/reactivate        │ │
│         ▼          │  /gconsole/businesses/[id]/archive           │ │
│  ┌──────────────┐  │  /gconsole/businesses/[id]/transfer         │ │
│  │  Gov Token   │  │  /gconsole/approved-creators    — manage    │ │
│  │  Required    │  │  /gconsole/verification         — review    │ │
│  │  (Phase 1) ✓ │  │                                            │ │
│  └──────┬───────┘  └──────────────────────────────────────────────┘ │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Backend: /api/v1/governance/businesses/*                     │   │
│  │   GovernanceTokenRequired on ALL endpoints                   │   │
│  │   BusinessPolicy._has_global_permission() for per-action     │   │
│  │   StandardPagination for lists                               │   │
│  │   PermissionInjectMixin for detail (_permissions)            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### What gets built:
1. **Backend** — 8 governance endpoints under `/api/v1/governance/` with GovernanceTokenRequired
2. **Backend** — Extended business selector (list_all, filter by status/verification/type)
3. **Backend** — Governance business policy (get_viewer_permissions for governance context)
4. **Backend** — Forced ownership transfer service method
5. **Frontend** — `/gconsole/businesses` list page with filters
6. **Frontend** — `/gconsole/businesses/[id]` detail page with Tier 1.5 _permissions + action buttons
7. **Frontend** — Governance action dialogs (suspend with reason, confirm transfer)
8. **Frontend** — Move `/pconsole/approved-creators` to `/gconsole/approved-creators`
9. **Frontend** — `/gconsole/verification` page for reviewing pending verification requests

---

## 3. Implementation Steps

### Phase 2A: Backend — Selectors & Serializers

#### 2A-1. Extend BusinessAccountSelector

**File:** `backend/apps/organization/business/selectors.py`

Add methods:
```python
@staticmethod
def list_all(*, include_deleted=False) -> QuerySet:
    """All businesses (governance view). Optionally include soft-deleted."""

@staticmethod
def list_filtered(
    *,
    status: str | None = None,
    verification_status: str | None = None,
    business_type: str | None = None,
    country: str | None = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> QuerySet:
    """Filtered list for governance. Supports status, verification, type, country, search."""
```

Pattern: follow `list_active()` (line 119) but without status filter. Add optional chained filters.

#### 2A-2. Governance serializers

**New file:** `backend/apps/organization/business/governance_serializers.py`

```python
class GovernanceBusinessListOutput(BaseOutputSerializer):
    """List output for governance — includes fields hidden from public."""
    # All fields from BusinessAccountListOutput PLUS:
    # - status_display, verification_status_display
    # - member_count (annotated)
    # - created_by email
    # - updated_at

class GovernanceBusinessDetailOutput(BaseOutputSerializer):
    """Detail output with governance-specific fields + _permissions."""
    # Full BusinessAccountOutput fields PLUS:
    # - member_count, owner_email, owner_name
    # - suspension reason (from last audit log)

class GovernanceSuspendInput(BaseInputSerializer):
    reason = serializers.CharField(required=True, max_length=1000)

class GovernanceTransferOwnershipInput(BaseInputSerializer):
    new_owner_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(required=False, max_length=1000)
```

#### 2A-3. Governance viewer permissions

**File:** `backend/apps/organization/business/policies.py`

Add method to BusinessPolicy:
```python
@staticmethod
def get_governance_viewer_permissions(*, user) -> dict:
    """Get governance action permissions for the user (not business-specific)."""
    return {
        "can_suspend": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_suspend_business"
        ),
        "can_view_businesses": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_view_businesses"
        ),
        "can_edit": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_edit_business"
        ),
        "can_verify": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_approve_verification_request"
        ),
        "can_remove_owner": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_remove_business_owner"
        ),
        "can_transfer_ownership": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_transfer_business_ownership"
        ),
        "can_view_legal_info": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_view_legal_info"
        ),
        "can_archive": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_suspend_business"
        ),
        "can_approve_creation": BusinessPolicy._has_global_permission(
            user=user, permission_code="can_approve_business_creation"
        ),
    }
```

### Phase 2B: Backend — Views & URLs

#### 2B-1. Governance business views

**New file:** `backend/apps/organization/business/governance_views.py`

8 endpoints — all use `[IsAuthenticated, GovernanceTokenRequired]`:

| View | Method | URL | Permission Check | Service Call |
|------|--------|-----|-----------------|--------------|
| `GovernanceBusinessListView` | GET | `/businesses/` | `can_view_businesses` | `BusinessAccountSelector.list_filtered()` |
| `GovernanceBusinessDetailView` | GET | `/businesses/{id}/` | `can_view_businesses` | `BusinessAccountSelector.get_by_id()` + _permissions |
| `GovernanceBusinessSuspendView` | POST | `/businesses/{id}/suspend/` | `can_suspend_business` | `BusinessAccountService.suspend()` |
| `GovernanceBusinessReactivateView` | POST | `/businesses/{id}/reactivate/` | `can_suspend_business` | `BusinessAccountService.reactivate()` |
| `GovernanceBusinessArchiveView` | POST | `/businesses/{id}/archive/` | `can_suspend_business` | `BusinessAccountService.archive()` |
| `GovernanceBusinessTransferView` | POST | `/businesses/{id}/transfer-ownership/` | `can_transfer_business_ownership` | `RBACService.transfer_ownership()` (forced) |
| `GovernanceVerificationListView` | GET | `/verification/` | `can_approve_verification_request` | Transaction selector (pending verifications) |
| `GovernanceApprovedCreatorsView` | GET | `/approved-creators/` | `can_approve_business_creation` | `User.objects.filter(can_create_business=True)` |

**Pattern to follow:** BusinessSuspendView (views.py:712-766)
- Lookup by UUID (not slug) for governance — avoids slug collision issues
- PermissionInjectMixin on detail view only
- StandardPagination on list views

#### 2B-2. Forced ownership transfer service

**File:** `backend/apps/rbac/services.py`

Add method:
```python
@staticmethod
@transaction.atomic
def force_transfer_ownership(
    *,
    account_type,
    account_id,
    new_owner_user,
    actor,
    request=None,
) -> None:
    """Governance-initiated forced ownership transfer."""
    # 1. Validate new_owner is active member of the business
    # 2. Call existing transfer_ownership() logic
    # 3. Audit log with actor_type=ADMIN
```

Reuses existing `RBACService.transfer_ownership()` (services.py:806-915).

**Owner removal guard:** Block removal if owner is the only member (Decision: block if only member).

#### 2B-3. Governance URL registration

**File:** `backend/backend_core/urls/governance.py`

```python
from django.urls import path
from apps.organization.business import governance_views

urlpatterns = [
    # Business governance
    path("api/v1/governance/businesses/", governance_views.GovernanceBusinessListView.as_view()),
    path("api/v1/governance/businesses/<uuid:pk>/", governance_views.GovernanceBusinessDetailView.as_view()),
    path("api/v1/governance/businesses/<uuid:pk>/suspend/", governance_views.GovernanceBusinessSuspendView.as_view()),
    path("api/v1/governance/businesses/<uuid:pk>/reactivate/", governance_views.GovernanceBusinessReactivateView.as_view()),
    path("api/v1/governance/businesses/<uuid:pk>/archive/", governance_views.GovernanceBusinessArchiveView.as_view()),
    path("api/v1/governance/businesses/<uuid:pk>/transfer-ownership/", governance_views.GovernanceBusinessTransferView.as_view()),
    # Verification
    path("api/v1/governance/verification/", governance_views.GovernanceVerificationListView.as_view()),
    # Approved creators
    path("api/v1/governance/approved-creators/", governance_views.GovernanceApprovedCreatorsView.as_view()),
]
```

### Phase 2C: Backend — Tests

#### 2C-1. Governance endpoint tests

**New file:** `backend/apps/organization/tests/business/test_governance_views.py`

Test matrix per endpoint:
- Global Moderator → 200 (has permission)
- Platform Admin → 403 (no global scope)
- Regular user → 403 (no governance token / no permission)
- Unauthenticated → 401
- State machine: suspend only from ACTIVE, reactivate only from SUSPENDED, etc.
- Transfer: validates new_owner is member, blocks if only member
- Pagination: page_size, page params on list

#### 2C-2. Selector tests

**File:** `backend/apps/organization/tests/business/test_selectors.py`

Add tests for `list_all()`, `list_filtered()` with various filter combinations.

### Phase 2D: Frontend — Types & API

#### 2D-1. Governance types

**New file:** `frontend/src/types/governance.ts`

```typescript
export interface GovernanceBusiness {
  id: string;
  slug: string;
  legal_name: string;
  country: string;
  city: string;
  business_type: string;
  status: string;
  status_display: string;
  verification_status: string;
  verification_status_display: string;
  member_count: number;
  profile: { display_name: string; logo: string | null; tagline: string };
  created_at: string;
}

export interface GovernanceBusinessDetail extends GovernanceBusiness {
  /* full fields + legal info */
}

export type GovernanceBusinessPermissions = {
  can_suspend: boolean;
  can_view_businesses: boolean;
  can_edit: boolean;
  can_verify: boolean;
  can_remove_owner: boolean;
  can_transfer_ownership: boolean;
  can_view_legal_info: boolean;
  can_archive: boolean;
  can_approve_creation: boolean;
};

export type GovernanceBusinessDetailWithPerms =
  GovernanceBusinessDetail & WithPermissions<GovernanceBusinessPermissions>;
```

#### 2D-2. Governance business API

**New file:** `frontend/src/features/governance/api/governance-business-api.ts`

Uses `governanceApiClient` (attaches governance token):
```typescript
export async function listGovernanceBusinessesApi(params): Promise<PaginatedResponse<GovernanceBusiness>>
export async function getGovernanceBusinessApi(id): Promise<GovernanceBusinessDetailWithPerms>
export async function suspendBusinessApi(id, reason): Promise<GovernanceBusinessDetail>
export async function reactivateBusinessApi(id): Promise<GovernanceBusinessDetail>
export async function archiveBusinessApi(id): Promise<GovernanceBusinessDetail>
export async function transferOwnershipApi(id, newOwnerId, reason?): Promise<void>
```

#### 2D-3. Query hooks

**New file:** `frontend/src/features/governance/hooks/use-governance-queries.ts`

```typescript
export function useGovernanceBusinesses(params)  // useQuery with pagination
export function useGovernanceBusiness(id)         // useQuery for detail
```

**New file:** `frontend/src/features/governance/hooks/use-governance-mutations.ts`

```typescript
export function useSuspendBusiness()
export function useReactivateBusiness()
export function useArchiveBusiness()
export function useTransferOwnership()
```

### Phase 2E: Frontend — Pages

#### 2E-1. Business list page

**New file:** `frontend/src/app/(app)/gconsole/businesses/page.tsx`

Thin wrapper importing feature component.

**New file:** `frontend/src/features/governance/components/GovernanceBusinessesPage.tsx`

- Filter bar: status dropdown (all/active/suspended/archived), verification dropdown, search input
- Paginated list using `useGovernanceBusinesses()`
- Business cards showing: logo, name, status badge, verification badge, member count, country
- Click → navigates to `/gconsole/businesses/[id]`

Pattern: follow `ApprovedCreatorsPage.tsx` (search, sorting, pagination).

#### 2E-2. Business detail page

**New file:** `frontend/src/app/(app)/gconsole/businesses/[id]/page.tsx`

**New file:** `frontend/src/features/governance/components/GovernanceBusinessDetailPage.tsx`

- Business info card (name, slug, status, verification, legal info)
- Action buttons gated by `_permissions`:
  - `<Can allowed={permissions.can_suspend}>` → Suspend button
  - `<Can allowed={permissions.can_archive}>` → Archive button
  - `<Can allowed={permissions.can_transfer_ownership}>` → Transfer button
- Status badge with color coding (active=green, suspended=red, archived=gray)
- Member count summary
- Suspend dialog: uses `ConfirmActionDialog` with `showReasonField={true}`
- Transfer dialog: select member + confirm

#### 2E-3. Move approved-creators

**File:** `frontend/src/app/(app)/gconsole/approved-creators/page.tsx`

Thin wrapper importing existing `ApprovedCreatorsPage` from `features/users/components/`.
The feature component is reusable — just needs different route context.

**File:** `frontend/src/app/(app)/pconsole/approved-creators/page.tsx`

Replace with redirect to `/gconsole/approved-creators` or remove.

#### 2E-4. Verification review page

**New file:** `frontend/src/app/(app)/gconsole/verification/page.tsx`

**New file:** `frontend/src/features/governance/components/GovernanceVerificationPage.tsx`

- List pending verification requests (from governance `/verification/` endpoint)
- Each card shows: business name, submitted date, form data preview
- Actions: Approve / Reject via **existing** transaction endpoints (`POST /api/v1/transactions/{id}/accept/`, `/deny/`) — no new endpoints needed for approve/reject

#### 2E-5. Fix navigation context detection (Phase 1 gap)

**File 1:** `frontend/src/hooks/use-nav-context.ts`

Add governance detection before the personal fallback (before line 46):
```typescript
if (pathname.startsWith("/gconsole")) {
  return { type: "governance" as const };
}
```

**File 2:** `frontend/src/hooks/use-filtered-nav.ts`

Add governance context handling after the personal check (after line 23):
```typescript
if (context.type === "governance") {
  return sections;  // Show all items — governance token proves authorization
}
```

**IMPORTANT:** Do this FIRST in Phase 2 (before building pages) — without it, the sidebar won't render governance nav items on any /gconsole page.

---

## 4. Files Summary

### New files (Backend: ~8, Frontend: ~10):

| File | Purpose |
|------|---------|
| `backend/apps/organization/business/governance_views.py` | 8 governance endpoint views |
| `backend/apps/organization/business/governance_serializers.py` | Governance-specific serializers |
| `backend/apps/organization/tests/business/test_governance_views.py` | Governance view tests |
| `frontend/src/types/governance.ts` | Governance TypeScript types |
| `frontend/src/features/governance/api/governance-business-api.ts` | Business governance API functions |
| `frontend/src/features/governance/hooks/use-governance-queries.ts` | TanStack Query hooks |
| `frontend/src/features/governance/hooks/use-governance-mutations.ts` | Mutation hooks |
| `frontend/src/features/governance/components/GovernanceBusinessesPage.tsx` | Business list page |
| `frontend/src/features/governance/components/GovernanceBusinessDetailPage.tsx` | Business detail page |
| `frontend/src/features/governance/components/GovernanceVerificationPage.tsx` | Verification review page |
| `frontend/src/app/(app)/gconsole/businesses/page.tsx` | Route wrapper |
| `frontend/src/app/(app)/gconsole/businesses/[id]/page.tsx` | Route wrapper |
| `frontend/src/app/(app)/gconsole/approved-creators/page.tsx` | Route wrapper (reuses existing component) |
| `frontend/src/app/(app)/gconsole/verification/page.tsx` | Route wrapper |

### Modified files:

| File | Changes |
|------|---------|
| `backend/apps/organization/business/selectors.py` | Add list_all(), list_filtered() |
| `backend/apps/organization/business/policies.py` | Add get_governance_viewer_permissions() |
| `backend/apps/rbac/services.py` | Add force_transfer_ownership() |
| `backend/backend_core/urls/governance.py` | Add 8 URL patterns |
| `frontend/src/hooks/use-nav-context.ts` | Add /gconsole → governance detection (Phase 1 gap) |
| `frontend/src/hooks/use-filtered-nav.ts` | Add governance context = show all items (Phase 1 gap) |
| `frontend/src/app/(app)/pconsole/approved-creators/page.tsx` | Redirect to gconsole |

---

## 5. Implementation Order

```
PRE   Fix Phase 1 nav gaps (use-nav-context.ts + use-filtered-nav.ts)
  │
  ▼
2A-1  Extend BusinessAccountSelector (list_all, list_filtered)
2A-2  Governance serializers (list output, detail output, inputs)
2A-3  Governance viewer permissions in BusinessPolicy
  │
  ▼
2B-1  Governance business views (8 endpoints)
2B-2  Forced ownership transfer service method
2B-3  Governance URL registration
  │
  ▼
2C    Backend tests (governance views + selectors)
  │
  ▼
2D-1  Frontend types
2D-2  Governance business API functions
2D-3  Query + mutation hooks
  │
  ▼
2E-1  Business list page
2E-2  Business detail page + action dialogs
2E-3  Move approved-creators to gconsole
2E-4  Verification review page
  │
  ▼
VERIFY: make check (lint + full test suite)
```

---

## 5.1. Pre-Requisites (Phase 1 gaps to fix FIRST)

Two Phase 1 gaps were found during verification that MUST be fixed before Phase 2 implementation:

### Gap 1: Navigation context detection (CRITICAL)

**File:** `frontend/src/hooks/use-nav-context.ts`

Currently only detects personal/business/platform. Must add governance detection:
```typescript
// Add BEFORE the personal fallback (before line 46)
if (pathname.startsWith("/gconsole")) {
  return { type: "governance" as const };
}
```

Without this, `/gconsole/*` pages fall through to "personal" context and the sidebar shows personal nav items instead of governance items.

### Gap 2: Filtered nav for governance context (CRITICAL)

**File:** `frontend/src/hooks/use-filtered-nav.ts`

Currently line 27-33 only finds business or platform membership. Governance context falls through to `membership = undefined`, and line 35-37 returns empty array → **no nav items rendered**.

Fix: treat governance like personal — show all items (governance token already proves authorization):
```typescript
// Add after line 23 (personal context check)
if (context.type === "governance") {
  return sections;
}
```

### Both gaps must be fixed at the start of Phase 2 (step 2E-5) before any frontend pages will work correctly.

---

## 6. Key Patterns to Reuse

| Pattern | Source File | Lines |
|---------|-----------|-------|
| Governance view with GovernanceTokenRequired | `apps/core/permissions/governance.py` | 23-62 |
| PermissionInjectMixin for _permissions | `apps/core/views.py` | 56-96 |
| BusinessSuspendView (reference endpoint) | `apps/organization/business/views.py` | 712-766 |
| StandardPagination | `apps/core/pagination/page.py` | 33-59 |
| BusinessAccountListOutput | `apps/organization/business/serializers.py` | 214-236 |
| ConfirmActionDialog (destructive actions) | `frontend/src/components/common/ConfirmActionDialog.tsx` | 1-103 |
| Can component (permission gating) | `frontend/src/components/common/Can.tsx` | 1-22 |
| WithPermissions type | `frontend/src/types/api.ts` | 1-23 |
| ApprovedCreatorsPage (reusable) | `frontend/src/features/users/components/ApprovedCreatorsPage.tsx` | 1-152 |
| BusinessCard (explore) | `frontend/src/features/explore/components/BusinessCard.tsx` | 1-93 |
| governanceApiClient | `frontend/src/lib/governance-api-client.ts` | 1-65 |

---

## 7. Verification

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

---

## 8. Verification Corrections (2026-04-07)

Issues found during plan review and fixed:

| # | Issue | Fix |
|---|-------|-----|
| 1 | `use-nav-context.ts` doesn't detect `/gconsole` → governance context | Added as pre-requisite in Section 5.1 + step 2E-5. Must fix FIRST. |
| 2 | `use-filtered-nav.ts` returns empty array for governance context (no membership match) | Added as pre-requisite in Section 5.1 + step 2E-5. Governance = show all items. |
| 3 | Plan referenced `list_active()` at line 90, actual is line 119 | Fixed in Section 2A-1. |
| 4 | Approved creators existing endpoint is at `/api/v1/platform/approved-creators/` (not `/users/me/`) | Governance endpoint at `/api/v1/governance/approved-creators/` is correct (new endpoint under governance URL group). |
| 5 | Verification approve/reject uses existing transaction endpoints, not new governance endpoints | Clarified in Section 2E-4. Frontend calls `POST /api/v1/transactions/{id}/accept/` and `/deny/`. |
| 6 | `GovernanceApprovedCreatorsView` queries `User.objects.filter(can_create_business=True)` | Correct — matches existing `ApprovedBusinessCreatorsListView` at `apps/users/views.py:604`. |

All 8 permission codes verified against `apps/rbac/permissions/registry.py`.
All 5 service methods verified with correct signatures.
All frontend component patterns (Can, ConfirmActionDialog, WithPermissions) verified.

---

### Manual E2E:
1. `make dev` (start server + Docker infra)
2. Login as Platform Owner
3. Navigate to `/gconsole` → step-up auth
4. Authenticate → redirected to dashboard
5. Click "Businesses" → list of all businesses with filters
6. Click a business → detail with status, _permissions, action buttons
7. Suspend a business → confirm with reason → status changes to suspended
8. Reactivate → status back to active
9. Navigate to "Approved Creators" → list of approved users
10. Navigate to "Verification" → list of pending verification requests
