# 06 — Validation & Business Logic Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 6.1 Validation Layer Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 6.1.1 | FAIL if business rules (quota checks, state transitions, permission logic) exist inside serializers | PASS/FAIL |
| 6.1.2 | FAIL if input parsing or shape/type validation is performed inside service methods rather than serializers | PASS/FAIL |
| 6.1.3 | FAIL if service methods are called with unvalidated data — no `serializer.is_valid()` before service call | PASS/FAIL |
| 6.1.4 | WARN if validation errors from different layers produce inconsistent response shapes | PASS/WARN |
| 6.1.5 | WARN if validation logic exists inside views instead of serializers or services | PASS/WARN |
| 6.1.6 | WARN if validation order is unpredictable — e.g., service validation runs before serializer validation | PASS/WARN |
| 6.1.7 | WARN if validation logic is tied to HTTP request/response cycle and cannot be tested in isolation | PASS/WARN |

## 6.2 Serializer-Level Validation

| ID | Rule | Verdict |
|----|------|---------|
| 6.2.1 | FAIL if any incoming data bypasses serializer validation and reaches the service or DB layer directly | PASS/FAIL |
| 6.2.2 | WARN if manual `if not serializer.is_valid()` checks are used instead of `is_valid(raise_exception=True)` | PASS/WARN |
| 6.2.3 | PASS if `validate_<field>()` methods handle field-level format/range/length checks | PASS |
| 6.2.4 | PASS if `validate()` handles cross-field validation | PASS |
| 6.2.5 | WARN if serializer validation makes DB calls that could cause N+1 in list views | PASS/WARN |
| 6.2.6 | WARN if manual queryset checks inside `validate()` are used instead of `UniqueValidator` for uniqueness | PASS/WARN |
| 6.2.7 | FAIL if serializer validation executes business rules that belong in the service layer | PASS/FAIL |
| 6.2.8 | WARN if error messages in `validate_<field>()` are raw Python exceptions instead of user-facing text | PASS/WARN |
| 6.2.9 | FAIL if serializer validation raises unhandled exceptions other than `serializers.ValidationError` | PASS/FAIL |
| 6.2.10 | WARN if read-only fields are silently ignored instead of explicitly excluded from writable fields | PASS/WARN |

## 6.3 Service Layer Design

| ID | Rule | Verdict |
|----|------|---------|
| 6.3.1 | FAIL if any app lacks a service layer and business logic exists directly in views or serializers | PASS/FAIL |
| 6.3.2 | FAIL if service methods accept Django `request` or `response` objects as parameters | PASS/FAIL |
| 6.3.3 | FAIL if services accept raw request data or serializer instances instead of validated deserialized data | PASS/FAIL |
| 6.3.4 | WARN if any service method exceeds 100 lines or handles multiple unrelated responsibilities | PASS/WARN |
| 6.3.5 | WARN if service methods are not independently unit-testable without HTTP context | PASS/WARN |
| 6.3.6 | FAIL if services instantiate serializers — serializers are a view-layer concern | PASS/FAIL |
| 6.3.7 | FAIL if services import from `views.py` or DRF modules — no upward dependency | PASS/FAIL |
| 6.3.8 | PASS if service layer files are organized per domain app | PASS |
| 6.3.9 | WARN if service classes carry mutable instance state between calls | PASS/WARN |
| 6.3.10 | WARN if service function signatures use `**kwargs` hiding what parameters are actually needed | PASS/WARN |

## 6.4 Business Rule Validation

| ID | Rule | Verdict |
|----|------|---------|
| 6.4.1 | FAIL if business rules are enforced in views, serializers, or models instead of the service layer | PASS/FAIL |
| 6.4.2 | FAIL if business rule violations raise generic `ValueError`, bare `Exception`, or DRF `ValidationError` | PASS/FAIL |
| 6.4.3 | FAIL if custom business exceptions are not mapped to appropriate HTTP status codes | PASS/FAIL |
| 6.4.4 | WARN if business rules lack documentation via docstrings or requirements references | PASS/WARN |
| 6.4.5 | WARN if any business rule lacks both positive and negative test cases | PASS/WARN |
| 6.4.6 | WARN if business rules spanning multiple models are split across multiple view operations instead of a single service call | PASS/WARN |
| 6.4.7 | WARN if a business rule is enforced only via API but not via admin, management commands, or tasks | PASS/WARN |
| 6.4.8 | WARN if rule violations produce generic "operation failed" messages instead of actionable errors | PASS/WARN |

## 6.5 Atomic Transactions

| ID | Rule | Verdict |
|----|------|---------|
| 6.5.1 | FAIL if a service method modifies 2+ related tables without `@transaction.atomic` | PASS/FAIL |
| 6.5.2 | WARN if `transaction.atomic()` is applied at the view or serializer layer instead of the service layer | PASS/WARN |
| 6.5.3 | WARN if nested `transaction.atomic()` savepoint behavior is unclear or unintentional | PASS/WARN |
| 6.5.4 | FAIL if side effects (emails, webhooks, queue publishes) happen inside `transaction.atomic()` | PASS/FAIL |
| 6.5.5 | FAIL if post-commit side effects are called directly inside atomic blocks instead of using `transaction.on_commit()` | PASS/FAIL |
| 6.5.6 | WARN if `select_for_update()` is missing where a record is read then immediately updated | PASS/WARN |
| 6.5.7 | INFO if `select_for_update(nowait=True)` or `skip_locked=True` is not used where lock contention is possible | PASS/INFO |
| 6.5.8 | FAIL if HTTP calls or external I/O happen inside `transaction.atomic()` blocks | PASS/FAIL |
| 6.5.9 | WARN if no deadlock mitigation strategy exists — inconsistent lock ordering across operations | PASS/WARN |

## 6.6 Idempotency

| ID | Rule | Verdict |
|----|------|---------|
| 6.6.1 | WARN if retryable create operations lack idempotency keys or natural unique identifiers | PASS/WARN |
| 6.6.2 | INFO if idempotency keys are not supported via request header or explicit field — depends on app requirements | PASS/INFO |
| 6.6.3 | WARN if duplicate idempotent requests return an error instead of the original response | PASS/WARN |
| 6.6.4 | INFO if idempotency key storage has no TTL — only relevant if idempotency keys are implemented | PASS/INFO |
| 6.6.5 | WARN if background tasks are not idempotent — re-running causes duplicate side effects | PASS/WARN |
| 6.6.6 | WARN if Celery tasks don't use unique task IDs to prevent duplicate execution | PASS/WARN |
| 6.6.7 | WARN if transitioning a state machine to its current state raises an error instead of being a no-op | PASS/WARN |
| 6.6.8 | WARN if webhook processing is not idempotent — same event processed twice creates duplicates | PASS/WARN |

## 6.7 State Machine Design

| ID | Rule | Verdict |
|----|------|---------|
| 6.7.1 | FAIL if models with lifecycle states allow arbitrary field updates without a defined transition map | PASS/FAIL |
| 6.7.2 | FAIL if valid state transitions are scattered across multiple service functions instead of defined in one place | PASS/FAIL |
| 6.7.3 | FAIL if invalid state transitions silently succeed or raise generic errors | PASS/FAIL |
| 6.7.4 | FAIL if state change and related side effects are not atomic — partial commits possible | PASS/FAIL |
| 6.7.5 | WARN if state transition history is not recorded (who, what, when) | PASS/WARN |
| 6.7.6 | WARN if direct field assignment to state fields is possible outside the state machine transition methods | PASS/WARN |
| 6.7.7 | INFO if `django-fsm` or equivalent library is not used — hand-rolled is acceptable if well-structured | PASS/INFO |
| 6.7.8 | WARN if any state or valid transition lacks test coverage | PASS/WARN |

## 6.8 Business Logic Isolation

| ID | Rule | Verdict |
|----|------|---------|
| 6.8.1 | FAIL if `views.py` contains business logic beyond request parsing, serialization, and response construction | PASS/FAIL |
| 6.8.2 | FAIL if `serializers.py` contains business logic beyond input validation and data transformation | PASS/FAIL |
| 6.8.3 | WARN if `models.py` contains business logic beyond field definitions, `__str__`, and simple computed properties | PASS/WARN |
| 6.8.4 | WARN if `signals.py` contains business logic beyond lightweight event dispatching | PASS/WARN |
| 6.8.5 | WARN if `admin.py` contains business logic instead of calling the service layer | PASS/WARN |
| 6.8.6 | WARN if management commands contain business logic instead of calling the service layer | PASS/WARN |
| 6.8.7 | WARN if Celery tasks contain business logic instead of calling the service layer | PASS/WARN |
| 6.8.8 | FAIL if the service layer is not the single source of truth — different entry points enforce different rules | PASS/FAIL |

## 6.9 Custom Exceptions

| ID | Rule | Verdict |
|----|------|---------|
| 6.9.1 | WARN if no base custom exception class exists that all business exceptions inherit from | PASS/WARN |
| 6.9.2 | WARN if custom exceptions lack a machine-readable `code` attribute | PASS/WARN |
| 6.9.3 | WARN if custom exceptions lack a human-readable `message` attribute suitable for API responses | PASS/WARN |
| 6.9.4 | WARN if custom exceptions don't carry an HTTP status code hint for the exception handler | PASS/WARN |
| 6.9.5 | FAIL if no global DRF exception handler maps custom exceptions to consistent API error responses | PASS/FAIL |
| 6.9.6 | FAIL if the exception handler is not registered in `REST_FRAMEWORK['EXCEPTION_HANDLER']` | PASS/FAIL |
| 6.9.7 | FAIL if unexpected exceptions leak stack traces to the client instead of returning generic 500 | PASS/FAIL |
| 6.9.8 | WARN if custom exceptions are defined inline in service/view files instead of dedicated `exceptions.py` | PASS/WARN |

## 6.10 Input Sanitization

| ID | Rule | Verdict |
|----|------|---------|
| 6.10.1 | WARN if string inputs are not stripped of leading/trailing whitespace before processing | PASS/WARN |
| 6.10.2 | WARN if HTML content from users is stored raw without sanitization | PASS/WARN |
| 6.10.3 | WARN if file upload content types are not validated server-side | PASS/WARN |
| 6.10.4 | WARN if uploaded file names are not sanitized for path traversal characters | PASS/WARN |
| 6.10.5 | WARN if numeric inputs lack min/max bounds validation | PASS/WARN |
| 6.10.6 | PASS if enum/choice inputs are validated against the allowed set via TextChoices | PASS |
| 6.10.7 | WARN if date/datetime inputs accept unreasonable ranges (year 9999, negative timestamps) | PASS/WARN |
| 6.10.8 | WARN if regex patterns used for validation are vulnerable to ReDoS (catastrophic backtracking) | PASS/WARN |

## 6.11 Output Consistency

| ID | Rule | Verdict |
|----|------|---------|
| 6.11.1 | WARN if responses from the same endpoint have conditional fields that appear only sometimes | PASS/WARN |
| 6.11.2 | WARN if optional fields are omitted from responses instead of returned as `null` | PASS/WARN |
| 6.11.3 | WARN if computed fields are calculated ad-hoc in views instead of serializers or services | PASS/WARN |
| 6.11.4 | FAIL if boolean fields return `0`/`1` or string `"true"`/`"false"` instead of JSON booleans | PASS/FAIL |
| 6.11.5 | FAIL if numeric fields inconsistently return strings vs numbers across endpoints | PASS/FAIL |
| 6.11.6 | FAIL if empty collections return `null`, `""`, or are omitted instead of `[]` | PASS/FAIL |
| 6.11.7 | WARN if paginated responses omit pagination metadata on the first or only page | PASS/WARN |

## 6.12 Third-Party & External Service Calls

| ID | Rule | Verdict |
|----|------|---------|
| 6.12.1 | FAIL if external HTTP calls lack try/except and explicit timeout settings | PASS/FAIL |
| 6.12.2 | WARN if external service calls have no circuit breaker or retry strategy | PASS/WARN |
| 6.12.3 | WARN if slow external calls inside a request cycle are not offloaded to Celery | PASS/WARN |
| 6.12.4 | FAIL if external service failures raise raw `requests.exceptions.*` instead of domain-specific exceptions | PASS/FAIL |
| 6.12.5 | WARN if external service responses are used without validating their shape/type | PASS/WARN |
| 6.12.6 | FAIL if API keys or credentials are passed through to the client in API responses | PASS/FAIL |
| 6.12.7 | PASS if external service calls are mocked in tests — no real HTTP calls in the test suite | PASS |
| 6.12.8 | WARN if retry logic uses fixed intervals instead of exponential backoff with jitter | PASS/WARN |

## 6.13 Data Integrity & Constraint Enforcement

| ID | Rule | Verdict |
|----|------|---------|
| 6.13.1 | FAIL if unique-together rules are enforced only at the application level without a DB constraint | PASS/FAIL |
| 6.13.2 | WARN if value range validation lacks corresponding `CheckConstraint` at the DB level | PASS/WARN |
| 6.13.3 | WARN if `bulk_create(ignore_conflicts=True)` is used without documented justification | PASS/WARN |
| 6.13.4 | WARN if soft-deleted records can violate uniqueness (unique constraint doesn't account for `is_deleted`) | PASS/WARN |
| 6.13.5 | WARN if `on_delete=CASCADE` is used on critical relationships without documentation | PASS/WARN |
| 6.13.6 | WARN if data migrations don't validate existing data before adding new constraints | PASS/WARN |
| 6.13.7 | WARN if orphan records are possible due to missing FK constraints or nullable FKs without cleanup | PASS/WARN |

## 6.14 Celery Task Design & Async Operations

| ID | Rule | Verdict |
|----|------|---------|
| 6.14.1 | FAIL if Celery tasks accept model instances or request objects as arguments | PASS/FAIL |
| 6.14.2 | WARN if tasks are not idempotent (re-running causes duplicate side effects) | PASS/WARN |
| 6.14.3 | WARN if tasks lack explicit retry policies (`max_retries`, `retry_backoff`) | PASS/WARN |
| 6.14.4 | WARN if long-running tasks lack `soft_time_limit` and `time_limit` settings | PASS/WARN |
| 6.14.5 | WARN if task failures are not logged or monitored | PASS/WARN |
| 6.14.6 | WARN if tasks that modify data don't use transactions where needed | PASS/WARN |
| 6.14.7 | WARN if `ignore_result=True` is not set on fire-and-forget tasks | PASS/WARN |
| 6.14.8 | FAIL if tasks import from views or serializers instead of services/selectors | PASS/FAIL |
