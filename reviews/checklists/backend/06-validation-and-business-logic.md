# 06 — Validation & Business Logic Checklist

## 6.1 Validation Layer Architecture

- [ ] Validation is clearly separated into **three distinct layers**: input validation (serializer), business rule validation (service), and data integrity validation (DB constraints)
- [ ] Each layer handles **only its own concern** — no business rules in serializers, no input parsing in services
- [ ] Validation layers are **never skipped** — service layer is not called with unvalidated data
- [ ] Validation errors from all layers produce **consistent error response shapes**
- [ ] No validation logic lives inside views — views call serializer validation, then delegate to service
- [ ] The order of validation is always: serializer → service → DB — never out of order
- [ ] Validation logic is **unit testable in isolation** — no validation tied to HTTP request/response cycle

## 6.2 Serializer-Level Validation

- [ ] **All incoming data** passes through a serializer before touching the service or DB layer
- [ ] `serializer.is_valid(raise_exception=True)` is used — not manual `if not serializer.is_valid()` checks
- [ ] `validate_<field>()` is used for **single field validation** — type coercion, format checks, allowed values
- [ ] `validate()` is used for **cross-field validation** — fields that depend on each other
- [ ] Serializer validation **does not call the database** unless absolutely necessary — no uniqueness checks that could cause N+1
- [ ] Uniqueness checks at serializer level use `UniqueValidator` — not manual queryset checks inside `validate()`
- [ ] Serializer validation **does not execute business rules** — those belong in the service layer
- [ ] Error messages in `validate_<field>()` are **user-facing and descriptive** — not internal technical messages
- [ ] Serializer validation never raises unhandled exceptions — all errors raised as `serializers.ValidationError`
- [ ] Read-only fields are **not silently ignored** — they are explicitly excluded from `writable_fields`

## 6.3 Service Layer Design

- [ ] A **service layer exists** — business logic is not split between serializers and views
- [ ] Service functions are **plain Python functions or classes** — no Django request/response objects as parameters
- [ ] Services accept **validated, deserialized data** — not raw request data or serializer instances
- [ ] Each service function has a **single responsibility** — no `process_order()` that does 12 unrelated things
- [ ] Service functions are **independently unit testable** without HTTP context
- [ ] Services do not instantiate serializers — serializers are a view-layer concern
- [ ] Services do not import from `views.py` or DRF — no upward dependency
- [ ] Service layer files are organized per domain app — `orders/services.py`, not a single global `services.py`
- [ ] Services are **stateless** where possible — no service instance holding mutable state between calls
- [ ] Service function signatures are **explicit** — no `**kwargs` hiding what parameters are actually needed

## 6.4 Business Rule Validation

- [ ] All business rules are enforced in the **service layer** — not in views, serializers, or models
- [ ] Business rule violations raise a **custom exception type** — not `ValueError` or bare `Exception`
- [ ] Custom business exceptions are mapped to appropriate HTTP status codes in the exception handler
- [ ] Business rules are **documented** — either via docstrings or linked to a requirements document
- [ ] Business rules are **unit tested exhaustively** — every rule has tests for both valid and invalid cases
- [ ] Business rules that span multiple models are handled in a **single service call** — not split across multiple view operations
- [ ] No business rule is enforced in **only one place** when it could be violated from multiple entry points (API, admin, management commands)
- [ ] Rule violations produce **actionable error messages** — not generic "operation failed" responses

## 6.5 Atomic Transactions

- [ ] Any operation that writes to **multiple tables** is wrapped in `transaction.atomic()`
- [ ] `transaction.atomic()` is applied at the **service layer** — not at the view or serializer layer
- [ ] Nested `transaction.atomic()` blocks use **savepoints** correctly — understood and intentional
- [ ] No **side effects** (sending emails, triggering webhooks, publishing to queues) happen inside `transaction.atomic()` — they run after commit
- [ ] Post-commit side effects use `transaction.on_commit()` — not called directly inside the atomic block
- [ ] `select_for_update()` is used when reading a record that will be immediately updated — preventing race conditions
- [ ] `select_for_update(nowait=True)` or `skip_locked=True` is used where lock contention must be handled gracefully
- [ ] Transactions are **not held open longer than necessary** — no user I/O or external HTTP calls inside an atomic block
- [ ] Database **deadlock scenarios** are identified and mitigated — consistent lock ordering across operations

## 6.6 Idempotency

- [ ] **Create operations** that could be retried (payments, order submissions) are idempotent via idempotency keys
- [ ] Idempotency keys are accepted via a request header (`Idempotency-Key`) or explicit field
- [ ] Duplicate requests with the same idempotency key return the **original response** — not an error or a duplicate record
- [ ] Idempotency key storage has a **TTL** — not stored indefinitely
- [ ] **Background tasks** are idempotent — re-running a task produces the same result as running it once
- [ ] Celery tasks use **unique task IDs** to prevent duplicate execution
- [ ] State machine transitions are idempotent — transitioning to the current state is a no-op, not an error
- [ ] **Webhook processing** is idempotent — the same event processed twice does not create duplicate side effects

## 6.7 State Machine Design

- [ ] Models with lifecycle states (`pending`, `active`, `cancelled`, `completed`) use an **explicit state machine**
- [ ] Valid state transitions are **defined in one place** — not scattered across multiple service functions
- [ ] Invalid state transitions raise a **clear, specific exception** — not a silent no-op or generic error
- [ ] State transitions are **atomic** — state change and related side effects commit together or not at all
- [ ] State history is **recorded** — a log of who changed what state and when
- [ ] No direct field assignment to state fields outside the state machine — always goes through transition methods
- [ ] `django-fsm` or equivalent library is used for complex state machines — not hand-rolled conditionals
- [ ] Every state and every valid transition is **covered by tests**

## 6.8 Business Logic Isolation

- [ ] **No business logic in `models.py`** beyond field definitions, `__str__`, and simple computed properties
- [ ] **No business logic in `serializers.py`** beyond input validation and data transformation
- [ ] **No business logic in `views.py`** — views orchestrate, not compute
- [ ] **No business logic in `signals.py`** — signals are used for decoupling, not for encoding rules
- [ ] **No business logic in `admin.py`** — admin actions call the same service layer as the API
- [ ] Management commands call the service layer — no business logic duplicated inside `handle()`
- [ ] Celery tasks call the service layer — no business logic duplicated inside task functions
- [ ] The service layer is the **single source of truth** for all business rules — any entry point (API, admin, CLI, task) uses the same service functions

## 6.9 Custom Exceptions

- [ ] A base custom exception class exists — `AppException` or equivalent — that all business exceptions inherit from
- [ ] Custom exceptions carry a **machine-readable `code`** attribute (`INSUFFICIENT_BALANCE`, `ORDER_ALREADY_CANCELLED`)
- [ ] Custom exceptions carry a **human-readable `message`** attribute suitable for API error responses
- [ ] Custom exceptions carry an **HTTP status code** hint for the exception handler
- [ ] A **global DRF exception handler** maps all custom exceptions to consistent API error responses
- [ ] The exception handler is registered in `REST_FRAMEWORK['EXCEPTION_HANDLER']`
- [ ] Unexpected exceptions (unhandled `Exception`) are caught at the handler level, logged with full context, and return a generic `500` — never leaking stack traces
- [ ] Custom exceptions are organized in a dedicated `exceptions.py` file per app — not defined inline

## 6.10 Input Sanitization

- [ ] All string inputs are **stripped of leading/trailing whitespace** before processing
- [ ] HTML content submitted by users is **sanitized** via `bleach` or equivalent — not stored raw and rendered unsanitized
- [ ] File upload content types are **validated server-side** — not trusting the client-provided MIME type
- [ ] File upload filenames are **sanitized** — no path traversal characters (`../`) allowed
- [ ] Integer and numeric inputs have **min/max bounds** validated — no unbounded numeric inputs
- [ ] Enum/choice inputs are validated against the **allowed set** — no arbitrary string accepted for a choices field
- [ ] Date and datetime inputs are validated for **format and reasonable range** — no accepting year `9999` or negative timestamps
- [ ] Regex patterns used for validation are **tested against ReDoS** (catastrophic backtracking) attacks

## 6.11 Output Consistency

- [ ] **All responses from the same endpoint** have the same shape — no conditional fields that appear only sometimes
- [ ] Optional fields are always present — returned as `null` when absent, not omitted from the response
- [ ] **Computed fields** in responses are derived at the service or serializer level — not calculated ad hoc in views
- [ ] Boolean fields never return `0`/`1` or `"true"`/`"false"` strings — always proper JSON booleans
- [ ] Numeric fields never return strings — `"42"` vs `42` is consistent across all endpoints
- [ ] Empty collections return `[]` — not `null`, `""`, or omitted
- [ ] Paginated responses always include all pagination metadata — even when returning the first or only page

## 6.12 Third-Party & External Service Calls

- [ ] All external HTTP calls are wrapped in **try/except** with explicit timeout settings
- [ ] External service calls have a **circuit breaker** or retry strategy — not silently failing or blocking indefinitely
- [ ] External calls inside a request cycle are **non-blocking where possible** — offloaded to Celery for slow operations
- [ ] External service failures raise **domain-specific exceptions** — not raw `requests.exceptions.Timeout`
- [ ] Responses from external services are **validated** before being used — no blind trust in third-party data shapes
- [ ] API keys and credentials for external services are **never passed through** to the client in responses
- [ ] External service calls are **mocked in tests** — no real HTTP calls in the test suite
- [ ] Retry logic uses **exponential backoff with jitter** — not fixed interval retries that overwhelm a failing service

## 6.13 Data Integrity & Constraint Enforcement

- [ ] All unique-together constraints are enforced at the **database level** — not just application-level checks
- [ ] Check constraints (`CheckConstraint`) are used for **value range validation** at the DB level
- [ ] Foreign key constraints are never bypassed with raw SQL or `bulk_create(ignore_conflicts=True)` without reason
- [ ] Soft-deleted records are handled in uniqueness — unique constraints account for `is_deleted` flag
- [ ] Cascade deletes are **intentional and documented** — no accidental data loss from `on_delete=CASCADE`
- [ ] Data migrations validate **existing data** before adding new constraints
- [ ] Orphan records are prevented — related records cannot exist without their parent

## 6.14 Celery Task Design & Async Operations

- [ ] Celery tasks accept only **serializable arguments** — no model instances, request objects, or querysets
- [ ] Tasks are **idempotent** — safe to retry without side effects
- [ ] Tasks have explicit **retry policies** — `max_retries`, `retry_backoff`, `retry_jitter` configured
- [ ] Long-running tasks have **timeouts** — `soft_time_limit` and `time_limit` set
- [ ] Task failures are **logged and monitored** — not silently failing
- [ ] Tasks that modify data use **atomic transactions** where needed
- [ ] Task results are stored only if consumed — `ignore_result=True` for fire-and-forget tasks
- [ ] Tasks don't import from views or serializers — only from services/selectors
