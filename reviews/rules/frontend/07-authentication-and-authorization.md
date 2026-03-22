# 07 — Authentication & Authorization Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 7.1 Authentication Flow

| ID | Rule | Verdict |
|----|------|---------|
| 7.1.1 | FAIL if login form does not use react-hook-form + zodResolver | PASS/FAIL |
| 7.1.2 | FAIL if register form is missing required fields (email, password, confirm, name, terms) or Zod validation | PASS/FAIL |
| 7.1.3 | WARN if forgot password flow reveals whether an email exists in the system | PASS/WARN |
| 7.1.4 | FAIL if reset password flow does not read token from URL and validate matching passwords | PASS/FAIL |
| 7.1.5 | FAIL if email verification flow does not handle code/link token from URL | PASS/FAIL |
| 7.1.6 | FAIL if validation errors appear as generic banners instead of below specific fields | PASS/FAIL |
| 7.1.7 | FAIL if server validation errors are not mapped to form fields via handleApiError/setError | PASS/FAIL |
| 7.1.8 | FAIL if successful login/register does not update auth store and set access token in memory | PASS/FAIL |

## 7.2 Auth Initialization

| ID | Rule | Verdict |
|----|------|---------|
| 7.2.1 | FAIL if AuthInitializer does not attempt token refresh on app mount | PASS/FAIL |
| 7.2.2 | FAIL if successful refresh does not populate auth store (user + token) | PASS/FAIL |
| 7.2.3 | FAIL if failed refresh shows error UI instead of silently setting unauthenticated state | PASS/FAIL |
| 7.2.4 | FAIL if missing isInitialized flag causes flash of unauthenticated content (FOUC) | PASS/FAIL |
| 7.2.5 | FAIL if AuthInitializer renders children before initialization completes | PASS/FAIL |
| 7.2.6 | FAIL if AuthInitializer is not placed inside Providers.tsx wrapping the entire app | PASS/FAIL |

## 7.3 Session Management

| ID | Rule | Verdict |
|----|------|---------|
| 7.3.1 | FAIL if has_session cookie is not used by middleware for routing decisions | PASS/FAIL |
| 7.3.2 | FAIL if has_session cookie lifecycle does not mirror auth state (set on login, cleared on logout) | PASS/FAIL |
| 7.3.3 | WARN if sessions page does not show active sessions with device info | PASS/WARN |
| 7.3.4 | WARN if session revocation (remote logout) is not supported | PASS/WARN |
| 7.3.5 | WARN if current session is not visually highlighted in session list | PASS/WARN |
| 7.3.6 | WARN if session entries lack device, IP, or last-active timestamp | PASS/WARN |

## 7.4 Multi-Tier Authorization

| ID | Rule | Verdict |
|----|------|---------|
| 7.4.1 | WARN if navigation items are not conditionally rendered based on permissions (Tier 1) | PASS/WARN |
| 7.4.2 | FAIL if _permissions in GET detail responses are not consumed via <Can> component (Tier 1.5) | PASS/FAIL |
| 7.4.3 | FAIL if route guards do not protect authenticated and role-specific routes (Tier 2) | PASS/FAIL |
| 7.4.4 | FAIL if frontend permission checks are treated as security boundaries instead of UX (Tier 3) | PASS/FAIL |
| 7.4.5 | FAIL if any frontend permission check could create a security hole if bypassed | PASS/FAIL |
| 7.4.6 | WARN if permission changes do not reflect on next API response without page reload | PASS/WARN |

## 7.5 Permission-Aware Responses

| ID | Rule | Verdict |
|----|------|---------|
| 7.5.1 | FAIL if WithPermissions<T> generic type does not exist for composing _permissions on resource types | PASS/FAIL |
| 7.5.2 | FAIL if _permissions is consumed from list, POST, PATCH, or DELETE responses (should be GET detail only) | PASS/FAIL |
| 7.5.3 | WARN if features do not define their own Permissions type (BusinessPermissions, etc.) | PASS/WARN |
| 7.5.4 | FAIL if permission values are anything other than booleans | PASS/FAIL |
| 7.5.5 | FAIL if frontend evaluates permissions from role name strings instead of boolean flags | PASS/FAIL |
| 7.5.6 | FAIL if missing _permissions causes a crash instead of defaulting to restrictive state | PASS/FAIL |

## 7.6 Relationship Injection

| ID | Rule | Verdict |
|----|------|---------|
| 7.6.1 | WARN if _relationship is not present on GET detail responses for membership/transaction state | PASS/WARN |
| 7.6.2 | WARN if RequestToJoinButton, FollowButton, ConnectButton do not read from _relationship | PASS/WARN |
| 7.6.3 | WARN if separate API calls are made for membership, follow, and transaction status when _relationship provides them | PASS/WARN |
| 7.6.4 | WARN if business/platform detail responses lack follow_status and active_follow_transaction | PASS/WARN |
| 7.6.5 | WARN if user detail responses lack connection_status and active_connection_transaction | PASS/WARN |
| 7.6.6 | FAIL if null _relationship values (no membership, no transaction) cause crashes instead of default states | PASS/FAIL |

## 7.7 Route Protection

| ID | Rule | Verdict |
|----|------|---------|
| 7.7.1 | FAIL if AuthGuard does not redirect to /login with callbackUrl for unauthenticated users | PASS/FAIL |
| 7.7.2 | FAIL if BusinessGuard does not verify active business membership from Zustand store | PASS/FAIL |
| 7.7.3 | FAIL if PlatformGuard does not verify platform membership | PASS/FAIL |
| 7.7.4 | FAIL if AdminGuard does not verify admin-level permissions | PASS/FAIL |
| 7.7.5 | FAIL if guards show blank page or flash of login instead of loading skeleton during init | PASS/FAIL |
| 7.7.6 | FAIL if guards render protected children before authorization is confirmed | PASS/FAIL |
| 7.7.7 | WARN if guards do not handle edge cases (expired sessions, revoked memberships, race conditions) | PASS/WARN |

## 7.8 OAuth Integration

| ID | Rule | Verdict |
|----|------|---------|
| 7.8.1 | WARN if OAuthButtons component does not handle Google and Apple OAuth | PASS/WARN |
| 7.8.2 | WARN if OAuth redirects do not preserve callback URL for post-auth navigation | PASS/WARN |
| 7.8.3 | WARN if account linking (existing email) is not handled gracefully | PASS/WARN |
| 7.8.4 | WARN if OAuth errors are not displayed with clear user-facing messages | PASS/WARN |
| 7.8.5 | WARN if OAuth flow does not support redirect mode | PASS/WARN |
| 7.8.6 | FAIL if OAuth provider tokens are stored client-side instead of exchanged server-side | PASS/FAIL |

## 7.9 Logout & Session Cleanup

| ID | Rule | Verdict |
|----|------|---------|
| 7.9.1 | FAIL if logout does not clear access token via clearTokens() | PASS/FAIL |
| 7.9.2 | FAIL if logout does not clear has_session cookie | PASS/FAIL |
| 7.9.3 | FAIL if logout does not reset Zustand auth store to initial state | PASS/FAIL |
| 7.9.4 | FAIL if logout does not call queryClient.clear() to remove cached data | PASS/FAIL |
| 7.9.5 | FAIL if user is not redirected to login page after logout | PASS/FAIL |
| 7.9.6 | FAIL if stale authenticated UI is visible after logout (store/cache not cleared) | PASS/FAIL |

## 7.10 Token Security

| ID | Rule | Verdict |
|----|------|---------|
| 7.10.1 | FAIL if access token appears in localStorage, sessionStorage, URL params, or non-HttpOnly cookies | PASS/FAIL |
| 7.10.2 | FAIL if refresh token is accessible to JavaScript (must be HttpOnly) | PASS/FAIL |
| 7.10.3 | FAIL if tokens appear in console.log, error reports, or API request logging | PASS/FAIL |
| 7.10.4 | WARN if CSP does not restrict script sources to prevent token exfiltration via XSS | PASS/WARN |
| 7.10.5 | FAIL if JWT payload is decoded client-side for authorization decisions | PASS/FAIL |
| 7.10.6 | WARN if error reporting (Sentry) does not exclude tokens from captured context | PASS/WARN |
| 7.10.7 | FAIL if has_session cookie contains token data, user ID, or session ID (should be boolean hint only) | PASS/FAIL |

## 7.11 Auth Testing

| ID | Rule | Verdict |
|----|------|---------|
| 7.11.1 | FAIL if auth store transitions (login/logout/refresh) lack test coverage | PASS/FAIL |
| 7.11.2 | WARN if guard redirect behavior is not tested (callbackUrl, non-member redirect) | PASS/WARN |
| 7.11.3 | WARN if guard render behavior is not tested (authorized user sees children) | PASS/WARN |
| 7.11.4 | WARN if token refresh flow is not tested with mock interceptors | PASS/WARN |
| 7.11.5 | FAIL if login/register form validation is not tested (Zod, field errors, server errors, success) | PASS/FAIL |
| 7.11.6 | WARN if session management (list, revoke, highlight) lacks test coverage | PASS/WARN |
| 7.11.7 | WARN if <Can> component permission gating is not tested | PASS/WARN |
