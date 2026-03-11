# Frontend Improvement Report — 2026-03-03

**Based on**: `docs/front_report_03032026.md` (12-phase frontend consistency review)
**Scope**: 8 findings (1 HIGH, 4 MEDIUM, 3 LOW) — all resolved
**Result**: 69 test files, 539 tests passing (was 62 files / 487 tests)

---

## Changes Summary

| Finding | Severity | Status | Files Changed |
|---------|----------|--------|---------------|
| H1: Platform profile redirect | HIGH | Fixed | `next.config.ts`, `middleware.ts` |
| M1: AdminGuard a11y | MEDIUM | Fixed | `AdminGuard.tsx` |
| M2: FeatureErrorBoundary unused | MEDIUM | Fixed | 4 page files |
| M3: Silent mutation failures | MEDIUM | Fixed | `use-auth-mutations.ts` |
| M4: Cross-feature imports | MEDIUM | Fixed | 2 new files, 7 import updates |
| L1: Missing success toasts | LOW | Fixed | `use-user-mutations.ts` |
| L2: 7 untested hooks | LOW | Fixed | 7 new test files (+52 tests) |
| L3: Unused query key domains | LOW | No action | Intentionally forward-looking |

---

## Detailed Changes

### H1: Public Platform Profile Unreachable (HIGH)

**Problem**: `/platform/profile` was intercepted by a blanket `/platform/:path+` → `/pconsole/:path+` redirect in `next.config.ts`, AND was missing from `PUBLIC_ROUTES` in middleware.

**Fix**:
- `next.config.ts`: Changed redirect source from `/platform/:path+` to `/platform/:path((?!profile).+)` — negative lookahead excludes the `profile` path from the redirect pattern.
- `middleware.ts`: Added `/platform/profile` to the `PUBLIC_ROUTES` array so unauthenticated users can access the public platform profile page.

**Files**:
- `frontend/next.config.ts`
- `frontend/src/middleware.ts`

---

### M1: AdminGuard Missing Accessibility Attributes (MEDIUM)

**Problem**: AdminGuard's loading skeleton was missing `role="status"` and `aria-label="Loading"` — inconsistent with the other 3 guards.

**Fix**: Added both attributes to match AuthGuard, BusinessGuard, and PlatformGuard.

**Files**: `frontend/src/components/guards/AdminGuard.tsx`

---

### M2: FeatureErrorBoundary Never Used in Production (MEDIUM)

**Problem**: `FeatureErrorBoundary` was fully implemented and tested (9 test cases) but not used in any production page. Feature component errors would crash the entire app.

**Fix**: Wrapped 4 key pages with `<FeatureErrorBoundary>`:
- `bconsole/[slug]/profile/page.tsx` — business console profile
- `pconsole/profile/page.tsx` — platform console profile
- `explore/page.tsx` — inside existing `<Suspense>` wrapper
- `sessions/page.tsx` — each card section wrapped separately for granular error isolation (SessionList + ChangePasswordForm independent)

**Files**:
- `frontend/src/app/(app)/bconsole/[slug]/profile/page.tsx`
- `frontend/src/app/(app)/pconsole/profile/page.tsx`
- `frontend/src/app/(public)/explore/page.tsx`
- `frontend/src/app/(app)/(user)/sessions/page.tsx`

---

### M3: Non-Form Mutations Have No Error Feedback (MEDIUM)

**Problem**: 5 mutations used fire-and-forget `.mutate()` with no `onError` — users got no feedback on failure.

**Fix**: Added `onError` callbacks with contextual `toast.error()` messages to all 5 mutations:
- `useLogoutAll`: "Failed to log out all sessions. Please try again."
- `useResendVerification`: "Failed to resend verification email. Please try again."
- `useRevokeSession`: "Failed to revoke session. Please try again."
- `useGoogleOAuth`: "Failed to connect with Google. Please try again."
- `useAppleOAuth`: "Failed to connect with Apple. Please try again."

**Files**: `frontend/src/features/auth/hooks/use-auth-mutations.ts`

---

### M4: Cross-Feature Import Coupling (MEDIUM)

**Problem**: `features/users/` and `features/business/` imported from `features/explore/` (country data + city hook), breaking feature isolation.

**Fix**: Moved shared utilities to proper shared locations and updated all imports:
- `features/explore/components/country-data.ts` → `lib/country-data.ts` (pure data)
- `features/explore/hooks/use-city-data.ts` → `hooks/use-city-data.ts` (shared hook)
- Original files now re-export from new locations (backwards-compatible for explore-internal usage)
- Updated 5 component imports + 2 test mock paths to use new locations directly

**New files**:
- `frontend/src/lib/country-data.ts`
- `frontend/src/hooks/use-city-data.ts`

**Updated imports in**:
- `features/users/components/EditProfileForm.tsx`
- `features/users/components/ProfileView.tsx`
- `features/users/components/UserPublicProfilePage.tsx`
- `features/business/components/BusinessProfileView.tsx`
- `features/business/components/BusinessProfileEditForm.tsx`
- `features/users/components/EditProfileForm.test.tsx` (mock path)
- `features/business/components/BusinessProfileEditForm.test.tsx` (mock path)

---

### L1: Missing Success Toasts (LOW)

**Problem**: `useUpdateUsername` and `useUpdateProfile` had no `toast.success()` in `onSuccess`, inconsistent with avatar mutations in the same file.

**Fix**: Added toast.success calls:
- `useUpdateUsername.onSuccess`: `toast.success("Username updated")`
- `useUpdateProfile.onSuccess`: `toast.success("Profile updated")`

**Files**: `frontend/src/features/users/hooks/use-user-mutations.ts`

---

### L2: 7 Untested Hooks (LOW)

**Problem**: 7 hook modules had no dedicated test files (some coverage via component tests).

**Fix**: Created 7 new test files with 52 total tests:

| Test File | Tests | What's Covered |
|-----------|-------|----------------|
| `use-auth-queries.test.ts` | 1 | sessionsQueryOptions (query key) |
| `use-membership-queries.test.ts` | 5 | membershipsQueryOptions (key, staleTime, gcTime, refetchOnWindowFocus), invalidateMemberships |
| `use-user-queries.test.ts` | 5 | currentUserQueryOptions (key, staleTime, retry), profileQueryOptions (key, staleTime) |
| `use-user-mutations.test.tsx` | 17 | All 4 mutations: API calls, store updates, query cache, toasts, fallback invalidation |
| `use-explore-queries.test.ts` | 12 | 3 queryOptions factories: keys, staleTime, enabled logic |
| `use-username-check.test.tsx` | 5 | Debounce, isCurrent detection, format validation, API available/unavailable |
| `use-city-data.test.tsx` | 7 | Data fetching, useCountryOptions sorting, useCitiesForCountry lookup |

**Testing patterns used**:
- Simple query hooks: test `queryOptions()` factories for correct query keys and config
- Mutation hooks: `renderHook` + `waitFor` with mocked APIs, verify `onSuccess` side effects
- Debounced hook: `vi.useFakeTimers()` + `act(() => vi.advanceTimersByTime())`, restore real timers before `waitFor` for TQ-dependent assertions
- TQ v5 mutation context: use `mock.calls[0][0]` to assert first arg only (TQ passes additional context as 2nd arg)

---

### L3: Unused Query Key Domains (LOW)

**Status**: No action taken — these are intentionally pre-defined for planned features (RBAC, transactions, forms, notifications).

---

## Test Coverage Delta

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Test files | 62 | 69 | +7 |
| Total tests | 487 | 539 | +52 |
| Hook test coverage | 5/12 hooks | 12/12 hooks | 100% |

All 539 tests pass with 0 failures.
