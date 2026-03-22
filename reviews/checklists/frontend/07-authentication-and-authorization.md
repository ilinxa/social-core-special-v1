# 07 — Authentication & Authorization Checklist

## 7.1 Authentication Flow

- [ ] **Login form with email/password using react-hook-form + Zod** — LoginForm uses useForm with zodResolver and a schema that validates email format and password presence
- [ ] **Register form with all required fields and validation** — RegisterForm includes email, password, password confirmation, name, and terms acceptance with Zod validation on all fields
- [ ] **Forgot password flow sends reset email** — ForgotPasswordForm accepts an email, calls the backend endpoint, and shows a success message regardless of whether the email exists
- [ ] **Reset password flow accepts token and new password** — ResetPasswordForm reads the token from URL params, validates matching passwords, and submits the reset
- [ ] **Email verification flow with code/link** — VerifyEmailForm handles the verification code or link token from the URL and confirms the email address
- [ ] **Each flow shows field-level validation errors** — Zod validation errors appear below the specific field that failed, not as a generic banner
- [ ] **Server validation errors mapped to fields via handleApiError** — backend validation errors (email already exists, password too weak) are mapped to the correct form field using setError
- [ ] **Success responses update auth store and set access token** — on login/register success, the auth store is updated with user data and the access token is stored in memory via setToken

## 7.2 Auth Initialization

- [ ] **AuthInitializer component attempts token refresh on app mount** — when the app loads, AuthInitializer calls the refresh endpoint to restore an existing session from the HttpOnly cookie
- [ ] **Silent refresh populates auth store with user data** — a successful refresh response updates the Zustand auth store with the user object and stores the new access token
- [ ] **If refresh fails user remains unauthenticated** — a failed refresh (no cookie, expired cookie) silently sets auth state to unauthenticated without showing error UI
- [ ] **isInitialized flag prevents flash of unauthenticated content** — until the refresh attempt completes, the app shows a loading state rather than briefly rendering the login page
- [ ] **AuthInitializer renders children only after initialization** — the component gates its children behind the isInitialized check, preventing premature rendering of route content
- [ ] **AuthInitializer placed in Providers.tsx** — it wraps the entire app inside the provider tree, ensuring all child components have access to the resolved auth state

## 7.3 Session Management

- [ ] **has_session cookie gates middleware redirects** — a client-readable boolean cookie indicates whether a session exists, allowing Next.js middleware to make routing decisions without hitting the backend
- [ ] **Cookie set on login success and cleared on logout** — the has_session cookie lifecycle mirrors the authentication state exactly, set when tokens are received and removed on logout
- [ ] **Sessions page shows list of active sessions with device info** — users can view all their active sessions including browser, OS, and approximate location information
- [ ] **Session revocation supported** — users can log out a specific session remotely by calling the backend's session revocation endpoint
- [ ] **Current session highlighted in session list** — the session matching the user's current browser is visually distinguished from other active sessions
- [ ] **Session details include device, IP, and last active timestamp** — each session entry shows enough information for the user to identify which device it belongs to

## 7.4 Multi-Tier Authorization

- [ ] **Tier 1: nav items conditionally rendered based on permissions** — navigation links and menu items are shown or hidden based on the user's role and permissions from the auth store
- [ ] **Tier 1.5: _permissions in GET detail responses gate UI elements via <Can>** — the Can component reads evaluated boolean permissions from the API response and conditionally renders children
- [ ] **Tier 2: route guards protect authenticated and role-specific routes** — AuthGuard, BusinessGuard, PlatformGuard, and AdminGuard prevent unauthorized access at the routing level
- [ ] **Tier 3: backend enforcement is the ultimate authority** — the frontend treats all its permission checks as UX optimizations, never as security boundaries
- [ ] **Frontend never trusts its own permission checks for security** — even if the UI hides a button, the backend independently validates every request against RBAC policies
- [ ] **Tiers are layered and additive** — each tier adds a layer of defense; no single tier is relied upon exclusively, and removing one tier does not create a security hole
- [ ] **Permission changes reflect immediately** — when the backend updates a user's permissions, the next API response carries the updated _permissions and the UI adjusts without requiring a page reload

## 7.5 Permission-Aware Responses

- [ ] **WithPermissions<T> type composes resource types with _permissions** — a generic type adds _permissions: T to any resource type, used for detail endpoint responses
- [ ] **_permissions consumed from GET detail responses only** — permissions are injected by the backend on single-resource GET endpoints, never on list, POST, PATCH, or DELETE responses
- [ ] **Each feature defines its own Permissions type** — BusinessPermissions, PlatformPermissions, UserPermissions, etc., each listing the boolean permission fields relevant to that resource
- [ ] **Permissions are boolean values** — each permission is true or false, not a role name, numeric level, or complex object
- [ ] **Frontend never evaluates permissions from role names directly** — the frontend does not compare role strings like "admin" or "owner"; it uses pre-evaluated boolean permissions from the backend
- [ ] **_permissions absence handled gracefully** — if a response lacks _permissions (e.g., anonymous user or list endpoint), the UI defaults to a restrictive state rather than crashing

## 7.6 Relationship Injection

- [ ] **_relationship from GET detail responses provides membership and transaction state** — membership_status and active_transaction fields indicate the viewer's current relationship with the resource
- [ ] **Used by RequestToJoinButton, FollowButton, and ConnectButton** — these components read _relationship to determine which action to show (join, pending, cancel, follow, unfollow, connect)
- [ ] **Reduces API calls from 3 to 1** — instead of separate calls for membership status, follow status, and transaction status, a single detail GET provides all relationship data
- [ ] **follow_status and active_follow_transaction on business/platform** — business and platform detail responses include follow relationship data for the authenticated viewer
- [ ] **connection_status and active_connection_transaction on user** — user detail responses include connection relationship data between the authenticated viewer and the profile user
- [ ] **Null values handled correctly** — null membership_status means not-a-member, null active_transaction means no pending transaction; the UI renders default states for these cases

## 7.7 Route Protection

- [ ] **AuthGuard redirects to /login with callbackUrl** — unauthenticated users are sent to login with the original URL preserved for post-login redirect
- [ ] **BusinessGuard verifies active business membership in Zustand store** — checks that the user has an active membership in the business identified by the route's [slug] parameter
- [ ] **PlatformGuard verifies platform membership** — checks that the user has an active membership in the platform before rendering platform console routes
- [ ] **AdminGuard verifies admin role** — checks that the user has admin-level permissions before rendering admin panel routes
- [ ] **All guards show loading skeleton during auth initialization** — guards render a loading state while auth state is being resolved, not a blank page or a flash of the login page
- [ ] **Guards do not render children until authorized** — the protected component tree is not mounted or rendered in any way until the guard confirms authorization
- [ ] **Guards handle edge cases** — expired sessions trigger re-authentication, revoked memberships redirect to an appropriate page, and race conditions during initialization are handled

## 7.8 OAuth Integration

- [ ] **OAuthButtons component handles Google and Apple OAuth** — dedicated buttons for each provider with appropriate branding and loading states
- [ ] **OAuth redirects preserve callback URL for post-auth navigation** — the return URL after OAuth completion sends the user to where they originally intended to go
- [ ] **Account linking handled safely** — when a user authenticates via OAuth with an email that already has an account, the flow handles linking or conflict resolution gracefully
- [ ] **OAuth errors displayed to user with clear messages** — provider errors, cancelled flows, and network issues during OAuth show understandable error messages
- [ ] **OAuth flow works in popup or redirect mode** — the implementation supports both popup-based and full-redirect OAuth flows depending on the browser context
- [ ] **OAuth tokens are not stored client-side** — the OAuth provider's tokens are exchanged server-side for the app's own JWT; provider tokens never reach the frontend

## 7.9 Logout & Session Cleanup

- [ ] **Logout clears access token via clearTokens()** — the in-memory access token is set to null, preventing any subsequent API calls from including an Authorization header
- [ ] **Logout clears has_session cookie** — the client-readable session indicator cookie is removed so middleware no longer treats the user as potentially authenticated
- [ ] **Logout clears auth store** — the Zustand auth store is reset to its initial state, clearing user data, tokens, and authentication flags
- [ ] **Logout invalidates all TanStack Query caches** — queryClient.clear() is called to remove all cached data, preventing stale authenticated data from being shown to a subsequent user
- [ ] **Page redirects to login after logout** — after all cleanup is complete, the user is navigated to the login page
- [ ] **No stale authenticated UI visible after logout** — the combination of store clearing, cache clearing, and redirect ensures no component briefly renders with the previous user's data

## 7.10 Token Security

- [ ] **Access token never in localStorage, sessionStorage, URL params, or non-HttpOnly cookies** — the token exists only as a JavaScript variable in memory, inaccessible to any persistence or inspection mechanism
- [ ] **Refresh token in HttpOnly cookie only** — the refresh token is set by the backend with HttpOnly, Secure, and SameSite flags, making it completely inaccessible to JavaScript
- [ ] **No token logging anywhere** — access tokens, refresh tokens, and any auth credentials are excluded from console.log, error reports, and API request logging
- [ ] **CSP prevents token exfiltration via XSS** — Content Security Policy headers restrict script sources and prevent inline scripts from exfiltrating tokens to attacker-controlled domains
- [ ] **Token payload is not parsed client-side for sensitive data** — the JWT is treated as an opaque string; no client-side code decodes it to read claims for authorization decisions
- [ ] **Tokens not included in error context sent to Sentry** — error reporting configurations explicitly exclude Authorization headers and token values from captured breadcrumbs and contexts
- [ ] **has_session cookie is a boolean hint only** — the cookie contains no token data, user ID, or session ID; it is purely a routing hint for the middleware

## 7.11 Auth Testing

- [ ] **Auth store transitions tested** — login sets user and token, logout clears everything, token refresh updates the token without clearing user data
- [ ] **Guard redirect behavior tested** — AuthGuard redirects unauthenticated users to /login with callbackUrl, BusinessGuard redirects non-members to an appropriate fallback
- [ ] **Guard render behavior tested** — authenticated and authorized users see the protected children component rendered correctly
- [ ] **Token refresh flow tested with mock interceptors** — tests simulate 401 responses, verify the refresh attempt, and confirm queued requests are replayed with the new token
- [ ] **Login/register form validation tested** — tests verify Zod schema validation, field-level error display, server error mapping, and successful submission behavior
- [ ] **Session management tested** — session list rendering, current session highlighting, and session revocation actions are covered by component tests
- [ ] **Permission-based UI gating tested** — tests verify that <Can> renders children when allowed is true and hides them when false, using different _permissions payloads
