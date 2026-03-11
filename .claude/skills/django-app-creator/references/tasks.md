# Tasks

Read this when implementing async tasks — Celery patterns, LoggedTask, idempotency, retry strategy, concurrency safety, and the canonical async flow.

## Quick Reference — Project Imports

```python
from celery import shared_task
from apps.core.observability.logging.celery import LoggedTask
from apps.core.observability import get_logger

logger = get_logger(__name__)
```

---

## 1. Role of Tasks

Tasks **schedule and execute work outside the request cycle**. They must not become a second business-logic layer.

Tasks SHOULD: be thin wrappers, resolve IDs via selectors, call commands (preferred) or services, implement retry + idempotency, use `base=LoggedTask` for correlation_id.

Tasks MUST NOT: contain business workflows, write to DB directly, call `.save()` / `.update()` / `.delete()`, bypass policies, depend on HTTP request objects.

> **Tasks schedule; Commands/Services decide & execute.**

---

## 2. MANDATORY: Use LoggedTask Base

Always use `LoggedTask` for automatic logging context (task_id, task_name, correlation_id):

```python
@shared_task(bind=True, base=LoggedTask, max_retries=3)
def process_product_task(self, product_id: int):
    """LoggedTask automatically binds task_id, task_name, correlation_id."""
    logger.info("task.process_product.start", product_id=product_id)
    try:
        product = ProductSelector.get_by_id(product_id=product_id)
        ProductService.process(product=product)
        logger.info("task.process_product.complete", product_id=product_id)
    except Exception as exc:
        logger.error("task.process_product.failed", product_id=product_id, error=str(exc), error_type=type(exc).__name__)
        raise self.retry(exc=exc, countdown=60)

@shared_task(base=LoggedTask)
def cleanup_expired_products_task():
    logger.info("task.cleanup_products.start")
    expired = ProductSelector.list_expired()
    count = 0
    for product in expired:
        ProductService.archive_product(product=product)
        count += 1
    logger.info("task.cleanup_products.complete", archived_count=count)
```

---

## 3. Canonical Async Flow

### Preferred (strict)
```
Task → Selector (load) → Command (intent + policy) → Service (transaction + mutation)
```

### Acceptable (minimal)
```
Task → Selector → Service
```

Use strict pattern by default — keeps async behavior consistent with HTTP.

---

## 4. Task Arguments (Primitives Only)

Tasks MUST accept **primitives only** (IDs, strings, numbers). Never pass ORM objects through the queue.

Include correlation identifiers when possible:
```python
def sync_customer_task(*, customer_id: int, request_id: str | None = None) -> None:
    ...
```

---

## 5. Scheduling from Services (CRITICAL)

Always use `transaction.on_commit()`:

```python
@staticmethod
@transaction.atomic
def create_product(...):
    product = ...
    transaction.on_commit(lambda: process_product_task.delay(product.id))
    return product
```

Why: prevents tasks from running before DB commit, avoids race conditions.

> External side effects must occur **after commit**, not during locks.

---

## 6. Idempotency (Mandatory for Side-Effects)

Tasks WILL run multiple times. Strategies:

1. **Idempotency keys** — store in DB/cache, "already processed → no-op"
2. **State-machine fields** — `status=pending|processing|done|failed`, guarded transitions
3. **Unique constraints** — prevent duplicate creation
4. **External idempotency** — pass idempotency headers to third-party APIs

> If a task sends an email, charges a card, or calls external APIs, assume it WILL run twice.

---

## 7. Retry Strategy

Retry **transient** failures: network timeouts, rate limits, temporary outages.
Do NOT retry **permanent** failures: validation errors, permission errors, missing resources.

Use exponential backoff with jitter. Set reasonable max retries.

---

## 8. External I/O & Database Locks

> Never hold DB locks while performing network/file I/O.

In services: write inside transaction, schedule task on commit.
In tasks: load minimal data, perform I/O, write results via services.

---

## 9. Concurrency & Race Safety

Tasks can run concurrently. Rules:
- Use `select_for_update()` in services when needed
- Use unique constraints for de-duplication
- Avoid "check then act" without locking
- For single-run guarantees: DB lock pattern or distributed lock (best-effort)

---

## 10. Logging

Tasks SHOULD log: task name, entity IDs, attempt number, request_id / trace_id.
Log start, complete, and failed events with `task.` prefix.

---

## 11. Testing

Test at two levels:
- **Unit tests**: verify delegation to command/service, retry rules, error classification
- **Integration tests**: use eager execution mode (Celery always_eager), verify DB state changes

Focus on: idempotency (double-run safety), error boundaries, correct object loading via selectors.

---

## 12. Anti-Patterns

❌ `@shared_task` without `base=LoggedTask` — Loses correlation_id
❌ `@shared_task(bind=True, max_retries=3)` without `base=LoggedTask` — Same issue
❌ Passing ORM objects as task args
❌ Business workflows in tasks
❌ Tasks calling `.save()` directly
❌ Scheduling tasks before DB commit (use `transaction.on_commit`)
❌ Retrying permanent errors
❌ Using cache as correctness mechanism
