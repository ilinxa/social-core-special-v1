# 10 — Code Quality & Style Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 10.1 Linting & Static Analysis

| ID | Rule | Verdict |
|----|------|---------|
| 10.1.1 | FAIL if no linter is configured (ruff, flake8, or equivalent) | PASS/FAIL |
| 10.1.2 | PASS if linter config is in pyproject.toml or dedicated config file | PASS |
| 10.1.3 | FAIL if linting does not run in CI | PASS/FAIL |
| 10.1.4 | WARN if no pre-commit hook for linting | PASS/WARN |
| 10.1.5 | PASS if linter rule set is explicitly configured | PASS |
| 10.1.6 | WARN if bugbear rules not enabled | PASS/WARN |
| 10.1.7 | INFO if simplify rules not enabled | PASS/INFO |
| 10.1.8 | INFO if pylint not used — ruff covers most rules | PASS/INFO |
| 10.1.9 | WARN if no static type checking (mypy/pyright) in CI | PASS/WARN |
| 10.1.10 | WARN if linting errors exist in current codebase | PASS/WARN |
| 10.1.11 | WARN if `# noqa` or `# type: ignore` suppressions are frequent (>20) without documented reasons | PASS/WARN |

## 10.2 Code Formatting

| ID | Rule | Verdict |
|----|------|---------|
| 10.2.1 | FAIL if no auto-formatter is configured | PASS/FAIL |
| 10.2.2 | PASS if import sorting tool is configured | PASS |
| 10.2.3 | PASS if formatter config in pyproject.toml | PASS |
| 10.2.4 | WARN if no pre-commit hook for formatting | PASS/WARN |
| 10.2.5 | FAIL if formatting check not in CI | PASS/FAIL |
| 10.2.6 | PASS if line length is configured consistently | PASS |
| 10.2.7 | PASS if isort profile matches formatter | PASS |
| 10.2.8 | FAIL if mixed indentation (tabs + spaces) found | PASS/FAIL |
| 10.2.9 | WARN if trailing whitespace found in Python files | PASS/WARN |
| 10.2.10 | INFO if no .editorconfig present | PASS/INFO |

## 10.3 Type Hints

| ID | Rule | Verdict |
|----|------|---------|
| 10.3.1 | WARN if >50% of public functions lack type hints | PASS/WARN |
| 10.3.2 | WARN if service layer functions lack type hints | PASS/WARN |
| 10.3.3 | INFO if serializer fields not annotated — Django handles types at runtime | PASS/INFO |
| 10.3.4 | WARN if utility functions lack type hints | PASS/WARN |
| 10.3.5 | INFO if using `List[str]` instead of `list[str]` — style preference for Python 3.10+ | PASS/INFO |
| 10.3.6 | INFO if using `Optional[X]` instead of `X | None` — both valid | PASS/INFO |
| 10.3.7 | PASS if TypedDict used for structured dict parameters where appropriate | PASS |
| 10.3.8 | INFO if Protocol not used — acceptable if inheritance hierarchy is clean | PASS/INFO |
| 10.3.9 | PASS if generics used correctly | PASS |
| 10.3.10 | WARN if `Any` used frequently (>10 times) without justification | PASS/WARN |
| 10.3.11 | WARN if mypy not configured at all | PASS/WARN |
| 10.3.12 | INFO if no py.typed marker — only needed for library packages | PASS/INFO |
| 10.3.13 | INFO if django-stubs not installed — helpful but not required | PASS/INFO |

## 10.4 Naming Conventions

| ID | Rule | Verdict |
|----|------|---------|
| 10.4.1 | FAIL if camelCase used for Python functions or variables | PASS/FAIL |
| 10.4.2 | FAIL if class names don't use PascalCase | PASS/FAIL |
| 10.4.3 | PASS if constants use UPPER_SNAKE_CASE | PASS |
| 10.4.4 | PASS if private attributes use single underscore | PASS |
| 10.4.5 | PASS if boolean names are affirmative (is_*, has_*, can_*) | PASS |
| 10.4.6 | PASS if function names are verbs | PASS |
| 10.4.7 | PASS if class names are nouns | PASS |
| 10.4.8 | WARN if single-letter variables used outside comprehensions/loops | PASS/WARN |
| 10.4.9 | WARN if unclear abbreviations used in public APIs | PASS/WARN |
| 10.4.10 | PASS if no Hungarian notation found | PASS |
| 10.4.11 | WARN if function names are misleading (get_ that creates) | PASS/WARN |
| 10.4.12 | WARN if vocabulary is inconsistent (create vs add vs insert mixed) | PASS/WARN |

## 10.5 Function & Method Design

| ID | Rule | Verdict |
|----|------|---------|
| 10.5.1 | PASS if functions have single responsibility | PASS |
| 10.5.2 | WARN if any function exceeds 50 lines (excluding docstring) | PASS/WARN |
| 10.5.3 | WARN if cyclomatic complexity exceeds 10 in any function | PASS/WARN |
| 10.5.4 | WARN if any function has more than 6 parameters | PASS/WARN |
| 10.5.5 | INFO if keyword-only args not used for functions with many params | PASS/INFO |
| 10.5.6 | INFO if boolean flag params used — common in Django APIs | PASS/INFO |
| 10.5.7 | PASS if no output parameters (mutating passed-in args as return mechanism) | PASS |
| 10.5.8 | WARN if nesting exceeds 4 levels | PASS/WARN |
| 10.5.9 | PASS if early returns used for guard clauses | PASS |
| 10.5.10 | WARN if get_ functions have write side effects | PASS/WARN |
| 10.5.11 | PASS if utility functions are pure where possible | PASS |
| 10.5.12 | WARN if complex functions lack docstrings | PASS/WARN |

## 10.6 Class Design

| ID | Rule | Verdict |
|----|------|---------|
| 10.6.1 | PASS if classes follow SRP | PASS |
| 10.6.2 | WARN if any class exceeds 300 lines | PASS/WARN |
| 10.6.3 | FAIL if a god class exists (>500 lines, knows everything) | PASS/FAIL |
| 10.6.4 | PASS if composition preferred over deep inheritance | PASS |
| 10.6.5 | WARN if inheritance exceeds 3 levels | PASS/WARN |
| 10.6.6 | PASS if ABC used for abstract interfaces | PASS |
| 10.6.7 | PASS if dataclasses used for data-holding classes | PASS |
| 10.6.8 | INFO if __slots__ not used — optional optimization | PASS/INFO |
| 10.6.9 | PASS if mixins are small and follow naming convention | PASS |
| 10.6.10 | FAIL if mutable class-level attributes shared across instances | PASS/FAIL |
| 10.6.11 | INFO if __repr__ not defined on domain classes | PASS/INFO |
| 10.6.12 | WARN if __eq__ overridden without __hash__ | PASS/WARN |

## 10.7 DRY & Code Reuse

| ID | Rule | Verdict |
|----|------|---------|
| 10.7.1 | WARN if significant code blocks are copy-pasted (3+ duplications) | PASS/WARN |
| 10.7.2 | PASS if shared utilities live in dedicated modules | PASS |
| 10.7.3 | PASS if view mixins used for shared behavior | PASS |
| 10.7.4 | PASS if serializer mixins used for shared field sets | PASS |
| 10.7.5 | PASS if abstract models used for shared model behavior | PASS |
| 10.7.6 | WARN if same constant value defined in multiple files | PASS/WARN |
| 10.7.7 | WARN if parallel implementations with slight variations exist | PASS/WARN |
| 10.7.8 | PASS if third-party libs used for solved problems | PASS |
| 10.7.9 | PASS if reusable components have independent tests | PASS |

## 10.8 Dead Code & Cleanliness

| ID | Rule | Verdict |
|----|------|---------|
| 10.8.1 | WARN if commented-out code blocks exist (>5 instances) | PASS/WARN |
| 10.8.2 | PASS if unused imports detected by linter | PASS |
| 10.8.3 | PASS if unused variables detected by linter | PASS |
| 10.8.4 | PASS if unused params prefixed with _ | PASS |
| 10.8.5 | FAIL if unreachable code exists after return/raise | PASS/FAIL |
| 10.8.6 | FAIL if empty except blocks exist without justification | PASS/FAIL |
| 10.8.7 | FAIL if bare `except:` exists (no exception type) | PASS/FAIL |
| 10.8.8 | FAIL if `print()` in production code | PASS/FAIL |
| 10.8.9 | WARN if stale TODO comments exist without issue references | PASS/WARN |
| 10.8.10 | WARN if experimental/prototype files committed | PASS/WARN |
| 10.8.11 | FAIL if debug breakpoints committed | PASS/FAIL |
| 10.8.12 | WARN if `pass` in except without comment | PASS/WARN |

## 10.9 Magic Numbers & Constants

| ID | Rule | Verdict |
|----|------|---------|
| 10.9.1 | WARN if magic numbers appear in business logic | PASS/WARN |
| 10.9.2 | WARN if magic strings used for status/type comparisons | PASS/WARN |
| 10.9.3 | PASS if constants defined at module level or constants.py | PASS |
| 10.9.4 | PASS if enums used for fixed value sets | PASS |
| 10.9.5 | INFO if raw seconds used instead of timedelta — common for TTL configs | PASS/INFO |
| 10.9.6 | WARN if bare HTTP status code integers used in views | PASS/WARN |
| 10.9.7 | PASS if thresholds are settings-driven | PASS |

## 10.10 Comments & Documentation

| ID | Rule | Verdict |
|----|------|---------|
| 10.10.1 | PASS if comments explain why, not what | PASS |
| 10.10.2 | WARN if >30% of public functions lack docstrings | PASS/WARN |
| 10.10.3 | WARN if docstring format is inconsistent across codebase | PASS/WARN |
| 10.10.4 | PASS if complex algorithms are commented | PASS |
| 10.10.5 | PASS if non-obvious business rules are commented | PASS |
| 10.10.6 | PASS if workarounds have HACK/WORKAROUND tags | PASS |
| 10.10.7 | INFO if @deprecated decorator not used — acceptable for early stage | PASS/INFO |
| 10.10.8 | WARN if TODOs lack ticket/issue references | PASS/WARN |
| 10.10.9 | WARN if misleading comments found | PASS/WARN |
| 10.10.10 | WARN if module-level docstrings missing from major modules | PASS/WARN |

## 10.11 Import Organization

| ID | Rule | Verdict |
|----|------|---------|
| 10.11.1 | PASS if imports follow stdlib → third-party → local ordering | PASS |
| 10.11.2 | PASS if isort enforces import ordering | PASS |
| 10.11.3 | FAIL if wildcard imports used in production code | PASS/FAIL |
| 10.11.4 | WARN if circular imports exist | PASS/WARN |
| 10.11.5 | PASS if imports are at file top (with justified exceptions) | PASS |
| 10.11.6 | PASS if inline imports have comments explaining why | PASS |
| 10.11.7 | INFO if relative vs absolute imports not consistent — both valid | PASS/INFO |
| 10.11.8 | INFO if __all__ not defined — optional for internal apps | PASS/INFO |

## 10.12 Code Review Standards

| ID | Rule | Verdict |
|----|------|---------|
| 10.12.1 | INFO if no code review checklist — early-stage/solo acceptable | PASS/INFO |
| 10.12.2 | INFO if PR size guidelines not defined | PASS/INFO |
| 10.12.3 | INFO if self-review not documented as requirement | PASS/INFO |
| 10.12.4 | INFO if review resolution not enforced | PASS/INFO |
| 10.12.5 | INFO if branch protection not configured — no CI yet | PASS/INFO |
| 10.12.6 | INFO if security review not formalized | PASS/INFO |
| 10.12.7 | WARN if no automated checks run before merge | PASS/WARN |
| 10.12.8 | INFO if draft PR convention not established | PASS/INFO |
| 10.12.9 | INFO if review turnaround not defined | PASS/INFO |
| 10.12.10 | INFO if review culture not documented | PASS/INFO |

## 10.13 Error Handling Patterns (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 10.13.1 | PASS if custom exception hierarchy exists | PASS |
| 10.13.2 | PASS if exceptions carry structured context | PASS |
| 10.13.3 | PASS if exception handling is centralized via DRF handler | PASS |
| 10.13.4 | PASS if business rule violations use dedicated exception type | PASS |
| 10.13.5 | WARN if `raise X from Y` not used when re-raising | PASS/WARN |
| 10.13.6 | PASS if logging happens at handler level, not every call site | PASS |
| 10.13.7 | PASS if transient vs permanent errors are distinguished | PASS |

## 10.14 Module Organization & Cohesion (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 10.14.1 | PASS if modules have single clear purpose | PASS |
| 10.14.2 | WARN if any single module exceeds 500 lines without being split | PASS/WARN |
| 10.14.3 | PASS if __init__.py re-exports public interfaces cleanly | PASS |
| 10.14.4 | WARN if circular dependencies between apps exist | PASS/WARN |
| 10.14.5 | PASS if apps communicate via services/selectors, not direct model imports | PASS |
