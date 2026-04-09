# Changelog

All notable changes to the E2E test suite are documented in this file.

## [1.0.0] — 2026-03-27

### Summary

Initial release of the full E2E testing suite. **125 test files, 465 tests** across 3 test layers covering 18 platform systems.

### Added

**Infrastructure (Phase 0-2)**
- Playwright configuration with 4 projects: smoke-desktop, smoke-mobile, workflows, scenarios
- Docker E2E stack: PostgreSQL 5433, Redis 6380, Backend (Daphne) 8001, Frontend 3001
- `ApiClient` — HTTP client ported from Python `APIHelper` for API-driven test data setup
- `DbClient` — Direct PostgreSQL client for email verification codes, password resets, data seeding
- `global-setup.ts` — DB health checks, user creation, storageState generation for 5 roles
- Feature gate integration — `isSystemEnabled()`, `getOrgMode()` for conditional `test.skip()`
- Base fixture with `apiClient` and `dbClient` injection

**Page Object Models (Phase 3)**
- 28 POM files covering all platform pages
- Accessibility-first selectors: `getByRole()` > `getByLabel()` > `getByText()` > `getByTestId()`
- `BasePage` with shared nav, header, toast, footer locators

**L1 Smoke Tests (Phases 4-8) — 89 files, 236 tests**
- Auth: 8 files (login, register, logout, password reset/change, email verification, session, OAuth)
- Users: 7 files (profile view/edit, settings, home/activity feed, other-user, username change)
- Business: 13 files (profile, creation, console, members, roles, settings, lifecycle, visibility, etc.)
- Platform: 8 files (profile, console, management, businesses, CMS, forms, transactions, audit)
- Chat: 13 files (conversations, messaging, groups, attachments, reactions, search, requests, etc.)
- Network: 6 files (follow, connect, network page, following/connection list, disconnect)
- Transactions: 7 files (invitation, join-request, ownership transfer, list, deny/cancel, pages, form-mapping)
- Forms: 6 files (template builder, submission, responses, lifecycle, field CRUD, all field types)
- CMS: 5 files (site management, page publish, content editing, media library, API keys)
- Notifications: 3 files (center, preferences, history)
- Explore: 3 files (search businesses, search users, filters)
- Feature Gates: 1 file (403 + UI degradation)
- Limits: 3 files (member quota, rate limits, field length)
- Navigation: 1 file (account switcher)
- Public: 1 file (landing pages)
- Responsive: 4 files (auth, chat, navigation, business console on mobile)

**L2 Workflow Tests (Phase 10) — 28 files, 30 tests**
- 25 active cross-system workflows (auth-to-profile, business creation, chat realtime, etc.)
- 12 multi-browser-context workflows (two users simultaneously)
- 15 feature-gated workflows with conditional skip
- 3 deferred workflows (notification inbox + audit log APIs not yet built)

**L3 Persona Scenarios (Phase 12) — 8 files, 199 tests**
- Alice (36 steps): Newcomer onboarding journey
- Bob (37 steps): Business entrepreneur lifecycle
- Eve (29 steps): Adversarial security testing
- Carol (17 steps): Platform administrator
- Dave (20 steps): Social features + real-time
- Frank (21 steps): Multi-context scope isolation
- Gary (18 steps): CMS management lifecycle
- Multi-Persona (21 steps): 5 actors interacting simultaneously

**Cross-Cutting (Phase 11)**
- 4 responsive/mobile test files (iPhone 14 Pro viewport)
- `a11y-checks.ts` accessibility utilities

**Reporting (Phase 13)**
- `generate-coverage-matrix.ts` — System x Parameter x Layer heatmap
- `generate-gap-report.ts` — Feature area gap analysis
- Auto-generated: `coverage-matrix.md`, `parameter-checklist.md`, `gap-report.md`

**CI/CD (Phase 9)**
- GitHub Actions: PR (L1 <5min), Main (L1+L2 <20min), Nightly (all <60min)

**Documentation (Phase 14)**
- `README.md` — Quick start, structure, troubleshooting
- `CHANGELOG.md` — This file
- Test layer catalogs: `l1-smoke-tests.md`, `l2-workflow-tests.md`, `l3-scenario-tests.md`, `ci-cd-pipeline.md`
- `CLAUDE.md` — Governance mandates and project rules

### Coverage

| Metric | Value |
|--------|-------|
| Test files | 125 |
| Total tests | 465 |
| Systems covered | 18/18 (Limits is L1 only) |
| Feature areas covered | 76/90 (84.4%) |
| Matrix cells covered | 113/252 (44.8%) |
| P9 (Visual Regression) | 0% (baselines not yet established) |
| P12 (Accessibility) | 0% (utility added, tests deferred) |

### Known Gaps

- **Visual Regression (P9)**: `toHaveScreenshot()` baselines not yet established — add to stable pages in future release
- **Accessibility (P12)**: `a11y-checks.ts` utility created but no dedicated a11y test files yet
- **Limits system**: Only L1 smoke coverage (3 files) — no L2/L3 coverage
- **3 deferred workflows**: Blocked on notification inbox API and audit log read API
