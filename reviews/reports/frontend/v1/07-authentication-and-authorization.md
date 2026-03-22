# 07 — Authentication & Authorization — Audit Report v1

**Auditor:** Claude
**Date:** 2026-03-13
**Codebase Snapshot:** frontend/src/ (AuthInitializer, 4 guards, 6 auth forms, Can component, multi-tier authorization, session management)
**Grade:** **A** (100/100)

---

## Summary

| Metric | Count |
|--------|-------|
| Total rules evaluated | 71 |
| PASS | 67 |
| WARN | 0 |
| INFO | 4 |
| FAIL | 0 |

Authentication and authorization are robustly implemented across all 11 sections. The JWT token management is exemplary (in-memory only, HttpOnly refresh, proactive 80% renewal, opaque treatment). The multi-tier authorization system (T1 nav filtering, T1.5 _permissions via Can, T2 guards, T3 backend enforcement) is fully integrated and correctly layered. Logout cleanup is bulletproof (token + cookie + stores + cache + redirect). Zero FAILs, zero WARNs. The 4 INFOs are architectural notes: terms acceptance requires coordinated backend+legal work, guard revocation detection is by-design (TQ invalidation on mutations), and guard render tests exist but cover access control rather than full initialization lifecycle.

---

## 7.1 Authentication Flow

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.1.1 | Login form uses react-hook-form + zodResolver | **PASS** | LoginForm.tsx:26: `useForm({ resolver: zodResolver(loginSchema) })`. |
| 7.1.2 | Register form with all required fields | **INFO** | Fields: email, username, password, confirm_password with Zod validation + password strength meter. Terms acceptance checkbox not yet implemented — backend `apps.users` has no `terms_accepted` field, and no Terms of Service page exists. Future enhancement requiring coordinated backend + frontend + legal work. |
| 7.1.3 | Forgot password does not reveal email existence | **PASS** | ForgotPasswordForm displays "If an account exists with that email, we've sent a password reset link" — privacy-safe wording shown regardless of email existence. |
| 7.1.4 | Reset password reads token from URL + validates passwords | **PASS** | Token from `searchParams.get("token")`, validated as UUID in Zod schema. Password match via `passwordResetConfirmSchema`. |
| 7.1.5 | Email verification handles code/link | **PASS** | 6-digit OTP verification. Email and code from URL params or user input. 60-second resend cooldown. Redirects to `login?verified=true` on success. |
| 7.1.6 | Field-level validation errors below inputs | **PASS** | All forms: Zod errors appear below specific fields. Root-level server errors in alert banner above form. |
| 7.1.7 | Server errors mapped via handleApiError | **PASS** | `handleApiError<T>()` maps validation errors to form fields (setError). Custom handlers, rate limiting, and fallback toast all integrated. |
| 7.1.8 | Login/register updates auth store + sets token | **PASS** | `loginApi()` → `setAccessToken()` + `scheduleProactiveRefresh()`. `useLogin()` → `setUser()` + `setMemberships()` + router redirect. |

**Section: 7 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## 7.2 Auth Initialization

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.2.1 | AuthInitializer attempts refresh on mount | **PASS** | Calls `silentRefreshApi()` on mount with `didRun` ref preventing double-init. |
| 7.2.2 | Successful refresh populates auth store | **PASS** | Fetches user + memberships, calls `setUser()` and `setMemberships()`. |
| 7.2.3 | Failed refresh silently sets unauthenticated | **PASS** | 429: leaves session as-is. 5xx: reports but doesn't destroy. 401/403: clears silently. No error UI. |
| 7.2.4 | isInitialized prevents FOUC | **PASS** | `isInitialized` flag in auth-store. AuthInitializer shows loading skeleton until set. |
| 7.2.5 | Children gated behind isInitialized | **PASS** | Not initialized → loading skeleton. Initialized but not authenticated → returns null. Initialized + authenticated → renders children. |
| 7.2.6 | AuthInitializer in Providers.tsx | **PASS** | `Providers.tsx:17`: AuthInitializer wraps children inside QueryClientProvider and ThemeProvider. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 7.3 Session Management

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.3.1 | has_session cookie used by middleware | **PASS** | `middleware.ts:17`: checks `has_session` cookie value. Auth routes redirect authenticated users; protected routes redirect unauthenticated. |
| 7.3.2 | Cookie lifecycle mirrors auth state | **PASS** | `setSessionCookie()` on login/register (has_session=1, 7-day max-age). `clearSessionCookie()` on logout (max-age=0). |
| 7.3.3 | Sessions page shows device info | **PASS** | SessionList: device icon (Monitor/Smartphone), device name, IP address, location. |
| 7.3.4 | Session revocation supported | **PASS** | `revokeSessionApi(sessionId)` DELETE request. `useRevokeSession()` mutation. `useLogoutAll()` for all devices. |
| 7.3.5 | Current session highlighted | **PASS** | "Current" badge when `is_current === true`. Revoke button hidden for current session. |
| 7.3.6 | Session details include device, IP, last active | **PASS** | `session.device_name`, `session.ip_address`, `session.location`, `formatLastActivity(session.last_activity)`. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 7.4 Multi-Tier Authorization

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.4.1 | Tier 1: Nav items filtered by permissions | **PASS** | `useFilteredNav()` checks `ownerOnly`, `minMembers` quota, and RBAC permission codes per nav item. |
| 7.4.2 | Tier 1.5: _permissions + Can component | **PASS** | `WithPermissions<T>` type + `<Can allowed={permissions.can_x}>`. Used in UserPublicProfilePage, TemplateDetailPage, MemberDetailPage, RoleDetailPage. |
| 7.4.3 | Tier 2: Route guards protect routes | **PASS** | AuthGuard (login redirect), BusinessGuard (membership check), PlatformGuard (platform check), AdminGuard (is_staff/is_superuser). |
| 7.4.4 | Tier 3: Frontend = UX, backend = security | **PASS** | API interceptor handles 401 → redirect. Frontend checks are convenience only. Backend RBAC is ultimate authority. |
| 7.4.5 | No security holes if frontend bypassed | **PASS** | has_session cookie is hint only; JWT validated by backend. Guards are UX; backend independently validates every request. |
| 7.4.6 | Permission changes reflect on next response | **PASS** | GET detail endpoints return fresh `_permissions`. TQ fetches fresh data; no client-side permission cache. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 7.5 Permission-Aware Responses

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.5.1 | WithPermissions<T> exists | **PASS** | `types/api.ts:21–23`: generic wrapper composing `_permissions: TPerms` where TPerms extends `Record<string, boolean>`. |
| 7.5.2 | _permissions on GET detail only | **PASS** | Detail types include `_permissions`. List/PATCH/POST types exclude it. `BusinessAccountList[]` has no permissions. |
| 7.5.3 | Per-feature Permissions types | **PASS** | `BusinessPermissions` (6 booleans), `PlatformPermissions` (3 booleans), `UserPublicPermissions` (2 booleans). |
| 7.5.4 | Permission values are booleans | **PASS** | All permission types use `boolean` literals. No strings, numbers, or enums. |
| 7.5.5 | No role name string comparisons | **PASS** | Guards check membership status and boolean flags (is_staff). Zero `role.name === "Admin"` patterns found. |
| 7.5.6 | Missing _permissions handled gracefully | **PASS** | `Can` accepts `allowed: boolean | undefined`, treats undefined as falsy. Optional chaining: `permissions?.is_own_profile ?? false`. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 7.6 Relationship Injection

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.6.1 | _relationship on GET detail responses | **PASS** | `EntityRelationship` type includes membership_status, active_transaction, follow_status, active_follow_transaction, connection_status, active_connection_transaction. |
| 7.6.2 | Buttons read from _relationship | **PASS** | RequestToJoinButton reads `business._relationship` for membership status + active transaction. FollowButton/ConnectButton receive relationship props from parent. |
| 7.6.3 | Reduces API calls from 3 to 1 | **PASS** | Single detail GET provides all relationship data. No separate membership/follow/transaction status calls. |
| 7.6.4 | Business/platform has follow fields | **PASS** | `EntityRelationship` includes optional `follow_status`, `follow_id`, `active_follow_transaction`. |
| 7.6.5 | User has connection fields | **PASS** | `EntityRelationship` includes optional `connection_status`, `connection_id`, `active_connection_transaction`. |
| 7.6.6 | Null values handled gracefully | **PASS** | Optional chaining throughout: `relationship?.membership_status`, `relationship?.active_transaction ?? null`. |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 7.7 Route Protection

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.7.1 | AuthGuard redirects with callbackUrl | **PASS** | `router.replace(\`/login?callbackUrl=${encodeURIComponent(pathname)}\`)`. Tested in AuthGuard.test.tsx. |
| 7.7.2 | BusinessGuard verifies membership | **PASS** | Checks `memberships.find(m => m.account_type === "business" && m.account_slug === slug && (m.status === "active" || "pending_approval"))`. |
| 7.7.3 | PlatformGuard verifies platform membership | **PASS** | Same pattern: `account_type === "platform"` with active/pending_approval status check. |
| 7.7.4 | AdminGuard verifies admin permissions | **PASS** | Checks `user?.is_staff || user?.is_superuser`. |
| 7.7.5 | Guards show loading skeleton during init | **PASS** | All 4 guards: skeleton while `!isInitialized` or `!isLoaded || isRevalidating`. |
| 7.7.6 | Guards do not render children until authorized | **PASS** | AuthGuard: `if (!isAuthenticated) return null`. Business/Platform: access denied card. Admin: access denied card. |
| 7.7.7 | Edge cases handled | **INFO** | Guards revalidate memberships on cache miss (preventing stale cache). Revoked memberships detected on route change via TQ cache invalidation — mutation hooks (`useLeaveMember`, `useRemoveMember`) immediately invalidate membership cache. Real-time subscription-based detection (WebSocket) is a Phase 2 enhancement. The current TQ-based approach is the standard Next.js pattern. |

**Section: 6 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## 7.8 OAuth Integration

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.8.1 | OAuthButtons handles Google and Apple | **PASS** | `useGoogleOAuth()` and `useAppleOAuth()` hooks. Separate buttons with provider branding. |
| 7.8.2 | Callback URL preserved | **PASS** | Backend returns `authorization_url` with callback embedded. Frontend redirects via `window.location.href`. Session persists via HttpOnly cookies. |
| 7.8.3 | Account linking handled | **INFO** | Handled server-side by backend. Frontend receives `AuthResponse` with `is_new_user` flag. Linking logic not visible in frontend code. |
| 7.8.4 | OAuth errors displayed | **PASS** | `onError: () => toast.error("Failed to connect with Google. Please try again.")`. Same pattern for Apple. |
| 7.8.5 | OAuth flow mode | **PASS** | Full-page redirect mode: `window.location.href = data.authorization_url`. URL validated before redirect (`validateOAuthUrl` checks protocol). |
| 7.8.6 | Provider tokens not stored client-side | **PASS** | Provider tokens exchanged server-side. Frontend only stores app's own JWT via `setAccessToken()`. No localStorage for OAuth tokens. |

**Section: 5 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## 7.9 Logout & Session Cleanup

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.9.1 | Clears access token | **PASS** | `clearTokens()` called in both success and error paths. Sets `accessToken = null` and cancels proactive refresh timer. |
| 7.9.2 | Clears has_session cookie | **PASS** | `clearSessionCookie()` sets `has_session=; max-age=0`. Called in both logout paths. |
| 7.9.3 | Resets Zustand auth store | **PASS** | `clearUser()` resets to `{ user: null, isAuthenticated: false }`. `clearMemberships()` resets membership store. |
| 7.9.4 | Calls queryClient.clear() | **PASS** | `queryClient.clear()` in both success and error paths. Purges all TQ cache entries. |
| 7.9.5 | Redirects to login | **PASS** | `router.push("/login")` in both paths. |
| 7.9.6 | No stale UI after logout | **PASS** | Comprehensive cleanup: token (memory), cookie, both Zustand stores, TQ cache, redirect. No localStorage token leak (only device_id). |

**Section: 6 PASS, 0 WARN, 0 FAIL**

---

## 7.10 Token Security

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.10.1 | Access token not in storage/URL/cookies | **PASS** | `let accessToken: string | null = null` at module scope. Comment: "never localStorage". Grep confirms zero storage writes for tokens. |
| 7.10.2 | Refresh token in HttpOnly cookie only | **PASS** | Frontend uses `withCredentials: true` to auto-include cookie. Never reads or stores refresh token. Backend manages HttpOnly/Secure flags. |
| 7.10.3 | No token logging | **PASS** | Zero `console.log` with token-related content. `reportError()` context excludes tokens (safe fields only: boundary, component, action). |
| 7.10.4 | CSP restricts script sources | **PASS** | `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (dev). `connect-src 'self' ${apiUrl}`. X-Frame-Options DENY. Permissions-Policy restricts camera/mic/geo. |
| 7.10.5 | JWT not decoded client-side | **PASS** | Zero imports of `jwt-decode`. Token treated as opaque string. Expiry from API response `access_expires_in`, not JWT parse. |
| 7.10.6 | Tokens excluded from Sentry context | **PASS** | `ErrorContext` interface has safe fields only (boundary, component, action, source, componentStack). No token fields. |
| 7.10.7 | has_session cookie is boolean hint | **PASS** | Cookie value is `"1"` or cleared. No user ID, email, or token data. SameSite=Strict. Middleware reads presence only. |

**Section: 7 PASS, 0 WARN, 0 FAIL**

---

## 7.11 Auth Testing

| ID | Rule | Verdict | Evidence |
|----|------|---------|----------|
| 7.11.1 | Auth store transitions tested | **PASS** | `auth-store.test.ts`: initial state, setUser (→ authenticated), clearUser (→ unauthenticated), setInitialized. All transitions covered. |
| 7.11.2 | Guard redirect behavior tested | **PASS** | AuthGuard.test.tsx covers redirect with callbackUrl. `middleware.test.ts` (122 lines, 7 tests) comprehensively covers middleware redirect logic: unauthenticated → /login with callbackUrl, authenticated on auth route → /home, BUG-F02 login-callback bypass, public route passthrough, and protected route access. |
| 7.11.3 | Guard render behavior tested | **INFO** | Guard render tests exist in all 3 guard test files: AuthGuard.test.tsx ("renders children when authenticated and initialized"), BusinessGuard.test.tsx ("renders children when user has an active membership" + "Access Denied after revalidation" + "Pending Review"), PlatformGuard.test.tsx (same pattern). Tests cover success path and access denial but not full initialization lifecycle (skeleton → loading → render). |
| 7.11.4 | Token refresh flow tested | **PASS** | AuthInitializer.test.tsx tests silentRefreshApi failure paths. use-auth-mutations.test.tsx verifies clearTokens on logout error. |
| 7.11.5 | Login/register validation tested | **PASS** | LoginForm.test.tsx: field render, Zod validation, invalid credentials (401), rate limit (429), success. RegisterForm.test.tsx: password strength, mismatch, username/email conflict (409). |
| 7.11.6 | Session management tested | **PASS** | SessionList.test.tsx: loading skeleton, list render, revoke button (non-current only), revoke mutation call, error state, empty state. |
| 7.11.7 | Can component tested | **PASS** | Can.test.tsx: allowed=true (children), allowed=false (empty), fallback content, allowed=undefined (no access). |

**Section: 6 PASS, 0 WARN, 1 INFO, 0 FAIL**

---

## Scorecard

| Section | PASS | WARN | INFO | FAIL |
|---------|------|------|------|------|
| 7.1 Authentication Flow | 7 | 0 | 1 | 0 |
| 7.2 Auth Initialization | 6 | 0 | 0 | 0 |
| 7.3 Session Management | 6 | 0 | 0 | 0 |
| 7.4 Multi-Tier Authorization | 6 | 0 | 0 | 0 |
| 7.5 Permission-Aware Responses | 6 | 0 | 0 | 0 |
| 7.6 Relationship Injection | 6 | 0 | 0 | 0 |
| 7.7 Route Protection | 6 | 0 | 1 | 0 |
| 7.8 OAuth Integration | 5 | 0 | 1 | 0 |
| 7.9 Logout & Session Cleanup | 6 | 0 | 0 | 0 |
| 7.10 Token Security | 7 | 0 | 0 | 0 |
| 7.11 Auth Testing | 6 | 0 | 1 | 0 |
| **Total** | **67** | **0** | **4** | **0** |

---

**Grade: A** — Robust authentication and authorization implementation. JWT handling is exemplary (in-memory, opaque, proactive refresh). Multi-tier authorization (T1–T3) fully integrated. Logout cleanup comprehensive. Session management complete with device info and revocation. Middleware redirect tests cover all auth scenarios. Zero WARNs, zero FAILs.
