# Backend Comprehensive Consistency Review — Final Report

**Date**: 2026-03-03
**Scope**: 11 apps, ~50 models, ~40 services, ~30 selectors, ~60 views, 13 Celery tasks, 2780 unit tests + 276 API integration tests.
**Methodology**: 12-phase review covering model layer, services, selectors, views, serializers, policies, exceptions, URLs, audit/observability, cross-app integration, tasks/signals, and test suite.

---

## Summary Table

| Severity | Count | Items |
|----------|-------|-------|
| **HIGH** | 3 | Missing `@extend_schema` (43+ endpoints), direct `request.data` access without serializer (6 views), CMS patch logic bug |
| **MEDIUM** | 6 | Missing audit logging (3 methods), `otp`/`verification_code` not redacted, Forms signal not wired, Beat schedule incomplete, duplicate BusinessAccountFactory, FormTemplatePolicy not wired |
| **LOW** | 8 | Selector naming (`_or_none`), serializer naming/inheritance, auth structlog usage, periodic tasks missing `bind=True`, return type annotation inconsistency, BaseOutputSerializer skipped in RBAC/Auth/Notifications, `oauth_error` not in STATUS_CODE_MAP, 1 service method missing keyword-only args |
| **PASS** | 46/60 checks | Model layer, URL routing, cross-app integration, test suite, exception hierarchy, policy logic, task idempotency, Celery config all clean |

---

## HIGH Severity (Breaks Functionality or API Contract)

### H1. 43+ API Endpoints Missing `@extend_schema` Decorators

**Files**:
- `backend/apps/rbac/views.py` — 20 POST/PATCH/DELETE methods, **zero** `@extend_schema`
- `backend/apps/transaction/api/views.py` — 9 POST/PATCH methods, **zero** `@extend_schema`
- `backend/apps/cms/api/views.py` — 14 POST/PATCH/DELETE methods without `@extend_schema` (only site/page CRUD has it)

**Problem**: Over 43 API endpoints lack `@extend_schema` decorators from `drf-spectacular`. This means:
1. These endpoints are invisible or incorrectly documented in the auto-generated OpenAPI spec
2. Request/response schemas are not validated at the documentation level
3. Frontend developers cannot rely on the API spec for these endpoints

**Well-covered apps**: Auth (17 decorators), Users (9), Forms (18), Notifications (6), Organization (18). These are clean.

**Recommended Fix**: Add `@extend_schema(request=..., responses=...)` to every POST, PATCH, DELETE method across RBAC, Transaction, and CMS admin views. Priority: RBAC (20 methods), then Transaction (9), then CMS admin (14).

---

### H2. 6 RBAC Views Read `request.data` Directly Without Input Serializer

**File**: `backend/apps/rbac/views.py`

**Problem**: Six member state-change views extract the `reason` field via `request.data.get("reason", "")` without passing through a validated input serializer. This bypasses:
1. Type coercion and validation (reason could be any type, not just string)
2. Schema documentation (related to H1)
3. Consistent error formatting for invalid input

**Affected views** (3 business + 3 platform duplicates):
- `views.py:373` — Suspend member (business): `reason = request.data.get("reason", "")`
- `views.py:395` — Remove member (business): `reason = request.data.get("reason", "")`
- `views.py:417` — Ban member (business): `reason = request.data.get("reason", "")`
- `views.py:670` — Suspend member (platform): same pattern
- `views.py:692` — Remove member (platform): same pattern
- `views.py:714` — Ban member (platform): same pattern

**Note**: Role change and permission management views correctly use input serializers (`MembershipRoleChangeInputSerializer`, `RoleCreateInputSerializer`, etc.). Only the suspend/remove/ban actions are affected.

**Recommended Fix**: Create a `MemberActionReasonInputSerializer` with a validated `reason` CharField and use it in all 6 views.

---

### H3. CMS AdminMediaFileDetailView.patch Validates But Doesn't Apply Changes

**File**: `backend/apps/cms/api/views.py` (around line 463)

**Problem**: The `patch()` method on `AdminMediaFileDetailView` runs validation logic on the incoming data but never actually applies the validated changes to the model instance. The method validates and returns a response, but the underlying model is not updated.

**Impact**: PATCH requests to update media file metadata (name, folder, alt_text) silently succeed but have no effect — data corruption by omission.

**Recommended Fix**: Add the actual save/update logic after validation. Ensure the validated fields are written to the MediaFile instance and saved.

---

## MEDIUM Severity (Audit Gap / Maintainability Risk)

### M1. 3 State-Changing Service Methods Missing AuditService.log()

**Files**:
- `backend/apps/users/services.py:142-175` — `UserService.verify_email()`
- `backend/apps/users/services.py:178-203` — `UserService.unverify_email()`
- `backend/apps/notifications/services/preference_service.py:215-239` — `PreferenceService.reset_preference()`

**Problem**: These methods change database state (toggle verification flags, delete preference records) but do not call `AuditService.log()`. Every other state-changing service method in the codebase creates an audit trail. These gaps mean:
1. No audit record for email verification/unverification events
2. No audit record for notification preference resets
3. Compliance risk for user data change tracking

**Note**: The email service (`apps/email/`) was originally flagged but excluded upon verification — `EmailLog` records serve as the email system's audit trail, which is the correct pattern for infrastructure services.

**Recommended Fix**: Add `AuditService.log()` calls with appropriate `AuditLog.Action` values. Note: `unverify_email` may need a new action enum value (e.g., `EMAIL_UNVERIFIED`).

---

### M2. Sensitive Data Redaction Missing `otp` and `verification_code`

**Files**:
- `backend/apps/core/observability/logging/processors.py:16-32` — `SENSITIVE_KEYS`
- `backend/apps/core/observability/audit/constants.py:12-31` — `REDACTED_FIELDS`

**Problem**: Both redaction systems cover passwords, tokens, API keys, SSN, and credit cards. However, neither includes:
- `otp` — one-time passwords used in 2FA flows
- `verification_code` — email/phone verification codes

These are sensitive authentication tokens that could leak into structured logs if any service accidentally includes them in log context.

**Comparison**:
- `REDACTED_FIELDS` (audit) includes `csrf` ✓ but not `otp` ✗
- `SENSITIVE_KEYS` (logging) does not include `csrf` ✗, `otp` ✗, or `verification_code` ✗

**Recommended Fix**: Add `otp`, `verification_code`, and `csrf` (for logging) to both `SENSITIVE_KEYS` and `REDACTED_FIELDS`.

---

### M3. Forms App Signal Handler Not Wired in AppConfig.ready()

**File**: `backend/apps/forms/apps.py`

**Problem**: `apps/forms/signals.py` defines a `@receiver(post_save, FormResponse)` handler, but `apps/forms/apps.py` does not import `signals` in its `ready()` method. This means the signal handler is never connected.

**Impact**: Currently harmless (the handler is a NOP placeholder), but any future implementation added to this signal will silently not work.

**Comparison**:
- `apps/users/apps.py` imports signals in `ready()` ✓
- `apps/transaction/apps.py` imports outcome handlers in `ready()` ✓
- `apps/forms/apps.py` — missing ✗

**Recommended Fix**: Add `import apps.forms.signals  # noqa: F401` to `FormsConfig.ready()`.

---

### M4. Celery Beat Schedule Missing 7 Defined Tasks

**File**: `backend/backend_core/celery.py` (beat_schedule section)

**Problem**: The beat schedule only includes 3 transaction tasks. Seven other periodic tasks are defined but never scheduled:

| Task | File | Purpose |
|------|------|---------|
| `auth.cleanup_expired_tokens` | auth/tasks.py | Daily token cleanup |
| `auth.cleanup_inactive_sessions` | auth/tasks.py | Weekly session cleanup |
| `email.retry_failed_emails_task` | email/tasks.py | Retry failed email sends |
| `email.cleanup_old_email_logs` | email/tasks.py | Clean old email logs |
| `notifications.cleanup_old_notification_logs` | notifications/tasks.py | Clean old notification logs |
| `cms.cleanup_tombstoned_media` | cms/tasks.py | Remove tombstoned media |
| `cms.prune_content_versions` | cms/tasks.py | Prune version history |

**Impact**: These tasks exist but will never run automatically. Expired tokens, old logs, and tombstoned media will accumulate indefinitely unless manually triggered.

**Recommended Fix**: Add entries to `app.conf.beat_schedule` in `celery.py` with appropriate cron schedules.

---

### M5. Duplicate BusinessAccountFactory Definitions

**Files**:
- `backend/apps/organization/tests/factories.py` — canonical definition
- `backend/apps/rbac/tests/factories.py` — separate definition

**Problem**: Two independent `BusinessAccountFactory` classes exist with slightly different field defaults. Neither imports from the other. This creates a maintenance risk — if the `BusinessAccount` model changes, both factories must be updated independently.

**Impact**: Currently both work, but divergence over time could cause subtle test failures or inconsistent test data.

**Recommended Fix**: Establish one canonical `BusinessAccountFactory` (likely in `organization/tests/factories.py`) and have `rbac/tests/factories.py` import from it, following the `UserFactory` pattern.

---

### M6. FormTemplatePolicy `get_viewer_permissions()` Not Wired to Views

**Files**:
- `backend/apps/forms/policies.py` — has `get_viewer_permissions()` with `_safe_check()` pattern
- `backend/apps/forms/api/views.py` — `FormTemplateDetailView` and `FormResponseDetailView` missing `PermissionInjectMixin`

**Problem**: The Forms policy layer correctly implements the Tier 1.5 permission-aware response pattern (`get_viewer_permissions()` returning `dict[str, bool]`), but no Forms view actually uses `PermissionInjectMixin` to inject `_permissions` into GET responses.

**Impact**: Frontend cannot use `<Can>` components to gate Forms UI elements without making additional API calls, defeating the purpose of the Tier 1.5 system.

**Recommended Fix**: Add `PermissionInjectMixin` to `FormTemplateDetailView` and `FormResponseDetailView`, set `policy_class`, implement `_build_policy_kwargs()`, and set `self._inject_permissions = True` in `get()`.

---

## LOW Severity (Style / Consistency Nits)

### L1. 6 Selector Methods Return Optional Without `_or_none` Suffix

**Files**:
- `backend/apps/email/selectors.py` — `get_by_name()` returns `Optional` but lacks `_or_none`
- `backend/apps/notifications/selectors.py` — `get_by_id()` returns `Optional` but lacks `_or_none`
- 4 similar cases across other apps

**Convention**: The codebase convention is: methods returning `Optional` should be named `get_*_or_none()` to signal nullable return. Methods that raise on not-found should be `get_*()`.

---

### L2. Serializer Naming Inconsistency

**Files**:
- `backend/apps/auth/` — uses `*Serializer` suffix instead of `*InputSerializer`
- `backend/apps/cms/` — some serializers use `*Serializer` instead of `*Input`

**Convention**: Project convention is `*InputSerializer` for request validation, `*OutputSerializer` for response formatting.

---

### L3. Output Serializers Not Inheriting BaseOutputSerializer

**Files**:
- `backend/apps/rbac/serializers.py` — 8 output serializers inherit `serializers.ModelSerializer`
- `backend/apps/auth/` and `backend/apps/notifications/` — similar pattern

**Convention**: All output serializers should inherit `BaseOutputSerializer` for consistent `read_only_fields` and future shared behavior.

---

### L4. Auth/OAuth Backends Using Bare `import logging`

**Files**:
- `backend/apps/auth/backends/google.py:34`
- `backend/apps/auth/backends/apple.py`
- `backend/apps/auth/tasks.py:13`
- `backend/apps/core/exceptions/handler.py:27`
- 3 other infrastructure files

**Convention**: App code should use `from apps.core.observability import get_logger`. These violations are all in infrastructure/framework code (not business logic), so the impact is low.

---

### L5. Periodic Celery Tasks Missing `bind=True`

**Files**: auth/tasks.py, email/tasks.py, cms/tasks.py, notifications/tasks.py

**Problem**: 5 periodic cleanup tasks use `@shared_task(name="...")` without `bind=True` or explicit `max_retries=0`. While functionally correct (they don't call `self.retry()`), the inconsistency with other tasks makes intent unclear.

---

### L6. Policy Return Type Annotation Inconsistency

**Files**: Various policy files across apps

**Problem**: Some `get_viewer_permissions()` methods annotate return as `dict` while others use `dict[str, bool]`. The more specific annotation is preferred.

---

### L7. `oauth_error` Exception Missing from STATUS_CODE_MAP

**File**: `backend/apps/core/exceptions/handler.py`

**Problem**: The custom DRF exception handler's `STATUS_CODE_MAP` has 15 entries mapping domain exception types to HTTP status codes. The `oauth_error` type is missing — it falls back to 400 (correct behavior by default), but the mapping is not explicit.

**Recommended Fix**: Add `"oauth_error": status.HTTP_400_BAD_REQUEST` to `STATUS_CODE_MAP` for completeness.

---

### L8. 1 Service Method Missing Keyword-Only Args Separator

**File**: `backend/apps/auth/services/verification_service.py:45-47`

**Problem**: The project convention is `def method(*, param1, param2)` (keyword-only args via `*`) for `@staticmethod` service methods. One method — `VerificationService.create_token(user, request=None)` — is missing the `*,` separator.

**Note**: All other service files across all 11 apps are compliant with the keyword-only convention.

**Recommended Fix**: Change to `def create_token(*, user, request=None)`.

---

## Phase Results Summary

| Phase | Area | Result | Checks Passed |
|-------|------|--------|--------------|
| 1 | Model Layer | **PASS** | 5/5 — All 50 models: correct inheritance, UUID PKs, soft delete, FK patterns, Meta |
| 2 | Service Layer | **PASS** | 4/5 — Missing audit logging (3 methods), 1 method missing keyword-only args |
| 3 | Selector Layer | **PASS** | 5/5 — 6 naming warnings (`_or_none` suffix) |
| 4 | View Layer | **FAIL** | 3/5 — 43+ missing `@extend_schema`, 6 direct `request.data` reads, CMS patch bug |
| 5 | Serializer Layer | **PASS** | 3/5 — Naming conventions and BaseOutputSerializer inheritance warnings |
| 6 | Policy Layer | **PASS** | 5/5 — FormTemplatePolicy not wired (MEDIUM), return type annotations |
| 7 | Exception Handling | **PASS** | 4/5 — `oauth_error` not in STATUS_CODE_MAP (LOW) |
| 8 | URL & Routing | **PASS** | 5/5 — All clean. Trailing slashes, namespaces, no `version` params |
| 9 | Audit & Observability | **MIXED** | 4/5 — 3 audit gaps (MEDIUM→M1), sensitive key gaps (MEDIUM→M2) |
| 10 | Cross-App Integration | **PASS** | 5/5 — FK patterns, ActorContext, lazy imports, polymorphic ownership, signals |
| 11 | Task & Signal Patterns | **PASS** | 4/5 — Beat schedule incomplete (MEDIUM→M4), Forms signal not wired (MEDIUM→M3) |
| 12 | Test Suite | **PASS** | 5/5 — Factories, conftest, naming, classes, mocking all consistent |

---

## Architecture Health

### Strengths
- **Model hierarchy**: Clean 5-level abstract model inheritance (UUIDModel → TimeStampedModel → SoftDeleteModel → AuditModel → BaseModel). 100% consistent across all 50 models.
- **Cross-app integration**: Zero circular imports. All cross-app calls use lazy imports inside functions. Polymorphic ownership pattern (owner_type + owner_id) shared correctly via `OwnerType` enum.
- **Exception hierarchy**: 17 domain exceptions all inherit `DomainException`. Custom handler maps to HTTP status codes. Zero bare `raise Exception`.
- **URL routing**: 100% consistent — all trailing slashes, all namespaced, no `version` URL param conflicts, no PUT endpoints.
- **Test suite maturity**: 2780 unit tests + 276 integration tests. Canonical factory patterns, consistent conftest organization, proper mock targeting, clean unit/integration separation.
- **Task idempotency**: All 13 Celery tasks handle duplicate execution safely via `select_for_update()`, status guards, or inherently idempotent batch operations.
- **Celery security**: JSON-only serialization (no pickle), hard time limits, `ALWAYS_EAGER` in test settings.
- **Observability stack**: Structlog throughout, AuditService for state changes, metrics validation preventing cardinality explosion, sensitive data redaction in both logging and audit layers.

### Areas Needing Attention
1. **API documentation** (H1): 43+ undocumented endpoints across RBAC, Transaction, and CMS admin views will block frontend development and API consumption.
2. **Input validation** (H2): 6 suspend/remove/ban views bypassing serializer validation for `reason` field.
3. **CMS patch bug** (H3): Silent data loss — validate-but-don't-save is a functional defect.
4. **Audit completeness** (M1): 3 methods creating audit gaps in user verification and notification preference tracking.
5. **Beat schedule** (M4): 7 cleanup tasks will never run, causing data accumulation over time.

---

## Prioritized Action Items

### Immediate (Before Next Feature)
1. Fix CMS `AdminMediaFileDetailView.patch` to actually apply validated changes (H3)
2. Add input serializers for 6 RBAC views reading `request.data` directly (H2)

### Short-Term (This Sprint)
3. Add `@extend_schema` to all 43+ undocumented endpoints (H1)
4. Add `AuditService.log()` to 3 missing service methods (M1)
5. Wire `PermissionInjectMixin` to Forms detail views (M6)
6. Add missing tasks to Celery Beat schedule (M4)

### Backlog
7. Add `otp`, `verification_code` to sensitive data redaction (M2)
8. Wire Forms signal in `AppConfig.ready()` (M3)
9. Consolidate duplicate `BusinessAccountFactory` (M5)
10. Fix selector naming (`_or_none` suffix) (L1)
11. Standardize serializer naming and inheritance (L2, L3)
12. Add `*,` to `VerificationService.create_token()` (L8)



H3: Fix CMS AdminMediaFileDetailView.patch — validates but doesn't save

H2: Add input serializer for 6 RBAC suspend/remove/ban views

H1: Add @extend_schema to RBAC views (20 methods)

H1: Add @extend_schema to Transaction views (9 methods)

H1: Add @extend_schema to CMS admin views (14 methods)

M1: Add AuditService.log to verify_email & unverify_email

M1: Add AuditService.log to reset_preference

M6: Wire PermissionInjectMixin to Forms detail views

M4: Add 7 missing tasks to Celery Beat schedule

M2: Add otp/verification_code to sensitive data redaction

M3: Wire Forms signal in AppConfig.ready()

M5: Consolidate duplicate BusinessAccountFactory

L1: Fix selector naming (_or_none suffix)

L2-L3: Standardize serializer naming and inheritance

L8: Add keyword-only args to VerificationService.create_token

L4-L7: Remaining LOW items (structlog, bind=True, annotations, oauth_error)