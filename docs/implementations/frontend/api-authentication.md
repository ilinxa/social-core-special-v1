# API & Authentication System — Implementation Reference

**Version:** v1
**Last Updated:** 2026-02-24
**Status:** Implemented

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  EDGE (middleware.ts)                                           │
│  has_session cookie → redirect auth/protected routes            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  PROVIDERS (Providers.tsx)                                      │
│  QueryClientProvider > ThemeProvider > AuthInitializer > App    │
│                                       │                        │
│  AuthInitializer: silentRefresh → fetchUser → setUser (once)   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  PAGES (app/(auth)/*.tsx)      Thin wrappers importing forms   │
│  /login → LoginForm           /register → RegisterForm         │
│  /verify-email → VerifyEmail  /forgot-password → ForgotPW      │
│  /reset-password → ResetPW    /resend-verification → ResendPW  │
│  /verify-success → Static     /dashboard → (protected)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  FORM COMPONENTS (features/auth/components/*.tsx)               │
│  react-hook-form + zodResolver → mutateAsync + try/catch       │
│                                                                 │
│  LoginForm   RegisterForm   VerifyEmailForm   ForgotPasswordForm│
│  ResetPasswordForm   ChangePasswordForm   SessionList           │
│  OAuthButtons   FormField   PasswordInput                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  HOOKS (features/auth/hooks/)                                   │
│  Queries:  useCurrentUser  useSessions                          │
│  Mutations: useLogin  useRegister  useLogout  useLogoutAll      │
│    useVerifyEmail  useResendVerification  usePasswordReset      │
│    usePasswordResetConfirm  usePasswordChange  useRevokeSession │
│    useGoogleOAuth  useAppleOAuth                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  API LAYER (features/auth/api/auth-api.ts)                     │
│  15 pure async functions → apiClient (Axios)                   │
│  Token side-effects: setAccessToken / clearTokens              │
│  Cookie side-effects: setSessionCookie / clearSessionCookie    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  API CLIENT (lib/api-client.ts)                                │
│  Axios instance + JWT interceptor + refresh queue              │
│  Access token: in-memory variable (never localStorage)         │
│  Refresh token: HttpOnly cookie (browser-managed, path-scoped) │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                        Backend API (/api/v1/)
```

### State Management

```
┌─────────────────────────┐     ┌──────────────────────────────┐
│  Zustand (auth-store)   │     │  TanStack Query (server)     │
│  user: User | null      │◄───►│  queryKeys.users.me()        │
│  isAuthenticated: bool  │     │  queryKeys.auth.sessions()   │
│  isInitialized: bool    │     └──────────────────────────────┘
└─────────────────────────┘
  No persist — bootstrapped
  fresh on every page load
  via AuthInitializer
```

---

## 2. Core Concepts & Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Token storage | Access: in-memory variable; Refresh: HttpOnly cookie | Security — tokens never in localStorage/sessionStorage. XSS can't steal them. |
| Zustand persistence | No `persist` middleware | Refresh tokens are HttpOnly cookies, access tokens are in-memory. State is bootstrapped fresh via AuthInitializer on every load. |
| Middleware auth signal | `has_session=1` non-HttpOnly cookie | Access tokens and path-scoped HttpOnly cookies aren't readable at the edge. Cookie is UX optimization for fast redirects, not a security boundary. |
| Form error handling | Per-form via `mutateAsync` + `try/catch` + `setError()` | Auth forms need fine-grained error mapping (invalid_credentials, rate_limited, account_not_verified). Global `onError` handles toasts for non-auth mutations. |
| Client validation | Zod schemas (client-side approximation) | Backend has validators Zod can't replicate (common password list, similarity check). Server errors caught and displayed via `setError()`. |
| OAuth scope | Initiation only (redirect to provider) | Backend handles OAuth callbacks and redirects back. Callback page handling is a separate feature. |
| Test environment | `happy-dom` (not jsdom) | jsdom 27 has ESM compatibility issues with `@csstools/css-calc` that break Vitest worker startup. happy-dom is faster and avoids this. |

---

## 3. Data Layer

### 3.1 API Functions

Location: `src/features/auth/api/auth-api.ts`

| Function | Method | Endpoint | Token Side-Effect |
|----------|--------|----------|-------------------|
| `loginApi` | POST | `/auth/login/` | `setAccessToken` + `setSessionCookie` |
| `registerApi` | POST | `/auth/register/` | `setAccessToken` + `setSessionCookie` |
| `silentRefreshApi` | POST | `/auth/refresh/` | `setAccessToken` |
| `logoutApi` | POST | `/auth/logout/` | `clearTokens` + `clearSessionCookie` |
| `logoutAllApi` | POST | `/auth/logout-all/` | `clearTokens` + `clearSessionCookie` |
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

All authenticating functions inject `device_type: "web"`. Login/register set `has_session=1` cookie (non-HttpOnly, `SameSite=Strict`, `max-age=604800` — 7 days matching refresh token lifetime).

### 3.2 Session Cookie Helpers

Location: `src/features/auth/api/auth-api.ts` (exported) + `src/lib/api-client.ts` (private copy)

```typescript
// Set on login/register success
setSessionCookie(): "has_session=1; path=/; SameSite=Strict; max-age=604800"

// Clear on logout, auth failure, token reuse detection
clearSessionCookie(): "has_session=; path=/; SameSite=Strict; max-age=0"
```

The `api-client.ts` also calls `clearSessionCookie()` in two failure handlers:
- Refresh failure (401 on `/auth/refresh/`) → clear cookie before redirect
- Token reuse detection (`token_already_used` error code) → clear cookie before redirect

### 3.3 Query Keys

```typescript
auth: {
  all: ["auth"],
  sessions: () => ["auth", "sessions"],
}
users: {
  all: ["users"],
  me: () => ["users", "me"],
}
```

---

## 4. Types & Interfaces

### Global Types (`src/types/index.ts`)

```typescript
type ApiErrorCode =
  | "bad_request" | "validation_error" | "business_rule_violation"
  | "domain_error" | "authentication_error" | "invalid_credentials"
  | "token_expired" | "token_invalid" | "token_already_used"
  | "account_not_verified" | "account_inactive" | "permission_denied"
  | "not_found" | "conflict" | "missing_token" | "oauth_error"
  | "rate_limit_exceeded" | "service_unavailable";

interface AuthResponse { user: User; tokens: AuthTokens; is_new_user?: boolean }
interface AuthTokens { access_token: string; access_expires_in: number; refresh_expires_in: number; token_type: "Bearer" }
```

### Auth Feature Types (`src/features/auth/types.ts`)

**Request types:**

| Interface | Fields |
|-----------|--------|
| `LoginCredentials` | email, password, device_id?, device_type?, device_name? |
| `RegisterData` | extends LoginCredentials + referred_by? |
| `VerifyEmailData` | email, code |
| `ResendVerificationData` | email |
| `PasswordResetData` | email |
| `PasswordResetConfirmData` | token, new_password |
| `PasswordChangeData` | current_password, new_password |

**Response types:**

| Interface | Fields |
|-----------|--------|
| `MessageResponse` | message |
| `VerifyEmailResponse` | message, user_id |
| `LogoutAllResponse` | message, sessions_revoked |
| `TokenRefreshResponse` | access_token, access_expires_in, refresh_expires_in, token_type |
| `OAuthInitResponse` | authorization_url |

**Session type:**

| Interface | Fields |
|-----------|--------|
| `DeviceSession` | id, device_id, device_name, device_type (enum), ip_address, location, last_activity, is_active, is_current, created_at |

### Validation Schemas (`src/lib/validations/auth.ts`)

| Schema | Fields | Rules |
|--------|--------|-------|
| `loginSchema` | email, password | email valid, password required |
| `registerSchema` | email, password, referred_by? | email valid, password >= 8 chars + not all numeric |
| `verifyEmailSchema` | email, code | email valid, code exactly 6 digits |
| `resendVerificationSchema` | email | email valid |
| `passwordResetSchema` | email | email valid |
| `passwordResetConfirmSchema` | token, new_password | token UUID, password >= 8 + not all numeric |
| `passwordChangeSchema` | current_password, new_password | both required, new >= 8 + not all numeric |

Each schema exports `z.infer<>` types (e.g., `LoginFormValues`, `RegisterFormValues`).

---

## 5. Hooks

### Query Hooks (`src/features/auth/hooks/use-auth-queries.ts`)

| Hook | Query Key | API Function | Options |
|------|-----------|-------------|---------|
| `useCurrentUser()` | `queryKeys.users.me()` | `fetchCurrentUserApi` | `staleTime: 5min`, `retry: false` |
| `useSessions()` | `queryKeys.auth.sessions()` | `fetchSessionsApi` | default |

Also exports `currentUserQueryOptions()` and `sessionsQueryOptions()` factory functions for prefetching.

### Mutation Hooks (`src/features/auth/hooks/use-auth-mutations.ts`)

| Hook | API Function | onSuccess Behavior |
|------|-------------|-------------------|
| `useLogin()` | `loginApi` | `setUser`, set query cache, push `/dashboard` |
| `useRegister()` | `registerApi` | `setUser`, set query cache, push `/verify-email` |
| `useLogout()` | `logoutApi` | `clearUser`, `queryClient.clear()`, push `/login` |
| `useLogoutAll()` | `logoutAllApi` | toast, `clearUser`, `queryClient.clear()`, push `/login` |
| `useVerifyEmail()` | `verifyEmailApi` | toast success |
| `useResendVerification()` | `resendVerificationApi` | toast success |
| `usePasswordReset()` | `passwordResetApi` | toast success |
| `usePasswordResetConfirm()` | `passwordResetConfirmApi` | toast, push `/login` |
| `usePasswordChange()` | `passwordChangeApi` | toast success |
| `useRevokeSession()` | `revokeSessionApi` | toast, invalidate sessions query |
| `useGoogleOAuth()` | `googleOAuthInitApi` | `window.location.href = authorization_url` |
| `useAppleOAuth()` | `appleOAuthInitApi` | `window.location.href = authorization_url` |

`useLogout()` has both `onSuccess` and `onError` handlers — on error, it still clears state and redirects (best-effort logout).

### Invalidation Hierarchy

```
useLogin/useRegister  → sets queryKeys.users.me() directly (setQueryData)
useLogout/useLogoutAll → queryClient.clear() (everything)
useRevokeSession      → invalidates queryKeys.auth.sessions()
```

---

## 6. Components

### Common Components

Location: `src/components/common/`

| Component | Purpose |
|-----------|---------|
| `FormField` | Reusable `Label + Input + error + description` wrapper. `forwardRef` for react-hook-form. Handles `aria-invalid` and `aria-describedby`. |
| `PasswordInput` | Password input with eye/eye-off visibility toggle (lucide-react). `forwardRef` for react-hook-form. |

### Auth Components

Location: `src/features/auth/components/`

| Component | Purpose |
|-----------|---------|
| `AuthInitializer` | Silent refresh bootstrap on mount. `useRef` prevents double-run in StrictMode. Wraps children in Providers.tsx. |
| `LoginForm` | Email + password form. Handles: `invalid_credentials`, `account_not_verified`, `account_inactive`, rate limiting, server validation errors. Includes forgot password link, OAuthButtons, sign up link. |
| `RegisterForm` | Email + password + optional referral. Handles: 409 conflict (email already registered), validation errors. Password description hint. OAuthButtons + sign in link. |
| `OAuthButtons` | Google + Apple OAuth buttons with SVG brand icons and "or" separator divider. |
| `VerifyEmailForm` | 6-digit code input. Email pre-filled from `?email=` search param. Resend button with 60-second cooldown timer. |
| `ForgotPasswordForm` | Email-only form. Shows generic success message after submission (doesn't reveal if email exists). |
| `ResetPasswordForm` | Token from `?token=` search param. Shows "Invalid reset link" if no token. New password field with PasswordInput. |
| `ChangePasswordForm` | Current password + new password. Maps `invalid_credentials` / `business_rule_violation` errors to `current_password` field. |
| `SessionList` | Device icons per type (Monitor/Smartphone/HelpCircle). Shows device name, IP, location, relative time. "Current" badge. Revoke button per non-current session. "Revoke All Other Sessions" button. Loading skeleton, error state, empty state. |

### Error Handling Pattern (all auth forms)

```typescript
// All auth forms follow the same pattern:
const { setError } = useForm({ resolver: zodResolver(schema) });
const mutation = useMutation();

async function onSubmit(values) {
  try {
    await mutation.mutateAsync(values);
  } catch (error) {
    if (error instanceof ApiError) {
      // Map error.code → setError("root", { message }) or setError("field", { message })
      if (error.code === "invalid_credentials") setError("root", { message: "..." });
      else if (error.isRateLimited) setError("root", { message: `... ${error.retryAfter}s` });
      else if (error.isValidation && error.details) {
        // Field-level server validation errors
        for (const [field, messages] of Object.entries(error.details)) {
          setError(field, { message: messages[0] });
        }
      }
    }
  }
}
```

---

## 7. Pages & Routes

| Route | Type | Component | Metadata Title |
|-------|------|-----------|----------------|
| `/login` | Client | `LoginForm` | Sign In |
| `/register` | Client | `RegisterForm` | Create Account |
| `/verify-email` | Client | `VerifyEmailForm` | Verify Email |
| `/verify-success` | Static | Success content + Sign In button | Email Verified |
| `/forgot-password` | Client | `ForgotPasswordForm` | Forgot Password |
| `/reset-password` | Client | `ResetPasswordForm` | Reset Password |
| `/resend-verification` | Client | Inline form (uses `resendVerificationSchema`) | Resend Verification |

All auth pages live under `app/(auth)/` layout group which provides a centered card layout.

---

## 8. Key Flows

### Flow 1: Login

1. User submits email + password in `LoginForm`
2. `useLogin.mutateAsync()` calls `loginApi()` → POST `/auth/login/`
3. `loginApi` stores access token in-memory, sets `has_session=1` cookie
4. Backend returns `{ user, tokens }` + sets `refresh_token` HttpOnly cookie
5. `useLogin.onSuccess` → `setUser(data.user)`, sets query cache, pushes `/dashboard`
6. Middleware sees `has_session=1` → allows access to protected routes

### Flow 2: Silent Refresh (App Bootstrap)

1. `AuthInitializer` runs once on mount (guarded by `useRef`)
2. Calls `silentRefreshApi()` → POST `/auth/refresh/` (browser sends HttpOnly cookie)
3. If success → `setAccessToken(new_token)`, then `fetchCurrentUserApi()` → `setUser()`
4. If failure → `clearUser()` (no valid session, user lands on public routes)
5. `setInitialized()` always called in `finally` block

### Flow 3: Token Refresh (Request Interceptor)

1. API request gets 401 response
2. Interceptor checks if refresh is already in progress → if yes, queues the request
3. Calls `POST /auth/refresh/` with HttpOnly cookie
4. If success → updates in-memory token, replays queued requests
5. If failure → clears tokens, clears `has_session` cookie, redirects to `/login`
6. If `token_already_used` → same as failure (token reuse detection = compromise)

### Flow 4: Email Verification

1. After registration, user redirected to `/verify-email?email=...`
2. `VerifyEmailForm` pre-fills email from search params
3. User enters 6-digit code → `useVerifyEmail.mutateAsync()` → POST `/auth/verify-email/`
4. On success → toast, redirect to `/login` or `/dashboard`
5. "Resend code" button with 60-second cooldown → `useResendVerification`

### Flow 5: Password Reset

1. User clicks "Forgot password?" on login form → `/forgot-password`
2. Submits email → `usePasswordReset` → POST `/auth/password/reset/`
3. Shows generic success message (doesn't reveal if email exists)
4. User clicks link in email → `/reset-password?token=UUID`
5. Submits new password → `usePasswordResetConfirm` → POST `/auth/password/reset/confirm/`
6. On success → toast + redirect to `/login`

### Flow 6: Session Management

1. User navigates to settings (future page) showing `SessionList`
2. `useSessions()` fetches active sessions → GET `/auth/sessions/`
3. Lists sessions with device icons, IP, location, "Current" badge
4. "Revoke" button per non-current session → `useRevokeSession` → DELETE `/auth/sessions/:id/`
5. "Revoke All Other Sessions" → `useLogoutAll` → POST `/auth/logout-all/` (also logs out current user)

### Flow 7: OAuth Initiation

1. User clicks Google/Apple button in `OAuthButtons`
2. `useGoogleOAuth.mutate()` → GET `/auth/oauth/google/?device_type=web`
3. Backend returns `{ authorization_url }`
4. `onSuccess` → `window.location.href = authorization_url` (full page redirect)
5. Provider handles auth → redirects to backend callback → backend redirects to frontend (separate feature)

---

## 9. Route Protection

### Middleware (`src/middleware.ts`)

| Path Pattern | No Session | Has Session | Notes |
|-------------|------------|-------------|-------|
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/verify-success`, `/resend-verification` | Allow | Redirect → `/dashboard` | Authenticated users skip auth pages |
| `/` | Allow | Allow | Landing page is always public |
| `/dashboard`, `/settings/*`, all other routes | Redirect → `/login?callbackUrl={path}` | Allow | Protected routes require session |
| `_next/*`, `favicon.ico`, `api/*` | Skip | Skip | Excluded by matcher |

**Matcher:** `["/((?!_next/static|_next/image|favicon.ico|api).*)"]`

**Important:** The `has_session` cookie is a UX optimization, not a security boundary. Real authentication happens via access tokens on API calls. If the cookie exists but the session is expired, the user sees the protected page shell momentarily, then AuthInitializer fails the silent refresh and clears state.

---

## 10. Auth State Store

Location: `src/stores/auth-store.ts`

```typescript
// State (NO persist — bootstrapped fresh each load)
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
}

// Actions
setUser(user: User)      → { user, isAuthenticated: true }
clearUser()              → { user: null, isAuthenticated: false }
setInitialized()         → { isInitialized: true }

// Selector hooks (export these, not raw store)
useUser()              → User | null
useIsAuthenticated()   → boolean
useIsInitialized()     → boolean

// Non-React access (for API layer)
getAuthStore()         → AuthState & AuthActions
```

---

## 11. Configuration & Gotchas

### Gotchas

- **jsdom 27 + Vitest incompatibility:** `jsdom@27` → `@asamuzakjp/css-color` → `@csstools/css-calc` (ESM-only) breaks Vitest worker startup with `ERR_REQUIRE_ESM`. Use `happy-dom` instead in `vitest.config.ts`.
- **RegisterForm naming conflict:** `useForm`'s `register` function conflicts with `useRegister` mutation hook. Alias as `registerField` in the component.
- **Form description + validation error text overlap:** If both a field description and its validation error match the same text (e.g., "at least 8 characters"), tests need specific regex to avoid `getByText` ambiguity. Use `getByText(/password must be at least 8 characters/i)` instead of `/at least 8 characters/i`.
- **Zod ≠ backend validation:** Zod can approximate password rules (min 8, not all numeric) but can't replicate Django's common-password-list or similarity checks. Always handle server validation errors via `setError()`.
- **`current_password` not `old_password`:** Backend uses `current_password` field name for password change. Verified against `apps/auth/serializers.py` `PasswordChangeSerializer`.
- **Password change returns 400 (not 403):** Wrong current password returns status 400 with code `invalid_credentials` or `business_rule_violation`, not 403.
- **Next.js 16 middleware deprecation:** `middleware.ts` file convention shows deprecation warning ("use proxy instead") but still works.
- **Session cookie `SameSite=Strict`:** The `has_session` cookie uses `SameSite=Strict` to prevent CSRF, same as the refresh token cookie.

### Backend Contract Cross-Check

| Contract Item | Backend Source | Frontend Status |
|---------------|--------------|-----------------|
| Error wrapper `{ error: { message, code, details } }` | `apps/core/exceptions.py` | Matched — `ApiError` class unpacks this |
| `current_password` (not `old_password`) | `apps/auth/serializers.py` | Fixed |
| Refresh returns flat tokens (no `user`) | `apps/auth/views.py` | `TokenRefreshResponse` type |
| Login/Register returns `{ user, tokens, is_new_user }` | `apps/auth/serializers.py` | `AuthResponse` type |
| Sessions endpoint returns array (not paginated) | `apps/auth/views.py` | `DeviceSession[]` |
| Cookie: `refresh_token`, HttpOnly, path=`/api/v1/auth/refresh/` | `apps/auth/services.py` | Not readable by middleware (has_session strategy) |
| Token rotation: single-use, reuse → revoke all | `apps/auth/services.py` | `token_already_used` handler in api-client.ts |
| Max 5 sessions per user, oldest revoked | `apps/auth/services.py` | Transparent to frontend |
| 18 error codes (16 existing + `missing_token` + `oauth_error`) | `apps/core/exceptions.py` + `apps/auth/views.py` | All in `ApiErrorCode` union |
| Rate limits: login 5/min, reset 3/hr, verification 3/hr | `apps/auth/throttles.py` | Handled via `error.isRateLimited` + `error.retryAfter` |

---

## 12. Testing

### Test Infrastructure

| Item | Config |
|------|--------|
| Framework | Vitest 4.0.18 |
| Environment | `happy-dom` |
| Setup | `src/test/setup.ts` (`@testing-library/jest-dom/vitest` + cleanup) |
| Utils | `src/test/utils.tsx` → `renderWithProviders()` (QueryClient wrapper) |
| Mocking | `vi.mock()` for hooks/modules, `vi.fn()` for function mocks |

### Test Results

| Module | File | Tests | Status |
|--------|------|-------|--------|
| Auth store | `src/stores/auth-store.test.ts` | 7 | Pass |
| Validation schemas | `src/lib/validations/auth.test.ts` | 20 | Pass |
| API functions | `src/features/auth/api/auth-api.test.ts` | 15 | Pass |
| LoginForm | `src/features/auth/components/LoginForm.test.tsx` | 6 | Pass |
| RegisterForm | `src/features/auth/components/RegisterForm.test.tsx` | 4 | Pass |
| VerifyEmailForm | `src/features/auth/components/VerifyEmailForm.test.tsx` | 4 | Pass |
| SessionList | `src/features/auth/components/SessionList.test.tsx` | 6 | Pass |
| **Total** | **7 files** | **62** | **All pass** |

### What Tests Cover

- **Store tests:** Initial state, setUser/clearUser/setInitialized actions, selector hooks
- **Schema tests:** All 7 schemas with valid data, invalid data (wrong email, short password, numeric-only, wrong code length, invalid UUID)
- **API tests:** All 15 functions call correct endpoints with correct payloads, mock apiClient
- **Component tests:** Form rendering, field presence, validation error display, successful submission, API error handling (invalid_credentials, rate_limit, conflict), OAuth button presence, loading/error/empty states (SessionList)

---

## 13. File Summary

### New Files (29)

| File | Description |
|------|-------------|
| `src/lib/validations/auth.ts` | 7 Zod schemas + inferred types for all auth forms |
| `src/stores/auth-store.ts` | Zustand auth store (no persist), selector hooks, non-React access |
| `src/features/auth/api/auth-api.ts` | 15 pure async API functions + session cookie helpers |
| `src/features/auth/hooks/use-auth-queries.ts` | 2 query hooks + queryOptions factories |
| `src/features/auth/hooks/use-auth-mutations.ts` | 12 mutation hooks with side effects |
| `src/features/auth/components/AuthInitializer.tsx` | Silent refresh bootstrap (runs once on mount) |
| `src/features/auth/components/LoginForm.tsx` | Login form with error handling + OAuth |
| `src/features/auth/components/RegisterForm.tsx` | Registration form with conflict handling |
| `src/features/auth/components/OAuthButtons.tsx` | Google + Apple OAuth buttons with divider |
| `src/features/auth/components/VerifyEmailForm.tsx` | 6-digit code input with resend cooldown |
| `src/features/auth/components/ForgotPasswordForm.tsx` | Email-only password reset request |
| `src/features/auth/components/ResetPasswordForm.tsx` | Token-based password reset confirm |
| `src/features/auth/components/ChangePasswordForm.tsx` | Current + new password change |
| `src/features/auth/components/SessionList.tsx` | Active sessions list with revoke |
| `src/components/common/FormField.tsx` | Reusable Label + Input + error wrapper |
| `src/components/common/PasswordInput.tsx` | Password with visibility toggle |
| `src/middleware.ts` | Edge-level route protection via has_session cookie |
| `src/app/(auth)/verify-email/page.tsx` | Verify email page |
| `src/app/(auth)/verify-success/page.tsx` | Static email verified success page |
| `src/app/(auth)/forgot-password/page.tsx` | Forgot password page |
| `src/app/(auth)/reset-password/page.tsx` | Reset password page |
| `src/app/(auth)/resend-verification/page.tsx` | Resend verification page |
| `src/stores/auth-store.test.ts` | Store unit tests (7) |
| `src/lib/validations/auth.test.ts` | Schema validation tests (20) |
| `src/features/auth/api/auth-api.test.ts` | API function tests (15) |
| `src/features/auth/components/LoginForm.test.tsx` | LoginForm component tests (6) |
| `src/features/auth/components/RegisterForm.test.tsx` | RegisterForm component tests (4) |
| `src/features/auth/components/VerifyEmailForm.test.tsx` | VerifyEmailForm component tests (4) |
| `src/features/auth/components/SessionList.test.tsx` | SessionList component tests (6) |

### Modified Files (7)

| File | Change |
|------|--------|
| `src/types/index.ts` | Added `missing_token` and `oauth_error` to `ApiErrorCode` union |
| `src/features/auth/types.ts` | Fixed `old_password` → `current_password`, removed duplicate `AuthResponse`, added 7 new interfaces |
| `src/lib/api-client.ts` | Added `clearSessionCookie()` helper, called in refresh-failure and token_already_used handlers |
| `src/app/Providers.tsx` | Added `AuthInitializer` wrapper around children |
| `src/app/(auth)/login/page.tsx` | Replaced placeholder with `LoginForm` import |
| `src/app/(auth)/register/page.tsx` | Replaced placeholder with `RegisterForm` import |
| `vitest.config.ts` | Changed test environment from `jsdom` to `happy-dom` |

---

## 14. Known Limitations

1. **OAuth callback pages not implemented** — Only initiation (redirect to provider). The backend handles callbacks and redirects back, but the frontend callback receiver page (`/auth/callback/google`, `/auth/callback/apple`) is not yet built.
2. **No `callbackUrl` consumption after login** — Middleware sets `callbackUrl` in search params on redirect to `/login`, but `useLogin.onSuccess` always pushes to `/dashboard`. Should read `callbackUrl` from URL and redirect there instead.
3. **No remember-me / session persistence indicator** — The `has_session` cookie has a fixed 7-day max-age. No UI toggle for session duration.
4. **No real-time session invalidation** — If a session is revoked from another device, the current session doesn't know until the next API call fails with 401.
5. **Middleware is deprecated convention** — Next.js 16 flags `middleware.ts` as deprecated in favor of "proxy". Currently works but should be migrated.

---

## 15. vNext TODOs

| Item | Context | Priority |
|------|---------|----------|
| OAuth callback pages | Backend redirects to `/auth/callback/{provider}`. Need pages that read tokens from URL/cookies and complete login. | P0 |
| `callbackUrl` redirect | Read `callbackUrl` from login URL params and redirect after successful login instead of always `/dashboard`. | P1 |
| Migrate middleware to proxy | Next.js 16 proxy convention replaces middleware. Same logic, new API. | P1 |
| Protected settings page | `ChangePasswordForm` and `SessionList` are built but have no settings page to live in yet. | P1 |
| Auth loading skeleton | Show loading state while `AuthInitializer` runs (currently renders children immediately, auth state may flash). | P2 |
| Biometric / passkey support | Backend has no passkey endpoint yet, but UI placeholder could be added. | P3 |

---

## 16. Changelog

### v1 (2026-02-24)
- Initial implementation of complete frontend auth system
- 15 API functions, 14 hooks (2 queries + 12 mutations), Zustand store
- 8 auth form components + 2 common components
- 7 route pages under `app/(auth)/`
- Edge middleware for route protection via `has_session` cookie
- 62 tests across 7 test files (all passing)
- Verified against backend contracts (18 error codes, 15 endpoints, all field names)
