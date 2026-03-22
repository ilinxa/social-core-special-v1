# 09 — Security Checklist

## 9.1 Django Security Hardening

- [ ] `DEBUG = False` is enforced in all non-local environments — verified in CI with `manage.py check --deploy`
- [ ] `SECRET_KEY` is at least **50 characters**, randomly generated, and **unique per environment**
- [ ] `ALLOWED_HOSTS` is explicitly set — no `['*']` in staging or production
- [ ] `SECURE_SSL_REDIRECT = True` in production — all HTTP traffic redirected to HTTPS
- [ ] `SECURE_HSTS_SECONDS = 31536000` in production — one year HSTS policy
- [ ] `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` in production
- [ ] `SECURE_HSTS_PRELOAD = True` if the domain is submitted to the HSTS preload list
- [ ] `SECURE_PROXY_SSL_HEADER` is set correctly if behind a reverse proxy — `('HTTP_X_FORWARDED_PROTO', 'https')`
- [ ] `SESSION_COOKIE_SECURE = True` in production
- [ ] `SESSION_COOKIE_HTTPONLY = True` — cookie inaccessible to JavaScript
- [ ] `SESSION_COOKIE_SAMESITE = 'Lax'` or `'Strict'` in production
- [ ] `CSRF_COOKIE_SECURE = True` in production
- [ ] `CSRF_COOKIE_HTTPONLY = False` — correctly allows JavaScript to read it for AJAX
- [ ] `X_FRAME_OPTIONS = 'DENY'` — prevents clickjacking via iframes
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF = True` — prevents MIME type sniffing
- [ ] `SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'` is set
- [ ] `manage.py check --deploy` passes with **zero warnings** in CI

## 9.2 Authentication Security

- [ ] Brute force protection is in place — **account lockout** after configurable failed login attempts
- [ ] Login endpoint is **rate limited** independently — stricter than general API throttling
- [ ] Password reset endpoint is **rate limited** — prevents email flooding and enumeration
- [ ] **User enumeration** is prevented — login and password reset return identical responses for valid and invalid accounts
- [ ] **Timing attacks** on authentication are mitigated — constant-time comparison for tokens and passwords
- [ ] Multi-factor authentication (MFA) is available for sensitive accounts — enforced for admin users
- [ ] OAuth state parameter is validated on callback — CSRF protection for social auth flows
- [ ] JWT tokens are validated for **signature, expiry, issuer, and audience** — not just signature
- [ ] **Token leakage** is prevented — tokens never appear in URLs, logs, or error responses
- [ ] Concurrent session limits are considered — multiple simultaneous sessions handled deliberately

## 9.3 Authorization Security

- [ ] **Insecure Direct Object Reference (IDOR)** is prevented — all resource access scoped to authenticated user's permissions
- [ ] Object ownership is verified at **queryset level** — not just permission class level
- [ ] **Privilege escalation** is prevented — users cannot assign themselves higher roles
- [ ] **Horizontal privilege escalation** is prevented — user A cannot access user B's resources by guessing IDs
- [ ] **Vertical privilege escalation** is prevented — regular users cannot access admin endpoints
- [ ] Mass assignment is prevented — serializers explicitly list writable fields, no `fields = '__all__'`
- [ ] Role changes require **re-authentication** or explicit elevated privilege — not a simple profile update
- [ ] Admin-only endpoints are tested with **non-admin credentials** — verify they return `403`
- [ ] Soft-deleted records are inaccessible to regular users — queryset-level filtering enforced
- [ ] **Indirect object references** (slugs, public tokens) are used for externally exposed identifiers where appropriate

## 9.4 Input Validation & Injection Prevention

- [ ] **All user input** passes through serializer validation before reaching service or DB layer
- [ ] **SQL injection** is prevented — ORM used exclusively, no raw SQL with string interpolation
- [ ] Raw SQL via `RawSQL`, `extra()`, or `cursor.execute()` uses **parameterized queries** — never f-strings or `.format()`
- [ ] **NoSQL injection** is prevented if MongoDB or similar is used alongside Django
- [ ] **LDAP injection** is prevented if LDAP authentication is used
- [ ] **Command injection** is prevented — no `subprocess` calls with user-supplied input
- [ ] **Path traversal** is prevented — file paths constructed from user input are sanitized and confined to allowed directories
- [ ] **XML injection / XXE** is prevented — `defusedxml` used if XML parsing is required
- [ ] **ReDoS** (regex denial of service) is prevented — user-supplied regex patterns are rejected or sandboxed
- [ ] **Mass assignment** is prevented — explicit field whitelisting in all serializers
- [ ] Integer overflow on numeric inputs is handled — bounds validation on all numeric fields
- [ ] Enum inputs are validated against **exact allowed values** — no partial match or case-insensitive acceptance without explicit intent

## 9.5 Cross-Site Request Forgery (CSRF)

- [ ] `CsrfViewMiddleware` is active and not disabled globally
- [ ] CSRF exemptions (`@csrf_exempt`) are rare, documented, and justified
- [ ] CSRF is correctly handled for **AJAX requests** — `X-CSRFToken` header sent and validated
- [ ] `CSRF_TRUSTED_ORIGINS` is explicitly set — no implicit trust of all origins
- [ ] SameSite cookie policy provides **defense in depth** alongside CSRF tokens
- [ ] DRF's `SessionAuthentication` enforces CSRF — not bypassed for session-based API endpoints
- [ ] CSRF protection is tested — requests without valid tokens return `403`

## 9.6 Cross-Origin Resource Sharing (CORS)

- [ ] `django-cors-headers` is used — no manual CORS header manipulation
- [ ] `CORS_ALLOWED_ORIGINS` is an **explicit whitelist** — no `CORS_ALLOW_ALL_ORIGINS = True` in production
- [ ] `CORS_ALLOW_CREDENTIALS = True` is only set if cookies or auth headers must cross origins — not enabled by default
- [ ] Allowed origins do not include **wildcards for subdomains** unless explicitly intended
- [ ] `CORS_ALLOWED_METHODS` is restricted to only methods the API actually uses
- [ ] `CORS_ALLOWED_HEADERS` is restricted — not allowing all headers by default
- [ ] CORS configuration differs per environment — development allows localhost, production does not
- [ ] CORS policy is **tested** — preflight requests return correct headers, disallowed origins are rejected

## 9.7 Sensitive Data Protection

- [ ] **Passwords** are never stored in plaintext — always hashed with Argon2 or bcrypt
- [ ] **API keys and tokens** stored in the DB are **encrypted at rest** — not plaintext
- [ ] **PII fields** (SSN, passport numbers, financial data) are encrypted at the field level — `django-encrypted-model-fields` or equivalent
- [ ] Sensitive data is **never logged** — log filters strip passwords, tokens, credit card numbers
- [ ] Sensitive data is **never included in error messages** or stack traces sent to clients
- [ ] Sensitive data is **never in URL parameters** — appears only in request body or headers
- [ ] **Sentry and error tracking** are configured to scrub sensitive fields — `before_send` hook filters PII
- [ ] Database backups are **encrypted** — not plaintext dumps accessible to anyone with storage access
- [ ] Sensitive data in transit is protected by **TLS 1.2 minimum**, TLS 1.3 preferred
- [ ] TLS certificates are **valid, not self-signed**, and auto-renewed — Let's Encrypt or equivalent

## 9.8 File Upload Security

- [ ] **File type validation** is done server-side via magic bytes — not trusting client-provided `Content-Type`
- [ ] **File size limits** are enforced — both at the application level and at the web server level (nginx `client_max_body_size`)
- [ ] Uploaded files are **stored outside the web root** — not directly accessible via URL without authorization
- [ ] Uploaded file names are **sanitized and replaced** — original filename never used directly on the filesystem
- [ ] **Malware scanning** is performed on uploaded files if they will be shared or processed — ClamAV or cloud equivalent
- [ ] **Image uploads** are re-encoded server-side — stripping EXIF data and preventing ImageTragick-style exploits
- [ ] Archive files (ZIP, TAR) are validated for **zip bomb** attacks — extraction size limits enforced
- [ ] Uploaded files served back to users have correct `Content-Disposition: attachment` headers — preventing inline execution

## 9.9 Dependency & Supply Chain Security

- [ ] **`pip-audit`** or **`safety`** runs in CI — known vulnerable dependencies fail the build
- [ ] **`dependabot`** or **`renovate`** is configured — automated PRs for dependency updates
- [ ] All dependencies are **pinned to exact versions** — no range specifiers (`>=`, `~=`) in production requirements
- [ ] **`pip install`** uses a **hash verification** (`--require-hashes`) in production builds
- [ ] Third-party packages are reviewed before adoption — not blindly installing any package
- [ ] **`SECRET_KEY` and credentials** are not present in any dependency (checked via secret scanning)
- [ ] Docker base images are **pinned to specific digests** — not `python:3.12-slim` (mutable tag)
- [ ] Docker images are **scanned for vulnerabilities** — Trivy, Snyk, or equivalent in CI
- [ ] No **abandoned or unmaintained packages** with known CVEs are in the dependency tree

## 9.10 Secret Scanning & Leak Prevention

- [ ] **`detect-secrets`** or **`gitleaks`** is configured as a pre-commit hook — catches secrets before they're committed
- [ ] Secret scanning runs in **CI** as a pipeline step — second line of defense
- [ ] Git history is **audited** for past secret commits — `git log` and `trufflehog` scan on repo setup
- [ ] **`.env` files** are in `.gitignore` and confirmed to have never been committed
- [ ] **`git-secrets`** or equivalent prevents common credential patterns from being committed
- [ ] All team members have **pre-commit hooks installed** — enforced via `pre-commit install` in onboarding docs
- [ ] Accidentally leaked secrets have a **documented incident response** — rotate immediately, audit access logs

## 9.11 Security Headers

- [ ] **`Content-Security-Policy`** header is set — restricting allowed sources for scripts, styles, images
- [ ] CSP is in **report-only mode** initially — violations logged before enforcement
- [ ] **`Strict-Transport-Security`** header is set with correct `max-age` and `includeSubDomains`
- [ ] **`X-Content-Type-Options: nosniff`** is set
- [ ] **`X-Frame-Options: DENY`** is set — or `SAMEORIGIN` if framing is required internally
- [ ] **`Referrer-Policy: strict-origin-when-cross-origin`** is set
- [ ] **`Permissions-Policy`** header restricts access to browser features (camera, microphone, geolocation)
- [ ] Security headers are verified via **`securityheaders.com`** or equivalent tool
- [ ] Headers are set at the **nginx level** for consistency — not only at the Django level
- [ ] **`Server` header** is suppressed or genericized — not revealing nginx version or Django

## 9.12 Rate Limiting & Denial of Service Protection

- [ ] **Global rate limiting** is configured in DRF — applies to all endpoints by default
- [ ] **Auth endpoints** have stricter rate limits than general API endpoints
- [ ] **IP-based rate limiting** is applied at the nginx or load balancer level — before hitting Django
- [ ] **Request body size limits** are enforced at nginx level — `client_max_body_size` configured
- [ ] **Slow loris attacks** are mitigated — nginx `client_body_timeout` and `client_header_timeout` set
- [ ] **Connection limits per IP** are configured at the load balancer level
- [ ] **`Retry-After`** header is returned on `429` responses — clients know when to retry
- [ ] **Celery task rate limits** are set — a single user cannot flood the task queue
- [ ] Expensive endpoints (report generation, bulk export) have **concurrency limits** — one active job per user

## 9.13 Logging & Incident Response

- [ ] **All authentication events** are logged — login, logout, failed attempts, password resets
- [ ] **All authorization failures** are logged — with user ID, resource, and action attempted
- [ ] **All admin actions** are logged — Django admin has `LogEntry` by default, verified it is active
- [ ] Logs contain **no sensitive data** — filtered at the logging handler level
- [ ] **Security-relevant log events** are tagged — easily filterable for incident investigation
- [ ] Logs are **shipped to a centralized system** (ELK, Datadog, CloudWatch) — not only on local disk
- [ ] Log retention policy is defined — minimum 90 days for security logs, 1 year for compliance-regulated apps
- [ ] **Alerting** is configured for suspicious patterns — multiple failed logins, sudden traffic spikes, error rate surges
- [ ] A **security incident response runbook** exists — what to do when a breach is detected
- [ ] **Contact information for security reports** is published — `security.txt` at `/.well-known/security.txt`

## 9.14 OWASP Top 10 Coverage

- [ ] **A01 Broken Access Control** — IDOR prevention, queryset scoping, role enforcement tested
- [ ] **A02 Cryptographic Failures** — TLS enforced, sensitive data encrypted, no weak algorithms
- [ ] **A03 Injection** — ORM used, parameterized queries, input validated — SQL/command/LDAP injection prevented
- [ ] **A04 Insecure Design** — threat modeling done, security requirements defined before implementation
- [ ] **A05 Security Misconfiguration** — `manage.py check --deploy` passes, debug off, headers set
- [ ] **A06 Vulnerable Components** — `pip-audit` in CI, dependencies pinned and scanned
- [ ] **A07 Authentication Failures** — brute force protection, MFA available, token security enforced
- [ ] **A08 Software and Data Integrity** — dependency hashes verified, CI/CD pipeline protected
- [ ] **A09 Security Logging Failures** — all auth and authorization events logged, alerts configured
- [ ] **A10 Server-Side Request Forgery (SSRF)** — user-supplied URLs validated and restricted to allowed domains

## 9.15 API-Specific Security (Added)

- [ ] API authentication is **required by default** — `DEFAULT_PERMISSION_CLASSES` includes `IsAuthenticated`
- [ ] API versioning prevents **deprecated endpoint abuse** — old versions can be sunset
- [ ] **Request content-type enforcement** — only `application/json` accepted, not `multipart/form-data` on non-upload endpoints
- [ ] **Response content-type** is always `application/json` — no HTML rendering from API endpoints
- [ ] **Error responses** do not leak internal details — no stack traces, DB errors, or file paths in 4xx/5xx responses
- [ ] **Throttle classes** are applied per-view or globally — not relying on nginx alone
- [ ] JWT `kid` (key ID) is validated if key rotation is supported
- [ ] **API key rotation** is supported — old keys can be revoked without downtime (CMS API keys)
- [ ] **Webhook signature verification** exists if the application receives webhooks

## 9.16 Cryptographic Practices (Added)

- [ ] Password hashing uses **Argon2id** or **bcrypt** — not MD5, SHA1, or plain SHA256
- [ ] Password hashing cost parameters are tuned to take **>250ms** — not default minimal rounds
- [ ] **HMAC** is used for token signing — not plain hash comparisons
- [ ] **Cryptographic randomness** uses `secrets` module or `os.urandom` — not `random.random()`
- [ ] JWT signing uses **RS256 or HS256 with adequate key length** — not `none` algorithm
- [ ] Token generation (password reset, email verification) uses **cryptographically secure random** — not sequential or predictable
- [ ] **Key derivation functions** (PBKDF2, scrypt, Argon2) are used for any user-supplied key material
- [ ] No **custom cryptography** implementations — uses well-audited libraries (cryptography, PyNaCl)
