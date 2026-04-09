# Notification System — E2E Test Specification

**Version:** v1
**Date:** 2026-03-30
**Backend Reference:** `backend/apps/notifications/CLAUDE.md`
**Frontend Reference:** `docs/descriptions/frontend/notification-system-frontend-description.md`

---

## Overview

55 E2E tests across 10 categories covering the complete notification system: API CRUD, notification delivery flow, organization scope isolation, feature gate degradation, RBAC integration, scoped preferences, and frontend smoke tests.

**Prerequisites:**
- Docker infrastructure running (PostgreSQL + Redis)
- Django server running with `local_docker` settings
- Next.js frontend running
- At least 2 registered/verified users
- At least 1 business account with members

---

## 1. Notification Preferences API (10 tests)

| # | Test | Method | Endpoint | Expected |
|---|---|---|---|---|
| 1.1 | Get all preferences (authenticated) | GET | `/api/v1/notifications/preferences/` | 200, grouped by 5 categories (auth, security, transactional, marketing, social), all 27 types present |
| 1.2 | Get all preferences (unauthenticated) | GET | `/api/v1/notifications/preferences/` | 401 |
| 1.3 | Get single preference detail | GET | `/api/v1/notifications/preferences/new_login/` | 200, has notification_type, display_name, description, category, user_configurable, email_enabled, push_enabled, sms_enabled |
| 1.4 | Get unknown type returns 404 | GET | `/api/v1/notifications/preferences/nonexistent/` | 404 |
| 1.5 | Update preference (toggle email off) | PATCH | `/api/v1/notifications/preferences/new_login/` | 200, email_enabled=false, other fields unchanged |
| 1.6 | Update non-configurable type rejected | PATCH | `/api/v1/notifications/preferences/verify_email/` | 400, "Cannot modify preferences" |
| 1.7 | Update with no fields rejected | PATCH | `/api/v1/notifications/preferences/new_login/` | 400, "At least one channel preference must be provided" |
| 1.8 | Reset preference to defaults | DELETE | `/api/v1/notifications/preferences/new_login/` | 204, subsequent GET returns type defaults |
| 1.9 | Reset non-configurable type rejected | DELETE | `/api/v1/notifications/preferences/verify_email/` | 400 |
| 1.10 | Reset unknown type returns 404 | DELETE | `/api/v1/notifications/preferences/nonexistent/` | 404 |

---

## 2. Notification History API (15 tests)

| # | Test | Method | Endpoint | Expected |
|---|---|---|---|---|
| 2.1 | Get history (authenticated) | GET | `/api/v1/notifications/history/` | 200, has `notifications` array + `count` |
| 2.2 | Get history (unauthenticated) | GET | `/api/v1/notifications/history/` | 401 |
| 2.3 | Filter by notification_type | GET | `/api/v1/notifications/history/?notification_type=welcome` | Only notifications with matching type |
| 2.4 | Filter by status | GET | `/api/v1/notifications/history/?status=sent` | Only sent notifications |
| 2.5 | Filter by scope_type=user | GET | `/api/v1/notifications/history/?scope_type=user` | Only user-scoped notifications |
| 2.6 | Filter by scope_type + scope_id | GET | `/api/v1/notifications/history/?scope_type=business&scope_id={biz_id}` | Only that business's notifications |
| 2.7 | Pagination: limit | GET | `/api/v1/notifications/history/?limit=5` | Max 5 results returned |
| 2.8 | Pagination: offset | GET | `/api/v1/notifications/history/?offset=2&limit=3` | Skips first 2 results |
| 2.9 | Invalid limit (non-integer) degrades gracefully | GET | `/api/v1/notifications/history/?limit=abc` | 200, uses default limit 50 (no 500 error) |
| 2.10 | Invalid status ignored | GET | `/api/v1/notifications/history/?status=bogus` | 200, returns all (no filter applied) |
| 2.11 | Response includes scope fields and context | GET | `/api/v1/notifications/history/` | Each item has scope_type, scope_id, context fields |
| 2.12 | User isolation (can't see other's notifications) | GET | `/api/v1/notifications/history/` | User A sees only their own, not User B's |
| 2.13 | Tier 1.5: _permissions injected for org scope | GET | `/api/v1/notifications/history/?scope_type=business&scope_id={biz_id}` | Response has `_permissions` with can_view_notifications, can_manage_preferences, can_manage_org_notifications |
| 2.14 | Tier 1.5: _permissions NOT injected without scope_id | GET | `/api/v1/notifications/history/` | Response does NOT have `_permissions` key |
| 2.15 | Non-member gets empty list (not 403) | GET | `/api/v1/notifications/history/?scope_type=business&scope_id={other_biz_id}` | 200, notifications: [], count: 0 |

---

## 3. Notification Scopes API (4 tests)

| # | Test | Method | Endpoint | Expected |
|---|---|---|---|---|
| 3.1 | Get scopes (authenticated) | GET | `/api/v1/notifications/scopes/` | 200, has `scopes` array + `count` |
| 3.2 | Get scopes (unauthenticated) | GET | `/api/v1/notifications/scopes/` | 401 |
| 3.3 | Scopes include counts per scope_type | GET | `/api/v1/notifications/scopes/` | Each scope has scope_type, scope_id, count > 0 |
| 3.4 | Empty scopes for new user | GET | `/api/v1/notifications/scopes/` | scopes: [], count: 0 |

---

## 4. Configurable Types API (3 tests)

| # | Test | Method | Endpoint | Expected |
|---|---|---|---|---|
| 4.1 | Get configurable types (authenticated) | GET | `/api/v1/notifications/types/` | 200, has `types` array + `count` |
| 4.2 | Only user-configurable types returned | GET | `/api/v1/notifications/types/` | verify_email, welcome, password_reset, password_changed, suspicious_activity NOT in list |
| 4.3 | Type structure has all required fields | GET | `/api/v1/notifications/types/` | Each type has name, display_name, description, category, default_channels |

---

## 5. Notification Delivery — End-to-End Flow (6 tests)

These tests trigger real actions and verify that NotificationLog records are created with correct scope.

| # | Test | Trigger Action | Expected NotificationLog |
|---|---|---|---|
| 5.1 | Login triggers new_login notification | POST `/api/v1/auth/login/` (new device) | type=new_login, scope_type=user, scope_id=null |
| 5.2 | Registration triggers verify_email | POST `/api/v1/auth/register/` | type=verify_email, scope_type=user, scope_id=null |
| 5.3 | Password reset triggers notification | POST `/api/v1/auth/password/reset/` | type=password_reset, scope_type=user, scope_id=null |
| 5.4 | Transaction invitation triggers scoped notification | Create business invitation via transaction API | type=transaction_invitation_received, scope_type=business, scope_id={biz_id} |
| 5.5 | Transaction acceptance triggers scoped notification | Accept a pending transaction | type=transaction_accepted, scope_type=business, scope_id={biz_id} |
| 5.6 | Approval request uses send_to_org | Create business membership request | NotificationLog created for approvers + owner, scope_type=business, scope_id={biz_id} |

---

## 6. Organization Scope Isolation (4 tests)

| # | Test | Setup | Expected |
|---|---|---|---|
| 6.1 | Business notification has correct scope | After business transaction | scope_type=business, scope_id={biz_id} in history |
| 6.2 | User notification has correct scope | After login | scope_type=user, scope_id=null in history |
| 6.3 | History filter by business scope returns only that business | Create notifications in 2 businesses | Filtered result matches only queried business |
| 6.4 | Scopes endpoint shows distinct scopes | After mixed user + business notifications | Both "user" and "business" scopes appear with counts |

---

## 7. Feature Gate (4 tests)

These tests require modifying deployment config or using test overrides.

| # | Test | Config Change | Expected |
|---|---|---|---|
| 7.1 | System gate OFF → all endpoints 404 | Set `systems.notifications: false` | All 5 notification endpoints return 404 |
| 7.2 | System gate ON → endpoints respond | Set `systems.notifications: true` | All 5 endpoints return 200/2xx |
| 7.3 | Feature gate OFF → mandatory types still delivered | Set `user.notifications.enabled: false` | verify_email NotificationLog still created after registration |
| 7.4 | Feature gate OFF → configurable types skipped | Set `user.notifications.enabled: false` | new_login NOT created after login |

---

## 8. Scoped Preferences — Round Trip (3 tests)

| # | Test | Steps | Expected |
|---|---|---|---|
| 8.1 | Update → Get → Verify | PATCH new_login email_enabled=false → GET new_login | email_enabled=false in response |
| 8.2 | Update → Reset → Get defaults | PATCH new_login email_enabled=false → DELETE new_login → GET new_login | email_enabled matches type default (true) |
| 8.3 | Full CRUD cycle | GET defaults → PATCH change → GET verify → DELETE reset → GET defaults again | All states correct at each step |

---

## 9. RBAC Integration (4 tests)

| # | Test | Setup | Expected |
|---|---|---|---|
| 9.1 | send_to_org delivers to members with permission | Business with member having `can_approve_membership_request`, trigger approval notification | Member receives notification with correct scope |
| 9.2 | send_to_org always includes owner | Owner without explicit approval permission | Owner still receives the notification |
| 9.3 | send_to_org respects exclude_user_ids | Actor who triggers the event | Actor does NOT receive their own notification |
| 9.4 | Non-member excluded from org notification | User not in the business | User does NOT receive business-scoped notification |

---

## 10. Frontend Smoke Tests (6 tests)

These require browser automation (Playwright/Cypress).

| # | Test | Steps | Expected |
|---|---|---|---|
| 10.1 | Notification bell visible when logged in | Login → check Topbar | Bell icon rendered between logo and user menu |
| 10.2 | Notification bell hidden when logged out | Visit page without login | No bell icon in Topbar |
| 10.3 | Notification page loads | Login → navigate to `/notifications` | Page heading "Notifications" + notification list or empty state |
| 10.4 | Settings page shows notification preferences | Login → navigate to `/settings` | "Notification Preferences" section visible with category cards and toggle switches |
| 10.5 | Toggle preference switch | Settings → click email switch for "New Login Alert" | Switch toggles, API call fires, no error toast |
| 10.6 | Empty state for new user | Login as user with no notifications → `/notifications` | "No notifications yet" message displayed |

---

## Summary

| Category | Tests | Type |
|---|---|---|
| 1. Preferences API | 10 | API |
| 2. History API | 15 | API |
| 3. Scopes API | 4 | API |
| 4. Types API | 3 | API |
| 5. Delivery Flow | 6 | Integration |
| 6. Scope Isolation | 4 | Integration |
| 7. Feature Gate | 4 | Config |
| 8. Scoped Preferences | 3 | Round-trip |
| 9. RBAC | 4 | Integration |
| 10. Frontend Smoke | 6 | Browser |
| **Total** | **59** | |

---

## Test Data Requirements

- **User A:** Registered, verified, has login history (triggers new_login notifications)
- **User B:** Registered, verified, separate from User A (for isolation tests)
- **Business X:** Created by User A, with open member requests
- **User C:** Member of Business X with `can_approve_membership_request` role
- **User D:** NOT a member of Business X (for non-member tests)
- **Platform account:** Configured with at least one platform member

## Execution Notes

- Tests in categories 1-4 and 8 are stateless API tests — can run in any order
- Tests in category 5 create side effects (NotificationLog records) — run these before category 2 and 6
- Tests in category 7 require config changes — run in isolation or with test-specific config overrides
- Tests in category 9 require RBAC setup (roles, permissions, memberships) — run after business/member setup
- Tests in category 10 require running frontend + backend — run last
