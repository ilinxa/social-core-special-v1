# STRIDE Threat Model

**Application**: Social Media Advertising Platform
**Version**: 1.0
**Date**: 2026-03-14
**Author**: Security Architecture Review

---

## 1. System Overview

### Architecture

```
                    ┌──────────────┐
                    │   Clients    │
                    │  (Web/Mobile)│
                    └──────┬───────┘
                           │ HTTPS
              ┌────────────▼────────────┐
              │         Nginx           │  ← Trust Boundary 1
              │  (TLS termination,      │
              │   rate limiting, headers)│
              └────────────┬────────────┘
                           │ HTTP (internal)
              ┌────────────▼────────────┐
              │     Django / DRF        │  ← Trust Boundary 2
              │  (Application Layer)    │
              │  ┌─────────────────┐    │
              │  │  Auth / JWT     │    │
              │  │  RBAC / Policies│    │
              │  │  Services       │    │
              │  │  Serializers    │    │
              │  └─────────────────┘    │
              └──┬──────────┬───────┬───┘
                 │          │       │
         ┌───────▼──┐  ┌───▼───┐  ┌▼────────┐
         │PostgreSQL │  │ Redis │  │   S3    │
         │  (Data)   │  │(Cache,│  │ (Media) │
         │           │  │ JTI)  │  │         │
         └───────────┘  └───────┘  └─────────┘
           TB 3           TB 4       TB 5
```

### Components

| Component | Technology | Role |
|-----------|-----------|------|
| Web Client | Next.js 16 | SPA frontend |
| API Server | Django 5.1 + DRF | REST API, business logic |
| Database | PostgreSQL 17 | Persistent storage |
| Cache/Blacklist | Redis 7 | JWT blacklist, session cache |
| Object Storage | S3 (production) | Media file storage |
| Task Queue | Celery + Redis | Async tasks (email, notifications) |
| Reverse Proxy | Nginx | TLS, rate limiting, headers |

### Authentication Mechanisms

| Mechanism | Scope | Implementation |
|-----------|-------|----------------|
| JWT (HS256) | API endpoints | Access token (short-lived) + refresh token (HttpOnly cookie or body) |
| OAuth 2.0 | Social login | Google + Apple with PKCE + state + nonce |
| API Key | CMS admin | SHA-256 hashed, `cmsk_` prefix, per-site scoped |
| Session | Django admin | Standard Django session auth |

---

## 2. Asset Inventory

### Critical Assets

| Asset | Sensitivity | Storage | Protection |
|-------|-----------|---------|------------|
| User passwords | HIGH | PostgreSQL (Argon2 hash) | Never stored in plaintext |
| JWT signing key | HIGH | Environment variable | Not in code, not logged |
| Refresh tokens | HIGH | PostgreSQL (SHA-256 hash) | HttpOnly cookies (web), body (mobile) |
| CMS API keys | HIGH | PostgreSQL (SHA-256 hash) | Plaintext shown once on creation |
| OAuth client secrets | HIGH | Environment variables | Not in code |
| User PII (email, phone) | MEDIUM | PostgreSQL | Visibility system (T1/T2/T3) |
| Business legal data | MEDIUM | PostgreSQL | T3 visibility + RBAC `can_view_legal_info` |
| Media files | LOW-MEDIUM | S3 / local filesystem | UUID-based paths, MIME whitelist |
| Audit logs | MEDIUM | PostgreSQL | Immutable, append-only |

### Data Classification

- **T1 (Public)**: Business name, slug, description, profile photo, city, country
- **T2 (Configurable)**: Business contact email/phone (default: followers+)
- **T3 (Members-only + RBAC)**: Registration number, tax ID, legal address, business settings

---

## 3. Trust Boundaries

### TB1: Internet → Nginx

**Description**: External traffic enters the system through Nginx reverse proxy.

**Controls**:
- TLS 1.2/1.3 only (ECDHE+AEAD ciphers)
- HSTS with 1-year max-age, includeSubDomains, preload
- Rate limiting: 10 req/s API, 5 req/m login, 20 connections per IP
- `client_max_body_size 50M`
- `client_body_timeout 12s`, `client_header_timeout 12s` (slow-loris mitigation)
- Security headers: CSP (report-only), X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- `server_tokens off` (version hidden)

### TB2: Nginx → Django Application

**Description**: Internal HTTP from Nginx to Django. Application handles auth, authz, and business logic.

**Controls**:
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
- CORS middleware with explicit origin whitelist (production)
- CSRF middleware (active, JWT endpoints exempt by design)
- Request logging middleware (all requests with user context)
- `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`
- `DEFAULT_PARSER_CLASSES = [JSONParser]` (file upload views opt-in)

### TB3: Django → PostgreSQL

**Description**: Application connects to database for persistent storage.

**Controls**:
- SSL required in production (`sslmode=require`)
- Dedicated `django_user` with limited privileges
- All queries via Django ORM (no raw SQL)
- Soft-delete filtering via `SoftDeleteManager`
- UUID primary keys (no enumeration)

### TB4: Django → Redis

**Description**: Application uses Redis for JWT blacklist and caching.

**Controls**:
- JTI blacklist: fail-closed on Redis failure (raises `ServiceUnavailable`)
- Blacklist write: best-effort fallback to Django cache
- Connection via `REDIS_URL` environment variable
- Cache keys namespaced by function (JTI prefix: `jti_blacklist:`)

### TB5: Django → S3 (Object Storage)

**Description**: Media files stored in S3 (production) or local filesystem (development).

**Controls**:
- UUID-based storage keys (no user-supplied filenames in paths)
- MIME type + extension whitelist before upload
- Nginx serves with `Content-Disposition: attachment` (images: inline)
- `X-Content-Type-Options: nosniff` on all media responses

### TB6: CMS API Key Boundary

**Description**: CMS admin API endpoints protected by API key authentication.

**Controls**:
- API keys SHA-256 hashed before storage
- `cmsk_` prefix for identification
- Per-site scoping
- Rate limiting (configurable per key)
- Keys revocable via soft-delete

---

## 4. STRIDE Analysis

### 4.1 Spoofing (Identity)

| Threat | Risk | Mitigation | Status |
|--------|------|-----------|--------|
| Stolen JWT used for impersonation | HIGH | Short-lived access tokens (configurable TTL), JTI blacklist for revocation, `iss`/`aud` claim validation | MITIGATED |
| JWT algorithm confusion | HIGH | `ALLOWED_ALGORITHMS = ["HS256"]` — only one algorithm accepted | MITIGATED |
| OAuth state forgery | HIGH | `secrets.token_urlsafe(32)` state, one-time use, 10-min TTL, PKCE | MITIGATED |
| Credential brute force | HIGH | Rate limiting (5/min login), progressive account lockout (10 attempts → 15 min) | MITIGATED |
| Session hijacking | MEDIUM | HttpOnly + Secure + SameSite cookies, HSTS, session limits (max 5) | MITIGATED |
| API key theft | MEDIUM | SHA-256 hashed storage, shown once on creation, revocable | MITIGATED |
| User enumeration via login | MEDIUM | Generic error messages for both "user not found" and "wrong password" | MITIGATED |
| User enumeration via registration | LOW | Returns 409 for duplicate email (necessary UX trade-off) | ACCEPTED |

### 4.2 Tampering (Data Integrity)

| Threat | Risk | Mitigation | Status |
|--------|------|-----------|--------|
| SQL injection | HIGH | Django ORM exclusively, no raw SQL, parameterized FTS queries | MITIGATED |
| XSS via rich text | HIGH | `nh3` HTML sanitization on all richtext fields before storage | MITIGATED |
| Mass assignment | HIGH | All serializers use explicit field lists, zero `fields = '__all__'` | MITIGATED |
| CSRF on state-changing endpoints | MEDIUM | JWT-based auth (CSRF not applicable), CSRF middleware active for session auth | MITIGATED |
| Request body tampering | MEDIUM | HTTPS (TLS 1.2/1.3), `JSONParser` only default, input validation via serializers | MITIGATED |
| ReDoS via CMS patterns | LOW | Schema-time validation (length limit, compile check, backtracking heuristic), runtime error handling | MITIGATED |

### 4.3 Repudiation (Audit Trail)

| Threat | Risk | Mitigation | Status |
|--------|------|-----------|--------|
| Untracked admin actions | MEDIUM | AuditLog with 70+ action types, immutable append-only, composite indexes | MITIGATED |
| Untracked auth events | MEDIUM | All auth events logged: login, logout, token refresh, password changes, session management | MITIGATED |
| Untracked authorization failures | MEDIUM | 403 responses audit-logged, RequestLoggingMiddleware captures all requests | MITIGATED |
| Log tampering | LOW | Structured JSON logging (structlog), stdout to container runtime, PII redaction | MITIGATED |
| Missing audit for bulk operations | LOW | Service layer logs all operations, no direct DB manipulation in views | MITIGATED |

### 4.4 Information Disclosure

| Threat | Risk | Mitigation | Status |
|--------|------|-----------|--------|
| PII exposure in API responses | HIGH | 3-tier visibility system (T1/T2/T3), queryset scoping by membership/ownership | MITIGATED |
| Sensitive data in error responses | HIGH | Custom exception handler returns clean JSON, `DEBUG=False` in production | MITIGATED |
| Sensitive data in logs | MEDIUM | structlog processors redact 15+ field patterns (password, token, secret, etc.) | MITIGATED |
| Sensitive data in Sentry | MEDIUM | `before_send` hook scrubs 14 sensitive field patterns before transmission | MITIGATED |
| Business legal data exposure | MEDIUM | T3 visibility + RBAC `can_view_legal_info` permission | MITIGATED |
| Token exposure in URLs | MEDIUM | Tokens in body/cookies only, never URL query params | MITIGATED |
| Server version disclosure | LOW | `server_tokens off` in nginx | MITIGATED |
| PII fields not encrypted at rest | LOW | T3 visibility restricts access. DB-level encryption is infrastructure concern | ACCEPTED (INFO) |

### 4.5 Denial of Service

| Threat | Risk | Mitigation | Status |
|--------|------|-----------|--------|
| API flood | HIGH | DRF throttling (anon 100/hr, user 1000/hr) + nginx rate limiting (10r/s) | MITIGATED |
| Login brute force | HIGH | Login throttle (5/min) + account lockout (10 attempts) + nginx login rate limit (5r/m) | MITIGATED |
| Large file upload | MEDIUM | `client_max_body_size 50M`, `FILE_UPLOAD_MAX_MEMORY_SIZE 10MB`, MIME whitelist | MITIGATED |
| Slow-loris attack | MEDIUM | `client_body_timeout 12s`, `client_header_timeout 12s` | MITIGATED |
| Connection exhaustion | MEDIUM | `limit_conn conn_limit 20` per IP | MITIGATED |
| ReDoS via regex patterns | LOW | Pattern validation at schema time, runtime error handling | MITIGATED |
| Password reset flood | LOW | Password reset throttle (3/hr) | MITIGATED |

### 4.6 Elevation of Privilege

| Threat | Risk | Mitigation | Status |
|--------|------|-----------|--------|
| Role escalation | HIGH | Role level hierarchy: actors can only assign roles below their own level | MITIGATED |
| Ownership theft | HIGH | Ownership transfer requires current owner initiation + target acceptance | MITIGATED |
| Cross-business access | HIGH | Queryset scoping by business membership, policy checks on all endpoints | MITIGATED |
| Accessing other users' resources | HIGH | UUID identifiers (no enumeration), policy checks, queryset scoping | MITIGATED |
| Admin endpoint access | MEDIUM | `IsAdminUser`, `IsPlatformOwner`, `IsPlatformAdmin` permission classes | MITIGATED |
| Soft-deleted resource access | MEDIUM | `SoftDeleteManager` filters `is_deleted=False` automatically | MITIGATED |
| Mass assignment of role fields | LOW | Serializers use explicit field lists, role assignment through dedicated service methods | MITIGATED |

---

## 5. Endpoint Inventory

### Summary

| App | Endpoints | Auth Mechanism | Primary Protection |
|-----|----------|----------------|-------------------|
| Auth | 12 | Public + JWT | Rate limiting, lockout |
| Users | 8 | JWT | Ownership check |
| Business | 15 | JWT | BusinessPolicy + RBAC |
| Platform | 10 | JWT | PlatformPolicy + RBAC |
| RBAC | 12 | JWT | MembershipPolicy |
| Transaction | 8 | JWT | TransactionPolicy |
| Forms | 14 | JWT | FormPolicy + RBAC |
| Network | 13 | JWT | NetworkPolicy |
| Notifications | 4 | JWT | Ownership scoping |
| CMS Admin | 20 | API Key | Site-scoped keys |
| CMS Public | 5 | Public | Read-only |
| Explore | 5 | Public/JWT | Visibility system |
| **Total** | **~126** | | |

### Auth Mechanism Distribution

- **JWT required**: ~95 endpoints
- **Public (AllowAny)**: ~20 endpoints (explore, CMS public, business/platform detail GET)
- **API Key**: ~20 endpoints (CMS admin)
- **Staff/Superuser**: Django admin panel

---

## 6. Mitigations Matrix

| Control | Threats Addressed | Implementation | Test Coverage |
|---------|------------------|----------------|---------------|
| JWT iss/aud validation | Spoofing, cross-service tokens | `apps/core/utils/jwt.py` | 190 tests |
| JTI blacklist (fail-closed) | Spoofing, revoked token reuse | `apps/auth/blacklist.py` | 15 tests |
| Account lockout | Brute force, credential stuffing | `apps/auth/services/auth_service.py` | 10 tests |
| RBAC policy checks | Elevation of privilege | `apps/rbac/policies.py` | 361 tests |
| 3-tier visibility | Information disclosure | `apps/core/visibility/` | 158 tests |
| Input validation | Injection, tampering | DRF serializers + `SchemaValidator` | All view tests |
| nh3 sanitization | XSS | `apps/cms/validators.py` | 4 tests |
| Rate limiting | DoS, brute force | DRF throttles + nginx | Integration tests |
| Audit logging | Repudiation | `apps/core/observability/` | 70+ action types |
| MIME whitelist | File upload attacks | `apps/cms/services.py` | CMS tests |
| ReDoS protection | DoS via regex | `apps/cms/validators.py` | 7 tests |
| UUID identifiers | Enumeration | All models | Architectural |
| Soft-delete manager | Data leakage | `apps/core/models.py` | All model tests |

---

## 7. Residual Risks (Accepted)

These items are classified as INFO — accepted for the current stage of the application:

| # | Risk | Justification |
|---|------|---------------|
| 1 | No MFA | Consumer social platform, acceptable for current stage |
| 2 | No centralized log shipping | structlog JSON to stdout is container-native, compatible with any shipper |
| 3 | No field-level encryption | T3 visibility + RBAC restricts access; DB encryption is infrastructure-level |
| 4 | No malware scanning on uploads | MIME whitelist + S3 isolation provides baseline protection |
| 5 | No image EXIF stripping | Low risk for current use case |
| 6 | No `--require-hashes` for pip | Dependencies pinned with `==`, Dependabot monitors for updates |
| 7 | No JWT key rotation (kid) | Single-service architecture, single key acceptable |
| 8 | No Celery task rate limits | Tasks triggered by service logic, not direct user input |
| 9 | No `Permissions-Policy` header | API-only backend, no browser feature policy needed |
| 10 | No incident response runbook | To be created as part of production readiness |

---

## 8. Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-14 | 1.0 | Initial threat model based on security audit |
