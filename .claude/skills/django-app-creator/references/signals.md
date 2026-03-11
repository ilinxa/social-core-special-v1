# Signals

Read this when working with Django signals — event reactions, thin handler rule, delegation pattern, idempotency, and the boundary between signals and services.

---

## 1. Role of Signals

Signals react to **events that already happened**. They are NOT a workflow mechanism.

Signals SHOULD: react to domain/framework events, trigger cross-cutting concerns (audit, cache, search index, notifications), delegate to services or tasks, be idempotent.

Signals SHOULD NOT: contain business logic, create or mutate core domain entities, enforce invariants, replace explicit service calls.

> **Signals observe. They do not decide.**

If the system **breaks** when a signal does not run, the logic does not belong in a signal.

---

## 2. Thin Handler Rule (MANDATORY)

Handlers MUST be thin (~10-15 lines max). Allowed: argument inspection, idempotency guards, delegation to services/tasks. Forbidden: ORM writes, business rules, branching workflows.

---

## 3. Delegation Pattern (REQUIRED)

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: UserService.handle_user_created(user_id=instance.id)
        )
```

The service decides **what to do**. The signal only reacts to **when it happened**.

---

## 4. Registration (MANDATORY)

Signals MUST be imported in `apps.py`:

```python
class UsersConfig(AppConfig):
    name = "apps.users"

    def ready(self):
        import apps.users.signals
```

---

## 5. Naming Conventions

- File: `{entity}_signals.py`
- Handler: `on_<entity>_<event>` (describes event, not action)
- Examples: `on_user_created`, `on_user_deleted`

---

## 6. `transaction.on_commit()` Usage

Use when: triggering async tasks, calling external systems, emitting events that must reflect committed state.

Do NOT rely on signals to: guarantee domain invariants, create required related models.

> Domain integrity belongs in **services + database constraints**.

---

## 7. Idempotency & Safety

Signals MAY fire more than once. Handlers MUST be idempotent.

Techniques: `get_or_create`, unique DB constraints, explicit existence checks.

---

## 8. When Signals Are Appropriate

| Use case | Allowed |
|----------|---------|
| Audit logging | ✅ |
| Cache invalidation | ✅ |
| Search index updates | ✅ |
| Notifications / webhooks | ✅ |
| Async task triggering | ✅ |
| Core business logic | ❌ |
| Sequential workflows | ❌ |
| Required domain invariants | ❌ |

---

## 9. Error Handling

Never catch broad `Exception`. Catch only expected errors and log with structured logging:

```python
except IntegrityError:
    logger.warning("profile.already_exists", user_id=instance.id)
```

Never silently swallow invariant violations.

---

## 10. Testing

Verify: signal is registered, delegation is triggered. Do NOT test business logic in signal tests — that belongs in service tests.

---

## 11. Anti-Patterns

❌ Creating related models in signals (use explicit service calls)
❌ Writing to database directly
❌ Complex branching logic
❌ Silent failure on errors
❌ Using signals as implicit workflow engine
