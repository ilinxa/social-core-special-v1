# 07 — Testing Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 7.1 Test Architecture & Organization

| ID | Rule | Verdict |
|----|------|---------|
| 7.1.1 | FAIL if tests are in inconsistent locations — some apps have `tests/` inside, others have tests at root level, with no clear convention | PASS/FAIL |
| 7.1.2 | WARN if test directory structure does not mirror source structure (test_views.py → views.py, etc.) | PASS/WARN |
| 7.1.3 | WARN if test files mix concerns — e.g., `test_views.py` contains model or service tests | PASS/WARN |
| 7.1.4 | WARN if any test file exceeds 500 lines without being split into sub-files | PASS/WARN |
| 7.1.5 | WARN if `conftest.py` fixtures are duplicated across multiple test files instead of shared | PASS/WARN |
| 7.1.6 | WARN if test class names don't follow `Test<Subject>` convention | PASS/WARN |
| 7.1.7 | WARN if test method names are unclear or don't describe the scenario being tested | PASS/WARN |
| 7.1.8 | FAIL if `setUp()` contains assertions or business logic beyond fixture setup | PASS/FAIL |
| 7.1.9 | PASS if tests are grouped by behavior/scenario within classes | PASS |
| 7.1.10 | WARN if dead/empty test files exist that are never executed | PASS/WARN |

## 7.2 Test Types & Coverage Balance

| ID | Rule | Verdict |
|----|------|---------|
| 7.2.1 | FAIL if any service function with business logic has zero unit tests | PASS/FAIL |
| 7.2.2 | WARN if any API endpoint has zero integration tests | PASS/WARN |
| 7.2.3 | WARN if custom managers or model methods lack test coverage | PASS/WARN |
| 7.2.4 | WARN if serializer validation logic (validate_<field>, validate) lacks tests | PASS/WARN |
| 7.2.5 | WARN if any custom permission class has no tests for both allow and deny cases | PASS/WARN |
| 7.2.6 | WARN if any Celery task lacks tests for success and failure paths | PASS/WARN |
| 7.2.7 | WARN if Django signals are used but have no tests verifying side effects | PASS/WARN |
| 7.2.8 | WARN if integration tests outnumber unit tests for business logic | PASS/WARN |
| 7.2.9 | WARN if no integration tests exist alongside comprehensive unit tests | PASS/WARN |
| 7.2.10 | FAIL if no coverage threshold is configured or it is below 70% | PASS/FAIL |

## 7.3 Test Isolation

| ID | Rule | Verdict |
|----|------|---------|
| 7.3.1 | FAIL if any test depends on another test having run first — ordering dependency | PASS/FAIL |
| 7.3.2 | FAIL if tests share mutable class-level state that leaks between test methods | PASS/FAIL |
| 7.3.3 | PASS if Django's TestCase or pytest-django's transaction rollback is used for DB isolation | PASS |
| 7.3.4 | WARN if TransactionTestCase is used without clear documented reason | PASS/WARN |
| 7.3.5 | FAIL if monkey-patching persists across test cases — patches not cleaned up | PASS/FAIL |
| 7.3.6 | WARN if temp files or environment variable overrides are not cleaned up after tests | PASS/WARN |
| 7.3.7 | WARN if tests fail when run in a different order (detected by pytest-randomly) | PASS/WARN |
| 7.3.8 | WARN if parallel test execution is not possible due to shared resources | PASS/WARN |

## 7.4 Fixtures & Factories

| ID | Rule | Verdict |
|----|------|---------|
| 7.4.1 | WARN if raw `Model.objects.create()` is used extensively in tests instead of factory_boy | PASS/WARN |
| 7.4.2 | WARN if any model with tests lacks a corresponding factory | PASS/WARN |
| 7.4.3 | WARN if factory defaults are empty strings, `None`, or obviously fake (`"test"`, `"foo"`) | PASS/WARN |
| 7.4.4 | PASS if factories use faker for realistic data generation | PASS |
| 7.4.5 | WARN if related objects are manually created in tests instead of using SubFactory | PASS/WARN |
| 7.4.6 | INFO if factory_boy traits are not used — Traits are convenient but not required | PASS/INFO |
| 7.4.7 | PASS if Django JSON/YAML fixtures are avoided for test data in favor of factories | PASS |
| 7.4.8 | PASS if static reference data fixtures are minimal and version-controlled | PASS |
| 7.4.9 | WARN if fixture loading requires a specific order | PASS/WARN |
| 7.4.10 | FAIL if the same factory class is defined in multiple apps — should be in one canonical location | PASS/FAIL |

## 7.5 Mocking & Patching

| ID | Rule | Verdict |
|----|------|---------|
| 7.5.1 | FAIL if any test makes real external HTTP calls — all must be mocked | PASS/FAIL |
| 7.5.2 | WARN if external SDKs are mocked at HTTP level instead of client/service level | PASS/WARN |
| 7.5.3 | WARN if mocking approach mixes `unittest.mock.patch` and `pytest-mock` inconsistently | PASS/WARN |
| 7.5.4 | FAIL if mocks are applied at the definition site instead of the import site | PASS/FAIL |
| 7.5.5 | INFO if `responses` or `httpretty` library is not used — manual mocking is acceptable | PASS/INFO |
| 7.5.6 | WARN if mocks don't verify they were called when the test depends on a side effect | PASS/WARN |
| 7.5.7 | WARN if mocks over-specify — asserting on internal implementation details instead of behavior | PASS/WARN |
| 7.5.8 | WARN if time-sensitive tests don't mock time — could fail at midnight or year boundaries | PASS/WARN |
| 7.5.9 | FAIL if Celery tasks are not tested synchronously — `CELERY_TASK_ALWAYS_EAGER` not set | PASS/FAIL |
| 7.5.10 | PASS if email backend is configured for testing (locmem or similar) | PASS |

## 7.6 API Integration Tests

| ID | Rule | Verdict |
|----|------|---------|
| 7.6.1 | WARN if any API endpoint lacks a happy-path integration test | PASS/WARN |
| 7.6.2 | WARN if API tests don't cover 401 (unauthenticated) and 403 (unauthorized) responses | PASS/WARN |
| 7.6.3 | WARN if API tests don't cover invalid input scenarios | PASS/WARN |
| 7.6.4 | PASS if DRF's APIClient is used for API tests | PASS |
| 7.6.5 | WARN if tests manually construct JWT tokens instead of using force_authenticate() | PASS/WARN |
| 7.6.6 | FAIL if API tests don't assert response status codes | PASS/FAIL |
| 7.6.7 | WARN if API tests only assert status code without checking response body | PASS/WARN |
| 7.6.8 | WARN if pagination behavior is not tested for list endpoints | PASS/WARN |
| 7.6.9 | WARN if filtering and ordering are not tested | PASS/WARN |
| 7.6.10 | WARN if edge cases (empty lists, boundary values) are not tested | PASS/WARN |
| 7.6.11 | WARN if write operation tests don't verify database side effects | PASS/WARN |
| 7.6.12 | INFO if concurrent request scenarios are not tested — only needed for race-condition-prone endpoints | PASS/INFO |

## 7.7 Model & Database Tests

| ID | Rule | Verdict |
|----|------|---------|
| 7.7.1 | WARN if custom manager methods lack test coverage | PASS/WARN |
| 7.7.2 | INFO if `__str__()` is not tested — low risk | PASS/INFO |
| 7.7.3 | WARN if `clean()` validation is not tested for models that override it | PASS/WARN |
| 7.7.4 | WARN if DB constraints are not tested for constraint violation behavior | PASS/WARN |
| 7.7.5 | WARN if unique_together/UniqueConstraint behavior is not tested | PASS/WARN |
| 7.7.6 | WARN if CheckConstraint violations are not tested | PASS/WARN |
| 7.7.7 | WARN if soft delete behavior is not tested — excluded from default queryset, accessible via unscoped | PASS/WARN |
| 7.7.8 | WARN if `manage.py migrate` from zero is not tested in CI | PASS/WARN |
| 7.7.9 | WARN if `makemigrations --check` is not run in CI | PASS/WARN |
| 7.7.10 | INFO if critical indexes are not tested via EXPLAIN — only needed for performance-critical queries | PASS/INFO |

## 7.8 Service Layer Tests

| ID | Rule | Verdict |
|----|------|---------|
| 7.8.1 | FAIL if any public service function lacks unit tests | PASS/FAIL |
| 7.8.2 | FAIL if service tests use APIClient instead of calling service functions directly | PASS/FAIL |
| 7.8.3 | WARN if service tests don't cover the happy path for every function | PASS/WARN |
| 7.8.4 | WARN if business rule violation scenarios don't have dedicated failure tests | PASS/WARN |
| 7.8.5 | WARN if transactional integrity is not tested — partial failures don't roll back | PASS/WARN |
| 7.8.6 | INFO if `on_commit` callbacks are not tested via captureOnCommitCallbacks() | PASS/INFO |
| 7.8.7 | WARN if state transition tests don't cover both valid and invalid paths | PASS/WARN |
| 7.8.8 | WARN if service tests are slow due to unnecessary DB operations | PASS/WARN |
| 7.8.9 | INFO if idempotency is not explicitly tested — depends on whether operations are expected to be idempotent | PASS/INFO |

## 7.9 Permission & Security Tests

| ID | Rule | Verdict |
|----|------|---------|
| 7.9.1 | FAIL if any custom permission class has no tests | PASS/FAIL |
| 7.9.2 | WARN if permission tests don't cover both has_permission() and has_object_permission() | PASS/WARN |
| 7.9.3 | WARN if role boundary tests are missing — verifying each role's access limits | PASS/WARN |
| 7.9.4 | FAIL if cross-tenant data isolation is not tested in a multi-tenant app | PASS/FAIL |
| 7.9.5 | WARN if IDOR prevention is not tested — guessing other user's resource IDs | PASS/WARN |
| 7.9.6 | WARN if rate limiting behavior is not tested | PASS/WARN |
| 7.9.7 | WARN if authentication requirement is not tested for protected endpoints | PASS/WARN |
| 7.9.8 | WARN if token expiry behavior is not tested | PASS/WARN |
| 7.9.9 | WARN if soft-deleted resource access is not tested | PASS/WARN |

## 7.10 Celery & Async Task Tests

| ID | Rule | Verdict |
|----|------|---------|
| 7.10.1 | WARN if any Celery task lacks unit tests for core logic | PASS/WARN |
| 7.10.2 | FAIL if test settings don't include CELERY_TASK_ALWAYS_EAGER = True | PASS/FAIL |
| 7.10.3 | WARN if retry behavior is not tested for tasks with retry policies | PASS/WARN |
| 7.10.4 | WARN if task idempotency is not tested | PASS/WARN |
| 7.10.5 | WARN if task failure handling is not tested | PASS/WARN |
| 7.10.6 | INFO if on_commit task scheduling is not explicitly tested | PASS/INFO |
| 7.10.7 | WARN if periodic task logic is not tested independently of the scheduler | PASS/WARN |
| 7.10.8 | WARN if task tests only verify task was called, not the resulting state | PASS/WARN |

## 7.11 Test Performance

| ID | Rule | Verdict |
|----|------|---------|
| 7.11.1 | WARN if full test suite takes more than 10 minutes in CI | PASS/WARN |
| 7.11.2 | INFO if pytest-xdist is not used for parallel execution | PASS/INFO |
| 7.11.3 | INFO if --reuse-db is not used for local development | PASS/INFO |
| 7.11.4 | WARN if expensive fixtures are created per-test instead of per-session where safe | PASS/WARN |
| 7.11.5 | INFO if pure unit tests are not separated from DB-hitting tests | PASS/INFO |
| 7.11.6 | FAIL if any test uses `time.sleep()` for synchronization instead of mocking time | PASS/FAIL |
| 7.11.7 | INFO if --durations is not used to identify slow tests | PASS/INFO |
| 7.11.8 | INFO if pytest-randomly is not used to detect test interdependencies | PASS/INFO |

## 7.12 CI Test Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 7.12.1 | FAIL if tests don't run automatically on PR — requires manual trigger | PASS/FAIL |
| 7.12.2 | WARN if CI Python version differs from production | PASS/WARN |
| 7.12.3 | WARN if CI uses SQLite while production uses PostgreSQL | PASS/WARN |
| 7.12.4 | WARN if coverage report is not generated on CI runs | PASS/WARN |
| 7.12.5 | WARN if coverage threshold doesn't fail the CI build | PASS/WARN |
| 7.12.6 | WARN if linting/formatting doesn't run before tests in CI | PASS/WARN |
| 7.12.7 | INFO if test results are not published as CI artifacts | PASS/INFO |
| 7.12.8 | WARN if `manage.py check --deploy` is not run in CI | PASS/WARN |
| 7.12.9 | WARN if `manage.py migrate --check` is not run in CI | PASS/WARN |
| 7.12.10 | WARN if `makemigrations --check` is not run in CI | PASS/WARN |

## 7.13 Test Data & Sensitive Data

| ID | Rule | Verdict |
|----|------|---------|
| 7.13.1 | FAIL if real PII (names, emails, addresses of real people) is used in test data | PASS/FAIL |
| 7.13.2 | FAIL if production data copies are used in tests | PASS/FAIL |
| 7.13.3 | FAIL if real API keys, secrets, or credentials appear in test files | PASS/FAIL |
| 7.13.4 | PASS if test database uses entirely synthetic data | PASS |
| 7.13.5 | INFO if faker seed is not fixed in CI — non-deterministic but acceptable | PASS/INFO |
| 7.13.6 | PASS if test environment variables are isolated from other environments | PASS |

## 7.14 Error Message & Assertion Quality

| ID | Rule | Verdict |
|----|------|---------|
| 7.14.1 | WARN if test failures produce vague messages without context | PASS/WARN |
| 7.14.2 | WARN if `assertTrue(a == b)` is used instead of `assertEqual(a, b)` or `assert a == b` | PASS/WARN |
| 7.14.3 | WARN if collection assertions only check length without verifying contents | PASS/WARN |
| 7.14.4 | WARN if exception assertions don't check both type and message | PASS/WARN |
| 7.14.5 | WARN if tests assert on internal implementation details instead of behavior | PASS/WARN |
| 7.14.6 | WARN if ordering-dependent assertions don't account for non-deterministic DB ordering | PASS/WARN |
| 7.14.7 | INFO if floating-point assertions don't use pytest.approx() — only relevant if floats are tested | PASS/INFO |

## 7.15 Test Documentation & Maintainability

| ID | Rule | Verdict |
|----|------|---------|
| 7.15.1 | WARN if complex test scenarios lack docstrings explaining the business context | PASS/WARN |
| 7.15.2 | WARN if test helper methods are undocumented | PASS/WARN |
| 7.15.3 | WARN if test data setup relies on implicit shared state instead of being self-contained | PASS/WARN |
| 7.15.4 | PASS if tests follow Arrange/Act/Assert pattern clearly | PASS |
| 7.15.5 | WARN if data-driven test variations don't use @pytest.mark.parametrize | PASS/WARN |
| 7.15.6 | WARN if skip markers lack a reason string | PASS/WARN |
| 7.15.7 | WARN if TODO/FIXME comments in tests are not tracked or have no timeline | PASS/WARN |
