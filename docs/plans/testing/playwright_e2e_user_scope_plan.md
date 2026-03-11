# Playwright E2E Test Suite — User Scope (U-01 to U-99)

## Context

All 15 manual UI bug fixes are complete (U scope). Now we automate the entire 99-item User scope checklist as Playwright E2E tests running against the real backend + frontend. Target: ≥90% confidence (97/99 items automatable — U-17/U-18 OAuth excluded).

---

## Architecture

**Location:** `e2e/` at project root (own `package.json` — isolates `pg`, Playwright from frontend build)

**Why Playwright over enhanced Vitest:**
- Tests real browser interactions against real servers (not mocked hooks)
- Multi-user flows via separate browser contexts (privacy, transactions, sessions)
- File upload, navigation guards, URL param persistence, infinite scroll — all testable
- Built-in HTML reporter + custom checklist reporter for U-XX mapping

**Dependencies:** `@playwright/test`, `pg` (direct DB access for verification codes/tokens), `dotenv`

---

## Test Infrastructure

### Directory Structure

```
e2e/
  package.json              # Isolated dependencies
  playwright.config.ts      # 1 worker, sequential, desktop Chrome + mobile Pixel 7
  tsconfig.json
  global-setup.ts           # Seed User B, C, deactivate user, business via API + DB
  global-teardown.ts        # Close DB pool
  helpers/
    db-helper.ts            # PostgreSQL client (mirrors backend DBHelper exactly)
    api-helper.ts           # HTTP client for setup (register, login, create business)
    auth-helper.ts          # loginViaUI(), registerAndVerifyViaAPI()
    constants.ts            # Test user emails/passwords with e2e_ prefix
    fixtures.ts             # Extended Playwright fixtures (db, api)
  reporters/
    checklist-reporter.ts   # Maps [U-XX] test titles → JSON report
  fixtures/
    test-avatar.jpg         # Valid small image
    test-avatar-large.jpg   # >5MB for rejection
    test-file.txt           # Wrong format for rejection
  tests/
    01-registration.spec.ts       # U-01..U-07  (9 tests)
    02-email-verification.spec.ts # U-08..U-12  (6 tests)
    03-login.spec.ts              # U-13..U-20  (8 tests)
    04-password-management.spec.ts # U-21..U-27 (8 tests)
    05-session-management.spec.ts  # U-28..U-32 (6 tests)
    06-profile-view-edit.spec.ts   # U-33..U-39 (9 tests)
    07-avatar.spec.ts              # U-40..U-43 (4 tests)
    08-username.spec.ts            # U-44..U-46 (4 tests)
    09-privacy.spec.ts             # U-47..U-50 (5 tests)
    10-nav-layout.spec.ts          # U-51..U-58 (10 tests)
    11-explore-discovery.spec.ts   # U-59..U-74 (18 tests)
    12-public-pages.spec.ts        # U-75..U-82 (10 tests)
    13-user-transactions.spec.ts   # U-83..U-93 (13 tests)
    14-activity-notifications.spec.ts # U-94..U-96 (3 tests)
    15-account-deactivation.spec.ts   # U-97..U-99 (4 tests)
```

**Total: 117 tests covering 97/99 checklist items (98% coverage)**

### DB Helper (`db-helper.ts`)

Mirrors `backend/tests/api_integration/conftest.py` DBHelper exactly:
- Same PG connection: `backend_core_db`, `django_user`, `postgres_dev_password`, localhost:5432
- Same table names: `auth_verification_tokens`, `auth_password_reset_tokens`, `auth_device_sessions`, `auth_refresh_tokens`, `users`
- Same query patterns: poll with retry for verification codes/tokens
- Additional: `cleanupTestUsers()`, `setBusinessMaxMembers()`, `grantBusinessCreation()`

### API Helper (`api-helper.ts`)

Lightweight fetch wrapper for test setup:
- `register(email, password, username)` → POST /auth/register/
- `login(email, password)` → POST /auth/login/ → returns access_token
- `X-Client-Type: mobile` header to get tokens in response body

### Auth Helper (`auth-helper.ts`)

- `loginViaUI(page, email, password)` — fills login form, waits for /home redirect
- `registerAndVerifyViaAPI(email, password, username)` — registers + verifies via DB
- `setupAuthenticatedContext(context, email)` — creates page already logged in

### Global Setup (`global-setup.ts`)

1. Clean up leftover `e2e_*` test users from previous runs
2. Register + verify User B (`e2e_user_b`), User C (`e2e_user_c`), deactivate user
3. Set User B profile: public, first_name="Bob", last_name="Tester", country=US, city=New York, tags
4. Set User C profile: private
5. Grant User B business creation, create `e2e-test-business` (public, open_member_request=true, max_members=10)
6. **User A is NOT pre-seeded** — registration tests (U-01..U-07) create them

### Naming Convention

Every test title includes `[U-XX]` tag for the checklist reporter:
```typescript
test('[U-01] Registration form renders correctly', async ({ page }) => { ... });
```

---

## Test Plan Per File

### 01-registration.spec.ts (U-01..U-07, 9 tests)

| U-ID | Test | Selectors |
|------|------|-----------|
| U-01 | Form renders: email, username, password, confirm_password, "Create Account", OAuth, "Sign in" link | `getByLabel('Email')`, `getByLabel('Username')`, `getByLabel('Password')`, `getByLabel('Confirm Password')`, `getByRole('button', { name: 'Create Account' })` |
| U-02 | Valid registration → redirect to /verify-email | Fill all 4 fields, submit, `waitForURL(/verify-email/)` |
| U-03 | Duplicate email → "This email is already registered" | Use `e2e_user_b@test.com`, assert `.text-destructive` under email |
| U-04 | Duplicate username → "This username is already taken" | Use `e2e_user_b` username, assert `.text-destructive` under username |
| U-05 | Weak password (short) → client validation | Type "1234567", assert error "at least 8 characters" |
| U-05b | Weak password (no uppercase) → client validation | Type "testpass123!", assert error "uppercase" |
| U-06 | Empty submit → validation errors on all fields | Click submit, assert 4 error messages |
| U-07 | Invalid email format → validation error | Type "not-an-email", assert email error |

### 02-email-verification.spec.ts (U-08..U-12, 6 tests)

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-08 | Page renders with email param pre-filled | Navigate to `/verify-email?email=e2e_fresh@test.com`, assert email input disabled |
| U-09 | Valid code → redirect to /login or /home | Get code from DB via `db.getVerificationCode()`, fill 6-digit input, submit |
| U-10 | Wrong code → error shown | Fill "000000", submit, assert `role="alert"` error |
| U-11 | Multiple wrong codes → lockout/rate-limit | Loop 5+ wrong submissions, assert lockout message appears |
| U-12 | Resend button with cooldown | Click "Resend code", assert disabled with countdown text |

### 03-login.spec.ts (U-13..U-20, 8 tests)

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-13 | Form renders correctly | Assert email, password, "Sign In", OAuth, "Forgot password?", "Sign up" |
| U-14 | Valid login → /home | Fill verified user creds, submit, `waitForURL('/home')` |
| U-15 | Wrong password → "Invalid email or password" | Fill wrong password, assert `role="alert"` text |
| U-16 | Rate limit (10+ rapid attempts) | Loop 10+ wrong logins, assert "Too many attempts" or 429 |
| U-17 | Google OAuth button visible | Assert OAuth button for Google renders (smoke only — can't test full flow) |
| U-18 | Apple OAuth button visible | Assert OAuth button for Apple renders (smoke only — can't test full flow) |
| U-19 | "Forgot password?" → /forgot-password | Click link, `waitForURL('/forgot-password')` |
| U-20 | "Sign up" → /register | Click link, `waitForURL('/register')` |

### 04-password-management.spec.ts (U-21..U-27, 8 tests)

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-21 | Forgot password form renders | Navigate `/forgot-password`, assert email field + "Send Reset Link" |
| U-22 | Submit → success message (no enumeration) | Fill email, submit, assert "If an account exists" message |
| U-23 | Reset form renders with token | Get token from DB, navigate `/reset-password?token=<token>`, assert form |
| U-24 | Valid reset → redirect to login | Fill new password, submit, then login with new password succeeds |
| U-25 | Invalid token → error | Navigate with random UUID token, submit, assert "invalid or expired" |
| U-26 | Missing token → error | Navigate `/reset-password` (no param), assert error message |
| U-27 | Change password (authenticated) | Login, go to sessions/security, fill current + new, submit, re-login works |

### 05-session-management.spec.ts (U-28..U-32, 6 tests)

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-28 | Sessions page shows at least 1 session | Login, navigate `/sessions`, assert session card visible |
| U-29 | Current session has "Current" badge | Assert one session has the "Current" badge |
| U-30 | Current session has no Revoke button | Assert the "Current" session card has no "Revoke" button |
| U-31 | Revoke other session | Login in 2nd browser context → creates 2 sessions. In 1st context, revoke the other |
| U-32 | "Sign Out Everywhere" → redirect to /login | Click button, assert `waitForURL('/login')` |

### 06-profile-view-edit.spec.ts (U-33..U-39, 9 tests)

| U-ID | Test | Selectors |
|------|------|-----------|
| U-33 | Profile page renders with user info | `/profile` → assert heading, Edit Profile button, user data |
| U-34 | Edit form renders all fields | `/profile/edit` → assert first_name, last_name, phone, bio, country, city, timezone, language, tags, is_public toggle, Save/Cancel |
| U-35 | Update name → profile reflects change | Fill first/last name, save, check profile page shows new name |
| U-36 | Country selection filters city dropdown | Select "United States" in country combobox, assert city combobox enabled + shows US cities |
| U-37 | Tags can be added | Type tag, press Enter, assert chip appears |
| U-38 | Timezone/language dropdowns work | Select timezone + language, save |
| U-39 | Public toggle works | Toggle ON, save, verify from another user context |

### 07-avatar.spec.ts (U-40..U-43, 4 tests)

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-40 | Upload valid JPEG | `setInputFiles('test-avatar.jpg')` on hidden file input, assert image renders |
| U-41 | Reject >5MB file | `setInputFiles('test-avatar-large.jpg')`, assert toast "smaller than 5 MB" |
| U-42 | Reject non-image (.txt) | `setInputFiles('test-file.txt')`, assert toast "Only JPEG, PNG, GIF, and WebP" |
| U-43 | Remove avatar → fallback initials | Click "Remove", assert AvatarFallback shows initials |

### 08-username.spec.ts (U-44..U-46, 4 tests)

| U-ID | Test | Selectors |
|------|------|-----------|
| U-44 | Change username successfully | On `/settings`, clear + type new username, wait for "Available", click "Update Username" |
| U-45 | Taken username → error indicator | Type `e2e_user_b`, wait for "taken" indicator |
| U-46 | Invalid chars → validation error | Type "user@name!", assert validation message |

### 09-privacy.spec.ts (U-47..U-50, 5 tests)

Multi-user: User A views User B (public) and User C (private) profiles.

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-47 | Public profile fully visible | Navigate `/users/e2e_user_b`, assert name, bio, location, tags |
| U-48 | Private profile → "This profile is private" | Navigate `/users/e2e_user_c`, assert limited view message |
| U-49 | Limited view shows only avatar + username | Assert no bio/location/tags sections on private profile |
| U-50 | Own private profile is fully visible | Login as User C, navigate `/users/e2e_user_c` or `/profile`, assert full data |

### 10-nav-layout.spec.ts (U-51..U-58, 10 tests)

Desktop + mobile viewports (Pixel 7 project for mobile tests).

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-51 | Desktop sidebar sections | Assert Home, Explore, Notifications, Activity, Profile, Settings, Security links |
| U-52 | Sidebar navigation works | Click each nav item, assert URL changes |
| U-53 | Mobile bottom navbar | Pixel 7 viewport, assert bottom nav with 4 icons |
| U-54 | Mobile menu sheet | Click hamburger, assert sheet opens with full nav |
| U-55 | User menu dropdown | Click user avatar in topbar, assert Profile, Settings, Sign Out options |
| U-56 | User menu Sign Out | Click Sign Out, `waitForURL('/login')` |
| U-57 | Account switcher (no memberships) | Assert only "Personal" shown |
| U-58 | Auth guard redirect | Without login, navigate `/profile`, assert redirect to `/login?callbackUrl=...` |

### 11-explore-discovery.spec.ts (U-59..U-74, 18 tests)

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-59 | Explore page renders | `/explore` → heading, search bar, tabs |
| U-60 | Search bar updates URL | Type "test", assert `?q=test` in URL |
| U-61 | Businesses tab shows cards | Click tab, assert BusinessCard components |
| U-62 | Users tab auth-gated | Anonymous → tab hidden or disabled. Authenticated → shows UserCards |
| U-63 | Search filters results | Type "E2E Test Business", assert matching card |
| U-64 | Country filter works | Select filter, assert URL param updates |
| U-65 | Filter panel renders | Assert Country, City, Industry, etc. controls |
| U-66 | Tags filter | Add tag, assert results update |
| U-67 | Infinite scroll | Scroll bottom (if enough data), assert loading/new results |
| U-68 | URL persistence on reload | Set filters, reload, assert preserved |
| U-69 | Empty state | Search nonsense, assert "No results" message |
| U-70 | Tab switching preserves query | Set query, switch tab, assert query preserved |
| U-71 | Ordering dropdown | Change to "name"/"newest", assert results re-sorted |
| U-72 | Business card navigates to profile | Click card, `waitForURL('/business/')` |
| U-73 | User card shows display info | Assert name, username, avatar on UserCard |
| U-74 | Multiple filters AND logic | Apply 2+ filters, assert combined filtering |

### 12-public-pages.spec.ts (U-75..U-82, 10 tests)

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-75 | Landing page `/` | Assert landing content |
| U-76 | About page `/about` | Assert heading |
| U-77 | Contact page `/contact` | Assert heading |
| U-78 | Public business profile | `/business/e2e-test-business` → name, profile data |
| U-79 | Request to Join visible (auth + open) | Login, assert "Request to Join" button |
| U-80 | Request to Join creates transaction | Click button, assert success toast + button changes |
| U-81 | Already member → no join button | Login as User B (owner), assert no join button |
| U-82 | Platform profile page | `/platform/profile` → page loads |

### 13-user-transactions.spec.ts (U-83..U-93, 13 tests)

Multi-user: User B (business owner) creates invitations for User A via API setup.

| U-ID | Test | Key Approach |
|------|------|-------------|
| U-83 | Activity page renders | `/activity` → heading, tabs (All/Sent/Received), status filter |
| U-84 | Empty state | Fresh user with no transactions → "No transactions found" |
| U-85 | Request to Join creates transaction | Click on business profile → Request → assert success |
| U-86 | Pending request in activity | After request, check `/activity` for pending item |
| U-87 | Cancel request | Cancel pending request, assert cancelled status |
| U-88 | Accept invitation | User B invites User A via API, User A accepts via UI |
| U-89 | Deny invitation | User B invites User A via API, User A denies |
| U-90 | Transaction detail page | Click transaction → `/activity/[id]` renders with timeline |
| U-91 | Sent tab filter | Click "Sent", assert only sent transactions |
| U-92 | Received tab filter | Click "Received", assert only received transactions |
| U-93 | Status filter | Select "Pending", assert only pending shown |

### 14-activity-notifications.spec.ts (U-94..U-96, 3 tests)

| U-ID | Test |
|------|------|
| U-94 | Activity accessible from sidebar nav |
| U-95 | Notifications page renders (placeholder) |
| U-96 | Notifications accessible from sidebar |

### 15-account-deactivation.spec.ts (U-97..U-99, 4 tests)

Uses dedicated `e2e_deactivate` user (consumed, not reusable).

| U-ID | Test | Selectors |
|------|------|-----------|
| U-97 | Deactivation dialog renders | `/settings` → click "Deactivate" → dialog with "Deactivate your account?", `getByPlaceholder("Type 'deactivate' to confirm")`, disabled "Deactivate Account" button |
| U-98 | Button enables only with "deactivate" typed | Type partial → disabled. Type "deactivate" → enabled |
| U-99 | Deactivation → logout → login fails | Click confirm → redirect to `/login`. Re-login → "Your account has been deactivated" |

---

## Custom Checklist Reporter

`reporters/checklist-reporter.ts` — extracts `[U-XX]` from test titles and generates:
- `reports/e2e-checklist-report.json` — machine-readable with pass/fail/skip/not-covered per item
- Console summary: `Passed: X/97 testable items (Y%)`

---

## Makefile Integration

```makefile
e2e-install:    # npm install + npx playwright install --with-deps chromium
e2e:            # npx playwright test (full suite)
e2e-ui:         # npx playwright test --ui (interactive)
e2e-headed:     # npx playwright test --headed (visible browser)
e2e-report:     # npx playwright show-report
e2e-section:    # npx playwright test tests/XX-name.spec.ts
```

---

## Items Not Fully Automatable

| U-ID | Reason | Mitigation |
|------|--------|------------|
| U-17 | Google OAuth → needs real Google credentials | Smoke test: assert button visible + clickable |
| U-18 | Apple OAuth → needs real Apple credentials | Smoke test: assert button visible + clickable |

97/99 = **98% automatable**, exceeding the >90% target.

---

## Implementation Phases

| Phase | Files | Tests |
|-------|-------|-------|
| **1. Foundation** | package.json, playwright.config, helpers (db, api, auth, constants, fixtures), global-setup/teardown, test fixture files | 0 |
| **2. Auth** | 01-registration, 02-email-verification, 03-login | 23 |
| **3. Password & Sessions** | 04-password-management, 05-session-management | 14 |
| **4. Profile & Settings** | 06-profile, 07-avatar, 08-username, 09-privacy | 22 |
| **5. Navigation & Explore** | 10-nav-layout, 11-explore, 12-public-pages | 38 |
| **6. Transactions & Deactivation** | 13-transactions, 14-activity, 15-deactivation | 20 |
| **7. Reporter & Polish** | checklist-reporter, Makefile targets, flaky test fixes | 0 |
| **Total** | 22 files | **117 tests** |

---

## Prerequisites to Run

1. `docker compose -f docker-compose.dev.yml up -d` (PostgreSQL + Redis)
2. `make dev` (Django server on :8000)
3. `cd frontend && npm run dev` (Next.js on :3000)
4. `cd e2e && npx playwright test`

---

## Verification

After implementation:
1. Run `make e2e` — all 117 tests should pass
2. Check `reports/e2e-checklist-report.json` — 95+ items should show "pass"
3. Open `reports/e2e-html/index.html` — Playwright HTML report for debugging any failures
4. Verify mobile viewport tests run correctly (navigation tests on Pixel 7)
