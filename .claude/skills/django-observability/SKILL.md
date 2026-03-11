---
name: django-observability
description: Use when adding logging, metrics, or audit trails to any Django app in this project. All apps MUST use apps.core.observability — never use bare logging, print(), or custom audit logic. Covers structlog integration, AuditService, and metrics. Triggers when writing views, services, serializers, tasks, or signal handlers.
---

# Django Observability System

All observability code is in `backend/apps/core/observability/`. Three pillars: structured logging (structlog), audit logging (compliance-grade immutable trail), metrics (NoOp by default, Prometheus-ready).

## Quick Start: Imports

```python
# Logging
from apps.core.observability import get_logger

# Audit
from apps.core.observability import AuditLog, AuditService, AuditSelector, audited

# Metrics
from apps.core.observability import metrics

# Context management (advanced)
from apps.core.observability.logging.context import bind_request_context, clear_request_context
```

## Logging

### Basic Pattern

```python
from apps.core.observability import get_logger

logger = get_logger(__name__)

class UserService:
    @staticmethod
    def create_user(*, data: dict, request=None):
        logger.info("user.create.start", email=data.get("email"))

        try:
            user = User.objects.create(**data)
            logger.info("user.create.success", user_id=user.id)
            return user
        except Exception as e:
            logger.error("user.create.failed", error=str(e), error_type=type(e).__name__)
            raise
```

**Key rules:**
- Use `get_logger(__name__)` to get logger
- Event names: dot notation, 3–4 segments (see Event Naming Convention below)
- Pass structured data as kwargs, never in the message string
- Sensitive fields (password, token, api_key, etc.) are auto-redacted

### Event Naming Convention

Format: `{domain}.{resource}.{action}.{outcome}`

```python
# Authentication
logger.info("auth.login.success", user_id=user.id)
logger.error("auth.login.failed", reason="invalid_password")
logger.info("auth.password.changed", user_id=user.id)

# User domain
logger.info("user.created", user_id=user.id, email=user.email)
logger.info("user.profile.updated", user_id=user.id)

# Email domain
logger.info("email.sent", to=recipient, template="welcome")
logger.error("email.failed", to=recipient, error=str(e))

# HTTP (automatic via middleware)
logger.info("http.request.complete", status_code=200, duration_ms=45.2)

# Celery
logger.info("celery.task.complete", task_id=task.id, duration_ms=1234.5)
```

### Log Levels

- **DEBUG**: Implementation details, cache hits, query execution
- **INFO**: Normal operational events, business milestones (user registered, payment processed)
- **WARNING**: Recoverable errors, rate limits approached, deprecated API usage
- **ERROR**: Unhandled errors affecting single request, validation failures
- **EXCEPTION**: Same as ERROR but includes stack trace (use in exception handlers)
- **CRITICAL**: System-wide failures, data corruption, security incidents

### Structured Data Rules

```python
# ✅ GOOD: Keyword arguments
logger.info("order.placed", order_id=order.id, total=order.total, items=len(order.items))

# ❌ BAD: String interpolation
logger.info(f"Order {order.id} placed with {len(order.items)} items")

# ✅ GOOD: Consistent field names
logger.info("user.login", user_id=user.id)  # Always user_id, not user/user_uuid/uid
logger.info("task.complete", duration_ms=1234.5)  # Always *_ms for milliseconds

# ✅ GOOD: Log IDs, not objects
logger.info("user.created", user_id=user.id, email=user.email)

# ❌ BAD: Logging whole objects (calls __str__, wasteful)
logger.info("user.created", user=user)

# ✅ GOOD: Hash PII if you must log it
import hashlib
email_hash = hashlib.sha256(email.encode()).hexdigest()
logger.info("auth.attempt", email_hash=email_hash)
```

### Context Propagation

RequestLoggingMiddleware (already configured) automatically adds to all logs:
- `request_id`: UUID for request correlation
- `user_id`: Authenticated user ID
- `path`: Request path
- `method`: HTTP method
- `service`: Service name (default: "django-api")

For long operations, manually bind context:

```python
from apps.core.observability.logging.context import bind_request_context

def process_batch(batch_id: str):
    bind_request_context(batch_id=batch_id, operation="batch_process")
    logger.info("batch.start")  # Includes batch_id, operation
    # ... all nested logs include context
    clear_request_context()  # Clean up when done
```

### Exception Logging

```python
# Use logger.exception() in exception handlers for stack trace
try:
    result = risky_operation()
except Exception:
    logger.exception("operation.failed", operation="risky_thing")
    raise
```

### Logging Anti-Patterns

```python
# ❌ String interpolation
logger.info(f"User {user.email} logged in")

# ✅ Structured fields
logger.info("user.login", user_id=user.id, email=user.email)

# ❌ Logging sensitive data
logger.info("auth.attempt", password=password)  # Even if redacted, don't

# ✅ Don't log sensitive data at all
logger.info("auth.attempt", email=email)
```

## Audit Logging

### Basic Pattern

```python
from apps.core.observability import AuditService, AuditLog

class UserService:
    @staticmethod
    def update_profile(*, user, data: dict, request=None):
        old_values = {"email": user.email, "first_name": user.first_name}

        user.email = data.get("email", user.email)
        user.first_name = data.get("first_name", user.first_name)
        user.save()

        new_values = {"email": user.email, "first_name": user.first_name}

        AuditService.log_change(
            action=AuditLog.Action.PROFILE_UPDATED,
            actor=user,
            resource=user,
            before=old_values,
            after=new_values,
            request=request,
        )

        return user
```

### Decorator Pattern

```python
from apps.core.observability import audited, AuditLog

@audited(
    action=AuditLog.Action.SESSION_CREATED,
    actor_param="user",
    include_result=True,
)
def create_session(*, user, device_info: dict, request=None):
    session = DeviceSession.objects.create(user=user, **device_info)
    return session
```

**Decorator params:**
- `action`: AuditLog.Action enum value (required)
- `actor_param`: Func param containing actor (default: "actor")
- `resource_param`: Func param containing resource (optional, uses result if None)
- `request_param`: Func param containing request (default: "request")
- `include_result`: Include result ID in details (default: False)

### When to Audit

**✅ ALWAYS audit:**
- Authentication (login, logout, password changes, token refresh)
- Authorization changes (OAuth link/unlink, session revoke)
- Data modifications of sensitive resources (user create/update/delete, profile changes)
- Sensitive data access/export
- Administrative actions (admin updating users, changing settings)

**❌ NEVER audit:**
- Read operations (except sensitive data)
- Health checks, metrics endpoints
- Automated system operations (cron jobs, scheduled tasks)

### Available Audit Actions

```python
class AuditLog.Action:
    # Authentication
    LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, TOKEN_REFRESH

    # Password
    PASSWORD_CHANGED, PASSWORD_RESET_REQUESTED, PASSWORD_RESET_COMPLETED

    # Email Verification
    VERIFICATION_SENT, EMAIL_VERIFIED

    # OAuth
    OAUTH_LINKED, OAUTH_UNLINKED

    # Sessions
    SESSION_CREATED, SESSION_REVOKED, ALL_SESSIONS_REVOKED

    # User Management
    USER_CREATED, USER_UPDATED, USER_DEACTIVATED, USER_REACTIVATED, USER_DELETED

    # Profile
    PROFILE_UPDATED, AVATAR_CHANGED, AVATAR_DELETED

    # Notifications
    NOTIFICATION_PREFERENCE_UPDATED

    # Email Templates (Admin)
    EMAIL_TEMPLATE_CREATED, EMAIL_TEMPLATE_UPDATED

    # Administrative
    ADMIN_USER_UPDATED, ADMIN_USER_DEACTIVATED, ADMIN_SETTINGS_CHANGED

    # Data Export/Access
    DATA_EXPORTED, SENSITIVE_DATA_ACCESSED
```

**Adding new actions:** Edit `backend/apps/core/observability/audit/models.py`, then run migrations.

### AuditService Methods

**Method 1: `log()` - General audit**

```python
AuditService.log(
    action=AuditLog.Action.SESSION_CREATED,
    actor=user,                    # User performing action
    resource=session,              # Object being acted upon
    request=request,               # For IP, user_agent, request_id
    details={"device": "iPhone"},  # Additional context
)
```

**Method 2: `log_failure()` - Failed actions**

```python
try:
    authenticate(email, password)
except AuthenticationFailed:
    AuditService.log_failure(
        action=AuditLog.Action.LOGIN_FAILED,
        reason="invalid_credentials",
        request=request,
        details={"email_hash": hashlib.sha256(email.encode()).hexdigest()}
    )
    raise
```

**Method 3: `log_change()` - Data changes**

```python
before = {"email": user.email, "first_name": user.first_name}
# ... make changes ...
after = {"email": user.email, "first_name": user.first_name}

AuditService.log_change(
    action=AuditLog.Action.USER_UPDATED,
    actor=admin,
    resource=user,
    before=before,
    after=after,
    request=request,
)
# Automatically filters to only changed fields
```

### Actor Types

```python
class ActorType:
    USER = "user"        # Regular user
    ADMIN = "admin"      # Admin/staff (auto-detected if is_superuser or is_staff)
    SYSTEM = "system"    # Automated process
    ANONYMOUS = "anonymous"  # Unauthenticated
```

### Outcome Types

```python
class Outcome:
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"   # Permission denied
```

### Querying Audit Logs

```python
from apps.core.observability import AuditSelector

# All logs for a user
logs = AuditSelector.for_actor(actor_id=user.id)

# Logs for specific action
login_attempts = AuditSelector.for_action(AuditLog.Action.LOGIN_FAILED)

# Logs for a resource
user_audits = AuditSelector.for_resource(resource_type="User", resource_id=user.id)

# Recent failures
yesterday = timezone.now() - timedelta(days=1)
failures = AuditLog.objects.filter(
    outcome=AuditLog.Outcome.FAILURE,
    timestamp__gte=yesterday
)

# Admin actions
admin_actions = AuditLog.objects.filter(
    actor_type=AuditLog.ActorType.ADMIN,
    timestamp__gte=yesterday
)
```

### Compliance Patterns

**GDPR: Data access request**

```python
def get_user_audit_trail(user_id: uuid.UUID):
    return AuditLog.objects.filter(
        models.Q(actor_id=user_id) | models.Q(resource_id=user_id)
    ).order_by("-timestamp")
```

**SOC2: Brute force detection**

```python
def detect_brute_force(ip_address: str, threshold=5, window_minutes=10):
    cutoff = timezone.now() - timedelta(minutes=window_minutes)
    failed_attempts = AuditLog.objects.filter(
        action=AuditLog.Action.LOGIN_FAILED,
        ip_address=ip_address,
        timestamp__gte=cutoff,
    ).count()

    if failed_attempts >= threshold:
        logger.warning("security.brute_force.detected", ip=ip_address, attempts=failed_attempts)
```

### Security: Immutability & Redaction

**Audit logs cannot be modified or deleted:**

```python
# These raise ValueError
audit.action = AuditLog.Action.USER_UPDATED
audit.save()  # ❌ "AuditLog entries cannot be modified"
audit.delete()  # ❌ "AuditLog entries cannot be deleted"
```

**Sensitive fields auto-redacted:**

```python
REDACTED_FIELDS = [
    "password", "password1", "password2", "old_password", "new_password",
    "token", "access_token", "refresh_token", "api_key", "secret",
    "authorization", "cookie", "session_id", "csrf",
    "credit_card", "card_number", "cvv", "ssn",
]

# Details stored as: {"email": "user@example.com", "password": "[REDACTED]"}
```

**Snapshots, not references:** Audit logs store actor_id, actor_email as values (not FKs) so trail survives user deletion.

### Audit Anti-Patterns

```python
# ❌ Auditing trivial actions
AuditService.log(action="USER_VIEWED_PAGE", ...)

# ✅ Audit only meaningful actions
AuditService.log(action=AuditLog.Action.USER_UPDATED, ...)

# ❌ Logging sensitive data directly
AuditService.log(details={"password": new_password})

# ✅ Don't include sensitive data at all
AuditService.log(action=AuditLog.Action.PASSWORD_CHANGED, actor=user)
```

## Metrics

### Basic Pattern

```python
from apps.core.observability import metrics

class EmailService:
    @staticmethod
    def send_email(*, to: str, template: str, context: dict):
        metrics.increment("email.send.total", tags={"template": template})

        with metrics.timer("email.send.duration_ms", tags={"template": template}):
            try:
                result = backend.send(to, template, context)
                metrics.increment("email.send.success", tags={"template": template})
                return result
            except Exception as e:
                metrics.increment("email.send.failed", tags={
                    "template": template,
                    "error": type(e).__name__
                })
                raise
```

### Metric Types

**Counter** - Monotonically increasing (requests, errors, events processed)

```python
metrics.increment(name, value=1, tags=None)

# Examples
metrics.increment("http.requests.total", tags={"method": "POST", "endpoint": "/api/users"})
metrics.increment("auth.login.total", tags={"method": "password"})
metrics.increment("email.sent.total", tags={"template": "welcome"})
```

**Gauge** - Point-in-time values (active sessions, queue size, memory)

```python
metrics.gauge(name, value, tags=None)

# Examples
active_count = DeviceSession.objects.filter(is_active=True).count()
metrics.gauge("sessions.active", active_count)

queue_size = get_queue_size("email")
metrics.gauge("queue.size", queue_size, tags={"queue": "email"})
```

**Histogram** - Distributions (response times, file sizes)

```python
metrics.histogram(name, value, tags=None)
metrics.timer(name, tags=None)  # Context manager

# Examples
metrics.histogram("http.request.duration_ms", duration_ms)
metrics.histogram("email.size_bytes", len(email_body), tags={"template": "welcome"})

with metrics.timer("db.query.duration_ms", tags={"query": "user_list"}):
    users = User.objects.all()
```

### Tag Design: Low Cardinality Only

Tags create unique metric series. Keep cardinality bounded.

```python
# ✅ GOOD: Low cardinality (< 100 unique values per tag)
metrics.increment("http.requests.total", tags={
    "method": "POST",         # ~10 values
    "endpoint": "/api/users", # ~50 values
    "status": "200",          # ~20 values
})

# ❌ BAD: High cardinality (unbounded)
metrics.increment("http.requests.total", tags={
    "user_id": user.id,       # ❌ Thousands/millions
    "request_id": request_id,  # ❌ Infinite
    "timestamp": str(now),     # ❌ Infinite
    "email": user.email,       # ❌ Unbounded
})
```

**Rule:** Each tag < 100 unique values. Total combinations < 1000.

### Naming Conventions

Format: `{domain}.{resource}.{metric}.{unit}`

```python
# HTTP
http.requests.total          # Counter
http.request.duration_ms     # Histogram
http.response.size_bytes     # Histogram

# Auth
auth.login.total             # Counter
auth.session.duration_ms     # Histogram

# Email
email.sent.total             # Counter
email.send.duration_ms       # Histogram
email.size_bytes             # Histogram

# Database
db.query.total               # Counter
db.query.duration_ms         # Histogram
db.connections               # Gauge

# Celery
celery.task.total            # Counter
celery.task.duration_ms      # Histogram
celery.queue.size            # Gauge

# Business
payment.processed.total      # Counter
payment.amount_cents         # Histogram
signup.total                 # Counter
```

**Unit suffixes:** Always include units
- `_ms` - Milliseconds
- `_seconds` - Seconds
- `_bytes` - Bytes
- `_percent` - Percentage (0-100)
- `_total` - Total count (counter)

### Common Patterns

**Request/response metrics:**

```python
class UserViewSet(viewsets.ModelViewSet):
    def create(self, request):
        metrics.increment("http.requests.total", tags={
            "method": request.method,
            "endpoint": "/api/v1/users/"
        })

        with metrics.timer("http.request.duration_ms", tags={"endpoint": "/api/v1/users/"}):
            try:
                user = UserService.create_user(data=request.data, request=request)
                metrics.increment("user.created.total")

                response = Response(UserSerializer(user).data, status=201)
                metrics.histogram("http.response.size_bytes", len(str(response.data)))
                return response

            except ValidationError:
                metrics.increment("http.requests.failed", tags={
                    "endpoint": "/api/v1/users/",
                    "error": "ValidationError"
                })
                raise
```

**Background task metrics:**

```python
@shared_task
def process_batch(batch_id: str):
    metrics.gauge("celery.queue.size", get_queue_size("batch_processing"), tags={"queue": "batch_processing"})

    with metrics.timer("celery.task.duration_ms", tags={"task": "process_batch"}):
        try:
            items = load_batch_items(batch_id)
            metrics.histogram("batch.size", len(items))

            for item in items:
                process_item(item)
                metrics.increment("batch.items.processed")

            metrics.increment("celery.task.total", tags={"task": "process_batch", "status": "success"})
        except Exception as e:
            metrics.increment("celery.task.total", tags={
                "task": "process_batch",
                "status": "failed",
                "error_type": type(e).__name__
            })
            raise
```

**External API metrics:**

```python
class StripeService:
    @staticmethod
    def create_charge(amount: int, customer: str):
        metrics.increment("external_api.calls.total", tags={"service": "stripe", "endpoint": "/charges"})

        with metrics.timer("external_api.duration_ms", tags={"service": "stripe", "endpoint": "/charges"}):
            try:
                charge = stripe.Charge.create(amount=amount, customer=customer)
                metrics.increment("external_api.calls.success", tags={"service": "stripe", "endpoint": "/charges"})
                return charge
            except stripe.error.CardError:
                metrics.increment("external_api.calls.failed", tags={
                    "service": "stripe",
                    "endpoint": "/charges",
                    "error_type": "CardError"
                })
                raise
```

### Current Implementation: NoOp

By default, metrics are NoOp (zero overhead):

```python
from apps.core.observability.metrics.noop import NoOpMetrics
metrics = NoOpMetrics()  # Does nothing, instant return
```

Add instrumentation now, enable Prometheus later by updating `backend/apps/core/observability/metrics/__init__.py`.

## Integration

### Middleware (Already Configured)

`RequestLoggingMiddleware` is in `backend_core/settings/base.py` after `AuthenticationMiddleware`:

```python
MIDDLEWARE = [
    # ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.observability.logging.middleware.RequestLoggingMiddleware",
    # ...
]
```

**What it does:**
- Generates/extracts `X-Request-ID` for correlation
- Binds `request_id`, `user_id`, `path`, `method` to all logs
- Logs request start and completion with timing
- Adds `X-Request-ID` header to responses
- Skips health endpoints (`/health`, `/healthz`, `/ready`, `/metrics`)

**Access request ID in views:**

```python
def my_view(request):
    request_id = request.request_id  # Set by middleware
```

### Celery Tasks

```python
from celery import shared_task
from apps.core.observability.logging.celery import LoggedTask
from apps.core.observability import get_logger

logger = get_logger(__name__)

@shared_task(base=LoggedTask)
def process_user_data(user_id: str):
    logger.info("task.process.start", user_id=user_id)
    # task_id, task_name, correlation_id automatically bound to context
    logger.info("task.process.complete", user_id=user_id)
```

**Alternative:** Signal-based logging in `backend_core/celery.py`:

```python
from apps.core.observability.logging.celery import connect_celery_signals
connect_celery_signals()
```

### Configuration

Observability is configured in `CoreConfig.ready()` (`apps/core/apps.py`):

```python
def ready(self):
    from apps.core.observability.logging.config import configure_logging
    configure_logging()
```

**Environment behavior:**
- **Development** (`DEBUG=True`): Colored console, DEBUG level
- **Production** (`DEBUG=False`): JSON to stdout, INFO level

**Settings variables:**
- `LOGGING_FORMAT`: "console" or "json" (default: "json")
- `LOGGING_LEVEL`: "DEBUG", "INFO", "WARNING" (default: "INFO")
- `LOGGING_SERVICE_NAME`: Service identifier (default: "django-api")

## Security: Automatic Redaction

Both the logging processor (`sanitize_sensitive_data`) and audit service (`_redact_sensitive_data`) auto-redact the same fields — see the `REDACTED_FIELDS` list in the Audit section above. Redaction is case-insensitive and recursive. Still best practice to never log sensitive data explicitly.
