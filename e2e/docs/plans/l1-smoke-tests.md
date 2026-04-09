# L1 Smoke Test Catalog

> **89 files** | **236 tests** | Projects: `smoke-desktop` (85 files) + `smoke-mobile` (4 files)
>
> Single-system, single-interaction verifications. Each test validates one page or feature works at its most basic level.

## Configuration

| Setting | Value |
|---------|-------|
| Projects | `smoke-desktop`, `smoke-mobile` |
| Workers | 4 (desktop), 2 (mobile) — CI: 2/1 |
| Retries | 1 in CI, 0 locally |
| Timeout | 30s per test |
| Viewport | 1280x720 (desktop), iPhone 14 Pro (mobile) |
| Artifacts | Screenshot on failure, trace on first retry |

---

## Auth (8 files, 33 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `login.spec.ts` | 10 | P1,P2,P3,P5,P7 | Valid/invalid/empty credentials, remember me, form validation |
| `register.spec.ts` | 7 | P1,P2,P5,P7 | Valid/duplicate/invalid registration, field validation |
| `logout.spec.ts` | 2 | P1,P2,P5,P14 | Session cleared, redirect, protected route inaccessible |
| `password-reset.spec.ts` | 4 | P1,P2,P4,P7 | Request reset email, enter token, set new password, login |
| `session-management.spec.ts` | 2 | P1,P5 | List active sessions, revoke specific session |
| `email-verification.spec.ts` | 4 | P1,P2,P4,P7 | Enter code, invalid code, resend, redirect on success |
| `password-change.spec.ts` | 1 | P1,P2,P5,P7 | Change password while logged in |
| `oauth-redirect.spec.ts` | 3 | P1,P2,P3 | Google/Apple redirect initiation (smoke only) |

## Users (7 files, ~23 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `profile-view.spec.ts` | 5 | P1,P3,P4,P5 | Avatar, bio, details display |
| `profile-edit.spec.ts` | 3 | P1,P2,P4,P5,P7 | Edit fields, save, cancel |
| `settings.spec.ts` | 6 | P1,P2,P5,P14 | Notification preferences, persistence |
| `home-feed.spec.ts` | 3 | P1,P3,P5 | Home renders after login |
| `activity-feed.spec.ts` | 3 | P1,P2,P3,P4,P5 | Activity list + detail |
| `other-user-profile.spec.ts` | 2 | P1,P3,P4,P5 | /users/[username] page |
| `username-change.spec.ts` | 1 | P1,P2,P4,P7 | Change + availability check |

## Business (13 files, 37 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `profile-public.spec.ts` | 5 | P1,P3,P5,P7 | Anonymous view, _permissions, visibility tiers |
| `create-business.spec.ts` | 3 | P1,P2,P4,P5 | Creation form, validation, redirect |
| `console-dashboard.spec.ts` | 5 | P1,P2,P3,P5 | Dashboard renders, stats, member count |
| `member-management.spec.ts` | 4 | P1,P2,P4,P5 | Member list, role badges, count |
| `role-management.spec.ts` | 3 | P1,P2,P5 | Role list, permissions, custom role |
| `business-settings.spec.ts` | 5 | P1,P2,P5 | Update fields, save, persist |
| `business-lifecycle.spec.ts` | 1 | P1,P2,P4,P5 | Suspend/reactivate/archive states |
| `member-actions.spec.ts` | 1 | P1,P2,P5,P7 | Suspend/ban/reactivate member |
| `member-detail.spec.ts` | 1 | P1,P5,P7 | Detail page, role badge, actions |
| `business-network.spec.ts` | 2 | P1,P3,P5 | Followers + connections management |
| `business-transactions-detail.spec.ts` | 3 | P1,P3,P5 | Requests/invitations list + detail |
| `business-audit.spec.ts` | 1 | P1,P5 | Audit log page |
| `business-visibility.spec.ts` | 3 | P1,P5,P7 | T2 visibility settings, public view changes |

## Platform (8 files, ~17 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `profile-public.spec.ts` | 1 | P1,P5 | Platform public profile |
| `console-dashboard.spec.ts` | 2 | P1,P3,P5 | Admin dashboard, stats |
| `platform-management.spec.ts` | 3 | P1,P2,P5 | Member list, roles |
| `platform-businesses.spec.ts` | 2 | P1,P5 | Business list management |
| `platform-cms.spec.ts` | 4 | P1,P2,P5 | CMS sites, templates, API keys |
| `platform-forms.spec.ts` | 2 | P1,P5 | Platform-scoped forms |
| `platform-transactions.spec.ts` | 2 | P1,P5 | Platform transactions |
| `platform-audit.spec.ts` | 1 | P1,P5 | Platform audit log |

## Chat (13 files, ~21 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `conversation-list.spec.ts` | 4 | P1,P3,P5 | List loads, empty state, items |
| `send-message.spec.ts` | 2 | P1,P2,P3,P5 | Type, send, appears in thread |
| `group-chat.spec.ts` | 2 | P1,P3,P5 | Create group, participants listed |
| `attachments.spec.ts` | 1 | P1,P2,P5 | Upload image, preview |
| `reactions.spec.ts` | 1 | P1,P2,P5 | Add/remove reaction, count |
| `search-messages.spec.ts` | 2 | P1,P3,P5 | Query, results, navigate |
| `chat-requests.spec.ts` | 1 | P1,P3,P5 | List, accept, decline |
| `message-edit-delete.spec.ts` | 2 | P1,P2,P5 | Edit own, delete own |
| `presence-indicators.spec.ts` | 1 | P1,P3,P5 | Online/offline dots |
| `delivery-status.spec.ts` | 1 | P1,P3,P5 | Sent/delivered/seen indicators |
| `group-admin.spec.ts` | 1 | P1,P2,P5 | Promote/demote/remove participant |
| `chat-mute.spec.ts` | 1 | P1,P2,P5 | Mute/unmute, badge suppression |
| `entity-sender-badge.spec.ts` | 2 | P1,P3,P5 | Business/platform sender indicator |

## Network (6 files, ~9 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `follow-business.spec.ts` | 2 | P1,P2,P3,P5 | Follow, verify, unfollow |
| `connect-user.spec.ts` | 1 | P1,P2,P3,P5 | Send connection request |
| `network-page.spec.ts` | 3 | P1,P3,P5 | Network page, tabs, content |
| `following-list.spec.ts` | 1 | P1,P3,P5 | Following businesses list |
| `connection-list.spec.ts` | 1 | P1,P3,P5 | User connections list |
| `disconnect.spec.ts` | 1 | P1,P2,P5 | Remove connection |

## Transactions (7 files, ~13 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `membership-invitation.spec.ts` | 2 | P1,P2,P5 | Create and view invitation |
| `join-request.spec.ts` | 2 | P1,P2,P5 | Submit join request |
| `ownership-transfer.spec.ts` | 1 | P1,P2,P5 | Initiate transfer |
| `transaction-list.spec.ts` | 3 | P1,P3,P5 | List, filter, pagination |
| `transaction-deny-cancel.spec.ts` | 1 | P1,P2,P5 | Deny/cancel actions |
| `transaction-pages.spec.ts` | 2 | P1,P3,P5 | Transaction detail pages |
| `form-mapping-settings.spec.ts` | 2 | P1,P2,P5 | Form mapping configuration |

## Forms (6 files, ~13 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `template-builder.spec.ts` | 3 | P1,P2,P5 | Create, add fields, save |
| `form-submission.spec.ts` | 2 | P1,P3,P5 | Fill all field types, submit |
| `form-responses.spec.ts` | 2 | P1,P3,P5 | Response list, detail view |
| `template-lifecycle.spec.ts` | 2 | P1,P2,P5 | Publish/archive/unarchive/fork |
| `field-crud.spec.ts` | 2 | P1,P2,P5 | Add/update/delete/reorder fields |
| `field-types-all.spec.ts` | 2 | P1,P4,P5 | All 14+ field types |

## CMS (5 files, ~9 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `cms-site-management.spec.ts` | 2 | P1,P2,P5 | CRUD sites |
| `cms-page-publish.spec.ts` | 2 | P1,P2,P5 | Create + publish page |
| `cms-content-editing.spec.ts` | 1 | P1,P2,P5 | Edit blocks, rich text |
| `cms-media-library.spec.ts` | 2 | P1,P2,P5 | Upload, list, delete media |
| `cms-api-keys.spec.ts` | 2 | P1,P2,P5 | Create (cmsk_ prefix), revoke |

## Notifications (3 files, ~4 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `notification-center.spec.ts` | 2 | P1,P3,P5 | List, badge, mark read |
| `notification-preferences.spec.ts` | 1 | P1,P2,P5 | Toggle categories, save |
| `notification-history.spec.ts` | 1 | P1,P3,P5 | Delivery history |

## Explore (3 files, ~9 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `search-businesses.spec.ts` | 5 | P1,P3,P5 | Search, results, detail link |
| `search-users.spec.ts` | 2 | P1,P3,P5 | User search, results |
| `filters.spec.ts` | 2 | P1,P3,P5 | Filter panel, active badges |

## Feature Gates (1 file, 3 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `feature-gate-403.spec.ts` | 3 | P1,P5,P6 | Disabled feature 403, UI hides |

## Limits (3 files, ~8 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `member-quota.spec.ts` | 3 | P1,P5,P10 | Fill to quota, over-quota error |
| `rate-limits.spec.ts` | 2 | P1,P4 | Rapid actions, 429 handling |
| `field-length-limits.spec.ts` | 3 | P1,P5 | Max length inline validation |

## Navigation (1 file, 5 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `account-switcher.spec.ts` | 5 | P1,P2,P3 | Personal → Business A → B, no data leakage |

## Public (1 file, 11 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `landing-pages.spec.ts` | 11 | P1,P3 | /, /about, /contact render correctly |

## Responsive / Mobile (4 files, ~21 tests)

| File | Tests | Parameters | Description |
|------|-------|-----------|-------------|
| `auth-mobile.spec.ts` | 6 | P1,P8 | Login/register on iPhone 14 Pro |
| `chat-mobile.spec.ts` | 3 | P7,P8 | Single-panel mode, back button |
| `navigation-mobile.spec.ts` | 6 | P2,P8 | Hamburger menu, all nav links |
| `business-console-mobile.spec.ts` | 6 | P2,P8 | Console adapts on mobile |
