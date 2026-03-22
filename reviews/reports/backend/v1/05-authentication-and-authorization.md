# 05 — Authentication & Authorization Report

**Date**: 2026-03-13 (updated)
**Auditor**: Claude Code (automated)
**Scope**: Backend authentication, JWT, OAuth, passwords, RBAC, permissions, CSRF, audit logging, token security, account lifecycle
**Settings reviewed**: `base.py`, `local.py`, `local_docker.py`, `production.py`
**Grade**: **A-** (14 PASS / 0 FAIL, 4 warnings across 14 sections)

---

## Grading Rubric

| Grade | Criteria |
|-------|----------|
| A | 0 FAIL, <= 3 WARN |
| A- | 0 FAIL, <= 6 WARN |
| B+ | <= 1 security FAIL, <= 8 WARN |
| B | <= 2 FAIL, <= 12 WARN |
| B- | <= 3 FAIL or 1 critical security FAIL |

---

## Executive Summary

The authentication and authorization system is **well-architected** with strong fundamentals: custom JWT with PyJWT (15-min access / 7-day refresh), Redis-backed JTI blacklisting, refresh token rotation with reuse detection, comprehensive RBAC with database-stored roles and explicit level hierarchy, policy-based authorization, and immutable audit logging.

Both prior FAIL findings have been resolved: (1) OAuth `redirect_to` is now validated against an origin allowlist (`ALLOWED_REDIRECT_ORIGINS`), and (2) account deactivation now calls `AuthService.logout_all()` to revoke all sessions/tokens. Additionally, 7 WARN findings have been fixed: Argon2 password hashing, consistent session revocation on password change, 403 audit logging, OAuth email verification guard, dedicated JWT secret, explicit session cookie SameSite, and CSRF trusted origins.

---

## Section Results

| # | Section | Verdict | Rules | Findings |
|---|---------|---------|-------|----------|
| 5.1 | Authentication Architecture | **PASS** | 8/8 | — |
| 5.2 | JWT Implementation | **PASS** | 13/13 | — |
| 5.3 | Session Authentication | **PASS** | 8/8 | — |
| 5.4 | OAuth2 / Social Authentication | **PASS** | 7/7 | 1 WARN |
| 5.5 | Password Management | **PASS** | 11/11 | — |
| 5.6 | Authorization Architecture | **PASS** | 8/8 | — |
| 5.7 | Role-Based Access Control | **PASS** | 9/9 | 1 INFO |
| 5.8 | Permission Classes | **PASS** | 9/9 | — |
| 5.9 | Data Scoping & Tenant Isolation | **PASS** | 7/7 | — |
| 5.10 | Sensitive Endpoint Protection | **PASS** | 8/8 | 2 WARN |
| 5.11 | CSRF Protection | **PASS** | 7/7 | — |
| 5.12 | Audit Logging | **PASS** | 8/8 | 1 WARN |
| 5.13 | Token Storage & Transport Security | **PASS** | 8/8 | 1 INFO |
| 5.14 | Account Security & Lifecycle | **PASS** | 9/9 | — |

**Totals**: 119 rules evaluated / 0 FAIL / 4 WARN / 2 INFO

---

## FAIL Findings

None. Both prior FAILs have been fixed (see Update Log below).

---

## WARN Findings

### MEDIUM Priority

| ID | Finding | File(s) | Impact |
|----|---------|---------|--------|
| W4 | No account lockout for failed login attempts. Only IP-based rate limit (5/min). | `apps/auth/views.py:182`, `settings/base.py:225` | Distributed attacker could bypass IP rate limit. |
| W5 | OAuth provider tokens stored in plaintext. Comment says "encrypted in production via custom field if needed" but no encryption implemented. | `apps/auth/models.py:441-442` | Provider tokens readable in DB. Mitigated: only used during initial OAuth flow. |

### LOW Priority

| ID | Finding | File(s) | Impact |
|----|---------|---------|--------|
| W10 | Django admin at default `/admin/` path in production. | `backend_core/urls.py:8` | Discoverable by automated scanners. |
| W11 | No additional admin authentication (2FA, IP restriction) in production. | `settings/production.py` | Admin relies on username/password only. |

### INFO (Intentional / Acceptable)

| ID | Finding | File(s) | Notes |
|----|---------|---------|-------|
| W9 | `is_superuser` grants app permissions | `policies.py` | Intentional platform admin bypass mechanism. Documented. |
| W12 | Refresh cookie path `/api/` | `apps/auth/views.py:162` | Narrower than `/` — acceptable defense-in-depth. |

---

## Detailed Section Audits

### 5.1 Authentication Architecture — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.1.1 | Auth strategy documented | PASS | Documented in `settings/base.py:241-270`, `apps/auth/CLAUDE.md`, `.claude/CLAUDE.md` |
| 5.1.2 | JWT+session without documented reason | PASS | Only `JWTAuthentication` in `DEFAULT_AUTHENTICATION_CLASSES`. Session middleware exists for Django admin only |
| 5.1.3 | Auth classes set globally | PASS | `base.py:187-189`: `['apps.auth.authentication.JWTAuthentication']` |
| 5.1.4 | >3 views override auth classes | PASS | Only 3 overrides, all in test files |
| 5.1.5 | Public endpoints lack AllowAny | PASS | All public auth endpoints explicitly set `permission_classes = [AllowAny]` (12 views) |
| 5.1.6 | Auth logic inline in views | PASS | All auth logic in `JWTAuthentication` class and `AuthService` |
| 5.1.7 | Auth endpoints scattered | PASS | All under `/api/v1/auth/` |
| 5.1.8 | No integration tests | PASS | `tests/api_integration/test_phase_01_auth.py` + `apps/auth/tests/test_views.py` |

### 5.2 JWT Implementation — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.2.1 | JWT fully hand-rolled | PASS | Uses PyJWT library (`apps/core/utils/jwt.py:44`) |
| 5.2.2 | Access token > 1 hour | PASS | 15 minutes (`base.py:446`) |
| 5.2.3 | Refresh token > 30 days | PASS | 7 days (`base.py:447`) |
| 5.2.4 | Algorithm is `none` | PASS | HS256 with `ALLOWED_ALGORITHMS = ["HS256"]` preventing confusion attacks |
| 5.2.5 | Uses SECRET_KEY for signing | PASS | **FIXED** — Dedicated `JWT_SECRET_KEY` setting (`base.py:451`), used in `jwt.py:103,148` |
| 5.2.6 | Payload contains sensitive PII | PASS | Only `user_id`, `jti`, `email`, `is_verified`, `token_type` |
| 5.2.7 | No refresh rotation | PASS | Full rotation with `replaced_by` chain tracking and replay detection |
| 5.2.8 | No blacklisting | PASS | `RefreshToken.is_revoked` in DB + `JTIBlacklist` in Redis |
| 5.2.9 | Blacklist in-memory only | PASS | Redis-backed (`blacklist.py:53-66`) |
| 5.2.10 | No `jti` claim | PASS | JTI in both access and refresh tokens, checked on every validation |
| 5.2.11 | `exp` not validated | PASS | PyJWT `verify_exp=True` + DB-level expiration check |
| 5.2.12 | Tokens in URL params | PASS | Authorization header + HttpOnly cookie. OAuth uses fragments (not query params) |
| 5.2.13 | Tokens in logs | PASS | Only `user_id`, `token_id`, `state_hash` logged — never raw tokens |

### 5.3 Session Authentication — PASS

Sessions are secondary (admin-only). API uses JWT.

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.3.1 | SESSION_COOKIE_SECURE False in prod | PASS | `production.py:70`: `True` |
| 5.3.2 | SESSION_COOKIE_HTTPONLY False | PASS | `production.py:73`: `True` |
| 5.3.3 | SESSION_COOKIE_SAMESITE not set | PASS | **FIXED** — `production.py:74`: `SESSION_COOKIE_SAMESITE = "Lax"` |
| 5.3.4 | SESSION_COOKIE_AGE at default | PASS | `production.py:167`: 86400 (1 day) |
| 5.3.5 | SESSION_EXPIRE_AT_BROWSER_CLOSE | INFO | Not set. Acceptable for admin-only sessions |
| 5.3.6 | Session backend DB/cookie | PASS | Redis-backed cache in production (`production.py:165`) |
| 5.3.7 | Session ID not regenerated | N/A | Sessions used for Django admin only (built-in cycle_key) |
| 5.3.8 | Logout doesn't flush | N/A | API uses JWT logout (token revocation + JTI blacklisting) |

### 5.4 OAuth2 / Social Authentication — PASS (1 WARN)

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.4.1 | OAuth fully hand-rolled | PASS | Uses PyJWT + google-auth library + Apple public key verification |
| 5.4.2 | State not validated | PASS | `validate_and_consume_state()` with one-time use + 10-min TTL + PKCE |
| 5.4.3 | Provider tokens plaintext | **WARN** | `OAuthConnection.access_token` is `TextField` — no encryption (W5) |
| 5.4.4 | Excessive scopes | PASS | Google: `openid email profile`. Apple: `name email` |
| 5.4.5 | Callback allows open redirect | PASS | **FIXED** — `OAuthInitSerializer.validate_redirect_to()` validates against `ALLOWED_REDIRECT_ORIGINS` |
| 5.4.6 | Account takeover via unverified email | PASS | **FIXED** — `oauth_service.py:241-252`: blocks linking when `email_verified=False`, raises `OAuthError` |
| 5.4.7 | Token refresh failure unhandled | INFO | No provider token refresh logic. Low risk: tokens only used during initial flow |

### 5.5 Password Management — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.5.1 | MD5/SHA1/unsalted hashing | PASS | Argon2 primary hasher with PBKDF2 fallback |
| 5.5.2 | Not Argon2/bcrypt primary | PASS | **FIXED** — `PASSWORD_HASHERS` configured with `Argon2PasswordHasher` first (`base.py:165-171`). `argon2-cffi` in requirements |
| 5.5.3 | Min length < 8 | PASS | `MinimumLengthValidator` with 8 + serializer `min_length=8` |
| 5.5.4 | AUTH_PASSWORD_VALIDATORS empty | PASS | 4 validators configured (`base.py:147-163`) |
| 5.5.5 | CommonPasswordValidator missing | PASS | Present in validator list |
| 5.5.6 | Reset tokens reusable/permanent | PASS | Single-use + 1-hour expiry. `mark_used()` on consumption |
| 5.5.7 | PASSWORD_RESET_TIMEOUT > 24h | PASS | Custom model with 1-hour expiry |
| 5.5.8 | Change doesn't require old password | PASS | `change_password()` verifies `current_password` |
| 5.5.9 | Change doesn't invalidate sessions | PASS | **FIXED** — `change_password()` now calls `AuthService.logout_all()` (matches `confirm_reset` behavior) |
| 5.5.10 | Passwords in API response | PASS | No password in any output serializer |
| 5.5.11 | Password fields lack write_only | PASS | All password fields have `write_only=True` |

### 5.6 Authorization Architecture — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.6.1 | Strategy not documented | PASS | Extensive docs in `docs/plans/` and `docs/implementations/` |
| 5.6.2 | Inline `if user.role ==` in views | PASS | Zero inline role checks — all via policy classes |
| 5.6.3 | Auth logic in models | PASS | Models are data-only; authorization in `policies.py` files |
| 5.6.4 | Object-level only, no queryset scoping | PASS | `TransactionListView.get_queryset()` scopes by user + membership |
| 5.6.5 | Scoping not in get_queryset() | PASS | Selector layer provides user-scoped queries |
| 5.6.6 | Manual ownership instead of framework | PASS | `MembershipSelector` + `PermissionSelector` for all checks |
| 5.6.7 | Auth failures return 404 undocumented | PASS | Distinct `PermissionDenied` (403) vs `NotFound` (404) |
| 5.6.8 | No auth unit tests | PASS | 361 RBAC tests + `test_policies.py` per app |

### 5.7 Role-Based Access Control — PASS (1 INFO)

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.7.1 | Bare string roles | PASS | `TextChoices` enums for types/statuses; DB-stored `Role` model with `level` |
| 5.7.2 | Hardcoded role assignments | PASS | DB-stored via `Role` model + `Membership` FK |
| 5.7.3 | Permissions on users, not roles | PASS | `Permission -> RolePermission -> Role -> Membership -> User` |
| 5.7.4 | Single role only | PASS | Multiple memberships across accounts (one per account) |
| 5.7.5 | Implicit role hierarchy | PASS | Explicit `level` field (0=owner..10=lowest) + coded dominance rule |
| 5.7.6 | Inline role checks in views | PASS | Zero inline checks — all via policy classes |
| 5.7.7 | is_superuser grants app permissions | **INFO** | `BusinessPolicy`/`PlatformPolicy` use `is_superuser` for platform admin bypass — intentional |
| 5.7.8 | Stale roles in JWT | PASS | No role data in JWT — resolved fresh from DB per request |
| 5.7.9 | Role escalation without approval | PASS | `MembershipPolicy` enforces dominance rule + `can_change_member_role` |

### 5.8 Permission Classes — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.8.1 | Not inheriting BasePermission | PASS | All 11 classes inherit from `BasePermission` |
| 5.8.2 | has_permission() for request checks | PASS | All implement `has_permission()` |
| 5.8.3 | has_object_permission() for object checks | PASS | `IsOwner`, `IsOwnerOrStaff`, `IsOwnerOrReadOnly` implement it |
| 5.8.4 | Generic DRF message | PASS | All have custom `message` attributes |
| 5.8.5 | AND/OR composition | INFO | DRF native AND + policy classes for complex rules |
| 5.8.6 | Modifies instance state | PASS | All read-only — no mutations |
| 5.8.7 | N+1 DB queries | PASS | Zero DB queries in permission classes — all in-memory attributes |
| 5.8.8 | Defined in views.py | PASS | All in `apps/core/permissions/base.py` |
| 5.8.9 | No unit tests | PASS | `test_permissions.py` with 130 test functions covering all classes |

### 5.9 Data Scoping & Tenant Isolation — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.9.1 | Client-provided tenant ID unverified | PASS | Always verified via `MembershipSelector.get_active_membership_for_user_account()` |
| 5.9.2 | Tenant from request, not user | PASS | All tenant context validated against `request.user` membership |
| 5.9.3 | get_queryset() doesn't filter by org | PASS | `TransactionListView` scopes by user_id + membership verification |
| 5.9.4 | Cross-tenant data to non-admin | PASS | All account-scoped views verify membership before returning data |
| 5.9.5 | Admin endpoints lack admin permission | PASS | Staff operations gated by policy (`can_suspend`, `can_reactivate`) |
| 5.9.6 | No row-level security | INFO | Application-layer enforcement via RBAC. Acceptable |
| 5.9.7 | Bulk ops don't scope | N/A | No bulk operations exist |

### 5.10 Sensitive Endpoint Protection — PASS (2 WARN)

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.10.1 | Admin endpoints unauth | PASS | Django admin + all CMS/RBAC admin views require `IsAuthenticated` |
| 5.10.2 | Admin on default `/admin/` | **WARN** | Default path in production (W10) |
| 5.10.3 | Admin lacks extra auth | **WARN** | No 2FA or IP restriction (W11) |
| 5.10.4 | Same rate limits everywhere | PASS | Dedicated throttles: login 5/min, password_reset 3/hr, verification 5/min |
| 5.10.5 | No audit logging | PASS | 80+ audit action types, used across all services |
| 5.10.6 | Bulk destructive without confirmation | N/A | No bulk operations |
| 5.10.7 | Internal endpoints unauthenticated | PASS | CMS via API key + origin check. SES webhook via SNS signature verification |
| 5.10.8 | Debug endpoints in production | PASS | `DEBUG=False` enforced by assertion. Debug toolbar conditional on dev |

### 5.11 CSRF Protection — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.11.1 | CsrfViewMiddleware missing | PASS | Present in MIDDLEWARE (`base.py:111`) |
| 5.11.2 | CSRF disabled globally | PASS | Middleware active. API uses JWT (naturally exempt) |
| 5.11.3 | @csrf_exempt on login/reset | PASS | Only on SES webhook (`email/webhooks.py:67`) — machine-to-machine |
| 5.11.4 | CSRF tokens not sent for session flows | PASS | API uses JWT, not session auth. Admin protected by middleware |
| 5.11.5 | CSRF_COOKIE_SECURE False | PASS | `production.py:71`: `True` |
| 5.11.6 | CSRF_COOKIE_HTTPONLY True | PASS | Set to `True`. API uses JWT — no JS CSRF read needed |
| 5.11.7 | CSRF_TRUSTED_ORIGINS not set | PASS | **FIXED** — `production.py:185-189`: `CSRF_TRUSTED_ORIGINS` from env (defaults to `CORS_ALLOWED_ORIGINS`) |

### 5.12 Audit Logging — PASS (1 WARN)

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.12.1 | Auth events not logged | PASS | `LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGOUT`, `ALL_SESSIONS_REVOKED` all logged |
| 5.12.2 | Auth failures not logged | PASS | **FIXED** — `AUTHORIZATION_DENIED` action + `_audit_log_authorization_denied()` in exception handler logs all 403s |
| 5.12.3 | No audit trail for mutations | PASS | 80+ action types across all domain services |
| 5.12.4 | Audit lacks required fields | PASS | `actor_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent` |
| 5.12.5 | Audit logs mutable | PASS | `save()` and `delete()` raise `ValueError`. Admin read-only |
| 5.12.6 | Audit mixed into app logs | PASS | Separate `audit_log` DB table + `AuditService.log()` vs `get_logger()` |
| 5.12.7 | No account lockout | **WARN** | Only IP-based rate limit (5/min). No per-account lockout counter (W4) |
| 5.12.8 | Lockout doesn't notify | INFO | No lockout mechanism. New device login sends notification |

### 5.13 Token Storage & Transport Security — PASS (1 INFO)

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.13.1 | Refresh in localStorage | PASS | HttpOnly cookie. Comment: "TOKEN STORE (in-memory only)" |
| 5.13.2 | Access in localStorage | PASS | In-memory variable only (`let accessToken: string | null = null`) |
| 5.13.3 | Refresh cookie lacks flags | PASS | `httponly=True`, `secure=!DEBUG`, `samesite="Strict"` (configurable) |
| 5.13.4 | Cookie path is `/` | **INFO** | Path is `/api/` — broader than ideal `/api/v1/auth/refresh/` but narrower than `/`. Acceptable. |
| 5.13.5 | Tokens in URL/Referer | PASS | OAuth uses fragments (not query params). API uses headers + cookies |
| 5.13.6 | JWT payload has sensitive data | PASS | Only `user_id`, `jti`, `email`, `is_verified`, `token_type` |
| 5.13.7 | CORS not origin-specific | PASS | `CORS_ALLOWED_ORIGINS` from env. Empty default (nothing allowed) |
| 5.13.8 | Mobile lacks secure storage | INFO | Mobile app is "planned". No implementation to verify yet |

### 5.14 Account Security & Lifecycle — PASS

| ID | Rule | Result | Evidence |
|----|------|--------|----------|
| 5.14.1 | Email verification not required | INFO | Users can log in unverified. Documented — verification gates business creation |
| 5.14.2 | Verification tokens permanent/reusable | PASS | 15-min expiry, single-use, old tokens invalidated on new creation |
| 5.14.3 | Deactivation doesn't revoke sessions | PASS | **FIXED** — `deactivate_user()` now calls `AuthService.logout_all()` (`users/services.py:558`) |
| 5.14.4 | Hard delete without grace period | PASS | DELETE endpoint calls `deactivate_user()` (soft delete) |
| 5.14.5 | No session listing | PASS | `GET /api/v1/auth/sessions/` returns active sessions |
| 5.14.6 | Can't revoke individual sessions | PASS | `DELETE /api/v1/auth/sessions/<pk>/` revokes token + blacklists JTI |
| 5.14.7 | No max concurrent sessions | INFO | `AUTH_MAX_SESSIONS_PER_USER = 5` with active enforcement |
| 5.14.8 | Password change doesn't force re-auth | PASS | **FIXED** — `change_password()` now calls `AuthService.logout_all()` (matches `confirm_reset`) |
| 5.14.9 | No suspicious activity detection | INFO | Token reuse detection triggers `logout_all`. New device notifications |

---

## Positive Highlights

1. **Token rotation with reuse detection**: Refresh token rotation tracks `replaced_by` chain. If a revoked or already-rotated token is reused, `logout_all()` is triggered as a security measure
2. **Redis-backed JTI blacklist**: Immediate access token revocation without DB queries on every request
3. **PKCE on OAuth flows**: Both Google and Apple OAuth include PKCE code challenge/verifier
4. **Refresh token stored as SHA-256 hash**: Raw refresh tokens never stored in database
5. **Immutable audit logs**: `save()` and `delete()` raise `ValueError`. Admin blocks add/change/delete
6. **3-layer authorization**: DRF permission classes (gate) -> RBAC membership (tenant boundary) -> Domain policies (business rules)
7. **No roles in JWT**: RBAC resolved fresh from DB per request — role changes take effect immediately
8. **Session management**: Full lifecycle (list, revoke individual, max limit enforcement, device tracking)
9. **Comprehensive rate limiting**: Dedicated throttles for login (5/min), password reset (3/hr), verification (5/min), refresh (30/min)
10. **Argon2 password hashing**: Primary hasher with PBKDF2 fallback for seamless migration
11. **OAuth redirect validation**: `redirect_to` validated against `ALLOWED_REDIRECT_ORIGINS` allowlist
12. **403 audit trail**: All authorization denials logged with `AUTHORIZATION_DENIED` action, view, method, and path

---

## Remaining Remediation

### Should Fix (Future Sprint)

| # | Finding | Effort | Risk |
|---|---------|--------|------|
| W4 | Add per-account lockout counter (3-5 failures -> temporary lock) | Medium | MEDIUM |
| W5 | Encrypt OAuth provider tokens at rest | Medium | LOW |

### Nice to Have

| # | Finding | Effort | Risk |
|---|---------|--------|------|
| W10 | Move admin to non-default path | Trivial | LOW |
| W11 | Add 2FA or IP restriction for admin panel | Medium | LOW |

---

## Update Log

### 2026-03-13: B+ → A- (9 fixes applied)

**Changes made:**

| ID | Fix | Files Modified |
|----|-----|----------------|
| **F1** (FAIL → PASS) | OAuth `redirect_to` validated against `ALLOWED_REDIRECT_ORIGINS` allowlist | `apps/auth/serializers.py` (added `validate_redirect_to()`), `settings/base.py` (added `ALLOWED_REDIRECT_ORIGINS`) |
| **F2** (FAIL → PASS) | Account deactivation now calls `AuthService.logout_all()` | `apps/users/services.py:558` |
| **W1** (WARN → PASS) | Added `PASSWORD_HASHERS` with Argon2 primary + fixed misleading docstrings | `settings/base.py:165-171`, `requirements/base.txt` (argon2-cffi), `apps/core/utils/password.py` |
| **W2** (WARN → PASS) | `change_password()` now uses `AuthService.logout_all()` instead of raw JTI blacklist | `apps/auth/services/password_service.py:301-302` |
| **W3** (WARN → PASS) | 403 responses now audit-logged with `AUTHORIZATION_DENIED` action | `apps/core/observability/audit/models.py`, `apps/core/exceptions/handler.py` |
| **W6** (WARN → PASS) | OAuth account linking blocked when provider email is unverified | `apps/auth/services/oauth_service.py:241-252` |
| **W7** (WARN → PASS) | Dedicated `JWT_SECRET_KEY` setting (falls back to `SECRET_KEY`) | `settings/base.py:451`, `apps/core/utils/jwt.py:103,148` |
| **W8** (WARN → PASS) | Explicit `SESSION_COOKIE_SAMESITE = "Lax"` in production | `settings/production.py:74` |
| **W13** (WARN → PASS) | `CSRF_TRUSTED_ORIGINS` set from env (defaults to CORS origins) | `settings/production.py:185-189` |
| **W9** (WARN → INFO) | Downgraded — `is_superuser` bypass is intentional for platform admin | No code change |
| **W12** (WARN → INFO) | Downgraded — cookie path `/api/` is narrower than `/`, acceptable | No code change |

**Test impact:** Updated `test_google_oauth_init_with_redirect` (redirect URL now uses allowed origin) and `test_deactivate_user_logs_audit` (expects 2 audit calls: deactivation + session revocation). All 3568 unit tests pass.
