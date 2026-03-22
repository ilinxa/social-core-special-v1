# 09 — Security Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 9.1 Django Security Hardening

| ID | Rule | Verdict |
|----|------|---------|
| 9.1.1 | FAIL if `DEBUG = True` is possible in production settings or if `manage.py check --deploy` is not run in CI | PASS/FAIL |
| 9.1.2 | FAIL if `SECRET_KEY` is hardcoded, under 50 chars, or shared across environments | PASS/FAIL |
| 9.1.3 | FAIL if `ALLOWED_HOSTS = ['*']` in production or staging settings | PASS/FAIL |
| 9.1.4 | FAIL if `SECURE_SSL_REDIRECT` is not `True` in production | PASS/FAIL |
| 9.1.5 | WARN if `SECURE_HSTS_SECONDS` is less than 31536000 in production | PASS/WARN |
| 9.1.6 | WARN if `SECURE_HSTS_INCLUDE_SUBDOMAINS` is not `True` in production | PASS/WARN |
| 9.1.7 | INFO if `SECURE_HSTS_PRELOAD` is not set — only needed if submitting to preload list | PASS/INFO |
| 9.1.8 | WARN if `SECURE_PROXY_SSL_HEADER` is not set when behind a reverse proxy | PASS/WARN |
| 9.1.9 | FAIL if `SESSION_COOKIE_SECURE` is not `True` in production | PASS/FAIL |
| 9.1.10 | PASS if `SESSION_COOKIE_HTTPONLY` defaults to `True` (Django default) | PASS |
| 9.1.11 | WARN if `SESSION_COOKIE_SAMESITE` is not explicitly set in production | PASS/WARN |
| 9.1.12 | FAIL if `CSRF_COOKIE_SECURE` is not `True` in production | PASS/FAIL |
| 9.1.13 | PASS if `CSRF_COOKIE_HTTPONLY` is `False` (allows JS to read for AJAX) | PASS |
| 9.1.14 | PASS if `X_FRAME_OPTIONS = 'DENY'` is set | PASS |
| 9.1.15 | PASS if `SECURE_CONTENT_TYPE_NOSNIFF = True` (Django 5.x default) | PASS |
| 9.1.16 | WARN if `SECURE_REFERRER_POLICY` is not explicitly set | PASS/WARN |
| 9.1.17 | FAIL if `manage.py check --deploy` is not run in any automated process | PASS/FAIL |

## 9.2 Authentication Security

| ID | Rule | Verdict |
|----|------|---------|
| 9.2.1 | WARN if no brute force protection (account lockout or progressive delay) exists on login | PASS/WARN |
| 9.2.2 | WARN if login endpoint has no independent rate limit stricter than global throttle | PASS/WARN |
| 9.2.3 | WARN if password reset endpoint has no rate limit | PASS/WARN |
| 9.2.4 | FAIL if login or password reset reveals whether an email/username exists | PASS/FAIL |
| 9.2.5 | WARN if constant-time comparison is not used for token validation | PASS/WARN |
| 9.2.6 | INFO if MFA is not available — acceptable for early-stage consumer apps | PASS/INFO |
| 9.2.7 | FAIL if OAuth state parameter is not validated on callback | PASS/FAIL |
| 9.2.8 | FAIL if JWT tokens are not validated for signature AND expiry at minimum | PASS/FAIL |
| 9.2.9 | FAIL if tokens appear in URL parameters, logs, or error responses | PASS/FAIL |
| 9.2.10 | INFO if concurrent session limits are not implemented — acceptable if sessions are managed | PASS/INFO |

## 9.3 Authorization Security

| ID | Rule | Verdict |
|----|------|---------|
| 9.3.1 | FAIL if any endpoint allows access to resources without permission verification (IDOR) | PASS/FAIL |
| 9.3.2 | FAIL if object access relies solely on permission classes without queryset-level scoping | PASS/FAIL |
| 9.3.3 | FAIL if users can assign themselves roles equal to or higher than their current role | PASS/FAIL |
| 9.3.4 | FAIL if user A can access user B's resources by guessing UUIDs/IDs | PASS/FAIL |
| 9.3.5 | FAIL if non-admin users can access admin-only endpoints | PASS/FAIL |
| 9.3.6 | FAIL if any serializer uses `fields = '__all__'` on a writable endpoint | PASS/FAIL |
| 9.3.7 | WARN if role changes don't require elevated privilege verification | PASS/WARN |
| 9.3.8 | WARN if admin endpoints are not tested with non-admin credentials | PASS/WARN |
| 9.3.9 | FAIL if soft-deleted records are accessible via default querysets | PASS/FAIL |
| 9.3.10 | PASS if externally exposed identifiers use slugs or UUIDs instead of sequential integers | PASS |

## 9.4 Input Validation & Injection Prevention

| ID | Rule | Verdict |
|----|------|---------|
| 9.4.1 | FAIL if any endpoint processes user input without serializer validation | PASS/FAIL |
| 9.4.2 | FAIL if raw SQL with string interpolation (f-strings, .format()) is found | PASS/FAIL |
| 9.4.3 | WARN if `RawSQL`, `extra()`, or `cursor.execute()` exists without parameterized queries | PASS/WARN |
| 9.4.4 | INFO if NoSQL injection is N/A — only PostgreSQL used | PASS/INFO |
| 9.4.5 | INFO if LDAP injection is N/A — no LDAP auth | PASS/INFO |
| 9.4.6 | FAIL if `subprocess` is called with user-supplied input without sanitization | PASS/FAIL |
| 9.4.7 | FAIL if file paths are constructed from user input without confinement | PASS/FAIL |
| 9.4.8 | INFO if XML/XXE is N/A — no XML parsing | PASS/INFO |
| 9.4.9 | WARN if user-supplied regex patterns are accepted without validation | PASS/WARN |
| 9.4.10 | FAIL if any serializer uses `fields = '__all__'` — mass assignment risk | PASS/FAIL |
| 9.4.11 | PASS if numeric fields have bounds validation via Django field types or validators | PASS |
| 9.4.12 | PASS if enum inputs validated against ChoiceField or TextChoices | PASS |

## 9.5 Cross-Site Request Forgery (CSRF)

| ID | Rule | Verdict |
|----|------|---------|
| 9.5.1 | FAIL if `CsrfViewMiddleware` is removed from MIDDLEWARE | PASS/FAIL |
| 9.5.2 | WARN if `@csrf_exempt` is used without documented justification | PASS/WARN |
| 9.5.3 | PASS if CSRF handled via DRF's token-based auth (JWT) — CSRF not needed for stateless auth | PASS |
| 9.5.4 | WARN if `CSRF_TRUSTED_ORIGINS` is not set in production | PASS/WARN |
| 9.5.5 | PASS if SameSite cookie policy is set | PASS |
| 9.5.6 | PASS if DRF SessionAuthentication enforces CSRF or if session auth is not used | PASS |
| 9.5.7 | WARN if no CSRF tests exist | PASS/WARN |

## 9.6 Cross-Origin Resource Sharing (CORS)

| ID | Rule | Verdict |
|----|------|---------|
| 9.6.1 | PASS if `django-cors-headers` is in INSTALLED_APPS and MIDDLEWARE | PASS |
| 9.6.2 | FAIL if `CORS_ALLOW_ALL_ORIGINS = True` in production settings | PASS/FAIL |
| 9.6.3 | WARN if `CORS_ALLOW_CREDENTIALS = True` without explicit justification | PASS/WARN |
| 9.6.4 | WARN if CORS origins include wildcard subdomains | PASS/WARN |
| 9.6.5 | INFO if `CORS_ALLOWED_METHODS` not explicitly restricted — DRF limits methods per view | PASS/INFO |
| 9.6.6 | INFO if `CORS_ALLOWED_HEADERS` not explicitly restricted | PASS/INFO |
| 9.6.7 | FAIL if production and development use identical CORS configuration | PASS/FAIL |
| 9.6.8 | WARN if CORS is not tested | PASS/WARN |

## 9.7 Sensitive Data Protection

| ID | Rule | Verdict |
|----|------|---------|
| 9.7.1 | FAIL if passwords are stored in plaintext or with weak hashing (MD5, SHA1) | PASS/FAIL |
| 9.7.2 | WARN if API keys stored in DB are not hashed or encrypted | PASS/WARN |
| 9.7.3 | WARN if PII fields that require encryption are stored in plaintext | PASS/WARN |
| 9.7.4 | FAIL if passwords, tokens, or secrets appear in log output | PASS/FAIL |
| 9.7.5 | FAIL if error responses contain stack traces, DB errors, or internal paths in non-debug mode | PASS/FAIL |
| 9.7.6 | FAIL if tokens or secrets are passed as URL query parameters | PASS/FAIL |
| 9.7.7 | WARN if Sentry/error tracking doesn't scrub sensitive fields | PASS/WARN |
| 9.7.8 | INFO if DB backups are not encrypted — infrastructure concern | PASS/INFO |
| 9.7.9 | PASS if TLS is enforced (SECURE_SSL_REDIRECT + HSTS) | PASS |
| 9.7.10 | INFO if TLS cert management is not automated — infrastructure concern | PASS/INFO |

## 9.8 File Upload Security

| ID | Rule | Verdict |
|----|------|---------|
| 9.8.1 | WARN if file type validation relies only on extension or Content-Type header | PASS/WARN |
| 9.8.2 | WARN if no file size limits are enforced at application level | PASS/WARN |
| 9.8.3 | PASS if uploaded files stored outside web root (S3, MEDIA_ROOT outside static) | PASS |
| 9.8.4 | WARN if original filenames are preserved — should be sanitized or replaced | PASS/WARN |
| 9.8.5 | INFO if no malware scanning — acceptable for early stage | PASS/INFO |
| 9.8.6 | INFO if no image re-encoding — acceptable for early stage | PASS/INFO |
| 9.8.7 | INFO if no zip bomb protection — acceptable if no archive uploads | PASS/INFO |
| 9.8.8 | WARN if files served without Content-Disposition header | PASS/WARN |

## 9.9 Dependency & Supply Chain Security

| ID | Rule | Verdict |
|----|------|---------|
| 9.9.1 | WARN if `pip-audit` or `safety` is not in CI pipeline | PASS/WARN |
| 9.9.2 | WARN if no automated dependency update tool (dependabot/renovate) configured | PASS/WARN |
| 9.9.3 | FAIL if dependencies use range specifiers in production requirements | PASS/FAIL |
| 9.9.4 | INFO if `--require-hashes` not used — acceptable for early stage | PASS/INFO |
| 9.9.5 | PASS if third-party packages are mainstream/well-maintained | PASS |
| 9.9.6 | FAIL if SECRET_KEY or credentials found in committed code | PASS/FAIL |
| 9.9.7 | WARN if Docker base images use mutable tags | PASS/WARN |
| 9.9.8 | WARN if Docker images not scanned for vulnerabilities | PASS/WARN |
| 9.9.9 | WARN if known-vulnerable packages exist in dependency tree | PASS/WARN |

## 9.10 Secret Scanning & Leak Prevention

| ID | Rule | Verdict |
|----|------|---------|
| 9.10.1 | WARN if no pre-commit secret scanning hook configured | PASS/WARN |
| 9.10.2 | WARN if no CI secret scanning step | PASS/WARN |
| 9.10.3 | INFO if git history not audited for past leaks | PASS/INFO |
| 9.10.4 | FAIL if `.env` files are not in `.gitignore` | PASS/FAIL |
| 9.10.5 | WARN if no credential pattern detection in pre-commit | PASS/WARN |
| 9.10.6 | INFO if pre-commit hooks not enforced via documentation | PASS/INFO |
| 9.10.7 | INFO if no incident response process documented for leaked secrets | PASS/INFO |

## 9.11 Security Headers

| ID | Rule | Verdict |
|----|------|---------|
| 9.11.1 | WARN if `Content-Security-Policy` header is not set | PASS/WARN |
| 9.11.2 | INFO if CSP not in report-only mode — only needed during initial rollout | PASS/INFO |
| 9.11.3 | PASS if `Strict-Transport-Security` is set (covered in 9.1) | PASS |
| 9.11.4 | PASS if `X-Content-Type-Options: nosniff` is set | PASS |
| 9.11.5 | PASS if `X-Frame-Options: DENY` is set | PASS |
| 9.11.6 | WARN if `Referrer-Policy` is not explicitly set | PASS/WARN |
| 9.11.7 | INFO if `Permissions-Policy` not set — newer header, not critical for API-only apps | PASS/INFO |
| 9.11.8 | INFO if headers not verified via external tool | PASS/INFO |
| 9.11.9 | PASS if security headers set at nginx level | PASS |
| 9.11.10 | WARN if `Server` header reveals software version | PASS/WARN |

## 9.12 Rate Limiting & Denial of Service Protection

| ID | Rule | Verdict |
|----|------|---------|
| 9.12.1 | FAIL if no global rate limiting configured in DRF | PASS/FAIL |
| 9.12.2 | WARN if auth endpoints don't have stricter rate limits | PASS/WARN |
| 9.12.3 | PASS if nginx provides IP-based rate limiting | PASS |
| 9.12.4 | PASS if `client_max_body_size` is configured in nginx | PASS |
| 9.12.5 | WARN if slow loris timeouts not configured in nginx | PASS/WARN |
| 9.12.6 | INFO if connection limits per IP not configured — acceptable behind CDN | PASS/INFO |
| 9.12.7 | WARN if `Retry-After` header not returned on 429 responses | PASS/WARN |
| 9.12.8 | INFO if Celery task rate limits not set — acceptable for early stage | PASS/INFO |
| 9.12.9 | INFO if no concurrency limits on expensive endpoints | PASS/INFO |

## 9.13 Logging & Incident Response

| ID | Rule | Verdict |
|----|------|---------|
| 9.13.1 | PASS if all auth events (login, logout, failed attempts) are logged | PASS |
| 9.13.2 | WARN if authorization failures not logged with context | PASS/WARN |
| 9.13.3 | PASS if admin actions logged (Django LogEntry) | PASS |
| 9.13.4 | FAIL if sensitive data (passwords, tokens) appears in logs | PASS/FAIL |
| 9.13.5 | WARN if security events are not easily filterable | PASS/WARN |
| 9.13.6 | WARN if logs only stored on local disk | PASS/WARN |
| 9.13.7 | INFO if log retention policy not defined | PASS/INFO |
| 9.13.8 | INFO if no alerting configured for suspicious patterns | PASS/INFO |
| 9.13.9 | INFO if no incident response runbook exists | PASS/INFO |
| 9.13.10 | INFO if no security.txt published | PASS/INFO |

## 9.14 OWASP Top 10 Coverage

| ID | Rule | Verdict |
|----|------|---------|
| 9.14.1 | PASS if IDOR prevention, queryset scoping, and role enforcement are tested | PASS |
| 9.14.2 | PASS if TLS enforced and sensitive data protection implemented | PASS |
| 9.14.3 | PASS if ORM used exclusively and input validated | PASS |
| 9.14.4 | WARN if no documented threat model or security requirements | PASS/WARN |
| 9.14.5 | WARN if `manage.py check --deploy` not automated | PASS/WARN |
| 9.14.6 | WARN if dependency scanning not in CI | PASS/WARN |
| 9.14.7 | WARN if no brute force protection or MFA | PASS/WARN |
| 9.14.8 | WARN if dependency integrity not verified (no hashes) | PASS/WARN |
| 9.14.9 | WARN if security logging has gaps | PASS/WARN |
| 9.14.10 | WARN if SSRF prevention not explicitly addressed for user-supplied URLs | PASS/WARN |

## 9.15 API-Specific Security (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 9.15.1 | FAIL if `DEFAULT_PERMISSION_CLASSES` does not include `IsAuthenticated` | PASS/FAIL |
| 9.15.2 | PASS if API versioning is implemented | PASS |
| 9.15.3 | WARN if non-upload endpoints accept multipart/form-data | PASS/WARN |
| 9.15.4 | PASS if all API responses are JSON | PASS |
| 9.15.5 | FAIL if error responses leak internal details (stack traces, DB errors, file paths) | PASS/FAIL |
| 9.15.6 | PASS if throttle classes applied globally or per-view | PASS |
| 9.15.7 | INFO if JWT key rotation (kid) not supported — acceptable for single-key setup | PASS/INFO |
| 9.15.8 | PASS if API key rotation supported (CMS keys) | PASS |
| 9.15.9 | INFO if webhook signature verification N/A — no inbound webhooks | PASS/INFO |

## 9.16 Cryptographic Practices (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 9.16.1 | FAIL if password hashing uses MD5, SHA1, or plain SHA256 | PASS/FAIL |
| 9.16.2 | WARN if password hashing cost is not tuned (default Django PBKDF2 iterations) | PASS/WARN |
| 9.16.3 | PASS if HMAC used for token signing | PASS |
| 9.16.4 | FAIL if `random.random()` used for security-sensitive operations instead of `secrets` | PASS/FAIL |
| 9.16.5 | PASS if JWT uses HS256 or RS256 with adequate key length | PASS |
| 9.16.6 | FAIL if token generation is predictable or sequential | PASS/FAIL |
| 9.16.7 | INFO if KDF not needed — no user-supplied key material | PASS/INFO |
| 9.16.8 | PASS if no custom crypto — uses Django/PyJWT/hashlib standard libraries | PASS |
