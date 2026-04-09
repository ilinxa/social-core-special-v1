# E2E Test Report — L1 Smoke Desktop Rerun

**Date:** 2026-03-31
**Layer:** L1 Smoke Desktop
**Project:** `smoke-desktop`
**Duration:** 266s (~4.4 min)
**Runner:** Local (4 workers, 1 retry)

---

## Summary

| Metric | Count | Rate |
|--------|-------|------|
| **Passed** | 264 | 92.6% |
| **Failed** | 16 | 5.6% |
| **Flaky** | 3 | 1.1% |
| **Skipped** | 2 | 0.7% |
| **Total** | 285 | — |

**Compared to prior run (same day, earlier):** pass rate improved from 89.5% (255) to 92.6% (264). 8 fewer failures. CMS and Notifications remain the only failing areas.

---

## Failed Tests (16)

### CMS — Platform Admin (10 failures)

| # | Test | File | Error Type |
|---|------|------|------------|
| 1 | CMS API Keys > key appears in list after dialog close | `cms-api-keys.spec.ts` | `toBeVisible` failed |
| 2 | CMS API Keys > revoke API key marks it as revoked | `cms-api-keys.spec.ts` | Timeout 15s (click) |
| 3 | CMS Page Publishing > create page via dialog shows draft badge | `cms-page-publish.spec.ts` | `toBeVisible` failed |
| 4 | CMS Page Publishing > publish page via UI | `cms-page-publish.spec.ts` | Timeout 15s (click) |
| 5 | CMS Page Publishing > unpublish reverts to draft | `cms-page-publish.spec.ts` | Timeout 15s (click) |
| 6 | CMS Site Management > platform admin can edit a site | `cms-site-management.spec.ts` | Timeout 15s (click) |
| 7 | CMS Site Management > platform admin can delete a site | `cms-site-management.spec.ts` | Timeout 15s (click) |
| 8 | CMS Business Management > business CMS management page lists businesses | `platform-business-management.spec.ts` | `toBeVisible` failed |
| 9 | CMS Business Management > toggle CMS on/off for a business | `platform-business-management.spec.ts` | Timeout 15s (click) |
| 10 | CMS Business Management > view activated templates sheet | `platform-business-management.spec.ts` | Timeout 15s (click) |

### CMS — Business (1 failure)

| # | Test | File | Error Type |
|---|------|------|------------|
| 11 | CMS Business Site CRUD > business can delete a site | `business-site-crud.spec.ts` | Timeout 15s (click) |

### CMS — Template Browser (1 failure)

| # | Test | File | Error Type |
|---|------|------|------------|
| 12 | CMS Template Browser > switch to block templates tab | `platform-templates-browser.spec.ts` | `toBeVisible` failed |

### Notifications (3 failures)

| # | Test | File | Error Type |
|---|------|------|------------|
| 13 | Notification Center > scope tabs are visible | `notification-center.spec.ts` | `toBeVisible` failed |
| 14 | Notification Center > notification list or empty state is shown | `notification-center.spec.ts` | `toBeVisible` failed |
| 15 | Notification Preferences > category cards render for all 5 categories | `notification-preferences.spec.ts` | `toBeVisible` failed |

### Forms (1 failure)

| # | Test | File | Error Type |
|---|------|------|------------|
| 16 | Field Types > template list shows templates or empty state | `field-types-all.spec.ts` | `toBeVisible` failed |

---

## Flaky Tests (3)

| Test | File | Notes |
|------|------|-------|
| Business Visibility > profile edit form has name and description fields | `business-visibility.spec.ts` | Race: `useBusiness()` query not settled before assertion |
| Chat Attachments > attachment button exists in compose bar | `attachments.spec.ts` | Race: WebSocket + store hydration timing |
| Username Change > change username successfully | `username-change.spec.ts` | Race: mutation not committed before `page.reload()` |

---

## Root Cause Analysis

### RC1: API Key list — ARIA role mismatch (2 tests)

**POM selector:** `page.getByRole('listitem').filter({ hasText: keyName })`
**Actual DOM:** API key rows are `<div>` elements inside `<div className="space-y-2">` — no `<ul>/<li>` structure, so `getByRole('listitem')` matches nothing.

**Affected files:**
- POM: `e2e/pages/cms/api-keys.page.ts:69-71`
- Frontend: `frontend/src/features/cms/components/ApiKeyManagementPage.tsx:126-159`

---

### RC2: `<Can>` permission gates hide action buttons (8 tests)

Edit, Delete, Publish, Unpublish buttons are wrapped in `<Can allowed={permissions?.can_*}>`. If the `_permissions` object is missing or the flag is `false`, buttons are not rendered at all.

**Example (SiteDetailPage.tsx:131-150):**
```tsx
<Can allowed={permissions?.can_edit_site}>
  <Button>Edit</Button>
</Can>
<Can allowed={permissions?.can_delete_site}>
  <Button>Delete</Button>
</Can>
```

Tests click these buttons but they never appear because either:
1. The backend detail endpoint does not return `_permissions` for the test user's role, or
2. The specific permission flag is `false` for the test user.

**Affected files:**
- `SiteDetailPage.tsx` — edit/delete site buttons
- `PageEditor.tsx` — publish/unpublish buttons
- `BusinessCmsManagementPage.tsx` — toggle/template sheet actions
- Business CMS — delete site button

---

### RC3: Notification tab accessible name includes badge count (2 tests)

**POM selector:** `page.getByRole('tab', { name: /^all$/i })`
**Actual DOM:** Tab renders as `<TabsTrigger>All <Badge>5</Badge></TabsTrigger>` — accessible name becomes `"All 5"`, which does not match `/^all$/i`.

**Affected files:**
- POM: `e2e/pages/notifications/notifications.page.ts:52-55`
- Frontend: `frontend/src/features/notifications/components/NotificationScopeTabBar.tsx:42-48`

---

### RC4: CardTitle renders `<div>`, not heading (1 test)

**POM selector:** `page.getByRole('heading', { name: /authentication/i })`
**Actual DOM:** `<CardTitle>` is a `<div data-slot="card-title">` — no heading role.

**Affected files:**
- POM: `e2e/pages/notifications/notifications.page.ts:88-92`
- Frontend: `frontend/src/components/ui/card.tsx:31-38`
- Frontend: `frontend/src/features/notifications/components/PreferenceCategorySection.tsx:29`

---

### RC5: Async data loading without explicit waits (3 tests)

Tests navigate and immediately assert content without waiting for React Query hooks to resolve. While components show loading skeletons, the expected elements only appear after API data arrives.

**Affected tests:** Business management list, template browser tabs, page publish badge.

---

### RC6: Flaky tests — mutation/query timing races (3 tests)

- **Business visibility:** `useBusiness()` not settled; form inputs appear only after data loads.
- **Chat attachments:** WebSocket + Zustand store not hydrated; `.or()` masks the issue.
- **Username change:** `page.reload()` fires before mutation response returns and persists.

---

## Failure Distribution

| Area | Failed | Root Causes |
|------|--------|-------------|
| CMS (all) | 12 | RC1, RC2, RC5 |
| Notifications | 3 | RC3, RC4 |
| Forms | 1 | RC5 (likely) |
| **Total** | **16** | — |

---

## Systems Fully Passing

Auth, Register, Login, Logout, Password Reset/Change, Session Management, OAuth, Email Verification, User Profile, User Settings, Business (CRUD, members, audit, visibility, followers), Chat (all 13 files), Network (all 6 files), Transactions (all 7 files), Explore (all 3 files), Feature Gates, Limits, Navigation, Public — **all green**.

---

## Recommended Priority

| Priority | Action | Impact |
|----------|--------|--------|
| **P0** | Fix RC2 — ensure `_permissions` returned for CMS test users | Resolves 8 failures |
| **P0** | Fix RC3 — notification tab selectors to tolerate badge counts | Resolves 2 failures |
| **P0** | Fix RC1 — API key list ARIA or POM selector | Resolves 2 failures |
| **P1** | Fix RC4 — CardTitle heading semantics or POM selector | Resolves 1 failure |
| **P1** | Fix RC5 — add explicit waits for async data in tests | Resolves 3 failures |
| **P2** | Fix RC6 — stabilize flaky tests with proper waits | Resolves 3 flaky |

Fixing P0 items resolves **12 of 16 failures (75%)**.
