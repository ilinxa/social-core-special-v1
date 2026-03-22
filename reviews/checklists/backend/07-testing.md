# 07 — Testing Checklist

## 7.1 Test Architecture & Organization

- [ ] Tests live in a **consistent location** across all apps — either `tests/` at root mirroring app structure, or `tests/` inside each app — never mixed
- [ ] Test directory structure **mirrors source structure** — `tests/test_views.py` maps to `views.py`, `tests/test_services.py` maps to `services.py`
- [ ] Each test file has a **single responsibility** — `test_views.py` tests views, not models or services
- [ ] Test files are **never longer than ~300 lines** — split into logical sub-files if growing beyond that
- [ ] `conftest.py` exists at appropriate levels with **shared fixtures** — not duplicated across test files
- [ ] Test class names follow `Test<SubjectUnderTest>` convention — `TestOrderService`, `TestOrderSerializer`
- [ ] Test method names follow `test_<action>_<condition>_<expected_result>` — `test_create_order_with_insufficient_balance_raises_error`
- [ ] No test logic lives inside `setUp()` beyond fixture setup — no assertions, no business logic
- [ ] Tests are **grouped by behavior**, not by method — related scenarios together in one class
- [ ] Dead test files (empty, skipped entirely, or never run) are removed

## 7.2 Test Types & Coverage Balance

- [ ] **Unit tests** exist for all service functions, custom managers, validators, and utility functions
- [ ] **Integration tests** exist for all API endpoints — testing the full request/response cycle
- [ ] **Model tests** exist for custom managers, model methods, properties, and constraints
- [ ] **Serializer tests** exist for validation logic, field-level errors, and cross-field validation
- [ ] **Permission tests** exist for every custom permission class — both allowed and denied cases
- [ ] **Celery task tests** exist for all background tasks — both success and failure paths
- [ ] **Signal tests** exist if Django signals are used — verifying they fire and produce correct side effects
- [ ] No **over-reliance on integration tests** — unit tests cover the majority of business logic
- [ ] No **over-reliance on unit tests** — integration tests verify the system works end to end
- [ ] A minimum **coverage threshold is enforced** in CI — typically 80%+ with no uncovered critical paths

## 7.3 Test Isolation

- [ ] Every test is **fully independent** — no test relies on another test having run first
- [ ] Tests do not share **mutable state** across test cases — no class-level mutable variables
- [ ] Database is **reset between tests** — Django's `TestCase` wraps each test in a transaction that rolls back
- [ ] Tests that require committed data use `TransactionTestCase` explicitly and intentionally
- [ ] No **global state mutation** in tests — no monkey-patching that persists across test cases
- [ ] Tests clean up after themselves — temp files, mocked patches, and env variable overrides are restored
- [ ] Test execution order does not matter — tests pass in any order
- [ ] Parallel test execution works cleanly — no shared resources causing race conditions between workers

## 7.4 Fixtures & Factories

- [ ] **`factory_boy`** is used for object creation — no raw `Model.objects.create()` calls in tests
- [ ] Each model has a corresponding **`ModelFactory`** in a dedicated `factories.py` file
- [ ] Factories define **sensible, realistic defaults** — not empty strings or `None` everywhere
- [ ] Factories use **`faker`** for realistic data — names, emails, addresses, not `"test"` and `"foo"`
- [ ] **Related object factories** use `SubFactory` — not manually creating related objects in each test
- [ ] `factory_boy` traits are used for common variations — `UserFactory(is_admin=True)` not a separate `AdminUserFactory`
- [ ] Django fixtures (JSON/YAML) are avoided for test data — factories are preferred for maintainability
- [ ] Fixtures used for static reference data (countries, currencies) are kept minimal and version-controlled
- [ ] No **fixture dependencies** that require a specific load order — factories handle relationships automatically
- [ ] Factory definitions are **not duplicated** across apps — shared factories live in a common `tests/factories.py`

## 7.5 Mocking & Patching

- [ ] All **external HTTP calls** are mocked — no real network requests in any test
- [ ] All **external service SDKs** (Stripe, AWS, SendGrid) are mocked at the client level — not at the HTTP level
- [ ] `unittest.mock.patch` or `pytest-mock`'s `mocker` fixture is used consistently — not mixed
- [ ] Mocks are applied at the **point of use** — patching where the function is imported, not where it's defined
- [ ] **`responses`** or **`httpretty`** library is used for mocking `requests` HTTP calls
- [ ] Mocks **assert they were called** when the test depends on a side effect having occurred
- [ ] Mocks do not **over-specify** — only assert on what the test actually cares about
- [ ] **Time-sensitive tests** mock `datetime.now()` or use `freezegun` — no tests that fail at midnight or year boundaries
- [ ] **Celery tasks** are tested with `CELERY_TASK_ALWAYS_EAGER = True` in test settings — tasks run synchronously
- [ ] Email sending is mocked via `django.test.utils.override_settings` with `EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'`

## 7.6 API Integration Tests

- [ ] Every API endpoint has at least one **happy path** integration test
- [ ] Every API endpoint has tests for **authentication failure** (`401`) and **authorization failure** (`403`)
- [ ] Every API endpoint has tests for **invalid input** — covering required fields, type errors, and constraint violations
- [ ] **`APIClient`** from DRF test utils is used — not Django's default `Client`
- [ ] Tests use `APIClient.force_authenticate()` for authenticated tests — not manually constructing JWT headers
- [ ] Response **status codes** are asserted on every test — not just response body
- [ ] Response **body structure** is asserted — not just that a `200` was returned
- [ ] **Pagination** behavior is tested — correct `count`, `next`, `previous` in list responses
- [ ] **Filtering and ordering** parameters are tested — results match expected subset
- [ ] **Edge cases** are tested — empty lists, single items, maximum page sizes, boundary values
- [ ] Tests verify **side effects** — database state after a write operation matches expected outcome
- [ ] **Concurrent request** scenarios are tested where race conditions are a risk

## 7.7 Model & Database Tests

- [ ] **Custom manager methods** are tested — each QuerySet method has at least one test
- [ ] **Model `__str__()`** is tested — returns expected human-readable string
- [ ] **Model `clean()`** validation is tested — both valid and invalid inputs
- [ ] **DB constraints** are tested — `IntegrityError` is raised when constraints are violated
- [ ] **`unique_together` and `UniqueConstraint`** are tested — duplicate creation raises the correct error
- [ ] **`CheckConstraint`** violations are tested — invalid values raise `IntegrityError`
- [ ] **Soft delete** behavior is tested — deleted records excluded from default queryset, accessible via unscoped manager
- [ ] **Migration consistency** is tested in CI — `manage.py migrate` from zero passes cleanly
- [ ] **`makemigrations --check`** is run in CI — fails if model changes have no corresponding migration
- [ ] Index existence is tested where critical — verifying indexes are present and used via `EXPLAIN`

## 7.8 Service Layer Tests

- [ ] Every public service function has **unit tests**
- [ ] Service tests **do not use `APIClient`** — they call service functions directly
- [ ] Service tests cover the **happy path** for every function
- [ ] Service tests cover every **business rule violation** — each rule has a dedicated failure test
- [ ] Service tests verify **transactional integrity** — partial failures roll back completely
- [ ] Service tests verify **`on_commit` callbacks** fire correctly using `TestCase.captureOnCommitCallbacks()`
- [ ] Service tests verify **state transitions** — valid transitions succeed, invalid ones raise exceptions
- [ ] Service tests are **fast** — no unnecessary DB operations, minimal fixture setup
- [ ] Service tests cover **idempotency** — calling the same function twice produces the same result

## 7.9 Permission & Security Tests

- [ ] Every custom **permission class** has dedicated unit tests
- [ ] Permission tests cover **both `has_permission()` and `has_object_permission()`**
- [ ] Permission tests verify **role boundaries** — each role can only access what it should
- [ ] Tests verify **cross-tenant data isolation** — user from tenant A cannot access tenant B's data
- [ ] Tests verify **IDOR prevention** — guessing another user's resource ID returns `403` or `404`
- [ ] Tests verify **rate limiting** — throttled endpoints return `429` after threshold is exceeded
- [ ] Tests verify **authentication requirement** — protected endpoints return `401` without credentials
- [ ] Tests verify **token expiry** — expired tokens are rejected with `401`
- [ ] Tests verify **soft-deleted resource access** — deleted records return `404` to regular users

## 7.10 Celery & Async Task Tests

- [ ] Every Celery task has **unit tests** for its core logic
- [ ] Task tests run with **`CELERY_TASK_ALWAYS_EAGER = True`** — tasks execute synchronously in tests
- [ ] Task **retry behavior** is tested — transient failures trigger retries, permanent failures do not
- [ ] Task **idempotency** is tested — running the same task twice produces the correct result
- [ ] Task **failure handling** is tested — exceptions are caught, logged, and handled gracefully
- [ ] `on_commit` task scheduling is tested — tasks are only enqueued after the transaction commits
- [ ] **Periodic tasks** (Celery Beat) have tests verifying their logic independent of the scheduler
- [ ] Task result and state are verified after execution — not just that the task was called

## 7.11 Test Performance

- [ ] Full test suite runs in **under 5 minutes** in CI — slow tests are identified and optimized
- [ ] **`pytest-xdist`** is used for parallel test execution in CI — reducing total run time
- [ ] Database setup uses `--reuse-db` (`pytest-django`) in local development — avoiding full DB recreation on every run
- [ ] Heavy fixtures are created **once per test session** using `scope='session'` where safe
- [ ] Tests that hit the DB are marked separately from **pure unit tests** — unit tests can run without DB
- [ ] No test uses `time.sleep()` — use `freezegun` or mock time instead
- [ ] Slow tests are identified with `--durations=10` and optimized or isolated
- [ ] **`pytest-randomly`** is used to randomize test order — detecting hidden test interdependencies

## 7.12 CI Test Configuration

- [ ] Tests run **automatically on every PR** — no manual trigger required
- [ ] CI runs tests against the **same Python version** as production
- [ ] CI runs tests against the **same database version** as production — not SQLite in CI, PostgreSQL in prod
- [ ] Coverage report is **generated and published** on every CI run
- [ ] Coverage below the threshold **fails the CI build** — not just a warning
- [ ] **Linting and formatting checks** run before tests — failing fast on style issues
- [ ] Test results are published as **CI artifacts** — accessible for debugging failures
- [ ] **`manage.py check --deploy`** runs in CI against production settings
- [ ] **`manage.py migrate --check`** runs in CI — fails if unapplied migrations exist
- [ ] **`makemigrations --check`** runs in CI — fails if model changes have no migration

## 7.13 Test Data & Sensitive Data

- [ ] **No real PII** is used in test data — all names, emails, addresses are faker-generated
- [ ] **No production data** is used in tests — even anonymized dumps avoided in favor of factories
- [ ] **No hardcoded credentials** in test files — test API keys use clearly fake values (`sk_test_fake`)
- [ ] Test database is **never a copy of production** — entirely synthetic data
- [ ] Faker seeds are **fixed in CI** — deterministic fake data across runs for reproducibility
- [ ] Test environment variables are set in a dedicated **`.env.test`** or `conftest.py` — not polluting other environments

## 7.14 Error Message & Assertion Quality

- [ ] Test failures produce **descriptive messages** — custom `msg=` parameter or assertion libraries used
- [ ] Assertions use the **most specific assert** available — `assertEqual` not `assertTrue(a == b)`
- [ ] Collection assertions check **contents, not just length** — `assertIn(item, results)` not just `len(results) == 3`
- [ ] Exception assertions use **`pytest.raises(ExceptionType, match="pattern")`** — checking type AND message
- [ ] No assertions on **implementation details** — tests assert behavior/outcomes, not internal method calls
- [ ] Flaky assertions on **ordering** use `set()` comparison or sorted lists — not relying on DB ordering guarantees
- [ ] Floating-point assertions use **`pytest.approx()`** — not exact equality

## 7.15 Test Documentation & Maintainability

- [ ] Complex test scenarios have **docstrings** explaining the business context being tested
- [ ] Test helper methods and custom assertions are documented
- [ ] Test data setup is **self-contained** within each test — not relying on implicit shared state
- [ ] Tests are **readable by someone unfamiliar** with the codebase — Arrange/Act/Assert pattern is clear
- [ ] Parameterized tests use **`@pytest.mark.parametrize`** for data-driven test variations
- [ ] Skip markers (`@pytest.mark.skip`, `@pytest.mark.skipif`) include a **reason string**
- [ ] TODO/FIXME comments in tests are tracked — no abandoned test stubs
