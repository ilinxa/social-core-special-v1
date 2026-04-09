# E2E Testing — Project Rules

> Governance mandates for the Playwright E2E test suite.
> These rules are **non-negotiable** and override any defaults.

## Architecture Reference

- Architecture spec: `e2e/docs/architecture.md` (v0.2.0)
- Gap analysis: `e2e/docs/system-feature-gap-analysis.md`
- README + quick start: `e2e/docs/README.md`
- Test catalogs: `e2e/docs/plans/l1-smoke-tests.md`, `l2-workflow-tests.md`, `l3-scenario-tests.md`
- Coverage matrix: `e2e/docs/coverage-matrix.md` (auto-generated)
- Gap report: `e2e/docs/reports/gap-report.md` (auto-generated)
- **Test map: `e2e/docs/test-map.json`** (versioned, machine-queryable index of all tests)

## Import Hierarchy (Strict — No Circular)

```
tests/  →  helpers/  →  pages/  →  lib/
  ↓          ↓           ↓         (leaf)
  OK         OK          OK
```

- **Tests** may import from: helpers, pages, lib, fixtures
- **Helpers** may import from: pages, lib
- **Pages** may import from: lib only
- **Lib** may NOT import from: pages, helpers, tests, fixtures
- **Fixtures** may import from: lib, pages
- Circular imports are **forbidden**. If detected, refactor immediately.

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Test files | `*.spec.ts` | `login.spec.ts` |
| Page objects | `*.page.ts` | `login.page.ts` |
| Helpers | `*.helper.ts` | `auth.helper.ts` |
| Fixtures | `*.fixture.ts` | `base.fixture.ts` |
| Lib modules | `*.ts` (no suffix) | `api-client.ts` |

## Selector Priority (Accessibility-First)

Use this order — NEVER skip to a lower priority without justification:

1. `page.getByRole()` — buttons, links, headings, textboxes, etc.
2. `page.getByLabel()` — form inputs with associated labels
3. `page.getByPlaceholder()` — inputs with placeholder text
4. `page.getByText()` — visible text content
5. `page.getByTestId()` — only when no semantic selector exists

**NEVER** use raw CSS selectors (`page.locator('.class')`, `page.locator('#id')`).
**NEVER** use XPath.

## Wait Strategy

- **NEVER** use `page.waitForTimeout(ms)` — this is a fixed sleep and causes flaky tests.
- **ALWAYS** use locator-based waits:
  - `await expect(locator).toBeVisible()` — wait for element to appear
  - `await expect(locator).toHaveText()` — wait for text content
  - `await page.waitForURL()` — wait for navigation
  - `await page.waitForResponse()` — wait for API response
  - `await expect(locator).toHaveCount()` — wait for list items

## Test Isolation

- Each test creates unique data using `test-{uuid}@e2e.com` style identifiers.
- Tests MUST NOT depend on data created by other tests (exception: L3 `test.describe.serial`).
- No shared mutable state between parallel tests.
- L1/L2: API-driven setup (`apiClient`). L3: Progressive UI-driven.

## Test Annotations (Required)

Every test file MUST include JSDoc at the top:

```typescript
/**
 * @layer L1 | L2 | L3
 * @system auth | users | business | platform | chat | network | transactions | forms | cms | notifications | explore | feature-gates | visibility | limits | navigation | public
 * @parameters P1,P2,P3 (comma-separated from P1-P14)
 * @priority P0 | P1 | P2
 */
```

## Forbidden in Committed Code

- `test.only()` — causes other tests to be silently skipped
- `test.skip()` without a comment explaining WHY and a tracking issue
- `console.log()` — use Playwright's built-in trace/report instead
- `page.waitForTimeout()` — use locator-based waits
- Raw CSS/XPath selectors — use accessible selectors
- Hardcoded URLs — use `baseURL` from config or constants
- Hardcoded credentials — use constants or fixtures

## Test Structure Pattern

```typescript
import { test, expect } from '../../fixtures/base.fixture';

/**
 * @layer L1
 * @system auth
 * @parameters P1,P2,P5
 * @priority P0
 */
test.describe('Login Page', () => {
  test('renders login form with all fields', async ({ page }) => {
    // Arrange: navigate
    // Act: interact
    // Assert: verify
  });
});
```

## Page Object Pattern

```typescript
import { type Page } from '@playwright/test';

export class LoginPage {
  constructor(private page: Page) {}

  // Locators (getters, not methods)
  get emailInput() { return this.page.getByLabel('Email'); }
  get passwordInput() { return this.page.getByLabel('Password'); }
  get submitButton() { return this.page.getByRole('button', { name: 'Sign in' }); }

  // Actions (imperative, no assertions)
  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  // Navigation
  async goto() {
    await this.page.goto('/login');
  }
}
```

## Four Playwright Projects

| Project | Test Dir | Viewport | Workers (local / CI) | Retries (local / CI) |
|---------|----------|----------|---------------------|---------------------|
| `smoke-desktop` | `tests/smoke` (excl. responsive/) | 1280x720 | 4 / 2 | 1 / 1 |
| `smoke-mobile` | `tests/smoke/responsive` | iPhone 14 Pro | 2 / 1 | 1 / 1 |
| `workflows` | `tests/workflows` | 1280x720 | 2 / 1 | 0 / 2 |
| `scenarios` | `tests/scenarios` | 1280x720 | 1 / 1 | 0 / 0 |

## Environment

- Backend: `http://localhost:8001` (Daphne ASGI, direct — NOT through frontend proxy)
- Frontend: `http://localhost:3001` (Next.js production build)
- WebSocket: `ws://localhost:8001/ws/`
- PostgreSQL: `localhost:5433` (E2E-isolated DB)
- Redis: `localhost:6380` (E2E-isolated)

## Data Setup Patterns

- L1/L2: Use `apiClient` (direct HTTP to backend:8001) for all data setup
- L3: Use browser UI for progressive state building
- Email verification codes: Use `dbClient.getVerificationCode(email)` (direct PG query)
- Password reset tokens: Use `dbClient.getPasswordResetToken(email)`
- Business max_members: Use `dbClient.setBusinessMaxMembers(id, max)` after creation
- Pre-built auth states: `fixtures/storage-states/*.json` (created by global-setup)

## Feature Gate Testing

- All gates enabled by default in E2E (full deployment config)
- `lib/feature-gates.ts` reads `deployment_config.json` for conditional `test.skip()`
- Feature gate 403 test: toggle gate off → verify 403/UI hide → toggle on → verify restore

## Commit Rules

- Run `npx playwright test --project=smoke-desktop` before committing any test changes
- New test files must include all required JSDoc annotations
- No `.only()`, no `console.log()`, no `waitForTimeout()`
- After adding/removing test files, regenerate reports: `npm run coverage-matrix && npm run gap-report`
- **IMPORTANT: Update `e2e/docs/test-map.json` whenever tests are added, removed, renamed, or moved** (see Test Map section below)

## Test Map (`e2e/docs/test-map.json`)

The test map is the **single source of truth** for what tests exist. It is a versioned JSON file that indexes every test across all 125 files. **Keep it in sync with the codebase.**

### When to Update

| Action | What to update in test-map.json |
|--------|-------------------------------|
| Add a new test file | Add a new entry to the `tests` array |
| Remove a test file | Remove its entry from the `tests` array |
| Rename a test file | Update the `file` field |
| Add/remove/rename a `test()` | Update the `tests` array in that file's entry |
| Change JSDoc annotations | Update `systems`, `parameters`, `priority` |
| Add feature gate dependency | Add/update `feature_gated` array |
| Defer a workflow | Set `"status": "deferred"` and `"deferred_reason"` |
| Bump version | Increment `version` at root level, update `generated` date |

### Entry Schema

```json
{
  "file": "tests/smoke/auth/login.spec.ts",
  "layer": "L1",
  "project": "smoke-desktop",
  "systems": ["auth"],
  "parameters": ["P1", "P2", "P5", "P7"],
  "priority": "P0",
  "serial": false,
  "multi_context": false,
  "feature_gated": ["chat"],
  "status": "deferred",
  "deferred_reason": "Notification inbox API not yet built",
  "tests": [
    "renders login form with all elements",
    "successful login redirects to home"
  ]
}
```

Required fields: `file`, `layer`, `project`, `systems`, `parameters`, `priority`, `serial`, `tests`.
Optional fields: `multi_context`, `feature_gated`, `status`, `deferred_reason`.

### Querying the Test Map

Use `jq` or any JSON tool to answer common questions:

```bash
# How many tests touch the Chat system?
jq '[.tests[] | select(.systems[] == "chat")] | length' test-map.json

# Which files need updating if Transaction service changes?
jq '.tests[] | select(.systems[] == "transaction") | .file' test-map.json

# Which systems have no L2 coverage?
jq '[.tests[] | select(.layer == "L2") | .systems[]] | unique' test-map.json

# All deferred workflows
jq '.tests[] | select(.status == "deferred") | {file, deferred_reason}' test-map.json

# All feature-gated tests
jq '.tests[] | select(.feature_gated) | {file, feature_gated}' test-map.json

# Total test count
jq '[.tests[].tests | length] | add' test-map.json
```

### Version Bumping

- Bump `version` minor (e.g., `1.1` → `1.2`) when adding/removing test files
- Bump `version` major (e.g., `1.2` → `2.0`) for structural changes to the schema
- Always update `summary.total_files`, `summary.total_tests`, and layer counts when totals change

## Lessons Learned

### Raw CSS Selectors in Chained Locators
`locator('[role="option"]')` is a raw CSS selector and violates the selector priority rule.
Use `getByRole('option')` instead — even when chaining off another locator:
```typescript
// BAD:  parentLocator.locator('[role="option"]').first()
// GOOD: parentLocator.getByRole('option').first()
```

### L3 Shared State + Feature Gate Skipping
When L3 serial steps share state (e.g., `let userId: string`), ensure the step that sets the variable
shares the **same feature gate** as all steps that consume it. A variable set inside
`test.skip(!isSystemEnabled('network'))` will be `undefined` if network is disabled, breaking later
steps that only check `getOrgMode()`. Solution: set shared variables in the earliest safe step.

### ESM + TypeScript Scripts
`ts-node` fails with `ERR_UNKNOWN_FILE_EXTENSION` when tsconfig uses ESNext modules.
Use `tsx` instead — it handles ESM/CJS transparently:
```json
"coverage-matrix": "tsx scripts/generate-coverage-matrix.ts"
```

### Multi-Context Login Pattern
For L2/L3 tests needing two users in browsers simultaneously, use `loginInNewContext()` from
`helpers/auth.helper.ts`. Each context must have its own `ApiClient` instance.

### Helper API Patterns
- CMS uses slug-based URLs for sites/pages, UUID-based for media/api-keys
- Business creation via API gets `max_members=1` — call `dbClient.setBusinessMaxMembers()` after
- Registration requires `username` field — auto-derive from email
- `DEFAULT_PASSWORD` is `testpass123` from lib/constants — use for pre-built test users
- Personas using custom passwords should declare them inline (e.g., `'FrankPass123!'`)

## Test Stats (v1.2)

| Category | Files | Tests |
|----------|-------|-------|
| L1 Smoke (desktop) | 96 | 285 |
| L1 Smoke (mobile) | 4 | 21 |
| L2 Workflows | 35 | 37 |
| L3 Scenarios | 10 | 238 |
| **Total** | **145** | **581** |

> Authoritative per-test detail: `e2e/docs/test-map.json` (v1.2)
