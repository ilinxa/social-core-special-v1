# E2E Test Architecture — Social Media Advertising Platform

> **Status**: DRAFT — Pending review and approval
> **Version**: 0.2.0
> **Date**: 2026-03-27
> **Scope**: Full-stack browser-based end-to-end testing
> **Companion**: [System Feature Gap Analysis](system-feature-gap-analysis.md) — feature-by-feature audit (426 features, 17 systems)

---

## Table of Contents

1. [Purpose & Goals](#1-purpose--goals)
2. [Current Test Coverage (Gap Analysis)](#2-current-test-coverage-gap-analysis)
3. [Foundational Decisions](#3-foundational-decisions)
4. [Test Layer Architecture](#4-test-layer-architecture)
5. [Test Data Strategy](#5-test-data-strategy)
6. [E2E Parameter Framework (P1–P14)](#6-e2e-parameter-framework-p1p14)
7. [Project File Structure](#7-project-file-structure)
8. [Page Object Model (POM)](#8-page-object-model-pom)
9. [L1 Smoke Tests — Complete Catalog](#9-l1-smoke-tests--complete-catalog)
10. [L2 Workflow Tests — Complete Catalog](#10-l2-workflow-tests--complete-catalog)
11. [L3 Persona Scenarios — Complete Catalog](#11-l3-persona-scenarios--complete-catalog)
12. [Multi-Persona Interaction Scenario](#12-multi-persona-interaction-scenario)
13. [CI/CD Pipeline](#13-cicd-pipeline)
14. [Docker Infrastructure](#14-docker-infrastructure)
15. [Feature Gate Testing Design](#15-feature-gate-testing-design)
16. [Reporting & Coverage](#16-reporting--coverage)
17. [Run Strategy & Time Budgets](#17-run-strategy--time-budgets)
18. [Decision Log](#18-decision-log)

---

## 1. Purpose & Goals

### Why E2E Tests?

The platform has strong lower-level coverage:

- **4,241 backend unit tests** — models, services, selectors, policies, views (mocked)
- **312 API integration tests** — 13 phases, real database, HTTP-level
- **1,645 frontend unit tests** — components, hooks, stores (mocked APIs)

What's missing is the **top layer**: tests that verify the full stack works together through a **real browser**, with a real backend, real database, and real frontend — exactly as a user experiences it.

### Goals

1. **Prove the system works end-to-end** — browser → frontend → API → backend → database → back
2. **Catch integration bugs** that unit tests miss (routing, auth flow, real-time, state persistence)
3. **Validate user journeys** — not just features in isolation, but realistic multi-step workflows
4. **Push boundaries** — adversarial personas that actively try to break the app
5. **Enforce limits** — verify quota enforcement, rate limiting, and field validation from the UI
6. **Establish a regression safety net** — catch regressions before they reach production
7. **Provide living documentation** — tests describe what the app actually does

### What E2E Tests Should NOT Do

- Re-test API logic already covered by API integration tests
- Test implementation details (internal state, function calls)
- Replace unit tests for edge cases (combinatorial testing stays at unit level)

### What E2E Tests Focus On

- **UI rendering** — does the page show the right thing?
- **User interactions** — clicks, forms, navigation, modals
- **Real-time features** — WebSocket chat, live updates, presence indicators
- **Cross-user interaction** — two users interacting simultaneously
- **Responsive behavior** — mobile vs desktop layouts
- **Error states** — what the user sees when things fail
- **Security boundaries** — can a user access things they shouldn't?
- **Limit enforcement** — what happens when quotas are exceeded?
- **Visual regression** — does the UI look the same as the approved baseline?
- **State persistence** — does data survive page refresh, re-login, context switch?

---

## 2. Current Test Coverage (Gap Analysis)

### Systems in the Platform

| # | System | Backend App | Frontend Feature | Routes | Unit Tests | API Tests |
|---|--------|-------------|-----------------|--------|-----------|-----------|
| 1 | Auth | `apps.auth` | `features/auth` | 7 auth routes | Yes | Phase 1 |
| 2 | Users | `apps.users` | `features/users` | profile, settings, sessions, home, activity (8 routes) | Yes | Phase 2 |
| 3 | Organization (Business) | `apps.organization.business` | `features/business` | Public profile + console (**27 routes**) | 226 | Phase 4 |
| 4 | Organization (Platform) | `apps.organization.platform` | `features/platform` | Public profile + console (**25 routes**) | 226 | Phase 3, 5 |
| 5 | RBAC | `apps.rbac` | (integrated) | (via business/platform console) | 361 | Phase 4, 5 |
| 6 | Transactions | `apps.transaction` | `features/transactions` | **6 business + 6 platform routes** (list, detail, settings) | 471 | Phase 6 |
| 7 | Forms | `apps.forms` | `features/forms` | **7 business + 7 platform routes** (templates, library, responses) | 465 | Phase 7 |
| 8 | Chat | `apps.chat` | `features/chat` | 3 chat routes (user, business, platform) | 387 | — |
| 9 | Network | `apps.network` | `features/network` | **3 routes** (network page, business followers, business connections) | 92 | — |
| 10 | Explore | `apps.explore` | `features/explore` | Explore page + search | Yes | — |
| 11 | CMS | `apps.cms` | `features/cms` (platform) | **6 platform console routes** (sites, templates, api-keys, media) | 165 | Phase 8 |
| 12 | Notifications | `apps.notifications` | (integrated) | Notification center | Yes | Phase 9 |
| 13 | Feature Gates | `apps.core.feature_config` | (integrated) | — (98 enforcement points) | 204 | Phase 13 |
| 14 | Content Visibility | `apps.core.visibility` | (integrated) | — | 101 | — |
| 15 | Email | `apps.email` | — | — | Yes | — |
| 16 | Activity | (in `apps.users`) | `features/activity` | 2 routes (`/activity`, `/activity/[id]`) | — | — |
| 17 | Public/Landing | — | `app/(marketing)` | 3 routes (`/`, `/about`, `/contact`) | — | — |
| 18 | Admin | — | `app/(app)/admin` | 1 route (`/admin`) | — | — |

### What E2E Will Cover That Others Don't

| Gap | Example | Why Unit/API Tests Miss It |
|-----|---------|---------------------------|
| Full auth flow through browser | Register → email verify → login → protected route | Unit tests mock auth; API tests don't test UI redirects |
| Real-time WebSocket in browser | Two users chatting live | API tests are HTTP-only |
| Frontend routing + guards | Deep link to protected page → redirect → return | Frontend tests mock router |
| Account context switching | Switch between personal/business/platform | No test covers UI state transitions |
| Responsive layouts | Chat single-panel on mobile | Frontend tests use happy-dom (no layout) |
| Visual regression | Button placement, spacing, alignment | No existing visual tests |
| Cross-user workflows | Alice invites Bob, Bob accepts | API tests simulate but don't test both UIs |
| Limit enforcement from UI | Exceed quota → see error message | API tests verify HTTP 400, not the UI message |
| Session/state persistence | Refresh page → still logged in, data intact | Frontend tests don't test real browser storage |

---

## 3. Foundational Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Framework** | Playwright | Best-in-class for modern web apps. Auto-wait, multi-browser context, trace viewer, built-in screenshot comparison |
| **Browser** | Chromium only | Speed over coverage; Chromium matches 80%+ of real users. Firefox/Safari can be added later without architecture changes |
| **Mobile testing** | Playwright mobile viewport emulation | Not real devices. Emulated viewport (iPhone 14 Pro, 393×852) tests responsive CSS breakpoints |
| **Visual regression** | Playwright `toHaveScreenshot()` | Built-in, baseline files committed to git, CI comparison |
| **Multi-user testing** | Playwright `browser.newContext()` | Multiple isolated browser contexts in one test = two users interacting simultaneously |
| **WebSocket testing** | Real WebSocket through browser | Not mocked. Tests connect to real backend Channels/WebSocket layer |
| **Test runner** | Playwright Test (built-in) | Parallel execution, fixtures, projects, HTML reports |
| **Language** | TypeScript | Matches frontend codebase; shared types possible |
| **Page abstraction** | Page Object Model (POM) | Locators in one place; when UI changes, update one file, not 50 tests |
| **Auth strategy** | Playwright `storageState` | Login once in global setup, reuse saved cookies/tokens across tests |
| **Feature gates** | All enabled (day 1) | Full deployment config. Architecture allows selective disable via config later |
| **Limits** | Tested from day 1 | Quotas, rate limits, field lengths — critical for production correctness |

---

## 4. Test Layer Architecture

### Three Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  L3  SCENARIOS — Full user personas, adversarial, long-running  │
│      "Alice registers, grows, interacts over 20+ steps"         │
├─────────────────────────────────────────────────────────────────┤
│  L2  WORKFLOWS — Cross-domain, multi-step, realistic flows      │
│      "Register → create business → invite member → member       │
│       accepts → appears in console"                             │
├─────────────────────────────────────────────────────────────────┤
│  L1  SMOKE — Single feature, isolated, fast, happy path         │
│      "Login page renders, valid login succeeds"                 │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Characteristics

| Property | L1 Smoke | L2 Workflow | L3 Scenario |
|----------|----------|-------------|-------------|
| **Scope** | Single feature | 2–4 systems | 5+ systems, full journey |
| **Steps** | 1–5 | 5–15 | 15–30+ |
| **Data setup** | API-driven per test | API-driven per file | Progressive (UI-driven) |
| **Isolation** | Fully isolated between tests | Isolated between files | Isolated between scenarios |
| **Parallelism** | Full parallel | Moderate parallel | Sequential within scenario |
| **Run time** | < 30s per test | 1–3 min per workflow | 5–15 min per scenario |
| **When to run** | Every PR | Merge to main | Nightly + release |
| **Time budget** | < 5 min total | < 15 min total | < 60 min total |
| **Test count** | ~45 tests | ~16 workflows | ~7 scenarios |
| **Failure means** | Feature broken | Integration broken | User journey broken |

### Composition — No Duplication

L1 tests are building blocks. L2/L3 don't re-test L1 features; they **compose helpers**:

```typescript
// L1: auth/login.spec.ts — tests the login UI itself
test('valid credentials redirect to home', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.fillEmail('alice@test.com');
  await loginPage.fillPassword('testpass123');
  await loginPage.submit();
  await expect(page).toHaveURL('/home');
});

// L2: uses a HELPER, not the login UI
test('business creation to first member', async ({ authenticatedPage }) => {
  // authenticatedPage is already logged in (via storageState or API)
  // No login UI interaction — that's L1's job
  const consolePage = new BusinessConsolePage(authenticatedPage);
  // ... test the workflow
});

// L3: uses UI for login because the journey IS the test
test('Alice: newcomer journey', async ({ page }) => {
  // Step 1: Register via UI (testing the actual experience)
  const registerPage = new RegisterPage(page);
  await registerPage.goto();
  await registerPage.fillForm({ name: 'Alice', ... });
  await registerPage.submit();
  // Step 2: Login via UI
  // ... continues through full journey
});
```

---

## 5. Test Data Strategy

### Decision: Hybrid (API-driven + Progressive)

The most **reliable** approach. Cost and speed are secondary to reliability.

### Fresh Database Per Suite Run

Before any tests execute:

1. Drop the E2E database entirely
2. Create a fresh database
3. Run all migrations
4. Seed base data (platform configuration, suggested tags, default roles)
5. Create pre-built auth states (save `storageState` files for reuse)

This ensures: **zero state leakage between suite runs**.

### Per-Layer Strategy

| Layer | Setup Method | Cleanup | Why |
|-------|-------------|---------|-----|
| **L1 Smoke** | Each test creates its own data via API client | None needed (fresh DB handles it) | **Full isolation**. Test A cannot break Test B. If a test fails, the data problem is 100% within that test. |
| **L2 Workflow** | Each workflow file creates all needed entities via API in `beforeAll` | None needed | Entities shared across steps within one file, isolated between files. |
| **L3 Scenario** | Database reset before each scenario. Data created progressively through UI. | DB reset between scenarios | The data creation IS the test. Alice registers (creating her user), then creates a business (creating the business). Each step builds on previous. |

### API Client for Fast Setup (L1 + L2)

L1 and L2 tests should **NOT** use the UI for data setup. A test verifying "business profile page renders correctly" should create the business via direct API call (milliseconds), not click through registration + business creation (30+ seconds).

```typescript
// CORRECT: Fast API-driven setup (~200ms)
const user = await apiClient.register({ email: 'test@e2e.com', ... });
const business = await apiClient.createBusiness(user.token, { name: 'Test Biz', ... });
await page.goto(`/business/${business.slug}`);
// ← Test starts here. Setup is invisible to the test.

// WRONG: Slow UI-driven setup (~30s) — only appropriate for L3
await page.goto('/register');
await page.fill('[name=email]', 'test@e2e.com');
// ... 15 more steps before the actual test begins
```

### L3: Progressive State Building

In L3 scenarios, the data creation IS the test:

```
Scenario: Alice the Newcomer
  DB Reset (clean slate)
  Step 1: Register via UI → user created as side effect
  Step 2: Login via UI → session established
  Step 3: Explore businesses → no data mutation
  Step 4: Follow a business → follow record created
  Step 5: Request to join → transaction created
  ...
  Step 22: Logout and re-login → verifies persistence of ALL previous state
```

Each step depends on the previous. This is intentional — it tests that the app maintains coherent state across a long user journey.

### Pre-Built Auth States

Global setup creates common auth states saved as `storageState` JSON files:

| State File | Purpose | Used By |
|------------|---------|---------|
| `regular-user.json` | Authenticated regular user | Most L1/L2 tests |
| `business-owner.json` | User who owns a business | Business console tests |
| `business-member.json` | User who is a member (not owner) | RBAC boundary tests |
| `platform-admin.json` | Platform administrator | Platform console tests |
| `unauthenticated.json` | No auth (cleared state) | Public page tests |

Tests declare which state they need via Playwright fixtures:

```typescript
test('business console renders', async ({ businessOwnerPage }) => {
  // businessOwnerPage already has business-owner.json loaded
  // No login step needed
});
```

---

## 6. E2E Parameter Framework (P1–P14)

Every test is tagged with which parameters it verifies. This forms the structured **checklist and reporting framework**.

### P1 — Render Integrity

Verifies the page displays correctly.

- [ ] Page loads without blank/broken state
- [ ] All text content visible (headings, labels, descriptions, placeholder text)
- [ ] Images/avatars load (no broken image icons)
- [ ] Icons render correctly
- [ ] Loading skeletons appear then resolve to content
- [ ] Empty states display when no data exists
- [ ] Counts/badges show correct numbers
- [ ] Timestamps formatted correctly (relative and absolute)
- [ ] Status indicators (badges, colors, icons) match actual state

### P2 — User Interaction

Verifies user actions work correctly.

- [ ] Button clicks trigger expected actions
- [ ] Form fields accept input (text, number, date, select, multiselect, file)
- [ ] Form submission succeeds with valid data
- [ ] Form validation rejects invalid data with visible inline errors
- [ ] Dropdowns/comboboxes open, filter, and select
- [ ] Modals/dialogs open, render content, close (X button, Escape key, backdrop click)
- [ ] Confirmation dialogs require explicit action before destructive operations
- [ ] Toggle/switch components change state visually and functionally
- [ ] Tabs switch content correctly
- [ ] Copy-to-clipboard works
- [ ] Double-click/rapid-click prevention on submit buttons

### P3 — Navigation

Verifies routing and navigation work correctly.

- [ ] Route transitions render correct page
- [ ] Browser back/forward buttons work
- [ ] Deep linking (direct URL access) loads correct page with correct data
- [ ] Query parameters persist and apply correctly
- [ ] Breadcrumbs/page titles reflect current location
- [ ] Sidebar/nav highlights active route
- [ ] Redirect after action (e.g., create → detail page, login → return URL)

### P4 — Data Accuracy

Verifies displayed data matches the source of truth.

- [ ] Lists display correct items in correct order
- [ ] Detail views show all expected fields with correct values
- [ ] Search returns relevant results
- [ ] Filtering narrows results correctly
- [ ] Sorting reorders correctly
- [ ] Pagination loads correct pages (next/prev/specific page)
- [ ] Infinite scroll loads more items on scroll
- [ ] Counts match actual data (member count, message count, follower count)
- [ ] After mutation (create/update/delete), UI reflects change immediately without refresh

### P5 — Authentication & Authorization

Verifies auth and permission enforcement.

- [ ] Login succeeds with valid credentials
- [ ] Login fails with invalid credentials (error message shown, no redirect)
- [ ] Registration creates account and redirects appropriately
- [ ] Token refresh happens silently (user stays logged in during active use)
- [ ] Session expiry redirects to login with informative message
- [ ] Logout clears all client state (no stale data visible on re-login)
- [ ] Protected routes redirect unauthenticated users to login (with return URL)
- [ ] Forbidden resources show 403 / permission denied page
- [ ] Role-based UI elements hidden/shown correctly (`Can` component enforcement)
- [ ] Account lockout triggers after excessive failed login attempts

### P6 — Real-Time

Verifies WebSocket and live-update features.

- [ ] WebSocket connection established on page load (no connection error banner)
- [ ] Messages appear in real-time for recipient (no manual refresh needed)
- [ ] Typing indicators appear when other user types, disappear when they stop
- [ ] Presence indicators (online/offline) update in real-time
- [ ] Notifications appear in real-time (badge count increments, toast appears)
- [ ] Connection loss shows visible banner/indicator
- [ ] Reconnection restores real-time functionality automatically
- [ ] Message ordering remains correct under concurrent sends from multiple users

### P7 — Error Handling

Verifies the app handles errors gracefully.

- [ ] Network error shows user-friendly message (not raw error object or stack trace)
- [ ] 404 pages render for invalid/non-existent routes
- [ ] 403 pages render for unauthorized access attempts
- [ ] Server error (500) shows graceful error page, not white screen
- [ ] Rate limit (429) shows appropriate message with retry guidance
- [ ] Business rule violations display clear human-readable explanation
- [ ] Form submission errors preserve user input (don't clear the form)
- [ ] Timeout/slow responses show loading state (no indefinite hang)
- [ ] Retry mechanisms work where applicable (e.g., WebSocket reconnect)

### P8 — Responsive (Mobile)

Verifies the app works on mobile viewports.

- [ ] Layout adapts at mobile breakpoint (< 768px)
- [ ] Navigation collapses to hamburger menu or bottom nav
- [ ] Content readable without horizontal scrolling
- [ ] Touch targets sufficiently large (minimum 48px)
- [ ] Modals/dialogs fit within mobile viewport
- [ ] Tables/lists adapt to narrow width (card layout, horizontal scroll, or truncation)
- [ ] Chat layout switches to single-panel mode on mobile

### P9 — Visual Regression

Verifies the UI looks correct compared to approved baselines.

- [ ] Full-page screenshots match baseline (`toHaveScreenshot()`)
- [ ] Component-level screenshots stable across test runs
- [ ] No unexpected layout shifts between runs
- [ ] Font rendering consistent
- [ ] Color and spacing correct

### P10 — Limits & Quotas

Verifies limit enforcement from the user's perspective.

- [ ] Member quota enforced (attempt to exceed → clear error message)
- [ ] Rate limits visible to user (rapid requests → 429 with guidance)
- [ ] File upload size limits enforced (oversized file → rejection with explanation)
- [ ] Text length limits enforced (exceed max → inline validation error)
- [ ] Conversation participant limits enforced
- [ ] Feature gate limits enforced (config-driven values)
- [ ] UI shows quota status where applicable (e.g., "3/5 members used")
- [ ] Graceful degradation when limit reached (clear message, not crash or hang)

### P11 — Security

Verifies security measures from the browser.

- [ ] XSS: User-generated content displayed safely (HTML entities escaped, no script execution)
- [ ] CSRF: Cross-site request forgery protection works
- [ ] Authorization: Cannot access other users' private data via URL manipulation
- [ ] Authorization: Cannot perform actions beyond assigned role (e.g., member can't delete business)
- [ ] Session: Old sessions invalidated after password change
- [ ] Input: SQL injection characters handled safely in search and form fields
- [ ] File upload: Non-allowed MIME types rejected with clear error

### P12 — Accessibility

Verifies basic accessibility compliance.

- [ ] ARIA landmarks present on major page sections (nav, main, aside)
- [ ] Focus trapped in open modals (Tab doesn't escape to background)
- [ ] Focus returns to trigger element after modal closes
- [ ] Keyboard navigation works (Tab order is logical through the page)
- [ ] Screen reader announcements for dynamic content (`aria-live` regions)
- [ ] Color is not the sole indicator of state (icons or text accompany color changes)
- [ ] Skip-to-content link present on pages with navigation

### P13 — Cross-User Interaction

Verifies multi-user scenarios work correctly.

- [ ] Two users see each other's actions in real-time (no refresh needed)
- [ ] Concurrent operations don't cause data corruption or duplicates
- [ ] Optimistic UI updates resolve correctly when server confirms or rejects
- [ ] Invitation/request flow works end-to-end between two distinct users
- [ ] Chat between two users delivers messages in both directions
- [ ] Follow/connect between two users updates both users' UIs

### P14 — State Persistence

Verifies data survives browser events.

- [ ] Page refresh preserves login state (user stays logged in)
- [ ] Page refresh preserves current route (user stays on same page)
- [ ] Browser tab close + reopen restores session (if within expiry)
- [ ] Form drafts survive accidental navigation (where implemented)
- [ ] Notification read status persists across page transitions
- [ ] User preferences (settings changes) persist across sessions

---

## 7. Project File Structure

```
e2e/
├── CLAUDE.md                          # Governance, mandates, conventions
├── package.json                       # Playwright + dependencies
├── playwright.config.ts               # Multi-project config
├── tsconfig.json                      # TypeScript configuration
├── .env.example                       # E2E environment variables template
├── .env                               # Local environment (gitignored)
├── .gitignore                         # Reports, screenshots, node_modules, .env
│
├── docker/
│   ├── docker-compose.e2e.yml         # Isolated E2E stack
│   ├── Dockerfile.backend             # Backend image for E2E
│   ├── Dockerfile.frontend            # Frontend image for E2E
│   ├── entrypoint.sh                 # DB setup + migrate + seed + health check
│   └── README.md                      # How to run E2E infrastructure
│
├── docs/
│   ├── README.md                      # Document map (links to everything)
│   ├── architecture.md                # THIS DOCUMENT
│   ├── parameter-checklist.md         # P1-P14 framework (extractable as checklist)
│   ├── coverage-matrix.md             # System x Parameter x Layer matrix
│   ├── plans/
│   │   ├── l1-smoke-tests.md          # Complete L1 test catalog with details
│   │   ├── l2-workflow-tests.md       # Complete L2 test catalog with details
│   │   ├── l3-scenario-tests.md       # Complete L3 persona definitions with details
│   │   └── ci-cd-pipeline.md          # CI/CD pipeline design
│   ├── reports/                       # Test run reports (gitignored, CI artifacts)
│   │   └── .gitkeep
│   └── versions/
│       └── CHANGELOG.md               # Test suite version history
│
├── global-setup.ts                    # Before all tests: DB reset, seed, create auth states
├── global-teardown.ts                 # After all tests: cleanup
│
├── lib/                               # Pure utilities (no Playwright dependency)
│   ├── api-client.ts                  # Direct HTTP client for fast test data setup
│   ├── constants.ts                   # Base URLs, timeouts, default credentials
│   ├── types.ts                       # Shared TypeScript types
│   ├── utils.ts                       # Common utilities (waitForToast, retry, etc.)
│   ├── feature-gates.ts              # Feature gate config reader for conditional tests
│   └── report-annotations.ts         # Parameter tagging for test reports
│
├── fixtures/                          # Playwright fixture definitions
│   ├── base.fixture.ts                # Extended test with custom fixtures
│   ├── auth.fixture.ts                # Authenticated page fixtures (per role)
│   ├── business.fixture.ts            # Business context fixtures (owner, member)
│   ├── platform.fixture.ts            # Platform context fixtures (admin)
│   └── storage-states/               # Saved auth state JSON files (gitignored)
│       └── .gitkeep
│
├── pages/                             # Page Object Models (POM)
│   ├── base.page.ts                   # BasePage — shared: nav, header, toasts, footer
│   ├── auth/
│   │   ├── login.page.ts             # LoginPage — email, password, submit, errors
│   │   ├── register.page.ts          # RegisterPage — all registration fields
│   │   └── forgot-password.page.ts   # ForgotPasswordPage — email, submit
│   ├── user/
│   │   ├── profile.page.ts           # UserProfilePage — view/edit profile
│   │   ├── home.page.ts              # HomePage — user home feed
│   │   └── settings.page.ts          # SettingsPage — preferences, account
│   ├── explore/
│   │   └── explore.page.ts           # ExplorePage — search, filters, results
│   ├── business/
│   │   ├── business-profile.page.ts  # BusinessProfilePage — public profile
│   │   └── business-console.page.ts  # BusinessConsolePage — dashboard, members, roles, etc.
│   ├── platform/
│   │   ├── platform-profile.page.ts  # PlatformProfilePage — public profile
│   │   └── platform-console.page.ts  # PlatformConsolePage — dashboard, management
│   ├── chat/
│   │   └── chat.page.ts              # ChatPage — conversations, messages, compose
│   ├── network/
│   │   └── network.page.ts           # NetworkPage — followers, connections, requests
│   ├── transactions/
│   │   └── transactions.page.ts      # TransactionsPage — list, detail, actions
│   ├── forms/
│   │   └── forms.page.ts             # FormsPage — templates, builder, submissions
│   └── notifications/
│       └── notifications.page.ts     # NotificationsPage — list, mark read, navigate
│
├── helpers/                           # Multi-step action sequences (composed from POMs)
│   ├── auth.helper.ts                 # loginViaApi(), registerViaApi(), loginViaUi()
│   ├── business.helper.ts            # createBusinessViaApi(), inviteMemberViaApi()
│   ├── chat.helper.ts                # createConversationViaApi(), sendMessageViaApi()
│   ├── network.helper.ts             # followViaApi(), connectViaApi()
│   ├── transaction.helper.ts         # createTransactionViaApi(), acceptViaApi()
│   ├── form.helper.ts                # createFormTemplateViaApi()
│   └── navigation.helper.ts          # goTo(), expectRoute(), switchAccount()
│
├── tests/
│   ├── smoke/                         # L1 — Single feature, isolated, fast
│   │   ├── auth/                      # 5 tests
│   │   │   ├── login.spec.ts
│   │   │   ├── register.spec.ts
│   │   │   ├── logout.spec.ts
│   │   │   ├── password-reset.spec.ts
│   │   │   └── session-management.spec.ts
│   │   ├── user/                      # 3 tests
│   │   │   ├── profile-view.spec.ts
│   │   │   ├── profile-edit.spec.ts
│   │   │   └── settings.spec.ts
│   │   ├── explore/                   # 3 tests
│   │   │   ├── search-businesses.spec.ts
│   │   │   ├── search-users.spec.ts
│   │   │   └── filters.spec.ts
│   │   ├── business/                  # 6 tests
│   │   │   ├── profile-public.spec.ts
│   │   │   ├── create-business.spec.ts
│   │   │   ├── console-dashboard.spec.ts
│   │   │   ├── member-management.spec.ts
│   │   │   ├── role-management.spec.ts
│   │   │   └── business-settings.spec.ts
│   │   ├── platform/                  # 3 tests
│   │   │   ├── profile-public.spec.ts
│   │   │   ├── console-dashboard.spec.ts
│   │   │   └── platform-management.spec.ts
│   │   ├── chat/                      # 7 tests
│   │   │   ├── conversation-list.spec.ts
│   │   │   ├── send-message.spec.ts
│   │   │   ├── group-chat.spec.ts
│   │   │   ├── attachments.spec.ts
│   │   │   ├── reactions.spec.ts
│   │   │   ├── search-messages.spec.ts
│   │   │   └── chat-requests.spec.ts
│   │   ├── network/                   # 3 tests
│   │   │   ├── follow-business.spec.ts
│   │   │   ├── connect-user.spec.ts
│   │   │   └── network-page.spec.ts
│   │   ├── transactions/              # 4 tests
│   │   │   ├── membership-invitation.spec.ts
│   │   │   ├── join-request.spec.ts
│   │   │   ├── ownership-transfer.spec.ts
│   │   │   └── transaction-list.spec.ts
│   │   ├── forms/                     # 3 tests
│   │   │   ├── template-builder.spec.ts
│   │   │   ├── form-submission.spec.ts
│   │   │   └── form-responses.spec.ts
│   │   ├── notifications/             # 1 test
│   │   │   └── notification-center.spec.ts
│   │   ├── limits/                    # 3 tests
│   │   │   ├── member-quota.spec.ts
│   │   │   ├── rate-limits.spec.ts
│   │   │   └── field-length-limits.spec.ts
│   │   └── responsive/               # 4 tests
│   │       ├── auth-mobile.spec.ts
│   │       ├── chat-mobile.spec.ts
│   │       ├── navigation-mobile.spec.ts
│   │       └── business-console-mobile.spec.ts
│   │
│   ├── workflows/                     # L2 — Cross-domain, multi-step
│   │   ├── auth-to-profile.spec.ts
│   │   ├── business-creation-to-first-member.spec.ts
│   │   ├── member-invitation-full-cycle.spec.ts
│   │   ├── join-request-with-form.spec.ts
│   │   ├── transaction-form-approval-workflow.spec.ts
│   │   ├── business-follow-to-join.spec.ts
│   │   ├── chat-conversation-lifecycle.spec.ts
│   │   ├── two-user-chat-realtime.spec.ts
│   │   ├── network-follow-connect-flow.spec.ts
│   │   ├── business-member-rbac-flow.spec.ts
│   │   ├── explore-to-interaction.spec.ts
│   │   ├── notification-triggered-actions.spec.ts
│   │   ├── platform-business-management.spec.ts
│   │   ├── ownership-transfer-workflow.spec.ts
│   │   ├── member-quota-enforcement.spec.ts
│   │   └── entity-chat-business-context.spec.ts
│   │
│   └── scenarios/                     # L3 — Full personas, adversarial
│       ├── persona-alice-newcomer.spec.ts
│       ├── persona-bob-entrepreneur.spec.ts
│       ├── persona-carol-admin.spec.ts
│       ├── persona-dave-social.spec.ts
│       ├── persona-eve-adversarial.spec.ts
│       ├── persona-frank-multi-context.spec.ts
│       └── multi-persona-interaction.spec.ts
│
└── playwright-report/                 # Playwright HTML reports (gitignored)
    └── .gitkeep
```

### Directory Purposes

| Directory | Purpose | Depends On |
|-----------|---------|------------|
| `lib/` | Pure TypeScript utilities. No Playwright imports. HTTP client, constants, types. | Nothing |
| `fixtures/` | Playwright fixture definitions. Extend `test` with custom fixtures. | `lib/` |
| `pages/` | Page Object Models. Encapsulate locators and page-specific actions. | Playwright `Page` |
| `helpers/` | Multi-step action composers. Use API client or POMs to perform complex setup. | `lib/`, `pages/` |
| `tests/` | Actual test files. Import from all above layers. | Everything above |
| `docker/` | E2E-specific Docker infrastructure. | Nothing (standalone) |
| `docs/` | Documentation, plans, reports, versioning. | Nothing |

### Import Hierarchy (Enforced)

```
tests/ → helpers/ → pages/ → lib/
tests/ → fixtures/ → lib/
tests/ → lib/

# Never:
lib/ → pages/      (lib has no Playwright dependency)
pages/ → helpers/   (pages don't know about multi-step flows)
helpers/ → tests/   (helpers don't know about specific tests)
```

---

## 8. Page Object Model (POM)

### Philosophy

Every page in the application gets a corresponding Page Object. Tests **never** use raw CSS selectors or `page.locator()` directly. When the UI changes, you update **one POM file**, not 50 test files.

### Example: LoginPage

```typescript
// pages/auth/login.page.ts
import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from '../base.page';

export class LoginPage extends BasePage {
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly forgotPasswordLink: Locator;
  readonly registerLink: Locator;

  constructor(page: Page) {
    super(page);
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: 'Sign in' });
    this.errorMessage = page.getByRole('alert');
    this.forgotPasswordLink = page.getByRole('link', { name: /forgot/i });
    this.registerLink = page.getByRole('link', { name: /register|sign up/i });
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectError(message: string) {
    await expect(this.errorMessage).toContainText(message);
  }

  async expectRedirectedToHome() {
    await expect(this.page).toHaveURL('/home');
  }
}
```

### POM Rules

1. **Locators use accessible selectors**: `getByRole()`, `getByLabel()`, `getByText()` — never raw CSS unless absolutely necessary
2. **POMs describe WHAT, not WHY**: `login(email, password)` not `testValidLogin()`
3. **POMs never assert test outcomes**: assertions belong in test files, not POMs (exception: convenience methods like `expectError()`)
4. **BasePage handles shared elements**: navigation, header, toast messages, footer — inherited by all page objects

---

## 9. L1 Smoke Tests — Complete Catalog

### Auth System (8 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `login.spec.ts` | Valid credentials → redirect to home; Invalid credentials → error message; Empty fields → validation | P1, P2, P3, P5, P7 | Critical |
| `register.spec.ts` | Valid registration → account created; Duplicate email → error; Invalid fields → inline validation | P1, P2, P3, P5, P7 | Critical |
| `logout.spec.ts` | Logout → session cleared → redirect to login; Re-visit protected route → login redirect | P2, P3, P5, P14 | Critical |
| `password-reset.spec.ts` | Request reset → confirmation shown; Reset with new password → can login | P1, P2, P3, P5 | High |
| `session-management.spec.ts` | Active sessions list renders; Session info correct; Revoke specific session | P1, P2, P4 | Medium |
| `email-verification.spec.ts` | Enter verification code → success page; Invalid code → error; Resend verification link | P1, P2, P3, P5, P7 | **Critical** |
| `password-change.spec.ts` | Change password while logged in; Current password required; Logout-other-sessions option | P1, P2, P5 | High |
| `oauth-redirect.spec.ts` | Google OAuth → redirect to Google; Apple Sign In → redirect to Apple (smoke only, no full flow) | P1, P3 | High |

### User System (7 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `profile-view.spec.ts` | Profile page renders with correct user info; Avatar displays; Bio and details shown | P1, P3, P4 | High |
| `profile-edit.spec.ts` | Edit fields → save → changes persist; Cancel → no changes | P1, P2, P4, P14 | High |
| `settings.spec.ts` | Settings page renders; Update notification preferences; Changes persist after re-login | P1, P2, P14 | Medium |
| `home-feed.spec.ts` | Home page renders after login; Activity items present; Navigation from home to other pages | P1, P3, P4 | **Critical** |
| `activity-feed.spec.ts` | Activity list renders; Activity detail page; Back navigation | P1, P3, P4 | High |
| `other-user-profile.spec.ts` | `/users/[username]` renders; Public fields visible; Connection/follow buttons present | P1, P4, P5 | High |
| `username-change.spec.ts` | Change username; Availability check (real-time); Slug updates | P1, P2, P4 | Medium |

### Explore System (3 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `search-businesses.spec.ts` | Enter query → results appear; Result cards render correctly; Click result → navigate to profile | P1, P2, P3, P4 | High |
| `search-users.spec.ts` | Auth required for user search; Results display user info; Empty state for no results | P1, P4, P5 | High |
| `filters.spec.ts` | Apply single filter → results narrow; Apply multiple filters → combined; Clear filters → all results | P2, P4 | Medium |

### Business System (13 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `profile-public.spec.ts` | Anonymous can view public profile; Public fields visible; Private fields hidden; `_permissions` shown correctly | P1, P3, P4, P5 | High |
| `create-business.spec.ts` | Fill creation form → submit → redirects to console; Required fields enforced | P1, P2, P3, P5 | Critical |
| `console-dashboard.spec.ts` | Dashboard renders with stats; Recent activity shown; Navigation works | P1, P3, P4, P5 | High |
| `member-management.spec.ts` | Member list renders; Role badges shown; Member count accurate | P1, P4, P5 | High |
| `role-management.spec.ts` | Role list renders; Permission checkboxes shown; Custom role visible | P1, P4, P5 | Medium |
| `business-settings.spec.ts` | Settings form renders; Update fields → save → persist | P1, P2, P14 | Medium |
| `business-lifecycle.spec.ts` | Suspend business → restricted; Reactivate → restored; Archive → read-only | P1, P2, P5 | High |
| `member-actions.spec.ts` | Suspend member → restricted access; Ban → removed; Reactivate suspended member | P1, P2, P5 | High |
| `member-detail.spec.ts` | Member detail page renders; Role badge; Permission list; Action buttons (role-dependent) | P1, P4, P5 | Medium |
| `business-network.spec.ts` | Followers management page; Connections management page; Remove follower | P1, P4 | Medium |
| `business-transactions-detail.spec.ts` | Requests list + detail; Invitations list + detail; Settings page | P1, P4 | Medium |
| `business-audit.spec.ts` | Audit log page renders; Entries present; Filter by action type | P1, P4 | Medium |
| `business-visibility.spec.ts` | T2 visibility settings; Toggle field visibility; Verify public view changes | P1, P2, P4, P5 | Medium |

### Platform System (8 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `profile-public.spec.ts` | Platform public profile renders for anonymous | P1, P3, P4 | High |
| `console-dashboard.spec.ts` | Admin dashboard renders; Stats accurate; Navigation to sub-pages | P1, P3, P4, P5 | High |
| `platform-management.spec.ts` | Business list renders; Member list renders; Pagination works | P1, P4 | Medium |
| `platform-businesses.spec.ts` | Businesses list management; Search; Detail view from platform | P1, P4 | High |
| `platform-cms.spec.ts` | CMS sites list; Create/edit site; Templates; API keys; Media library | P1, P2, P4 | **Critical** |
| `platform-forms.spec.ts` | Platform-scoped form templates; Responses list; Detail view | P1, P4 | Medium |
| `platform-transactions.spec.ts` | Platform-scoped transaction list; Detail pages; Filter by type | P1, P4 | Medium |
| `platform-audit.spec.ts` | Platform audit log; Entries present; Filter by action | P1, P4 | Medium |

### Chat System (13 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `conversation-list.spec.ts` | Conversation list renders; Latest message preview shown; Unread indicators | P1, P4 | High |
| `send-message.spec.ts` | Type message → send → appears in thread; Message shows correct timestamp and sender | P1, P2, P4, P6 | Critical |
| `group-chat.spec.ts` | Create group → participants listed; Group name displayed | P1, P2, P4 | High |
| `attachments.spec.ts` | Upload image → preview shown; Click image → lightbox opens | P1, P2 | Medium |
| `reactions.spec.ts` | Add reaction → appears on message; Remove reaction → disappears; Reaction count updates | P2, P4 | Medium |
| `search-messages.spec.ts` | Search query → matching messages shown; Click result → navigates to message | P2, P4 | Medium |
| `chat-requests.spec.ts` | Chat request list renders; Accept request → conversation opens; Decline → removed from list | P1, P2, P4 | High |
| `message-edit-delete.spec.ts` | Edit own message → content updates; Delete own message → removed; Can't edit others' | P1, P2, P4 | High |
| `presence-indicators.spec.ts` | Online user shows green dot; Offline user shows grey; Status updates on connect/disconnect | P1, P4, P6 | Medium |
| `delivery-status.spec.ts` | Sent → delivered → seen indicators; Watermark updates on read | P1, P4, P6 | Medium |
| `group-admin.spec.ts` | Promote participant to admin; Demote admin; Remove participant; Admin-only actions gated | P1, P2, P5 | Medium |
| `chat-mute.spec.ts` | Mute conversation → no notification badge; Unmute → badge returns | P1, P2 | Low |
| `entity-sender-badge.spec.ts` | Business sender badge on message; Platform sender badge; Distinguishes entity vs user | P1, P4 | Medium |

### Network System (6 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `follow-business.spec.ts` | Click follow → button state changes; Unfollow → reverts | P2, P4, P6 | High |
| `connect-user.spec.ts` | Send connection request → pending state shown | P2, P4 | High |
| `network-page.spec.ts` | Network page renders; Follower/following/connection counts accurate; Lists populated | P1, P4 | Medium |
| `following-list.spec.ts` | User's following list renders; Unfollow from list; Empty state | P1, P2, P4 | Medium |
| `connection-list.spec.ts` | User's connections list renders; Disconnect; Pending connections shown | P1, P2, P4 | Medium |
| `disconnect.spec.ts` | Disconnect from user → connection removed; Disconnect from account → relationship cleared | P2, P4 | Medium |

### Transaction System (7 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `membership-invitation.spec.ts` | Owner sends invitation → appears in recipient's transaction list | P1, P2, P4 | Critical |
| `join-request.spec.ts` | User sends join request → pending; Owner accepts → status updates | P1, P2, P4 | Critical |
| `ownership-transfer.spec.ts` | Initiate transfer → pending; Target accepts → ownership changes | P1, P2, P5 | High |
| `transaction-list.spec.ts` | Transaction list renders; Status badges correct; Filter by type; Pagination | P1, P2, P4 | Medium |
| `transaction-deny-cancel.spec.ts` | Deny transaction → status updates; Cancel own transaction → status updates | P1, P2, P4, P7 | High |
| `transaction-pages.spec.ts` | Requests list page; Invitations list page; Detail pages with action buttons | P1, P4 | Medium |
| `form-mapping-settings.spec.ts` | Transaction form mapping config; Set required form; Remove mapping | P1, P2, P4 | Medium |

### Forms System (6 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `template-builder.spec.ts` | Create template → add fields (text, select, date, etc.) → save | P1, P2 | High |
| `form-submission.spec.ts` | Open form → fill all field types → submit → success confirmation | P1, P2, P4 | High |
| `form-responses.spec.ts` | Response list renders; Click response → detail view with correct data | P1, P4 | Medium |
| `template-lifecycle.spec.ts` | Publish template → status change; Archive → hidden; Unarchive → restored; Fork → new draft | P1, P2, P4 | High |
| `field-crud.spec.ts` | Add field → appears; Update field config; Delete field; Reorder via drag or buttons | P1, P2 | High |
| `field-types-all.spec.ts` | Test all 14+ field types render correctly in builder and submission form | P1, P2, P4 | Medium |

### Notifications (3 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `notification-center.spec.ts` | Notification list renders; Unread badge count accurate; Mark as read; Click → navigate to source | P1, P2, P3, P4 | High |
| `notification-preferences.spec.ts` | Full preference management; Toggle categories; Save → changes reflected on next notification | P1, P2, P14 | Medium |
| `notification-history.spec.ts` | Delivery history list; Filter by type; Delivery status indicators | P1, P4 | Low |

### Public / Landing Pages (1 test)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `landing-pages.spec.ts` | `/` renders correctly; `/about` renders; `/contact` renders; Navigation between public pages | P1, P3 | Medium |

### Navigation (1 test)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `account-switcher.spec.ts` | Account context switching; Personal → Business A → Business B; Correct data per context; No data leakage | P1, P3, P4, P5 | **Critical** |

### CMS System (5 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `cms-site-management.spec.ts` | CRUD sites; Site list renders; Domain configuration | P1, P2, P4 | **Critical** |
| `cms-page-publish.spec.ts` | Create page → add blocks → publish → verify public view | P1, P2, P4 | **Critical** |
| `cms-content-editing.spec.ts` | Edit block content; Rich text sanitization; Schema validation errors | P1, P2, P7 | High |
| `cms-media-library.spec.ts` | Upload media; Media list; Delete media; Tombstoning | P1, P2 | Medium |
| `cms-api-keys.spec.ts` | Create API key; Key prefix displayed; Revoke key | P1, P2, P5 | Medium |

### Feature Gate Degradation (1 test)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `feature-gate-403.spec.ts` | Disabled feature → 403 response; UI hides disabled feature; Re-enable → feature restored | P1, P5, P7 | High |

### Limits & Quotas (3 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `member-quota.spec.ts` | Business at quota → invite new member → clear quota error message; Remove member → can invite again | P2, P7, P10 | Critical |
| `rate-limits.spec.ts` | Rapid API-triggering actions → 429 message displayed to user | P7, P10 | High |
| `field-length-limits.spec.ts` | Exceed max length on form fields → inline validation error shown | P2, P7, P10 | Medium |

### Responsive / Mobile (4 tests)

| File | Test Cases | Parameters | Priority |
|------|-----------|------------|----------|
| `auth-mobile.spec.ts` | Login + register pages render correctly on mobile viewport | P1, P8 | High |
| `chat-mobile.spec.ts` | Chat single-panel mode; Conversation list → tap → message view; Back button | P1, P2, P8 | High |
| `navigation-mobile.spec.ts` | Sidebar collapses; Hamburger menu opens/closes; All nav links accessible | P1, P2, P8 | High |
| `business-console-mobile.spec.ts` | Console navigation adapts; Dashboard readable; Member list usable | P1, P8 | Medium |

### L1 Summary

**Total: 89 test files, ~270 individual test cases**

| System | Files | Priority Breakdown |
|--------|-------|-------------------|
| Auth | 8 | 4 Critical, 2 High, 2 Medium |
| User | 7 | 1 Critical, 3 High, 3 Medium |
| Explore | 3 | 2 High, 1 Medium |
| Business | 13 | 1 Critical, 5 High, 7 Medium |
| Platform | 8 | 2 Critical, 3 High, 3 Medium |
| Chat | 13 | 1 Critical, 4 High, 7 Medium, 1 Low |
| Network | 6 | 2 High, 4 Medium |
| Transactions | 7 | 2 Critical, 2 High, 3 Medium |
| Forms | 6 | 4 High, 2 Medium |
| Notifications | 3 | 1 High, 1 Medium, 1 Low |
| Public/Landing | 1 | 1 Medium |
| Navigation | 1 | 1 Critical |
| CMS | 5 | 2 Critical, 1 High, 2 Medium |
| Feature Gates | 1 | 1 High |
| Limits | 3 | 1 Critical, 1 High, 1 Medium |
| Responsive | 4 | 3 High, 1 Medium |

---

## 10. L2 Workflow Tests — Complete Catalog

Each workflow crosses 2+ systems and tests a realistic multi-step process.

### W1: Register → Profile Setup

**Systems**: Auth, User, Settings
**Parameters**: P1, P2, P3, P4, P5, P14

| Step | Action | Verify |
|------|--------|--------|
| 1 | Register with valid data | Account created, redirect to appropriate page |
| 2 | Login with new credentials | Session established, home page loads |
| 3 | Navigate to profile | Profile page shows registration data (name, email) |
| 4 | Edit profile (bio, avatar, details) | Save succeeds, changes reflected immediately |
| 5 | Navigate to settings | Settings page loads with defaults |
| 6 | Update notification preferences | Save succeeds |
| 7 | Logout and re-login | All profile changes + preferences persist |

### W2: Business Creation → First Member

**Systems**: Auth, Organization, Transaction, RBAC
**Parameters**: P1, P2, P3, P4, P5, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | Login as User A (business creator) | Authenticated |
| 2 | Create business via form | Business created, redirected to console |
| 3 | Customize business profile | Profile updated, public page reflects changes |
| 4 | Navigate to member management | Owner listed as only member |
| 5 | Invite User B by email | Invitation transaction created |
| 6 | Switch to User B context | See pending invitation in transactions |
| 7 | User B accepts invitation | Membership created, role assigned |
| 8 | Switch to User A context | Member count = 2, User B in member list |
| 9 | User B accesses business console | Console loads with member-appropriate features |

### W3: Member Invitation Full Cycle

**Systems**: Transaction, Notification, RBAC, Organization
**Parameters**: P1, P2, P3, P4, P5, P6, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | Owner sends invitation to User | Transaction created (pending) |
| 2 | User receives notification | Notification appears (real-time if possible) |
| 3 | User views invitation details | Transaction details correct, action buttons present |
| 4 | User accepts invitation | Status → accepted |
| 5 | User gets member role | Default role assigned |
| 6 | User accesses business console | Role-permitted features visible |
| 7 | Owner sees updated member list | New member appears with correct role |

### W4: Join Request with Required Form

**Systems**: Explore, Transaction, Forms, Organization
**Parameters**: P1, P2, P3, P4, P5, P10, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | Owner configures form template | Form created with multiple field types |
| 2 | Owner maps form as required for join requests | Mapping saved |
| 3 | User searches and finds business | Business appears in explore results |
| 4 | User views business profile | "Request to Join" button visible |
| 5 | User clicks "Request to Join" | Form dialog appears (required form) |
| 6 | User fills form and submits | Transaction created (PENDING_REVIEW) |
| 7 | Owner sees request with form response | Form data displayed alongside request |
| 8 | Owner approves request | Membership created (ACTIVE) |
| 9 | User can now access business console | Console loads with member features |

### W5: Transaction + Form + Approval (Two-Phase)

**Systems**: Transaction, Forms, RBAC
**Parameters**: P1, P2, P3, P4, P5, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | Business requires form on join | Form-transaction mapping configured |
| 2 | User submits join request with form | Status: PENDING_REVIEW, membership: PENDING_APPROVAL |
| 3 | Owner reviews form response | Form data visible, approve/deny buttons present |
| 4 | Owner approves | Transaction: ACCEPTED, membership: ACTIVE |
| 5 | Verify member counts updated | PENDING_APPROVAL counted toward quota, then ACTIVE |

### W6: Discover → Follow → Join

**Systems**: Explore, Network, Transaction, Organization
**Parameters**: P1, P2, P3, P4, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | User searches for businesses | Results appear |
| 2 | User views business profile | Profile renders, follow button visible |
| 3 | User follows business | Follow registered, button state changes |
| 4 | User requests to join | Transaction created |
| 5 | Owner accepts | User is now both follower AND member |
| 6 | Verify dual relationship | Network page shows follow; business console shows membership |

### W7: Chat Conversation Lifecycle

**Systems**: Chat
**Parameters**: P1, P2, P3, P4, P6, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | User A starts conversation with User B | Conversation created, appears in both users' lists |
| 2 | User A sends message | Message appears in thread |
| 3 | User A adds User C to conversation | Participant list updates, User C sees conversation |
| 4 | User C sends message | Message visible to all participants |
| 5 | User B reacts to message | Reaction count updates for all |
| 6 | User A searches messages | Search results found within conversation |
| 7 | User B leaves conversation | Participant removed, conversation still exists for others |

### W8: Two-User Realtime Chat

**Systems**: Chat (WebSocket focus)
**Parameters**: P2, P4, P6, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | User A and User B both have chat page open | Two browser contexts, both connected |
| 2 | User A starts typing | User B sees typing indicator |
| 3 | User A sends message | User B receives message in real-time (no refresh) |
| 4 | User B replies | User A receives reply in real-time |
| 5 | User A sends 5 messages rapidly | All 5 arrive in correct order for User B |
| 6 | Disconnect User A's network briefly | Connection banner appears for User A |
| 7 | Reconnect User A | Banner disappears, missed messages sync |

### W9: Network Follow + Connect

**Systems**: Network, Notification
**Parameters**: P2, P4, P6, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | User A follows Business X | Follow registered, follower count increments |
| 2 | User B sends connection request to User A | Request created, notification sent |
| 3 | User A sees notification | Real-time notification appears |
| 4 | User A accepts connection | Connection established |
| 5 | Both users' network pages update | Correct counts, connection visible in lists |
| 6 | User A unfollows Business X | Follow removed, count decrements |

### W10: Business Member RBAC Flow

**Systems**: RBAC, Organization, Transaction
**Parameters**: P1, P2, P3, P4, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | Owner creates custom role with specific permissions | Role created with selected permissions |
| 2 | Owner invites User with custom role | Invitation sent with role assignment |
| 3 | User accepts | Membership with custom role |
| 4 | User accesses console | Permitted features visible (e.g., member management) |
| 5 | User tries to access restricted feature (e.g., business settings) | Blocked — UI element hidden or 403 |
| 6 | Owner changes user's role to one with more permissions | Role updated |
| 7 | User refreshes | New permissions take effect, previously hidden feature now visible |

### W11: Explore → Interact

**Systems**: Explore, Network, Chat
**Parameters**: P1, P2, P3, P4, P6

| Step | Action | Verify |
|------|--------|--------|
| 1 | Search for users | Results appear |
| 2 | View user profile | Profile renders correctly |
| 3 | Send connection request | Request created, pending state shown |
| 4 | Other user accepts (via API) | Connection established |
| 5 | Start chat with connected user | Conversation created |
| 6 | Send message | Message appears, real-time delivery |

### W12: Notification → Action

**Systems**: Notification, Transaction, Organization, Navigation
**Parameters**: P1, P2, P3, P4, P6

| Step | Action | Verify |
|------|--------|--------|
| 1 | User receives invitation (created via API) | Notification appears in notification center |
| 2 | Click notification | Navigate to transaction detail |
| 3 | Accept invitation | Transaction accepted, membership created |
| 4 | Automatically redirected or navigate to business console | Console accessible with correct role |
| 5 | Notification marked as actioned | Badge count decrements |

### W13: Platform Business Management

**Systems**: Platform, Organization, RBAC
**Parameters**: P1, P2, P3, P4, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | Platform admin navigates to console | Dashboard renders with platform stats |
| 2 | View businesses list | All businesses on platform listed |
| 3 | View specific business detail | Business info accurate |
| 4 | View platform members | Member list with roles |
| 5 | Manage platform settings | Settings update and persist |

### W14: Ownership Transfer

**Systems**: Transaction, RBAC, Organization, Notification
**Parameters**: P1, P2, P3, P4, P5, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | Owner initiates ownership transfer to Member | Transfer transaction created |
| 2 | Member receives notification | Notification appears |
| 3 | Member accepts transfer | Transaction accepted |
| 4 | Member becomes new owner | Owner role assigned, full console access |
| 5 | Original owner loses owner role | Downgraded to member, restricted features hidden |
| 6 | Original owner tries owner-only action | Blocked |

### W15: Member Quota Enforcement

**Systems**: Organization, Transaction, Limits
**Parameters**: P2, P4, P7, P10, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | Business has max_members = 3 (owner + 2 slots) | Quota visible in settings/management |
| 2 | Invite Member A → accepts | Count: 2/3 |
| 3 | Invite Member B → accepts | Count: 3/3 |
| 4 | Invite Member C | Quota error message displayed clearly |
| 5 | Remove Member A | Count: 2/3, slot freed |
| 6 | Invite Member C again | Succeeds. Count: 3/3 |

### W16: Entity Chat in Business Context

**Systems**: Chat, Organization, RBAC
**Parameters**: P1, P2, P3, P4, P5, P6, P13

| Step | Action | Verify |
|------|--------|--------|
| 1 | Business owner switches to business context | Business console loads |
| 2 | Navigate to business chat | Chat page in business scope |
| 3 | Start conversation as business entity | Conversation created with business as participant |
| 4 | Send message as business | Message attributed to business, not owner personally |
| 5 | External user replies | Reply visible in entity inbox |
| 6 | Owner views entity inbox | All business conversations listed |

### W17: Registration → Email Verification → First Login

**Systems**: Auth, Email
**Parameters**: P1, P2, P3, P5, P7

| Step | Action | Verify |
|------|--------|--------|
| 1 | Register with valid data | Account created, redirect to verification prompt |
| 2 | Enter wrong verification code | Error message, code not consumed |
| 3 | Resend verification code | New code sent, rate limit respected |
| 4 | Enter correct verification code | Email verified, success page |
| 5 | Login with verified account | Session established, home page loads |
| 6 | Verify email badge/status in profile | Verified indicator shown |

### W18: CMS Content Lifecycle

**Systems**: CMS, Platform
**Parameters**: P1, P2, P3, P4, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | Platform admin navigates to CMS | CMS dashboard/site list renders |
| 2 | Create a new site | Site created, appears in list |
| 3 | Create a content template | Template saved with schema |
| 4 | Create a page using template | Page created in draft status |
| 5 | Add content blocks (text, image, rich text) | Blocks render in editor |
| 6 | Publish page | Status → published, public URL accessible |
| 7 | Edit published page → create new draft | Versioning: published still live, draft editable |
| 8 | Publish new version | Old version replaced, new content live |
| 9 | Verify public view shows correct content | Anonymous user sees published content |

### W19: Form Template Lifecycle

**Systems**: Forms, Organization
**Parameters**: P1, P2, P4

| Step | Action | Verify |
|------|--------|--------|
| 1 | Create form template | Template in draft status |
| 2 | Add 5+ field types (text, select, date, checkbox, number) | All field types work in builder |
| 3 | Reorder fields (drag or buttons) | Order persists after save |
| 4 | Publish template | Status → published, available for use |
| 5 | Fork published template | New draft created from published |
| 6 | Edit forked draft | Changes don't affect original |
| 7 | Publish forked version | New version available |
| 8 | Archive original template | Status → archived, hidden from active list |

### W20: Member Discipline Flow

**Systems**: Organization, RBAC
**Parameters**: P1, P2, P4, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | Owner suspends member | Member status → suspended |
| 2 | Suspended member tries to access console | Blocked — restricted access message |
| 3 | Owner reactivates member | Member status → active |
| 4 | Reactivated member accesses console | Full access restored per role |
| 5 | Owner bans member | Member status → banned, removed from business |
| 6 | Banned user tries to rejoin | Blocked — business rule violation |

### W21: Audit Trail Verification

**Systems**: Audit, Organization, RBAC
**Parameters**: P1, P4

| Step | Action | Verify |
|------|--------|--------|
| 1 | Perform 5 tracked actions (invite, role change, settings update, etc.) | Actions succeed |
| 2 | Navigate to business audit log | Audit page renders |
| 3 | Verify all 5 actions appear | Entries present with correct actor, action, timestamp |
| 4 | Filter by action type | Only matching entries shown |
| 5 | Navigate to platform audit log | Platform-level entries visible |

### W22: Business Status Lifecycle

**Systems**: Organization, RBAC
**Parameters**: P1, P2, P4, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | Create business | Active status |
| 2 | Suspend business | Status → suspended, public profile restricted |
| 3 | Verify suspended business restrictions | Members can't access console, public view shows suspended notice |
| 4 | Reactivate business | Status → active, full access restored |
| 5 | Archive business | Status → archived, read-only |
| 6 | Verify archived business | Console read-only, no new actions allowed |

### W23: OAuth Registration Flow

**Systems**: Auth
**Parameters**: P1, P2, P3, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | Click "Continue with Google" on login page | Redirect to Google OAuth |
| 2 | (Simulated) Google callback with valid state | Account created, auto-verified, session established |
| 3 | Verify user profile has Google-provided data | Name, email from OAuth |
| 4 | Logout and login via Google again | Existing account matched, no duplicate |

### W24: Full Notification Lifecycle

**Systems**: Notification, Transaction, Organization, Navigation
**Parameters**: P1, P2, P3, P4, P6

| Step | Action | Verify |
|------|--------|--------|
| 1 | Trigger action that generates notification (e.g., invitation) | Notification created |
| 2 | Notification appears in notification center | Badge count increments, notification in list |
| 3 | Click notification | Navigate to source (transaction detail) |
| 4 | Take action on source (accept invitation) | Action succeeds |
| 5 | Return to notifications | Notification marked as actioned, badge decrements |
| 6 | Mark remaining notifications as read | All read, badge cleared |

### W25: Chat Request → DM → Block Flow

**Systems**: Chat, Network
**Parameters**: P1, P2, P4, P6

| Step | Action | Verify |
|------|--------|--------|
| 1 | Stranger sends DM to user | Chat request appears (not in main inbox) |
| 2 | User navigates to chat requests | Request listed with message preview |
| 3 | User accepts request | Conversation moves to main inbox |
| 4 | User and stranger exchange messages | Real-time message delivery |
| 5 | User blocks stranger | Conversation hidden, block confirmed |
| 6 | Stranger's messages no longer reach user | Block enforcement verified |
| 7 | User unblocks stranger | Block removed (conversation may reappear) |

### W26: Form Builder Complete Lifecycle

**Systems**: Forms, Transaction, Organization
**Parameters**: P1, P2, P4

| Step | Action | Verify |
|------|--------|--------|
| 1 | Create form template | Draft created |
| 2 | Add 5+ field types | Text, select, date, checkbox, number fields |
| 3 | Configure field validation (required, min/max) | Validation rules saved |
| 4 | Reorder fields | Order persists |
| 5 | Publish template | Published, usable |
| 6 | Map as required form for join request | Mapping saved |
| 7 | User submits join request → form renders | All field types render correctly |
| 8 | Fill form with valid data → submit | Response saved with transaction |
| 9 | Owner reviews form response | All fields displayed correctly |

### W27: Business Network Management

**Systems**: Network, Organization, RBAC
**Parameters**: P1, P2, P4, P5

| Step | Action | Verify |
|------|--------|--------|
| 1 | Business gains followers (via API) | Follower count increments |
| 2 | Owner navigates to followers management | Followers list renders |
| 3 | Owner removes a follower | Follower removed, count decrements |
| 4 | Business gains connections (via API) | Connection count increments |
| 5 | Owner navigates to connections management | Connections list renders |
| 6 | Owner manages connection | Connection actions work |

### W28: Feature Gate Degradation

**Systems**: Feature Gates, Chat
**Parameters**: P1, P5, P7

| Step | Action | Verify |
|------|--------|--------|
| 1 | Verify chat system is accessible | Chat page loads, messages work |
| 2 | Disable chat system gate (via config) | System gate off |
| 3 | Navigate to chat | 403 or redirect, UI hides chat nav |
| 4 | Verify chat nav item hidden | Feature removed from navigation |
| 5 | Re-enable chat system gate | System gate on |
| 6 | Verify chat restored | Chat page loads, nav item visible |

### L2 Summary

**Total: 28 workflow files, ~185 individual steps**

---

## 11. L3 Persona Scenarios — Complete Catalog

### Design Principles for L3

1. **Realistic**: Each persona behaves as a real user would — exploring, making mistakes, going back
2. **Comprehensive**: Together, all personas cover 100% of features and routes
3. **Adversarial**: Each persona has a critical eye — they push boundaries and test edge cases
4. **Progressive**: State builds naturally through the journey — no API shortcuts
5. **Isolated**: Each scenario starts with a fresh database. No shared state between personas.

---

### Persona A: Alice the Newcomer

**Profile**: New to the platform. Explores everything. Cautious but curious. Tests onboarding friction, discovery, and organic growth.

**Adversarial angle**: Tries things out of order. Accesses protected routes before authenticating. Abandons processes midway. Tests what the naive user encounters.

**Systems covered**: Auth, Explore, Network, Transaction, Organization, Chat, Notifications, Settings, Visibility

| Step | Action | What We Verify | Parameters |
|------|--------|---------------|------------|
| 1 | Visit site anonymously, browse explore page | Public pages accessible, no auth data leaks | P1, P3, P5 |
| 2 | Click on a business profile (public view) | Public fields visible, private fields hidden (visibility tiers) | P1, P4, P5 |
| 3 | Try to access `/chat` directly (protected route) | Redirected to login, return URL preserved in query string | P3, P5 |
| 4 | Try to access `/bconsole/some-business/` (not a member) | Redirected or 403, no data leakage | P3, P5, P11 |
| 5 | Navigate to register page | Registration form renders correctly | P1 |
| 6 | Submit with missing required fields | Inline validation errors shown | P2, P7 |
| 7 | Register with valid data | Account created, redirect to verification prompt | P2, P5 |
| 7a | **Verify email** — enter wrong code first | Error message, not verified | P2, P7 |
| 7b | **Enter correct verification code** | Email verified, success page | P2, P5 |
| 8 | Try to register again with same email | Duplicate email error shown clearly | P7 |
| 9 | Login with new credentials | Session established, **home page** loads | P2, P5 |
| 9a | **Browse home feed** | Home feed renders, activity items present | P1, P4 |
| 9b | **Navigate to activity page** | Activity list renders | P1, P3 |
| 10 | Explore businesses — search with query | Results appear, relevance ordering | P1, P2, P4 |
| 11 | Apply filters to search | Results narrow correctly | P2, P4 |
| 12 | View a business profile (now authenticated) | More fields visible than anonymous (T2 visibility) | P1, P4, P5 |
| 13 | Follow 3 businesses | Follow status updates each time, count increments | P2, P4, P6 |
| 14 | Unfollow 1 business | Status reverts, count decrements | P2, P4 |
| 15 | Navigate to network page | 2 followed businesses listed, counts correct | P1, P4 |
| 16 | Search for users | User results appear (auth-required endpoint works) | P1, P4, P5 |
| 17 | Send connection request to a user | Request created, pending state shown on profile | P2, P4 |
| 18 | Other user accepts (via API setup) | Connection established, Alice's network page updates | P4, P6 |
| 19 | Start chat with connected user | Conversation created, message view opens | P1, P2 |
| 20 | Send a text message | Message appears in thread with timestamp | P2, P4, P6 |
| 21 | Send a message with image attachment | Image uploads, preview shown, lightbox works | P2 |
| 22 | React to a received message | Reaction appears, count updates | P2, P4 |
| 23 | Request to join a business (with open requests) | Transaction created, pending status shown | P2, P4 |
| 24 | Business has required form → fill and submit | Form renders, validates, submits with transaction | P2, P4 |
| 25 | Get accepted (via API) → see notification | Notification appears | P4, P6 |
| 26 | Business appears in account switcher | Can switch to business context | P1, P3 |
| 27 | Browse business console as member | Member-appropriate features visible | P1, P5 |
| 28 | Try to access owner-only features via URL | Blocked — 403 or redirect | P5, P11 |
| 29 | Navigate to settings | Settings page renders | P1, P3 |
| 30 | Update notification preferences | Preferences saved | P2, P14 |
| 31 | Check notification center | All accumulated notifications present, counts correct | P1, P4 |
| 32 | Logout | Session cleared | P2, P5 |
| 33 | Login again | All data persists — profile, follows, memberships, preferences | P5, P14 |

---

### Persona B: Bob the Entrepreneur

**Profile**: Business-focused power user. Creates and manages a business from scratch. Tests the full business lifecycle, team management, limits, and eventually transfers ownership.

**Adversarial angle**: Tests quota boundaries. Assigns roles then verifies enforcement. Tries to break quotas. Tests what happens after ownership loss.

**Systems covered**: Auth, Organization, RBAC, Transaction, Forms, Network, Chat, Notifications, Limits

| Step | Action | What We Verify | Parameters |
|------|--------|---------------|------------|
| 1 | Register and login | Baseline auth flow | P2, P5 |
| 2 | Create business account (fill all fields) | Business created, redirect to console | P1, P2, P3 |
| 3 | Customize business profile (bio, avatar, category, tags) | All field types save correctly | P2, P4 |
| 4 | Open new incognito context → view business as anonymous | Visibility tiers correct: public fields only | P1, P4, P5 |
| 5 | Navigate to role management | Default roles listed (owner, member) | P1, P4 |
| 6 | Create custom role "Editor" with specific permissions | Role created with selected permissions | P2, P4 |
| 7 | Create custom role "Viewer" with minimal permissions | Second role created | P2, P4 |
| 8 | Navigate to form builder | Form template list (empty or with defaults) | P1 |
| 9 | Create form template for join requests (text, select, date, checkbox) | All field types work in builder | P1, P2 |
| 9a | **Publish form template** | Status → published, available for mapping | P2 |
| 9b | **Configure business visibility settings** (T2 fields) | Visibility saved, public view reflects changes | P2, P4, P5 |
| 10 | Configure form as required for join requests | Form-transaction mapping saved | P2 |
| 11 | Invite User A as member | Invitation transaction created | P2, P4 |
| 12 | Invite User B as member | Second invitation created | P2, P4 |
| 13 | User A accepts (via API) | Membership created with default role | P4 |
| 14 | User B accepts (via API) | Membership created with default role | P4 |
| 15 | Assign "Editor" role to User A | Role changed, User A sees updated permissions | P2, P4, P5 |
| 16 | Verify User A can access Editor-permitted features | Feature visible in console | P5 |
| 17 | Verify User A CANNOT access restricted features | Feature hidden or 403 | P5, P11 |
| 18 | Verify User B (default role) has different access than User A | RBAC enforcement per role | P5 |
| 19 | Set max_members = 4 (owner + 3 slots, 2 filled) | Setting saved, quota visible | P2, P10 |
| 20 | Invite User C | Invitation sent (3/4 after accept) | P2 |
| 21 | User C accepts (via API) | Count: 4/4, at quota | P4, P10 |
| 22 | Invite User D → expect quota error | Clear "member quota exceeded" message | P7, P10 |
| 23 | Remove User B from business | Member removed, count: 3/4 | P2, P4, P10 |
| 24 | Invite User D again → succeeds | Count: 4/4, quota works correctly after removal | P2, P10 |
| 25 | Navigate to business chat | Business scope chat | P1, P3 |
| 26 | Start entity conversation as business | Entity chat works | P1, P2 |
| 27 | Send message as business entity | Message attributed to business | P2, P4 |
| 28 | External user sends join request (via API) | Request appears in transaction list | P4, P6 |
| 29 | Review form response attached to request | Form data displayed correctly | P1, P4 |
| 30 | Approve join request | Membership created, member count updates | P2, P4 |
| 30a | **Suspend User B** from business | User B status → suspended, can't access console | P2, P5 |
| 30b | **Reactivate User B** | User B restored, access works again | P2, P5 |
| 30c | **Navigate to audit log** | All actions (invites, role changes, suspend/reactivate) logged | P1, P4 |
| 31 | Initiate ownership transfer to User A (Editor) | Transfer transaction created | P2, P4 |
| 32 | User A accepts transfer (via API) | Ownership transferred | P4 |
| 33 | Bob refreshes console | Bob now has member role, owner features hidden | P1, P5 |
| 34 | Bob tries to access owner-only features | Blocked — RBAC enforced after ownership loss | P5, P11 |

---

### Persona C: Carol the Platform Administrator

**Profile**: Platform-level administrator. Oversees the entire platform. Manages businesses, members, configuration. Tests the admin perspective.

**Adversarial angle**: Tests admin privilege boundaries. Verifies platform-wide visibility. Checks that admin actions are auditable.

**Systems covered**: Auth, Platform, RBAC, Organization, Transactions, Forms, CMS, Notifications

| Step | Action | What We Verify | Parameters |
|------|--------|---------------|------------|
| 1 | Login as platform admin | Admin access granted | P2, P5 |
| 2 | Platform console dashboard renders | Stats, counts, recent activity all present | P1, P4 |
| 3 | Navigate to businesses list | All businesses on platform listed with details | P1, P4 |
| 4 | View specific business detail from platform | Cross-entity view renders, data accurate | P1, P4 |
| 5 | Navigate to platform members | Member list with roles | P1, P4 |
| 6 | Create platform-specific role | Role created at platform scope | P2, P4 |
| 7 | Navigate to platform transactions | All transaction types visible | P1, P4 |
| 8 | Navigate to platform forms | Form templates at platform scope | P1, P4 |
| 9 | Platform settings: update configuration | Settings persist after page refresh | P2, P14 |
| 10 | Navigate to platform chat | Platform scope chat | P1, P3 |
| 11 | Start conversation as platform entity | Entity chat at platform scope | P1, P2 |
| 12 | **Navigate to CMS sites** | CMS site list renders | P1 |
| 12a | **Create a CMS site** | Site created, appears in list | P1, P2 |
| 12b | **Create content template** | Template with schema saved | P1, P2 |
| 12c | **Create page → add blocks → publish** | Page published, public view accessible | P1, P2, P4 |
| 12d | **Edit published content → publish new version** | Versioning works, new content live | P1, P2 |
| 12e | **Verify public view shows published content** (incognito) | Anonymous user sees CMS content | P1, P4 |
| 12f | **Manage CMS API keys** — create, view prefix, revoke | Key lifecycle works | P1, P2, P5 |
| 12g | **Manage CMS media library** — upload, list, delete | Media operations work | P1, P2 |
| 13 | Navigate to platform forms management | Platform-scoped form templates visible | P1, P4 |
| 13a | Navigate to platform transactions | Transaction types visible at platform scope | P1, P4 |
| 13b | Navigate to approved creators management | Creator list renders | P1, P4 |
| 14 | Navigate to platform audit log | All actions logged with correct details | P1, P4 |
| 15 | Try to access a specific business's internal console | Should work (admin privilege) or blocked (scope isolation) | P5 |
| 16 | Open incognito context as regular user → try platform console | Blocked — only admins access platform console | P5, P11 |
| 17 | Verify platform actions in audit trail | Actions logged correctly | P4 |

---

### Persona D: Dave the Social Butterfly

**Profile**: Highly social user. Follows many businesses, connects with many users, uses chat heavily. Tests social features at volume and concurrency.

**Adversarial angle**: Tests rapid-fire actions. Sends many messages quickly. Creates many connections. Pushes for race conditions and ordering bugs.

**Systems covered**: Auth, Network, Chat, Notifications, Explore, Settings

| Step | Action | What We Verify | Parameters |
|------|--------|---------------|------------|
| 1 | Register and complete profile | Baseline | P2, P5 |
| 2 | Follow 10 businesses in rapid succession | All follows registered, no duplicates, no race conditions | P2, P4, P6 |
| 3 | Verify network page shows 10 followed | Count accurate, all listed | P1, P4 |
| 4 | Search users, send connection requests to 5 users | All requests created, all in pending state | P2, P4 |
| 5 | 3 users accept (via API), 1 declines, 1 pending | All statuses correct in Dave's view | P4 |
| 6 | Start conversations with 3 connected users | All conversations created | P2, P4 |
| 7 | Send messages rapidly in conversation 1 (5 messages, 1-second gaps) | All 5 messages appear in correct order | P2, P4, P6 |
| 7a | **Edit a sent message** | Message content updates, "edited" indicator shown | P2, P4 |
| 7b | **Delete a sent message** | Message removed from thread | P2, P4 |
| 7c | **Check delivery status indicators** | Sent → delivered → seen progression visible | P4, P6 |
| 7d | **Check presence indicators** | Online contacts show green dot | P4, P6 |
| 8 | Switch to conversation 2, send messages | Messages in correct conversation (no cross-contamination) | P4 |
| 9 | Receive messages from 2 users simultaneously | Both messages appear in correct conversations, real-time | P4, P6, P13 |
| 10 | Create group chat with 4 participants | Group created, all participants listed | P2, P4 |
| 11 | All participants send messages (via API) | Messages appear in correct order, correct attribution | P4, P6 |
| 12 | Search messages across all conversations | Results from correct conversations, relevance ranking | P2, P4 |
| 13 | Block a user | Blocked user's conversation hidden, can't message Dave | P2, P4 |
| 14 | Unblock the user | Conversation reappears (if applicable) | P2, P4 |
| 15 | Check notification center | All social notifications present (follows, connections, messages) | P1, P4 |
| 16 | Mark all notifications as read | Badge clears, read state persists on refresh | P2, P14 |
| 17 | Navigate to network page | All counts match: 10 following, 3 connections, 2 pending, 1 declined | P1, P4 |
| 17a | **Browse following list** | All 10 followed businesses listed, unfollow action works | P1, P4 |
| 17b | **Browse connections list** | 3 connections listed, pending shown separately | P1, P4 |
| 18 | **Navigate to activity feed** | Activity items from all social interactions present | P1, P4 |

---

### Persona E: Eve the Adversary

**Profile**: Deliberately tries to break the application. Tests security boundaries, authorization bypasses, input injection, edge cases, and error handling.

**Adversarial angle**: This IS the adversarial persona. Every single step attempts to exploit, abuse, or crash something.

**Systems covered**: Auth, RBAC, Organization, Chat, Forms, Network, Transactions, Limits, Security

| Step | Action | What We Verify | Parameters |
|------|--------|---------------|------------|
| 1 | Register with XSS in name field: `<script>alert('xss')</script>` | Name displayed safely everywhere (escaped), no script execution | P11 |
| 2 | Register with SQL injection in email: `test' OR '1'='1` | Rejected or sanitized, no database error exposed | P7, P11 |
| 3 | Login with wrong password 11 times | Account lockout triggers after threshold, clear lockout message, `Retry-After` shown | P5, P7, P10 |
| 4 | Wait for lockout to expire, login successfully | Lockout lifts, access restored | P5 |
| 5 | Directly navigate to `/bconsole/other-business-slug/` (not a member) | 403 or redirect, no business data visible | P5, P11 |
| 6 | Directly navigate to `/pconsole/dashboard` (not platform admin) | 403 or redirect, no platform data visible | P5, P11 |
| 7 | Manipulate URL parameters: `/explore?page=-1` | Graceful handling — first page shown or empty, no crash | P7 |
| 8 | Manipulate URL parameters: `/explore?page=999999` | Empty results or last page, no server error | P7 |
| 9 | Open browser DevTools, modify JWT in storage, refresh | Token invalid → redirected to login, no stale data shown | P5, P11 |
| 10 | Upload non-image file renamed to .jpg as avatar | MIME type check rejects it, error message shown | P7, P11 |
| 11 | Submit form with every field exceeding max length | Validation catches all fields, specific error per field | P7, P10 |
| 12 | Send empty chat message (bypass disabled button via DOM) | Backend rejects, no empty message saved | P11 |
| 13 | Send chat message with 50,000 characters | Length limit enforced at frontend or backend, clear error | P7, P10 |
| 14 | Open 2 browser tabs as 2 different users (Tab A: User X, Tab B: User Y) | Sessions isolated, Tab A shows User X data, Tab B shows User Y data | P5, P14 |
| 15 | In Tab A, try to access User Y's private profile data via URL | Authorization blocks it | P5, P11 |
| 16 | Expire access token manually (delete from storage), then click a button | Silent refresh works OR redirect to login. No partial/broken state | P5, P7 |
| 17 | Try to invite self to own business | Business rule violation displayed clearly | P7 |
| 18 | Try to create business with duplicate name/slug | Handled gracefully — error message, not 500 | P7 |
| 19 | Rapidly click "Accept" on a transaction 5 times in 1 second | Idempotent — transaction accepted once, no duplicates, no 500 | P2, P7 |
| 20 | Navigate to non-existent route: `/this-page-does-not-exist` | Custom 404 page renders, not white screen | P3, P7 |
| 21 | Request to join business with closed member requests | Clear "member requests closed" message (not "quota exceeded") | P7, P10 |
| 22 | As regular member, try owner-only API actions via browser network tab (DevTools) | Backend returns 403, frontend doesn't break | P5, P11 |
| 23 | Send XSS payload in chat message: `<img src=x onerror=alert(1)>` | Message displayed as text, no script execution | P11 |
| 24 | Enter XSS in search query: `"><script>alert(1)</script>` | Search handles it safely, no injection | P11 |
| 25 | **Open 5 tabs simultaneously as same user** | All 5 sessions work, max session limit (5) enforced | P5, P10, P14 |
| 26 | **Attempt account deactivation** | Deactivation prompt with clear warning; Execute → logged out | P2, P5 |
| 27 | **Try to login after deactivation** | Account deactivated message, can't login | P5, P7 |
| 28 | **Navigate to a feature-gated page (with gate disabled)** | 403 or graceful redirect, UI hides feature | P5, P7 |
| 29 | **Submit duplicate transaction** (same type to same target) | Conflict detection → clear error message, not 500 | P7 |

---

### Persona F: Frank the Multi-Context Switcher

**Profile**: Power user who operates across personal, multiple business, and platform contexts. Tests context isolation and account switching.

**Adversarial angle**: Rapid context switching. Verifies no data leaks between contexts. Tests that chat scope isolation holds.

**Systems covered**: Auth, Organization, RBAC, Chat, Navigation, Network

| Step | Action | What We Verify | Parameters |
|------|--------|---------------|------------|
| 1 | Register and login | Baseline | P2, P5 |
| 2 | Create Business A | Business A console accessible | P2, P3 |
| 3 | Create Business B | Business B console accessible | P2, P3 |
| 4 | Switch to Business A console via account switcher | Correct data for Business A displayed | P1, P3, P4 |
| 5 | Navigate to Business A member management | Business A members shown (not B's) | P4 |
| 6 | Switch to Business B console | Correct data for Business B, zero Business A data | P1, P3, P4 |
| 7 | Navigate to Business B member management | Business B members shown (not A's) | P4 |
| 8 | Switch back to personal context | Personal data: profile, network. No business data leaking | P1, P3, P4 |
| 9 | Receive invitation to Business C (owned by another user, via API) | Notification appears in personal context | P4, P6 |
| 10 | Accept invitation | Business C appears in account switcher | P2, P3 |
| 11 | Switch to Business C console | Business C data. Frank has member role (not owner) | P1, P4, P5 |
| 12 | Verify Frank can't access owner features of Business C | RBAC enforcement in foreign business | P5 |
| 13 | Start chat in personal context | Personal chat scope conversation | P1, P2 |
| 14 | Switch to Business A context, start chat | Business A chat scope conversation | P1, P2 |
| 15 | Verify Business A chat NOT visible in personal context | Scope isolation enforced | P4, P5 |
| 16 | Verify personal chat NOT visible in Business A context | Scope isolation enforced | P4, P5 |
| 17 | Rapidly switch contexts 5 times | No stale data, no flash of wrong content, no errors | P1, P3, P4, P7 |
| 18 | **Check notifications in personal context** | Only personal notifications (connections, follows) | P4, P5 |
| 19 | **Switch to Business A → check notifications** | Only Business A notifications (member actions, transactions) | P4, P5 |
| 20 | **Verify notification scope isolation** | Business B notifications NOT in Business A, and vice versa | P4, P5 |
| 21 | **Browse activity feed in personal context** | Personal activity items only | P1, P4 |

---

### Persona G: Gary the CMS Content Manager (Optional)

**Profile**: Platform admin focused specifically on content management. Exercises the full CMS system lifecycle. Tests content creation, publishing, versioning, and public delivery.

**Adversarial angle**: Tests content with XSS payloads in rich text. Tests media upload limits. Tests draft/publish lifecycle edge cases (edit published, rollback).

**Systems covered**: Auth, Platform, CMS, Media

| Step | Action | What We Verify | Parameters |
|------|--------|---------------|------------|
| 1 | Login as platform admin | Admin access granted | P2, P5 |
| 2 | Navigate to CMS sites | Site list renders (may be empty) | P1 |
| 3 | Create CMS site with domain | Site created, domain configured | P1, P2 |
| 4 | Create content template with schema | Template saved, schema validates | P1, P2 |
| 5 | Create page using template | Page in draft status | P1, P2 |
| 6 | Add content blocks (heading, text, image, rich_text) | Blocks render in editor | P1, P2 |
| 7 | Enter XSS in rich text block: `<img src=x onerror=alert(1)>` | HTML sanitized (nh3), no script | P11 |
| 8 | Publish page | Status → published | P2 |
| 9 | Open incognito → verify public view | Published content visible, correct layout | P1, P4 |
| 10 | Edit published page → save as new draft | Published version still live, draft editable | P2, P4 |
| 11 | Publish new draft | New version replaces old, content updated | P2, P4 |
| 12 | Upload media (images, valid MIME types) | Upload succeeds, media in library | P2 |
| 13 | Upload invalid file (non-image disguised as .jpg) | MIME check rejects, error shown | P7, P11 |
| 14 | Create API key | Key created, `cmsk_` prefix shown, full key shown once | P1, P2, P5 |
| 15 | Revoke API key | Key deactivated, API requests with key fail | P2, P5 |
| 16 | Archive old content template | Template hidden from active list | P2 |
| 17 | Delete unpublished page | Page removed | P2 |
| 18 | Verify media tombstoning | Deleted media returns 410 Gone, not 404 | P4, P7 |

---

## 12. Multi-Persona Interaction Scenario

**The ultimate integration test.** Multiple personas interact with each other simultaneously using separate browser contexts.

### Setup

- Fresh database
- Personas created in order: Bob, Alice, Dave, Carol, Eve
- Each persona has their own browser context (Playwright `browser.newContext()`)

### Script

| Step | Actor | Action | Verification |
|------|-------|--------|-------------|
| 1 | **Bob** | Registers, creates Business "TechCorp", opens member requests | Business exists, open for requests |
| 2 | **Bob** | Creates form template, maps as required for join requests | Form configured |
| 3 | **Alice** | Registers, searches explore, finds "TechCorp" | Search returns Bob's business |
| 4 | **Alice** | Follows "TechCorp" | Follower count increments (Bob can verify) |
| 5 | **Alice** | Requests to join "TechCorp" → fills required form | Transaction created (PENDING_REVIEW) |
| 6 | **Bob** | Sees Alice's request with form response | Request visible, form data correct |
| 7 | **Bob** | Approves Alice's request | Alice becomes member |
| 8 | **Alice** | Sees notification, accesses TechCorp console | Console loads with member features |
| 9 | **Dave** | Registers, sends connection request to Alice | Connection request created |
| 10 | **Alice** | Accepts Dave's connection request | Connection established |
| 11 | **Dave** | Starts chat with Alice | Conversation created |
| 12 | **Dave** | Sends message: "Hey Alice!" | Alice sees message in real-time |
| 13 | **Alice** | Replies: "Hi Dave!" | Dave sees reply in real-time |
| 14 | **Bob** | Sends message to Alice in business context | Alice sees business message in entity inbox |
| 15 | **Carol** | Logs in as platform admin | Platform console loads |
| 16 | **Carol** | Views "TechCorp" in platform business list | Business details accurate (members: Bob, Alice) |
| 17 | **Eve** | Registers, tries to access TechCorp console directly | Blocked — 403 |
| 18 | **Eve** | Tries to join TechCorp when quota is reached (set via API to max_members=3, already 2) | Quota error OR succeeds depending on count |
| 19 | **Bob** | Sets max_members = 2 (just Bob + Alice) via API | Quota updated |
| 20 | **Eve** | Requests to join TechCorp | "Member quota exceeded" error |
| 21 | **Eve** | Sends XSS in chat to Dave: `<script>alert(1)</script>` | Message displayed as text, no execution in Dave's browser |

---

## 13. CI/CD Pipeline

### Three Pipeline Tiers

```
┌─────────────────────────────────────────────────────┐
│  PR Pipeline (every pull request)                    │
│  ► L1 Smoke tests only                              │
│  ► Parallel execution, all workers                   │
│  ► Budget: < 5 minutes                              │
│  ► Gate: must pass to merge                         │
├─────────────────────────────────────────────────────┤
│  Main Pipeline (merge to main branch)               │
│  ► L1 Smoke + L2 Workflow tests                     │
│  ► Moderate parallelism                              │
│  ► Budget: < 20 minutes                             │
│  ► Gate: failure alerts team, doesn't block deploy   │
├─────────────────────────────────────────────────────┤
│  Nightly Pipeline (scheduled, daily)                │
│  ► ALL tests: L1 + L2 + L3                          │
│  ► Visual regression comparison                      │
│  ► Full coverage report generated                    │
│  ► Budget: < 60 minutes                             │
│  ► Artifacts: HTML report, screenshots, videos       │
└─────────────────────────────────────────────────────┘
```

### Pipeline Steps (Generic — Applies to All Tiers)

```
1. Start E2E Docker stack (docker-compose.e2e.yml)
2. Wait for health checks:
   - Backend: GET /health/ → 200
   - Frontend: GET / → 200
   - Database: pg_isready
   - Redis: redis-cli ping
3. Run global-setup.ts (DB reset, migrations, seed, create auth states)
4. Execute tests (Playwright with --project flag for tier selection)
5. Collect artifacts on failure:
   - Screenshots (automatic on failure)
   - Videos (configurable per layer)
   - Playwright traces (on failure, for debugging)
6. Generate HTML report
7. Upload artifacts to CI storage
8. Tear down Docker stack
```

### Retry Strategy

| Layer | Retries | Rationale |
|-------|---------|-----------|
| L1 | 1 retry on failure | Smoke tests should be rock-solid. 1 retry catches flakes. |
| L2 | 2 retries on failure | Cross-domain tests have more moving parts. |
| L3 | 0 retries | Scenarios must pass cleanly. Flakiness indicates a real problem. |

---

## 14. Docker Infrastructure

### Isolated E2E Stack

Separate from the development Docker stack. Different ports to avoid conflicts.

```yaml
# docker-compose.e2e.yml (conceptual)
services:
  postgres-e2e:
    image: postgres:17
    ports: ["5433:5432"]          # Port 5433 (not 5432) to avoid dev conflict
    environment:
      POSTGRES_DB: backend_core_e2e_db
      POSTGRES_USER: django_user
      POSTGRES_PASSWORD: django_password

  redis-e2e:
    image: redis:7
    ports: ["6380:6379"]          # Port 6380 (not 6379) to avoid dev conflict

  backend-e2e:
    build:
      context: ../backend
      dockerfile: ../e2e/docker/Dockerfile.backend
    ports: ["8001:8000"]          # Port 8001
    environment:
      DJANGO_SETTINGS_MODULE: backend_core.settings.local_docker
      POSTGRES_HOST: postgres-e2e
      POSTGRES_PORT: 5432
      POSTGRES_DB: backend_core_e2e_db
      REDIS_URL: redis://redis-e2e:6379/0
    depends_on:
      postgres-e2e: { condition: service_healthy }
      redis-e2e: { condition: service_healthy }
    volumes:
      - e2e-media:/app/media          # Media storage for file upload tests
    command: >
      sh -c "python manage.py migrate &&
             daphne -b 0.0.0.0 -p 8000 backend_core.asgi:application"
    # NOTE: Daphne (ASGI) required for WebSocket chat tests — NOT runserver

  frontend-e2e:
    build:
      context: ../frontend
      dockerfile: ../e2e/docker/Dockerfile.frontend
    ports: ["3001:3000"]          # Port 3001
    environment:
      NEXT_PUBLIC_API_URL: http://backend-e2e:8000
    depends_on:
      - backend-e2e

volumes:
  e2e-media:                           # Persistent media volume for upload tests
```

**Docker environment notes:**
- **Backend**: Must use Daphne ASGI server (NOT `runserver`) — chat system uses WebSocket via Django Channels
- **Celery tasks**: `CELERY_TASK_ALWAYS_EAGER=True` — tasks run synchronously, no separate worker needed
- **Media storage**: Mount `/media/` volume for file upload tests (avatars, attachments, chat images)
- **Frontend**: Must be production build (`npm run build && npm start`) for accurate E2E

### Why Isolated?

1. **No conflicts** with development environment (different ports, different database)
2. **Reproducible** — same stack every time, regardless of local dev state
3. **CI-ready** — same docker-compose runs locally and in CI
4. **Clean state** — fresh database per run, no leftover dev data

---

## 15. Feature Gate Testing Design

### Day 1: All Features Enabled

For the initial implementation, all feature gates are enabled (full deployment configuration). Tests validate the complete platform.

### Limits Tested From Day 1

These are embedded in L1, L2, and L3 tests:

| Limit | Where Tested |
|-------|-------------|
| `max_members` quota | L1 `member-quota.spec.ts`, L2 W15, L3 Bob step 22 |
| Rate limiting (429) | L1 `rate-limits.spec.ts`, L3 Eve step 3 |
| Field length limits | L1 `field-length-limits.spec.ts`, L3 Eve steps 11, 13 |
| File upload size | L3 Eve step 10 |
| Chat message length | L3 Eve step 13 |
| Conversation participant limit | L2 W7 (if applicable) |

### Future: Config-Aware Testing

The architecture supports feature-gate-aware test execution:

```typescript
// lib/feature-gates.ts
import deploymentConfig from '../deployment_config.json';

export const featureGates = {
  isSystemEnabled(system: string): boolean {
    return deploymentConfig.systems?.[system] === true;
  },
  isFeatureEnabled(path: string): boolean {
    // Navigate nested config by dot path
    // e.g., "chat.attachments" → deploymentConfig.features.chat.attachments
  },
  getLimit(path: string): number {
    // e.g., "organization.business.max_members" → config value
  }
};

// In tests:
test.skip(!featureGates.isSystemEnabled('chat'), 'Chat system disabled');

test('send message', async ({ page }) => {
  // This test only runs if chat is enabled
});
```

### Adding Gate Variants (Future)

`playwright.config.ts` can define multiple projects with different configs:

```typescript
// Future: playwright.config.ts
projects: [
  {
    name: 'full-deployment',
    use: { deploymentConfig: 'full' },
    testDir: './tests',
  },
  {
    name: 'user-only-deployment',
    use: { deploymentConfig: 'user_only' },
    testDir: './tests',
    // Tests auto-skip based on disabled features
  },
]
```

This is not implemented on day 1, but the architecture doesn't need to change to support it.

---

## 16. Reporting & Coverage

### Test Annotations

Every test file includes metadata for the reporting system:

```typescript
/**
 * @layer L1
 * @system auth
 * @parameters P1, P2, P3, P5, P7
 * @priority critical
 */
test.describe('Login', () => {
  // ...
});
```

### Report Types

| Report | Generated By | Frequency | Purpose |
|--------|-------------|-----------|---------|
| **Playwright HTML Report** | Playwright built-in | Every run | Pass/fail per test, screenshots, traces |
| **Coverage Matrix** | Custom script | Nightly | System × Parameter × Layer coverage heatmap |
| **Gap Report** | Custom script | On demand | Which parameters lack coverage per system |
| **Trend Report** | CI aggregation | Weekly | Pass rate over time, flakiness tracking |

### Coverage Matrix Format

```
                    P1   P2   P3   P4   P5   P6   P7   P8   P9   P10  P11  P12  P13  P14
Auth                ██   ██   ██   ░░   ██   ░░   ██   ██   ░░   ██   ██   ░░   ░░   ██
User                ██   ██   ██   ██   ░░   ░░   ░░   ░░   ░░   ░░   ░░   ░░   ░░   ██
Business            ██   ██   ██   ██   ██   ░░   ██   ██   ░░   ██   ██   ░░   ██   ██
Chat                ██   ██   ░░   ██   ░░   ██   ░░   ██   ░░   ██   ██   ░░   ██   ░░
...

██ = covered   ░░ = gap
```

---

## 17. Run Strategy & Time Budgets

### Playwright Config Projects

```typescript
// playwright.config.ts projects (conceptual)
projects: [
  {
    name: 'smoke-desktop',
    testDir: './tests/smoke',
    use: { viewport: { width: 1280, height: 720 } },
  },
  {
    name: 'smoke-mobile',
    testDir: './tests/smoke/responsive',
    use: { ...devices['iPhone 14 Pro'] },
  },
  {
    name: 'workflows',
    testDir: './tests/workflows',
    use: { viewport: { width: 1280, height: 720 } },
  },
  {
    name: 'scenarios',
    testDir: './tests/scenarios',
    use: {
      viewport: { width: 1280, height: 720 },
      video: 'on',        // Always record L3 scenarios
      trace: 'on',         // Always capture traces for L3
    },
  },
]
```

### Execution Time Estimates

| Layer | Test Files | Parallel Workers | Est. Time |
|-------|-----------|------------------|-----------|
| L1 Smoke (desktop) | 85 | 4 workers | ~6 min |
| L1 Smoke (mobile) | 4 | 2 workers | ~1 min |
| L2 Workflows | 28 | 2 workers | ~20 min |
| L3 Scenarios | 8 | 1 worker (sequential) | ~55 min |
| **Total** | **125** | — | **~82 min** |

### Makefile Targets

```makefile
e2e-install:     # Install Playwright + Chromium browser
e2e-up:          # Start E2E Docker stack
e2e-down:        # Stop E2E Docker stack
e2e-reset:       # Reset E2E database (drop + create + migrate + seed)
e2e:             # Run all E2E tests (headless)
e2e-smoke:       # Run L1 smoke tests only
e2e-workflows:   # Run L2 workflow tests only
e2e-scenarios:   # Run L3 scenario tests only
e2e-headed:      # Run with visible browser (for debugging)
e2e-ui:          # Run with Playwright interactive UI mode
e2e-report:      # Open HTML test report
e2e-update:      # Update visual regression baselines
```

---

## 18. Decision Log

All architectural decisions recorded for traceability.

| # | Decision | Choice | Alternatives Considered | Rationale |
|---|----------|--------|------------------------|-----------|
| D1 | Test framework | Playwright | Cypress, Selenium, TestCafe | Best auto-wait, multi-context, trace viewer, screenshot comparison. Native TypeScript. |
| D2 | Browser | Chromium only | Multi-browser (Chrome, Firefox, Safari) | Speed. Chromium covers 80%+ market. Add others later without architecture change. |
| D3 | Mobile testing | Viewport emulation | Real devices, BrowserStack | Emulation tests responsive CSS. Real device testing is a future concern. |
| D4 | Data strategy | Hybrid (API + Progressive) | Fresh DB per test, shared fixtures, seeders only | Most reliable. API setup for speed (L1/L2), progressive for realism (L3). |
| D5 | Page abstraction | POM (Page Object Model) | Raw selectors, component testing | One place to update when UI changes. 50 tests don't break for a selector change. |
| D6 | Auth management | storageState | Login in beforeEach, shared cookies | Login once in global setup, reuse. Saves 30+ seconds per test. |
| D7 | File organization | Layer-first, system-second | System-first, flat | Each layer has different run characteristics (time, parallelism, frequency). |
| D8 | Docker infra | Isolated E2E stack | Share dev stack, no Docker | Reproducible, no conflicts with dev, CI-ready. |
| D9 | Visual regression | Playwright toHaveScreenshot | Percy, Chromatic, custom | Built-in, no external dependency, baselines in git. |
| D10 | Feature gates | All enabled (day 1) | Minimal, test each variant | Full deployment first. Architecture supports variants later via config. |
| D11 | Limits testing | Day 1 | Defer to later | Quotas/limits are critical for production correctness. Can't defer. |
| D12 | CI pipeline | 3-tier (PR/Main/Nightly) | Single pipeline | Different layers have different costs. PR: fast gate. Nightly: comprehensive. |
| D13 | L3 personas | 6 + 1 multi-interaction | Fewer personas, more workflows | Personas catch real user journey bugs that isolated workflows miss. |
| D14 | Adversarial testing | Dedicated persona (Eve) + angles in all personas | Separate security suite | Security is woven into the user experience, not a separate concern. |
| D15 | CMS persona | Dedicated Persona G (Gary) | CMS steps in Carol only | CMS has 30 features across 11 models — too much to embed in one persona. Gary isolates CMS testing. |
| D16 | Backend server | Daphne ASGI | `manage.py runserver` | WebSocket (chat) requires ASGI. `runserver` does NOT support WebSocket connections. |
| D17 | Gap analysis companion | Separate document | Inline in architecture.md | 1,014-line audit would bloat architecture doc. Cross-reference via link. |

---

## Appendix A: System × Layer × Parameter Coverage Map

```
SYSTEM              L1 FILES  L2 WORKFLOWS               L3 PERSONAS                       PARAMETERS
──────────────────────────────────────────────────────────────────────────────────────────────────────────
Auth                8         W1, W17, W23               Alice(1-9b), Bob(1),              P1-P5, P7, P8,
                                                         Eve(1-4,9,12,16,25-27)            P10, P11, P14
User                7         W1                         Alice(9a-9b,10,20,29-30)          P1-P4, P14
Explore             3         W6, W11                    Alice(10-12,16),                  P1-P5
                                                         Dave(2-4)
Organization        13        W2, W4, W6, W13,           Bob(2-4,9b,19-24,30a-c),          P1-P5, P7, P10,
(Business)                    W14, W15, W20, W22         Frank(2-8,11-12)                  P11, P13, P14
Organization        8         W13, W18                   Carol(1-17),                      P1-P5, P14
(Platform)                                               Gary(1-18)
RBAC                (in biz)  W3, W10, W14, W20          Bob(5-7,15-18,30a-b,33-34),       P1, P2, P4, P5,
                                                         Alice(27-28), Frank(12)           P11
Transaction         7         W2-W6, W12, W14, W15       Alice(23-26), Bob(11-14,          P1, P2, P4, P5,
                                                         20,22,28-32), Eve(17,19,29)       P7, P10, P13
Forms               6         W4, W5, W19, W26           Bob(8-9a,29),                     P1, P2, P4
                                                         Alice(24)
Chat                13        W7, W8, W16, W25           Alice(19-22),                     P1, P2, P4, P6,
                                                         Dave(6-14,7a-d), Bob(25-27),      P8, P10, P11, P13
                                                         Frank(13-16), Eve(12-13,23)
Network             6         W6, W9, W11, W27           Alice(13-18),                     P2, P4, P6, P13
                                                         Dave(2-5,17-17b)
Notifications       3         W3, W9, W12, W24           Alice(25,31),                     P1, P4, P6, P14
                                                         Dave(15-16), Frank(18-20)
CMS                 5         W18                        Carol(12-12g),                    P1, P2, P4, P5,
                                                         Gary(2-18)                        P7, P11
Feature Gates       1         W28                        Eve(28)                           P1, P5, P7
Limits              3         W15                        Bob(19-24), Eve(3,11,13,          P2, P7, P10
                                                         17,21)
Responsive          4         —                          —                                 P1, P2, P8
Security            (in Eve)  —                          Eve(ALL)                          P5, P7, P11
Visibility          (in biz)  —                          Alice(2,12), Bob(4,9b)            P1, P4, P5
Public/Nav          2         —                          —                                 P1, P3, P4, P5
Audit               (in biz)  W21                        Bob(30c), Carol(14)               P1, P4
```

---

## Appendix B: Test Count Summary

| Category | v0.1 (Original) | v0.2 (After Audit) |
|----------|-----------------|-------------------|
| L1 Smoke test files | 45 | **89** |
| L1 estimated test cases | ~135 | **~270** |
| L2 Workflow files | 16 | **28** |
| L2 estimated steps | ~100 | **~185** |
| L3 Scenario files | 7 | **8** (+ Gary) |
| L3 estimated steps | ~175 | **~250** |
| Page Object Models | 13 | **~28** |
| Helper files | 7 | **~12** |
| **Total test files** | **68** | **~125** |
| **Total estimated assertions** | **~410** | **~705** |

---

## Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **POM** | Page Object Model — pattern where page UI is represented by a class with locators and methods |
| **storageState** | Playwright feature to save/restore browser auth state (cookies, localStorage) |
| **Smoke test** | Quick test that verifies basic functionality works (happy path) |
| **Workflow** | Multi-step test crossing multiple systems |
| **Scenario** | Full user journey simulating realistic behavior over many steps |
| **Parameter (P1-P14)** | Dimension of quality being verified (render, interaction, nav, etc.) |
| **API client** | HTTP wrapper that calls backend API directly for fast test data setup |
| **Browser context** | Playwright's isolated browser session (separate cookies, storage) |
| **Visual regression** | Screenshot comparison against approved baselines to catch UI drift |
| **Feature gate** | Configuration toggle that enables/disables platform features per deployment |

---

---

## Appendix D: Architecture Audit (2026-03-27) — RESOLVED in v0.2

> **Audit method**: Cross-referenced architecture doc against full codebase inventory:
> **90 frontend routes**, **~200 API endpoints**, **234+ frontend components**, **18 backend apps/systems**.
> **Status**: All CRITICAL and HIGH findings have been incorporated into the main document (Sections 2, 9, 10, 11, 14).
> **Deep analysis**: See [System Feature Gap Analysis](system-feature-gap-analysis.md) for feature-by-feature breakdown (426 features, 17 systems).
> Appendix D below is preserved for audit trail — all findings marked with resolution status.

### CRITICAL: Docker Infrastructure Error (Section 14)

The architecture doc specifies `manage.py runserver` for the backend container. **This will NOT work for chat E2E tests.** The chat system uses WebSocket via Django Channels + Daphne ASGI server. `runserver` does not support WebSocket.

**Fix required:**

| Item | Current (Wrong) | Correct |
|------|-----------------|---------|
| Backend server | `python manage.py runserver` | `daphne -b 0.0.0.0 -p 8000 backend_core.asgi:application` |
| Celery tasks | Not mentioned | `CELERY_TASK_ALWAYS_EAGER=True` (tasks run synchronously — no worker needed) |
| Media storage | Not mentioned | Must mount `/media/` volume for file upload tests (avatars, attachments) |
| Frontend build | Not specified | Must be **production build** (`npm run build && npm start`) for accurate E2E |

### CRITICAL: Missing Routes — 30+ Pages Not Covered

The doc claims to cover all features but **misses 30+ actual frontend routes**. Organized by severity:

#### Missing from L1 Smoke Tests (should have dedicated tests)

| Route | What It Is | Why It Matters |
|-------|-----------|----------------|
| `/verify-email` | Email verification page | **Critical auth flow** — registration is useless without it |
| `/resend-verification` | Resend verification | Part of auth recovery |
| `/verify-success` | Verification success | Completion of auth flow |
| `/home` | User home feed | **Primary landing page** after login — not tested anywhere |
| `/activity` | User activity stream | Entire feature untested |
| `/activity/[id]` | Activity detail | Entire feature untested |
| `/users/[username]` | Other user's public profile | Different from `/profile` (self) — not covered |
| `/profile/edit` | Profile edit (separate route) | Doc treats view+edit as one; they are separate routes |
| `/` | Landing page | First thing anonymous users see |
| `/about` | About page | Public page, renders correctly? |
| `/contact` | Contact page | Public page, renders correctly? |
| `/admin` | Admin dashboard | Super-admin route, completely missing |

#### Missing from Business Console L1 (27 routes exist, doc covers ~6)

| Route | What It Is |
|-------|-----------|
| `/bconsole/[slug]/network/followers` | Business follower management page |
| `/bconsole/[slug]/network/connections` | Business connection management page |
| `/bconsole/[slug]/content` | CMS content list (business scope) |
| `/bconsole/[slug]/media` | Media library (business scope) |
| `/bconsole/[slug]/transactions/requests` | Separate requests list page |
| `/bconsole/[slug]/transactions/requests/[id]` | Request detail page |
| `/bconsole/[slug]/transactions/invitations` | Separate invitations list page |
| `/bconsole/[slug]/transactions/invitations/[id]` | Invitation detail page |
| `/bconsole/[slug]/transactions/settings` | Transaction settings (form mappings) |
| `/bconsole/[slug]/audit` | Audit log page |
| `/bconsole/[slug]/members/[id]` | Individual member detail page |
| `/bconsole/[slug]/members/roles/[id]` | Member role assignment page |
| `/bconsole/[slug]/forms/templates/new` | Create new form template page |
| `/bconsole/[slug]/forms/templates/[id]` | Edit specific form template page |
| `/bconsole/[slug]/forms/library` | Form public library page |
| `/bconsole/[slug]/forms/responses` | Form responses list page |
| `/bconsole/[slug]/forms/responses/[id]` | Form response detail page |

#### Missing from Platform Console L1 (25 routes exist, doc covers ~3)

| Route | What It Is |
|-------|-----------|
| `/pconsole/businesses` | Businesses list/management |
| `/pconsole/approved-creators` | Approved creators management |
| `/pconsole/members/[id]` | Platform member detail |
| `/pconsole/members/roles/[id]` | Member role assignment |
| `/pconsole/roles` | Platform role management |
| `/cconsole/sites` | CMS sites management |
| `/cconsole/templates` | CMS template list (create/edit via dialogs) |
| `/cconsole/api-keys` | API key management |
| `/cconsole/media` | CMS media library |
| `/cconsole/businesses` | Business CMS management |
| `/cconsole/[slug]/sites` | Business CMS sites |
| `/cconsole/[slug]/catalog` | Business template catalog |
| `/cconsole/[slug]/library` | Business template library |
| `/pconsole/media` | Platform media library |
| `/pconsole/forms/*` | All platform form routes (7 routes) |
| `/pconsole/transactions/*` | All platform transaction routes (6 routes) |
| `/pconsole/audit` | Platform audit log |

### CRITICAL: Missing Features/Functionality Not Tested

| Feature | Status in Doc | Actual State |
|---------|--------------|--------------|
| **Email verification flow** | Not in L1, vaguely in W1 | 3 dedicated routes exist, critical for registration |
| **OAuth (Google/Apple)** | Not mentioned anywhere | API endpoints + frontend components exist |
| **Password change** (while logged in) | Not tested | Different from password reset; API + component exists |
| **Account deactivation** | Not tested | API endpoint + frontend exists |
| **Activity feed** | Not mentioned in any test | 2 routes, full feature |
| **Home feed** | Not mentioned in any L1 | Primary authenticated landing page |
| **CMS system** | Only vague mention in Carol scenario | 6 platform console routes, 17 API endpoints, full admin UI |
| **Audit log** | Not in any L1 | 2 routes (business + platform), audit trail verification |
| **Form template lifecycle** | Only "create" in L1 | publish, archive, unarchive, fork, edit-draft all untested |
| **Form field CRUD + reorder** | Not tested | Core form builder interactions |
| **Chat edit/delete message** | Not tested | Edit + delete APIs + UI components exist |
| **Chat mute/unmute** | Not tested | API + UI exists |
| **Chat promote/demote participant** | Not tested | Group admin management |
| **Chat media gallery** | Not tested | Separate API + component |
| **Cover image upload** | Not tested | Separate from avatar, API + component exists |
| **Username change/check** | Not tested | Real-time validation component exists |
| **Social links editor** | Not tested | Profile editing component |
| **Business suspend/reactivate/archive** | Not tested | 3 API actions, lifecycle management |
| **Member suspend/ban/reactivate** | Not tested in L1 | 3 member action APIs + components |
| **Approved creators** | Not tested | Platform management feature |
| **Transaction settings** (form mappings) | Not tested in L1 | Separate settings page exists |
| **Visibility settings** | Not tested | User + business profile visibility configuration |
| **Account switcher** | Only in Frank L3 | Core navigation component, used constantly |

### HIGH: Parameter Framework Gaps

| Parameter | Issue |
|-----------|-------|
| **P9 (Visual Regression)** | Not assigned to ANY specific L1 test. No smoke test file is tagged with P9. Systematic gap. |
| **P12 (Accessibility)** | Not assigned to ANY L1 test. Zero accessibility coverage in smoke tests. |
| **P14 (State Persistence)** | Only assigned to 3 tests (settings, logout, profile-edit). Missing: chat draft persistence, notification read state, context switch state. |

### HIGH: Missing L1 Smoke Tests (Additions Required)

Based on the audit, these L1 test files must be added:

```
tests/smoke/
  auth/
    + email-verification.spec.ts        # Verify email flow (3 routes)
    + password-change.spec.ts            # Authenticated password change
  user/
    + home-feed.spec.ts                  # Home page renders after login
    + activity-feed.spec.ts              # Activity list + detail
    + other-user-profile.spec.ts         # /users/[username] page
  business/
    + business-network.spec.ts           # Followers + connections management pages
    + business-transactions-detail.spec.ts  # Requests/invitations list + detail pages
    + business-audit.spec.ts             # Audit log page
    + business-content.spec.ts           # CMS content + media pages
  platform/
    + platform-businesses.spec.ts        # Businesses list management
    + platform-cms.spec.ts               # CMS sites, templates, API keys, media
    + platform-transactions.spec.ts      # Platform transaction management
    + platform-audit.spec.ts             # Platform audit log
    + platform-forms.spec.ts             # Platform form management
  public/
    + landing-pages.spec.ts              # /, /about, /contact render correctly
  navigation/
    + account-switcher.spec.ts           # Account context switching (critical UX)
```

**Revised L1 count: 45 → 61 test files**

### HIGH: Missing L2 Workflows (Additions Required)

| # | Workflow | Systems | Why Missing Matters |
|---|----------|---------|---------------------|
| W17 | **Registration → Email Verification → First Login** | Auth | Current W1 skips verification entirely. Registration without verification is incomplete. |
| W18 | **CMS Content Lifecycle** | CMS, Platform | Create site → create template → create page → add blocks → publish → verify public |
| W19 | **Form Template Lifecycle** | Forms, Organization | Create → add fields → reorder → publish → fork → edit draft → publish new version |
| W20 | **Member Discipline Flow** | Organization, RBAC | Suspend member → verify restricted access → reactivate → verify restored access |
| W21 | **Audit Trail Verification** | Audit, Organization, RBAC | Perform 5 actions → navigate to audit log → verify all 5 appear correctly |
| W22 | **Business Status Lifecycle** | Organization | Create → suspend → verify restricted → reactivate → archive → verify archived |

**Revised L2 count: 16 → 22 workflows**

### HIGH: Persona Scenario Gaps

| Persona | Missing Steps |
|---------|--------------|
| **Alice** | Steps 7→9 skip email verification (register → login, but how without verifying?). Must add verify-email step. Also missing: home feed page, activity page. |
| **Bob** | Missing: CMS/content management from business console, audit log verification, business visibility settings, form template publish flow. |
| **Carol** | CMS testing is "if UI exists" — it DOES exist (6 routes, 17 APIs). Must be explicit. Missing: approved creators, platform forms, platform transactions detail pages, platform audit. |
| **Dave** | Missing: activity feed interaction, notification preferences impact on received notifications. |
| **Eve** | Missing: OAuth bypass attempts, account deactivation abuse, concurrent session manipulation beyond 2 tabs. |
| **Frank** | Missing: activity feed across contexts, notification scope isolation. |
| **ALL** | No persona tests OAuth login (Google/Apple). No persona tests account deactivation. No persona tests password change while logged in. |

### MEDIUM: POM (Page Object Model) Gaps

Missing page objects that need to be added to `pages/` directory:

```
pages/
  auth/
    + verify-email.page.ts
    + resend-verification.page.ts
  user/
    + activity.page.ts
    + other-user-profile.page.ts
  business/
    + business-network.page.ts          # Followers + connections management
    + business-transactions.page.ts     # Requests/invitations list + detail
    + business-audit.page.ts
    + business-content.page.ts          # CMS content + media
  platform/
    + platform-businesses.page.ts
    + platform-cms.page.ts
    + platform-audit.page.ts
  admin/
    + admin.page.ts
  public/
    + landing.page.ts
```

### MEDIUM: Helper Gaps

Missing helpers for test data setup:

```
helpers/
  + user.helper.ts                      # verifyEmailViaApi(), changePasswordViaApi()
  + platform.helper.ts                  # configurePlatformViaApi(), manageCmsViaApi()
  + member-actions.helper.ts            # suspendMemberViaApi(), banMemberViaApi()
```

### MEDIUM: Section 2 Table Inaccuracies

| Row | Issue |
|-----|-------|
| Row 3 (Business) | Says "12 routes" — actual count is **27 routes** |
| Row 4 (Platform) | Says "14 routes" — actual count is **25 routes** |
| Row 6 (Transactions) | Says "Transaction list + detail" — actually 6 business + 6 platform routes |
| Row 7 (Forms) | Says "Template builder + submissions" — actually 7 business + 7 platform routes |
| Row 9 (Network) | Says "Network page" — actually 3 routes (network + business followers + business connections) |
| Row 11 (CMS) | Says "(admin-only)" — platform console has 6 CMS routes |
| Missing | Activity feature not listed (2 routes, own system) |
| Missing | Public/landing pages not listed (3 routes) |
| Missing | Admin not listed (1 route) |

### MEDIUM: Internal Consistency Issues

1. **Appendix A** claims Auth covers P8 (Responsive) — but the responsive test is in `responsive/auth-mobile.spec.ts`, not `auth/`. Attribution is correct but may confuse readers.
2. **Appendix B** says "68 total test files" — after adding missing tests, this will be **~84 files**.
3. **Session management L1** (`session-management.spec.ts`) covers list + info display but not session revocation.
4. **Health endpoint**: Section 13 references `GET /api/health` but actual endpoint is `GET /health/` (no `/api` prefix).

### LOW: Structural Suggestions

1. **`tests/smoke/public/`** directory missing from structure — needed for landing page tests.
2. **`tests/smoke/navigation/`** directory missing — needed for account switcher tests.
3. **`fixtures/` naming**: Consider adding `multi-business-owner.json` for Frank's scenario (owns 2+ businesses).

---

### Audit Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **CRITICAL** | 3 | Docker server wrong (Daphne not runserver), 30+ routes missing, major features untested |
| **HIGH** | 4 | P9/P12 parameters unassigned, 16 L1 tests missing, 6 workflows missing, persona gaps |
| **MEDIUM** | 4 | POM gaps, helper gaps, Section 2 inaccuracies, internal consistency |
| **LOW** | 1 | Structural suggestions |

### Revised Counts After Fixes

| Category | Original | After Fixes |
|----------|----------|-------------|
| L1 Smoke test files | 45 | **61** |
| L2 Workflow files | 16 | **22** |
| L3 Scenario files | 7 | **7** (same files, more steps per persona) |
| Page Object Models | 13 | **25** |
| Helper files | 7 | **10** |
| **Total test files** | **68** | **~90** |

---

*End of document. Version 0.2.0 — All audit findings incorporated. Pending review and approval before implementation begins.*

*Companion document: [system-feature-gap-analysis.md](system-feature-gap-analysis.md) — 426-feature deep audit with per-system coverage tables.*
