# Frontend Foundation Overhaul

**Date:** 2026-03-01
**Status:** Pending Approval
**Scope:** 7 phases, 79 files (53 new + 26 modified), ~67 new tests

## Context

The frontend (Next.js 16 + React 19) has a complete auth system (62 tests passing) but needs architectural work to become a **reusable foundation** matching the backend's quality. A review identified 6 bugs, missing test coverage, and no support for the backend's multi-role user system (business members, platform admins, staff/superusers).

**Goal:** Transform the frontend into a production-grade foundation with: comprehensive auth flow, central API system, solid state management, dynamic route protection, role-based route structure, centralized error handling, and security hardening.

**Backend user model flags:** `is_active`, `is_verified`, `is_complete`, `can_create_business`, `is_staff`, `is_superuser`
**Backend account types:** Business (slug-based, multi-membership) and Platform (singleton)
**Backend membership data:** `GET /api/v1/users/me/memberships/` returns plain array (not paginated) of `{id, account_type, account_id, role, is_owner, status, joined_at, permissions: [{code, scope}]}`

---

## Key Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Business/platform context | URL-based (`/business/{slug}/...`, `/platform/...`) | Explicit, self-documenting URLs. `/business/acme-corp/dashboard` |
| 2 | When to fetch memberships | On auth init (alongside user fetch) | Small payload (<10 items), needed for sidebar navigation, one parallel request |
| 3 | Route access enforcement | Middleware = auth only; Layout guards = membership/permission | Edge middleware can't call backend; layout guards use cached Zustand state |
| 4 | Active context for API calls | Explicit params (pass slug/id to API functions) | No hidden state; URL is source of truth; components extract slug from `useParams` |
| 5 | Permission checking | Client-side for UI, backend for enforcement | `useHasPermission()` checks cached snapshot; backend is always final authority |
| 6 | Global mutation error handling | Remove global `onError` toast entirely | Every mutation explicitly handles its errors; no double-toast; form errors stay inline |
| 7 | Business slug in memberships | Add `account_slug`/`account_name` to backend serializer | Avoids extra API call to resolve slug; membership response includes slug directly |
| 8 | Membership freshness strategy | Event-driven invalidation, not timer-based | Memberships change through discrete events (join, leave, role change), not on a clock. `staleTime: Infinity` + explicit invalidation on events |

---

## Authorization Model: Three-Tier System

> **Core principle:** The backend is the sole security authority. All frontend authorization is a UX optimization — never a security boundary.

Memberships are fetched once on auth init and invalidated by events, not timers. Three tiers of authorization with explicit freshness guarantees:

### Tier 1 — Navigation Hints (cached, can be stale)

**Purpose:** Sidebar links, tab visibility, conditional UI rendering.
**Source:** Zustand membership store (read-only selectors).
**Freshness:** Best-effort from last fetch. Can be stale.
**Performance:** Zero API calls. Instant.
**Acceptable staleness:** Worst case is showing a link that leads to a guard denial or 403 — both handled gracefully.

Examples: `useBusinessMemberships()` → sidebar links, `usePlatformMembership()` → platform tab, `user.is_staff` → admin link.

**Implemented in:** Phase 2.2 (Zustand selectors), Phase 4.4 (app layout sidebar).

### Tier 2 — Route Guards (cached + single retry on miss)

**Purpose:** Deciding whether to render a route or show "Access Denied."
**Source:** Zustand membership store, with one retry-fetch on cache miss.
**Freshness:** Current within the session, self-correcting on miss.
**Performance:** Zero API calls in common case. One API call on cache miss (rare).

Guard flow for `BusinessGuard` and `PlatformGuard`:
1. Check cached memberships for match (slug for business, type for platform)
2. If found with `status === "active"` → allow instantly (zero API calls)
3. If NOT found and memberships are loaded → invalidate memberships query (one fresh fetch)
4. If still not found after fresh fetch → show "Access Denied"

`AdminGuard` is a simple cached check (no retry) because `is_staff`/`is_superuser` come from `/users/me/` (different endpoint), change extremely rarely, and "log out and back in" is acceptable for admin promotions.

**Implemented in:** Phase 4.1 (guard components), Phase 4.6 (guard tests).

### Tier 3 — Action Enforcement (always backend)

**Purpose:** Can this user perform this specific action?
**Source:** Backend API response (200 = allowed, 403 = denied).
**Freshness:** Always current — every action hits the backend.
**Performance:** One API call per action (already required for the mutation itself).

The frontend `useHasPermission()` hook only hides/disables UI elements as a convenience. It never prevents an action. If the cache is stale and a button is visible that shouldn't be, the backend returns 403 and the error handler shows an appropriate message.

**Implemented in:** Phase 2.3 (permission hooks), Phase 3.1 (error handler for 403s).

### Invalidation Events

Without WebSocket/SSE (future work), the frontend detects membership changes through:

| Event | Trigger | Mechanism |
|-------|---------|-----------|
| User logs in | Auth init | `fetchMyMembershipsApi()` in `AuthInitializer` |
| User's own mutation | Join/leave/create business | `queryClient.invalidateQueries({ queryKey: ['memberships'] })` in mutation `onSuccess` |
| Route guard cache miss | Direct link to new business | Guard triggers single refetch before denying |
| User returns to tab | Window/tab focus | TanStack Query `refetchOnWindowFocus: 'always'` |
| External change (admin action) | Not detectable in real-time | Caught by window focus refetch or next guard miss |

> **Future:** WebSocket/SSE push for real-time membership invalidation. Current approach covers all cases with at most one extra API call and a window-focus catch-all for external changes.

---

## Phase 1: Bug Fixes + Backend Serializer Change

**Goal:** Fix all 6 bugs, expose missing user flags from backend. Foundation for everything else.

### 1.1 BUG-F01: Double Toast on Mutation Errors
**File:** `frontend/src/lib/query-client.ts`
**Fix:** Remove `mutations.onError` handler from `createQueryClient()`. Keep only `retry: 0`.

### 1.2 BUG-F02: Middleware AUTH_ROUTES Matching
**File:** `frontend/src/middleware.ts` (line 20)
**Fix:** Change `pathname.startsWith(route)` to `pathname === route || pathname.startsWith(route + "/")` (matches the PUBLIC_ROUTES pattern already on line 26-27).

### 1.3 BUG-F03: callbackUrl Not Consumed
**File:** `frontend/src/features/auth/hooks/use-auth-mutations.ts`
**Fix:** In `useLogin()`, add `useSearchParams()`, read `callbackUrl`, validate it starts with `/` (prevent open redirect), redirect there or fall back to `/dashboard`.

### 1.4 BUG-F04: Silent Refresh Session Cookie
**File:** `frontend/src/features/auth/api/auth-api.ts`
**Fix:** Add `setSessionCookie()` call in `silentRefreshApi()` after successful refresh.

### 1.5 BUG-F05: VerifyEmailForm Resend
**File:** `frontend/src/features/auth/components/VerifyEmailForm.tsx`
**Fix:** Use `getValues("email")` from react-hook-form instead of `emailFromParams` for the resend action.

### 1.6 BUG-F06: Session Button Label
**File:** `frontend/src/features/auth/components/SessionList.tsx`
**Fix:** Change "Revoke All Other Sessions" to "Sign Out Everywhere" (matches actual behavior: revokes ALL sessions including current).

### 1.7 Backend: Expose User Flags
**File:** `backend/apps/users/serializers.py`
**Change:** Add `can_create_business`, `is_staff`, `is_superuser` to `UserOutputSerializer.Meta.fields`.

**File:** `frontend/src/types/index.ts`
**Change:** Add same 3 fields to `User` interface.

**Test updates:** Add the 3 fields to `mockUser` in `auth-api.test.ts` and `auth-store.test.ts`.

### 1.8 Backend: Add Slug/Name to Membership Serializer

> **Rationale:** Phase 2 types and Phase 4 guards both need `account_slug`/`account_name` from memberships. Moving this backend change to Phase 1 ensures the API returns these fields before any frontend code depends on them.

**File:** `backend/apps/rbac/serializers.py`
**Change:** Add `account_name` and `account_slug` as `SerializerMethodField` to `MyMembershipOutputSerializer`:
- `account_slug`: resolves `BusinessAccount.slug` for business memberships, empty string `""` for platform
- `account_name`: resolves `BusinessAccount.legal_name` for business, `"Platform"` for platform
- Add both to `Meta.fields`

**Performance note:** User typically has <10 memberships. Individual lookups acceptable. If needed later, optimize with annotation in view queryset.

**Backend test updates:** Update RBAC membership view tests to verify new fields in response.

### Phase 1 Files (12 files)

| File | Action |
|------|--------|
| `frontend/src/lib/query-client.ts` | Modify — remove global `onError` |
| `frontend/src/middleware.ts` | Modify — fix route matching |
| `frontend/src/features/auth/hooks/use-auth-mutations.ts` | Modify — read callbackUrl |
| `frontend/src/features/auth/api/auth-api.ts` | Modify — add `setSessionCookie()` |
| `frontend/src/features/auth/components/VerifyEmailForm.tsx` | Modify — use form value for resend |
| `frontend/src/features/auth/components/SessionList.tsx` | Modify — fix label |
| `frontend/src/types/index.ts` | Modify — add 3 User fields |
| `backend/apps/users/serializers.py` | Modify — expose 3 fields |
| `backend/apps/rbac/serializers.py` | Modify — add `account_slug`, `account_name` |
| `frontend/src/features/auth/api/auth-api.test.ts` | Modify — update mockUser |
| `frontend/src/stores/auth-store.test.ts` | Modify — update mockUser |
| `backend/apps/rbac/tests/test_views.py` | Modify — verify new membership fields |

### Verification
- `cd frontend && npm run test` — 62 tests pass
- `cd frontend && npm run typecheck` — 0 errors
- Backend: `pytest apps/users/tests/ -v` — all pass
- Backend: `pytest apps/rbac/tests/test_views.py -v` — membership endpoint returns slug/name

---

## Phase 2: Membership Types, Store, and Permission Hooks

**Goal:** Build the type system and state management for memberships and permissions. Pure infrastructure — no UI changes yet.

**Depends on:** Phase 1 (User type must have new flags)

### 2.1 New Types

**Create:** `frontend/src/types/rbac.ts`
```typescript
export type AccountType = "business" | "platform";
export type MembershipStatus = "active" | "suspended" | "left" | "removed" | "banned";

export interface MembershipPermission { code: string; scope: string; }

export interface Role {
  id: string; name: string; account_type: AccountType; account_id: string;
  level: number; is_system_role: boolean; description: string;
  created_at: string; updated_at: string;
}

export interface Membership {
  id: string; account_type: AccountType; account_id: string;
  account_name: string; account_slug: string;  // from Phase 1.8 backend change
  role: Role; is_owner: boolean; status: MembershipStatus;
  joined_at: string; permissions: MembershipPermission[];
}
```

**Create:** `frontend/src/types/organization.ts` — `BusinessAccount`, `BusinessAccountList`, `BusinessProfile`, `PlatformAccount` types matching backend serializers (`BusinessAccountOutput`, `BusinessAccountListOutput`, `BusinessProfileOutput`).

> **Note:** Per ilinxa standards ("No barrel `index.ts` re-exports"), do NOT re-export from `types/index.ts`. Consumers import directly: `import type { Membership } from "@/types/rbac"` and `import type { BusinessAccount } from "@/types/organization"`. Keep `types/index.ts` for its existing types (User, ApiError, etc.).

### 2.2 Membership Store (Zustand)

**Create:** `frontend/src/stores/membership-store.ts`

State: `memberships: Membership[]`, `isLoaded: boolean`
Actions: `setMemberships()`, `clearMemberships()`
Derived: `getBusinessMemberships()`, `getPlatformMembership()`, `getMembershipForAccount(type, id)`
Selector hooks: `useMemberships()`, `useBusinessMemberships()`, `usePlatformMembership()`, `useMembershipsLoaded()`
Non-React: `getMembershipStore()`

Pattern: Follows existing `auth-store.ts` exactly (Zustand + devtools, no persist).

### 2.3 Permission Hooks

**Create:** `frontend/src/hooks/use-has-permission.ts`
- `useHasPermission(code, accountType, accountId)` — checks cached membership permissions
- `useIsMember(accountType, accountId)` — has active membership?
- `useIsOwner(accountType, accountId)` — is owner?

> **Authorization tier:** These are **Tier 1 (Navigation Hints)** and **Tier 3 (Action Enforcement) UI layer** — used to hide/disable UI elements as a convenience. The backend ALWAYS enforces. If the cache is stale and a button is visible that shouldn't be, the backend returns 403 and `handleApiError()` (Phase 3) shows an appropriate message. See "Authorization Model: Three-Tier System" above.

### 2.4 Membership API + Query Hook

**Create:** `frontend/src/features/auth/api/membership-api.ts`
- `fetchMyMembershipsApi()` — calls `apiClient.get<Membership[]>("/users/me/memberships/")` → resolves to `GET /api/v1/users/me/memberships/` (returns plain array, NOT paginated)

**Create:** `frontend/src/features/auth/hooks/use-membership-queries.ts`
- `membershipsQueryOptions()` — event-driven invalidation strategy:
  - `staleTime: Infinity` — never auto-refetch on a timer (memberships change through discrete events, not on a clock)
  - `refetchOnWindowFocus: 'always'` — catch external changes (admin actions on other devices) when user returns to tab
  - `gcTime: 30 * 60 * 1000` (30 min) — keep cached data longer since we control invalidation
- `useMembershipsQuery()` — TanStack Query wrapper (distinct from `useMemberships()` Zustand selector in 2.2)
- Export `invalidateMemberships(queryClient)` — helper that calls `queryClient.invalidateQueries({ queryKey: ['memberships'] })`, used by guards (Phase 4) and future business mutations

> **Why not `staleTime: 10 minutes`?** Timer-based refetching is the wrong model for memberships. A 10-minute timer either refetches uselessly (99.9% of sessions) or misses the moment it matters (user was just added to a business). Event-driven invalidation ensures every refetch has a reason: login, mutation, guard miss, or window focus. See "Authorization Model: Three-Tier System" above.

### 2.5 Update AuthInitializer

> **Mounting location:** `AuthInitializer` is rendered in `Providers.tsx`, which wraps `{children}` in the root `layout.tsx`. This means it runs on **every page** (public, auth, and app routes). When a user navigates client-side from a public page to `/business/acme-corp/dashboard`, the membership store will already be populated from the initial load. No additional mounting is needed.

**Modify:** `frontend/src/features/auth/components/AuthInitializer.tsx`
- After `silentRefreshApi()`, fetch user AND memberships in parallel via `Promise.all`
- Store both in their respective Zustand stores
- On error: clear both stores

### 2.6 Update Login/Logout/OAuth Mutations

> **Cross-phase note:** `use-auth-mutations.ts` was already modified in Phase 1.3 (callbackUrl). This phase builds on that version — adding membership fetch/clear to the same hooks.

**Modify:** `frontend/src/features/auth/hooks/use-auth-mutations.ts`
- `useLogin()` → after success, also fetch memberships and store
- `useRegister()` → set empty memberships (new user has none)
- `useLogout()` / `useLogoutAll()` → also clear membership store + `queryClient.removeQueries({ queryKey: ['memberships'] })`
- `useGoogleOAuth()` / `useAppleOAuth()` → also fetch memberships and store (these log users in too)

> **Invalidation pattern for future mutations:** Any mutation that affects the user's memberships (join business, leave business, create business, accept invitation) should call `invalidateMemberships(queryClient)` from Phase 2.4 in its `onSuccess` callback. This is the "event-driven" part of the invalidation strategy — the frontend knows immediately when the user's own actions change their memberships. See "Authorization Model: Three-Tier System" above.

### 2.7 Tests

**Create:** `frontend/src/stores/membership-store.test.ts` (~8 tests)
**Create:** `frontend/src/hooks/use-has-permission.test.ts` (~6 tests)
**Create:** `frontend/src/features/auth/api/membership-api.test.ts` (~2 tests)

### Phase 2 Files (12 files)

| File | Action |
|------|--------|
| `frontend/src/types/rbac.ts` | Create — AccountType, MembershipStatus, Membership, Role, MembershipPermission |
| `frontend/src/types/organization.ts` | Create — BusinessAccount, BusinessAccountList, BusinessProfile, PlatformAccount |
| `frontend/src/stores/membership-store.ts` | Create — Zustand store + selector hooks |
| `frontend/src/hooks/use-has-permission.ts` | Create — permission/member/owner checks |
| `frontend/src/features/auth/api/membership-api.ts` | Create — fetchMyMembershipsApi() |
| `frontend/src/features/auth/hooks/use-membership-queries.ts` | Create — queryOptions + hook |
| `frontend/src/features/auth/components/AuthInitializer.tsx` | Modify — parallel fetch memberships |
| `frontend/src/features/auth/hooks/use-auth-mutations.ts` | Modify — add membership fetch/clear |
| `frontend/src/stores/membership-store.test.ts` | Create (~8 tests) |
| `frontend/src/hooks/use-has-permission.test.ts` | Create (~6 tests) |
| `frontend/src/features/auth/api/membership-api.test.ts` | Create (~2 tests) |
| `frontend/src/test/utils.tsx` | Modify — add membership provider to renderWithProviders |

### Verification
- `cd frontend && npm run test` — 62 existing + ~16 new tests pass
- `cd frontend && npm run typecheck` — 0 errors

---

## Phase 3: Centralized Error Handling System

**Goal:** Eliminate duplicated error handling patterns across all form components. Establish error boundaries.

**Depends on:** Phase 1 (double-toast fix)

### 3.1 API Error Handler Utility

**Create:** `frontend/src/lib/api-error-handler.ts`

```typescript
handleApiError<T>(error, { setError?, showToast?, handlers? })
```

- Maps `validation_error` details to form fields via `setError`
- Handles rate limiting with retry-after message
- Supports custom handlers per error code (e.g., `invalid_credentials`)
- Falls back to root error or toast
- Non-ApiError: calls `reportError()`

This replaces the ~15-line catch block duplicated across all 7 form components.

### 3.2 Refactor All 7 Existing Form Components

Migrate all form `catch` blocks to use `handleApiError()`:

| Component | Custom handlers needed |
|-----------|----------------------|
| `LoginForm.tsx` | `invalid_credentials`, `account_not_verified`, `account_inactive` |
| `RegisterForm.tsx` | `conflict` (email already registered) |
| `VerifyEmailForm.tsx` | `not_found` (no pending verification) |
| `ForgotPasswordForm.tsx` | (none — just rate limiting) |
| `ResetPasswordForm.tsx` | `not_found` (expired token) |
| `ChangePasswordForm.tsx` | `invalid_credentials`, `business_rule_violation` |
| `resend-verification/page.tsx` | (none — just rate limiting) |

> **Note:** The last entry is a route page (`app/(auth)/resend-verification/page.tsx`), not a reusable form component. It handles its own mutation inline. There is no `ResendVerificationForm.tsx`.

Each refactored form drops ~10-15 lines of duplicated error handling.

### 3.3 Error Boundary Components

**Create:** `frontend/src/components/common/ErrorBoundary.tsx`
- Uses `react-error-boundary` (already installed v6.1.1)
- `FeatureErrorBoundary` — wraps feature sections, shows card with error + retry button
- Calls `reportError()` on error

### 3.4 Upgrade Error Reporting

**Modify:** `frontend/src/lib/error-reporting.ts`
- Add typed `ErrorContext` interface (`boundary?`, `component?`, `action?`)
- Structured logging ready for Sentry integration

### 3.5 Tests

**Create:** `frontend/src/lib/api-error-handler.test.ts` (~6 tests)

### Phase 3 Files (11 files)

| File | Action |
|------|--------|
| `frontend/src/lib/api-error-handler.ts` | Create |
| `frontend/src/components/common/ErrorBoundary.tsx` | Create |
| `frontend/src/lib/error-reporting.ts` | Modify |
| `frontend/src/lib/api-error-handler.test.ts` | Create |
| `frontend/src/features/auth/components/LoginForm.tsx` | Modify — use handleApiError |
| `frontend/src/features/auth/components/RegisterForm.tsx` | Modify — use handleApiError |
| `frontend/src/features/auth/components/VerifyEmailForm.tsx` | Modify — use handleApiError |
| `frontend/src/features/auth/components/ForgotPasswordForm.tsx` | Modify — use handleApiError |
| `frontend/src/features/auth/components/ResetPasswordForm.tsx` | Modify — use handleApiError |
| `frontend/src/features/auth/components/ChangePasswordForm.tsx` | Modify — use handleApiError |
| `frontend/src/app/(auth)/resend-verification/page.tsx` | Modify — use handleApiError |

### Verification
- `cd frontend && npm run test` — all tests pass
- Manual: Verify form error handling still works identically

---

## Phase 4: Route Structure, Guards, and Layouts

**Goal:** Build the complete route tree with role-based access guards. This is the biggest phase.

**Depends on:** Phase 2 (membership store for guards)

### 4.1 Route Guard Components

> **Authorization tier:** All guards implement **Tier 2 (Route Guards)** from the three-tier model. See "Authorization Model: Three-Tier System" above.
>
> **Note:** Backend serializer change for `account_slug`/`account_name` already done in Phase 1.8. Frontend `Membership` type already includes these fields from Phase 2.1.

**Create:** `frontend/src/components/guards/AuthGuard.tsx`
- Checks `isAuthenticated` from auth store
- Shows loading skeleton while `!isInitialized`
- Redirects to `/login` if unauthenticated

**Create:** `frontend/src/components/guards/BusinessGuard.tsx`
- Reads `slug` from `useParams()`
- Checks `membership-store` for active membership matching `account_slug === slug`
- **If no match found and memberships are loaded:** calls `invalidateMemberships(queryClient)` (from Phase 2.4) to trigger a single fresh fetch before denying access. This handles: (a) user was just added to a business (stale cache), (b) direct link to a business the user joined after initial load.
- Shows "Access Denied" only after fresh fetch confirms no membership
- Shows loading while memberships not loaded or revalidating

**Create:** `frontend/src/components/guards/PlatformGuard.tsx`
- Checks for active platform membership in store
- Uses same retry-on-miss pattern as `BusinessGuard` (calls `invalidateMemberships(queryClient)` before denying)
- Shows "Access Denied" if no platform membership after fresh fetch

**Create:** `frontend/src/components/guards/AdminGuard.tsx`
- Checks `user.is_staff || user.is_superuser` from auth store
- Simple cached check, no retry — admin flags come from `/users/me/` and change extremely rarely
- Shows "Access Denied" for non-admin users

### 4.2 Route Tree

```
app/
  (auth)/                          [EXISTS] Login, register, verify, etc.
  (public)/                        [NEW] Landing, marketing
    page.tsx                       Move existing home page here
    layout.tsx                     Clean layout (no sidebar)
  (app)/                           [EXISTS, restructured]
    layout.tsx                     [MODIFY] Real app shell with sidebar
    (user)/                        [NEW] Personal routes
      layout.tsx                   User context layout
      dashboard/page.tsx           Personal dashboard (move existing)
      profile/page.tsx             Profile management
      settings/page.tsx            User settings + notification prefs
      sessions/page.tsx            Mount SessionList + ChangePasswordForm
    business/[slug]/               [NEW] Business-scoped routes
      layout.tsx                   BusinessGuard wrapper
      dashboard/page.tsx           Business dashboard
      members/page.tsx             Member management
      roles/page.tsx               Role management
      settings/page.tsx            Business settings
    platform/                      [NEW] Platform-scoped routes
      layout.tsx                   PlatformGuard wrapper
      dashboard/page.tsx           Platform dashboard
      members/page.tsx             Platform members
      roles/page.tsx               Platform role management
      settings/page.tsx            Platform settings
    admin/                         [NEW] Staff/superuser routes
      layout.tsx                   AdminGuard wrapper
      page.tsx                     Admin dashboard
```

### 4.3 Middleware Update

**Modify:** `frontend/src/middleware.ts`
- Expand `PUBLIC_ROUTES` list
- Keep middleware thin: auth-only redirect (cookie-based)
- All membership/permission checks happen in layout guards (client-side, cached state)

### 4.4 App Layout with Real Navigation

**Modify:** `frontend/src/app/(app)/layout.tsx`
- Sidebar: user's businesses (from `useBusinessMemberships()`), platform link (from `usePlatformMembership()`), admin link (from `user.is_staff`)
- Header: user avatar dropdown (profile, settings, sign out)
- Mobile: responsive sidebar via `Sheet` component
- Uses `AuthGuard` wrapper

### 4.5 Loading Skeletons

**Create:** Per-route `loading.tsx` files:
- `frontend/src/app/(app)/(user)/loading.tsx` — user routes skeleton
- `frontend/src/app/(app)/business/[slug]/loading.tsx` — business routes skeleton
- `frontend/src/app/(app)/platform/loading.tsx` — platform routes skeleton

### 4.6 Guard Tests

> **Rationale:** Guards contain meaningful conditional logic (loading states, redirect, slug matching, revalidation). Testing them immediately catches bugs before Phases 5-7 build on top.

**Create:** `frontend/src/components/guards/AuthGuard.test.tsx` (~4 tests)
- Redirects to `/login` when unauthenticated
- Redirects to `/login?callbackUrl=...` preserving the intended destination
- Shows loading while `!isInitialized`
- Renders children when authenticated and initialized

**Create:** `frontend/src/components/guards/BusinessGuard.test.tsx` (~5 tests)
- Shows loading while memberships not loaded
- Renders children when user has active membership matching slug
- Triggers revalidation when slug not in cached memberships
- Shows "Access Denied" after revalidation confirms no membership
- Handles edge case: membership exists but status is not "active"

**Create:** `frontend/src/components/guards/PlatformGuard.test.tsx` (~4 tests)
- Shows loading while memberships not loaded
- Renders children when platform membership exists
- Triggers revalidation when no platform membership in cache
- Shows "Access Denied" after revalidation confirms no membership

**Create:** `frontend/src/components/guards/AdminGuard.test.tsx` (~3 tests)
- Shows "Access Denied" for non-staff, non-superuser
- Renders children when `is_staff` or `is_superuser`

### Phase 4 Files (32 files)

| File | Action |
|------|--------|
| `frontend/src/components/guards/AuthGuard.tsx` | Create |
| `frontend/src/components/guards/BusinessGuard.tsx` | Create |
| `frontend/src/components/guards/PlatformGuard.tsx` | Create |
| `frontend/src/components/guards/AdminGuard.tsx` | Create |
| `frontend/src/components/guards/AuthGuard.test.tsx` | Create (~4 tests) |
| `frontend/src/components/guards/BusinessGuard.test.tsx` | Create (~5 tests) |
| `frontend/src/components/guards/PlatformGuard.test.tsx` | Create (~4 tests) |
| `frontend/src/components/guards/AdminGuard.test.tsx` | Create (~3 tests) |
| `frontend/src/middleware.ts` | Modify — expand PUBLIC_ROUTES |
| `frontend/src/app/(app)/layout.tsx` | Modify — real app shell with sidebar |
| `frontend/src/app/(public)/layout.tsx` | Create — clean layout (no sidebar) |
| `frontend/src/app/(public)/page.tsx` | Move from app/page.tsx |
| `frontend/src/app/(app)/(user)/layout.tsx` | Create — AuthGuard wrapper |
| `frontend/src/app/(app)/(user)/dashboard/page.tsx` | Create (move existing) |
| `frontend/src/app/(app)/(user)/profile/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/(user)/settings/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/(user)/sessions/page.tsx` | Create — mounts SessionList + ChangePasswordForm |
| `frontend/src/app/(app)/business/[slug]/layout.tsx` | Create — BusinessGuard |
| `frontend/src/app/(app)/business/[slug]/dashboard/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/business/[slug]/members/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/business/[slug]/roles/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/business/[slug]/settings/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/platform/layout.tsx` | Create — PlatformGuard |
| `frontend/src/app/(app)/platform/dashboard/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/platform/members/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/platform/roles/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/platform/settings/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/admin/layout.tsx` | Create — AdminGuard |
| `frontend/src/app/(app)/admin/page.tsx` | Create placeholder |
| `frontend/src/app/(app)/(user)/loading.tsx` | Create — user routes skeleton |
| `frontend/src/app/(app)/business/[slug]/loading.tsx` | Create — business routes skeleton |
| `frontend/src/app/(app)/platform/loading.tsx` | Create — platform routes skeleton |

### Verification
- `cd frontend && npm run test` — guard tests pass (~16 new tests)
- `cd frontend && npm run typecheck` — 0 errors
- `cd frontend && npm run build` — verify route generation
- Manual: test route guards with different user types
- Backend: `pytest apps/rbac/tests/test_views.py -v` — memberships endpoint still works

---

## Phase 5: API Module System

**Goal:** Create typed API modules per backend domain. Prepare feature module structure for future development.

**Depends on:** Phase 2 (types only — API wrapper functions are standalone and don't require route pages to exist)

### 5.1 Feature Module Structure

```
features/
  auth/          [EXISTS] — no changes
  users/         [NEW]
    api/users-api.ts        — profile CRUD, avatar upload
    hooks/use-user-queries.ts
  business/      [NEW]
    api/business-api.ts     — fetch/update business, list my businesses
    hooks/use-business-queries.ts
  platform/      [NEW]
    api/platform-api.ts     — fetch/update platform account
    hooks/use-platform-queries.ts
```

Each module is a thin typed wrapper around `apiClient` calls. Functions are added as features are built — we only scaffold the structure and add the API functions needed by Phase 4 routes.

### 5.2 Request Cancellation

> **Note:** TanStack Query natively passes `signal` to `queryFn`, so query cancellation on route change works automatically. No custom `createAbortSignal()` utility needed — all data-fetching goes through TanStack Query hooks. Imperative `apiClient` calls (e.g., in mutation `onSuccess` callbacks) are short-lived and don't need cancellation.

### Phase 5 Files (6 files)

| File | Action |
|------|--------|
| `frontend/src/features/users/api/users-api.ts` | Create |
| `frontend/src/features/users/hooks/use-user-queries.ts` | Create |
| `frontend/src/features/business/api/business-api.ts` | Create |
| `frontend/src/features/business/hooks/use-business-queries.ts` | Create |
| `frontend/src/features/platform/api/platform-api.ts` | Create |
| `frontend/src/features/platform/hooks/use-platform-queries.ts` | Create |

---

## Phase 6: Security Hardening

**Goal:** Add CSP header, audit PII exposure.

**Depends on:** Phase 1

### 6.1 Content-Security-Policy

**Development:** `frontend/next.config.ts` — Add CSP header with permissive dev directives:
- `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (Next.js dev HMR requires both)
- `style-src 'self' 'unsafe-inline'` (Tailwind injects styles)

**Production:** Nonce-based CSP via middleware (Next.js App Router built-in support):
- `script-src 'self' 'nonce-{random}'` — per-request nonce eliminates need for `unsafe-inline`/`unsafe-eval`
- `style-src 'self' 'unsafe-inline'` (Tailwind CSS injection still requires this)
- `default-src 'self'`
- `img-src 'self' data: blob: https:`
- `font-src 'self' https://fonts.gstatic.com`
- `connect-src 'self' ${API_URL}` (dynamic based on env)
- `frame-ancestors 'none'`

**Implementation steps for nonce-based CSP:**
1. Generate nonce per request in middleware (`crypto.randomUUID()`)
2. Set CSP header with nonce value in middleware response
3. Pass nonce to layout via `headers()` server function
4. Next.js automatically applies nonce to its `<script>` tags when CSP header contains a nonce

### 6.2 PII Audit
All query keys verified clean: `["users", "me"]`, `["business", "detail", slug]` — no PII.
No localStorage/sessionStorage usage found — Zustand stores are in-memory only (no `persist`). Clean.

### Phase 6 Files (1 file)

| File | Action |
|------|--------|
| `frontend/next.config.ts` | Modify — add CSP |

---

## Phase 7: Critical Missing Tests

**Goal:** Add tests for the 3 highest-priority untested areas plus 2 missing component tests.

**Depends on:** Phases 1-2 (bug fixes + AuthInitializer changes)

### 7.1 AuthInitializer Tests

**Create:** `frontend/src/features/auth/components/AuthInitializer.test.tsx` (~6 tests)
- Calls silentRefresh → fetchUser + fetchMemberships in parallel
- On success: sets user and memberships in stores
- On failure: clears both stores
- Always calls `setInitialized()`
- Double-mount protection (StrictMode)

### 7.2 Middleware Tests

**Create:** `frontend/src/middleware.test.ts` (~6 tests)
- Unauthenticated on protected route → redirects to `/login?callbackUrl=...`
- Authenticated on auth route → redirects to `/dashboard`
- Authenticated on `/login-callback` → does NOT redirect (BUG-F02 fix verification)
- Public routes pass through
- Auth routes with trailing paths work correctly

### 7.3 API Client Interceptor Tests

**Create:** `frontend/src/lib/api-client.test.ts` (~8 tests)
- Request interceptor: attaches Bearer token when present, omits when absent
- Response interceptor: converts errors to ApiError
- 401 token_expired → refresh + retry
- 401 token_already_used → clear + redirect
- Concurrent 401s queue → single refresh
- Network error handling

### 7.4 Missing Component Tests

**Create:** `frontend/src/features/auth/components/ResetPasswordForm.test.tsx` (~5 tests)
**Create:** `frontend/src/features/auth/components/ChangePasswordForm.test.tsx` (~4 tests)

### Phase 7 Files (5 files, ~29 tests)

> **Note:** Guard tests (~15) were moved to Phase 4.6 so they're verified before dependent phases. Phase 7 covers infrastructure and remaining component tests only.

| File | Action |
|------|--------|
| `frontend/src/features/auth/components/AuthInitializer.test.tsx` | Create (~6 tests) |
| `frontend/src/middleware.test.ts` | Create (~6 tests) |
| `frontend/src/lib/api-client.test.ts` | Create (~8 tests) |
| `frontend/src/features/auth/components/ResetPasswordForm.test.tsx` | Create (~5 tests) |
| `frontend/src/features/auth/components/ChangePasswordForm.test.tsx` | Create (~4 tests) |

### Verification
- `cd frontend && npm run test` — target: 62 existing + ~67 new = ~129+ tests, all passing
- `cd frontend && npm run typecheck` — 0 errors
- `cd frontend && npm run lint` — 0 warnings

---

## Backend Changes Summary

Only 2 backend files modified (both backward-compatible additions, both in Phase 1):

| File | Change | Phase |
|------|--------|-------|
| `backend/apps/users/serializers.py` | Add `can_create_business`, `is_staff`, `is_superuser` to `UserOutputSerializer` | 1.7 |
| `backend/apps/rbac/serializers.py` | Add `account_name`, `account_slug` to `MyMembershipOutputSerializer` via `SerializerMethodField` | 1.8 |

**Exact backend API URLs consumed by frontend:**
- `POST /api/v1/auth/login/` → `{user, tokens, is_new_user}`
- `POST /api/v1/auth/register/` → `{user, tokens, is_new_user}`
- `POST /api/v1/auth/refresh/` → `{access_token, access_expires_in, ...}`
- `GET /api/v1/users/me/` → `UserOutputSerializer`
- `GET /api/v1/users/me/memberships/` → `MyMembershipOutputSerializer[]` (plain array, NOT paginated)
- `GET /api/v1/business/my/` → `BusinessAccountListOutput[]` (user's businesses)
- `GET /api/v1/business/<slug>/` → `BusinessAccountOutput`

---

## Total File Count

| Phase | New | Modified | Tests Added |
|-------|-----|----------|-------------|
| 1. Bug Fixes + Backend | 0 | 12 | 0 (update existing mocks + backend tests) |
| 2. Types/Stores | 9 | 3 | ~16 |
| 3. Error Handling | 3 | 8 | ~6 |
| 4. Routes/Guards/Layouts | 30 | 2 | ~16 (guard tests) |
| 5. API Modules | 6 | 0 | 0 (added per-feature later) |
| 6. Security | 0 | 1 | 0 |
| 7. Tests | 5 | 0 | ~29 |
| **Total** | **53** | **26** | **~67** |

> **Counting convention:** "New" = all files created (source + test). "Modified" = existing files changed. "Tests Added" = number of test cases (not files).

**Target test count:** 62 existing + ~67 new = **~129 tests**

---

## Reusable Patterns Established

After implementation, these patterns are available for any new feature:

1. **Feature module** → `features/{name}/api/`, `hooks/`, `components/`, `types.ts`
2. **Typed API function** → wrap `apiClient.get/post/patch/delete` with input/output types
3. **TanStack Query hook** → `queryOptions()` factory + `useQuery()` wrapper
4. **Zustand store** → state + actions, devtools middleware, selector hooks
5. **Route guard** → layout-level check against cached membership/user state (Tier 2)
6. **Error handling** → `handleApiError()` for forms, `{ showToast: true }` for non-form mutations
7. **Permission check** → `useHasPermission(code, accountType, accountId)` for UI gating (Tier 1/3)
8. **Error boundary** → `<FeatureErrorBoundary>` wrapping feature sections
9. **Three-tier authorization** → Tier 1 (cached navigation), Tier 2 (guard + retry), Tier 3 (backend enforces)
10. **Event-driven invalidation** → `invalidateMemberships(queryClient)` in mutation `onSuccess` + `refetchOnWindowFocus: 'always'`

---

## Implementation Order

```
Phase 1 (Bug fixes + BOTH backend serializer changes)  ← foundation, no dependencies
  ↓
Phase 2 (Types + stores + hooks)                        ← depends on Phase 1 (User type + membership fields)
  ↓
Phase 3 (Error handling system)                         ← depends on Phase 1 toast fix
  ↓
Phase 4 (Routes + guards + layouts)                     ← depends on Phase 2 membership store
  ↓
Phase 5 (API modules)                                   ← depends on Phase 2 types only
  ↓
Phase 6 (Security)                                      ← independent, can run after Phase 1
  ↓
Phase 7 (Tests)                                         ← depends on Phases 1-2 changes
```

Phases 3, 5, and 6 are independent of each other and can be parallelized after Phase 2 completes.

---

## Deep Review Verification Log

**Cross-referenced against backend on 2026-03-01:**

| Check | Status | Detail |
|-------|--------|--------|
| UserOutputSerializer fields | VERIFIED | `id, email, username, is_active, is_verified, is_complete, date_joined, last_login, profile` — missing 3 flags confirmed |
| MyMembershipOutputSerializer fields | VERIFIED | `id, account_type, account_id, role, is_owner, status, joined_at, permissions` — no slug/name confirmed |
| RoleOutputSerializer fields | MATCH | `id, name, account_type, account_id, level, is_system_role, description, created_at, updated_at` |
| MembershipStatus enum | FIXED | Added missing `"left"` status (5 total: active, suspended, left, removed, banned) |
| AccountType enum | MATCH | `"platform" \| "business"` |
| Permission format | MATCH | `{code: string, scope: string}` |
| Membership endpoint URL | VERIFIED | `GET /api/v1/users/me/memberships/` (mounted in users app, not rbac) |
| Response format | VERIFIED | Plain array, NOT paginated (`return Response(serializer.data)`) |
| BusinessAccount serializer | VERIFIED | `BusinessAccountOutput` has id, slug, legal_name, + 16 more fields |
| Business URL pattern | VERIFIED | `<slug:slug>/` and `<slug:business_slug>/` for RBAC sub-routes |
| Backend RBAC URL structure | VERIFIED | `/api/v1/business/<slug>/members/`, `/api/v1/platform/members/` |
| Platform role endpoints | VERIFIED | `/api/v1/platform/roles/` — full CRUD parallel to business roles (PlatformRoleListView, PlatformRoleDetailView, PlatformRolePermissionView) |
| AuthInitializer mount point | VERIFIED | Mounted in `Providers.tsx` → root `layout.tsx`, runs on ALL pages including public |

**Cross-referenced against ilinxa-frontend-standards:**

| Standard | Compliance | Notes |
|----------|------------|-------|
| No barrel re-exports | FIXED | Removed `types/index.ts` re-export plan; direct imports from `@/types/rbac` |
| Named exports only | COMPLIANT | All components use named exports; page.tsx uses default (Next.js requirement) |
| Zustand: selector hooks | COMPLIANT | Follows existing auth-store pattern |
| Zustand: devtools | COMPLIANT | No persist (correct — in-memory only) |
| TanStack Query: queryOptions factory | COMPLIANT | All query hooks use queryOptions() pattern |
| State separation | COMPLIANT | Zustand = client state, TanStack Query = server state |
| Feature module structure | COMPLIANT | `features/{name}/api/`, `hooks/`, `components/` |
| Error boundaries | COMPLIANT | react-error-boundary v6.1.1 (already installed) |
| Testing: happy-dom | COMPLIANT | All new tests use happy-dom (NOT jsdom) |
| `interface` for objects, `type` for unions | COMPLIANT | Membership/Role = interface, AccountType/MembershipStatus = type |
| No `any` | COMPLIANT | Plan uses typed generics throughout |
| Route groups | COMPLIANT | `(auth)`, `(public)`, `(app)` grouping |
| Page.tsx < 30 lines | COMPLIANT | All new pages are thin wrappers |
| Middleware: thin, auth-only | COMPLIANT | Cookie check only; guards in layouts |
