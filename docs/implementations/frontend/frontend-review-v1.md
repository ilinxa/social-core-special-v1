# Frontend Application Review v1

**Date:** 2026-03-01
**Version:** 1.0
**Scope:** Full codebase review — architecture, security, quality, testing, bugs
**Stack:** Next.js 16.1.6 + React 19 + Tailwind v4 + shadcn/ui + Zustand + TanStack Query
**Test Results:** 62/62 passed | TypeScript: 0 errors | ESLint: 0 warnings

---

## Health Check

| Check | Result |
|-------|--------|
| Unit tests (62) | All passing |
| TypeScript strict mode | Zero errors |
| ESLint | Zero warnings/errors |
| Build config | `standalone` output, React Compiler enabled |

---

## Architecture Assessment

### Structure

```
frontend/src/
├── app/                          # Next.js 16 App Router
│   ├── (auth)/                   # 7 auth pages (login, register, verify-email, etc.)
│   ├── (app)/                    # Authenticated routes (dashboard placeholder)
│   ├── layout.tsx                # Root layout (Providers wrapper)
│   ├── error.tsx / not-found.tsx # Error boundaries
│   └── Providers.tsx             # QueryClient, ThemeProvider, AuthInitializer, Toaster
├── features/auth/                # Self-contained auth feature module
│   ├── api/auth-api.ts           # 15 API functions
│   ├── hooks/                    # 2 query hooks, 12 mutation hooks
│   ├── components/               # 9 components (forms, session list, OAuth, initializer)
│   └── types.ts                  # Request/response type definitions
├── stores/auth-store.ts          # Zustand store (no persist, devtools)
├── lib/
│   ├── api-client.ts             # Axios + interceptors + token management
│   ├── query-client.ts           # TanStack Query config
│   ├── query-keys.ts             # Hierarchical key factory (8 domains pre-scaffolded)
│   ├── validations/auth.ts       # 7 Zod schemas
│   └── error-reporting.ts        # Sentry placeholder
├── components/
│   ├── ui/                       # 11 shadcn/ui components
│   └── common/                   # FormField, PasswordInput
├── types/index.ts                # Shared API contract types
├── middleware.ts                  # Cookie-based route protection
└── test/                         # Test setup + renderWithProviders utility
```

### What's Done Well

1. **Security-first token handling** — Access tokens in-memory only (never localStorage), refresh via HttpOnly cookies, `has_session` cookie for SSR middleware. Correct approach.

2. **Token refresh queue** (`api-client.ts:106-121`) — Deduplicates concurrent 401 refreshes. Failed requests queue and retry after single refresh call.

3. **Feature-based module structure** — Auth is fully self-contained: `api/`, `hooks/`, `components/`, `types.ts`. Clean separation.

4. **Type safety** — Full TypeScript strict mode, Zod validation matching backend, typed TanStack Query with `queryOptions` factories, `ApiError` class with status getters.

5. **Consistent error handling** — All 7 form components handle: validation (field-level), auth errors (root-level), rate limiting, and specific API error codes. Same pattern throughout.

6. **Accessibility** — `aria-invalid`, `aria-describedby`, `role="alert"`, semantic `<Label htmlFor>`, proper `autoComplete` attributes.

7. **Query key factory** (`query-keys.ts`) — Pre-scaffolded for business, platform, RBAC, transactions, forms, notifications — ready for future features.

8. **Security headers** (`next.config.ts`) — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy.

---

## Bugs Found

### BUG-F01: Double Toast on Mutation Errors

**Severity:** Medium
**Location:** `src/lib/query-client.ts:16-25` + all form components

The global `onError` for mutations calls `toast.error(error.message)` for all non-401 API errors. But every form component also catches errors and calls `setError()`. Result: server errors (e.g., rate limited) show **both** a toast AND a form error message with the same text.

**Fix:** Remove global mutation `onError` toast, or have form components opt out via mutation `meta` flag.

### BUG-F02: Middleware AUTH_ROUTES Matching Too Broad

**Severity:** Low
**Location:** `src/middleware.ts:20`

`pathname.startsWith(route)` means `/login-something` matches `/login`. Line 26-27 uses the correct pattern (`pathname === route || pathname.startsWith(route + "/")`) for PUBLIC_ROUTES but AUTH_ROUTES on line 20 is inconsistent.

**Fix:** Use the same exact-or-prefix pattern for AUTH_ROUTES.

### BUG-F03: `callbackUrl` Set But Never Consumed

**Severity:** Medium
**Location:** `src/middleware.ts:30` + `src/features/auth/hooks/use-auth-mutations.ts:37`

Middleware sets `callbackUrl` search param when redirecting unauthenticated users to login. But `useLogin()` always does `router.push("/dashboard")` — the callback URL is never read or used.

**Fix:** Read `callbackUrl` from search params in `useLogin()` and redirect there on success.

### BUG-F04: Silent Refresh Doesn't Reset Session Cookie

**Severity:** Low
**Location:** `src/features/auth/api/auth-api.ts:61-67`

`loginApi()` and `registerApi()` call `setSessionCookie()`, but `silentRefreshApi()` does not. If `has_session` cookie expires (7-day max-age) while the refresh token is still valid, middleware redirects to login even though the user could still authenticate.

**Fix:** Call `setSessionCookie()` in `silentRefreshApi()` on success.

### BUG-F05: VerifyEmailForm Resend Ignores User-Typed Email

**Severity:** Low
**Location:** `src/features/auth/components/VerifyEmailForm.tsx:42`

`handleResend` uses `emailFromParams` (from URL), not the form field value. If user arrives without `?email=` and types email manually, the resend button does nothing (guard `!emailFromParams` prevents the call).

**Fix:** Use `getValues("email")` from the form instead of `emailFromParams`.

### BUG-F06: "Revoke All Other Sessions" Logs Out Current User Too

**Severity:** Cosmetic
**Location:** `src/features/auth/components/SessionList.tsx:112-118`

Button says "Revoke All Other Sessions" but `logoutAllApi()` calls `POST /auth/logout-all/` which revokes ALL sessions including current, then navigates to `/login`.

**Fix:** Change label to "Sign Out Everywhere" or update backend to only revoke other sessions.

---

## Missing OAuth Callback Route

**Severity:** Medium (blocks OAuth feature)
**Location:** No `/auth/oauth/callback` page exists

`OAuthButtons` redirects to provider's `authorization_url`, but no callback route handles the redirect back. Backend presumably redirects to a frontend URL with tokens, but no page receives them.

**Status:** Expected — OAuth is not yet wired end-to-end.

---

## Test Coverage Analysis

### Covered (7 test files, 62 tests)

| File | Tests | Coverage |
|------|-------|----------|
| `auth-api.test.ts` | 15 | All 15 API functions |
| `LoginForm.test.tsx` | 6 | Fields, validation, errors, mutations |
| `RegisterForm.test.tsx` | 4 | Fields, validation, conflict error |
| `VerifyEmailForm.test.tsx` | 4 | Pre-fill, code validation, mutations |
| `SessionList.test.tsx` | 6 | Loading, render, revoke, empty/error states |
| `auth-store.test.ts` | 7 | State, actions, selectors |
| `validations/auth.test.ts` | 20 | All 7 Zod schemas |

### Missing (by priority)

| Area | Priority | Reason |
|------|----------|--------|
| AuthInitializer | **High** | Critical startup logic — silent refresh + user fetch |
| Middleware | **High** | Route protection — redirect logic, cookie checks |
| api-client interceptors | **High** | Token refresh queue, 401 handling, error conversion |
| ResetPasswordForm | Medium | Token handling from URL params |
| ChangePasswordForm | Medium | Current password error mapping |
| ForgotPasswordForm | Low | Simple form, same pattern as others |
| OAuthButtons | Low | Simple click handlers |
| Error/404 pages | Low | Static UI |
| ResendVerificationPage | Low | Duplicates VerifyEmailForm pattern |

---

## Code Quality Ratings

| Aspect | Rating | Notes |
|--------|--------|-------|
| Consistency | Excellent | Identical patterns across all 7 forms |
| Type safety | Excellent | Strict TS, Zod schemas, typed queries |
| Security | Excellent | In-memory tokens, HttpOnly cookies, security headers |
| State management | Excellent | Zustand client + TanStack Query server, proper selector hooks |
| Accessibility | Good | ARIA attributes, semantic HTML, `role="alert"` |
| Error handling | Good | Comprehensive per-error-code handling (6 bugs found) |
| Testing | Good | 62 tests, but missing critical path coverage |
| Bundle prep | Good | Standalone output, React Compiler |
| Dark mode | Good | next-themes with system detection |
| Loading states | Minimal | Only root `loading.tsx`, no per-route |
| CSP | Missing | Content-Security-Policy header not configured |

---

## Placeholder / Incomplete Areas

1. **App layout** (`src/app/(app)/layout.tsx`) — Sidebar and header are placeholder text
2. **Dashboard** — Single placeholder card
3. **OAuth callbacks** — No callback route to receive tokens
4. **User profile/settings** — Not built
5. **Session management UI** — `SessionList` component exists but isn't mounted in any page
6. **Error reporting** — `reportError()` is a `console.error` stub (Sentry placeholder)

---

## Dependency Versions (as of 2026-03-01)

| Package | Version | Notes |
|---------|---------|-------|
| Next.js | 16.1.6 | App Router, standalone output |
| React | 19.2.3 | With React Compiler |
| TypeScript | 5.x | Strict mode |
| Tailwind CSS | 4 | v4 with @tailwindcss/postcss |
| Zustand | 5.0.11 | With devtools middleware |
| TanStack Query | 5.90.21 | queryOptions pattern |
| react-hook-form | 7.71.2 | With @hookform/resolvers |
| Zod | 4.3.6 | Schema validation |
| Axios | 1.13.5 | With interceptors |
| Vitest | 4.0.18 | happy-dom environment |
| shadcn/ui | Radix 1.4.3 | new-york style, 11 components |
| MSW | 2.12.10 | Installed but not actively used in tests |

---

## Recommended Next Actions (Priority Order)

1. Fix BUG-F01 (double toast) — quick win, improves UX immediately
2. Fix BUG-F03 (callbackUrl) — needed before real users navigate protected routes
3. Fix BUG-F04 (session cookie on silent refresh) — prevents unnecessary logouts
4. Add AuthInitializer + middleware + api-client interceptor tests — highest-value coverage
5. Fix BUG-F02 (middleware matching) — defensive, prevents future bugs
6. Fix BUG-F05 (resend email) — edge case but confusing UX
