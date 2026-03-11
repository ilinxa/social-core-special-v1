# Commands

Read this when implementing the command layer — intent expression, use-case boundaries, and when commands are optional vs required.

---

## 1. Role of Commands

Commands represent **explicit user or system intent**. They sit between delivery mechanisms (HTTP, tasks, events) and services.

Commands exist to: make use-cases explicit, decouple intent from delivery, prevent services from becoming god-objects.

> Commands do NOT execute business logic themselves. They express what is being attempted and delegate.

---

## 2. When to Use Commands

**Use commands when:**
- Same use-case triggered from multiple entry points (API, task, consumer, admin)
- Intent has a nameable meaning (`RegisterUser`, `JoinArena`, `SubmitChallengeResult`)
- Pre-conditions or policies must always run consistently
- Clear audit/traceability needed

**Commands are optional when:**
- Action is trivial
- Service only called from one place
- No orchestration or policy needed

> Commands are a **clarity tool**, not a mandatory layer.

---

## 3. Structure

```python
class JoinArena:
    @staticmethod
    def execute(*, user: User, arena: Arena) -> None:
        ArenaPolicy.can_join(user=user, arena=arena)
        ArenaService.join(user=user, arena=arena)
```

Rules: static or class methods only, keyword-only arguments, no hidden dependencies.

File: verb-based intent (`join_arena.py`), Class: imperative (`JoinArena`), Method: `execute()`.

---

## 4. Commands vs Services

| Concern | Command | Service |
|---------|---------|---------|
| Intent expression | ✅ | ❌ |
| Authorization (via policy) | ✅ | ❌ |
| Business workflow | ❌ | ✅ |
| Transactions | ❌ | ✅ |
| Side effects | ❌ | ✅ |

> Commands **describe**, services **decide & execute**.

---

## 5. Commands and Tasks / Consumers

Tasks and consumers SHOULD call commands, not services directly — guarantees policies always run:

```python
@shared_task(base=LoggedTask)
def join_arena_task(user_id, arena_id):
    user = UserSelector.get_by_id(user_id=user_id)
    arena = ArenaSelector.get_by_id(arena_id=arena_id)
    JoinArena.execute(user=user, arena=arena)
```

---

## 6. Error Handling

Commands let domain exceptions bubble up. They do NOT translate errors to HTTP or swallow exceptions. Error mapping belongs to views / API layer / task retry logic.

---

## 7. Testing

Test commands with: unit tests, policy allow/deny cases, service call verification. Focus on correct delegation, policy enforcement, and no side effects inside command.

---

## 8. Anti-Patterns

❌ Commands containing transactions
❌ Commands calling `.save()`
❌ Commands duplicating service logic
❌ Commands branching into multiple workflows
❌ Commands without a clear intent name
