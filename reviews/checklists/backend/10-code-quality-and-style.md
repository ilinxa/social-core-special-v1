# 10 — Code Quality & Style Checklist

## 10.1 Linting & Static Analysis

- [ ] **`ruff`** is the primary linter — fast, comprehensive, replaces `flake8`, `pyflakes`, `pycodestyle`, and more
- [ ] `ruff` configuration is in `pyproject.toml` or `ruff.toml` — not scattered across multiple config files
- [ ] **Linting runs in CI** on every PR — failing lint fails the build
- [ ] **Linting runs as a pre-commit hook** — catches issues before they reach CI
- [ ] `ruff` rule set is explicitly configured — not relying on defaults that may change between versions
- [ ] **`flake8-bugbear`** rules are enabled in `ruff` — catches common Python footguns beyond style
- [ ] **`flake8-simplify`** rules are enabled — flags unnecessarily complex code patterns
- [ ] **`pylint`** is considered for deeper static analysis on critical modules — beyond what `ruff` catches
- [ ] **`mypy`** or **`pyright`** runs in CI for static type checking — not just linting
- [ ] Zero linting errors are enforced — no suppressed warnings without documented justification
- [ ] Lint suppressions (`# noqa`, `# type: ignore`) are rare, inline-commented with reason, and reviewed in PRs

## 10.2 Code Formatting

- [ ] **`black`** is used for code formatting — no manual style debates
- [ ] **`isort`** is used for import sorting — configured to be compatible with `black`
- [ ] `black` and `isort` configurations are in `pyproject.toml` — consistent and version-pinned
- [ ] **Formatting runs automatically** as a pre-commit hook — no manually formatted code
- [ ] **Formatting check runs in CI** — unformatted code fails the build
- [ ] `black` line length is set consistently — default `88` or team-agreed value, not mixed
- [ ] `isort` profile is set to `black` — `profile = "black"` in config to avoid conflicts
- [ ] **No mixed indentation** — all files use 4 spaces, no tabs anywhere
- [ ] **No trailing whitespace** anywhere — enforced by pre-commit or editor config
- [ ] **`.editorconfig`** is present — enforces consistent formatting across editors and IDEs

## 10.3 Type Hints

- [ ] **All public function signatures** have type hints — parameters and return types annotated
- [ ] **All service layer functions** are fully typed — the most critical layer for correctness
- [ ] **All serializer fields** that have non-obvious types are annotated
- [ ] **All utility functions** are fully typed
- [ ] Type hints use **modern syntax** — `list[str]` not `List[str]`, `dict[str, int]` not `Dict[str, int]` (Python 3.10+)
- [ ] **`Optional[X]`** is replaced with `X | None` in Python 3.10+ codebases
- [ ] **`TypedDict`** is used for structured dictionary types — not bare `dict[str, Any]`
- [ ] **`Protocol`** is used for duck-typed interfaces — not inheritance where composition is cleaner
- [ ] **`TypeVar`** and **`Generic`** are used correctly for generic utility functions
- [ ] **`Any`** is used sparingly — each usage has a comment explaining why it cannot be more specific
- [ ] **`mypy` strict mode** is the target — at minimum `disallow_untyped_defs = true` and `ignore_missing_imports = false`
- [ ] Type stubs (`py.typed`, `*.pyi`) are present for any internal packages
- [ ] **Django-stubs** and **DRF-stubs** are installed — enabling type checking on ORM and serializer code

## 10.4 Naming Conventions

- [ ] **Variables and functions** use `snake_case` — no `camelCase` in Python code
- [ ] **Classes** use `PascalCase` — no exceptions
- [ ] **Constants** use `UPPER_SNAKE_CASE` — defined at module level, not inline
- [ ] **Private attributes** use a single leading underscore `_name` — double underscore only for name mangling
- [ ] **Boolean variables and functions** use affirmative names — `is_active`, `has_permission`, `can_edit` — not `not_deleted` or `no_access`
- [ ] **Function names are verbs** — `create_order()`, `send_notification()`, not `order()` or `notification()`
- [ ] **Class names are nouns** — `OrderService`, `UserSerializer`, not `ProcessOrder` or `Serializing`
- [ ] **No single-letter variable names** outside of comprehensions and math — `i`, `x` acceptable in loops, not in function signatures
- [ ] **No abbreviations** unless universally understood — `num_users` not `n_usrs`, `config` not `cfg` in public APIs
- [ ] **No Hungarian notation** — no `strName`, `lstItems`, `boolActive`
- [ ] **No misleading names** — a function called `get_user()` only gets, never creates or modifies
- [ ] **Consistent vocabulary** across the codebase — `create` vs `add` vs `insert` used consistently, not interchangeably

## 10.5 Function & Method Design

- [ ] Functions do **one thing** — no function responsible for multiple unrelated concerns
- [ ] Functions are **short** — target under 20 lines, hard limit at 50 lines with documented exception
- [ ] **Cyclomatic complexity** is low — maximum complexity of 10 per function enforced via `ruff`
- [ ] Functions have **no more than 4–5 parameters** — more parameters suggest a missing abstraction
- [ ] Functions with many parameters use a **dataclass or TypedDict** as input — not a long positional argument list
- [ ] **No boolean flag parameters** — `create_user(send_email=True)` should be two functions or use an enum
- [ ] **No output parameters** — functions return values, not modify passed-in containers as side effects
- [ ] **No deeply nested logic** — maximum 3 levels of indentation; extract early returns or helper functions
- [ ] **Early returns** are used to reduce nesting — guard clauses at the top of functions
- [ ] Functions have **no hidden side effects** — a function named `get_X` never writes to the DB
- [ ] **Pure functions** are preferred in utility modules — same input always produces same output
- [ ] Function **docstrings** explain the why and non-obvious behavior — not restating what the code does

## 10.6 Class Design

- [ ] Classes follow the **Single Responsibility Principle** — one class, one reason to change
- [ ] Classes are **small** — target under 200 lines; large classes signal a missing decomposition
- [ ] **No god classes** — a class that knows about everything and does everything
- [ ] **Inheritance is used sparingly** — composition preferred over deep inheritance hierarchies
- [ ] Inheritance hierarchies are **maximum 3 levels deep** — beyond that, composition is cleaner
- [ ] **Abstract base classes** use `abc.ABC` and `@abstractmethod` — not just convention-based "please override this"
- [ ] **`dataclass`** is used for data-holding classes — not plain classes with `__init__` assigning attributes
- [ ] **`__slots__`** is used on high-frequency, memory-sensitive classes where appropriate
- [ ] **Mixin classes** are small, focused, and named with `Mixin` suffix — `TimestampMixin`, not `ExtraStuff`
- [ ] **Class attributes** vs **instance attributes** are not confused — mutable class attributes are a common bug source
- [ ] **`__repr__`** is defined on domain classes — useful for debugging
- [ ] **`__eq__`** and **`__hash__`** are defined together if either is overridden — never one without the other

## 10.7 DRY & Code Reuse

- [ ] **No copy-pasted code blocks** — any logic duplicated more than twice is extracted to a shared utility
- [ ] Shared utilities live in a **`utils/` or `common/` module** — not copy-pasted across apps
- [ ] **Django mixins** are used for shared view behavior — not copy-pasted permission checks across ViewSets
- [ ] **Serializer mixins** are used for shared field sets — not duplicated field declarations across serializers
- [ ] **Abstract model methods** are used for shared model behavior — not copy-pasted `save()` overrides
- [ ] Constants are **defined once** and imported — not redefined with the same value in multiple files
- [ ] No **parallel implementations** of the same logic with slight variations — parameterize instead
- [ ] **Third-party libraries** are used for solved problems — no reinventing pagination, filtering, or validation
- [ ] Reusable components are **tested independently** — not only tested as part of the feature that first needed them

## 10.8 Dead Code & Cleanliness

- [ ] **No commented-out code** anywhere in the codebase — version control is the history, not inline comments
- [ ] **No unused imports** — enforced by `ruff` with `F401` rule
- [ ] **No unused variables** — enforced by `ruff` with `F841` rule
- [ ] **No unused function parameters** — prefixed with `_` if intentionally unused (`_request`)
- [ ] **No unreachable code** — no code after `return`, `raise`, or `continue` statements
- [ ] **No empty `except` blocks** — `except Exception: pass` is never acceptable
- [ ] **No bare `except:`** — always catch specific exception types
- [ ] **No `print()` statements** in production code — use the logging framework
- [ ] **No `TODO` comments older than one sprint** — converted to tracked issues or removed
- [ ] **No experimental or prototype files** committed — `test2.py`, `temp_views.py`, `old_serializer.py`
- [ ] **No debug breakpoints** committed — `pdb.set_trace()`, `breakpoint()`, `ipdb.set_trace()`
- [ ] **No `pass` in exception handlers** without a comment explaining why swallowing the exception is correct

## 10.9 Magic Numbers & Constants

- [ ] **No magic numbers** in business logic — `if attempts > 5:` replaced with `if attempts > MAX_LOGIN_ATTEMPTS:`
- [ ] **No magic strings** — `if status == 'active':` replaced with `if status == OrderStatus.ACTIVE:`
- [ ] Constants are defined at **module level** or in a dedicated `constants.py` — not inline in functions
- [ ] **Enums** (`TextChoices`, `IntegerChoices`, `enum.Enum`) are used for all fixed value sets
- [ ] Time durations are expressed as **`timedelta`** objects — not raw seconds or magic integers
- [ ] HTTP status codes use **`http.HTTPStatus`** constants — not bare `200`, `404`, `500` integers
- [ ] Configuration thresholds (timeouts, limits, retries) are **settings-driven** — not hardcoded constants in code

## 10.10 Comments & Documentation

- [ ] Comments explain **why**, not **what** — the code itself explains what it does
- [ ] Every **public function and class** has a docstring — parameters, return type, and raised exceptions documented
- [ ] Docstrings follow a **consistent format** — Google style, NumPy style, or Sphinx — not mixed
- [ ] **Complex algorithms** have a comment explaining the approach and linking to references
- [ ] **Non-obvious business rules** are commented — `# Per regulation X, amount must be rounded up`
- [ ] **Workarounds and hacks** are commented with a `# HACK:` or `# WORKAROUND:` tag and a linked issue
- [ ] **Deprecated functions** are marked with `@deprecated` or a clear docstring warning — not silently left
- [ ] **`TODO` and `FIXME` comments** reference a ticket number — `# TODO(#1234): refactor after migration`
- [ ] No **misleading comments** — comments that describe what the code used to do, not what it does now
- [ ] Module-level docstrings exist for all non-trivial modules — explaining the module's purpose and scope

## 10.11 Import Organization

- [ ] Imports are organized in **three groups** separated by blank lines: stdlib → third-party → local
- [ ] **`isort`** enforces import ordering automatically — no manual sorting
- [ ] **No wildcard imports** (`from module import *`) anywhere in production code
- [ ] **No circular imports** — detected via `import-linter` or `pydeps` in CI
- [ ] Imports are at the **top of the file** — no inline imports inside functions except for circular import resolution
- [ ] Inline imports inside functions are **commented** explaining why they are deferred
- [ ] **Relative imports** are used within an app — `from .models import User` not `from apps.users.models import User`
- [ ] **Absolute imports** are used across apps — `from apps.orders.models import Order` not relative
- [ ] **`__all__`** is defined in modules that are intended as public APIs — controlling what is exported

## 10.12 Code Review Standards

- [ ] A **code review checklist** exists and is used on every PR — not ad-hoc review criteria
- [ ] PRs are **small and focused** — one concern per PR, target under 400 lines changed
- [ ] **Self-review** is performed by the author before requesting review — no WIP code submitted for review
- [ ] **All review comments are resolved** before merge — no "we'll fix it later" merges
- [ ] **At least one approving review** is required before merge — enforced via branch protection
- [ ] Reviewers check for **security implications** — not just functionality and style
- [ ] **Automated checks** (lint, tests, type check) must all pass before human review begins
- [ ] **Draft PRs** are used for early feedback — clearly labeled, not accidentally merged
- [ ] Review turnaround target is defined — e.g. first review within 24 business hours
- [ ] **Constructive review culture** is documented — how to give and receive feedback professionally

## 10.13 Error Handling Patterns (Added)

- [ ] **Custom exception hierarchy** exists — domain-specific exceptions inherit from a base class
- [ ] Exceptions carry **structured context** — not just string messages
- [ ] **Exception handling is centralized** — DRF exception handler, not try/except in every view
- [ ] **Business rule violations** use a dedicated exception type — not generic `ValueError` or `ValidationError`
- [ ] **Re-raising exceptions** preserves the original traceback — `raise NewError() from original`
- [ ] **Logging happens at the right level** — logged once at the handler, not at every call site
- [ ] **Retry-worthy vs fatal errors** are distinguished — transient errors retry, permanent errors fail fast

## 10.14 Module Organization & Cohesion (Added)

- [ ] Each module has a **clear, single purpose** — `services.py` only has service functions, not utils or validators
- [ ] Large modules are **split by domain** — `services/` package with `member_service.py`, `role_service.py` instead of one 1000-line `services.py`
- [ ] **`__init__.py` files** re-export public interfaces — clean import paths
- [ ] **Circular dependencies between modules** are avoided — dependency graph is acyclic
- [ ] **App boundaries are respected** — apps communicate via services/selectors, not by importing each other's models directly
