# E2E Testing Suite

> Playwright-based end-to-end testing for the Social Media Advertising Platform.
> **145 test files** | **581 tests** | **3 test layers** | **16 systems** | **14 verification parameters**

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Infrastructure](#infrastructure)
- [Test Layers](#test-layers)
- [Playwright Projects](#playwright-projects)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Global Setup](#global-setup)
- [Fixtures & Auth](#fixtures--auth)
- [Data Setup Patterns](#data-setup-patterns)
- [Feature Gate Integration](#feature-gate-integration)
- [Verification Parameters (P1-P14)](#verification-parameters-p1p14)
- [Reporting & Coverage](#reporting--coverage)
- [Test Map](#test-map)
- [CI/CD Pipeline](#cicd-pipeline)
- [Import Hierarchy](#import-hierarchy)
- [Selector & Wait Rules](#selector--wait-rules)
- [Deferred Tests](#deferred-tests)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Docker Desktop (for the E2E stack)
- Node.js 22+
- The backend and frontend codebases built and ready

### 1. Start the E2E Docker Stack

```bash
make e2e-up
```

### 2. Install Dependencies

```bash
cd e2e
npm install
npx playwright install chromium
```

### 3. Run Tests

```bash
npm run test:smoke      # L1 desktop (~5 min)
npm run test:mobile     # L1 mobile (~3 min)
npm run test:workflows  # L2 workflows (~15 min)
npm run test:scenarios  # L3 personas (~45 min, serial)
npm test                # All of the above
```

### 4. View Reports

```bash
npm run report
```

### 5. Stop the Stack

```bash
make e2e-down
```

---

## Architecture Overview

The E2E suite is organized around three principles:

1. **Layered testing** — L1 smoke (fast, isolated) through L3 scenarios (full journeys)
2. **API-driven setup** — tests create data via backend API, not the browser UI
3. **Complete isolation** — dedicated Docker stack on separate ports, fresh DB per run

```
                         16 Systems
                              |
            L1 Smoke -------- L2 Workflows -------- L3 Scenarios
           (285 tests)        (37 tests)             (238 tests)
           4 workers          2 workers              1 worker (serial)
           ~5 min             ~15 min                ~45 min
                              |
                    14 Verification Parameters (P1-P14)
```

**Key architectural decisions:**

| Decision | Rationale |
|----------|-----------|
| Fresh DB per suite run | Zero state leakage; guaranteed clean slate |
| API-driven L1/L2 setup | 200ms vs 30s per test; data creation invisible to test |
| Progressive L3 setup | Data creation IS the test; verifies real user experience |
| StorageState reuse | Login once globally, reuse auth cookies across all tests |
| All feature gates ON | Full deployment config; architecture supports selective disable |
| Daphne ASGI server | WebSocket support required for chat and real-time tests |

---

## Infrastructure

The E2E stack runs on **dedicated, isolated ports** — completely separate from development.

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| PostgreSQL | postgres:17-alpine | **5433** | E2E-isolated database (`backend_core_e2e_db`) |
| Redis | redis:7-alpine | **6380** | E2E-isolated cache + WebSocket channels |
| Backend | Python 3.12 + Daphne | **8001** | Django ASGI server (NOT gunicorn) |
| Frontend | Node 22 + Next.js | **3001** | Next.js production build (standalone) |

**Stack management:**

| Command | Action |
|---------|--------|
| `make e2e-up` | Start stack, wait for health checks, print endpoints |
| `make e2e-down` | Stop stack (preserves volumes) |
| `make e2e-reset` | Full reset: drop volumes, rebuild images, migrate |
| `make e2e-logs` | Follow Docker logs for all 4 services |

**Docker files:** `docker/docker-compose.e2e.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `entrypoint.sh`

### Environment Variables

Configured in `e2e/.env` (template: `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `E2E_BASE_URL` | `http://localhost:3001` | Frontend URL |
| `E2E_API_URL` | `http://localhost:8001/api/v1` | Backend API |
| `E2E_WS_URL` | `ws://localhost:8001/ws` | WebSocket endpoint |
| `E2E_DB_HOST` | `localhost` | PostgreSQL host |
| `E2E_DB_PORT` | `5433` | PostgreSQL port |
| `E2E_DB_NAME` | `backend_core_e2e_db` | Database name |
| `E2E_DB_USER` | `django_user` | Database user |
| `E2E_DB_PASSWORD` | `django_password` | Database password |
| `E2E_REDIS_URL` | `redis://localhost:6380/0` | Redis connection |
| `E2E_DEFAULT_PASSWORD` | `TestPass123!` | Default password for all test users |
| `E2E_TIMEOUT` | `30000` | Global test timeout (ms) |
| `E2E_ACTION_TIMEOUT` | `15000` | Action timeout (ms) |
| `E2E_DEPLOYMENT_CONFIG_PATH` | `../backend/deployment_config.json` | Feature gate config |

---

## Test Layers

### L1 Smoke Tests — 100 files, 306 tests

Single-system, single-interaction verifications. "Does this page load? Does this button work?"

- **96 desktop files** across 16 categories + **4 mobile responsive files**
- Full parallel execution (4 workers desktop, 2 mobile)
- 1 retry in CI for transient backend errors
- API-driven data setup (no browser interaction for test prerequisites)

**Coverage by system:**

| Directory | Files | Systems |
|-----------|-------|---------|
| `smoke/auth/` | 8 | Login, register, logout, password reset/change, session, OAuth, email verification |
| `smoke/user/` | 7 | Profile view/edit, settings, home/activity feed, other-user, username |
| `smoke/business/` | 13 | Profile, create, console, members, roles, settings, lifecycle, audit, network, transactions |
| `smoke/platform/` | 8 | Profile, console, management, businesses, CMS, forms, transactions, audit |
| `smoke/chat/` | 13 | Conversation list, send message, group, attachments, reactions, requests, blocks |
| `smoke/network/` | 6 | Follow, connect, network page, following/connection list, disconnect |
| `smoke/transactions/` | 7 | Invitation, join request, ownership transfer, list, deny/cancel, form mapping |
| `smoke/forms/` | 6 | Template builder, submission, responses, lifecycle, field CRUD, field types |
| `smoke/cms/` | 12 | Site CRUD, page publish, content editing, media, API keys, templates, permissions, limits |
| `smoke/notifications/` | 7 | Bell, inbox, preferences, delivery flow, API endpoints, RBAC, scopes |
| `smoke/explore/` | 3 | Search businesses, search users, filters |
| `smoke/feature-gates/` | 1 | Feature gate 403 + UI degradation |
| `smoke/limits/` | 3 | Member quota, rate limits, field length limits |
| `smoke/navigation/` | 1 | Account switcher |
| `smoke/public/` | 1 | Landing pages |
| `smoke/responsive/` | 4 | Auth, chat, navigation, business console (iPhone 14 Pro) |

### L2 Workflow Tests — 35 files, 37 tests

Cross-system, multi-step flows. "Can a user register, get invited to a business, and chat with the owner?"

- 2 workers (local), 1 in CI
- Retries: 0 locally, 2 in CI
- 12 workflows require multi-browser contexts (two users simultaneously)
- 15 workflows feature-gated via `test.skip()` on disabled systems
- 3 workflows deferred (blocked on backend APIs — see [Deferred Tests](#deferred-tests))

**Example workflows:**

```
auth-to-profile → business-creation-to-first-member → member-invitation-full-cycle
registration-email-verification → oauth-registration-flow
two-user-chat-realtime → chat-request-dm-block-flow → entity-chat-business-context
form-builder-complete-lifecycle → transaction-form-approval-workflow
cms-business-onboarding → cms-template-lifecycle → cms-cross-context-isolation
network-follow-connect-flow → explore-to-interaction → business-follow-to-join
notification-preferences-roundtrip → notification-scope-isolation
```

### L3 Persona Scenarios — 10 files, 238 tests

Full user journey simulations spanning 15-37 sequential steps per persona.

- **Serial execution** (1 worker, no parallelism) — steps share state
- **0 retries** — must pass on first attempt
- Full video + trace + screenshot recording on all tests
- Mix of API-driven and browser-driven setup (progressive state building)

| Persona | File | Steps | Systems | Focus |
|---------|------|-------|---------|-------|
| Alice (Newcomer) | `persona-alice-newcomer` | 36 | auth, users, explore, network, transactions, business, chat | Complete onboarding |
| Bob (Entrepreneur) | `persona-bob-entrepreneur` | 37 | auth, business, forms, transactions | Business creation to full management |
| Carol (Admin) | `persona-carol-admin` | 17 | auth, platform, business, cms, forms | Platform administration |
| Dave (Social) | `persona-dave-social` | 20 | auth, network, chat, explore | Social features + real-time chat |
| Eve (Adversarial) | `persona-eve-adversarial` | 29 | auth, users, business | XSS, injection, lockout, deactivation |
| Frank (Multi-Context) | `persona-frank-multi-context` | 21 | auth, business | 3 businesses, scope isolation |
| Gary (CMS Manager) | `persona-gary-cms` | 18 | auth, cms, platform | CMS lifecycle management |
| Helen (Business CMS) | `persona-helen-business-cms` | 20 | auth, cms, transactions, business | Business CMS onboarding and publishing |
| Nina (Notifications) | `persona-nina-notifications` | 15 | auth, notifications, business | Notification exploration and preferences |
| Multi-Persona | `multi-persona-interaction` | 21 | auth, business, network, chat, transactions | 5 actors interacting simultaneously |

---

## Playwright Projects

Four projects configured in `playwright.config.ts`:

| Project | Test Dir | Viewport | Workers (local / CI) | Retries (local / CI) | Files | Tests |
|---------|----------|----------|---------------------|---------------------|-------|-------|
| `smoke-desktop` | `tests/smoke` (excl. responsive/) | 1280x720 | 4 / 2 | 1 / 1 | 96 | 285 |
| `smoke-mobile` | `tests/smoke/responsive` | iPhone 14 Pro | 2 / 1 | 1 / 1 | 4 | 21 |
| `workflows` | `tests/workflows` | 1280x720 | 2 / 1 | 0 / 2 | 35 | 37 |
| `scenarios` | `tests/scenarios` | 1280x720 | 1 / 1 | 0 / 0 | 10 | 238 |

**Artifact collection:**

| Project | Traces | Screenshots | Video |
|---------|--------|-------------|-------|
| smoke-desktop | On first retry | On failure | Off |
| smoke-mobile | On first retry | On failure | Off |
| workflows | On first retry | On failure | On first retry |
| scenarios | Always | Always | Always |

---

## Project Structure

```
e2e/
  playwright.config.ts        # 4 projects, timeouts, reporters, global setup/teardown
  global-setup.ts             # DB reset, seed users, create auth storage states
  global-teardown.ts          # Completion logging

  lib/                        # Leaf modules (import nothing from e2e/)
    api-client.ts             # HTTP client → backend:8001/api/v1 (data setup)
    db-client.ts              # Direct PostgreSQL → localhost:5433 (verification codes, seeds)
    constants.ts              # URLs, ports, credentials, timeouts, test users
    types.ts                  # Shared TypeScript types (Auth, Business, CMS, Notifications)
    utils.ts                  # generateEmail(), usernameFromEmail(), retry(), slugify()
    feature-gates.ts          # Reads deployment_config.json for conditional test.skip()
    a11y-checks.ts            # Accessibility audit utilities
    report-annotations.ts     # JSDoc annotation parsing, system normalization

  fixtures/                   # Playwright test fixtures
    base.fixture.ts           # Extended test with apiClient + dbClient
    auth.fixture.ts           # Pre-authenticated pages (regular, business, platform)
    business.fixture.ts       # businessContext (pre-created business + owner)
    cms.fixture.ts            # cmsContext (CMS-enabled business)
    platform.fixture.ts       # platformContext (platform admin + account)
    storage-states/           # 5 pre-built auth JSON files (created by global-setup)

  pages/                      # Page Object Models (34 files, import from lib only)
    base.page.ts              # Shared: sidebar, header, toasts, footer, user menu
    auth/                     # LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage
    user/                     # ProfilePage, HomePage, SettingsPage, ActivityPage, OtherUserProfilePage
    business/                 # BusinessProfilePage, BusinessConsolePage, MembersPage, AuditPage, etc.
    platform/                 # PlatformProfilePage, PlatformConsolePage, PlatformFormsPage, etc.
    chat/                     # ChatPage (conversation list, message view, compose bar)
    cms/                      # SiteDetailPage, PageEditorPage, ApiKeysPage, BusinessCmsPage
    explore/                  # ExplorePage
    forms/                    # FormsPage
    network/                  # NetworkPage
    notifications/            # NotificationsPage
    public/                   # LandingPage
    transactions/             # TransactionsPage

  helpers/                    # API-driven setup functions (10 files)
    auth.helper.ts            # loginViaApi, registerAndVerifyViaApi, loginInNewContext
    business.helper.ts        # createBusinessViaApi, getBusinessMembersViaApi
    chat.helper.ts            # createConversationViaApi, sendMessageViaApi
    cms.helper.ts             # createCmsSiteViaApi, publishCmsPageViaApi, enableCmsForBusinessViaApi
    form.helper.ts            # createTemplateViaApi, addFieldViaApi
    navigation.helper.ts     # goTo, waitForToast, verifyActiveSidebarItem
    network.helper.ts         # followBusinessViaApi, sendConnectionRequestViaApi
    notification.helper.ts    # getNotificationHistoryViaApi, updatePreferenceViaApi
    platform.helper.ts        # createPlatformAccountViaApi
    transaction.helper.ts     # createInvitationViaApi, acceptTransactionViaApi

  tests/
    smoke/                    # L1 — 100 files (96 desktop + 4 mobile)
    workflows/                # L2 — 35 files (32 active + 3 deferred)
    scenarios/                # L3 — 10 files, 238 tests (serial)

  scripts/
    generate-coverage-matrix.ts   # JSDoc → coverage-matrix.md + parameter-checklist.md
    generate-gap-report.ts        # Feature gap analysis → gap-report.md

  docker/
    docker-compose.e2e.yml    # 4 services: PG:5433, Redis:6380, Backend:8001, Frontend:3001
    docker-compose.ci.yml     # CI overrides (faster healthchecks, reduced logging)
    Dockerfile.backend        # Python 3.12 + Daphne ASGI
    Dockerfile.frontend       # Node 22 + Next.js standalone production
    entrypoint.sh             # Wait for PG → migrate → collect static → start Daphne

  docs/
    README.md                 # This file
    architecture.md           # Full architecture spec (v0.2.0)
    test-map.json             # Machine-queryable test index (v1.2, 145 files, 581 tests)
    coverage-matrix.md        # Auto-generated: System x Parameter x Layer matrix
    parameter-checklist.md    # Auto-generated: Per-parameter file listing
    system-feature-gap-analysis.md  # 426-feature audit across 16 systems
    plans/                    # l1-smoke-tests.md, l2-workflow-tests.md, l3-scenario-tests.md, ci-cd-pipeline.md
    reports/gap-report.md     # Auto-generated: Feature area coverage gaps
    versions/CHANGELOG.md     # Version history
```

---

## Running Tests

### By project

```bash
npm run test:smoke          # L1 desktop (96 files, 285 tests)
npm run test:mobile         # L1 mobile (4 files, 21 tests)
npm run test:workflows      # L2 workflows (35 files, 37 tests)
npm run test:scenarios      # L3 personas (10 files, 238 tests)
npm test                    # All 4 projects
```

### By file pattern

```bash
npx playwright test --project=smoke-desktop auth/login
npx playwright test --project=smoke-desktop business/
npx playwright test --project=workflows chat-
npx playwright test --project=scenarios persona-alice
```

### By test name

```bash
npx playwright test -g "valid credentials redirect to home"
```

### Interactive modes

```bash
npm run test:headed         # Visible browser window
npm run test:ui             # Playwright UI mode (interactive)
npm run codegen             # Record new tests (opens codegen at http://localhost:3001)
npx playwright test --debug # Step-through debugger
```

### Makefile shortcuts

```bash
make e2e                    # Run all tests
make e2e-smoke              # L1 desktop
make e2e-mobile             # L1 mobile
make e2e-workflows          # L2 workflows
make e2e-scenarios          # L3 scenarios
make e2e-ui                 # UI mode
make e2e-headed             # Headed mode
make e2e-report             # Open HTML report
```

---

## Global Setup

`global-setup.ts` runs **once before all tests** and performs an 8-step initialization:

| Step | Action | Details |
|------|--------|---------|
| 1 | Health checks | Verify backend (:8001) and frontend (:3001) respond (30 retries, 2s interval) |
| 2 | Database reset | Drop and recreate `backend_core_e2e_db` (clean slate) |
| 3 | Migrations | Run Django migrations via `docker exec` |
| 4 | Create test users | Register 5 users via API with email verification bypass |
| 5 | Setup business owner | Grant permissions, create business (`e2e-test-biz`), set `max_members=10` |
| 6 | Setup platform admin | Make superuser, create platform account + owner membership |
| 7 | Seed CMS templates | Create 2 section templates + 2 block templates |
| 8 | Save storage states | Login as each user via browser, save cookies to JSON files |

**Pre-built test users:**

| User | Email | Role | Storage State |
|------|-------|------|---------------|
| Regular | `e2e-regular@test.com` | Authenticated user | `regular-user.json` |
| Business Owner | `e2e-bizowner@test.com` | Owns "E2E Test Business" | `business-owner.json` |
| Business Member | `e2e-bizmember@test.com` | Member of owner's business | `business-member.json` |
| Platform Admin | `e2e-platform@test.com` | Superuser + platform admin | `platform-admin.json` |
| Second User | `e2e-second@test.com` | For multi-user tests | (shares regular state) |
| Anonymous | — | No auth | `unauthenticated.json` |

All users share the password `TestPass123!` (from `DEFAULT_PASSWORD` constant).

---

## Fixtures & Auth

### Base Fixture

Every test imports from `fixtures/base.fixture.ts` instead of `@playwright/test`:

```typescript
import { test, expect } from '../../fixtures/base.fixture';

test('example', async ({ page, apiClient, dbClient }) => {
  // apiClient: HTTP client pre-configured for backend:8001/api/v1
  // dbClient:  Direct PostgreSQL client for verification codes, seeds
});
```

### Auth Fixtures

`fixtures/auth.fixture.ts` provides pre-authenticated browser pages:

```typescript
import { test, expect } from '../../fixtures/auth.fixture';

test('business owner sees dashboard', async ({ businessOwnerPage }) => {
  await businessOwnerPage.goto('/bconsole/e2e-test-biz');
  await expect(businessOwnerPage.getByRole('heading', { name: /dashboard/i })).toBeVisible();
});
```

| Fixture | Description |
|---------|-------------|
| `authenticatedPage` | Regular user session |
| `businessOwnerPage` | Business owner session |
| `businessMemberPage` | Business member session |
| `platformAdminPage` | Platform admin session |

Each fixture creates a **fresh, independent login session** per test (unique refresh token per parallel worker). Cookies are set with `sameSite: Lax` to match real-user browser behavior.

### Context-specific Fixtures

| Fixture File | Provides | Use Case |
|-------------|----------|----------|
| `business.fixture.ts` | `businessContext` (slug, id, name) | Tests needing a pre-created business |
| `cms.fixture.ts` | `cmsContext` (business + CMS enabled) | CMS-specific tests |
| `platform.fixture.ts` | `platformContext` | Platform admin tests |

---

## Data Setup Patterns

### API-Driven (L1/L2)

Tests create data via the backend API — fast (200ms) and invisible to the test:

```typescript
test('owner invites member', async ({ apiClient, dbClient }) => {
  // Register a fresh user via API
  const user = await registerAndVerifyViaApi(apiClient, dbClient, {
    email: generateEmail('invited'),
  });
  // Create invitation via API
  await createInvitationViaApi(apiClient, {
    targetUserId: user.id,
    contextType: 'business',
    contextId: businessId,
  });
  // Assert via browser or API
});
```

### Browser-Driven (L3)

Scenario tests build state through the UI — the data creation IS the test:

```typescript
test.describe.serial('Alice: The Newcomer', () => {
  test('Step 1: Visit landing page', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading')).toBeVisible();
  });
  test('Step 2: Navigate to register', async ({ page }) => { /* ... */ });
});
```

### Direct Database Access

For operations that bypass the API (Celery tasks, admin-only data):

```typescript
// Get email verification code (created by async Celery task)
const code = await dbClient.getVerificationCode(email);

// Override business member limit
await dbClient.setBusinessMaxMembers(businessId, 10);

// Get password reset token
const token = await dbClient.getPasswordResetToken(email);
```

---

## Feature Gate Integration

The platform supports 3 deployment modes (`full`, `user_and_platform`, `user_only`). Tests automatically skip when a system or feature is disabled:

```typescript
import { isSystemEnabled, getOrgMode } from '../../lib/feature-gates';

test.skip(!isSystemEnabled('chat'), 'Chat system disabled');
test.skip(getOrgMode() === 'user_only', 'Business features disabled');
```

In E2E, **all gates are enabled by default** (full deployment config). The feature gate system supports selective disabling for gate-specific tests:

```typescript
// Verify 403 when gate is off
test('chat endpoints return 403 when disabled', async ({ apiClient }) => {
  // Test uses feature_config_override fixture to disable chat
});
```

---

## Verification Parameters (P1-P14)

Every test is tagged with parameters it verifies, forming a structured coverage matrix.

| Param | Focus | Example Verifications |
|-------|-------|-----------------------|
| **P1** | Render Integrity | Page loads without blank state, text visible, images load, empty states |
| **P2** | User Interaction | Button clicks, form validation, dropdowns, modals, toggles, confirmations |
| **P3** | Navigation | Route transitions, back/forward, deep linking, breadcrumbs, redirects |
| **P4** | Data Accuracy | Lists correct, details complete, search/filter/sort, counts match, mutations reflect |
| **P5** | Auth & Authorization | Login/logout, token refresh, session expiry, protected routes, 403, role-based UI |
| **P6** | Real-Time | WebSocket connection, messages in real-time, typing, presence, reconnect |
| **P7** | Error Handling | Network errors, 404/403/500 pages, rate limits, form error preservation |
| **P8** | Responsive | Layout adapts <768px, hamburger menu, touch targets, single-panel chat |
| **P9** | Visual Regression | Screenshot baselines, no layout shifts, component snapshots |
| **P10** | Limits & Quotas | Member quota, rate limits, file size, text length, graceful degradation |
| **P11** | Security | XSS prevention, CSRF, auth boundaries, role enforcement, safe file upload |
| **P12** | Accessibility | ARIA landmarks, focus trapping, keyboard nav, screen reader, color contrast |
| **P13** | Cross-User | Two users see each other's actions, concurrent ops safe, bidirectional chat |
| **P14** | State Persistence | Refresh preserves login, route, form drafts, notification status, preferences |

Tests declare parameters in their JSDoc block:

```typescript
/**
 * @layer L1
 * @system auth
 * @parameters P1,P2,P5,P7
 * @priority P0
 */
```

---

## Reporting & Coverage

### HTML Report

```bash
npm run report              # Open from last run
```

Interactive HTML report at `reports/e2e-html/index.html` with:
- Pass/fail/skip summary per project
- Per-test duration, screenshots, videos, traces
- Playwright Inspector trace viewer for failed tests

### Coverage Matrix

```bash
npm run coverage-matrix     # System x Parameter x Layer matrix
```

Generates `docs/coverage-matrix.md` + `docs/parameter-checklist.md`:
- 16 systems x 14 parameters = 224-cell matrix
- Shows L1/L2/L3 coverage per cell
- Identifies coverage gaps

### Gap Report

```bash
npm run gap-report          # Feature area gap analysis
```

Generates `docs/reports/gap-report.md`:
- Cross-references 145 test files against expected feature areas
- Reports: covered / partial / missing / deferred status per feature

---

## Test Map

`docs/test-map.json` (v1.2) is the **machine-queryable index** of all 145 test files and 581 tests.

### Schema

```json
{
  "file": "tests/smoke/auth/login.spec.ts",
  "layer": "L1",
  "project": "smoke-desktop",
  "systems": ["auth"],
  "parameters": ["P1", "P2", "P5", "P7"],
  "priority": "P0",
  "serial": false,
  "feature_gated": ["chat"],
  "status": "active",
  "tests": ["renders login form", "successful login redirects to home"]
}
```

### Querying

```bash
# How many tests touch Chat?
jq '[.tests[] | select(.systems[] == "chat")] | length' docs/test-map.json

# Which files need updating if Transactions service changes?
jq '.tests[] | select(.systems[] == "transactions") | .file' docs/test-map.json

# All deferred workflows
jq '.tests[] | select(.status == "deferred") | {file, deferred_reason}' docs/test-map.json

# All feature-gated tests
jq '.tests[] | select(.feature_gated) | {file, feature_gated}' docs/test-map.json

# Total test count
jq '[.tests[].tests | length] | add' docs/test-map.json

# L2 coverage by system
jq '[.tests[] | select(.layer == "L2") | .systems[]] | unique' docs/test-map.json
```

### Maintenance

Update `test-map.json` whenever tests are added, removed, renamed, or moved:

| Action | Update |
|--------|--------|
| Add test file | Add entry to `tests` array, bump version minor |
| Remove test file | Remove entry, bump version minor |
| Rename test | Update `file` field |
| Add/remove `test()` | Update `tests` array in that entry |
| Change JSDoc | Update `systems`, `parameters`, `priority` |

---

## CI/CD Pipeline

| Tier | Trigger | Projects | Budget |
|------|---------|----------|--------|
| **PR** | Pull request | `smoke-desktop` + `smoke-mobile` | <5 min |
| **Main** | Merge to main | Smoke + `workflows` | <20 min |
| **Nightly** | Cron 2am daily | All 4 projects | <60 min |

CI workflows: `.github/workflows/e2e.yml` (PR/main) and `e2e-nightly.yml` (nightly).

CI uses `docker/docker-compose.ci.yml` overrides: faster healthcheck intervals (3s), reduced logging (`DJANGO_LOG_LEVEL=WARNING`), and `docker compose down -v` between runs.

---

## Import Hierarchy

Strict, unidirectional dependency flow. Circular imports are forbidden.

```
tests/  -->  helpers/  -->  pages/  -->  lib/
  |            |              |          (leaf)
  +--> fixtures/              |
         |                    |
         +--> lib/ -----------+
         +--> pages/ ---------+
```

| Layer | May Import From |
|-------|----------------|
| `tests/` | helpers, pages, lib, fixtures |
| `helpers/` | pages, lib |
| `pages/` | lib only |
| `lib/` | Nothing (leaf modules) |
| `fixtures/` | lib, pages, helpers |

---

## Selector & Wait Rules

### Selector Priority (Accessibility-First)

Always use the highest-priority accessible selector available:

| Priority | Selector | When |
|----------|----------|------|
| 1 | `page.getByRole()` | Buttons, links, headings, textboxes, options |
| 2 | `page.getByLabel()` | Form inputs with labels |
| 3 | `page.getByPlaceholder()` | Inputs with placeholder text |
| 4 | `page.getByText()` | Visible text content |
| 5 | `page.getByTestId()` | Only when no semantic selector exists |

**Forbidden:** Raw CSS selectors (`page.locator('.class')`), XPath, `#id` selectors.

### Wait Strategy

Always use locator-based waits. Never use fixed sleeps.

```typescript
// GOOD
await expect(locator).toBeVisible();
await expect(locator).toHaveText('Done');
await page.waitForURL('**/dashboard');
await page.waitForResponse(resp => resp.url().includes('/api/') && resp.ok());

// FORBIDDEN
await page.waitForTimeout(2000);  // Fixed sleep — causes flaky tests
```

---

## Deferred Tests

3 workflow tests are deferred (placeholder with `test.skip()`):

| Test | Blocker | Unblock When |
|------|---------|-------------|
| `notification-triggered-actions.spec.ts` | No notification inbox API | Backend inbox endpoints built |
| `full-notification-lifecycle.spec.ts` | No notification inbox API | Backend inbox endpoints built |
| `audit-trail-verification.spec.ts` | No audit log read API | Backend audit query endpoint built |

---

## Troubleshooting

### Backend not starting

```bash
curl http://localhost:8001/health/                              # Check health
docker compose -f e2e/docker/docker-compose.e2e.yml logs backend-e2e  # Check logs
make e2e-down && make e2e-up                                    # Restart
```

### Database issues

```bash
make e2e-reset              # Full reset: drop volumes, rebuild, migrate
```

### Tests fail with "Element not found"

- Verify the frontend build is current (`npm run build` in `frontend/`)
- Check that page objects match current frontend selectors
- Use `npm run test:headed` to visually debug
- Use `npx playwright test --debug` for step-through debugging

### Storage state expired / auth failures

```bash
npx playwright test --global-setup=./global-setup.ts    # Regenerate auth states
```

### WebSocket tests fail

- Backend must run with **Daphne ASGI** (not Django runserver or gunicorn)
- Verify `ws://localhost:8001/ws/` is reachable
- Check `CHANNEL_LAYERS` config uses E2E Redis (port 6380)

### Flaky tests

- Never use `page.waitForTimeout()` — always use locator-based waits
- Multi-context tests: ensure each context has its own `ApiClient` instance
- For async operations: use `Promise.all([waitForResponse(...), click()])` pattern
- Network tests: handle race conditions with the `retry()` utility from `lib/utils.ts`

### Regenerating reports after test changes

```bash
npm run coverage-matrix     # Regenerate coverage matrix
npm run gap-report          # Regenerate gap report
```

Also update `docs/test-map.json` whenever tests are added, removed, or renamed.
