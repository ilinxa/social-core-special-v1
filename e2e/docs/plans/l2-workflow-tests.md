# L2 Workflow Test Catalog

> **28 files** | **30 tests** | Project: `workflows`
>
> Cross-system, multi-step flows. Each workflow crosses 2-4 systems and validates realistic user journeys.

## Configuration

| Setting | Value |
|---------|-------|
| Project | `workflows` |
| Workers | 2 — CI: 1 |
| Retries | 2 in CI, 0 locally |
| Timeout | 30s per test |
| Viewport | 1280x720 |
| Artifacts | Screenshot on failure, trace on first retry, video on first retry |

---

## Active Workflows (25)

### Sub-Phase A — Auth/Registration (4)

| # | File | Systems | Multi-Context | Feature-Gated |
|---|------|---------|--------------|---------------|
| W1 | `auth-to-profile.spec.ts` | Auth, User | No | No |
| W2 | `business-creation-to-first-member.spec.ts` | Auth, Organization, Transaction, RBAC | Yes (2) | organization |
| W3 | `member-invitation-full-cycle.spec.ts` | Transaction, Organization, RBAC | Yes (2) | No |
| W17 | `registration-email-verification.spec.ts` | Auth, Email | No | No |

**W1**: Login → home → profile → refresh (session persistence) → sidebar nav.
**W2**: Register user A → grant business creation → create business via UI → register user B → invite B → B accepts → verify member count = 2.
**W3**: Owner invites user → owner sees pending invitation → invitee sees incoming → accept → member appears → invitee accesses console.
**W17**: Register via UI → enter verification code from DB → login with verified account.

### Sub-Phase B — Core Business (5)

| # | File | Systems | Multi-Context | Feature-Gated |
|---|------|---------|--------------|---------------|
| W4 | `join-request-with-form.spec.ts` | Transaction, Forms, Organization | Yes (2) | forms |
| W5 | `transaction-form-approval-workflow.spec.ts` | Transaction, Forms, Organization, RBAC | Yes (2) | forms |
| W8 | `two-user-chat-realtime.spec.ts` | Chat (WebSocket), Auth | Yes (2) | chat |
| W10 | `business-member-rbac-flow.spec.ts` | RBAC, Organization, Auth | Yes (2) | No |
| W15 | `member-quota-enforcement.spec.ts` | Organization, Transaction, RBAC | No | No |

**W4**: Owner creates form template + mapping → user submits join request with form → pending_review.
**W5**: Owner creates form mapping → user submits join request → owner views form submission → approves → member created.
**W8**: Two users in separate browser contexts → both open /chat → user A sends message → user B sees it in real-time (WebSocket) → B replies → A sees reply.
**W10**: Owner invites member → member has restricted settings view → owner assigns admin role → member sees edit controls.
**W15**: Set max_members=2 → fill to quota → attempt over-quota invitation → 400 → remove member → invitation succeeds.

### Sub-Phase C — Network + Ownership (6)

| # | File | Systems | Multi-Context | Feature-Gated |
|---|------|---------|--------------|---------------|
| W6 | `business-follow-to-join.spec.ts` | Network, Transaction, Organization | Yes (2) | network |
| W7 | `chat-conversation-lifecycle.spec.ts` | Chat, Auth | No | chat |
| W9 | `network-follow-connect-flow.spec.ts` | Network, Transaction, Auth | Yes (2) | network |
| W11 | `explore-to-interaction.spec.ts` | Explore, Network, Organization | No | network |
| W12 | `notification-triggered-actions.spec.ts` | Notifications | — | **DEFERRED** |
| W14 | `ownership-transfer-workflow.spec.ts` | Transaction, Organization, RBAC | Yes (2) | No |

**W6**: Follow business → verify in following list → request to join → owner accepts → member accesses console.
**W7**: Create DM + 3 messages via API → verify in UI → edit message → see "(edited)" → delete message → verify removed.
**W9**: User A creates business → B follows → B sends connection request to A → A accepts → both see connection in network.
**W11**: Create uniquely named business → search in /explore → find result → click → follow from profile page → verify in network.
**W14**: Owner A invites user B → B accepts → A transfers ownership to B → B can edit settings → A has reduced permissions.

### Sub-Phase D — Remaining (13)

| # | File | Systems | Multi-Context | Feature-Gated |
|---|------|---------|--------------|---------------|
| W13 | `platform-business-management.spec.ts` | Platform, Organization | No | organization |
| W16 | `entity-chat-business-context.spec.ts` | Chat, Organization, RBAC | Yes (2) | chat |
| W18 | `cms-content-lifecycle.spec.ts` | CMS, Platform | No | cms |
| W19 | `form-template-lifecycle.spec.ts` | Forms, Organization | No | forms |
| W20 | `member-discipline-flow.spec.ts` | Organization, RBAC, Auth | Yes (2) | No |
| W21 | `audit-trail-verification.spec.ts` | Organization, RBAC | — | **DEFERRED** |
| W22 | `business-status-lifecycle.spec.ts` | Organization, Platform, Auth | Yes (1) | No |
| W23 | `oauth-registration-flow.spec.ts` | Auth (OAuth) | No | No |
| W24 | `full-notification-lifecycle.spec.ts` | Notifications | — | **DEFERRED** |
| W25 | `chat-request-dm-block-flow.spec.ts` | Chat, Network | Yes (2) | chat |
| W26 | `form-builder-complete-lifecycle.spec.ts` | Forms, Organization | No | forms |
| W27 | `business-network-management.spec.ts` | Network, Organization | No | network |
| W28 | `feature-gate-degradation.spec.ts` | Feature Gates, Chat | No | N/A |

**W13**: Create 2 businesses → platform admin sees both in /pconsole/businesses → search/filter → detail view.
**W16**: Business entity sends message to external user → external sees entity sender badge → replies.
**W18**: Create CMS site + page via API → platform admin sees in /cconsole → publish/unpublish lifecycle.
**W19**: Create template → add fields → publish → submit response → verify in responses list.
**W20**: Owner suspends member → member loses access → owner reactivates → member regains access.
**W22**: Create business → verify active → suspend → verify status change → reactivate → verify active.
**W23**: Click "Continue with Google" → verify redirect URL (smoke-level, no full OAuth).
**W25**: User A DMs user B → B sees chat request → B accepts → B blocks A → A can't send more messages.
**W26**: Create template + 5 field types → publish → submit response → detail view shows all fields.
**W27**: 3 users follow business → owner sees follower count = 3 → search by username.
**W28**: Verify chat loads → intercept API with 403 → verify UI handles gracefully → remove intercept → verify recovery.

---

## Deferred Workflows (3)

| # | File | Blocker | Unblock When |
|---|------|---------|-------------|
| W12 | `notification-triggered-actions.spec.ts` | No notification inbox API | Backend inbox endpoints built |
| W21 | `audit-trail-verification.spec.ts` | No audit log read API | Backend audit query endpoint built |
| W24 | `full-notification-lifecycle.spec.ts` | No notification inbox API | Backend inbox endpoints built |

---

## Multi-Context Summary

12 workflows require 2+ browser contexts (two users logged in simultaneously):

W2, W3, W4, W5, W6, W8, W9, W10, W14, W16, W20, W25

Pattern:
```typescript
// helpers/auth.helper.ts — loginInNewContext()
const pageA = await loginInNewContext(browser, emailA, passwordA);
const pageB = await loginInNewContext(browser, emailB, passwordB);
// Both interact simultaneously
```

## Feature-Gated Summary

15 workflows conditionally skip based on deployment configuration:

```typescript
test.skip(!isSystemEnabled('chat'), 'Chat disabled');
test.skip(getOrgMode() === 'user_only', 'Organization disabled');
```
