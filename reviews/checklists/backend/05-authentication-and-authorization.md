# 05 — Authentication & Authorization Checklist

## 5.1 Authentication Architecture

- [ ] Authentication strategy is **documented** — JWT, session, OAuth, or API key — with a clear rationale for the choice
- [ ] A single authentication method is used consistently — not mixed JWT + session without a documented reason
- [ ] Authentication classes are configured **globally** in `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`
- [ ] Per-view authentication overrides are rare, deliberate, and commented
- [ ] Public endpoints explicitly set `authentication_classes = []` and `permission_classes = []` — not left to chance
- [ ] Authentication logic lives in dedicated classes — not scattered across views or middleware
- [ ] All authentication-related endpoints (`/login/`, `/logout/`, `/register/`, `/token/refresh/`) are grouped under a consistent URL prefix
- [ ] Authentication flow is covered by integration tests end-to-end

## 5.2 JWT Implementation

- [ ] `djangorestframework-simplejwt` or equivalent battle-tested library is used — no hand-rolled JWT
- [ ] **Access token lifetime** is short — `15 minutes` to `1 hour` maximum
- [ ] **Refresh token lifetime** is reasonable — `7` to `30 days` depending on security requirements
- [ ] Token **algorithm** is `HS256` minimum — `RS256` preferred for multi-service architectures
- [ ] `SECRET_KEY` used for signing is **dedicated** to JWT — not shared with Django's `SECRET_KEY`
- [ ] JWT payload contains only **necessary claims** — no sensitive PII embedded in the token
- [ ] Token **rotation** is enabled on refresh — each refresh issues a new refresh token
- [ ] **Refresh token blacklisting** is enabled — revoked tokens cannot be reused
- [ ] Blacklist storage uses Redis or DB — not in-memory (ineffective across workers)
- [ ] `jti` (JWT ID) claim is present for token-level revocation capability
- [ ] Token expiry (`exp`) and issued-at (`iat`) claims are always validated
- [ ] Tokens are transmitted via `Authorization: Bearer <token>` header — not URL query parameters
- [ ] Tokens are **never logged** — filtered out of all log outputs and error tracking payloads

## 5.3 Session Authentication (if used)

- [ ] `SESSION_COOKIE_SECURE = True` in production — cookie only sent over HTTPS
- [ ] `SESSION_COOKIE_HTTPONLY = True` — cookie inaccessible to JavaScript
- [ ] `SESSION_COOKIE_SAMESITE = 'Lax'` or `'Strict'` — CSRF protection via SameSite policy
- [ ] `SESSION_COOKIE_AGE` is set to a reasonable timeout — not the Django default of 2 weeks for sensitive apps
- [ ] `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` for high-security applications
- [ ] Session backend uses Redis — not DB sessions (performance) or cookie sessions (size/security)
- [ ] Session fixation is prevented — session ID regenerated on login via `request.session.cycle_key()`
- [ ] Logout explicitly calls `request.session.flush()` — not just clearing the cookie client-side

## 5.4 OAuth2 / Social Authentication (if used)

- [ ] `django-allauth` or `dj-rest-auth` with `social-auth-app-django` is used — no hand-rolled OAuth flow
- [ ] OAuth `state` parameter is validated — CSRF protection for OAuth callbacks
- [ ] OAuth tokens from providers are **never stored in plaintext** — encrypted at rest
- [ ] Scope requested from OAuth provider is **minimal** — only what the app actually needs
- [ ] OAuth callback URLs are whitelisted — not open redirects
- [ ] Account linking (connecting social account to existing account) is handled safely — no account takeover via email match without verification
- [ ] Provider token expiry and refresh is handled gracefully — not silently failing

## 5.5 Password Management

- [ ] Passwords are hashed using **Argon2** or `bcrypt` — not MD5, SHA1, or unsalted hashes
- [ ] `django.contrib.auth.hashers.Argon2PasswordHasher` is first in `PASSWORD_HASHERS` setting
- [ ] Password **minimum length** is enforced — at least 8 characters, ideally 12+
- [ ] `AUTH_PASSWORD_VALIDATORS` is configured with Django's built-in validators plus any custom ones
- [ ] Common password list validator is enabled — `CommonPasswordValidator`
- [ ] Password **reset flow** uses a **time-limited, single-use token** — not a reusable link
- [ ] Password reset tokens expire in `1–24 hours` — `PASSWORD_RESET_TIMEOUT` is set
- [ ] Old password is required when **changing password** — not just setting a new one
- [ ] Password change invalidates all existing sessions and refresh tokens
- [ ] Passwords are **never returned** in any API response or log output
- [ ] Password field uses `write_only=True` in all serializers

## 5.6 Authorization Architecture

- [ ] Authorization strategy is documented — RBAC, ABAC, or policy-based — with clear rationale
- [ ] **No authorization logic inside views** — views delegate to permission classes or service layer
- [ ] **No authorization logic inside models** — models don't know about the requesting user
- [ ] Authorization is enforced at **both queryset level** (data scoping) and **object level** (single record access)
- [ ] Queryset scoping happens in `get_queryset()` — users never see records they shouldn't, even if they guess the ID
- [ ] Object-level checks happen in `check_object_permissions()` — not ad-hoc `if obj.owner != request.user`
- [ ] Authorization failures return `403 Forbidden` — not `404` (unless intentionally hiding existence)
- [ ] Authorization logic is **unit tested independently** — not only tested through full API integration tests

## 5.7 Role-Based Access Control (RBAC)

- [ ] Roles are defined as an **enum or `TextChoices`** — not bare strings scattered in permission checks
- [ ] Role assignments are stored in the database — not hardcoded or derived from username patterns
- [ ] Permissions are **attached to roles**, not directly to users (users get permissions via roles)
- [ ] A user can hold **multiple roles** if the domain requires it — not a single-role constraint
- [ ] Role hierarchy is explicit — if `admin` implies `editor` permissions, this is coded, not assumed
- [ ] Roles are checked via **dedicated permission classes** — not `if user.role == 'admin':` in views
- [ ] **Superuser** access is separate from application-level roles — Django's `is_superuser` is for admin only
- [ ] Role changes take effect **immediately** — no stale role cached in JWT payload beyond token lifetime
- [ ] Role escalation requires **re-authentication** or explicit approval — not just a profile update

## 5.8 Permission Classes

- [ ] All custom permission classes inherit from `BasePermission`
- [ ] `has_permission()` handles **request-level** checks (is the user authenticated? do they have the right role?)
- [ ] `has_object_permission()` handles **object-level** checks (does this user own this specific record?)
- [ ] Permission classes have a descriptive **`message`** attribute — not the generic DRF default
- [ ] Permission classes are **composable** — combined via `AND` (`&`) and `OR` (`|`) operators where needed
- [ ] Permission classes are **stateless** — no instance state modified during a request
- [ ] Permission classes do **not** hit the database unless absolutely necessary — avoid N+1 in permission checks
- [ ] Permission classes are in a dedicated `permissions.py` file per app — not defined inside `views.py`
- [ ] Every permission class has **unit tests** covering both allowed and denied cases

## 5.9 Data Scoping & Tenant Isolation

- [ ] **Multi-tenant data** is isolated at the queryset level — never relying on client-provided tenant ID alone
- [ ] Tenant context is derived from the **authenticated user** — not from a request parameter that can be spoofed
- [ ] `get_queryset()` always filters by the current user's organization/tenant
- [ ] No endpoint accidentally returns **cross-tenant data** — tested explicitly in the test suite
- [ ] Admin endpoints that access all tenant data are clearly separated and require explicit admin role
- [ ] Row-level security (RLS) is considered for highly sensitive multi-tenant data at the DB level
- [ ] Bulk operations (update, delete) scope to the authenticated user's tenant — no accidental cross-tenant bulk ops

## 5.10 Sensitive Endpoint Protection

- [ ] **Admin endpoints** require both authentication and explicit admin permission
- [ ] `/admin/` Django admin is not served on the default path in production — moved or blocked
- [ ] Django admin has **extra authentication** — 2FA or IP whitelist in production
- [ ] **Financial, PII, and destructive endpoints** have stricter rate limiting than regular endpoints
- [ ] **Audit logging** is in place for all sensitive operations — who did what, when, on which record
- [ ] Bulk delete and bulk update endpoints require **explicit confirmation parameter** — no accidental mass operations
- [ ] Internal service-to-service endpoints are protected by **API keys or mTLS** — not open internally
- [ ] Debug endpoints (`/debug/`, `/__debug__/`) are completely absent in production builds

## 5.11 CSRF Protection

- [ ] CSRF protection is **enabled** for all session-based endpoints — `CsrfViewMiddleware` is active
- [ ] CSRF is **not disabled globally** — only for explicitly JWT-authenticated API endpoints where it's safe to do so
- [ ] `@csrf_exempt` is never used on sensitive endpoints — documented exceptions only
- [ ] CSRF tokens are correctly sent for browser-based session flows
- [ ] `CSRF_COOKIE_SECURE = True` in production
- [ ] `CSRF_COOKIE_HTTPONLY = False` — correctly set so JavaScript can read and send it
- [ ] `CSRF_TRUSTED_ORIGINS` is explicitly configured for cross-origin form submissions

## 5.12 Audit Logging

- [ ] All **authentication events** are logged — login, logout, failed login, token refresh
- [ ] All **authorization failures** are logged — who attempted what on which resource
- [ ] All **sensitive data mutations** are logged — create, update, delete on critical models
- [ ] Audit logs include: `timestamp`, `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `result`
- [ ] Audit logs are **immutable** — written to append-only storage, not updatable
- [ ] Audit logs are **separate** from application logs — not mixed into the same log stream
- [ ] Failed login attempts trigger **account lockout** after a configurable threshold
- [ ] Account lockout events are logged and optionally alert the account owner via email

## 5.13 Token Storage & Transport Security

- [ ] Refresh tokens are stored in **HttpOnly cookies** for web clients — not in localStorage (XSS risk)
- [ ] Access tokens are stored **in memory only** (JavaScript variable) — not in localStorage or sessionStorage
- [ ] Refresh token cookies have `Secure`, `HttpOnly`, `SameSite=Lax` flags set
- [ ] Token cookies have a `Path` attribute set to the refresh endpoint path only — not `/`
- [ ] Tokens are **never included in URLs** — not in query parameters, redirects, or Referer headers
- [ ] Token payload does not contain sensitive data that could be read via base64 decoding
- [ ] Cross-origin token handling (CORS) is configured to only allow specific origins
- [ ] Mobile clients use **secure storage** (Keychain/Keystore) — not plain SharedPreferences/UserDefaults

## 5.14 Account Security & Lifecycle

- [ ] **Email verification** is required before full account access
- [ ] Email verification uses a **time-limited, single-use token** — not a permanent link
- [ ] **Account deactivation** revokes all active sessions and tokens immediately
- [ ] **Account deletion** (if supported) is soft-delete with a grace period before permanent removal
- [ ] Session listing endpoint exists — users can see active sessions/devices
- [ ] Session revocation is possible — users can logout individual sessions remotely
- [ ] **Maximum concurrent sessions** limit is enforced if security policy requires it
- [ ] Password change forces re-authentication on all other sessions
- [ ] Suspicious activity (new device, new location) triggers additional verification or notification
