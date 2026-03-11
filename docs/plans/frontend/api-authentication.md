# Frontend API & Authentication System — Implementation Plan

**Created:** 2026-02-24
**Status:** Implemented (see `docs/implementations/frontend/api-authentication.md`)

---

## Context

Phase 0 (project scaffolding) is complete. The frontend has a working Next.js 16 + React 19 + Tailwind v4 + shadcn/ui setup with all tooling configured. The backend Django REST API has a comprehensive auth system with 15+ endpoints covering login, registration, token refresh, email verification, password management, session management, and OAuth.

**This plan implements the complete frontend auth system** — the reusable API layer, auth state management, route protection, form components, and all auth pages. Every type, endpoint, and error code is aligned with the actual backend contracts.

**What already exists (mostly complete):**
- `src/lib/api-client.ts` — Axios + JWT interceptors + token refresh queue (needs session cookie helpers)
- `src/lib/query-client.ts` — QueryClient factory (complete)
- `src/lib/query-keys.ts` — Query key factory (complete)
- `src/types/index.ts` — User, AuthTokens, AuthResponse, ApiErrorResponse, PaginatedResponse (needs 2 missing error codes)
- `src/app/Providers.tsx` — QueryClient + Theme + Toaster (needs AuthInitializer addition)
- 11 shadcn/ui components installed
- Vitest + RTL test infrastructure

---

## Phase 1: Foundation — Types, Schemas, Store

### Step 1.0: Fix `src/types/index.ts` — Add missing error codes

The `ApiErrorCode` union type is missing two backend error codes. Add:
- `"missing_token"` — returned when refresh token is absent (400)
- `"oauth_error"` — returned on OAuth provider failures (400)

### Step 1.1: Fix `src/features/auth/types.ts`

**Changes:**
- Fix `old_password` → `current_password` in `PasswordChangeData` (backend uses `current_password`)
- Remove duplicate `AuthResponse` (already exists in `@/types/index.ts`, import from there)
- Add missing interfaces:

```typescript
// New interfaces to add:
export interface ResendVerificationData { email: string }
export interface MessageResponse { message: string }
export interface VerifyEmailResponse { message: string; user_id: string }
export interface LogoutAllResponse { message: string; sessions_revoked: number }
export interface TokenRefreshResponse {
  access_token: string;
  access_expires_in: number;
  refresh_expires_in: number;
  token_type: "Bearer";
}
export interface OAuthInitResponse { authorization_url: string }
export interface DeviceSession {
  id: string;
  device_id: string;
  device_name: string;
  device_type: "web" | "ios" | "android" | "desktop" | "unknown";
  ip_address: string | null;
  location: string;
  last_activity: string;
  is_active: boolean;
  is_current: boolean;
  created_at: string;
}
```

### Step 1.2: Create `src/lib/validations/auth.ts`

Zod schemas matching backend validation constraints. Types derived via `z.infer<>`.

| Schema | Fields | Rules |
|--------|--------|-------|
| `loginSchema` | email, password | email valid, password required |
| `registerSchema` | email, password, referred_by? | email valid, password ≥8 chars + not all numeric |
| `verifyEmailSchema` | email, code | email valid, code exactly 6 digits |
| `resendVerificationSchema` | email | email valid |
| `passwordResetSchema` | email | email valid |
| `passwordResetConfirmSchema` | token, new_password | token UUID, password ≥8 + not all numeric |
| `passwordChangeSchema` | current_password, new_password | both required, new ≥8 + not all numeric |

### Step 1.3: Create `src/stores/auth-store.ts`

Zustand store — NO `persist` middleware (access tokens are in-memory, refresh tokens are HttpOnly cookies).

```
State: { user: User | null, isAuthenticated: boolean, isInitialized: boolean }
Actions: { setUser, clearUser, setInitialized }
```

Export selector hooks per standards: `useUser()`, `useIsAuthenticated()`, `useIsInitialized()`.
Export `getAuthStore()` for non-React contexts (API layer).

---

## Phase 2: API Functions

### Step 2.1: Create `src/features/auth/api/auth-api.ts`

Pure async functions (no React hooks). Each calls `apiClient` and returns typed data.

| Function | Method | Endpoint | Token Side-Effect |
|----------|--------|----------|-------------------|
| `loginApi` | POST | `/auth/login/` | `setAccessToken` + set `has_session` cookie |
| `registerApi` | POST | `/auth/register/` | `setAccessToken` + set `has_session` cookie |
| `silentRefreshApi` | POST | `/auth/refresh/` | `setAccessToken` |
| `logoutApi` | POST | `/auth/logout/` | `clearTokens` + clear `has_session` cookie |
| `logoutAllApi` | POST | `/auth/logout-all/` | `clearTokens` + clear `has_session` cookie |
| `verifyEmailApi` | POST | `/auth/verify-email/` | — |
| `resendVerificationApi` | POST | `/auth/resend-verification/` | — |
| `passwordResetApi` | POST | `/auth/password/reset/` | — |
| `passwordResetConfirmApi` | POST | `/auth/password/reset/confirm/` | — |
| `passwordChangeApi` | POST | `/auth/password/change/` | — |
| `fetchSessionsApi` | GET | `/auth/sessions/` | — |
| `revokeSessionApi` | DELETE | `/auth/sessions/:id/` | — |
| `fetchCurrentUserApi` | GET | `/users/me/` | — |
| `googleOAuthInitApi` | GET | `/auth/oauth/google/` | — |
| `appleOAuthInitApi` | GET | `/auth/oauth/apple/` | — |

All functions inject `device_type: "web"` where applicable. Login/register set a lightweight `has_session=1` cookie (non-HttpOnly, `SameSite=Strict`, `max-age=604800`) for middleware route protection.

### Step 2.2: Modify `src/lib/api-client.ts`

Add `has_session` cookie clearing in two places:
1. **Refresh failure handler** (line ~162-170): clear `has_session` cookie before redirect
2. **`token_already_used` handler** (line ~177-182): clear `has_session` cookie before redirect

Also add a helper function `clearSessionCookie()` and `setSessionCookie()` to centralize cookie logic.

---

## Phase 3: TanStack Query Hooks

### Step 3.1: Create `src/features/auth/hooks/use-auth-queries.ts`

| Hook | Query Key | API Function | Options |
|------|-----------|-------------|---------|
| `useCurrentUser()` | `queryKeys.users.me()` | `fetchCurrentUserApi` | `retry: false` (don't retry 401s) |
| `useSessions()` | `queryKeys.auth.sessions()` | `fetchSessionsApi` | default |

Also exports `currentUserQueryOptions()` and `sessionsQueryOptions()` for prefetching.

### Step 3.2: Create `src/features/auth/hooks/use-auth-mutations.ts`

| Hook | API Function | onSuccess Behavior |
|------|-------------|-------------------|
| `useLogin()` | `loginApi` | `setUser`, set query cache, push `/dashboard` |
| `useRegister()` | `registerApi` | `setUser`, set query cache, push `/verify-email` |
| `useLogout()` | `logoutApi` | `clearUser`, clear query cache, push `/login` |
| `useLogoutAll()` | `logoutAllApi` | `clearUser`, clear query cache, toast, push `/login` |
| `useVerifyEmail()` | `verifyEmailApi` | toast success |
| `useResendVerification()` | `resendVerificationApi` | toast success |
| `usePasswordReset()` | `passwordResetApi` | toast success |
| `usePasswordResetConfirm()` | `passwordResetConfirmApi` | toast, push `/login` |
| `usePasswordChange()` | `passwordChangeApi` | toast success |
| `useRevokeSession()` | `revokeSessionApi` | toast, invalidate sessions query |
| `useGoogleOAuth()` | `googleOAuthInitApi` | `window.location.href = authorization_url` |
| `useAppleOAuth()` | `appleOAuthInitApi` | `window.location.href = authorization_url` |

Error handling is **per-form** (via `mutateAsync` + `try/catch` + `setError()`), not global. The global `onError` in query-client.ts shows toasts for non-auth mutations and suppresses 401s.

---

## Phase 4: Auth Initialization

### Step 4.1: Create `src/features/auth/components/AuthInitializer.tsx`

`"use client"` component that runs once on mount:
1. Attempt `silentRefreshApi()` (cookie auto-sent)
2. If success → `fetchCurrentUserApi()` → `setUser()`
3. If failure → `clearUser()` (no valid session)
4. Always → `setInitialized()` at the end

Uses `useRef` to prevent double-run in React StrictMode.

### Step 4.2: Modify `src/app/Providers.tsx`

Wrap children with `<AuthInitializer>` inside `QueryClientProvider`:
```
QueryClientProvider > ThemeProvider > AuthInitializer > {children} + Toaster
```

---

## Phase 5: Route Protection Middleware

### Step 5.1: Create `src/middleware.ts`

**Design rationale:** Access tokens are in-memory (not accessible at edge). Refresh tokens are HttpOnly cookies scoped to `/api/v1/auth/refresh/` (not readable by middleware). Solution: a lightweight `has_session=1` cookie set on login/register, cleared on logout/auth failure. This is a **UX optimization** (fast redirects), not a security boundary — real auth happens via access tokens on API calls.

**Logic:**
- Auth routes (`/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/verify-success`, `/resend-verification`): if `has_session=1` → redirect to `/dashboard`
- Protected routes (everything else except `/` and static): if no `has_session` → redirect to `/login?callbackUrl={pathname}`
- Matcher excludes: `_next/static`, `_next/image`, `favicon.ico`, `api`

---

## Phase 6: Form Components

### Step 6.1: Create `src/components/common/FormField.tsx`

Reusable `Label + Input + error message` wrapper. Props: `label`, `error` (FieldError), `description?`. Handles `aria-invalid` and `aria-describedby` for accessibility.

### Step 6.2: Create `src/components/common/PasswordInput.tsx`

Password input with eye/eye-off visibility toggle button (lucide-react icons). Wraps shadcn `Input` with `type` toggling.

### Step 6.3: Create `src/features/auth/components/LoginForm.tsx`

- `react-hook-form` + `zodResolver(loginSchema)`
- Fields: email, password
- Forgot password link
- Error handling: `invalid_credentials` → root error, `account_not_verified` → root error with link, `account_inactive` → root error, rate limited → retry message, validation → field-level via `setError()`
- `OAuthButtons` below form
- Sign up link at bottom

### Step 6.4: Create `src/features/auth/components/RegisterForm.tsx`

- `react-hook-form` + `zodResolver(registerSchema)`
- Fields: email, password
- Error handling: 409 conflict → "email already registered", validation → field-level
- `OAuthButtons` below form
- Sign in link at bottom

### Step 6.5: Create `src/features/auth/components/OAuthButtons.tsx`

Two buttons (Google, Apple) with separator "or" divider. Each calls `useGoogleOAuth()`/`useAppleOAuth()` with redirect path.

### Step 6.6: Create `src/features/auth/components/VerifyEmailForm.tsx`

- 6-digit code input field
- Email field (pre-filled from search params or entered)
- "Resend code" button with cooldown timer (60s)
- On success: redirect to `/login` or `/dashboard`

### Step 6.7: Create `src/features/auth/components/ForgotPasswordForm.tsx`

- Email-only form
- Shows generic success message (does not reveal if email exists — matches backend)

### Step 6.8: Create `src/features/auth/components/ResetPasswordForm.tsx`

- New password field
- Token from URL search params
- On success: toast + redirect to `/login`

### Step 6.9: Create `src/features/auth/components/ChangePasswordForm.tsx`

- Current password + new password fields
- Error: 400 with `invalid_credentials` or `business_rule_violation` code → mapped to `current_password` field error

### Step 6.10: Create `src/features/auth/components/SessionList.tsx`

- Uses `useSessions()` query
- Lists sessions: device name, type icon, IP, location, last activity, "current" badge
- Revoke button per session (disabled for current session)
- "Revoke all" button using `useLogoutAll()`
- Loading skeleton + empty state

---

## Phase 7: Route Pages

Thin server components that import feature components. Follow the existing pattern in login/register pages.

| Page File | Component Imported | Metadata Title |
|-----------|-------------------|----------------|
| `src/app/(auth)/login/page.tsx` (MODIFY) | `LoginForm` | "Sign In" |
| `src/app/(auth)/register/page.tsx` (MODIFY) | `RegisterForm` | "Create Account" |
| `src/app/(auth)/verify-email/page.tsx` (NEW) | `VerifyEmailForm` | "Verify Email" |
| `src/app/(auth)/verify-success/page.tsx` (NEW) | Static content | "Email Verified" |
| `src/app/(auth)/forgot-password/page.tsx` (NEW) | `ForgotPasswordForm` | "Forgot Password" |
| `src/app/(auth)/reset-password/page.tsx` (NEW) | `ResetPasswordForm` | "Reset Password" |
| `src/app/(auth)/resend-verification/page.tsx` (NEW) | Email input + resend button | "Resend Verification" |

---

## Phase 8: Tests

Co-located with source per standards. Uses `renderWithProviders`, `userEvent`, mock hooks.

| Test File | What It Tests |
|-----------|--------------|
| `src/stores/auth-store.test.ts` | Store actions, selector hooks, initial state |
| `src/lib/validations/auth.test.ts` | All schemas with valid/invalid data |
| `src/features/auth/api/auth-api.test.ts` | API functions call correct endpoints, token management |
| `src/features/auth/components/LoginForm.test.tsx` | Form rendering, validation, submission, error display |
| `src/features/auth/components/RegisterForm.test.tsx` | Same pattern, conflict handling |
| `src/features/auth/components/VerifyEmailForm.test.tsx` | Code input, resend cooldown |
| `src/features/auth/components/SessionList.test.tsx` | Session list rendering, revoke action |

---

## File Inventory

### New Files (~28)

| # | File | Purpose |
|---|------|---------|
| 1 | `src/lib/validations/auth.ts` | Zod schemas for all auth forms |
| 2 | `src/stores/auth-store.ts` | Zustand auth state |
| 3 | `src/features/auth/api/auth-api.ts` | All auth HTTP functions |
| 4 | `src/features/auth/hooks/use-auth-queries.ts` | TanStack Query options + hooks |
| 5 | `src/features/auth/hooks/use-auth-mutations.ts` | TanStack Query mutation hooks |
| 6 | `src/features/auth/components/AuthInitializer.tsx` | Silent refresh bootstrap |
| 7 | `src/features/auth/components/LoginForm.tsx` | Login form |
| 8 | `src/features/auth/components/RegisterForm.tsx` | Register form |
| 9 | `src/features/auth/components/OAuthButtons.tsx` | Google + Apple OAuth buttons |
| 10 | `src/features/auth/components/VerifyEmailForm.tsx` | Email verification form |
| 11 | `src/features/auth/components/ForgotPasswordForm.tsx` | Password reset request form |
| 12 | `src/features/auth/components/ResetPasswordForm.tsx` | Password reset confirm form |
| 13 | `src/features/auth/components/ChangePasswordForm.tsx` | Change password form |
| 14 | `src/features/auth/components/SessionList.tsx` | Active sessions list |
| 15 | `src/components/common/FormField.tsx` | Reusable form field wrapper |
| 16 | `src/components/common/PasswordInput.tsx` | Password with visibility toggle |
| 17 | `src/middleware.ts` | Edge-level route protection |
| 18 | `src/app/(auth)/verify-email/page.tsx` | Verify email page |
| 19 | `src/app/(auth)/verify-success/page.tsx` | Magic link success page |
| 20 | `src/app/(auth)/forgot-password/page.tsx` | Forgot password page |
| 21 | `src/app/(auth)/reset-password/page.tsx` | Reset password page |
| 22 | `src/app/(auth)/resend-verification/page.tsx` | Resend verification page |
| 23 | `src/stores/auth-store.test.ts` | Store tests |
| 24 | `src/lib/validations/auth.test.ts` | Schema tests |
| 25 | `src/features/auth/api/auth-api.test.ts` | API function tests |
| 26 | `src/features/auth/components/LoginForm.test.tsx` | LoginForm tests |
| 27 | `src/features/auth/components/RegisterForm.test.tsx` | RegisterForm tests |
| 28 | `src/features/auth/components/VerifyEmailForm.test.tsx` | VerifyEmailForm tests |

### Modified Files (6)

| # | File | Change |
|---|------|--------|
| 1 | `src/types/index.ts` | Add `missing_token` and `oauth_error` to `ApiErrorCode` union |
| 2 | `src/features/auth/types.ts` | Fix `old_password`→`current_password`, remove duplicate `AuthResponse`, add 7 new interfaces |
| 3 | `src/lib/api-client.ts` | Add `setSessionCookie()`/`clearSessionCookie()` helpers, call them in refresh-failure and token_already_used handlers |
| 4 | `src/app/Providers.tsx` | Add `AuthInitializer` wrapper around children |
| 5 | `src/app/(auth)/login/page.tsx` | Replace placeholder with `LoginForm` import |
| 6 | `src/app/(auth)/register/page.tsx` | Replace placeholder with `RegisterForm` import |

---

## Implementation Order (Dependency Chain)

```
Phase 1 (Foundation) ← no dependencies
  ├── 1.1 Fix auth types
  ├── 1.2 Create Zod schemas
  └── 1.3 Create Zustand store

Phase 2 (API) ← depends on Phase 1
  ├── 2.1 Auth API functions
  └── 2.2 Modify api-client.ts (session cookie helpers)

Phase 3 (Hooks) ← depends on Phase 2
  ├── 3.1 Query options/hooks
  └── 3.2 Mutation hooks

Phase 4 (Bootstrap) ← depends on Phase 2-3
  ├── 4.1 AuthInitializer component
  └── 4.2 Modify Providers.tsx

Phase 5 (Middleware) ← depends on Phase 2 (session cookie)
  └── 5.1 Create middleware.ts

Phase 6 (Components) ← depends on Phase 1-3
  ├── 6.1 FormField helper
  ├── 6.2 PasswordInput
  ├── 6.3 LoginForm
  ├── 6.4 RegisterForm
  ├── 6.5 OAuthButtons
  ├── 6.6 VerifyEmailForm
  ├── 6.7 ForgotPasswordForm
  ├── 6.8 ResetPasswordForm
  ├── 6.9 ChangePasswordForm
  └── 6.10 SessionList

Phase 7 (Pages) ← depends on Phase 6
  ├── 7.1-7.2 Modify login/register pages
  └── 7.3-7.7 Create new auth pages

Phase 8 (Tests) ← depends on all above
  └── 8.1-8.7 Test files
```

---

## Key Architectural Decisions

1. **No `persist` in Zustand** — Access tokens stay in-memory (security). Auth state bootstrapped fresh via `AuthInitializer` on every page load (silent refresh + fetch user).

2. **`has_session` cookie for middleware** — Since in-memory tokens and path-scoped HttpOnly cookies aren't readable at the edge, a lightweight flag cookie enables fast route redirects. Not a security boundary — real auth is via API.

3. **Form error handling is per-form, not global** — Auth forms use `mutateAsync` + `try/catch` + `setError()` for fine-grained error mapping (invalid_credentials, rate_limited, account_not_verified, field validation). The global `onError` handles toasts for other mutations.

4. **OAuth: initiation only** — We redirect to the provider. The backend handles the callback and redirects back to the frontend. Callback page handling is a separate feature.

5. **Zod is client-side approximation** — Backend has validators Zod can't replicate (common password list, similarity check). Server errors are caught and displayed via `setError()`.

---

## Backend Contract Cross-Check (Verified)

Every endpoint, field name, and error code in this plan was verified against the actual backend source:

| Contract Item | Backend Source | Plan Status |
|---------------|--------------|-------------|
| Error wrapper `{ error: { message, code, details } }` | `apps/core/exceptions.py` | Matched |
| `current_password` (not `old_password`) | `apps/auth/serializers.py` PasswordChangeSerializer | Fixed |
| Refresh returns flat tokens (no `user`) | `apps/auth/views.py` TokenRefreshView | `TokenRefreshResponse` type |
| Login/Register returns `{ user, tokens, is_new_user }` | `apps/auth/serializers.py` AuthResponseSerializer | `AuthResponse` type |
| Sessions endpoint returns array (not paginated) | `apps/auth/views.py` SessionListView | `DeviceSession[]` |
| `POST /auth/resend-verification/` exists | `apps/auth/urls.py` | Included |
| Apple callback is POST (form_post) | `apps/auth/views.py` AppleOAuthCallbackView | Noted (OAuth initiation only in scope) |
| Cookie: `refresh_token`, HttpOnly, path=`/api/v1/auth/refresh/`, SameSite=Strict | `apps/auth/services.py` | Not readable by middleware (has_session strategy) |
| Token rotation: single-use, reuse → revoke all | `apps/auth/services.py` | `token_already_used` handler in api-client.ts |
| Max 5 sessions per user, oldest revoked | `apps/auth/services.py` | Transparent to frontend |
| Error codes: 16 existing + `missing_token`, `oauth_error` | `apps/core/exceptions.py` + `apps/auth/views.py` | Adding 2 missing codes |
| Password change wrong password → 400 (not 403) | `apps/auth/views.py` PasswordChangeView | Fixed |
| Rate limits: login 5/min, reset 3/hr, verification 3/hr | `apps/auth/throttles.py` | Handled in form error display |

---

## Verification

After implementation:
1. `npm run build` — Next.js production build succeeds (no type errors)
2. `npm run lint` — ESLint passes with zero errors
3. `npm run typecheck` — TypeScript strict compilation passes
4. `npm run test` — All tests pass
5. `npm run dev` → navigate to `/login`, `/register`, `/forgot-password`, `/verify-email` — all pages render
6. Middleware: unauthenticated → `/dashboard` redirects to `/login`; set `has_session=1` cookie manually → `/login` redirects to `/dashboard`
