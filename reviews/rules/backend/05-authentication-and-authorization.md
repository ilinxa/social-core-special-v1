# 05 — Authentication & Authorization Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 5.1 Authentication Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 5.1.1 | WARN if authentication strategy is not documented anywhere (README, docs, settings comments) | PASS/WARN |
| 5.1.2 | WARN if JWT and session auth are both active without documented reason | PASS/WARN |
| 5.1.3 | FAIL if authentication classes are not set globally in REST_FRAMEWORK settings | PASS/FAIL |
| 5.1.4 | WARN if more than 3 views override authentication_classes without comments | PASS/WARN |
| 5.1.5 | FAIL if any public endpoint lacks explicit `AllowAny` or equivalent — relies on missing auth class | PASS/FAIL |
| 5.1.6 | FAIL if authentication logic is inline in views instead of dedicated auth classes | PASS/FAIL |
| 5.1.7 | WARN if auth endpoints are scattered across multiple URL prefixes | PASS/WARN |
| 5.1.8 | WARN if no integration tests exist for authentication flows | PASS/WARN |

## 5.2 JWT Implementation

| ID | Rule | Verdict |
|----|------|---------|
| 5.2.1 | WARN if JWT is fully hand-rolled with no standard library dependency | PASS/WARN |
| 5.2.2 | FAIL if access token lifetime exceeds 1 hour | PASS/FAIL |
| 5.2.3 | WARN if refresh token lifetime exceeds 30 days | PASS/WARN |
| 5.2.4 | FAIL if JWT algorithm is `none` or unsecured | PASS/FAIL |
| 5.2.5 | WARN if JWT signing uses Django's SECRET_KEY directly (not a dedicated JWT secret) | PASS/WARN |
| 5.2.6 | FAIL if JWT payload contains passwords, credit cards, SSN, or other sensitive PII | PASS/FAIL |
| 5.2.7 | WARN if refresh token rotation is not enabled (same refresh token reused indefinitely) | PASS/WARN |
| 5.2.8 | FAIL if refresh token blacklisting is not implemented (revoked tokens can be reused) | PASS/FAIL |
| 5.2.9 | FAIL if token blacklist is in-memory only (lost on restart, not shared across workers) | PASS/FAIL |
| 5.2.10 | WARN if no `jti` claim exists for per-token revocation | PASS/WARN |
| 5.2.11 | FAIL if `exp` claim is not validated on token verification | PASS/FAIL |
| 5.2.12 | FAIL if tokens are transmitted via URL query parameters | PASS/FAIL |
| 5.2.13 | FAIL if tokens appear in log output or error tracking payloads | PASS/FAIL |

## 5.3 Session Authentication

| ID | Rule | Verdict |
|----|------|---------|
| 5.3.1 | FAIL if `SESSION_COOKIE_SECURE` is False in production when sessions are used | PASS/FAIL |
| 5.3.2 | FAIL if `SESSION_COOKIE_HTTPONLY` is False when sessions are used | PASS/FAIL |
| 5.3.3 | WARN if `SESSION_COOKIE_SAMESITE` is not set to `Lax` or `Strict` | PASS/WARN |
| 5.3.4 | WARN if SESSION_COOKIE_AGE is left at Django default (2 weeks) for sensitive apps | PASS/WARN |
| 5.3.5 | INFO if SESSION_EXPIRE_AT_BROWSER_CLOSE is not set — depends on security requirements | PASS/INFO |
| 5.3.6 | WARN if session backend uses DB or cookie instead of Redis/cache | PASS/WARN |
| 5.3.7 | WARN if session ID is not regenerated on login | PASS/WARN |
| 5.3.8 | FAIL if logout does not flush the session server-side | PASS/FAIL |

## 5.4 OAuth2 / Social Authentication

| ID | Rule | Verdict |
|----|------|---------|
| 5.4.1 | WARN if OAuth flow is completely hand-rolled with no standard library | PASS/WARN |
| 5.4.2 | FAIL if OAuth `state` parameter is not validated on callback | PASS/FAIL |
| 5.4.3 | WARN if provider access/refresh tokens are stored in plaintext | PASS/WARN |
| 5.4.4 | WARN if OAuth scopes requested exceed what the app needs | PASS/WARN |
| 5.4.5 | FAIL if OAuth callback URL allows open redirects | PASS/FAIL |
| 5.4.6 | FAIL if social login allows account takeover via unverified email match | PASS/FAIL |
| 5.4.7 | WARN if provider token refresh failure is not handled gracefully | PASS/WARN |

## 5.5 Password Management

| ID | Rule | Verdict |
|----|------|---------|
| 5.5.1 | FAIL if passwords use MD5, SHA1, or unsalted hashing | PASS/FAIL |
| 5.5.2 | WARN if Argon2 or bcrypt is not the primary password hasher | PASS/WARN |
| 5.5.3 | FAIL if password minimum length is less than 8 characters | PASS/FAIL |
| 5.5.4 | FAIL if AUTH_PASSWORD_VALIDATORS is empty or not configured | PASS/FAIL |
| 5.5.5 | WARN if CommonPasswordValidator is not enabled | PASS/WARN |
| 5.5.6 | FAIL if password reset tokens are reusable or permanent | PASS/FAIL |
| 5.5.7 | WARN if PASSWORD_RESET_TIMEOUT exceeds 24 hours | PASS/WARN |
| 5.5.8 | WARN if password change does not require old password | PASS/WARN |
| 5.5.9 | WARN if password change does not invalidate existing sessions/tokens | PASS/WARN |
| 5.5.10 | FAIL if passwords appear in any API response | PASS/FAIL |
| 5.5.11 | FAIL if password serializer fields lack `write_only=True` | PASS/FAIL |

## 5.6 Authorization Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 5.6.1 | WARN if authorization strategy is not documented | PASS/WARN |
| 5.6.2 | FAIL if authorization logic (`if user.role ==`) exists inside view methods | PASS/FAIL |
| 5.6.3 | FAIL if authorization logic exists inside model methods | PASS/FAIL |
| 5.6.4 | WARN if authorization is only at object level without queryset scoping | PASS/WARN |
| 5.6.5 | WARN if queryset scoping is not in get_queryset() for list views | PASS/WARN |
| 5.6.6 | WARN if object-level checks use manual ownership comparison instead of permission framework | PASS/WARN |
| 5.6.7 | WARN if authorization failures return 404 without documented reason for hiding existence | PASS/WARN |
| 5.6.8 | WARN if authorization logic has no dedicated unit tests | PASS/WARN |

## 5.7 Role-Based Access Control (RBAC)

| ID | Rule | Verdict |
|----|------|---------|
| 5.7.1 | WARN if roles are bare strings without enum/TextChoices definition | PASS/WARN |
| 5.7.2 | FAIL if role assignments are hardcoded instead of database-stored | PASS/FAIL |
| 5.7.3 | WARN if permissions are attached directly to users instead of through roles | PASS/WARN |
| 5.7.4 | INFO if users can only hold one role — acceptable if domain requires it | PASS/INFO |
| 5.7.5 | WARN if role hierarchy is implicit (assumed, not coded) | PASS/WARN |
| 5.7.6 | FAIL if role checks are inline in views instead of permission classes/policies | PASS/FAIL |
| 5.7.7 | WARN if is_superuser grants application-level permissions instead of only Django admin | PASS/WARN |
| 5.7.8 | WARN if stale roles in JWT payload could grant access beyond token lifetime | PASS/WARN |
| 5.7.9 | WARN if role escalation (e.g. member→admin) requires no approval flow | PASS/WARN |

## 5.8 Permission Classes

| ID | Rule | Verdict |
|----|------|---------|
| 5.8.1 | FAIL if custom permission classes don't inherit from BasePermission | PASS/FAIL |
| 5.8.2 | PASS if has_permission() handles request-level checks | PASS |
| 5.8.3 | PASS if has_object_permission() handles object-level checks | PASS |
| 5.8.4 | WARN if permission classes use the generic DRF message instead of custom message | PASS/WARN |
| 5.8.5 | INFO if permission classes don't support AND/OR composition — only needed for complex rules | PASS/INFO |
| 5.8.6 | FAIL if permission class modifies instance state during a request | PASS/FAIL |
| 5.8.7 | WARN if permission classes make DB queries that could cause N+1 | PASS/WARN |
| 5.8.8 | WARN if permission classes are defined inside views.py instead of permissions.py | PASS/WARN |
| 5.8.9 | WARN if permission classes lack unit tests for allowed and denied cases | PASS/WARN |

## 5.9 Data Scoping & Tenant Isolation

| ID | Rule | Verdict |
|----|------|---------|
| 5.9.1 | FAIL if multi-tenant data relies solely on client-provided tenant ID without verification | PASS/FAIL |
| 5.9.2 | FAIL if tenant context comes from a request parameter instead of the authenticated user | PASS/FAIL |
| 5.9.3 | WARN if get_queryset() does not filter by user's organization in multi-tenant list views | PASS/WARN |
| 5.9.4 | FAIL if any endpoint returns cross-tenant data to non-admin users | PASS/FAIL |
| 5.9.5 | WARN if admin endpoints accessing all tenants don't require explicit admin permission | PASS/WARN |
| 5.9.6 | INFO if row-level security is not implemented — only relevant for highly sensitive data | PASS/INFO |
| 5.9.7 | WARN if bulk operations don't scope to the authenticated user's tenant | PASS/WARN |

## 5.10 Sensitive Endpoint Protection

| ID | Rule | Verdict |
|----|------|---------|
| 5.10.1 | FAIL if admin endpoints are accessible without authentication | PASS/FAIL |
| 5.10.2 | WARN if `/admin/` is on the default path in production | PASS/WARN |
| 5.10.3 | WARN if Django admin lacks additional authentication in production | PASS/WARN |
| 5.10.4 | WARN if sensitive endpoints have same rate limits as regular endpoints | PASS/WARN |
| 5.10.5 | WARN if no audit logging exists for sensitive operations | PASS/WARN |
| 5.10.6 | WARN if bulk destructive operations lack confirmation parameter | PASS/WARN |
| 5.10.7 | WARN if internal service endpoints are not authenticated | PASS/WARN |
| 5.10.8 | FAIL if debug endpoints exist in production builds | PASS/FAIL |

## 5.11 CSRF Protection

| ID | Rule | Verdict |
|----|------|---------|
| 5.11.1 | FAIL if CsrfViewMiddleware is not in MIDDLEWARE when session auth is used | PASS/FAIL |
| 5.11.2 | FAIL if CSRF is disabled globally | PASS/FAIL |
| 5.11.3 | FAIL if @csrf_exempt is on login, password reset, or payment endpoints | PASS/FAIL |
| 5.11.4 | WARN if CSRF tokens are not properly sent for session-based browser flows | PASS/WARN |
| 5.11.5 | FAIL if CSRF_COOKIE_SECURE is False in production | PASS/FAIL |
| 5.11.6 | WARN if CSRF_COOKIE_HTTPONLY is True (JavaScript can't read the cookie for AJAX) | PASS/WARN |
| 5.11.7 | WARN if CSRF_TRUSTED_ORIGINS is not set for cross-origin deployments | PASS/WARN |

## 5.12 Audit Logging

| ID | Rule | Verdict |
|----|------|---------|
| 5.12.1 | WARN if authentication events (login, logout, failed login) are not logged | PASS/WARN |
| 5.12.2 | WARN if authorization failures are not logged | PASS/WARN |
| 5.12.3 | WARN if sensitive data mutations have no audit trail | PASS/WARN |
| 5.12.4 | WARN if audit logs lack user_id, action, resource_type, resource_id, ip_address | PASS/WARN |
| 5.12.5 | FAIL if audit logs are mutable (updatable or deletable) | PASS/FAIL |
| 5.12.6 | WARN if audit logs are mixed into the application log stream | PASS/WARN |
| 5.12.7 | WARN if no account lockout exists for failed login attempts | PASS/WARN |
| 5.12.8 | INFO if account lockout doesn't notify the account owner — depends on UX | PASS/INFO |

## 5.13 Token Storage & Transport Security

| ID | Rule | Verdict |
|----|------|---------|
| 5.13.1 | WARN if refresh tokens are stored in localStorage for web clients | PASS/WARN |
| 5.13.2 | WARN if access tokens are persisted to localStorage or sessionStorage | PASS/WARN |
| 5.13.3 | FAIL if refresh token cookies lack Secure, HttpOnly, SameSite flags | PASS/FAIL |
| 5.13.4 | WARN if refresh token cookie Path is set to `/` instead of the refresh endpoint | PASS/WARN |
| 5.13.5 | FAIL if tokens are included in URL query parameters or Referer headers | PASS/FAIL |
| 5.13.6 | WARN if JWT payload contains data that would be sensitive if base64 decoded | PASS/WARN |
| 5.13.7 | PASS if CORS is configured to allow only specific origins for token endpoints | PASS |
| 5.13.8 | WARN if mobile clients don't use platform secure storage for tokens | PASS/WARN |

## 5.14 Account Security & Lifecycle

| ID | Rule | Verdict |
|----|------|---------|
| 5.14.1 | WARN if email verification is not required before full account access | PASS/WARN |
| 5.14.2 | FAIL if email verification tokens are permanent or reusable | PASS/FAIL |
| 5.14.3 | FAIL if account deactivation does not revoke all sessions and tokens | PASS/FAIL |
| 5.14.4 | WARN if account deletion is hard-delete without grace period | PASS/WARN |
| 5.14.5 | WARN if no session listing endpoint exists for users | PASS/WARN |
| 5.14.6 | WARN if users cannot revoke individual sessions | PASS/WARN |
| 5.14.7 | INFO if no maximum concurrent session limit — depends on security requirements | PASS/INFO |
| 5.14.8 | WARN if password change does not force re-auth on other sessions | PASS/WARN |
| 5.14.9 | INFO if no suspicious activity detection — only relevant for high-security apps | PASS/INFO |
